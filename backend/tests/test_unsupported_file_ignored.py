import pytest
import uuid
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from webhooks.import_chat_modules.helpers import is_system_or_badge_message
from agent_core.logic.pre_router.shortcuts_modules.matcher import check_programmatic_shortcuts
from models import AgentConfigModel, WebhookConfigModel, WebhookEventModel


def test_helpers_is_system_or_badge_unsupported():
    """Valida que mensagens de arquivos não suportados são detectadas como badges/sistema."""
    # Variação com emoji de clipe (padrão Chatwoot/WhatsApp)
    assert is_system_or_badge_message({"content": "📎 Arquivo (unsupported) recebido"}) is True

    # Variação sem emoji
    assert is_system_or_badge_message({"content": "Arquivo (unsupported) recebido"}) is True

    # Variação apenas com a tag (unsupported)
    assert is_system_or_badge_message({"content": "(unsupported)"}) is True

    # Variação com colchetes
    assert is_system_or_badge_message({"content": "Arquivo [unsupported] recebido"}) is True

    # message_type explícito unsupported
    assert is_system_or_badge_message({"message_type": "unsupported", "content": "Mídia"}) is True

    # Mensagens de usuários normais NUNCA devem ser confundidas com unsupported
    assert is_system_or_badge_message({"content": "Olá, tudo bem? Gostaria de saber sobre o curso"}) is False
    assert is_system_or_badge_message({"content": "Como funciona a garantia?"}) is False


def test_shortcuts_matcher_unsupported():
    """Valida que o atalho do Pre-Router intercepta arquivos não suportados determinísticamente sem gastar LLM."""
    agent_mock = MagicMock(spec=AgentConfigModel)
    agent_mock.id = 1
    agent_mock.initial_message = "Olá! Como posso ajudar?"

    raw_msg = "📎 Arquivo (unsupported) recebido"
    res = check_programmatic_shortcuts(
        raw_user_message=raw_msg,
        history=[],
        main_agent=agent_mock,
        is_first_msg=True,
        is_ad=False,
        similarity_info="",
        cleaned_message=raw_msg,
        message=raw_msg
    )

    assert res is not None
    assert res["eh_mensagem_automatica"] is True
    assert res["resposta_direta"] is None
    assert res["_model_used"] == "shortcut-logic"
    assert res["tipo_mensagem"] == "Arquivo Não Suportado (Ignorado)"
    assert res["precisa_rag"] is False


@patch("webhook_tasks.SessionLocal")
def test_automation_task_discards_unsupported_message(mock_session_local):
    """Valida que process_webhook_automation descarta defensivamente mensagens com (unsupported) sem chamar o LLM."""
    from webhook_tasks.automation import process_webhook_automation

    db_mock = MagicMock()
    mock_session_local.return_value = db_mock

    event = MagicMock(spec=WebhookEventModel)
    event.id = 777
    event.status = "pending"
    event.mensagem = "📎 Arquivo (unsupported) recebido"
    event.message_type = "text"
    event.webhook_config_id = 1
    event.is_automatic = False
    event.processing_steps = "[]"

    config = MagicMock(spec=WebhookConfigModel)
    config.id = 1
    config.agent_id = 10

    def db_query_side_effect(model):
        q = MagicMock()
        if model == WebhookEventModel:
            q.filter.return_value.first.return_value = event
        elif model == WebhookConfigModel:
            q.filter.return_value.first.return_value = config
        return q

    db_mock.query.side_effect = db_query_side_effect

    with patch("webhook_tasks._add_step") as mock_add_step, \
         patch("webhook_tasks.automation.execute_agent_pipeline") as mock_execute_pipeline:
        process_webhook_automation.run(event_id=777)

        # O evento deve ter sido marcado como ignorado
        assert event.status == "ignored"
        assert event.is_automatic is True
        # Step de arquivo não suportado adicionado
        step_names = [call.args[2] for call in mock_add_step.call_args_list]
        assert "🚫 Arquivo não suportado ignorado" in step_names
        # O pipeline do agente de IA NUNCA foi chamado
        mock_execute_pipeline.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_receiver_discards_unsupported_file(client: AsyncClient, db_session: AsyncSession):
    """Valida que a rota /webhooks/receive/{token} descarta imediatamente o payload com status system_badge_ignored."""
    wh_token = f"token-unsupported-{uuid.uuid4().hex[:8]}"
    wh = WebhookConfigModel(
        name="Teste Webhook Unsupported",
        token=wh_token,
        is_active=True,
        zapvoice_client_id="99"
    )
    db_session.add(wh)
    await db_session.commit()

    payload = {
        "event": "message_created",
        "client_id": "99",
        "contact": {
            "phone": "+5511999998888",
            "name": "Cliente Teste"
        },
        "message": {
            "content": "📎 Arquivo (unsupported) recebido",
            "message_type": "text",
            "sender_type": "contact"
        }
    }

    resp = await client.post(f"/webhooks/receive/{wh_token}", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("status") == "system_badge_ignored"


@pytest.mark.asyncio
async def test_memory_webhook_discards_unsupported_file(client: AsyncClient, db_session: AsyncSession):
    """Valida que a rota de webhook de memória /webhooks/memory/{token} também descarta unsupported files."""
    mem_token = f"mem-unsupported-{uuid.uuid4().hex[:8]}"
    wh = WebhookConfigModel(
        name="Teste Webhook Memory Unsupported",
        token=f"wh-base-{uuid.uuid4().hex[:8]}",
        memory_token=mem_token,
        memory_sync_enabled=True,
        is_active=True,
        memory_phone_path="telefone"
    )
    db_session.add(wh)
    await db_session.commit()

    payload = {
        "telefone": "+5511999998888",
        "mensagem": "📎 Arquivo (unsupported) recebido",
        "dono": "cliente"
    }

    resp = await client.post(f"/webhooks/memory/{mem_token}", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("status") == "system_badge_ignored"
