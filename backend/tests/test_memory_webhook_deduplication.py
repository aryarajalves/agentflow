import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import WebhookConfigModel, WebhookEventModel
from webhooks.service import ensure_leads_table
from webhooks.utils import texts_match_flexible, get_phone_suffix


def test_texts_match_flexible():
    text_a = "Olá, Adriana! Tudo bem?\n\nQuis apenas checar se você conseguiu baixar o documento que te enviei mais cedo."
    text_b = "Olá, Adriana! Tudo bem?\r\nQuis apenas checar se você conseguiu baixar o documento que te enviei mais cedo."
    assert texts_match_flexible(text_a, text_b) is True

    text_with_media = f"{text_a}\n\n📄 [Conteúdo da Mídia/Documento Enviado (doc.pdf)]:\nTexto extraído..."
    assert texts_match_flexible(text_a, text_with_media) is True
    assert texts_match_flexible(text_with_media, text_a) is True

    diff_text = "Outra mensagem totalmente diferente."
    assert texts_match_flexible(text_a, diff_text) is False


def test_phone_suffix_matching():
    phone_with_nine = "5585998259497"
    phone_without_nine = "558598259497"
    phone_clean = "8598259497"

    assert get_phone_suffix(phone_with_nine, 8) == "98259497"
    assert get_phone_suffix(phone_without_nine, 8) == "98259497"
    assert get_phone_suffix(phone_clean, 8) == "98259497"


@pytest.mark.asyncio
async def test_memory_webhook_deduplicates_consecutive_calls(client: AsyncClient, db_session: AsyncSession):
    """
    Testa se duas requisições consecutivas para o webhook de memória
    com o mesmo template e telefone são deduplicadas (evitando o bug dos 7 segundos).
    """
    token = f"mem-dup-{uuid.uuid4().hex[:8]}"
    slug = f"slug-dup-{uuid.uuid4().hex[:8]}"
    leads_tbl = f"leads_{uuid.uuid4().hex[:8]}"
    await ensure_leads_table(leads_tbl)

    webhook = WebhookConfigModel(
        name="Webhook Teste Deduplicação",
        token=slug,
        memory_token=token,
        memory_sync_enabled=True,
        is_active=True,
        leads_table=leads_tbl
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)

    phone = "5585998259497"
    template_msg = "Olá, Adriana! Tudo bem?\n\nQuis apenas checar se você conseguiu baixar o documento."

    payload = {
        "phone": phone,
        "name": "Adriana Salum",
        "dono": "agente",
        "template_name": "aviso_documento",
        "template_content": template_msg
    }

    # 1. Primeiro disparo
    res1 = await client.post(f"/webhooks/memory/{token}", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["ok"] is True
    assert data1["status"] == "agent_memory_saved_to_history"
    event_id_1 = data1["event_id"]

    # 2. Segundo disparo (simula retry ou segundo webhook 7s depois)
    res2 = await client.post(f"/webhooks/memory/{token}", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["ok"] is True
    assert data2["status"] == "duplicate_agent_memory_ignored"
    assert data2["event_id"] == event_id_1

    # 3. Garante que só 1 registro foi criado no banco
    stmt = select(WebhookEventModel).where(
        WebhookEventModel.webhook_config_id == webhook.id,
        WebhookEventModel.telefone == phone
    )
    res_evts = await db_session.execute(stmt)
    evts = res_evts.scalars().all()
    assert len(evts) == 1
    assert evts[0].id == event_id_1


@pytest.mark.asyncio
async def test_cross_deduplication_between_zapvoice_and_memory(client: AsyncClient, db_session: AsyncSession):
    """
    Testa a deduplicação cruzada entre o eco do ZapVoice (/webhooks/receive)
    e o webhook de memória (/webhooks/memory), mesmo com variação no nono dígito do telefone.
    """
    token = f"cross-dup-{uuid.uuid4().hex[:8]}"
    leads_tbl = f"leads_{uuid.uuid4().hex[:8]}"
    await ensure_leads_table(leads_tbl)

    webhook = WebhookConfigModel(
        name="Webhook Teste Cruzado",
        token=token,
        memory_token=token,
        memory_sync_enabled=True,
        is_active=True,
        leads_table=leads_tbl,
        zapvoice_client_id="99"
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)

    phone_zapvoice = "5585998259497"  # com o 9
    phone_memory = "558598259497"     # sem o 9 (variável de CRM/automação)
    template_msg = "Olá! Gostaria de confirmar seu agendamento para hoje."

    # 1. Chega eco de saída do ZapVoice
    zap_payload = {
        "event": "message_created",
        "client_id": "99",
        "contact": {
            "phone": phone_zapvoice,
            "name": "Cliente Teste"
        },
        "message": {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "sender_type": "system",
            "message_type": "template",
            "template_name": "confirmacao_agendamento",
            "template_content": template_msg
        }
    }
    resp1 = await client.post(f"/webhooks/receive/{token}", json=zap_payload)
    assert resp1.status_code == 200
    assert resp1.json()["ok"] is True

    # 2. 7 segundos depois chega o webhook de memória enviado pelo funil
    mem_payload = {
        "phone": phone_memory,
        "name": "Cliente Teste",
        "dono": "agente",
        "template_name": "confirmacao_agendamento",
        "template_content": template_msg
    }
    resp2 = await client.post(f"/webhooks/memory/{token}", json=mem_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["ok"] is True
    # O webhook de memória deve detectar o evento recente do ZapVoice e ignorar duplicidade
    assert data2["status"] == "duplicate_agent_memory_ignored"

    # 3. Garante que só existe 1 evento registrado para este contato
    all_evts_stmt = select(WebhookEventModel).where(
        WebhookEventModel.webhook_config_id == webhook.id
    )
    all_evts = (await db_session.execute(all_evts_stmt)).scalars().all()
    assert len(all_evts) == 1
