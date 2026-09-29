import pytest
from unittest.mock import AsyncMock, MagicMock
from api.routers.inbox import list_unanswered_questions

@pytest.mark.asyncio
async def test_list_unanswered_questions_filters():
    """Testa a aplicação dos novos filtros de busca na listagem de dúvidas sem resposta."""
    mock_db = AsyncMock()
    
    # Mock do retorno do count e dos itens
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1
    
    mock_item = MagicMock()
    mock_item.id = 1
    mock_item.agent_id = 5
    mock_item.session_id = "5511999999999"
    mock_item.question = "Qual é a carga horária do curso?"
    mock_item.context = "Sessão: 5511999999999\nHistórico:\nuser: Qual a carga horária?"
    mock_item.status = "PENDENTE"
    mock_item.source = "zapvoice"
    mock_item.created_at = None
    mock_item.updated_at = None

    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = [mock_item]

    mock_empty_rows = MagicMock()
    mock_empty_rows.all.return_value = []
    mock_empty_rows.scalar.return_value = None

    async def fake_execute(stmt):
        stmt_str = str(stmt).lower()
        if "count" in stmt_str:
            return mock_count_result
        if "unanswered_questions" in stmt_str:
            return mock_items_result
        return mock_empty_rows

    mock_db.execute.side_effect = fake_execute
    mock_agent = MagicMock()
    mock_agent.name = "Agente Vendas 7Ps"
    mock_db.get.return_value = mock_agent

    response = await list_unanswered_questions(
        status="PENDENTE",
        agent_id=5,
        phone="5511999999999",
        date_start="2026-09-01",
        date_end="2026-09-30",
        source="zapvoice",
        limit=20,
        offset=0,
        db=mock_db,
        _=None
    )

    assert response["success"] is True
    assert response["total"] == 1
    assert len(response["items"]) == 1
    item = response["items"][0]
    assert item["id"] == 1
    assert item["agent_id"] == 5
    assert item["session_id"] == "5511999999999"
    assert item["source"] == "zapvoice"
    assert item["agent_name"] == "Agente Vendas 7Ps"

@pytest.mark.asyncio
async def test_list_unanswered_questions_source_chat_filter():
    """Testa o filtro por fonte 'chat'."""
    mock_db = AsyncMock()
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 0
    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [mock_count_result, mock_items_result]

    response = await list_unanswered_questions(
        status="PENDENTE",
        source="chat",
        limit=10,
        offset=0,
        db=mock_db,
        _=None
    )

    assert response["success"] is True
    assert response["total"] == 0
    assert response["items"] == []
