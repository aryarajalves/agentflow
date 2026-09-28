import os
import re
import json
import random
import logging
import asyncio
import httpx
import anthropic
import openai
from datetime import datetime
from sqlalchemy import text as _text

from models import InteractionLog
from zapvoice_utils import (
    is_conversation_paused, 
    send_zapvoice_whatsapp_template, 
    sync_conversation_labels
)
from config_store import USD_TO_BRL, MODEL_INFO
from .evaluator import resolve_ab_variation

logger = logging.getLogger(__name__)

def _format_delay_text(delay_minutes: float) -> str:
    """Retorna uma representação textual amigável do tempo de inatividade."""
    mins = int(delay_minutes)
    if mins < 60:
        return f"{mins} minutos"
    elif mins >= 1440 and mins % 1440 == 0:
        d = mins // 1440
        return f"{d} dia" if d == 1 else f"{d} dias"
    else:
        h = round(delay_minutes / 60.0, 1)
        if h == int(h):
            h = int(h)
        return f"{h} hora" if h == 1 else f"{h} horas"


def _generate_followup_message(
    cw_url, cw_token, conta_id, conversa_id, delay_minutes, nome,
    custom_prompt=None, lead_msg=None, agent_resp=None
):
    """Consulta o histórico de mensagens e gera uma mensagem de follow-up com Claude Haiku."""
    history = ""
    try:
        if cw_url and cw_token and conta_id and conversa_id and str(conversa_id).strip() != "None":
            # Suporta rota Chatwoot e rota ZapVoice
            with httpx.Client(timeout=8) as client:
                resp = client.get(
                    f"{cw_url}/api/v1/accounts/{conta_id}/conversations/{conversa_id}/messages",
                    headers={"api_access_token": cw_token}
                )
                if resp.status_code != 200:
                    resp = client.get(
                        f"{cw_url}/api/chat/conversations/{conversa_id}/messages?limit=10",
                        headers={"Authorization": f"Bearer {cw_token}", "X-Client-ID": str(conta_id)}
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        all_msgs = data
                    elif isinstance(data, dict):
                        all_msgs = data.get("payload", {})
                        if isinstance(all_msgs, dict):
                            all_msgs = all_msgs.get("messages", [])
                        elif not isinstance(all_msgs, list):
                            all_msgs = data.get("messages", [])
                    else:
                        all_msgs = []

                    text_msgs = [m for m in all_msgs if isinstance(m, dict) and m.get("content") and m.get("message_type") in (0, 1)]
                    text_msgs.sort(key=lambda m: m.get("created_at", 0))
                    last_5 = text_msgs[-5:]

                    if last_5 and last_5[-1].get("message_type") == 0:
                        logger.info(f"[FollowUp] Lead enviou a última mensagem na conversa {conversa_id}. Cancelando envio do follow-up.")
                        return "LEAD_RESPONDED", None

                    if last_5:
                        history_lines = []
                        for m in last_5:
                            role = "Usuário" if m.get("message_type") == 0 else "Agente"
                            history_lines.append(f"{role}: {m['content'].strip()}")
                        history = "\n".join(history_lines)
    except Exception as e:
        logger.warning(f"[FollowUp] Aviso/Erro ao buscar histórico da API: {e}")

    if not history:
        h_parts = []
        if lead_msg and str(lead_msg).strip():
            h_parts.append(f"Usuário: {str(lead_msg).strip()}")
        if agent_resp and str(agent_resp).strip():
            h_parts.append(f"Agente: {str(agent_resp).strip()}")
        history = "\n".join(h_parts) if h_parts else "Agente: Olá! Como posso te ajudar?"

    delay_str = _format_delay_text(delay_minutes)

    if custom_prompt and custom_prompt.strip():
        instruction_text = (
            f"Diretriz/Instrução específica para este disparo de follow-up: {custom_prompt.strip()}\n\n"
            "Crie uma mensagem de follow-up curta, natural e amigável seguindo a instrução específica acima. "
            "Não mencione o tempo decorrido. Responda APENAS com a mensagem, sem explicações."
        )
    else:
        instruction_text = (
            "Crie uma mensagem de follow-up curta, natural e amigável que retome o assunto da última pergunta "
            "feita pelo Agente. Não mencione o tempo decorrido. Responda APENAS com a mensagem, sem explicações."
        )

    user_content = (
        f"Você é um assistente de atendimento. O contato '{nome}' não respondeu há {delay_str}.\n\n"
        f"Histórico recente da conversa:\n{history}\n\n"
        f"{instruction_text}"
    )

    # 1. Modelo Principal: gpt-5-mini (OpenAI)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            oai_client = openai.OpenAI(api_key=openai_key)
            completion = oai_client.chat.completions.create(
                model="gpt-5-mini",
                max_completion_tokens=500,
                messages=[{"role": "user", "content": user_content}]
            )
            text_out = (completion.choices[0].message.content or "").strip()
            if text_out:
                return text_out, completion.usage
        except Exception as e_gpt5:
            logger.warning(f"[FollowUp] Erro no modelo principal gpt-5-mini ({e_gpt5}). Tentando fallback gpt-4o-mini...")

        # 2. Modelo de Fallback: gpt-4o-mini (OpenAI)
        try:
            oai_client = openai.OpenAI(api_key=openai_key)
            completion = oai_client.chat.completions.create(
                model="gpt-4o-mini",
                max_completion_tokens=300,
                temperature=0.7,
                messages=[{"role": "user", "content": user_content}]
            )
            text_out = (completion.choices[0].message.content or "").strip()
            if text_out:
                return text_out, completion.usage
        except Exception as e_gpt4o:
            logger.warning(f"[FollowUp] Erro no modelo de fallback gpt-4o-mini ({e_gpt4o}).")

    # 3. Fallback secundário com Anthropic (caso disponível ou em testes)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            ai_client = anthropic.Anthropic(api_key=anthropic_key)
            result = ai_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{"role": "user", "content": user_content}]
            )
            return result.content[0].text.strip(), result.usage
        except Exception as e_anthropic:
            logger.warning(f"[FollowUp] Erro com Anthropic ({e_anthropic}).")

    # 4. Fallback de contingência amigável caso as APIs de IA falhem
    primeiro_nome = (nome or "").strip().split()[0] if (nome or "").strip() else "lá"
    fallback_msg = f"Oi {primeiro_nome}, tudo bem? Passando para saber se você conseguiu ver a mensagem anterior e se posso te ajudar em algo!"
    logger.info(f"[FollowUp] Usando mensagem amigável de contingência para '{nome}': {fallback_msg}")
    return fallback_msg, None


