import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models import WebhookConfigModel, WebhookEventModel
from datetime import datetime
import uuid


@pytest.mark.asyncio
async def test_followup_template_resolves_real_text(db_session: AsyncSession):
    """
    Testa se o despachante de follow-up extrai o texto real do template
    (substituindo variáveis) em vez de gravar apenas '[Template Oficial]: nome'.
    """
    from services.followup_modules.dispatcher import dispatch_single_lead_followup

    step_cfg = {
        "type": "whatsapp_template",
        "template_name": "pix_gerado",
        "language": "pt_BR",
        "template_components": [
            {
                "type": "BODY",
                "text": "Olá {{1}}, seu PIX para o curso está disponível!"
            }
        ],
        "template_variables": {
            "body_1": "{primeiro_nome}"
        }
    }

    lead_info = {
        "id": 1,
        "conta_id": "1",
        "conversa_id": "100",
        "telefone": "5511999998888",
        "contato_nome": "Aryaraj Fernandes",
        "active_followup_funnel_id": None
    }

    mock_db = MagicMock()

    with patch("services.followup_modules.dispatcher.send_zapvoice_whatsapp_template", new=AsyncMock(return_value=(True, {"ok": True}))):
        with patch("services.followup_modules.dispatcher.save_followup_event") as mock_save:
            success = await dispatch_single_lead_followup(
                session_factory=lambda: mock_db,
                config_id=1,
                leads_table="leads",
                cw_url="http://mock-zapvoice",
                cw_token="fake_token",
                agent_id=1,
                zv_client_cfg="1",
                followup_add_label=None,
                step_raw=step_cfg,
                step_index=0,
                delay_minutes=60,
                elapsed_minutes=65.0,
                lead_info=lead_info,
                apply_jitter=False,
                is_manual=True
            )

            assert success is True
            assert mock_save.called
            call_args = mock_save.call_args[0]
            # Argumentos: (db, config_id, eff_conta_id, eff_conversa_id, telefone, nome, message, pipeline_steps, "processed", ...)
            message_saved = call_args[6]
            # O texto salvo deve ser a mensagem resolvida com o nome real, NÃO '[Template Oficial]: pix_gerado'
            assert "Olá Aryaraj, seu PIX para o curso está disponível!" in message_saved
            assert "[Template Oficial]" not in message_saved


@pytest.mark.asyncio
async def test_deduplication_of_zapvoice_echo_and_memory(client: AsyncClient, db_session: AsyncSession):
    """
    Testa se o receptor de webhooks ignora ecos de saída e memória quando um disparo
    de follow-up com o mesmo texto já acabou de ser registrado para aquele telefone.
    """
    from webhooks.service import ensure_leads_table
    table_name = "leads_test_echo_dedup"
    await ensure_leads_table(table_name)

    token = f"echo-tok-{uuid.uuid4().hex[:8]}"
    mem_token = f"mem-tok-{uuid.uuid4().hex[:8]}"
    webhook = WebhookConfigModel(
        name="Test Echo Dedup",
        token=token,
        memory_token=mem_token,
        memory_sync_enabled=True,
        leads_table=table_name
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)

    telefone = "5585998259497"
    template_msg = "Oi! É a Sofia, da Escola Sexologia Sem Tabu. Passando para ajudar com seu curso."

    # 1. Simula o evento de Follow-up registrado pelo dispatcher
    ev_followup = WebhookEventModel(
        webhook_config_id=webhook.id,
        telefone=telefone,
        contato_nome="Aryaraj Fernandes",
        mensagem="🔄 [Follow-Up Passo #3]",
        agent_response=template_msg,
        dono="Agente",
        status="processed",
        event_type="followup",
        message_type="template",
        created_at=datetime.utcnow()
    )
    db_session.add(ev_followup)
    await db_session.commit()

    # 2. Simula chegada do webhook de memória do ZapVoice com o mesmo texto
    memory_payload = {
        "event_type": "memory",
        "phone": telefone,
        "name": "Aryaraj Fernandes",
        "dono": "agente",
        "template_content": template_msg
    }
    resp_mem = await client.post(f"/webhooks/memory/{mem_token}", json=memory_payload)
    assert resp_mem.status_code == 200
    assert resp_mem.json().get("status") == "duplicate_agent_memory_ignored"

    # 3. Simula chegada do webhook de saída (outgoing echo) do ZapVoice com o mesmo texto
    echo_payload = {
        "event": "message_created",
        "message_type": "template",
        "message": {
            "content": template_msg,
            "message_type": "outgoing",
            "template_name": "pix_gerado"
        },
        "conversation": {
            "id": 1234,
            "channel": "Channel::Whatsapp"
        },
        "contact": {
            "phone_number": f"+{telefone}",
            "name": "Aryaraj Fernandes"
        }
    }
    resp_echo = await client.post(f"/webhooks/receive/{token}", json=echo_payload)
    assert resp_echo.status_code == 200

    # 4. Na listagem de eventos (/webhooks/{wid}/events), deve existir APENAS 1 evento (o de FOLLOW-UP)
    resp_list = await client.get(f"/webhooks/{webhook.id}/events?search={telefone}&event_type=all")
    assert resp_list.status_code == 200
    items = resp_list.json()["items"]
    assert len(items) == 1
    assert items[0]["event_type"] == "followup"
    assert items[0]["agent_response"] == template_msg
    assert items[0]["mensagem"] == "🔄 [Follow-Up Passo #3]"
