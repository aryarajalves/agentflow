import pytest
import json
from datetime import datetime, timedelta, timezone
from services.followup_modules import calculate_projected_dispatch_time

def test_calculate_projected_dispatch_time_no_business_hours():
    """Valida projeção de disparo sem janela comercial (24h contínuo)."""
    now = datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc)
    # 60 minutos de espera
    proj = calculate_projected_dispatch_time(now, 60, None)
    expected = now + timedelta(minutes=60)
    assert proj == expected

def test_calculate_projected_dispatch_time_with_business_hours():
    """Valida projeção de 1 dia (24h) disparando no dia seguinte no mesmo horário dentro do expediente."""
    bh = {
        "enabled": True,
        "start": "08:00",
        "end": "20:00",
        "weekdays": True,
        "saturday": True,
        "sunday": True
    }
    # Quarta-feira às 09:31 BRT (12:31 UTC). Delay de 1 dia (1440 min = 24h).
    start_utc = datetime(2026, 9, 23, 12, 31, 0, tzinfo=timezone.utc)
    proj_utc = calculate_projected_dispatch_time(start_utc, 1440, bh)

    # Quinta-feira 24/09 às 09:31 BRT (12:31 UTC).
    expected_utc = datetime(2026, 9, 24, 12, 31, 0, tzinfo=timezone.utc)
    assert proj_utc == expected_utc

def test_calculate_projected_dispatch_time_overnight_pause():
    """Valida que disparo previsto para madrugada é postergado para abertura comercial (08:00)."""
    bh = {
        "enabled": True,
        "start": "08:00",
        "end": "20:00",
        "weekdays": True,
        "saturday": True,
        "sunday": True
    }
    # Quarta-feira às 21:00 BRT (00:00 UTC do dia seguinte). Delay de 4 horas (240 min = 01:00 BRT de madrugada).
    start_utc = datetime(2026, 9, 24, 0, 0, 0, tzinfo=timezone.utc)
    proj_utc = calculate_projected_dispatch_time(start_utc, 240, bh)

    # Quinta-feira às 08:00 BRT (11:00 UTC).
    expected_utc = datetime(2026, 9, 24, 11, 0, 0, tzinfo=timezone.utc)
    assert proj_utc == expected_utc

@pytest.mark.asyncio
async def test_pipeline_info_includes_schedule_and_reset_flag():
    """Valida se o endpoint get_lead_followup_pipeline calcula started_at, estimated_dispatch_at e reset_by_lead_message."""
    from webhooks.leads_modules.pipeline_info import get_lead_followup_pipeline
    from unittest.mock import AsyncMock, MagicMock

    mock_db = AsyncMock()
    mock_config = MagicMock()
    mock_config.id = 1
    mock_config.name = "Config Teste"
    mock_config.leads_table = "leads"
    mock_config.followup_enabled = True
    mock_config.ignore_by_label = None
    mock_config.followup_cancel_label = "compra-aprovada"
    mock_config.followup_required_label = None
    mock_config.followup_business_hours = '{"enabled": false}'
    mock_config.followup_steps = '[{"delay_minutes": 60, "type": "ai"}]'
    mock_config.followup_funnels = None

    mock_db.get.return_value = mock_config

    lead_row = {
        "id": 10,
        "contato_nome": "Lead Teste",
        "telefone": "5511999999999",
        "followup_step": 0,
        "active_followup_funnel_id": None,
        "ultima_mensagem_em": "2026-09-23T10:00:00Z",
        "ultima_resposta_agente_em": "2026-09-23T09:30:00Z",
        "created_at": "2026-09-23T09:00:00Z",
        "labels": '["whatsapp"]',
        "pode_enviar_mensagem": True
    }

    mock_lead_res = MagicMock()
    mock_lead_res.fetchone.return_value = list(lead_row.values())
    mock_lead_res.keys.return_value = list(lead_row.keys())

    mock_events_res = MagicMock()
    mock_events_res.fetchall.return_value = []
    mock_events_res.keys.return_value = ["id", "event_type", "message_type", "mensagem", "agent_response", "status", "created_at", "scheduled_at", "processing_steps", "dono"]

    mock_db.execute.side_effect = [mock_lead_res, mock_events_res]

    res = await get_lead_followup_pipeline(webhook_id=1, lead_id=10, db=mock_db)

    assert res["overall_status"] == "active"
    assert len(res["steps"]) == 1
    step_0 = res["steps"][0]
    assert step_0["status"] == "active"
    assert step_0["started_at"] is not None
    assert step_0["estimated_dispatch_at"] is not None
    # Como ultima_mensagem_em (10:00) > ultima_resposta_agente_em (09:30), reset_by_lead_message deve ser True
    assert step_0["reset_by_lead_message"] is True