def save_followup_event(db, config_id, conta_id, conversa_id, telefone, nome, message, steps, status, step_index: int = 0, message_type: str = "text"):
    """Registra evento de log em webhook_events para que apareça no histórico do lead no frontend e conste como memória."""
    try:
        if status == "processed" and message:
            db.execute(_text("""
                INSERT INTO webhook_events (
                    webhook_config_id, conta_id, conversa_id, telefone, contato_nome,
                    mensagem, agent_response, dono, status, event_type, message_type,
                    processing_steps, created_at
                ) VALUES (
                    :wid, :conta, :conv, :tel, :nome,
                    :msg, :resp, 'Agente', 'processed', 'followup', :message_type,
                    :steps, :created_at
                )
            """), {
                "wid": config_id,
                "conta": str(conta_id),
                "conv": str(conversa_id),
                "tel": telefone,
                "nome": nome or telefone,
                "msg": f"🔄 [Follow-Up Passo #{step_index + 1}]",
                "resp": message,
                "message_type": message_type,
                "steps": json.dumps(steps, ensure_ascii=False),
                "created_at": datetime.utcnow()
            })
            db.commit()
    except Exception as e:
        logger.error(f"[FollowUp] Erro ao salvar evento no webhook_events: {e}")


async def dispatch_single_lead_followup(
    session_factory,
    config_id: int,
    leads_table: str,
    cw_url: str,
    cw_token: str,
    agent_id: int,
    zv_client_cfg: str | None,
    followup_add_label: str | None,
    step_raw: dict,
    step_index: int,
    delay_minutes: int,
    elapsed_minutes: float,
    lead_info: dict,
    apply_jitter: bool = True,
    is_manual: bool = False
) -> bool:
    """
    Processa e dispara o follow-up para um único lead de forma segura, assíncrona e com Jitter Anti-Ban.
    """
    lead_id = lead_info.get("id")
    conta_id = lead_info.get("conta_id") or "1"
    conversa_id = lead_info.get("conversa_id")
    telefone = lead_info.get("telefone") or ""
    nome = lead_info.get("contato_nome") or lead_info.get("nome") or telefone
    lead_msg = lead_info.get("mensagem")
    agent_resp = lead_info.get("ultima_resposta_agente")

    # 1. Aplicação do Teste A/B de Copy
    step, ab_variation = resolve_ab_variation(step_raw, telefone)

    # 2. Jitter Humano Anti-Ban (Pausa aleatória de 3 a 8 segundos entre os disparos)
    jitter_delay = 0.0
    if apply_jitter:
        jitter_delay = round(random.uniform(3.0, 8.0), 2)
        logger.info(f"[FollowUp Anti-Ban] Aguardando jitter de {jitter_delay}s antes de enviar para {telefone}")
        await asyncio.sleep(jitter_delay)

    db = session_factory()
    try:
        eff_conta_id = str(conta_id or zv_client_cfg or "1")
        eff_conversa_id = str(conversa_id or "1")

        eval_step_title = f"⚡ Disparo Manual: Follow-Up {step_index + 1}" if is_manual else f"Avaliando Disparo: Follow-Up {step_index + 1}"
        eval_step_detail = "Disparo acionado manualmente pelo operador no painel." if is_manual else (f"Tempo decorrido: {int(elapsed_minutes)}min úteis (Espera: {delay_minutes}min)." + (f" Jitter Anti-Ban: {jitter_delay}s aplicado." if jitter_delay > 0 else ""))

        pipeline_steps = [
            {
                "step": eval_step_title,
                "detail": eval_step_detail,
                "timestamp": datetime.utcnow().isoformat(),
                "is_manual": is_manual,
                "metadata": {"ab_variation": ab_variation} if ab_variation else None
            }
        ]

        step_type = step.get("type", "ai")
        custom_prompt = step.get("custom_prompt", "")
        fixed_message = step.get("fixed_message", "")

        # Higienização do nome
        raw_nome = (nome or "").strip()
        is_num = raw_nome.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "").isdigit()
        if not raw_nome or is_num or raw_nome.lower() in ("sem nome", "cliente", "lead"):
            clean_nome = ""
            primeiro_nome = ""
        else:
            clean_nome = raw_nome
            primeiro_nome = raw_nome.split()[0]

        media_url = step.get("media_url", "")
        media_type = step.get("media_type", "video" if step.get("media_type") == "video" else "audio")

        message = ""
        ai_usage = None
        processed_components = []

        if step_type == "fixed" and (fixed_message.strip() or (media_url and media_url.strip())):
            if fixed_message and fixed_message.strip():
                message = fixed_message.replace("{nome}", clean_nome) \
                                       .replace("{primeiro_nome}", primeiro_nome) \
                                       .replace("{telefone}", telefone or "")
                message = re.sub(r' +', ' ', message).strip()
            pipeline_steps.append({
                "step": "Usando Disparo de Mídia / Mensagem Fixa" + (f" (Variação {ab_variation})" if ab_variation else ""),
                "detail": f"Disparo de {(media_type or 'Mídia/Mensagem').upper()} formatada para {clean_nome or telefone}.",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"ab_variation": ab_variation} if ab_variation else None
            })
        elif step_type == "whatsapp_template":
            template_name = step.get("template_name") or ""
            template_language = step.get("language", "pt_BR")
            template_variables = step.get("template_variables") or {}
            template_header_media = step.get("template_header_media") or ""
            template_header_type = step.get("template_header_type") or "IMAGE"

            def resolve_val(raw_v):
                if not raw_v: return " "
                res = str(raw_v).replace("{nome}", clean_nome) \
                                .replace("{primeiro_nome}", primeiro_nome) \
                                .replace("{telefone}", telefone or "")
                return res.strip() if res.strip() else " "

            components_payload = []
            if template_header_media and template_header_media.strip():
                media_link = resolve_val(template_header_media.strip())
                media_type_key = template_header_type.lower()
                components_payload.append({
                    "type": "header",
                    "parameters": [{"type": media_type_key, media_type_key: {"link": media_link}}]
                })

            header_var_keys = sorted([k for k in template_variables.keys() if k.startswith("header_")])
            if header_var_keys:
                components_payload.append({
                    "type": "header",
                    "parameters": [{"type": "text", "text": resolve_val(template_variables.get(hk, ""))} for hk in header_var_keys]
                })

            body_var_keys = sorted([k for k in template_variables.keys() if k.startswith("body_")], key=lambda x: int(x.split("_")[1]) if x.split("_")[1].isdigit() else 0)
            if body_var_keys:
                components_payload.append({
                    "type": "body",
                    "parameters": [{"type": "text", "text": resolve_val(template_variables.get(bk, ""))} for bk in body_var_keys]
                })

            # ZapVoice e Meta WhatsApp Cloud API exigem que 'components' contenha APENAS
            # substituições de parâmetros (parameters). Se não houver variáveis ou mídia,
            # deve ser enviado como lista vazia [], nunca a estrutura crua do template.
            processed_components = components_payload if components_payload else []

            # Extrair o texto real do corpo do template resolvendo variáveis
            template_text = ""
            raw_comps = step.get("template_components") or []
            if isinstance(raw_comps, str):
                try:
                    raw_comps = json.loads(raw_comps)
                except Exception:
                    raw_comps = []

            for comp in raw_comps:
                if isinstance(comp, dict) and comp.get("type", "").upper() == "BODY":
                    body_txt = comp.get("text", "")
                    for bk in body_var_keys:
                        try:
                            idx_str = bk.split("_")[1]
                            val = resolve_val(template_variables.get(bk, ""))
                            body_txt = body_txt.replace(f"{{{{{idx_str}}}}}", val)
                        except Exception:
                            pass
                    template_text = body_txt.strip()
                    break

            if not template_text:
                template_text = step.get("fixed_message") or f"[Template Oficial]: {template_name}"

            message = template_text
            pipeline_steps.append({
                "step": "📱 Disparando Template WhatsApp Oficial" + (f" (Variação {ab_variation})" if ab_variation else ""),
                "detail": f"Template: '{template_name}' ({template_language}) via API Oficial ZapVoice.",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"ab_variation": ab_variation} if ab_variation else None
            })
        else:
            # IA Dinâmica
            pipeline_steps.append({
                "step": "Gerando mensagem do Agente com IA" + (f" (Variação {ab_variation})" if ab_variation else ""),
                "detail": f"Consultando histórico recente. Diretriz: '{custom_prompt or 'Padrão'}'",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"ab_variation": ab_variation} if ab_variation else None
            })
            message, ai_usage = _generate_followup_message(
                cw_url, cw_token, eff_conta_id, eff_conversa_id, delay_minutes,
                nome or telefone, custom_prompt=custom_prompt, lead_msg=lead_msg, agent_resp=agent_resp
            )

        if message == "LEAD_RESPONDED":
            logger.info(f"[FollowUp] Lead {telefone} respondeu a conversa recentemente. Interrompendo disparo.")
            pipeline_steps.append({"step": "Interrompido", "detail": "O cliente enviou mensagem no chat. Follow-up interrompido.", "timestamp": datetime.utcnow().isoformat()})
            save_followup_event(db, config_id, eff_conta_id, eff_conversa_id, telefone, nome, None, pipeline_steps, "lead_responded")
            return False

        if not message and not (media_url and media_url.strip()):
            logger.warning(f"[FollowUp] Não foi possível gerar mensagem nem mídia para lead {lead_id}, pulando.")
            return False

        usage_meta = {"ab_variation": ab_variation} if ab_variation else {}
        if ai_usage:
            usage_meta.update({
                "model": "claude-haiku-4-5-20251001",
                "usage": {
                    "input_tokens": getattr(ai_usage, 'input_tokens', 0),
                    "output_tokens": getattr(ai_usage, 'output_tokens', 0)
                }
            })
        pipeline_steps.append({
            "step": "Mensagem gerada e encaminhada",
            "detail": "Resposta final estruturada para o cliente.",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": usage_meta if usage_meta else None
        })

        sent_ok = False
        status_code_res = 500

        # Disparo Template vs Mensagem Normal
        if step_type == "whatsapp_template":
            zv_url = cw_url or "http://zapvoice_app:8000"
            try:
                sent_ok, zv_res = await send_zapvoice_whatsapp_template(
                    zapvoice_url=zv_url,
                    token=cw_token,
                    client_id=eff_conta_id,
                    phone=telefone,
                    template_name=template_name,
                    language=template_language,
                    components=processed_components
                )
                status_code_res = 200 if sent_ok else 500
            except Exception as e_tpl:
                logger.error(f"[FollowUp] Erro ao disparar template ZapVoice para {telefone}: {e_tpl}")
                sent_ok = False
        else:
            msg_payload = {"content": message or "", "message_type": "outgoing"}
            if media_url and media_url.strip():
                msg_payload["attachments"] = [{"file_type": media_type or "audio", "data_url": media_url.strip()}]
                pipeline_steps.append({
                    "step": "🎙️ Anexando Mídia / Áudio Humanizado",
                    "detail": f"Tipo: {(media_type or 'audio').upper()} | URL: {media_url.strip()}",
                    "timestamp": datetime.utcnow().isoformat()
                })

            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    msg_url = f"{cw_url}/api/v1/accounts/{eff_conta_id}/conversations/{eff_conversa_id}/messages"
                    headers = {"api_access_token": cw_token, "Content-Type": "application/json"}
                    resp = await client.post(msg_url, json=msg_payload, headers=headers)
                    status_code_res = resp.status_code
                    if resp.status_code in (200, 201):
                        sent_ok = True
                except Exception as e1:
                    logger.warning(f"[FollowUp] Tentativa 1 de envio para {telefone} falhou: {e1}")

                if not sent_ok and cw_url:
                    try:
                        zv_base = cw_url.rstrip("/")
                        if not zv_base.endswith("/api"): zv_base = f"{zv_base}/api"
                        zv_msg_url = f"{zv_base}/chat/conversations/{eff_conversa_id}/messages"
                        zv_headers = {
                            "Authorization": f"Bearer {cw_token}",
                            "X-Client-ID": str(eff_conta_id),
                            "Content-Type": "application/json"
                        }
                        resp_zv = await client.post(zv_msg_url, json={"content": message, "is_private": False}, headers=zv_headers)
                        status_code_res = resp_zv.status_code
                        if resp_zv.status_code in (200, 201):
                            sent_ok = True
                    except Exception as e2:
                        logger.warning(f"[FollowUp] Tentativa 2 ZapVoice para {telefone} falhou: {e2}")

        if sent_ok:
            db.execute(_text(f"""
                UPDATE {leads_table} 
                SET followup_step = :next_step, 
                    ultima_resposta_agente_em = :now,
                    ultima_resposta_agente = :agent_resp
                WHERE id = :id
            """), {
                "next_step": step_index + 1,
                "now": datetime.utcnow(),
                "agent_resp": message,
                "id": lead_id
            })
            pipeline_steps.append({"step": "📩 Mensagem Entregue", "detail": f"Status: {status_code_res}. Passo concluído.", "timestamp": datetime.utcnow().isoformat()})

            # Etiqueta de follow-up
            if followup_add_label and followup_add_label.strip() and eff_conversa_id:
                try:
                    lbl_to_add = followup_add_label.strip()
                    zv_client = zv_client_cfg or str(eff_conta_id or "1")
                    await sync_conversation_labels(
                        cw_url, str(zv_client), int(eff_conversa_id), cw_token, to_add=[lbl_to_add]
                    )
                    pipeline_steps.append({"step": "🏷️ Etiqueta de Follow-Up Aplicada", "detail": f"Etiqueta '{lbl_to_add}' adicionada no ZapVoice.", "timestamp": datetime.utcnow().isoformat()})
                except Exception as e_lbl:
                    logger.warning(f"[FollowUp] Falha ao aplicar etiqueta no ZapVoice: {e_lbl}")

            save_followup_event(db, config_id, eff_conta_id, eff_conversa_id, telefone, nome, message, pipeline_steps, "processed", step_index=step_index, message_type="template" if step_type == "whatsapp_template" else "text")

            # Custo financeiro
            try:
                input_tk = getattr(ai_usage, 'input_tokens', 0) if ai_usage else 0
                output_tk = getattr(ai_usage, 'output_tokens', 0) if ai_usage else 0
                haiku_info = MODEL_INFO.get("claude-4.5-haiku", {"input": 0.000001, "output": 0.000005})
                cost_usd = (input_tk * haiku_info["input"]) + (output_tk * haiku_info["output"])
                cost_brl = cost_usd * USD_TO_BRL

                log = InteractionLog(
                    agent_id=agent_id,
                    session_id=telefone,
                    user_message="[FOLLOW-UP AUTOMÁTICO]",
                    agent_response=message,
                    model_used="Claude Haiku (Follow-up)" + (f" [Var {ab_variation}]" if ab_variation else ""),
                    input_tokens=input_tk,
                    output_tokens=output_tk,
                    cost_usd=cost_usd,
                    cost_brl=cost_brl,
                    timestamp=datetime.utcnow()
                )
                db.add(log)
            except Exception as e_cost:
                logger.warning(f"[FollowUp] Erro ao registrar custo: {e_cost}")

            db.commit()
            logger.info(f"[FollowUp] Step {step_index + 1} enviado com sucesso para {telefone} (A/B: {ab_variation or 'N/A'})")
            return True
        else:
            logger.warning(f"[FollowUp] Falha ao enviar para {telefone}: HTTP {status_code_res}")
            pipeline_steps.append({"step": "Erro de Envio no Servidor", "detail": f"Status HTTP {status_code_res} ao enviar.", "timestamp": datetime.utcnow().isoformat()})
            save_followup_event(db, config_id, eff_conta_id, eff_conversa_id, telefone, nome, message, pipeline_steps, "error", step_index=step_index, message_type="template" if step_type == "whatsapp_template" else "text")
            return False
    finally:
        db.close()
