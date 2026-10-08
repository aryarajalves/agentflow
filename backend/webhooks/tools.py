import os
import json
import time
import logging
from typing import Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from core.timezone import get_now_br
from models import WebhookConfigModel, WebhookEventModel
from webhook_tasks import process_webhook_automation
from .schemas import SimulateLoadRequest
from .service import ensure_leads_table, upsert_lead

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{webhook_id}/simulate-load", status_code=200, include_in_schema=False)
async def simulate_webhook_load(
    webhook_id: int, 
    payload: SimulateLoadRequest, 
    db: AsyncSession = Depends(get_db)
):
    config = await db.get(WebhookConfigModel, webhook_id)
    if not config:
        raise HTTPException(status_code=404, detail="Integração de Webhook não encontrada")

    await ensure_leads_table(config.leads_table)

    start_time = time.time()
    contacts_processed = 0
    errors_count = 0
    now_br = get_now_br()

    base_phone_num = 558599000000
    msg_text = payload.sample_message or "Olá, gostaria de testar o suporte e a automação do sistema."
    
    delay_sec = config.delay_seconds if (config.delay_seconds is not None) else 30
    events_to_process = []

    for i in range(1, payload.contact_count + 1):
        fake_phone = str(base_phone_num + i)
        fake_name = f"Contato Simulado {i}"
        
        try:
            await upsert_lead(config.leads_table, {
                "telefone": fake_phone,
                "contato_nome": fake_name,
                "mensagem": msg_text,
                "dono": "cliente"
            }, config.id)

            initial_steps = []
            if delay_sec > 0:
                initial_steps.append({
                    "step": "⏱️ Agrupamento Ativo (Debounce)",
                    "detail": f"Aguardando {delay_sec}s para ver se o usuário envia mais mensagens.",
                    "timestamp": now_br.isoformat()
                })

            is_waiting = payload.respect_delay and (delay_sec > 0)

            event = WebhookEventModel(
                webhook_config_id=config.id,
                event_type="message",
                message_type="text",
                status="waiting" if is_waiting else "received",
                raw_payload=json.dumps({"simulated": True, "phone": fake_phone, "message": msg_text}, ensure_ascii=False),
                telefone=fake_phone,
                contato_nome=fake_name,
                mensagem=msg_text,
                conversa_id=str(900000 + i),
                conta_id="1",
                dono="usuario",
                created_at=now_br,
                scheduled_at=now_br + timedelta(seconds=delay_sec) if is_waiting else None,
                processing_steps=json.dumps(initial_steps, ensure_ascii=False) if initial_steps else None
            )
            db.add(event)
            await db.flush()

            if is_waiting:
                process_webhook_automation.apply_async(args=[event.id], countdown=delay_sec)
                contacts_processed += 1
            else:
                events_to_process.append(event.id)
        except Exception as e:
            logger.error(f"Erro ao criar evento simulado para contato {i}: {e}")
            errors_count += 1

    await db.commit()

    if not payload.respect_delay:
        for eid in events_to_process:
            try:
                process_webhook_automation(eid)
                contacts_processed += 1
            except Exception as e:
                logger.error(f"Erro ao executar pipeline para evento {eid}: {e}")
                errors_count += 1

    elapsed_sec = max(0.001, time.time() - start_time)
    elapsed_ms = round(elapsed_sec * 1000, 2)
    throughput = round(contacts_processed / elapsed_sec, 1)
    avg_latency_ms = round(elapsed_ms / max(1, contacts_processed), 2)

    return {
        "ok": True,
        "total_requested": payload.contact_count,
        "contacts_processed": contacts_processed,
        "errors_count": errors_count,
        "elapsed_ms": elapsed_ms,
        "throughput_per_sec": throughput,
        "avg_latency_ms": avg_latency_ms,
        "message": f"Simulação de carga concluída: {contacts_processed} contatos processados por TODA A PIPELINE a {throughput} req/s."
    }


@router.get("/{webhook_id}/whatsapp-templates")
async def get_webhook_whatsapp_templates(
    webhook_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Busca a lista de templates oficiais do WhatsApp configurados no ZapVoice para este webhook."""
    query = select(WebhookConfigModel).where(WebhookConfigModel.id == webhook_id)
    res = await db.execute(query)
    config = res.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")

    from zapvoice_utils import get_zapvoice_whatsapp_templates
    zv_url = config.zapvoice_url or os.getenv("ZAPVOICE_URL", "http://zapvoice_app:8000")
    zv_token = config.zapvoice_api_token or os.getenv("ZAPVOICE_API_TOKEN", "")
    client_id = config.zapvoice_client_id

    templates = await get_zapvoice_whatsapp_templates(
        zapvoice_url=zv_url,
        token=zv_token,
        client_id=client_id
    )
    return templates


@router.get("/zapvoice/templates")
async def get_zapvoice_templates_custom(
    zapvoice_url: Optional[str] = None,
    zapvoice_api_token: Optional[str] = None,
    zapvoice_client_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Busca templates do WhatsApp via parâmetros diretos de conexão ZapVoice."""
    from zapvoice_utils import get_zapvoice_whatsapp_templates
    zv_url = zapvoice_url or os.getenv("ZAPVOICE_URL", "http://zapvoice_app:8000")
    zv_token = zapvoice_api_token or os.getenv("ZAPVOICE_API_TOKEN", "")
    client_id = zapvoice_client_id

    if not zv_token:
        q = select(WebhookConfigModel).where(WebhookConfigModel.zapvoice_api_token.isnot(None)).limit(1)
        r = await db.execute(q)
        first_cfg = r.scalar_one_or_none()
        if first_cfg:
            zv_url = zv_url or first_cfg.zapvoice_url
            zv_token = first_cfg.zapvoice_api_token
            client_id = client_id or first_cfg.zapvoice_client_id

    templates = await get_zapvoice_whatsapp_templates(
        zapvoice_url=zv_url,
        token=zv_token,
        client_id=client_id
    )
    return templates