@pytest.mark.asyncio
async def test_pipeline_info_skipped_step():
    """Valida se passos anteriores pulados manualmente retornam com status 'skipped' (Dispensado)."""
    from webhooks.leads_modules.pipeline_info import get_lead_followup_pipeline
    from unittest.mock import AsyncMock, MagicMock

    mock_db = AsyncMock()
    mock_config = MagicMock()
    mock_config.id = 1
    mock_config.name = "Config Teste"
    mock_config.leads_table = "leads"
    mock_config.followup_enabled = True
    mock_config.ignore_by_label = None
    mock_config.followup_cancel_label = None
    mock_config.followup_required_label = None
    mock_config.followup_business_hours = '{"enabled": false}'
    mock_config.followup_steps = json.dumps([
        {"delay_minutes": 60, "type": "ai"},
        {"delay_minutes": 120, "type": "fixed", "fixed_message": "Passo 2"}
    ])
    mock_config.followup_funnels = None

    mock_db.get.return_value = mock_config

    lead_row = {
        "id": 10,
        "contato_nome": "Lead Teste",
        "telefone": "5511999999999",
        "followup_step": 1,  # Passo 0 foi pulado, passo 1 está ativo
        "active_followup_funnel_id": None,
        "ultima_mensagem_em": "2026-09-23T10:00:00Z",
        "ultima_resposta_agente_em": "2026-09-23T09:30:00Z",
        "created_at": "2026-09-23T09:00:00Z",
        "labels": '["whatsapp"]',
        "pode_enviar_mensagem": True
    }

    mock_lead_res = MagicMock()
    mock_lead_res.fetchone.return_value = list(lead_row.values())
    mock_lead_res.keys.return_value = list(lead_row.keys())

    # Evento de skip registrado para o passo 0
    event_row = {
        "id": 100,
        "event_type": "followup",
        "message_type": "text",
        "mensagem": "🔄 [Follow-Up Passo #1]",
        "agent_response": "[Passo 1 pulado manualmente]",
        "status": "skipped",
        "created_at": "2026-09-23T09:30:00Z",
        "scheduled_at": None,
        "processing_steps": '[{"step": "⏭️ Passo 1 Pulado Manualmente", "is_skipped": true}]',
        "dono": "Agente"
    }

    mock_events_res = MagicMock()
    mock_events_res.fetchall.return_value = [list(event_row.values())]
    mock_events_res.keys.return_value = list(event_row.keys())

    mock_db.execute.side_effect = [mock_lead_res, mock_events_res]

    res = await get_lead_followup_pipeline(webhook_id=1, lead_id=10, db=mock_db)

    assert len(res["steps"]) == 2
    step_0 = res["steps"][0]
    step_1 = res["steps"][1]

    # O passo 0 deve estar marcado como "skipped" (Dispensado), e NÃO "completed" (Disparado)
    assert step_0["status"] == "skipped"
    assert step_1["status"] == "active"


@pytest.mark.asyncio
async def test_pipeline_info_manual_dispatch():
    """Valida se passos disparados manualmente retornam com is_manual=True na pipeline."""
    from webhooks.leads_modules.pipeline_info import get_lead_followup_pipeline
    from unittest.mock import AsyncMock, MagicMock

    mock_db = AsyncMock()
    mock_config = MagicMock()
    mock_config.id = 1
    mock_config.name = "Config Teste"
    mock_config.leads_table = "leads"
    mock_config.followup_enabled = True
    mock_config.ignore_by_label = None
    mock_config.followup_cancel_label = None
    mock_config.followup_required_label = None
    mock_config.followup_business_hours = '{"enabled": false}'
    mock_config.followup_steps = json.dumps([
        {"delay_minutes": 60, "type": "ai"},
        {"delay_minutes": 120, "type": "fixed", "fixed_message": "Passo 2"}
    ])
    mock_config.followup_funnels = None

    mock_db.get.return_value = mock_config

    lead_row = {
        "id": 10,
        "contato_nome": "Lead Teste",
        "telefone": "5511999999999",
        "followup_step": 1,
        "active_followup_funnel_id": None,
        "ultima_mensagem_em": "2026-09-23T10:00:00Z",
        "ultima_resposta_agente_em": "2026-09-23T09:30:00Z",
        "created_at": "2026-09-23T09:00:00Z",
        "labels": '["whatsapp"]',
        "pode_enviar_mensagem": True
    }

    mock_lead_res = MagicMock()
    mock_lead_res.fetchone.return_value = list(lead_row.values())
    mock_lead_res.keys.return_value = list(lead_row.keys())

    # Evento de disparo manual registrado para o passo 0
    event_row = {
        "id": 101,
        "event_type": "followup",
        "message_type": "text",
        "mensagem": "🔄 [Follow-Up Passo #1]",
        "agent_response": "Olá! Segue sua resposta.",
        "status": "processed",
        "created_at": "2026-09-23T09:30:00Z",
        "scheduled_at": None,
        "processing_steps": '[{"step": "⚡ Disparo Manual: Follow-Up 1", "is_manual": true}]',
        "dono": "Agente"
    }

    mock_events_res = MagicMock()
    mock_events_res.fetchall.return_value = [list(event_row.values())]
    mock_events_res.keys.return_value = list(event_row.keys())

    mock_db.execute.side_effect = [mock_lead_res, mock_events_res]

    res = await get_lead_followup_pipeline(webhook_id=1, lead_id=10, db=mock_db)

    assert len(res["steps"]) == 2
    step_0 = res["steps"][0]
    assert step_0["status"] == "completed"
    assert step_0["is_manual"] is True


