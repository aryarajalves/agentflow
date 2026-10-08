import os
import json
import logging
from datetime import timedelta
from typing import Optional, Dict, Any
import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from database import get_db
from core.timezone import get_now_br, get_now_utc
from core.websocket import manager
from models import WebhookConfigModel, WebhookEventModel
from webhook_tasks import process_webhook_automation, sync_memory_to_vector, process_media_content_task
from .utils import normalize_phone, get_phone_suffix, texts_match_flexible, get_value_by_path, extract_and_compose_media_memory
from .service import ensure_leads_table, upsert_lead, handle_keyword_handoffs, save_media_memory_to_user_memory
from .import_chat_modules.helpers import is_system_or_badge_message

logger = logging.getLogger(__name__)
router = APIRouter()

def _get_redis():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis_lib.from_url(redis_url, decode_responses=True)
        r.ping()
        return r
    except Exception:
        try:
            r = redis_lib.from_url("redis://localhost:6382/0", decode_responses=True)
            r.ping()
            return r
        except Exception:
            return None

def _redis_get(key: str) -> Optional[str]:
    try:
        r = _get_redis()
        return r.get(key) if r else None
    except Exception:
        return None

def _redis_setex(key: str, ttl: int, value: str):
    try:
        r = _get_redis()
        if r:
            r.setex(key, ttl, value)
    except Exception:
        pass

CHATWOOT_URL_DEFAULT = (os.getenv("CHATWOOT_URL") or "").rstrip("/")
CHATWOOT_TOKEN_DEFAULT = os.getenv("CHATWOOT_API_TOKEN") or ""


