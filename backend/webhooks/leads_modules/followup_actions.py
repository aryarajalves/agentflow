import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db, SessionLocal
from models import WebhookConfigModel
from services.followup_modules import (
    dispatch_single_lead_followup,
    save_followup_event
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{webhook_id}/leads/{lead_id}/followup/trigger-now")
async def trigger_lead_followup_now(
    webhook_id: int,
    lead_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Executa imediatamente o disparo do passo atual de follow-up para o contato,
    avançando o lead para a próxima etapa (followup_step = followup_step + 1).
    """
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
    current_step = lead_dict.get("followup_step")
    if current_step is None or current_step < 0:
        raise HTTPException(
            status_code=400,
            detail="O follow-up deste contato está finalizado ou cancelado. Não é possível disparar."
        )

    # Identificar passos do funil ativo
    funnels = []
    if config.followup_funnels:
        try:
            funnels = json.loads(config.followup_funnels) if isinstance(config.followup_funnels, str) else config.followup_funnels
        except Exception:
            funnels = []

    steps = []
    lead_funnel_id = lead_dict.get("active_followup_funnel_id")
    if funnels and isinstance(funnels, list) and len(funnels) > 0:
        matched_funnel = None
        if lead_funnel_id:
            matched_funnel = next((f for f in funnels if f.get("id") == lead_funnel_id), None)
        if not matched_funnel:
            matched_funnel = next((f for f in funnels if f.get("is_default")), funnels[0])
        if matched_funnel:
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

    if not steps or current_step >= len(steps):
        raise HTTPException(
            status_code=400,
            detail=f"Não há passo ativo configurado para o índice {current_step + 1}."
        )

    target_step = steps[current_step]
    delay_hours = float(target_step.get("delay_hours", 0))
    delay_minutes = int(target_step.get("delay_minutes", delay_hours * 60))

    cw_url = (config.zapvoice_url or config.chatwoot_url or "").rstrip("/")
    cw_token = config.zapvoice_api_token or config.chatwoot_api_token or ""

    # Disparar imediatamente sem jitter
    sent_success = await dispatch_single_lead_followup(
        session_factory=SessionLocal,
        config_id=config.id,
        leads_table=config.leads_table,
        cw_url=cw_url,
        cw_token=cw_token,
        agent_id=config.agent_id,
        zv_client_cfg=config.zapvoice_client_id,
        followup_add_label=config.followup_add_label,
        step_raw=target_step,
        step_index=current_step,
        delay_minutes=delay_minutes,
        elapsed_minutes=float(delay_minutes + 1),  # Força inatividade atingida
        lead_info=lead_dict,
        apply_jitter=False,
        is_manual=True
    )

    if not sent_success:
        raise HTTPException(
            status_code=502,
            detail="Falha ao disparar follow-up via integração externa (verifique se a conversa está aberta no ZapVoice)."
        )

    return {
        "success": True,
        "message": f"Passo {current_step + 1} disparado com sucesso!",
        "next_step": current_step + 1
    }


@router.post("/{webhook_id}/leads/{lead_id}/followup/skip-step")
async def skip_lead_followup_step(
    webhook_id: int,
    lead_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Pula o passo atual de follow-up do contato sem enviar mensagem,
    avançando o lead para a próxima etapa (followup_step = followup_step + 1)
    e reiniciando a contagem de tempo.
    """
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
    current_step = lead_dict.get("followup_step")
    if current_step is None or current_step < 0:
        raise HTTPException(
            status_code=400,
            detail="O follow-up deste contato está finalizado ou cancelado. Não há passo para pular."
        )

    next_step = current_step + 1
    now_utc = datetime.utcnow()

    # Atualiza o passo no banco e reinicia a contagem
    await db.execute(
        text(f"""
            UPDATE {config.leads_table}
            SET followup_step = :next_step,
                ultima_resposta_agente_em = :now
            WHERE id = :id
        """),
        {"next_step": next_step, "now": now_utc, "id": lead_id}
    )

    # Registra o evento manual no histórico do lead
    telefone = lead_dict.get("telefone") or ""
    nome = lead_dict.get("contato_nome") or lead_dict.get("nome") or ""
    conversa_id = str(lead_dict.get("conversa_id") or "")
    conta_id = str(lead_dict.get("conta_id") or config.zapvoice_client_id or "1")

    pipeline_steps = [{
        "step": f"⏭️ Passo {current_step + 1} Pulado Manualmente",
        "detail": f"O operador pulou o Passo {current_step + 1}. Contato avançado para o Passo {next_step + 1}.",
        "timestamp": now_utc.isoformat(),
        "is_skipped": True
    }]

    # Registra o evento de skip diretamente na tabela webhook_events com status 'skipped'
    try:
        await db.execute(
            text("""
                INSERT INTO webhook_events (
                    webhook_config_id, conta_id, conversa_id, telefone, contato_nome,
                    mensagem, agent_response, dono, status, event_type, message_type,
                    processing_steps, created_at
                ) VALUES (
                    :wid, :conta, :conv, :tel, :nome,
                    :msg, :resp, 'Agente', 'skipped', 'followup', 'text',
                    :steps, :created_at
                )
            """),
            {
                "wid": config.id,
                "conta": str(conta_id),
                "conv": str(conversa_id),
                "tel": telefone,
                "nome": nome or telefone,
                "msg": f"🔄 [Follow-Up Passo #{current_step + 1}]",
                "resp": f"[Passo {current_step + 1} pulado manualmente]",
                "steps": json.dumps(pipeline_steps, ensure_ascii=False),
                "created_at": now_utc
            }
        )
    except Exception as e:
        logger.error(f"[FollowUp] Erro ao registrar evento de passo pulado: {e}")

    await db.commit()

    return {
        "success": True,
        "message": f"Passo {current_step + 1} pulado com sucesso! Contato avançado para o Passo {next_step + 1}.",
        "previous_step": current_step,
        "next_step": next_step
    }
