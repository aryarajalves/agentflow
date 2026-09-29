import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models import KnowledgeBaseModel, KnowledgeItemModel, UnansweredQuestionModel, AgentConfigModel

@pytest.mark.asyncio
async def test_answer_question_as_variation_success(client: AsyncClient, db_session: AsyncSession):
    # 1. Cria agente
    agent = AgentConfigModel(name="Agente Teste", is_active=True)
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    # 2. Cria base e item existente
    kb = KnowledgeBaseModel(name="Base Teste Variação", description="Base para teste de variação")
    db_session.add(kb)
    await db_session.commit()
    await db_session.refresh(kb)

    item = KnowledgeItemModel(
        knowledge_base_id=kb.id,
        question="Qual é a formação do professor?",
        answer="Ele é formado em Astrologia e Filosofia.",
        category="Institucional",
        question_variations=[]
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    # 3. Cria dúvida no Inbox vinculada ao agente
    uq = UnansweredQuestionModel(
        agent_id=agent.id,
        question="Qual a graduação do professor?",
        status="PENDENTE"
    )
    db_session.add(uq)
    await db_session.commit()
    await db_session.refresh(uq)

    # 4. Chama o endpoint para responder como variação
    response = await client.post(
        f"/unanswered-questions/{uq.id}/answer-as-variation",
        json={
            "knowledge_item_id": item.id,
            "variation": "Qual a graduação do professor?"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Qual a graduação do professor?" in data["question_variations"]

    # 5. Verifica no banco se o item foi atualizado e a dúvida foi para RESPONDIDA
    await db_session.refresh(item)
    assert "Qual a graduação do professor?" in item.question_variations

    await db_session.refresh(uq)
    assert uq.status == "RESPONDIDA"


@pytest.mark.asyncio
async def test_answer_question_as_variation_limit_exceeded(client: AsyncClient, db_session: AsyncSession):
    # Cria agente
    agent = AgentConfigModel(name="Agente Teste 2", is_active=True)
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    # Cria item já com 8 variações (limite máximo)
    kb = KnowledgeBaseModel(name="Base Limite Variação")
    db_session.add(kb)
    await db_session.commit()
    await db_session.refresh(kb)

    item = KnowledgeItemModel(
        knowledge_base_id=kb.id,
        question="Pergunta Base",
        answer="Resposta Base",
        question_variations=[f"Variação {i}" for i in range(1, 9)]
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    uq = UnansweredQuestionModel(
        agent_id=agent.id,
        question="Nova dúvida que estoura limite",
        status="PENDENTE"
    )
    db_session.add(uq)
    await db_session.commit()
    await db_session.refresh(uq)

    # Deve retornar erro 400 avisando sobre o limite de 8 variações
    response = await client.post(
        f"/unanswered-questions/{uq.id}/answer-as-variation",
        json={
            "knowledge_item_id": item.id,
            "variation": "Nova dúvida que estoura limite"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "8 variações" in data["detail"]


@pytest.mark.asyncio
async def test_answer_question_as_variation_not_found(client: AsyncClient, db_session: AsyncSession):
    # Dúvida inexistente
    response = await client.post(
        "/unanswered-questions/999999/answer-as-variation",
        json={"knowledge_item_id": 1, "variation": "Teste"}
    )
    assert response.status_code == 404

    # Item inexistente
    agent = AgentConfigModel(name="Agente Teste 3", is_active=True)
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    uq = UnansweredQuestionModel(
        agent_id=agent.id,
        question="Pergunta de teste",
        status="PENDENTE"
    )
    db_session.add(uq)
    await db_session.commit()
    await db_session.refresh(uq)

    response2 = await client.post(
        f"/unanswered-questions/{uq.id}/answer-as-variation",
        json={"knowledge_item_id": 999999, "variation": "Teste"}
    )
    assert response2.status_code == 404
