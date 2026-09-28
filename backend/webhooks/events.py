import re
import json
import logging
from typing import Optional
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from core.timezone import get_now_br, get_now_utc
from core.websocket import manager
from models import WebhookConfigModel, WebhookEventModel
from .schemas import (
    WebhookEventsPaginatedResponse,
    LeadHistoryResponse,
    LeadHistoryItem,
    BulkDeleteRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{webhook_id}/events", response_model=WebhookEventsPaginatedResponse)
async def list_webhook_events(
    webhook_id: int, 
    page: int = 1, 
    limit: int = 50, 
    status: Optional[str] = None,
    search: Optional[str] = None,
    dono: Optional[str] = None,
    event_type: Optional[str] = "message",
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * limit
    where_clauses = ["webhook_config_id = :wid"]
    params = {"wid": webhook_id, "limit": limit, "offset": offset}

    if status and status != 'all':
        where_clauses.append("status = :status")
        params["status"] = status
    else:
        where_clauses.append("status != 'skipped'")
    
    if dono:
        where_clauses.append("dono = :dono")
        params["dono"] = dono
    
    if event_type and event_type != "all":
        where_clauses.append("event_type = :event_type")
        params["event_type"] = event_type
        
    is_sqlite = db.bind.dialect.name == "sqlite"

    if search:
        digits_only = re.sub(r"\D", "", search)
        if len(digits_only) >= 7:
            suffix7 = digits_only[-7:]
            suffix8 = digits_only[-8:] if len(digits_only) >= 8 else digits_only
            clean_search = f"%{digits_only}%"
            plus_search = f"%+{digits_only}%"

            if is_sqlite:
                where_clauses.append("""(
                    telefone LIKE :search OR 
                    telefone LIKE :clean_search OR 
                    telefone LIKE :plus_search OR
                    RIGHT(telefone, 7) = :suffix7 OR 
                    RIGHT(telefone, 8) = :suffix8 OR 
                    contato_nome LIKE :search OR 
                    mensagem LIKE :search
                )""")
            else:
                where_clauses.append("""(
                    telefone ILIKE :search OR 
                    telefone ILIKE :clean_search OR 
                    telefone ILIKE :plus_search OR 
                    RIGHT(REGEXP_REPLACE(telefone, '[^0-9]', '', 'g'), 7) = :suffix7 OR 
                    RIGHT(REGEXP_REPLACE(telefone, '[^0-9]', '', 'g'), 8) = :suffix8 OR 
                    contato_nome ILIKE :search OR 
                    mensagem ILIKE :search OR
                    agent_response ILIKE :search
                )""")
            params["clean_search"] = clean_search
            params["plus_search"] = plus_search
            params["suffix7"] = suffix7
            params["suffix8"] = suffix8
        else:
            where_clauses.append("(telefone LIKE :search OR contato_nome ILIKE :search OR mensagem ILIKE :search OR agent_response ILIKE :search)")
        params["search"] = f"%{search}%"

    where_str = " AND ".join(where_clauses)
    
    total_res = await db.execute(text(f"SELECT COUNT(*) FROM webhook_events WHERE {where_str}"), params)
    total = total_res.scalar() or 0

    # Fallback: busca sem restringir por wid se busca por telefone retornar 0
    if total == 0 and search and len(re.sub(r"\D", "", search)) >= 7:
        fallback_clauses = [c for c in where_clauses if not c.startswith("webhook_config_id")]
        fallback_where_str = " AND ".join(fallback_clauses)
        fb_total_res = await db.execute(text(f"SELECT COUNT(*) FROM webhook_events WHERE {fallback_where_str}"), params)
        fb_total = fb_total_res.scalar() or 0
        if fb_total > 0:
            where_str = fallback_where_str
            total = fb_total

    query = text(f"""
        SELECT id, webhook_config_id, event_type, message_type, conta_id, inbox_id, inbox_nome,
               conversa_id, mensagem_id, contato_id, telefone, labels, contato_nome, mensagem,
               link, status, task_id, agent_response, legenda, dono, scheduled_at, created_at,
               updated_at, is_automatic, processing_steps, raw_payload
        FROM webhook_events WHERE {where_str} ORDER BY created_at DESC LIMIT :limit OFFSET :offset
    """)
    res = await db.execute(query, params)
    columns = res.keys()
    items = [dict(zip(columns, row)) for row in res.fetchall()]

    agent_responses_in_batch = {item['agent_response'].strip() for item in items if item.get('agent_response')}
    followup_msgs_in_batch = {
        item['agent_response'].strip()
        for item in items
        if item.get('event_type') == 'followup' and item.get('agent_response')
    }

    filtered_items = []
    for item in items:
        msg = (item.get('mensagem') or '').strip()
        resp = (item.get('agent_response') or '').strip()
        ev_type = item.get('event_type')

        # Se for um eco (memória ou outgoing) e houver um evento de follow-up correspondente no lote, descartar o eco
        if ev_type in ('memory', 'message') and (item.get('dono') in ('agente', 'bot') or ev_type == 'memory'):
            check_txt = resp if resp and not resp.startswith("Modo Silencioso") else msg
            if check_txt and any(check_txt == f_text or check_txt in f_text or f_text in check_txt for f_text in followup_msgs_in_batch if f_text):
                continue

        if item.get('event_type') == 'memory' and item.get('dono') not in ('agente', 'bot'):
            if msg and any(msg in resp_item or resp_item in msg for resp_item in agent_responses_in_batch if resp_item):
                item['dono'] = 'agente'
        
        is_agent_item = item.get('dono') in ('agente', 'bot') or item.get('event_type') == 'memory'
        if is_agent_item and not item.get('agent_response') and msg:
            if any(msg in resp_item or resp_item in msg for resp_item in agent_responses_in_batch if resp_item):
                continue

        # Enriquecer com informações de custo e se foi pelo cache semântico (de graça), zapvoice ou pago (IA)
        p_steps_raw = item.get("processing_steps")
        is_cache = False
        is_partial = False
        is_zapvoice_import = False
        cost = 0.0
        if p_steps_raw:
            try:
                p_steps = json.loads(p_steps_raw) if isinstance(p_steps_raw, str) else p_steps_raw
                if isinstance(p_steps, list):
                    for s in p_steps:
                        meta = s.get("metadata") or {}
                        if meta.get("is_zapvoice_import") or meta.get("origin") == "zapvoice_import":
                            is_zapvoice_import = True
                        if meta.get("from_semantic_cache") is True:
                            is_cache = True
                        elif meta.get("from_semantic_cache") == "partial":
                            is_partial = True
                        elif meta.get("from_semantic_cache") == "funnel" or meta.get("funnel_active"):
                            is_partial = True

                        step_cost = meta.get("cost") or s.get("cost")
                        if step_cost:
                            try:
                                cost += float(step_cost)
                            except (ValueError, TypeError):
                                pass

                        title = (s.get("step") or "").lower()
                        if title.startswith("📥 importação do zapvoice") or title.startswith("📥 importacao do zapvoice"):
                            is_zapvoice_import = True
                        if "cache semântico" in title or "cache semantico" in title:
                            if "funil" in title or "qualificação" in title or "qualificacao" in title or "parcial" in title:
                                is_partial = True
                            elif "custo zero" in title or "hit" in title or "resposta do cache" in title:
                                is_cache = True
            except Exception:
                pass

        raw_p = item.get("raw_payload")
        if raw_p:
            try:
                raw_data = json.loads(raw_p) if isinstance(raw_p, str) else raw_p
                if isinstance(raw_data, dict) and (raw_data.get("origin") == "zapvoice_import" or raw_data.get("is_zapvoice_import")):
                    is_zapvoice_import = True
            except Exception:
                pass

        if is_zapvoice_import:
            item["is_zapvoice_import"] = True
            item["origin"] = "zapvoice_import"
            item["from_semantic_cache"] = False
            item["is_partial_cache"] = False
            item["is_free"] = False
            item["cost"] = 0.0
            if item.get("message_type") == "template" or (isinstance(raw_p, str) and '"is_template": true' in raw_p.lower()):
                item["is_template"] = True
        else:
            if cost > 0:
                is_cache = False
                is_partial = True

            item["is_zapvoice_import"] = False
            item["from_semantic_cache"] = is_cache
            item["is_partial_cache"] = is_partial
            item["is_free"] = (is_cache and cost == 0.0) or (item.get("event_type") == "followup" and cost == 0.0)
            item["cost"] = round(cost, 4)
            if item.get("message_type") == "template" or (isinstance(raw_p, str) and '"is_template": true' in raw_p.lower()):
                item["is_template"] = True

        filtered_items.append(item)

    items = filtered_items
    return {"total": total, "items": items}


@router.get("/{webhook_id}/leads-by-phone/{phone}/history", response_model=LeadHistoryResponse)
async def get_lead_history(webhook_id: int, phone: str, page: int = 1, page_size: int = 50, db: AsyncSession = Depends(get_db)):
    config = await db.get(WebhookConfigModel, webhook_id)
    if not config: 
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    
    offset = (page - 1) * page_size
    
    total_query = text("""
        SELECT COALESCE(SUM(
            (CASE WHEN mensagem IS NOT NULL AND mensagem != '' THEN 1 ELSE 0 END) +
            (CASE WHEN agent_response IS NOT NULL AND agent_response != '' THEN 1 ELSE 0 END)
        ), 0)
        FROM webhook_events 
        WHERE webhook_config_id = :wid AND telefone = :tel AND status != 'skipped'
    """)
    total_res = await db.execute(total_query, {"wid": webhook_id, "tel": phone})
    total_messages = total_res.scalar() or 0

    query = text("SELECT id, contato_id, telefone, mensagem, dono, created_at, agent_response FROM webhook_events WHERE webhook_config_id = :wid AND telefone = :tel AND status != 'skipped' ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    res = await db.execute(query, {"wid": webhook_id, "tel": phone, "limit": page_size, "offset": offset})
    rows = res.fetchall()
    
    items = []
    for r in rows:
        evt_id, contato_id, telefone, mensagem, dono, created_at, agent_response = r
        if mensagem:
            items.append(LeadHistoryItem(
                id=evt_id,
                contato_id=contato_id,
                telefone=telefone,
                conteudo=mensagem,
                dono="Humano" if (dono and dono.lower() in ["cliente", "usuario"]) or not dono else "Agente",
                timestamp=created_at,
                index=0
            ))
        if agent_response:
            items.append(LeadHistoryItem(
                id=evt_id,
                contato_id=contato_id,
                telefone=telefone,
                conteudo=agent_response,
                dono="Agente",
                timestamp=created_at,
                index=0
            ))
            
    items.reverse()
    for idx, item in enumerate(items):
        item.index = idx + offset + 1
    items.reverse()
    
    return LeadHistoryResponse(total=total_messages, page=page, page_size=page_size, items=items)


@router.post("/{webhook_id}/events/bulk-delete", status_code=204)
async def delete_events_bulk(webhook_id: int, req: BulkDeleteRequest, db: AsyncSession = Depends(get_db)):
    await db.execute(text("DELETE FROM webhook_events WHERE id = ANY(:ids) AND webhook_config_id = :wid"), {"ids": req.event_ids, "wid": webhook_id})
    await db.commit()


@router.post("/{webhook_id}/events/{event_id}/cancel", status_code=200)
async def cancel_webhook_event_endpoint(webhook_id: int, event_id: int, db: AsyncSession = Depends(get_db)):
    event = await db.get(WebhookEventModel, event_id)
    if event and event.webhook_config_id == webhook_id:
        event.status = "canceled"
        
        steps = json.loads(event.processing_steps or "[]")
        steps.append({
            "step": "🚫 Automação Cancelada",
            "detail": "A automação para esta mensagem foi cancelada manualmente pelo usuário ou pelo sistema.",
            "timestamp": get_now_br().isoformat()
        })
        event.processing_steps = json.dumps(steps, ensure_ascii=False)
        
        await db.commit()
        
        await manager.broadcast({
            "type": "status_update",
            "webhook_id": webhook_id,
            "event_id": event_id,
            "status": "canceled",
            "steps": steps
        })
    return {"ok": True}


@router.post("/{webhook_id}/events/{event_id}/retry", status_code=200)
async def retry_webhook_event_endpoint(webhook_id: int, event_id: int, db: AsyncSession = Depends(get_db)):
    event = await db.get(WebhookEventModel, event_id)
    if not event or event.webhook_config_id != webhook_id:
        raise HTTPException(status_code=404, detail="Evento de webhook não encontrado")
        
    if event.status == "processing":
        last_update = event.updated_at or event.created_at
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
        
        time_elapsed = get_now_utc() - last_update
        if time_elapsed.total_seconds() < 120:
            raise HTTPException(status_code=400, detail="Este evento já está sendo processado no momento.")
        
    from webhook_tasks import process_webhook_automation
    
    event.status = "processing"
    event.agent_response = None
    if event.legenda and event.legenda.startswith("❌ Erro técnico:"):
        event.legenda = None
    
    now_br = get_now_br()
    steps = [{
        "step": "🔄 Reiniciando Pipeline",
        "detail": "A retentativa da automação foi iniciada manualmente pelo usuário. Reprocessando mensagem original...",
        "timestamp": now_br.isoformat()
    }]
    event.processing_steps = json.dumps(steps, ensure_ascii=False)
    event.updated_at = now_br
    
    await db.commit()
    
    try:
        await manager.broadcast({
            "type": "status_update",
            "webhook_id": webhook_id,
            "event_id": event_id,
            "status": "processing",
            "steps": steps
        })
    except Exception as ws_err:
        logger.error(f"Erro ao transmitir status_update via WS no retry: {ws_err}")
        
    process_webhook_automation.delay(event_id)
    logger.info(f"🔄 Retentativa manual de automação iniciada para o evento {event_id} (Webhook Config ID: {webhook_id})")
    
    return {"ok": True, "status": "processing"}


@router.get("/{webhook_id}/events/{event_id}")
async def get_webhook_event_detail(webhook_id: int, event_id: int, db: AsyncSession = Depends(get_db)):
    event = await db.get(WebhookEventModel, event_id)
    if not event or event.webhook_config_id != webhook_id:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    
    return {
        "id": event.id,
        "webhook_config_id": event.webhook_config_id,
        "status": event.status,
        "processing_steps": event.processing_steps,
        "agent_response": event.agent_response,
        "updated_at": event.updated_at,
        "scheduled_at": event.scheduled_at,
        "created_at": event.created_at,
        "server_now": get_now_br()
    }


@router.get("/events/{event_id}")
async def get_webhook_event_detail_by_id(event_id: int, db: AsyncSession = Depends(get_db)):
    event = await db.get(WebhookEventModel, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    
    return {
        "id": event.id,
        "webhook_config_id": event.webhook_config_id,
        "status": event.status,
        "processing_steps": event.processing_steps,
        "agent_response": event.agent_response,
        "updated_at": event.updated_at,
        "scheduled_at": event.scheduled_at,
        "created_at": event.created_at,
        "server_now": get_now_br()
    }


@router.post("/events/{event_id}/explain-response")
async def explain_webhook_event_response(event_id: int, db: AsyncSession = Depends(get_db)):
    """
    Analisa criticamente por que a IA gerou aquela resposta no evento de automação.
    Retorna a 1ª parte da resposta, a própria pergunta e o passo a passo do raciocínio.
    """
    event = await db.get(WebhookEventModel, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    raw_steps = event.processing_steps
    steps = raw_steps if isinstance(raw_steps, list) else json.loads(raw_steps or "[]")

    # 1. Se já existir o raciocínio nos metadados da etapa, retornar do cache imediato
    for s in steps:
        if isinstance(s, dict) and "Resposta gerada pelo agente" in s.get("step", ""):
            meta = s.get("metadata") or {}
            if meta.get("reasoning") and isinstance(meta.get("reasoning"), dict):
                return meta["reasoning"]

    # 2. Localizar dados de Raio-X e Resposta do Agente
    raiox_detail = None
    agent_resp_text = event.agent_response or ""

    for s in steps:
        if not isinstance(s, dict):
            continue
        step_name = s.get("step", "")
        if "Raio-X" in step_name:
            detail_val = s.get("detail", "{}")
            if isinstance(detail_val, str):
                try:
                    raiox_detail = json.loads(detail_val)
                except Exception:
                    raiox_detail = {"prompt_sistema": detail_val}
            elif isinstance(detail_val, dict):
                raiox_detail = detail_val
        elif "Resposta gerada pelo agente" in step_name:
            if not agent_resp_text and s.get("detail"):
                agent_resp_text = str(s.get("detail"))

    if not agent_resp_text:
        raise HTTPException(status_code=400, detail="Este evento não possui uma resposta gerada pelo agente para ser analisada.")

    resolved_prompt = ""
    user_message = event.mensagem or ""
    if raiox_detail:
        resolved_prompt = raiox_detail.get("prompt_sistema", "") or ""
        if not user_message:
            user_message = raiox_detail.get("mensagem_enviada_ao_agente") or raiox_detail.get("mensagem_original") or ""

    MAX_PROMPT_CHARS = 10000
    if len(resolved_prompt) > MAX_PROMPT_CHARS:
        resolved_prompt = resolved_prompt[:MAX_PROMPT_CHARS] + "\n\n[... prompt truncado para análise ...]"

    meta_prompt = f"""Você é um auditor especialista em sistemas de IA conversacional e funis de vendas.

Analise criticamente o contexto da conversa, as regras do prompt do sistema e a resposta gerada pela IA, e decomponha com clareza o motivo da resposta e o encadeamento de passos.

### Prompt do Sistema (Instruções e Regras dadas à IA):
{resolved_prompt}

### Mensagem Recebida do Usuário:
"{user_message}"

### Resposta Gerada pela IA:
"{agent_resp_text}"

Identifique com precisão cirúrgica:
1. "primeira_parte": A primeira sentença/frase da resposta (normalmente um acolhimento, simpatia, validação ou saudação) e o motivo exato pelo qual ela foi escolhida, citando explicitamente a regra do prompt que exigiu essa primeira parte (ex: regra de negação/continuidade do funil, diretriz de tom, etc.).
2. "pergunta_conducao": A pergunta ou condução realizada no corpo da resposta e o motivo exato pelo qual essa pergunta foi feita (ex: qual etapa do funil de qualificação estava pendente, ou qual exemplo/diretriz do prompt foi seguido).
3. "passo_a_passo": Uma lista de 3 a 5 passos sequenciais numerados explicando a linha de raciocínio da IA desde o recebimento da mensagem do usuário até a conclusão do texto.
4. "summary": Resumo executivo em 1-2 frases do raciocínio central da IA.
5. "fatores": Lista de até 4 fatores determinantes com "titulo", "explicacao" e "relevancia" ("alta", "media").

Retorne APENAS um JSON válido no seguinte formato:
{{
  "summary": "Resumo do raciocínio em 1-2 frases.",
  "primeira_parte": {{
    "texto": "Trecho da primeira parte da resposta",
    "motivo": "Explicação detalhada e direta de por que a IA gerou esse início, citando as regras do prompt correspondentes."
  }},
  "pergunta_conducao": {{
    "texto": "Trecho da pergunta ou condução formulada",
    "motivo": "Explicação detalhada de por que essa pergunta específica foi formulada pela IA."
  }},
  "passo_a_passo": [
    "Passo 1: ...",
    "Passo 2: ...",
    "Passo 3: ..."
  ],
  "fatores": [
    {{
      "titulo": "Nome da Regra ou Fator",
      "explicacao": "Como esse fator orientou a resposta.",
      "relevancia": "alta"
    }}
  ]
}}
"""

    from agent_core.clients import get_openai_client
    try:
        client = get_openai_client()
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": meta_prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        data = json.loads(completion.choices[0].message.content)

        # Salvar o raciocínio gerado dentro do metadata do passo para cache permanente
        updated_steps = False
        for s in steps:
            if isinstance(s, dict) and "Resposta gerada pelo agente" in s.get("step", ""):
                if "metadata" not in s or not isinstance(s["metadata"], dict):
                    s["metadata"] = {}
                s["metadata"]["reasoning"] = data
                updated_steps = True
                break

        if updated_steps:
            event.processing_steps = json.dumps(steps, ensure_ascii=False)
            await db.commit()

        return data

    except Exception as e:
        logger.error(f"Erro ao explicar resposta da automação no evento {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar explicação da resposta: {str(e)}")


@router.get("/{webhook_id}/followup-metrics")
async def get_webhook_followup_metrics(
    webhook_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retorna métricas consolidadas de conversão, disparos e teste A/B do Follow-Up."""
    from services.followup_modules.metrics import calculate_followup_metrics
    return await db.run_sync(lambda session: calculate_followup_metrics(session, webhook_id))

