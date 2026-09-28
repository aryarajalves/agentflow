import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models import WebhookConfigModel, WebhookEventModel
from datetime import datetime
import uuid

@pytest.mark.asyncio
async def test_skipped_events_excluded_from_history_and_events(client: AsyncClient, db_session: AsyncSession):
    """
    Garante que eventos de follow-up pulados (status='skipped') NÃO apareçam
    no histórico de conversas do contato nem na listagem geral de eventos,
    para não sujar o histórico de mensagens trocadas.
    """
    from webhooks.service import ensure_leads_table
    table_name = "leads_test_skipped_filter"
    await ensure_leads_table(table_name)

    token = f"skip-filter-{uuid.uuid4().hex[:8]}"
    webhook = WebhookConfigModel(
        name="Test Webhook Skipped Filter",
        token=token,
        leads_table=table_name
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)

    telefone = "5585999990001"

    # Evento 1: Mensagem normal e resposta (deve aparecer)
    ev_normal = WebhookEventModel(
        webhook_config_id=webhook.id,
        telefone=telefone,
        contato_nome="Contato Teste",
        mensagem="Olá, tenho interesse!",
        agent_response="Olá! Que ótimo, como posso ajudar?",
        dono="Agente",
        status="completed",
        event_type="message",
        created_at=datetime.utcnow()
    )

    # Evento 2: Follow-up pulado manualmente (NÃO deve aparecer no histórico do contato)
    ev_skipped = WebhookEventModel(
        webhook_config_id=webhook.id,
        telefone=telefone,
        contato_nome="Contato Teste",
        mensagem="🔄 [Follow-Up Passo #2]",
        agent_response="[Passo 2 pulado manualmente]",
        dono="Agente",
        status="skipped",
        event_type="followup",
        created_at=datetime.utcnow()
    )

    db_session.add_all([ev_normal, ev_skipped])
    await db_session.commit()

    # 1. Validação em /webhooks/{wid}/events (list_webhook_events padrão)
    resp_events = await client.get(f"/webhooks/{webhook.id}/events")
    assert resp_events.status_code == 200
    data_events = resp_events.json()
    # Deve conter apenas a mensagem normal, nunca o evento skipped
    assert data_events["total"] == 1
    assert data_events["items"][0]["status"] != "skipped"
    assert data_events["items"][0]["id"] == ev_normal.id

    # 2. Validação com busca por telefone e event_type=all (como é feito no LeadHistoryModal)
    resp_history_search = await client.get(
        f"/webhooks/{webhook.id}/events?search={telefone}&event_type=all"
    )
    assert resp_history_search.status_code == 200
    data_search = resp_history_search.json()
    assert data_search["total"] == 1
    assert len(data_search["items"]) == 1
    assert data_search["items"][0]["id"] == ev_normal.id
    assert not any(item["status"] == "skipped" for item in data_search["items"])

    # 3. Validação no endpoint dedicado de histórico: /webhooks/{wid}/leads-by-phone/{phone}/history
    resp_lead_history = await client.get(
        f"/webhooks/{webhook.id}/leads-by-phone/{telefone}/history?page=1&page_size=20"
    )
    assert resp_lead_history.status_code == 200
    data_lead_hist = resp_lead_history.json()
    # O evento skipped tem mensagem e resposta, se não fosse filtrado daria total 4
    # Como o ev_normal tem 1 pergunta e 1 resposta, total deve ser 2
    assert data_lead_hist["total"] == 2
    for item in data_lead_hist["items"]:
        assert "pulado manualmente" not in item["conteudo"].lower()
        assert "passo #2" not in item["conteudo"].lower()
