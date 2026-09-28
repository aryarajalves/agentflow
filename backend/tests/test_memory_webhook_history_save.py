import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import WebhookConfigModel, WebhookEventModel, UserMemoryModel
from webhook_services_modules.context import retrieve_context_history
from agent_core.memory import fetch_user_memory
import uuid


@pytest.mark.asyncio
async def test_memory_webhook_saves_agent_template_to_history(client: AsyncClient, db_session: AsyncSession):
    """Valida que mensagens de template e saídas enviadas via webhook de memória são salvas em webhook_events com status completed."""
    token = f"mem-token-{uuid.uuid4().hex[:8]}"
    slug = f"slug-{uuid.uuid4().hex[:8]}"
    webhook = WebhookConfigModel(
        name="Webhook Memória Teste",
        token=slug,
        memory_token=token,
        memory_sync_enabled=True,
        leads_table="leads_test_mem_hist"
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)

    phone = "5511999998888"
    template_msg = "Você estava a um passo de dominar o que 99% dos homens nunca vão saber... e parou?"

    payload = {
        "phone": phone,
        "name": "Aryaraj Fernandes",
        "dono": "agente",
        "template_content": template_msg
    }

    res = await client.post(f"/webhooks/memory/{token}", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "event_id" in data
    assert data["status"] == "agent_memory_saved_to_history"

    # Verifica se o evento foi criado na tabela webhook_events com status completed
    event_stmt = await db_session.execute(
        select(WebhookEventModel).where(WebhookEventModel.id == data["event_id"])
    )
    event = event_stmt.scalar_one_or_none()
    assert event is not None
    assert event.telefone == phone
    assert event.dono == "agente"
    assert event.message_type == "template"
    assert event.status == "completed"
    assert "Modo Silencioso" in event.agent_response
    assert template_msg in event.mensagem


@pytest.mark.asyncio
async def test_memory_webhook_with_document_content_saves_media_memory_and_injects_into_agent_history(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Valida que quando o webhook de memória recebe um template contendo mídia/documento (document_content, filename, media_url),
    o conteúdo integral do documento é salvo na mensagem do evento, na memória estruturada (UserMemoryModel)
    e injetado no histórico de contexto da IA (retrieve_context_history).
    """
    token = f"mem-doc-{uuid.uuid4().hex[:8]}"
    slug = f"slug-doc-{uuid.uuid4().hex[:8]}"
    webhook = WebhookConfigModel(
        name="Webhook Memória Com Documento",
        token=slug,
        memory_token=token,
        memory_sync_enabled=True,
        leads_table="leads_test_mem_doc"
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)

    phone = "5555519934480"
    doc_text = (
        "✨ LEITURA PERSONALIZADA DA BÚSSOLA ✨\n\n"
        "Nome: Paloma Manfio\n"
        "Perfil: Guardiã do Portal\n\n"
        "Texto completo e integral extraído diretamente do documento anexado..."
    )
    media_url = "https://seu-dominio.com/api/media/proxy/bussola_paloma_manfio.pdf"
    filename = "✨ Leitura da Bússola - Paloma Manfio.pdf"

    payload = {
        "contact_phone": phone,
        "contact_name": "Paloma Manfio",
        "phone": phone,
        "name": "Paloma Manfio",
        "contact_id": 888,
        "template_name": "mensagem_bussola_porta_aberta_oficial",
        "template_content": "Olá Paloma! Sua leitura da bússola está pronta em anexo.",
        "Dono": "agente",
        "is_button_click": False,
        "timestamp": "2026-09-26T17:25:00.000000+00:00",
        "client_id": 1,
        "conta_id": 1,
        "account_id": 1,
        "chatwoot_account_id": 1,
        "platform": "outra",
        "account": {"id": 1, "conta_id": 1},
        "conta": {"id": 1},
        "trigger_id": 778,
        "node_id": None,
        "document_content": doc_text,
        "media_url": media_url,
        "filename": filename
    }

    res = await client.post(f"/webhooks/memory/{token}", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["status"] == "agent_memory_saved_to_history"

    # 1. Verificar evento em webhook_events
    event_stmt = await db_session.execute(
        select(WebhookEventModel).where(WebhookEventModel.id == data["event_id"])
    )
    event = event_stmt.scalar_one_or_none()
    assert event is not None
    assert event.telefone == phone
    assert event.dono == "agente"
    assert event.message_type == "template"
    assert event.status == "completed"
    assert event.link == media_url
    assert "Olá Paloma! Sua leitura da bússola está pronta em anexo." in event.mensagem
    assert filename in event.mensagem
    assert "Perfil: Guardiã do Portal" in event.mensagem

    # 2. Verificar persistência em UserMemoryModel (memória de longo prazo do agente)
    mem_text = await fetch_user_memory(db_session, f"tel_{phone}")
    assert "Perfil: Guardiã do Portal" in mem_text
    assert filename in mem_text

    # 3. Verificar injeção em retrieve_context_history (memória de conversa da IA)
    class MockDbAgent:
        context_window = 10

    user_reply_event = WebhookEventModel(
        id=999998,
        webhook_config_id=webhook.id,
        telefone=phone,
        mensagem="O que significa ser Guardiã do Portal?",
        dono="usuario",
        status="waiting"
    )

    class SyncSessionWrapper:
        def __init__(self, async_s):
            self.s = async_s
        def commit(self):
            pass
        def query(self, model):
            class QueryObj:
                def __init__(self, m):
                    self.m = m
                def filter(self, *conds):
                    return self
                def order_by(self, *args):
                    return self
                def limit(self, n):
                    return self
                def all(self):
                    if self.m == WebhookEventModel:
                        return [event]
                    return []
                def first(self):
                    if self.m == WebhookConfigModel:
                        return webhook
                    if self.m == WebhookEventModel:
                        return user_reply_event
                    return None
            return QueryObj(model)

    history = retrieve_context_history(
        db=SyncSessionWrapper(db_session),
        event=user_reply_event,
        db_agent=MockDbAgent(),
        raw_phone=phone,
        clean_phone=phone,
        event_id=user_reply_event.id
    )

    assert len(history) == 1
    assert history[0]["role"] == "assistant"
    assert "Modo Silencioso" not in history[0]["content"]
    assert "Olá Paloma! Sua leitura da bússola está pronta em anexo." in history[0]["content"]
    assert "Perfil: Guardiã do Portal" in history[0]["content"]
    assert filename in history[0]["content"]


@pytest.mark.asyncio
async def test_memory_webhook_enriches_existing_echo_event_with_document_content(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Valida que se um eco de saída chegou primeiro sem document_content e logo em seguida chega
    o webhook de memória com document_content, o evento existente é enriquecido com o conteúdo da mídia.
    """
    token = f"mem-enrich-{uuid.uuid4().hex[:8]}"
    slug = f"slug-enrich-{uuid.uuid4().hex[:8]}"
    webhook = WebhookConfigModel(
        name="Webhook Enriquecimento Mídia",
        token=slug,
        memory_token=token,
        memory_sync_enabled=True,
        is_active=True,
        leads_table="leads_test_mem_enrich"
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)

    phone = "5555519934499"
    base_tpl = "Olá Paloma! Sua leitura da bússola está pronta em anexo."

    # 1. Primeiro chega sem document_content
    res1 = await client.post(f"/webhooks/memory/{token}", json={
        "phone": phone,
        "name": "Paloma Manfio",
        "Dono": "agente",
        "template_content": base_tpl
    })
    assert res1.status_code == 200
    evt_id = res1.json()["event_id"]

    # 2. Em seguida chega com document_content
    res2 = await client.post(f"/webhooks/memory/{token}", json={
        "phone": phone,
        "name": "Paloma Manfio",
        "Dono": "agente",
        "template_content": base_tpl,
        "document_content": "Conteúdo detalhado do PDF da Bússola: Guardiã do Portal",
        "filename": "Bussola.pdf",
        "media_url": "https://exemplo.com/bussola.pdf"
    })
    assert res2.status_code == 200
    assert res2.json()["event_id"] == evt_id

    event_stmt = await db_session.execute(
        select(WebhookEventModel).where(WebhookEventModel.id == evt_id)
    )
    event = event_stmt.scalar_one_or_none()
    assert event is not None
    assert "Conteúdo detalhado do PDF da Bússola: Guardiã do Portal" in event.mensagem
    assert event.link == "https://exemplo.com/bussola.pdf"


@pytest.mark.asyncio
async def test_memory_webhook_extracts_pdf_from_media_url_when_document_content_missing(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch
):
    """
    Valida que quando o webhook de memória envia apenas media_url e filename (sem document_content no JSON),
    o backend baixa automaticamente o arquivo PDF da media_url, extrai o texto integral e o salva no histórico e memória.
    """
    import requests
    import pypdf

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/pdf"}
        content = b"%PDF-1.4 fake pdf bytes"

    class FakePage:
        def extract_text(self):
            return "Leitura - Bússola Astrológica\nA PORTA ABERTA AGORA\nSol atravessando a sua casa 12"

    class FakePdfReader:
        def __init__(self, stream):
            self.pages = [FakePage()]

    monkeypatch.setattr(requests, "get", lambda url, timeout=10: FakeResponse())
    monkeypatch.setattr(pypdf, "PdfReader", FakePdfReader)

    token = f"mem-pdfurl-{uuid.uuid4().hex[:8]}"
    slug = f"slug-pdfurl-{uuid.uuid4().hex[:8]}"
    webhook = WebhookConfigModel(
        name="Webhook Extração Automática PDF",
        token=slug,
        memory_token=token,
        memory_sync_enabled=True,
        is_active=True,
        leads_table="leads_test_mem_pdfurl"
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)

    phone = "5585998259497"
    media_url = "https://api.aryaraj.shop/api/media/proxy/fbbc1768-41e6-4430-8d27-59784e0af15d.pdf"
    filename = "fbbc1768-41e6-4430-8d27-59784e0af15d.pdf"

    payload = {
        "contact_phone": phone,
        "contact_name": phone,
        "phone": phone,
        "name": phone,
        "contact_id": 155569,
        "template_name": "mensagem_bussola_porta_aberta_oficial",
        "template_content": "No documento acima tem a mensagem que você recebeu da porta que está aberta, chegou a ler a mensagem?",
        "Dono": "agente",
        "is_button_click": False,
        "media_url": media_url,
        "filename": filename
    }

    res = await client.post(f"/webhooks/memory/{token}", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True

    event_stmt = await db_session.execute(
        select(WebhookEventModel).where(WebhookEventModel.id == data["event_id"])
    )
    event = event_stmt.scalar_one_or_none()
    assert event is not None
    assert "No documento acima tem a mensagem que você recebeu da porta que está aberta" in event.mensagem
    assert "A PORTA ABERTA AGORA" in event.mensagem
    assert "Sol atravessando a sua casa 12" in event.mensagem

    mem_text = await fetch_user_memory(db_session, f"tel_{phone}")
    assert "A PORTA ABERTA AGORA" in mem_text


