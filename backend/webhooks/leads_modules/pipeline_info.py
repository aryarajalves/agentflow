import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from core.timezone import get_now_br
from models import WebhookConfigModel
from services.followup_modules import calculate_projected_dispatch_time

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    dt = None
    if isinstance(val, datetime):
        dt = val
    else:
        try:
            clean_str = str(val).replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


@router.get("/{webhook_id}/leads/{lead_id}/followup-pipeline")
async def get_lead_followup_pipeline(webhook_id: int, lead_id: int, db: AsyncSession = Depends(get_db)):
    config = await db.get(WebhookConfigModel, webhook_id)
    if not config:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")

    res = await db.execute(
        text(f"SELECT * FROM {config.leads_table} WHERE id = :lead_id AND webhook_config_id = :wid"),
        {"lead_id": lead_id, "wid": webhook_id}
    )
    row = res.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    lead_dict = dict(zip(res.keys(), row))

    # Suporte a Múltiplos Fluxos de Follow-Up por Produto
    lead_followup_funnel_id = lead_dict.get("active_followup_funnel_id")
    active_funnel_id = "followup_default"
    active_funnel_name = "Padrão / Principal"
    
    funnels = []
    if config.followup_funnels:
        try:
            funnels = json.loads(config.followup_funnels) if isinstance(config.followup_funnels, str) else config.followup_funnels
        except Exception:
            funnels = []

    steps = []
    if funnels and isinstance(funnels, list) and len(funnels) > 0:
        matched_funnel = None
        if lead_followup_funnel_id:
            matched_funnel = next((f for f in funnels if f.get("id") == lead_followup_funnel_id), None)
        if not matched_funnel:
            matched_funnel = next((f for f in funnels if f.get("is_default")), funnels[0])
            
        if matched_funnel:
            active_funnel_id = matched_funnel.get("id", "followup_default")
            active_funnel_name = matched_funnel.get("name", "Padrão / Principal")
            steps = matched_funnel.get("steps", [])
    else:
        steps_raw = config.followup_steps
        if isinstance(steps_raw, str) and steps_raw.strip():
            try:
                steps = json.loads(steps_raw)
            except Exception:
                steps = []
        elif isinstance(steps_raw, list):
            steps = steps_raw

    bh_raw = config.followup_business_hours
    business_hours = None
    if isinstance(bh_raw, str) and bh_raw.strip():
        try:
            business_hours = json.loads(bh_raw)
        except Exception:
            business_hours = None
    elif isinstance(bh_raw, dict):
        business_hours = bh_raw

    tel = lead_dict.get("telefone") or ""
    tel_clean = tel.lstrip("+")
    events_res = await db.execute(
        text("""
            SELECT id, event_type, message_type, mensagem, agent_response, status, created_at, scheduled_at, processing_steps, dono
            FROM webhook_events
            WHERE webhook_config_id = :wid 
              AND (telefone = :t1 OR telefone = :t2 OR telefone = :t3)
              AND (event_type = 'followup' OR message_type = 'followup')
            ORDER BY created_at ASC
        """),
        {"wid": webhook_id, "t1": tel, "t2": f"+{tel_clean}", "t3": tel_clean}
    )
    executed_events = []
    for ev_row in events_res.fetchall():
        ev_dict = dict(zip(events_res.keys(), ev_row))
        executed_events.append(ev_dict)

    lead_labels = []
    lead_labels_raw = lead_dict.get("labels")
    if lead_labels_raw:
        if isinstance(lead_labels_raw, list):
            lead_labels = lead_labels_raw
        elif isinstance(lead_labels_raw, str):
            try:
                parsed = json.loads(lead_labels_raw)
                if isinstance(parsed, list):
                    lead_labels = parsed
                else:
                    lead_labels = [x.strip() for x in lead_labels_raw.split(",") if x.strip()]
            except Exception:
                lead_labels = [x.strip() for x in lead_labels_raw.split(",") if x.strip()]

    lead_labels_lower = [str(lbl).lower().strip() for lbl in lead_labels]

    cancel_labels = []
    if config.ignore_by_label:
        cancel_labels.extend([l.strip() for l in config.ignore_by_label.split(",") if l.strip()])
    if config.followup_cancel_label:
        cancel_labels.extend([l.strip() for l in config.followup_cancel_label.split(",") if l.strip()])
    if not cancel_labels:
        cancel_labels = ["humano"]

    current_step = lead_dict.get("followup_step") if lead_dict.get("followup_step") is not None else 0
    ultima_msg_em = lead_dict.get("ultima_mensagem_em")
    ultima_resp_em = lead_dict.get("ultima_resposta_agente_em")
    created_at_lead = lead_dict.get("created_at")

    matched_cancel_labels = [cl for cl in cancel_labels if cl.lower().strip() in lead_labels_lower]
    has_cancel_label = len(matched_cancel_labels) > 0

    # Verificar se houve registro de desinteresse nos eventos
    has_disinterest_event = False
    try:
        dis_res = await db.execute(
            text("""
                SELECT id FROM webhook_events
                WHERE webhook_config_id = :wid 
                  AND (telefone = :t1 OR telefone = :t2 OR telefone = :t3)
                  AND (processing_steps LIKE '%Desinteresse Declarado%' OR mensagem LIKE '%não tenho interesse%' OR mensagem LIKE '%nao tenho interesse%')
                LIMIT 1
            """),
            {"wid": webhook_id, "t1": tel, "t2": f"+{tel_clean}", "t3": tel_clean}
        )
        has_disinterest_event = dis_res.fetchone() is not None
    except Exception:
        has_disinterest_event = False

    is_buyer = any(lbl in lead_labels_lower for lbl in ["aluno", "compra-aprovada", (config.purchased_label or "").lower() if config.purchased_label else "aluno"])

    cancellation_reason = None
    if has_cancel_label:
        cancellation_reason = f"Contato possui a etiqueta: '{', '.join(matched_cancel_labels)}'"
    elif current_step == -1:
        if not config.followup_enabled:
            cancellation_reason = "Follow-up desativado nas configurações do webhook"
        elif is_buyer:
            cancellation_reason = "O contato comprou o curso / matrícula confirmada"
        elif has_disinterest_event:
            cancellation_reason = "O contato informou que não tem interesse ou não vai comprar"
        else:
            cancellation_reason = "Follow-up finalizado ou cancelado"

    lead_msg_dt = _parse_dt(ultima_msg_em)
    agent_resp_dt = _parse_dt(ultima_resp_em)
    created_dt = _parse_dt(created_at_lead)

    pipeline_steps = []
    for idx, step_cfg in enumerate(steps):
        delay_hours = float(step_cfg.get("delay_hours", 0))
        delay_minutes = int(step_cfg.get("delay_minutes", delay_hours * 60))
        
        step_type = step_cfg.get("type", "ai")
        prompt = step_cfg.get("custom_prompt", "")
        fixed_msg = step_cfg.get("fixed_message", "")
        media_type = step_cfg.get("media_type", "none")
        media_url = step_cfg.get("media_url", "")

        step_status = "pending"
        dispatched_event = None

        if idx < len(executed_events):
            dispatched_event = executed_events[idx]

        is_step_skipped = False
        is_step_manual = False
        if dispatched_event:
            ev_resp = str(dispatched_event.get("agent_response") or "")
            ev_msg = str(dispatched_event.get("mensagem") or "")
            ev_status = str(dispatched_event.get("status") or "")
            ev_steps = str(dispatched_event.get("processing_steps") or "")
            if (
                ev_status == "skipped"
                or "pulado manualmente" in ev_resp.lower()
                or "pulado manualmente" in ev_msg.lower()
                or "pulado manualmente" in ev_steps.lower()
                or '"is_skipped": true' in ev_steps.lower()
            ):
                is_step_skipped = True

            if (
                "disparo manual" in ev_steps.lower()
                or '"is_manual": true' in ev_steps.lower()
                or "disparo acionado manualmente" in ev_steps.lower()
            ):
                is_step_manual = True

        if current_step == -1:
            step_status = "cancelled"
        elif idx < current_step:
            step_status = "skipped" if is_step_skipped else "completed"
        elif idx == current_step:
            if not config.followup_enabled:
                step_status = "disabled"
            elif has_cancel_label:
                step_status = "cancelled"
            else:
                step_status = "active"
        else:
            step_status = "pending"

        started_at = None
        estimated_dispatch_at = None
        reset_by_lead_message = False
        lead_last_message_at = None

        if step_status == "active":
            prev_event_dt = _parse_dt(executed_events[idx - 1].get("created_at")) if idx > 0 and idx - 1 < len(executed_events) else None
            
            base_candidates = [d for d in [lead_msg_dt, agent_resp_dt, created_dt] if d]
            if prev_event_dt:
                base_candidates.append(prev_event_dt)

            if base_candidates:
                started_at_dt = max(base_candidates)
                started_at = started_at_dt.isoformat()

                if lead_msg_dt:
                    if prev_event_dt and lead_msg_dt > prev_event_dt:
                        reset_by_lead_message = True
                        lead_last_message_at = lead_msg_dt.isoformat()
                    elif not prev_event_dt and agent_resp_dt and lead_msg_dt > agent_resp_dt:
                        reset_by_lead_message = True
                        lead_last_message_at = lead_msg_dt.isoformat()

                proj_dt = calculate_projected_dispatch_time(started_at_dt, delay_minutes, business_hours)
                estimated_dispatch_at = proj_dt.isoformat()

        step_cancellation_reason = cancellation_reason if step_status == "cancelled" else None

        pipeline_steps.append({
            "step_index": idx,
            "step_number": idx + 1,
            "delay_minutes": delay_minutes,
            "type": step_type,
            "custom_prompt": prompt,
            "fixed_message": fixed_msg,
            "media_type": media_type,
            "media_url": media_url,
            "target_audience": step_cfg.get("target_audience", "ambos"),
            "template_name": step_cfg.get("template_name", ""),
            "language": step_cfg.get("language", "pt_BR"),
            "template_variables": step_cfg.get("template_variables", {}),
            "template_header_media": step_cfg.get("template_header_media", ""),
            "status": step_status,
            "dispatched_event": dispatched_event,
            "is_manual": is_step_manual,
            "started_at": started_at,
            "estimated_dispatch_at": estimated_dispatch_at,
            "reset_by_lead_message": reset_by_lead_message,
            "lead_last_message_at": lead_last_message_at,
            "cancellation_reason": step_cancellation_reason
        })

    overall_status = "active"
    status_message = "Em andamento na régua de follow-up"

    if not config.followup_enabled:
        overall_status = "disabled"
        status_message = "Follow-up desativado nas configurações do webhook"
    elif has_cancel_label:
        overall_status = "cancelled"
        status_message = f"Cancelado devido à etiqueta de cancelamento ({', '.join(cancel_labels)})"
    elif current_step == -1:
        overall_status = "cancelled"
        if is_buyer:
            overall_status = "completed"
            status_message = "🎉 Compra Confirmada / Aluno Matriculado"
        elif has_disinterest_event:
            status_message = "🚫 Desinteresse Declarado pelo Contato"
        elif has_cancel_label:
            status_message = f"Cancelado pela etiqueta: '{', '.join(matched_cancel_labels)}'"
        else:
            status_message = "Follow-up Cancelado / Finalizado"
    elif not steps:
        overall_status = "no_steps"
        status_message = "Nenhum passo de follow-up configurado"
    elif current_step >= len(steps):
        overall_status = "completed"
        status_message = "Todos os passos da régua foram concluídos"
    else:
        overall_status = "active"
        status_message = f"Aguardando disparo do Passo {current_step + 1}"

    return {
        "lead": {
            "id": lead_dict.get("id"),
            "contato_nome": lead_dict.get("contato_nome") or lead_dict.get("nome"),
            "telefone": lead_dict.get("telefone"),
            "followup_step": current_step,
            "active_followup_funnel_id": lead_followup_funnel_id,
            "ultima_mensagem_em": ultima_msg_em,
            "labels": lead_labels,
            "pode_enviar_mensagem": lead_dict.get("pode_enviar_mensagem", True)
        },
        "active_funnel": {
            "id": active_funnel_id,
            "name": active_funnel_name
        },
        "webhook": {
            "id": config.id,
            "name": config.name,
            "followup_enabled": config.followup_enabled,
            "cancel_labels": cancel_labels,
            "required_label": config.followup_required_label,
            "business_hours": business_hours
        },
        "overall_status": overall_status,
        "status_message": status_message,
        "cancellation_reason": cancellation_reason,
        "steps": pipeline_steps,
        "executed_events": executed_events,
        "server_now": get_now_br()
    }
