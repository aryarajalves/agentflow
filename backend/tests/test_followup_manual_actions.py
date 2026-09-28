import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from webhooks.leads_modules.followup_actions import (
    trigger_lead_followup_now,
    skip_lead_followup_step
)

@pytest.mark.asyncio
async def test_skip_lead_followup_step_success():
    """Valida avanço do passo de follow-up sem disparo de mensagem e gravação de evento de histórico."""
    mock_db = AsyncMock()
    mock_config = MagicMock()
    mock_config.id = 113
    mock_config.leads_table = "leads"
    mock_config.zapvoice_client_id = "11"

    mock_db.get.return_value = mock_config

    mock_result = MagicMock()
    mock_result.keys.return_value = ["id", "followup_step", "telefone", "contato_nome", "conversa_id", "conta_id"]
    mock_result.fetchone.return_value = (10, 0, "5585999999999", "Aryaraj", "1234", "11")
    mock_db.execute.return_value = mock_result

    res = await skip_lead_followup_step(webhook_id=113, lead_id=10, db=mock_db)

    assert res["success"] is True
    assert res["previous_step"] == 0
    assert res["next_step"] == 1
    assert "pulado com sucesso" in res["message"]

    # Valida que o UPDATE (lead) e o INSERT (webhook_events) foram executados
    assert mock_db.execute.call_count >= 2
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_skip_lead_followup_step_cancelled_lead():
    """Valida que lead com follow-up cancelado/finalizado (-1) não pode ter passo pulado."""
    mock_db = AsyncMock()
    mock_config = MagicMock()
    mock_config.id = 113
    mock_config.leads_table = "leads"
    mock_db.get.return_value = mock_config

    mock_result = MagicMock()
    mock_result.keys.return_value = ["id", "followup_step", "telefone"]
    mock_result.fetchone.return_value = (10, -1, "5585999999999")
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await skip_lead_followup_step(webhook_id=113, lead_id=10, db=mock_db)

    assert exc_info.value.status_code == 400
    assert "finalizado ou cancelado" in exc_info.value.detail


@pytest.mark.asyncio
async def test_trigger_lead_followup_now_success():
    """Valida disparo forçado imediato do passo ativo chamando dispatch_single_lead_followup."""
    mock_db = AsyncMock()
    mock_config = MagicMock()
    mock_config.id = 113
    mock_config.leads_table = "leads"
    mock_config.agent_id = 1
    mock_config.zapvoice_url = "https://api.teste.com"
    mock_config.zapvoice_api_token = "token123"
    mock_config.zapvoice_client_id = "11"
    mock_config.followup_add_label = "contatado"
    mock_config.followup_funnels = None
    mock_config.followup_steps = json.dumps([
        {"delay_minutes": 60, "type": "fixed", "fixed_message": "Olá, tudo bem?"}
    ])

    mock_db.get.return_value = mock_config

    mock_result = MagicMock()
    mock_result.keys.return_value = ["id", "followup_step", "telefone", "contato_nome", "active_followup_funnel_id"]
    mock_result.fetchone.return_value = (10, 0, "5585999999999", "Aryaraj", None)
    mock_db.execute.return_value = mock_result

    with patch("webhooks.leads_modules.followup_actions.dispatch_single_lead_followup", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = True

        res = await trigger_lead_followup_now(webhook_id=113, lead_id=10, db=mock_db)

        assert res["success"] is True
        assert res["next_step"] == 1
        assert "disparado com sucesso" in res["message"]
        mock_dispatch.assert_awaited_once()


@pytest.mark.asyncio
async def test_trigger_lead_followup_now_fails_external():
    """Valida que falha de envio externo no disparo manual retorna HTTP 502 com mensagem amigável."""
    mock_db = AsyncMock()
    mock_config = MagicMock()
    mock_config.id = 113
    mock_config.leads_table = "leads"
    mock_config.agent_id = 1
    mock_config.zapvoice_url = "https://api.teste.com"
    mock_config.zapvoice_api_token = "token123"
    mock_config.zapvoice_client_id = "11"
    mock_config.followup_add_label = None
    mock_config.followup_funnels = None
    mock_config.followup_steps = json.dumps([
        {"delay_minutes": 60, "type": "fixed", "fixed_message": "Olá!"}
    ])

    mock_db.get.return_value = mock_config

    mock_result = MagicMock()
    mock_result.keys.return_value = ["id", "followup_step", "telefone", "contato_nome", "active_followup_funnel_id"]
    mock_result.fetchone.return_value = (10, 0, "5585999999999", "Aryaraj", None)
    mock_db.execute.return_value = mock_result

    with patch("webhooks.leads_modules.followup_actions.dispatch_single_lead_followup", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await trigger_lead_followup_now(webhook_id=113, lead_id=10, db=mock_db)

        assert exc_info.value.status_code == 502
        assert "Falha ao disparar follow-up" in exc_info.value.detail
