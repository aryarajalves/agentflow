import sys
import logging
from ..clients import get_openai_client

logger = logging.getLogger(__name__)


from unittest.mock import Mock, MagicMock, AsyncMock

def _get_client_fn():
    """Detecta se get_openai_client foi mockado localmente ou no agent_core.core."""
    if isinstance(get_openai_client, (Mock, MagicMock, AsyncMock)) or hasattr(get_openai_client, "return_value"):
        return get_openai_client
    core_mod = sys.modules.get("agent_core.core")
    if core_mod and hasattr(core_mod, "get_openai_client"):
        c_fn = getattr(core_mod, "get_openai_client")
        if isinstance(c_fn, (Mock, MagicMock, AsyncMock)) or hasattr(c_fn, "return_value"):
            return c_fn
    return get_openai_client


def _build_fallback_response(agent_config, unanswered_question: str, is_handoff: bool) -> str:
    agent_name = getattr(agent_config, "name", "Assistente") or "Assistente"
    guideline = getattr(agent_config, "unanswered_question_prompt", None)
    
    if is_handoff:
        return "Entendi perfeitamente. Registrei sua dúvida e transferi seu atendimento para nossa equipe especializada para que você receba o suporte adequado. Um momento, por favor! ✨"
    
    if guideline and guideline.strip():
        return guideline.strip()
        
    return (
        f"Entendi perfeitamente sua dúvida sobre '{unanswered_question}'! "
        "Já registrei aqui para nossa equipe especializada verificar os detalhes exatos e te retorno com tudo certinho! ✨"
    )


async def generate_unanswered_micro_response(
    user_message: str,
    unanswered_question: str,
    agent_config,
    tool_output: str = "",
    rag_context: str = None,
    on_step: callable = None
) -> tuple[str, dict]:
    """
    Gera uma resposta humanizada rápida e de baixíssimo custo (Opção B - Micro-Prompt Ultraleve)
    quando a ferramenta 'registrar_duvida_sem_resposta' é acionada.
    
    Elimina o segundo turno pesado (~20.000 tokens) no modelo principal,
    utilizando gpt-4o-mini com prompt enxuto (~100-250 tokens).
    """
    is_handoff = "AUTOMATICAMENTE TRANSFERIDO PARA O SUPORTE HUMANO" in str(tool_output)
    agent_name = getattr(agent_config, "name", "Assistente") or "Assistente"
    custom_guideline = getattr(agent_config, "unanswered_question_prompt", "") or ""
    
    if not custom_guideline.strip():
        custom_guideline = (
            "Explique de forma gentil e acolhedora que você registrou a dúvida e que a equipe especializada "
            "vai verificar a informação para dar um retorno completo."
        )

    # Construção do Micro-Prompt Ultraleve
    handoff_instruction = (
        "\nAVISO DE TRANSBORDO HUMANO: O limite de dúvidas sem resposta foi atingido nesta conversa e o atendimento "
        "foi transferido para um atendente humano. Informe de maneira acolhedora que a dúvida foi registrada e que "
        "um especialista humano da equipe já vai assumir o atendimento para ajudar.\n"
        if is_handoff else ""
    )

    rag_instruction = ""
    if rag_context and rag_context.strip():
        rag_excerpt = rag_context.strip()[:1000]
        rag_instruction = (
            f"\nINFORMAÇÕES ADICIONAIS CONFIRMADAS NA BASE (utilize se o usuário fez outra pergunta na mesma mensagem):\n"
            f"{rag_excerpt}\n"
        )

    system_prompt = (
        f"Você é o assistente virtual '{agent_name}'.\n"
        "Seu tom de voz é prestativo, acolhedor, empático e natural (estilo WhatsApp, com emojis moderados).\n\n"
        f"SITUAÇÃO DO ATENDIMENTO:\n"
        "O usuário enviou uma mensagem com uma dúvida cuja resposta exata não está disponível na base de conhecimento.\n"
        f"A dúvida registrada internamente para a equipe foi: \"{unanswered_question}\".\n"
        f"{handoff_instruction}"
        f"{rag_instruction}\n"
        f"DIRETRIZ DE RESPOSTA AO CLIENTE:\n"
        f"\"{custom_guideline.strip()}\"\n\n"
        "REGRAS RÍGIDAS:\n"
        "1. Responda em 1ª pessoa no WhatsApp com simpatia e acolhimento direto ao cliente.\n"
        f"2. Explique com naturalidade que você registrou a dúvida sobre \"{unanswered_question}\" e que nossa equipe vai checar para trazer a resposta certinha.\n"
        "3. Se o usuário tiver feito mais de uma pergunta na MESMA mensagem e houver informação confirmada acima, responda a essa outra pergunta normalmente.\n"
        "4. É TERMINANTEMENTE PROIBIDO inventar informações técnicas, prazos, preços ou dados que não estejam expressamente confirmados.\n"
        "5. Mantenha a resposta concisa, clara e acolhedora (máximo de 2 a 3 frases)."
    )

    fn_get_client = _get_client_fn()
    client = fn_get_client("gpt-4o-mini")
    if not client:
        logger.warning("Cliente OpenAI não disponível para micro-prompt de dúvida sem resposta. Usando fallback.")
        return _build_fallback_response(agent_config, unanswered_question, is_handoff), {"prompt_tokens": 0, "completion_tokens": 0}

    try:
        if on_step:
            on_step(
                "⚡ Micro-Prompt Ultraleve Ativado (Opção B)",
                f"Gerando resposta humanizada de baixo custo via gpt-4o-mini para a dúvida: '{unanswered_question}'"
            )

        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=300
        )

        response_content = (completion.choices[0].message.content or "").strip()
        if not response_content:
            response_content = _build_fallback_response(agent_config, unanswered_question, is_handoff)
        
        usage = {
            "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
            "completion_tokens": completion.usage.completion_tokens if completion.usage else 0
        }

        if on_step:
            on_step(
                "✅ Resposta Humanizada Gerada (Micro-Prompt)",
                f"Tokens consumidos: {usage['prompt_tokens']} IN / {usage['completion_tokens']} OUT (~R$ 0,0001)"
            )

        return response_content, usage

    except Exception as e:
        logger.error(f"Erro ao executar micro-prompt ultraleve via gpt-4o-mini: {e}. Aplicando resposta de fallback.")
        return _build_fallback_response(agent_config, unanswered_question, is_handoff), {"prompt_tokens": 0, "completion_tokens": 0}