@router.get("/receive/{token}", status_code=200, include_in_schema=False)
async def check_webhook_active(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WebhookConfigModel).where(WebhookConfigModel.token == token, WebhookConfigModel.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Webhook inativo ou token inválido")
    
    return {
        "status": "online",
        "webhook_name": config.name,
        "message": f"O webhook '{config.name}' está ativo e pronto para receber requisições POST!"
    }


@router.post("/receive/{token}", status_code=200, include_in_schema=False)
async def receive_webhook(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WebhookConfigModel).where(WebhookConfigModel.token == token, WebhookConfigModel.is_active == True))
    config = result.scalar_one_or_none()
    if not config: 
        raise HTTPException(status_code=404, detail="Webhook inativo")

    try: 
        body = await request.json()
    except Exception: 
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Extração Básica e Completa
    is_zapvoice = "event" in body and "message" in body and "contact" in body
    if is_zapvoice:
        zap_msg = body.get("message", {}) or {}
        zap_contact = body.get("contact", {}) or {}
        sender_type = zap_msg.get("sender_type", "contact")
        
        is_out = sender_type in ("user", "system")
        phone = normalize_phone(str(zap_contact.get("phone") or ""))
        msg_id = str(zap_msg.get("id") or "")
        
        labels_raw = zap_contact.get("labels", [])
        if not labels_raw:
            labels_raw = body.get("labels", [])
        labels_str = json.dumps(labels_raw) if isinstance(labels_raw, list) else str(labels_raw or "[]")
        
        content_type = zap_msg.get("message_type", "text")
        
        media_url_raw = str(zap_msg.get("media_url") or "")
        if media_url_raw.startswith("media_id:"):
            media_id = media_url_raw.split("media_id:")[1]
            zv_url = (config.zapvoice_url or os.getenv("ZAPVOICE_URL", "")).rstrip("/")
            if zv_url and not zv_url.endswith("/api"):
                zv_url = f"{zv_url}/api"
            zv_token = config.zapvoice_api_token or os.getenv("ZAPVOICE_API_TOKEN", "")
            client_id = str(body.get("client_id") or "")
            media_url_raw = f"{zv_url}/chat/media/{media_id}?client_id={client_id}&token={zv_token}"
        
        zv_name = (
            zap_contact.get("name") or 
            zap_contact.get("pushname") or 
            zap_contact.get("push_name") or 
            body.get("contact_name") or 
            body.get("name")
        )
        contato_nome_val = str(zv_name).strip() if zv_name and str(zv_name).strip() and str(zv_name).strip().lower() not in ("none", "null", "contato desconhecido") else None

        raw_zap_msg = str(zap_msg.get("template_content") or zap_msg.get("content") or "")
        media_info = extract_and_compose_media_memory(body, base_message=raw_zap_msg)

        extracted = {
            "conta_id": str(body.get("client_id") or ""),
            "inbox_id": str(body.get("client_id") or ""),
            "inbox_nome": "ZapVoice Canal",
            "conversa_id": str(zap_msg.get("conversation_id") or ""),
            "mensagem_id": msg_id,
            "contato_id": str(zap_contact.get("phone") or ""),
            "telefone": phone,
            "contato_nome": contato_nome_val,
            "mensagem": media_info["composed_message"],
            "labels": labels_str,
            "link": media_url_raw or media_info["media_url"],
            "dono": "agente" if is_out else "usuario",
            "message_type": content_type
        }
    else:
        conv = body.get("conversation", {}) or {}
        sender = body.get("sender", {}) or {}
        inbox = body.get("inbox", {}) or {}
        account = body.get("account", {}) or {}
        is_out = str(body.get("message_type")) in ("1", "outgoing")
        if is_out and "meta" in conv: 
            sender = conv["meta"].get("sender", sender)

        phone = normalize_phone(str(sender.get("phone_number") or ""))
        msg_id = str(body.get("id") or "")
        
        labels_raw = body.get("labels", [])
        if not labels_raw and conv:
            labels_raw = conv.get("labels", [])
        labels_str = json.dumps(labels_raw) if isinstance(labels_raw, list) else str(labels_raw or "[]")

        attachments = body.get("attachments", [])
        media_link = ""
        if attachments and len(attachments) > 0:
            media_link = str(
                attachments[0].get("data_url") or 
                attachments[0].get("url") or 
                attachments[0].get("file_url") or 
                attachments[0].get("attachment_url") or 
                ""
            )
        if not media_link:
            media_link = str(
                body.get("media_url") or 
                body.get("audio_url") or 
                body.get("file_url") or 
                body.get("data_url") or 
                body.get("link") or 
                ""
            )

        content_type = "text"
        if attachments and len(attachments) > 0:
            file_type = str(attachments[0].get("file_type") or attachments[0].get("type") or "").lower()
            if "image" in file_type or (media_link and media_link.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))):
                content_type = "image"
            elif "audio" in file_type or "voice" in file_type or (media_link and media_link.lower().endswith(('.ogg', '.mp3', '.wav', '.m4a', '.oga', '.opus'))):
                content_type = "audio"
            elif "video" in file_type:
                content_type = "video"
            elif "file" in file_type or "application" in file_type:
                content_type = "document"
            else:
                content_type = file_type or "file"
        elif body.get("message_type") in ("audio", "image", "video", "file", "document"):
            content_type = body.get("message_type")
        elif body.get("content_type") in ("audio", "image", "video", "file", "document"):
            content_type = body.get("content_type")

        meta_sender = (conv.get("meta", {}) or {}).get("sender", {}) or {}
        cw_name = (
            sender.get("name") or 
            sender.get("push_name") or 
            sender.get("pushname") or 
            meta_sender.get("name") or 
            meta_sender.get("push_name") or 
            (body.get("contact", {}) or {}).get("name") or 
            body.get("contact_name") or 
            body.get("name")
        )
        contato_nome_val = str(cw_name).strip() if cw_name and str(cw_name).strip() and str(cw_name).strip().lower() not in ("none", "null", "contato desconhecido") else None

        raw_body_msg = str(body.get("template_content") or body.get("content") or (body.get("message", {}) or {}).get("content") or "")
        media_info = extract_and_compose_media_memory(body, base_message=raw_body_msg)

        extracted = {
            "conta_id": str(body.get("account_id") or account.get("id") or conv.get("account_id") or ""),
            "inbox_id": str(inbox.get("id") or body.get("inbox_id") or conv.get("inbox_id") or ""),
            "inbox_nome": str(inbox.get("name") or ""),
            "conversa_id": str(conv.get("id") or body.get("conversation_id") or ""),
            "mensagem_id": msg_id,
            "contato_id": str(sender.get("id") or body.get("contact_id") or ""),
            "telefone": phone,
            "contato_nome": contato_nome_val,
            "mensagem": media_info["composed_message"],
            "labels": labels_str,
            "link": media_link or media_info["media_url"],
            "dono": "agente" if is_out else "usuario",
            "message_type": content_type
        }
    
    logger.info(f"📩 Webhook: {config.name} | De: {phone} | Msg: {extracted['mensagem'][:30]}... | Account: {extracted['conta_id']} | Inbox: {extracted['inbox_id']} | Conv: {extracted['conversa_id']} | Contact: {extracted['contato_id']}")

    # Filtro por ID do Cliente do ZapVoice (ou ID do Inbox do Chatwoot legado)
    target_client_id = config.zapvoice_client_id or getattr(config, 'chatwoot_inbox_id', None)
    if target_client_id and str(extracted.get("inbox_id") or "").strip() != str(target_client_id).strip():
        logger.info(f"⏭️ Webhook ignorado: inbox_id '{extracted.get('inbox_id')}' não corresponde ao configurado '{target_client_id}'")
        return {"ok": True, "status": "ignored_inbox"}

    # --- FILTRO DE BADGES E NOTIFICAÇÕES INTERNAS DE SISTEMA ---
    # Ignora logs administrativos (ex: "O atendente Super Admin adicionou marcador(es)...", tags internas, início de funil)
    # que não representam mensagens reais enviadas entre o contato e o agente/template
    check_badge_dict = {
        "content": extracted.get("mensagem") or "",
        "sender_type": zap_msg.get("sender_type") if is_zapvoice else (body.get("sender_type") or body.get("message_type")),
        "message_type": extracted.get("message_type") or "text",
        "meta_data": zap_msg.get("metadata") if is_zapvoice else body.get("meta_data")
    }
    if is_system_or_badge_message(check_badge_dict):
        logger.info(f"⏭️ Webhook ignorado: notificação interna de sistema/badge descartada para {phone} ({extracted['mensagem'][:50]})")
        return {"ok": True, "status": "system_badge_ignored"}

    # --- FILTRO DE MENSAGENS DE SAÍDA (ECHO) ---
    if is_out:
        resetting_key = f"webhook:resetting:{config.id}:{phone}"
        if _redis_get(resetting_key):
            logger.info(f"⏭️ Mensagem de saída de eco pós-reset ignorada para evitar recriação do lead {phone}")
            return {"ok": True, "status": "outgoing_ignored"}

        lead_id_out = None
        try:
            await ensure_leads_table(config.leads_table)
            lead_id_out = await upsert_lead(config.leads_table, {**extracted, "dono": "agente"}, config.id)
        except Exception as e:
            logger.error(f"Erro ao inserir lead de saída: {e}")

        if media_info.get("has_document_content"):
            await save_media_memory_to_user_memory(db, phone, lead_id_out, media_info)

        # Ingerir mensagem de saída (Template ou Atendente) na tabela webhook_events para histórico e memória da IA
        msg_out_text = (extracted.get("mensagem") or "").strip()
        msg_id_out = str(extracted.get("mensagem_id") or "").strip()
        
        if msg_out_text or extracted.get("link"):
            try:
                # Deduplicação por mensagem_id
                already_exists = False
                if msg_id_out:
                    dup_check = await db.execute(
                        select(WebhookEventModel.id).where(
                            WebhookEventModel.webhook_config_id == config.id,
                            WebhookEventModel.mensagem_id == msg_id_out
                        ).limit(1)
                    )
                    if dup_check.scalar_one_or_none():
                        already_exists = True

                # Deduplicação inteligente de ecos (Template / Follow-Up / Atendente / Memória):
                # Se nos últimos 120 segundos já foi registrado um evento para este telefone (com ou sem nono dígito)
                # com o mesmo texto ou se o texto faz parte de um evento recente do agente/followup
                if not already_exists and msg_out_text:
                    cutoff_dt = get_now_utc() - timedelta(seconds=120)
                    phone_suffix = get_phone_suffix(phone, 8)
                    recent_events_res = await db.execute(
                        select(WebhookEventModel.agent_response, WebhookEventModel.mensagem).where(
                            WebhookEventModel.webhook_config_id == config.id,
                            or_(
                                WebhookEventModel.telefone == phone,
                                WebhookEventModel.telefone.like(f"%{phone_suffix}")
                            ),
                            WebhookEventModel.created_at >= cutoff_dt
                        ).order_by(WebhookEventModel.created_at.desc()).limit(10)
                    )
                    for r_resp, r_msg in recent_events_res.fetchall():
                        r_resp_clean = (r_resp or "").strip()
                        r_msg_clean = (r_msg or "").strip()
                        valid_resp = r_resp_clean if not r_resp_clean.startswith("Modo Silencioso") else ""
                        if (
                            (valid_resp and texts_match_flexible(msg_out_text, valid_resp)) or
                            (r_msg_clean and texts_match_flexible(msg_out_text, r_msg_clean))
                        ):
                            already_exists = True
                            logger.info(f"⏭️ Mensagem de saída de eco descartada por duplicidade com evento recente de follow-up/agente para {phone}")
                            break

                if not already_exists:
                    now_br = get_now_br()
                    is_template = (
                        extracted.get("message_type") == "template" or
                        "template" in str(extracted.get("message_type", "")).lower() or
                        (isinstance(body.get("message"), dict) and bool(body.get("message", {}).get("template_name")))
                    )

                    step_title = "📋 Disparo Template WhatsApp" if is_template else "📤 Mensagem do Agente / Atendente"
                    step_detail = "Template Oficial disparado via ZapVoice" if is_template else "Mensagem enviada pelo atendente/sistema"

                    steps = [{
                        "step": step_title,
                        "detail": step_detail,
                        "timestamp": now_br.isoformat(),
                        "metadata": {
                            "is_out": True,
                            "is_template": is_template,
                            "origin": "outgoing_echo"
                        }
                    }]

                    out_event = WebhookEventModel(
                        webhook_config_id=config.id,
                        event_type="message",
                        status="completed",
                        message_type="template" if is_template else (extracted.get("message_type") or "text"),
                        conta_id=extracted.get("conta_id"),
                        inbox_id=extracted.get("inbox_id"),
                        inbox_nome=extracted.get("inbox_nome"),
                        conversa_id=extracted.get("conversa_id"),
                        mensagem_id=msg_id_out or None,
                        contato_id=extracted.get("contato_id"),
                        telefone=phone,
                        labels=extracted.get("labels"),
                        contato_nome=extracted.get("contato_nome"),
                        mensagem=None,
                        agent_response=msg_out_text,
                        link=extracted.get("link"),
                        raw_payload=json.dumps(body, ensure_ascii=False),
                        dono="agente",
                        created_at=now_br,
                        updated_at=now_br,
                        is_automatic=False,
                        processing_steps=json.dumps(steps, ensure_ascii=False)
                    )
                    db.add(out_event)
                    await db.commit()
                    await db.refresh(out_event)

                    await manager.broadcast({
                        "type": "new_event",
                        "webhook_id": config.id,
                        "event": {
                            "id": out_event.id,
                            "event_type": out_event.event_type,
                            "status": out_event.status,
                            "telefone": out_event.telefone,
                            "contato_nome": out_event.contato_nome,
                            "mensagem": out_event.mensagem,
                            "agent_response": out_event.agent_response,
                            "dono": out_event.dono,
                            "message_type": out_event.message_type,
                            "created_at": out_event.created_at.isoformat() if out_event.created_at else None
                        }
                    })
                    logger.info(f"✅ Mensagem de saída ({'Template' if is_template else 'Atendente'}) gravada em webhook_events: ID {out_event.id} para {phone}")
            except Exception as e_evt:
                logger.error(f"Erro ao salvar evento de saída em webhook_events: {e_evt}")

        return {"ok": True, "status": "outgoing_recorded"}

    # --- FILTRO DE CONTATOS PERMITIDOS E BLOQUEADOS ---
    blocked_list = []
    if config.blocked_messages:
        try:
            blocked_list = json.loads(config.blocked_messages)
        except Exception:
            blocked_list = []

    allowed_list = []
    if config.allowed_contacts:
        try:
            allowed_list = json.loads(config.allowed_contacts)
        except Exception:
            allowed_list = []

    def match_contact(item_to_match: str, phone_num: str, name_str: str) -> bool:
        item_str = str(item_to_match).strip().lower()
        if not item_str:
            return False
            
        clean_item = "".join(c for c in item_str if c.isdigit())
        if clean_item:
            clean_phone = "".join(c for c in phone_num if c.isdigit())
            match_len = min(8, len(clean_item), len(clean_phone))
            if match_len >= 6:
                return clean_phone[-match_len:] == clean_item[-match_len:]
                
        if name_str and item_str in name_str.lower():
            return True
            
        return False

    # 1. Validar se o contato está na lista de bloqueados
    for blocked_item in blocked_list:
        if match_contact(blocked_item, phone, extracted.get("contato_nome", "")):
            logger.info(f"🚫 Webhook bloqueado: Contato {phone} / {extracted.get('contato_nome')} está na lista de bloqueados.")
            return {"ok": True, "status": "blocked", "reason": "contact is blocked"}

    # 2. Validar se o contato está na lista de permitidos
    if allowed_list:
        is_allowed = False
        for allowed_item in allowed_list:
            if match_contact(allowed_item, phone, extracted.get("contato_nome", "")):
                is_allowed = True
                break
        
        if not is_allowed:
            logger.info(f"🚫 Webhook bloqueado: Contato {phone} / {extracted.get('contato_nome')} não está na lista de permitidos.")
            return {"ok": True, "status": "blocked", "reason": "contact not in allowed list"}

    # 1. Verificar palavra-chave de deleção antes de checar tag de ignorar
    is_delete_keyword = False
    msg_limpa = extracted["mensagem"].lower().strip()
    if msg_limpa and config.delete_keywords:
        try:
            keywords = []
            if config.delete_keywords.strip().startswith("["):
                keywords = json.loads(config.delete_keywords)
            else:
                keywords = [k.strip() for k in config.delete_keywords.split(",") if k.strip()]
            
            keywords_lower = [str(k).lower().strip() for k in keywords]
            if msg_limpa in keywords_lower:
                is_delete_keyword = True
                logger.info(f"🗑️ Mensagem coincide com palavra-chave de deleção: '{msg_limpa}'")
        except Exception as e:
            logger.error(f"Erro ao parsear delete_keywords: {e}")

    # 2. Filtro por etiqueta (Ignore by Label)
    if config.ignore_by_label and not is_delete_keyword:
        labels_list = labels_raw if isinstance(labels_raw, list) else []
        if config.ignore_by_label in labels_list:
            logger.info(f"🚫 Contato possui etiqueta de bloqueio/ignorar: '{config.ignore_by_label}'. Gravando mensagem e log de pausado.")
            now_br = get_now_br()
            
            steps = [{
                "step": "🚫 Automação Pausada",
                "detail": f"A automação para este contato está pausada porque ele possui a etiqueta '{config.ignore_by_label}', que indica suporte humano ativo ou pausa manual da IA.",
                "timestamp": now_br.isoformat()
            }]
            
            event = WebhookEventModel(
                webhook_config_id=config.id,
                event_type="message",
                status="ignored",
                message_type=content_type,
                conta_id=extracted.get("conta_id"),
                inbox_id=extracted.get("inbox_id"),
                inbox_nome=extracted.get("inbox_nome"),
                conversa_id=extracted.get("conversa_id"),
                mensagem_id=extracted.get("mensagem_id"),
                contato_id=extracted.get("contato_id"),
                telefone=phone,
                labels=extracted.get("labels"),
                contato_nome=extracted.get("contato_nome"),
                mensagem=extracted.get("mensagem"),
                link=extracted.get("link"),
                raw_payload=json.dumps(body, ensure_ascii=False),
                dono="usuario",
                agent_response=f"Automação pausada: Contato possui a etiqueta '{config.ignore_by_label}'",
                processing_steps=json.dumps(steps, ensure_ascii=False)
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)

            await manager.broadcast({
                "type": "new_event",
                "webhook_id": config.id,
                "event": {
                    "id": event.id,
                    "event_type": event.event_type,
                    "status": event.status,
                    "telefone": event.telefone,
                    "contato_nome": event.contato_nome,
                    "mensagem": event.mensagem,
                    "agent_response": event.agent_response,
                    "created_at": event.created_at.isoformat() if event.created_at else None
                }
            })

            try:
                await ensure_leads_table(config.leads_table)
                await upsert_lead(config.leads_table, extracted, config.id)
            except Exception as e:
                logger.error(f"Erro ao atualizar lead ignorado: {e}")

            return {"ok": True, "status": "ignored", "reason": f"contact has block label: {config.ignore_by_label}"}

    # --- LÓGICA DE AGRUPAMENTO (DEBOUNCE) ---
    now_br = get_now_br()
    redis_id_key = f"webhook:debounce:id:{config.id}:{phone}"
    redis_text_key = f"webhook:debounce:text:{config.id}:{phone}"
    
    last_event_id = _redis_get(redis_id_key)
    accumulated_text = _redis_get(redis_text_key) or ""
    
    if last_event_id:
        try:
            old_event_res = await db.execute(select(WebhookEventModel).where(WebhookEventModel.id == int(last_event_id)))
            old_event = old_event_res.scalar_one_or_none()
            
            if old_event and old_event.status == "waiting":
                old_event.status = "grouped"
                
                steps = json.loads(old_event.processing_steps or "[]")
                steps.append({
                    "step": "📦 Mensagem Absorvida",
                    "detail": "Uma nova mensagem chegou antes do processamento desta. Esta mensagem foi agrupada à próxima para manter o contexto e evitar respostas fragmentadas.",
                    "timestamp": now_br.isoformat()
                })
                old_event.processing_steps = json.dumps(steps, ensure_ascii=False)
                
                await manager.broadcast({
                    "type": "status_update",
                    "webhook_id": config.id,
                    "event_id": int(last_event_id),
                    "status": "grouped",
                    "steps": steps
                })
                
                if accumulated_text:
                    accumulated_text += "\n\n"
            else:
                accumulated_text = ""
        except Exception as e:
            logger.error(f"Erro ao agrupar evento anterior {last_event_id}: {e}")

    current_content = extracted.get("mensagem") or ""
    if content_type in ["audio", "image"]:
        current_content = f"[{content_type.upper()} PENDENTE]"
    
    accumulated_text += current_content
    
    event = WebhookEventModel(
        webhook_config_id=config.id, 
        event_type="message", 
        status="waiting" if config.delay_seconds > 0 else "processing", 
        raw_payload=json.dumps(body), 
        scheduled_at=now_br + timedelta(seconds=config.delay_seconds) if config.delay_seconds > 0 else None,
        created_at=now_br,
        **{**extracted, "mensagem": accumulated_text}
    )
    
    if config.delay_seconds > 0:
        event.processing_steps = json.dumps([{
            "step": "⏱️ Agrupamento Ativo",
            "detail": f"Aguardando {config.delay_seconds}s para ver se o usuário envia mais mensagens.",
            "timestamp": now_br.isoformat()
        }], ensure_ascii=False)
    
    db.add(event)
    await db.commit()
    await db.refresh(event)

    _redis_setex(redis_id_key, config.delay_seconds + 60, str(event.id))
    _redis_setex(redis_text_key, config.delay_seconds + 60, accumulated_text)

    # --- PROCESSAMENTO IMEDIATO DE MÍDIA ---
    if content_type in ["audio", "image"]:
        process_a = config.process_audio if config.process_audio is not None else True
        process_i = config.process_image if config.process_image is not None else True
        
        is_enabled = (content_type == "audio" and process_a) or (content_type == "image" and process_i)
        if is_enabled:
            logger.info(f"🎙️ Disparando processamento imediato de {content_type} para evento {event.id}")
            process_media_content_task.delay(config.id, event.id)

    try:
        await manager.broadcast({
            "type": "new_event",
            "webhook_id": config.id,
            "event": {
                "id": event.id,
                "telefone": event.telefone,
                "mensagem": event.mensagem,
                "agent_response": event.agent_response,
                "dono": event.dono,
                "message_type": event.message_type,
                "status": event.status,
                "scheduled_at": event.scheduled_at.isoformat() if event.scheduled_at else None,
                "created_at": event.created_at.isoformat() if event.created_at else None
            }
        })
    except Exception as ws_err:
        logger.error(f"Erro ao transmitir via WebSocket: {ws_err}")

    try:
        await ensure_leads_table(config.leads_table)
        await upsert_lead(config.leads_table, {**extracted, "dono": "cliente"}, config.id)
    except Exception as e:
        logger.error(f"Erro ao inserir lead na tabela {config.leads_table}: {e}")

    if await handle_keyword_handoffs(db, config, event, extracted, CHATWOOT_URL_DEFAULT, CHATWOOT_TOKEN_DEFAULT):
        event.status = "completed"
        await db.commit()
        return {"ok": True, "status": "handoff"}

    if config.delay_seconds > 0:
        logger.info(f"⏳ Agrupando automação para {event.telefone} em {config.delay_seconds}s (ID: {event.id})")
        process_webhook_automation.apply_async(args=[event.id], countdown=config.delay_seconds)
    else:
        process_webhook_automation.apply_async(args=[event.id])
    
    return {"ok": True, "event_id": event.id}


