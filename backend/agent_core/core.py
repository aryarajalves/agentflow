import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from core.timezone import get_now_br

from .clients import get_openai_client, get_anthropic_client
from .models.usage import UsageLog
from .utils import INTERNAL_CTX_KEYS, sanitize_phone_number, format_whatsapp_message
from .logic.classification import classify_message_complexity
from .logic.substitution import resolve_conditional_blocks
from .logic.history import generate_handoff_summary
from .logic.pre_router import run_pre_router_ai
from .logic.cache_handler import handle_semantic_cache_check
from .logic.question_funnel_handler import handle_question_funnel_check
from .logic.tool_preparer import prepare_agent_tools
from .security import verify_output_safety, validate_response_ai
from .memory import fetch_user_memory, update_user_memory
from .tools.handlers.chatwoot import handle_chatwoot_handoff
from .tools.handlers.internal import handle_date_calculator, handle_unanswered_question, handle_lead_qualified
from .tools.handlers.google import handle_google_calendar

from .logic.prompt_builder import prepare_context_variables, build_system_prompt_messages
from .logic.rag_resolver import resolve_rag_context
from .logic.tool_executor import inject_pre_executed_tool_calls, execute_tool_calls
from .logic.output_processor import process_final_response

logger = logging.getLogger(__name__)


def format_ai_error_message(e: Exception, provider: str = "OpenAI") -> str:
    """Transforma exceções do provedor de IA em mensagens explícitas em português."""
    err_str = str(e)
    err_lower = err_str.lower()
    
    if "insufficient_quota" in err_lower or "credit_balance_exhausted" in err_lower or ("429" in err_str and "credit" in err_lower):
        return f"❌ Erro na {provider}: Saldo de créditos esgotado (insufficient_quota / credit_balance_exhausted). Adicione créditos no painel da {provider}."
    elif "rate_limit_exceeded" in err_lower or "429" in err_str:
        return f"❌ Erro na {provider}: Limite de requisições excedido (Rate Limit Exceeded / 429). Aguarde alguns instantes."
    elif "invalid_api_key" in err_lower or "incorrect api key" in err_lower or "401" in err_str:
        return f"❌ Erro na {provider}: Chave de API inválida ou não configurada (401 Unauthorized)."
    elif "model_not_found" in err_lower or "does not exist" in err_lower or "404" in err_str:
        return f"❌ Erro na {provider}: O modelo de IA solicitado não existe ou não está disponível para esta conta."
    elif "context_length_exceeded" in err_lower or "maximum context length" in err_lower:
        return f"❌ Erro na {provider}: O tamanho do contexto da conversa excedeu o limite do modelo."
    else:
        clean_msg = err_str[:250]
        return f"❌ Erro na {provider}: {clean_msg}"


