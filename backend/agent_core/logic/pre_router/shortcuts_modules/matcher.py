"""Avaliador principal de atalhos determinísticos e programáticos para mensagens de entrada."""

import logging
import re

from .classification import (
    _is_recurrent_thank_you_or_closing,
    _count_payment_issue_occurrences,
    _is_closing_or_no_more_doubts,
    _is_explicit_farewell,
    _agent_has_active_qualification_funnel,
)

logger = logging.getLogger(__name__)


def check_programmatic_shortcuts(
    raw_user_message: str,
    history: list,
    main_agent,
    is_first_msg: bool,
    is_ad: bool,
    similarity_info: str,
    cleaned_message: str,
    message: str,
    context_variables: dict = None
) -> dict | None:
    """Verifica e executa todos os atalhos determinísticos/programáticos rápidos antes de chamar o LLM."""
    has_prev_closing = _is_recurrent_thank_you_or_closing(history)
    
    # Listas de saudações e agradecimentos comuns
    common_greetings = ["oi", "ola", "oie", "oiee", "bom dia", "boa tarde", "boa noite"]
    common_thanks = ["obrigado", "obrigada", "valeu", "gratidao", "obrigadao", "thanks", "tanks"]
    common_emojis = ["👍🏻", "👍🏼", "👍🏽", "👍🏾", "👍🏿", "👌🏻", "👌🏼", "👌🏽", "👌🏾", "👌🏿", "👍", "👌", "👏", "🙌", "✌️", "❤️", "✔️", "☑️", "✅", "🆗"]
    negative_emojis = ["👎🏻", "👎🏼", "👎🏽", "👎🏾", "👎🏿", "🖕🏻", "🖕🏼", "🖕🏽", "🖕🏾", "🖕🏿", "👎", "🖕", "😡", "😠", "🤬", "😕", "🙁", "☹️", "😢", "😭"]
    common_confirmations = [
        "ok", "blz", "show", "combinado", "perfeito", "certo", "beleza", "entendi", "tendi",
        "tá", "ta", "sim", "isso", "fechado", "ta bom", "tá bom", "ta bem", "tá bem",
        "tudo bem", "tudo bom", "tá certo", "ta certo", "tá ótimo", "ta otimo", "ótimo", "otimo",
        "maravilha", "belezinha", "fechou", "tá joia", "ta joia", "joia", "jóia", "combinadíssimo", "combinadissimo"
    ]
    
    initial_msg = getattr(main_agent, 'initial_message', None)
    if not initial_msg or str(initial_msg).strip().lower() in ["", "none", "null"]:
        initial_msg = "Olá! Como posso ajudar?"

    msg_clean_no_punct = cleaned_message.lower().strip()
    for char in ["?", "!", ".", ",", ";", ":", "-", "_", "(", ")", "[", "]", "{", "}"]:
        msg_clean_no_punct = msg_clean_no_punct.replace(char, "")
    msg_clean_no_punct = msg_clean_no_punct.strip()

    msg_no_emojis = msg_clean_no_punct
    has_reaction_emoji = False
    has_negative_emoji = False
    
    for em in negative_emojis:
        if em in msg_no_emojis:
            has_negative_emoji = True
        msg_no_emojis = msg_no_emojis.replace(em, "")
        
    for em in common_emojis:
        if em in msg_no_emojis:
            has_reaction_emoji = True
        msg_no_emojis = msg_no_emojis.replace(em, "")
        
    msg_no_emojis = msg_no_emojis.strip()

    # 0. Atalho para Arquivo Não Suportado (ex: "📎 Arquivo (unsupported) recebido")
    raw_lower = (raw_user_message or "").strip().lower()
    if "(unsupported)" in raw_lower or "[unsupported]" in raw_lower or "arquivo (unsupported)" in raw_lower:
        logger.info(f"🚫 [UNSUPPORTED FILE DETECTED] Mensagem '{raw_user_message}' classificada como arquivo não suportado/bot. Silenciando automação.")
        return {
            "eh_saudacao": False,
            "eh_agradecimento": False,
            "eh_agradecimento_recorrente": False,
            "eh_mensagem_automatica": True,
            "precisa_esclarecimento": False,
            "resposta_esclarecimento": None,
            "eh_anuncio": False,
            "detalhe_anuncio": None,
            "resposta_direta": None,
            "perguntas_extraidas": "",
            "lista_perguntas_extraidas": [],
            "id_agente_alvo": getattr(main_agent, "id", None),
            "precisa_ferramenta": False,
            "chamada_ferramenta": None,
            "precisa_rag": False,
            "data_extraida": None,
            "mensagem_original": raw_user_message,
            "mensagem_melhorada": None,
            "tipo_mensagem": "Arquivo Não Suportado (Ignorado)",
            "_model_used": "shortcut-logic"
        }

    # 1a. Atalho para Resposta de E-mail / Cadastro de Lead (fornecendo e-mail no fluxo de qualificação)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', raw_user_message.strip())
    if email_match and len(raw_user_message.strip().split()) <= 4:
        logger.info(f"📧 [EMAIL DETECTED] E-mail do usuário detectado: '{email_match.group(0)}'. Desativando RAG para continuidade do fluxo de atendimento/qualificação.")
        return {
            "eh_saudacao": False,
            "eh_agradecimento": False,
            "eh_agradecimento_recorrente": False,
            "eh_mensagem_automatica": False,
            "precisa_esclarecimento": False,
            "resposta_esclarecimento": None,
            "eh_anuncio": is_ad,
            "detalhe_anuncio": similarity_info,
            "resposta_direta": None,
            "perguntas_extraidas": raw_user_message.strip(),
            "lista_perguntas_extraidas": [],
            "id_agente_alvo": main_agent.id,
            "precisa_ferramenta": False,
            "chamada_ferramenta": None,
            "precisa_rag": False,
            "data_extraida": None,
            "mensagem_original": raw_user_message,
            "mensagem_melhorada": None,
            "tipo_mensagem": "Resposta de Dados / E-mail do Usuário",
            "_model_used": "shortcut-logic"
        }

    target_msg_for_questions = cleaned_message if is_ad else raw_user_message
    has_real_question = "?" in target_msg_for_questions or any(term in target_msg_for_questions.lower() for term in [
        "qual", "como", "quanto", "quem", "onde", "quando", "pode", "precisa",
        "faz", "curso", "valor", "preço", "preco", "gostaria", "tenho interesse", "funciona",
        "endereço", "endereco", "horario", "horário", "ajuda",
        "inscrição", "incrição", "requisito", "formação", "formacao", "posso", "consigo",
        "serve", "aula", "aulas", "plano", "planos", "comprar", "alugar", "saber mais"
    ])

    # 1b. Atalho para Dificuldade Recorrente no Pagamento (>= 3 mensagens relatando erro/tentativa)
    payment_issue_count = _count_payment_issue_occurrences(history, raw_user_message)
    if payment_issue_count >= 3:
        return {
            "eh_saudacao": False,
            "eh_agradecimento": False,
            "eh_agradecimento_recorrente": False,
            "precisa_esclarecimento": False,
            "resposta_esclarecimento": None,
            "id_agente_alvo": main_agent.id,
            "chamada_ferramenta": {
                "name": "transferir_suporte_humano",
                "arguments": {"motivo": f"Dificuldade recorrente de pagamento ({payment_issue_count} mensagens do cliente tentando pagar sem sucesso)"}
            },
            "resposta_direta": "Poxa, lamento muito que esteja com dificuldades para concluir o pagamento! Vou te transferir agora mesmo para nossa equipe de suporte humano para te ajudar a finalizar certinho. Um momento, por favor! 😊",
            "perguntas_extraidas": None,
            "lista_perguntas_extraidas": [],
            "data_extraida": None,
            "precisa_rag": False,
            "eh_anuncio": is_ad,
            "detalhe_anuncio": similarity_info,
            "mensagem_original": raw_user_message,
            "mensagem_melhorada": None,
            "tipo_mensagem": "Dificuldade Recorrente de Pagamento (Transferir para Suporte Humano)",
            "_model_used": "shortcut-logic"
        }

    # 1c. Atalho para Encerramento / Sem Mais Dúvidas ("Não era só isso mesmo", "Só isso mesmo", "Não preciso de mais nada")
    if _is_closing_or_no_more_doubts(raw_user_message, history):
        has_active_funnel = _agent_has_active_qualification_funnel(main_agent, context_variables)
        if has_active_funnel and not _is_explicit_farewell(raw_user_message):
            logger.info(f"🎯 [QUALIFICATION FUNNEL] Lead declarou ausência de dúvidas ('{raw_user_message}'), mas o agente possui funil de qualificação ativo com etapas pendentes. Prosseguindo para o Agente Principal continuar o funil.")
            return {
                "eh_saudacao": False,
                "eh_agradecimento": False,
                "eh_agradecimento_recorrente": False,
                "eh_mensagem_automatica": False,
                "eh_resposta_ao_agente": True,
                "precisa_esclarecimento": False,
                "resposta_esclarecimento": None,
                "eh_anuncio": is_ad,
                "detalhe_anuncio": similarity_info,
                "resposta_direta": None,
                "perguntas_extraidas": None,
                "lista_perguntas_extraidas": [],
                "id_agente_alvo": main_agent.id,
                "precisa_ferramenta": False,
                "chamada_ferramenta": None,
                "precisa_rag": False,
                "data_extraida": None,
                "mensagem_original": raw_user_message,
                "mensagem_melhorada": None,
                "tipo_mensagem": "Resposta de Ausência de Dúvidas / Continuidade de Qualificação",
                "_model_used": "shortcut-logic"
            }

        if has_prev_closing:
            return {
                "eh_saudacao": True,
                "eh_agradecimento": True,
                "eh_agradecimento_recorrente": True,
                "precisa_esclarecimento": False,
                "resposta_esclarecimento": None,
                "id_agente_alvo": main_agent.id,
                "resposta_direta": None,
                "perguntas_extraidas": None,
                "lista_perguntas_extraidas": [],
                "data_extraida": None,
                "precisa_rag": False,
                "eh_anuncio": is_ad,
                "detalhe_anuncio": similarity_info,
                "mensagem_original": raw_user_message,
                "mensagem_melhorada": message if message != raw_user_message else None,
                "tipo_mensagem": "Agradecimento / Encerramento Recorrente (Não Responder)",
                "motivo_silencio": "2º agradecimento/encerramento consecutivo detectado. Automação silenciada para evitar envio de mensagens infinitamente.",
                "_model_used": "shortcut-logic"
            }
        else:
            return {
                "eh_saudacao": True,
                "eh_agradecimento": True,
                "eh_agradecimento_recorrente": False,
                "precisa_esclarecimento": False,
                "resposta_esclarecimento": None,
                "id_agente_alvo": main_agent.id,
                "resposta_direta": "Perfeito! Fico à disposição se precisar de qualquer outra informação ou se tiver alguma dúvida. Bons estudos e até logo! 😊",
                "perguntas_extraidas": None,
                "lista_perguntas_extraidas": [],
                "data_extraida": None,
                "precisa_rag": False,
                "eh_anuncio": is_ad,
                "detalhe_anuncio": similarity_info,
                "mensagem_original": raw_user_message,
                "mensagem_melhorada": message if message != raw_user_message else None,
                "tipo_mensagem": "Encerramento / Sem Mais Dúvidas (Atalho Programático)",
                "_model_used": "shortcut-logic"
            }

    # 1d. Atalho para Respostas Negativas / Conversacionais Curtas (Ex: "Não", "Nao", "Ainda não", "Nenhuma", "Não trabalho na área", "Não tenho dúvidas", "Era só isso")
    short_negations = {
        "nao", "não", "nao.", "não.", "nao nao", "não não",
        "nenhuma", "nenhum", "nada", "nada mais", "mais nada",
        "ainda nao", "ainda não", "por enquanto nao", "por enquanto não",
        "nao tenho", "não tenho", "nao trabalho", "não trabalho", "nao atuo", "não atuo",
        "nao sou", "não sou", "começando do zero", "comecando do zero", "do zero",
        "nunca trabalhei", "nunca atuei", "nao tenho curso", "não tenho curso",
        "nao era so isso", "não era só isso", "nao era so isso mesmo", "não era só isso mesmo",
        "era so isso", "era só isso", "era so isso mesmo", "era só isso mesmo",
        "so isso", "só isso", "so isso mesmo", "só isso mesmo",
        "so essa duvida", "só essa dúvida", "era so essa duvida", "era só essa dúvida",
        "nao tenho mais duvidas", "não tenho mais dúvidas", "sem mais duvidas", "sem mais dúvidas",
        "sem duvidas", "sem dúvidas", "por enquanto e so", "por enquanto é só",
        "nao preciso de mais nada", "não preciso de mais nada", "tudo certo", "tudo claro"
    }
    if (msg_clean_no_punct in short_negations or bool(re.match(r'^(?:n[aã]o|nenhum[a]?|nada|ainda\s+n[aã]o|sem\s+d[uú]vidas?|era\s+s[oó]|s[oó]\s+isso|por\s+enquanto)\b', msg_clean_no_punct))) and not has_real_question:
        logger.info(f"🛑 [CONVERSATIONAL NEGATION] Resposta negativa conversacional detectada: '{raw_user_message}'. Desativando RAG e mantendo texto original para continuidade do atendimento.")
        return {
            "eh_saudacao": False,
            "eh_agradecimento": False,
            "eh_agradecimento_recorrente": False,
            "eh_mensagem_automatica": False,
            "precisa_esclarecimento": False,
            "resposta_esclarecimento": None,
            "eh_anuncio": is_ad,
            "detalhe_anuncio": similarity_info,
            "resposta_direta": None,
            "perguntas_extraidas": raw_user_message.strip(),
            "lista_perguntas_extraidas": [],
            "id_agente_alvo": main_agent.id,
            "precisa_ferramenta": False,
            "chamada_ferramenta": None,
            "precisa_rag": False,
            "data_extraida": None,
            "mensagem_original": raw_user_message,
            "mensagem_melhorada": raw_user_message,
            "tipo_mensagem": "Resposta Conversacional / Qualificação do Usuário",
            "_model_used": "shortcut-logic"
        }

    is_thank_you = (msg_clean_no_punct in common_thanks) or (msg_no_emojis in common_thanks)

    # 3. Saudação simples ou Anúncio puro sem perguntas (apenas se não houver pergunta)
    if not has_real_question and (msg_clean_no_punct in common_greetings or (msg_clean_no_punct == "" and (not raw_user_message.strip() or is_ad))):
        greeting_prefix = None
        if "bom dia" in msg_clean_no_punct:
            greeting_prefix = "Bom dia!"
        elif "boa tarde" in msg_clean_no_punct:
            greeting_prefix = "Boa tarde!"
        elif "boa noite" in msg_clean_no_punct:
            greeting_prefix = "Boa noite!"

        if is_first_msg:
            if initial_msg:
                clean_initial = initial_msg.strip()
                if greeting_prefix:
                    match_lead_greet = re.match(r'^(?:oi|olá|ola|oie|oiee|bom dia|boa tarde|boa noite)[\s,!-]*', clean_initial, re.IGNORECASE)
                    if match_lead_greet:
                        rest_of_msg = clean_initial[match_lead_greet.end():].lstrip()
                        resposta = f"{greeting_prefix} {rest_of_msg}".strip()
                    else:
                        resposta = f"{greeting_prefix} {clean_initial}".strip()
                else:
                    resposta = clean_initial
            else:
                prefix = greeting_prefix or "Olá!"
                resposta = f"{prefix} Como posso te ajudar?"
        else:
            if greeting_prefix:
                resposta = f"{greeting_prefix} Como posso te ajudar?"
            else:
                resposta = "Olá! Como posso te ajudar?"

        if getattr(main_agent, 'greeting_mode', 'prompt') == 'disabled':
            logger.info(f"🚫 [GREETING DISABLED] Saudação inicial desativada nas configurações do agente. Pulando atalho programático de saudação.")
            return None
        elif getattr(main_agent, 'greeting_mode', 'prompt') == 'panel':
            return {
                "eh_saudacao": True,
                "eh_agradecimento": False,
                "precisa_esclarecimento": False,
                "id_agente_alvo": main_agent.id,
                "resposta_direta": resposta,
                "perguntas_extraidas": None,
                "lista_perguntas_extraidas": [],
                "data_extraida": None,
                "precisa_rag": False,
                "eh_anuncio": is_ad,
                "detalhe_anuncio": similarity_info,
                "mensagem_original": raw_user_message,
                "mensagem_melhorada": message if message != raw_user_message else None,
                "tipo_mensagem": "Saudação (Atalho Programático)",
                "_model_used": "shortcut-logic"
            }
    elif is_thank_you:
        if has_prev_closing:
            return {
                "eh_saudacao": True,
                "eh_agradecimento": True,
                "eh_agradecimento_recorrente": True,
                "precisa_esclarecimento": False,
                "id_agente_alvo": main_agent.id,
                "resposta_direta": None,
                "perguntas_extraidas": None,
                "lista_perguntas_extraidas": [],
                "data_extraida": None,
                "precisa_rag": False,
                "eh_anuncio": is_ad,
                "detalhe_anuncio": similarity_info,
                "mensagem_original": raw_user_message,
                "mensagem_melhorada": message if message != raw_user_message else None,
                "tipo_mensagem": "Agradecimento Recorrente (Não Responder)",
                "motivo_silencio": "2º agradecimento/encerramento consecutivo detectado. Automação silenciada para evitar envio de mensagens infinitamente.",
                "_model_used": "shortcut-logic"
            }
        return None
    else:
        is_pure_emoji_reaction = (has_reaction_emoji or has_negative_emoji) and msg_no_emojis == ""
        is_confirmation_word = msg_clean_no_punct in common_confirmations or msg_no_emojis in common_confirmations
        
        if is_pure_emoji_reaction or is_confirmation_word:
            if has_negative_emoji and is_pure_emoji_reaction:
                return {
                    "eh_saudacao": True,
                    "eh_agradecimento": False,
                    "eh_emoji_negativo": True,
                    "precisa_esclarecimento": False,
                    "id_agente_alvo": main_agent.id,
                    "resposta_direta": "Puxa, sinto muito! 😕 Percebi que algo não deu certo. O que aconteceu? Como posso te ajudar a resolver de uma forma melhor?",
                    "perguntas_extraidas": None,
                    "lista_perguntas_extraidas": [],
                    "data_extraida": None,
                    "precisa_rag": False,
                    "eh_anuncio": is_ad,
                    "detalhe_anuncio": similarity_info,
                    "mensagem_original": raw_user_message,
                    "mensagem_melhorada": message if message != raw_user_message else None,
                    "tipo_mensagem": "Emoji Negativo / Insatisfação (Atalho Empático)",
                    "_model_used": "shortcut-logic"
                }

            last_assistant_asked = False
            if history:
                for h in reversed(history):
                    if h.get("role") == "assistant":
                        content = h.get("content", "")
                        if "?" in content:
                            last_assistant_asked = True
                        break
            
            if is_pure_emoji_reaction or not last_assistant_asked:
                if has_prev_closing:
                    return {
                        "eh_saudacao": True,
                        "eh_agradecimento": True,
                        "eh_agradecimento_recorrente": True,
                        "precisa_esclarecimento": False,
                        "id_agente_alvo": main_agent.id,
                        "resposta_direta": None,
                        "perguntas_extraidas": None,
                        "lista_perguntas_extraidas": [],
                        "data_extraida": None,
                        "precisa_rag": False,
                        "eh_anuncio": is_ad,
                        "detalhe_anuncio": similarity_info,
                        "mensagem_original": raw_user_message,
                        "mensagem_melhorada": message if message != raw_user_message else None,
                        "tipo_mensagem": "Agradecimento Recorrente (Não Responder)",
                        "motivo_silencio": "2º agradecimento/encerramento consecutivo detectado. Automação silenciada para evitar envio de mensagens infinitamente.",
                        "_model_used": "shortcut-logic"
                    }
                else:
                    resposta_confirmacao = "Perfeito! Se precisar de mais alguma coisa, é só chamar. 😊"
                    if "combinado" in msg_clean_no_punct:
                        resposta_confirmacao = "Combinado! Qualquer dúvida, estou por aqui. 😉"
                    elif "ok" in msg_clean_no_punct:
                        resposta_confirmacao = "Combinado! Se precisar de algo, é só chamar. 👍"
                    elif "certo" in msg_clean_no_punct:
                        resposta_confirmacao = "Certo! Se precisar de mais alguma ajuda, estou à disposição. 👍"
                    elif any(t in msg_clean_no_punct for t in ["ta bom", "tá bom", "ta bem", "tá bem", "tudo bem", "tudo bom"]):
                        resposta_confirmacao = "Combinado! Se precisar de qualquer ajuda, estou por aqui. 😊"
                    elif any(t in msg_clean_no_punct for t in ["ótimo", "otimo", "maravilha", "show", "beleza", "blz"]):
                        resposta_confirmacao = "Maravilha! Qualquer dúvida, é só me chamar por aqui. 😊"
                        
                    return {
                        "eh_saudacao": True,
                        "eh_agradecimento": False,
                        "precisa_esclarecimento": False,
                        "id_agente_alvo": main_agent.id,
                        "resposta_direta": resposta_confirmacao,
                        "perguntas_extraidas": None,
                        "lista_perguntas_extraidas": [],
                        "data_extraida": None,
                        "precisa_rag": False,
                        "eh_anuncio": is_ad,
                        "detalhe_anuncio": similarity_info,
                        "mensagem_original": raw_user_message,
                        "mensagem_melhorada": message if message != raw_user_message else None,
                        "tipo_mensagem": "Confirmação / Reação (Atalho Programático)",
                        "_model_used": "shortcut-logic"
                    }

    return None