@router.get("/memory/{token}", status_code=200, include_in_schema=False)
async def check_memory_webhook(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WebhookConfigModel).where(WebhookConfigModel.memory_token == token, WebhookConfigModel.is_active == True))
    config = result.scalar_one_or_none()
    if not config or not config.memory_sync_enabled:
        raise HTTPException(status_code=404, detail="Memória desativada ou token inválido")
    
    return {
        "status": "online",
        "message": "O endpoint de memória está ativo e aguardando requisições POST!"
    }


@router.post("/memory/{token}", status_code=200, include_in_schema=False)
async def receive_memory_webhook(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WebhookConfigModel).where(WebhookConfigModel.memory_token == token, WebhookConfigModel.is_active == True))
    config = result.scalar_one_or_none()
    if not config or not config.memory_sync_enabled: 
        raise HTTPException(status_code=404, detail="Memória desativada")

    try: 
        body = await request.json()
    except Exception: 
        raise HTTPException(status_code=400, detail="JSON inválido")

    phone_raw = get_value_by_path(body, config.memory_phone_path)
    if not phone_raw:
        phone_raw = get_value_by_path(body, "telefone") or get_value_by_path(body, "phone") or get_value_by_path(body, "sender.phone")
        
    phone = normalize_phone(str(phone_raw or ""))
    if not phone: 
        raise HTTPException(status_code=400, detail="Telefone não encontrado. O JSON deve conter 'phone', 'telefone' ou 'sender.phone'")

    media_info = extract_and_compose_media_memory(body)
    mensagem_text = media_info["composed_message"]
    dono_raw = (
        get_value_by_path(body, "Dono") or 
        get_value_by_path(body, "dono") or 
        get_value_by_path(body, "sender_type") or 
        get_value_by_path(body, "sender.type")
    )
    if not dono_raw:
        direction = get_value_by_path(body, "direction") or get_value_by_path(body, "type") or ""
        from_me = get_value_by_path(body, "from_me") or get_value_by_path(body, "fromMe")
        if str(direction).lower() in ("outgoing", "outbound", "sent") or from_me is True or str(from_me).lower() == "true":
            dono = "agente"
        else:
            dono = "cliente"
    else:
        dono = str(dono_raw).lower()

    # Filtro de Badges e Arquivos Não Suportados no Webhook de Memória
    check_badge_dict = {
        "content": mensagem_text,
        "sender_type": dono,
        "message_type": body.get("message_type") or "text",
        "meta_data": body.get("meta_data")
    }
    if is_system_or_badge_message(check_badge_dict):
        logger.info(f"⏭️ Webhook de memória ignorado: badge/não suportado descartado para {phone} ({mensagem_text[:50]})")
        return {"ok": True, "status": "system_badge_ignored"}

    if dono not in ("agente", "bot"):
        phone_suffix = get_phone_suffix(phone, 8)
        recent_agent_evt = await db.execute(
            select(WebhookEventModel).where(
                WebhookEventModel.webhook_config_id == config.id,
                or_(
                    WebhookEventModel.telefone == phone,
                    WebhookEventModel.telefone.like(f"%{phone_suffix}")
                ),
                WebhookEventModel.agent_response.isnot(None),
                WebhookEventModel.agent_response != ""
            ).order_by(WebhookEventModel.created_at.desc()).limit(5)
        )
        recent_evts = recent_agent_evt.scalars().all()
        for revt in recent_evts:
            if revt.agent_response and not revt.agent_response.startswith("Modo Silencioso") and mensagem_text and (
                texts_match_flexible(mensagem_text, revt.agent_response)
            ):
                dono = "agente"
                break

    name_raw = None
    if getattr(config, 'memory_name_path', None):
        name_raw = get_value_by_path(body, config.memory_name_path)
    if not name_raw:
        name_raw = (
            get_value_by_path(body, "name") or 
            get_value_by_path(body, "nome") or 
            get_value_by_path(body, "contato_nome") or 
            get_value_by_path(body, "sender.name") or 
            get_value_by_path(body, "contact.name") or 
            get_value_by_path(body, "pushname")
        )

    memory_contato_nome = str(name_raw).strip() if name_raw and str(name_raw).strip() and str(name_raw).strip().lower() not in ("none", "null", "contato desconhecido") and not str(name_raw).strip().startswith("Lead_") else None

    await ensure_leads_table(config.leads_table)
    lead_id = await upsert_lead(config.leads_table, {
        "telefone": phone, 
        "contato_nome": memory_contato_nome, 
        "dono": dono,
        "mensagem": mensagem_text,
        "link": media_info["media_url"] or None,
        "is_memory": True,
        "event_type": "memory"
    }, config.id)

    if media_info.get("has_document_content"):
        await save_media_memory_to_user_memory(db, phone, lead_id, media_info)
    
    preview_msg = (mensagem_text[:50] + "...") if len(mensagem_text) > 50 else mensagem_text
    logger.info(
        f"💾 [MEMÓRIA RECEBIDA] Mensagem registrada no lead ({phone}) | "
        f"Autor: {dono} | Nome: {memory_contato_nome or 'Desconhecido'} | "
        f"Mídia Anexada: {media_info.get('filename') or 'Não'} | Texto: '{preview_msg}'"
    )

    now_br = get_now_br()
    is_agent_message = dono in ("agente", "bot")

    # Detecta se é disparo de template
    is_template = bool(
        get_value_by_path(body, "template_content") or 
        get_value_by_path(body, "template_name") or 
        get_value_by_path(body, "is_template") or 
        str(get_value_by_path(body, "message_type") or "").lower() == "template"
    )
    detected_msg_type = "template" if is_template else (get_value_by_path(body, "message_type") or "text")

    # Se for mensagem enviada pelo agente/empresa, status nasce completed para evitar loop de auto-resposta
    event_status = "completed" if (is_agent_message or (media_info.get("has_document_content") and not body.get("facts"))) else "waiting"
    agent_resp = (
        "Modo Silencioso (Disparo de Template)" if is_template else "Modo Silencioso (Mensagem de Saída)"
    ) if is_agent_message else None

    detail_step = (
        (
            f"Disparo de template com conteúdo de mídia anexado ({media_info['filename'] or 'Documento'}) registrado com sucesso na memória do contato."
            if media_info.get("has_document_content")
            else "Disparo de template registrado com sucesso no histórico do contato."
        ) if is_template else
        "Mensagem de saída registrada com sucesso no histórico do contato."
    ) if is_agent_message else "Os dados foram recebidos e estão aguardando o processamento da fila de vetorização."

    step_title = "💾 Disparo de Template Registrado" if is_template else (
        "💾 Mensagem de Saída Registrada" if is_agent_message else "📥 Recebido Webhook de Memória"
    )

    if is_agent_message:
        cutoff_dt = get_now_utc() - timedelta(seconds=120)
        phone_suffix = get_phone_suffix(phone, 8)
        recent_evts_res = await db.execute(
            select(WebhookEventModel.id, WebhookEventModel.agent_response, WebhookEventModel.mensagem).where(
                WebhookEventModel.webhook_config_id == config.id,
                or_(
                    WebhookEventModel.telefone == phone,
                    WebhookEventModel.telefone.like(f"%{phone_suffix}")
                ),
                WebhookEventModel.created_at >= cutoff_dt
            ).order_by(WebhookEventModel.created_at.desc()).limit(10)
        )
        for r_id, r_resp, r_msg in recent_evts_res.fetchall():
            r_resp_clean = (r_resp or "").strip()
            r_msg_clean = (r_msg or "").strip()
            valid_resp = r_resp_clean if not r_resp_clean.startswith("Modo Silencioso") else ""
            if mensagem_text and (
                (valid_resp and texts_match_flexible(mensagem_text, valid_resp)) or
                (r_msg_clean and texts_match_flexible(mensagem_text, r_msg_clean))
            ):
                doc_str = media_info.get("document_content") or ""
                if doc_str and doc_str not in valid_resp and doc_str not in r_msg_clean:
                    existing_evt = await db.get(WebhookEventModel, r_id)
                    if existing_evt:
                        if existing_evt.agent_response and not existing_evt.agent_response.startswith("Modo Silencioso"):
                            existing_evt.agent_response = mensagem_text
                        if existing_evt.mensagem or existing_evt.event_type == "memory":
                            existing_evt.mensagem = mensagem_text
                        if media_info.get("media_url") and not existing_evt.link:
                            existing_evt.link = media_info["media_url"]
                        await db.commit()
                        logger.info(f"✨ Evento recente {r_id} enriquecido com conteúdo de mídia anexada ({media_info.get('filename')}) para {phone}")
                        return {"ok": True, "phone": phone, "event_id": r_id, "status": "agent_memory_saved_to_history"}

                logger.info(f"⏭️ Webhook de memória do agente ignorado por duplicidade com evento recente {r_id} para {phone}")
                return {"ok": True, "phone": phone, "event_id": r_id, "status": "duplicate_agent_memory_ignored"}

    event = WebhookEventModel(
        webhook_config_id=config.id,
        event_type="memory",
        message_type=detected_msg_type,
        status=event_status,
        raw_payload=json.dumps(body, ensure_ascii=False),
        telefone=phone,
        contato_nome=memory_contato_nome or ("Lead_" + phone[-4:]),
        dono=dono,
        mensagem=mensagem_text,
        link=media_info["media_url"] or None,
        agent_response=agent_resp,
        created_at=now_br,
        processing_steps=json.dumps([{
            "step": step_title,
            "detail": detail_step,
            "timestamp": now_br.isoformat(),
            "metadata": {
                "has_document_content": media_info.get("has_document_content", False),
                "filename": media_info.get("filename") or None,
                "media_url": media_info.get("media_url") or None,
                "template_name": media_info.get("template_name") or None
            }
        }], ensure_ascii=False)
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    if is_agent_message:
        logger.info(
            f"🛡️ [HISTÓRICO REGISTRADO] Mensagem/Template do agente armazenado no histórico ({phone}) "
            f"com ID {event.id} - IA não auto-responderá para evitar loop."
        )
        if body.get("facts"):
            sync_memory_to_vector.delay(event.id)
        return {"ok": True, "phone": phone, "event_id": event.id, "status": "agent_memory_saved_to_history"}

    if body.get("facts") or not media_info.get("has_document_content"):
        sync_memory_to_vector.delay(event.id)
    return {"ok": True, "phone": phone, "event_id": event.id}
