import pytest
import json
from sqlalchemy.ext.asyncio import AsyncSession
from agent_core.tools.handlers.internal import handle_unanswered_question
from agent_core.logic.strict_rules_prompt import get_strict_rules_prompt
from models import AgentConfigModel

@pytest.mark.asyncio
async def test_unanswered_question_handler_restricts_to_current_message(db_session: AsyncSession):
    """Valida se o retorno da ferramenta registrar_duvida_sem_resposta proíbe explicitamente
    re-responder perguntas anteriores do histórico ou citar dúvidas passadas.
    """
    agent = AgentConfigModel(
        name="Agente Teste Escopo Dúvidas",
        is_active=True,
        unanswered_question_prompt="Direcionei sua pergunta para a equipe.",
        unanswered_handoff_limit=5
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    context_vars = {
        "contact_phone": "5511988887777",
        "contact_name": "Lead Teste",
        "session_id": "session_scope_123"
    }
    history = [
        {"role": "user", "content": "Quem é o professor do curso?"},
        {"role": "assistant", "content": "O professor é o Crassus Gobbi."},
        {"role": "user", "content": "Tem certificado?"},
        {"role": "assistant", "content": "Vou verificar sobre o certificado com a equipe."},
        {"role": "user", "content": "qual é a carga horaria do curso?"}
    ]

    args = json.dumps({"pergunta": "qual é a carga horaria do curso?"})
    result = await handle_unanswered_question(db_session, context_vars, args, history, agent.id)

    # Validações da instrução de retorno da ferramenta
    assert "ATENÇÃO CRÍTICA DE ESCOPO" in result
    assert "É TERMINANTEMENTE PROIBIDO re-responder perguntas que o usuário fez em turnos anteriores do histórico" in result
    assert "é ESTRITAMENTE PROIBIDO citar ou recapitular dúvidas passadas" in result
    assert "Se e somente se o usuário fez mais de uma pergunta na MESMA mensagem atual" in result


def test_strict_rules_prompt_forbids_historical_repetition_and_past_doubt_accumulation():
    """Valida se o strict_rules_prompt bloqueia o modelo de regurgitar apresentações passadas
    ou ficar acumulando/citando dúvidas de turnos anteriores.
    """
    prompt = get_strict_rules_prompt()
    assert "Escopo Exclusivo da Mensagem Atual" in prompt
    assert "É TERMINANTEMENTE PROIBIDO re-responder perguntas de mensagens/turnos anteriores do histórico" in prompt
    assert "é ESTRITAMENTE PROIBIDO ficar citando, recapitulando ou acumulando dúvidas passadas" in prompt
    assert "É PROIBIDO despejar apresentações genéricas, biografias ou conteúdos institucionais não solicitados" in prompt
