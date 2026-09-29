import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent_core.logic.unanswered_micro_responder import (
    generate_unanswered_micro_response,
    _build_fallback_response
)
from agent_core.models.usage import UsageLog
from agent_core.logic.tool_executor import execute_tool_calls


@pytest.mark.asyncio
async def test_generate_unanswered_micro_response_success():
    """Valida se o micro-prompt ultraleve chama o gpt-4o-mini com os parâmetros corretos
    e retorna o conteúdo humanizado e os tokens gastos.
    """
    mock_config = MagicMock()
    mock_config.name = "Vinicius"
    mock_config.unanswered_question_prompt = "Explique com simpatia que vai verificar com a equipe."

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="Entendi sua dúvida sobre a carga horária! Já encaminhei para a equipe e te trago a resposta certinha. ✨"))
    ]
    mock_completion.usage = MagicMock(prompt_tokens=150, completion_tokens=45)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("agent_core.logic.unanswered_micro_responder.get_openai_client", return_value=mock_client):
        content, usage = await generate_unanswered_micro_response(
            user_message="quantas horas de curso temos no 7Ps?",
            unanswered_question="Qual é a carga horária total do 7Ps?",
            agent_config=mock_config,
            tool_output="Dúvida registrada com sucesso.",
            rag_context=None
        )

        assert "Entendi sua dúvida sobre a carga horária" in content
        assert usage["prompt_tokens"] == 150
        assert usage["completion_tokens"] == 45

        # Verifica se chamou gpt-4o-mini
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert len(call_kwargs["messages"]) == 2
        sys_msg = call_kwargs["messages"][0]["content"]
        assert "Vinicius" in sys_msg
        assert "Qual é a carga horária total do 7Ps?" in sys_msg
        assert "Explique com simpatia" in sys_msg


@pytest.mark.asyncio
async def test_generate_unanswered_micro_response_with_rag_context():
    """Valida se o micro-prompt inclui o contexto do RAG quando há mais de uma pergunta
    na mensagem e uma delas possui resposta na base.
    """
    mock_config = MagicMock()
    mock_config.name = "Vinicius"
    mock_config.unanswered_question_prompt = None

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="O curso é 100% online! E sobre a carga horária, vou checar com a equipe. ✨"))
    ]
    mock_completion.usage = MagicMock(prompt_tokens=220, completion_tokens=50)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("agent_core.logic.unanswered_micro_responder.get_openai_client", return_value=mock_client):
        content, usage = await generate_unanswered_micro_response(
            user_message="O curso é online? E quantas horas tem?",
            unanswered_question="Quantas horas de curso tem?",
            agent_config=mock_config,
            tool_output="Dúvida registrada.",
            rag_context="[Trecho 1]: O curso 7Ps é 100% online e gravado."
        )

        assert "100% online" in content
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        sys_msg = call_kwargs["messages"][0]["content"]
        assert "O curso 7Ps é 100% online e gravado." in sys_msg
        assert "INFORMAÇÕES ADICIONAIS CONFIRMADAS NA BASE" in sys_msg


@pytest.mark.asyncio
async def test_generate_unanswered_micro_response_handoff():
    """Valida se o micro-prompt inclui o aviso de transbordo quando a ferramenta transfere para humano."""
    mock_config = MagicMock()
    mock_config.name = "Vinicius"
    mock_config.unanswered_question_prompt = None

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="Registrei sua dúvida e transferi para nossa equipe humana que já vai te atender!"))
    ]
    mock_completion.usage = MagicMock(prompt_tokens=180, completion_tokens=30)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("agent_core.logic.unanswered_micro_responder.get_openai_client", return_value=mock_client):
        content, usage = await generate_unanswered_micro_response(
            user_message="qual é o endereço físico?",
            unanswered_question="qual é o endereço físico?",
            agent_config=mock_config,
            tool_output="ATENÇÃO: O limite de 2 dúvida(s) sem resposta foi atingido. AUTOMATICAMENTE TRANSFERIDO PARA O SUPORTE HUMANO.",
            rag_context=None
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        sys_msg = call_kwargs["messages"][0]["content"]
        assert "TRANSBORDO HUMANO" in sys_msg


@pytest.mark.asyncio
async def test_generate_unanswered_micro_response_fallback_on_error():
    """Valida se o fallback gracioso é acionado em caso de erro da API OpenAI sem quebrar a execução."""
    mock_config = MagicMock()
    mock_config.name = "Vinicius"
    mock_config.unanswered_question_prompt = "Mensagem configurada no painel."

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("Timeout na OpenAI"))

    with patch("agent_core.logic.unanswered_micro_responder.get_openai_client", return_value=mock_client):
        content, usage = await generate_unanswered_micro_response(
            user_message="dúvida teste",
            unanswered_question="dúvida teste",
            agent_config=mock_config,
            tool_output="Dúvida registrada.",
            rag_context=None
        )

        assert content == "Mensagem configurada no painel."
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0


@pytest.mark.asyncio
async def test_execute_tool_calls_triggers_terminal_micro_responder():
    """Valida se execute_tool_calls aciona o micro-responder, encerra como terminal (sem Turno 2 pesado)
    e acumula os tokens leves no total_usage.
    """
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_unanswered_1"
    mock_tool_call.function.name = "registrar_duvida_sem_resposta"
    mock_tool_call.function.arguments = '{"pergunta": "Qual é a carga horária do 7Ps?"}'

    mock_response_msg = MagicMock()
    mock_response_msg.tool_calls = [mock_tool_call]

    mock_config = MagicMock()
    mock_config.id = 1
    mock_config.name = "Vinicius"
    mock_config.unanswered_question_prompt = None

    total_usage = UsageLog(mp=0, mc=0, xp=20000, xc=30)
    context_vars = {"raw_user_message": "Quantas horas tem o curso?"}

    mock_micro_resp = "Entendi! Vou checar a carga horária com a equipe e te retorno certinho. ✨"
    mock_micro_usage = {"prompt_tokens": 120, "completion_tokens": 40}

    with patch("agent_core.tools.handlers.internal.handle_unanswered_question", new_callable=AsyncMock) as mock_unanswered, \
         patch("agent_core.logic.unanswered_micro_responder.generate_unanswered_micro_response", new_callable=AsyncMock) as mock_micro:
        
        mock_unanswered.return_value = "Dúvida registrada para nossa equipe."
        mock_micro.return_value = (mock_micro_resp, mock_micro_usage)

        is_term, handoff_d, last_resp, _ = await execute_tool_calls(
            response_message=mock_response_msg,
            openai_tools=[],
            messages=[{"role": "user", "content": "Quantas horas tem o curso?"}],
            tool_calls_log=[],
            tool_call_counts={},
            tool_failure_counts={},
            tools=[],
            config=mock_config,
            db=MagicMock(),
            context_variables=context_vars,
            history=[],
            total_usage=total_usage
        )

        # Deve ser terminal (evitando Turno 2 com modelo principal de 20.000 tokens)
        assert is_term is True
        assert last_resp == mock_micro_resp

        # Tokens leves do micro-prompt foram somados no mini_prompt e mini_completion
        assert total_usage.mini_prompt == 120
        assert total_usage.mini_completion == 40
        assert total_usage.main_prompt == 20000
