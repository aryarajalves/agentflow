import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from agent_core.tools.handlers.internal import handle_unanswered_question
from api.routers.inbox import answer_question, discard_question, bulk_discard_questions

@pytest.mark.asyncio
async def test_handle_unanswered_question_broadcast():
    """Testa se handle_unanswered_question emite o evento WebSocket unanswered_question_created"""
    mock_db = AsyncMock()
    mock_agent_row = MagicMock(unanswered_handoff_limit=2, unanswered_question_prompt=None)
    mock_db.execute.return_value = MagicMock(
        first=MagicMock(return_value=mock_agent_row),
        scalar=MagicMock(return_value=0)
    )
    
    with patch("core.websocket.manager.broadcast", new_callable=AsyncMock) as mock_broadcast:
        context_vars = {
            "session_id": "sess_123",
            "contact_phone": "5511999999999"
        }
        func_args_str = json.dumps({"pergunta": "Como funciona o reembolso?"})
        history = [{"role": "user", "content": "Como funciona o reembolso?"}]
        agent_id = 1
        
        result = await handle_unanswered_question(
            db=mock_db,
            context_variables=context_vars,
            func_args_str=func_args_str,
            history=history,
            agent_id=agent_id
        )
        assert "Dúvida registrada" in result
        
        # Valida que o broadcast foi disparado com o payload correto
        mock_broadcast.assert_awaited_once()
        call_args = mock_broadcast.await_args[0][0]
        assert call_args["type"] == "unanswered_question_created"
        assert call_args["action"] == "create"
        assert call_args["agent_id"] == 1
        assert call_args["question"] == "Como funciona o reembolso?"
        assert call_args["session_id"] == "5511999999999"

@pytest.mark.asyncio
async def test_inbox_answer_question_broadcast():
    """Testa se answer_question emite evento WebSocket unanswered_question_updated"""
    mock_db = AsyncMock()
    mock_q = MagicMock()
    mock_q.id = 456
    mock_q.question = "Pergunta teste"
    mock_q.status = "PENDENTE"
    mock_db.get.return_value = mock_q
    mock_db.execute.return_value = MagicMock(scalar=MagicMock(return_value=None))
    
    payload = {
        "answer": "O prazo é de 7 dias úteis.",
        "knowledge_base_id": 1
    }
    
    with patch("core.websocket.manager.broadcast", new_callable=AsyncMock) as mock_broadcast, \
         patch("api.routers.inbox.get_embedding", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = ([0.1, 0.2], 10)
        response = await answer_question(question_id=456, payload=payload, db=mock_db, _=None)
        assert response["success"] is True
        
        mock_broadcast.assert_awaited_once()
        call_args = mock_broadcast.await_args[0][0]
        assert call_args["type"] == "unanswered_question_updated"
        assert call_args["question_id"] == 456
        assert call_args["action"] == "answer"
        assert call_args["status"] == "RESPONDIDA"

@pytest.mark.asyncio
async def test_inbox_discard_question_broadcast():
    """Testa se discard_question emite evento WebSocket unanswered_question_updated"""
    mock_db = AsyncMock()
    mock_q = MagicMock()
    mock_q.id = 789
    mock_q.status = "PENDENTE"
    mock_db.get.return_value = mock_q
    
    with patch("core.websocket.manager.broadcast", new_callable=AsyncMock) as mock_broadcast:
        response = await discard_question(question_id=789, db=mock_db, _=None)
        assert response["success"] is True
        
        mock_broadcast.assert_awaited_once()
        call_args = mock_broadcast.await_args[0][0]
        assert call_args["type"] == "unanswered_question_updated"
        assert call_args["question_id"] == 789
        assert call_args["action"] == "discard"
        assert call_args["status"] == "DESCARTADA"

@pytest.mark.asyncio
async def test_inbox_bulk_discard_broadcast():
    """Testa se bulk_discard_questions emite evento WebSocket unanswered_question_bulk_discarded"""
    mock_db = AsyncMock()
    payload = {"ids": [101, 102]}
    
    with patch("core.websocket.manager.broadcast", new_callable=AsyncMock) as mock_broadcast:
        response = await bulk_discard_questions(payload=payload, db=mock_db, _=None)
        assert response["success"] is True
        
        mock_broadcast.assert_awaited_once()
        call_args = mock_broadcast.await_args[0][0]
        assert call_args["type"] == "unanswered_question_bulk_discarded"
        assert call_args["question_ids"] == [101, 102]
        assert call_args["action"] == "bulk_discard"