async def process_message(
    message: str, history: list, config, tools: list = None, 
    context_variables: dict = None, db: AsyncSession = None,
    performed_tool_calls: list = None, image_url: str = None,
    on_step: callable = None,
    pre_executed_tool_calls: list = None,
    pre_executed_rag_context: str = None
):
    active_role = "main"
    now_br = get_now_br()
    context_variables = await prepare_context_variables(context_variables, db=db)
    performed_tool_calls = performed_tool_calls if performed_tool_calls is not None else []
    
    # 0.05 FUNIL DE CONVERSÃO POR DÚVIDA (ÁUDIO HUMANIZADO + PASSOS SEQUENCIAIS)
    funnel_res, _ = await handle_question_funnel_check(
        config=config, message=message, history=history, context_variables=context_variables,
        db=db, image_url=image_url, performed_tool_calls=performed_tool_calls,
        pre_executed_tool_calls=pre_executed_tool_calls, pre_executed_rag_context=pre_executed_rag_context,
        on_step=on_step, return_diagnostics=True
    )
    if funnel_res:
        return funnel_res

    # 0.1 CACHE SEMÂNTICO DE RESPOSTAS APROVADAS (CUSTO ZERO OU PARCIAL)
    cache_result, pre_executed_rag_context, cache_diagnostics = await handle_semantic_cache_check(
        config=config,
        message=message,
        history=history,
        context_variables=context_variables,
        db=db,
        image_url=image_url,
        performed_tool_calls=performed_tool_calls,
        pre_executed_tool_calls=pre_executed_tool_calls,
        pre_executed_rag_context=pre_executed_rag_context,
        on_step=on_step,
        return_diagnostics=True
    )
    if cache_result:
        return cache_result

    pre_router_tokens = {"prompt": 0, "completion": 0, "model": None}
    pre_router_result = {}

    # 0. Pre-Router (Saudação, Triagem e Datas)
    if not image_url and not performed_tool_calls and not pre_executed_tool_calls and pre_executed_rag_context is None:
        try:
            pre_router_result = await run_pre_router_ai(message, history, config, context_variables=context_variables, db=db)
            
            if pre_router_result.get("eh_agradecimento_recorrente") or (pre_router_result.get("eh_agradecimento") and pre_router_result.get("resposta_direta") is None and not pre_router_result.get("perguntas_extraidas")):
                usage = pre_router_result.get("_usage", {})
                if on_step:
                    on_step("🤫 Automação Silenciada (Agradecimento Recorrente)", "2º agradecimento/encerramento consecutivo do usuário detectado. Nenhuma mensagem será enviada para evitar loop.")
                return {
                    "content": None,
                    "model": pre_router_result.get("_model_used", "pre-router"),
                    "model_role": "pre-router",
                    "usage": UsageLog(
                        mp=usage.get("prompt_tokens", 0),
                        mc=usage.get("completion_tokens", 0)
                    ),
                    "error": False,
                    "ignored_recurrent_thanks": True,
                    "semantic_cache": cache_diagnostics,
                    "debug": {"pre_router": pre_router_result, "semantic_cache": cache_diagnostics, "model_role": "pre-router"}
                }

            if (pre_router_result.get("eh_saudacao") or pre_router_result.get("_model_used") == "shortcut-logic") and pre_router_result.get("resposta_direta") and not on_step:
                usage = pre_router_result.get("_usage", {})
                return {
                    "content": pre_router_result.get("resposta_direta"),
                    "model": pre_router_result.get("_model_used", "pre-router"),
                    "model_role": "pre-router",
                    "usage": UsageLog(
                        mp=usage.get("prompt_tokens", 0),
                        mc=usage.get("completion_tokens", 0)
                    ),
                    "error": False,
                    "semantic_cache": cache_diagnostics,
                    "debug": {"pre_router": pre_router_result, "semantic_cache": cache_diagnostics, "model_role": "pre-router"}
                }
            
            pr_usage = pre_router_result.get("_usage", {})
            pre_router_tokens["prompt"] = pr_usage.get("prompt_tokens", 0)
            pre_router_tokens["completion"] = pr_usage.get("completion_tokens", 0)
            pre_router_tokens["model"] = pre_router_result.get("_model_used")

            if pre_router_result.get("data_extraida"):
                context_variables["data_extraida"] = pre_router_result["data_extraida"]
            
            if pre_router_result.get("perguntas_extraidas"):
                original_msg = message
                message = pre_router_result["perguntas_extraidas"]
                if original_msg != message and on_step:
                    on_step("🧹 Melhoria de Mensagem (Pre-Router)", f"Pergunta isolada para busca pelo Pre-Router (mensagem integral preservada para o agente).\nAntes: \"{original_msg}\"\nDepois: \"{message}\"")
                
        except Exception as e_pr:
            logger.error(f"Erro no Pre-Router (core): {e_pr}")

    is_partial_cache = bool((cache_diagnostics or {}).get("status") == "partial_hit")

    # 1. Cost Router
    if getattr(config, 'router_enabled', False):
        has_cache_resolved = bool(pre_executed_rag_context and "RESPOSTA OFICIAL PRÉ-APROVADA DO CACHE SEMÂNTICO" in pre_executed_rag_context and not is_partial_cache)
        
        if has_cache_resolved:
            complexity = "SIMPLE"
            active_role = "router_simple"
            config.model = getattr(config, 'router_simple_model', None) or config.model
        else:
            complexity = "COMPLEX" if image_url else await classify_message_complexity(message, config, history)
            active_role = "router_simple" if complexity == "SIMPLE" else "router_complex"
            
            if complexity == "SIMPLE":
                config.model = getattr(config, 'router_simple_model', None) or config.model
            else:
                config.model = getattr(config, 'router_complex_model', None) or config.model
            
        print(f"🚀 [ROTEAMENTO DE CUSTO] Complexidade: {complexity}. Modelo selecionado: {config.model} (Papel: {active_role})")

    executed_model = config.model
    executed_role = active_role

    # 2. Context Window
    target_window = config.context_window or 5
    if history and len(history) > (target_window * 2):
        history = history[-(target_window * 2):]

    client = get_openai_client(config.model)
    if not client: 
        return {"content": "Erro: API Key não configurada.", "error": True}

    # 3. System Prompt & Variable Injection
    messages = await build_system_prompt_messages(
        config=config, 
        context_variables=context_variables, 
        tools=tools, 
        history=history, 
        db=db
    )

    # 4. RAG & Bases de Conhecimento
    rag_data = await resolve_rag_context(
        config=config,
        db=db,
        message=message,
        history=history,
        context_variables=context_variables,
        messages=messages,
        pre_router_result=pre_router_result,
        pre_executed_rag_context=pre_executed_rag_context,
        is_partial_cache=is_partial_cache,
        cache_diagnostics=cache_diagnostics,
        on_step=on_step
    )
    rag_context = rag_data["rag_context"]
    if rag_context and context_variables is not None:
        context_variables["rag_context"] = rag_context
    rag_queries = rag_data["rag_queries"]
    rag_query_str = rag_data["rag_query_str"]
    all_relevant = rag_data["all_relevant"]
    mini_prompt_tokens = rag_data["mini_prompt_tokens"]
    mini_completion_tokens = rag_data["mini_completion_tokens"]

    messages.extend(history)
    raw_user_input = context_variables.get("raw_user_message") or (original_msg if 'original_msg' in locals() and original_msg else message)
    user_prompt_content = str(raw_user_input).strip() if raw_user_input else message
    messages.append({"role": "user", "content": user_prompt_content})

    # 5. Preparar Ferramentas (Tools)
    is_already_qualified = bool(context_variables.get("lead_already_qualified"))
    has_lead_qualified = (any(getattr(t, "name", "") == "lead_qualificado" for t in tools) if tools else False) and not is_already_qualified
    openai_tools = prepare_agent_tools(
        tools=tools,
        config=config,
        context_variables=context_variables,
        pre_router_result=pre_router_result,
        is_already_qualified=is_already_qualified,
        has_lead_qualified=has_lead_qualified
    )

    # 6. Loop de Execução (Turnos de Ferramentas)
    total_usage = UsageLog(0, 0, 0, 0)
    total_usage.mini_prompt += (mini_prompt_tokens + pre_router_tokens["prompt"])
    total_usage.mini_completion += (mini_completion_tokens + pre_router_tokens["completion"])
    
    handoff_data = {"handoff": False, "destino": None, "motivo": None}
    last_response = ""
    iteration = 0
    tool_calls_log = []
    is_handoff_terminal = False
    tool_call_counts = {}
    tool_failure_counts = {}

    if pre_executed_tool_calls:
        h_data, is_term, l_resp = inject_pre_executed_tool_calls(
            messages=messages,
            pre_executed_tool_calls=pre_executed_tool_calls,
            tool_calls_log=tool_calls_log,
            now_br=now_br,
            on_step=on_step
        )
        if h_data.get("handoff"):
            handoff_data = h_data
        if is_term:
            is_handoff_terminal = True
        if l_resp:
            last_response = l_resp

    while iteration < 5:
        if is_handoff_terminal:
            break
        iteration += 1
        try:
            models_to_try = [config.model]
            if getattr(config, 'fallback_model', None):
                models_to_try.append(config.fallback_model)
            
            response_message = None
            last_error = None
            for m in models_to_try:
                try:
                    curr_client = get_openai_client(m)
                    if not curr_client: 
                        continue
                    
                    api_params = {
                        "model": m,
                        "messages": messages,
                        "temperature": getattr(config, 'temperature', 0.1)
                    }
                    if openai_tools:
                        api_params["tools"] = openai_tools
                        api_params["tool_choice"] = "auto"
                    
                    completion = await curr_client.chat.completions.create(**api_params)
                    response_message = completion.choices[0].message
                    executed_model = m
                    executed_role = active_role if m == config.model else "fallback"
                    
                    if completion.usage:
                        total_usage.main_prompt += completion.usage.prompt_tokens
                        total_usage.main_completion += completion.usage.completion_tokens
                        
                        cached_toks = 0
                        if hasattr(completion.usage, 'prompt_tokens_details') and completion.usage.prompt_tokens_details:
                            details = completion.usage.prompt_tokens_details
                            cached_toks = getattr(details, 'cached_tokens', 0) or (details.get('cached_tokens', 0) if isinstance(details, dict) else 0) or 0
                        elif hasattr(completion.usage, 'cache_read_input_tokens'):
                            cached_toks = getattr(completion.usage, 'cache_read_input_tokens', 0) or 0
                        elif hasattr(completion.usage, 'extra_fields') and 'prompt_cache_hit_tokens' in completion.usage.extra_fields:
                            cached_toks = completion.usage.extra_fields.get('prompt_cache_hit_tokens', 0) or 0
                        total_usage.cached_tokens += cached_toks
                    break
                except Exception as e:
                    last_error = e
                    logger.error(f"⚠️ Erro no modelo {m}: {str(e)}")
                    continue

            if not response_message:
                tech_error_msg = format_ai_error_message(last_error, "OpenAI") if last_error else "❌ Erro na integração de IA: Falha ao comunicar com os modelos configurados."
                user_friendly_msg = "Desculpe, estou enfrentando uma instabilidade temporária agora. Por favor, tente novamente em instantes."
                return {
                    "content": user_friendly_msg, 
                    "system_error": tech_error_msg,
                    "error": True, 
                    "usage": total_usage, 
                    "model": getattr(config, 'model', 'gpt-4o-mini')
                }

            messages.append(response_message)
            
            t_calls = getattr(response_message, "tool_calls", None)
            if t_calls and isinstance(t_calls, list):
                term_h, h_info, resp_t, openai_tools = await execute_tool_calls(
                    response_message=response_message,
                    openai_tools=openai_tools,
                    messages=messages,
                    tool_calls_log=tool_calls_log,
                    tool_call_counts=tool_call_counts,
                    tool_failure_counts=tool_failure_counts,
                    tools=tools,
                    config=config,
                    db=db,
                    context_variables=context_variables,
                    history=history,
                    on_step=on_step,
                    total_usage=total_usage
                )
                if h_info.get("handoff"):
                    handoff_data = h_info
                if resp_t:
                    last_response = resp_t
                if term_h:
                    is_handoff_terminal = True
                    break
                continue
            
            if response_message.content is not None:
                last_response = str(response_message.content)
            elif not last_response:
                last_response = ""
            break
            
        except Exception as e:
            logger.error(f"❌ Erro crítico no loop do agente: {str(e)}")
            return {"content": f"Erro interno: {str(e)}", "error": True, "usage": total_usage, "model": getattr(config, 'model', 'gpt-4o-mini')}

    # 7. Pós-Processamento da Resposta e Auditoria
    final_content = await process_final_response(
        last_response=last_response,
        handoff_data=handoff_data,
        config=config,
        history=history,
        message=message,
        context_variables=context_variables,
        db=db,
        tool_calls_log=tool_calls_log,
        has_lead_qualified=has_lead_qualified,
        on_step=on_step
    )

    c_diag = cache_diagnostics if 'cache_diagnostics' in locals() and cache_diagnostics else {}
    final_model = executed_model if 'executed_model' in locals() and executed_model else config.model
    final_role = executed_role if 'executed_role' in locals() and executed_role else active_role
    return {
        "content": final_content,
        "usage": total_usage,
        "model": final_model,
        "model_role": final_role,
        "router_model": pre_router_tokens.get("model"),
        "router_tokens": {
            "prompt": pre_router_tokens["prompt"],
            "completion": pre_router_tokens["completion"]
        },
        "handoff_data": handoff_data,
        "error": False,
        "semantic_cache": c_diag,
        "from_semantic_cache": c_diag.get("status") == "hit_direct",
        "cached_similarity": c_diag.get("similarity"),
        "cached_original_query": c_diag.get("matched_query"),
        "rag_queries": rag_queries if 'rag_queries' in locals() and rag_queries else [],
        "rag_query": rag_query_str if 'rag_query_str' in locals() and rag_query_str else (rag_queries[0] if 'rag_queries' in locals() and rag_queries else None),
        "debug": {
            "iterations": iteration,
            "rag_items": all_relevant if 'all_relevant' in locals() and all_relevant else [],
            "rag_queries": rag_queries if 'rag_queries' in locals() and rag_queries else [],
            "rag_query": rag_query_str if 'rag_query_str' in locals() and rag_query_str else (rag_queries[0] if 'rag_queries' in locals() and rag_queries else None),
            "resolved_prompt": messages[0]["content"],
            "tool_calls": tool_calls_log,
            "pre_router": pre_router_result if 'pre_router_result' in locals() else None,
            "context_variables": context_variables,
            "semantic_cache": c_diag,
            "cache_hit": c_diag.get("status") in ["hit_direct", "hit_qualification", "partial_hit"],
            "cached_similarity": c_diag.get("similarity"),
            "cached_original_query": c_diag.get("matched_query"),
            "matched_queries": c_diag.get("matched_queries") or ([c_diag.get("matched_query")] if c_diag.get("matched_query") else []),
            "from_semantic_cache": c_diag.get("status") == "hit_direct",
            "user_message_sent": user_prompt_content if 'user_prompt_content' in locals() else message,
            "model_role": final_role
        }
    }
