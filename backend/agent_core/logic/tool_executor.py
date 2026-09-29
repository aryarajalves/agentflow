import json
import logging
import sys
import httpx
from .history import generate_handoff_summary
from ..tools.handlers.chatwoot import handle_chatwoot_handoff
from ..tools.handlers.internal import handle_date_calculator, handle_unanswered_question, handle_lead_qualified
from ..tools.handlers.google import handle_google_calendar

logger = logging.getLogger(__name__)


def _get_core_attr(attr_name: str, default_val):
    """Obtém atributo de agent_core.core se disponível (para respeitar patches e mocks em testes)."""
    core_mod = sys.modules.get("agent_core.core")
    if core_mod and hasattr(core_mod, attr_name):
        return getattr(core_mod, attr_name)
    return default_val


def inject_pre_executed_tool_calls(
    messages: list, 
    pre_executed_tool_calls: list, 
    tool_calls_log: list, 
    now_br, 
    on_step: callable = None
) -> tuple:
    """Injeta chamadas de ferramentas pré-executadas de forma simulada no histórico de mensagens."""
    handoff_data = {"handoff": False, "destino": None, "motivo": None}
    is_handoff_terminal = False
    last_response = ""

    if not pre_executed_tool_calls:
        return handoff_data, is_handoff_terminal, last_response

    simulated_calls = []
    for i, tc in enumerate(pre_executed_tool_calls):
        t_id = f"call_pre_{i}_{now_br.microsecond}"
        simulated_calls.append({
            "id": t_id,
            "type": "function",
            "function": {
                "name": tc["name"],
                "arguments": json.dumps(tc["args"], ensure_ascii=False)
            }
        })
    
    # Mensagem do assistente propondo as chamadas
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": simulated_calls
    })
    
    # Respostas das ferramentas correspondentes
    for i, tc in enumerate(pre_executed_tool_calls):
        messages.append({
            "role": "tool",
            "name": tc["name"],
            "tool_call_id": simulated_calls[i]["id"],
            "content": tc["output"]
        })
        
        tool_calls_log.append({
            "name": tc["name"],
            "args": json.dumps(tc["args"], ensure_ascii=False),
            "output": tc["output"]
        })
        
        # Tratamento de suporte humano se a ferramenta pré-executada for de transbordo
        if tc["name"] in ["transferir_atendimento", "transferir_suporte_humano"]:
            motivo = tc["args"].get("motivo", "Solicitado pelo usuário")
            handoff_data = {"handoff": True, "destino": "humano", "motivo": motivo}
            is_handoff_terminal = True
            last_response = "Entendi perfeitamente. Estou transferindo seu atendimento para nossa equipe especializada para que você receba o suporte adequado. Um momento, por favor! ✨"
            if on_step:
                on_step("🚑 Suporte Humano solicitado (Pré-executado)", f"Motivo: {motivo}")
        elif tc["name"] == "registrar_duvida_sem_resposta":
            if "AUTOMATICAMENTE TRANSFERIDO PARA O SUPORTE HUMANO" in str(tc.get("output", "")):
                motivo = f"Dúvida sem resposta acionada > 1 vez: {tc.get('args', {}).get('pergunta', 'Dúvida do usuário')}"
                handoff_data = {"handoff": True, "destino": "humano", "motivo": motivo}

    return handoff_data, is_handoff_terminal, last_response


async def execute_tool_calls(
    response_message,
    openai_tools: list,
    messages: list,
    tool_calls_log: list,
    tool_call_counts: dict,
    tool_failure_counts: dict,
    tools: list,
    config,
    db,
    context_variables: dict,
    history: list,
    on_step: callable = None,
    total_usage=None
) -> tuple:
    """Executa as ferramentas acionadas pelo modelo na iteração atual."""
    handoff_data = {"handoff": False, "destino": None, "motivo": None}
    is_handoff_terminal = False
    last_response = ""

    t_calls = getattr(response_message, "tool_calls", None)
    if not t_calls or not isinstance(t_calls, list):
        return is_handoff_terminal, handoff_data, last_response, openai_tools

    fn_summary = _get_core_attr("generate_handoff_summary", generate_handoff_summary)
    fn_chatwoot = _get_core_attr("handle_chatwoot_handoff", handle_chatwoot_handoff)
    fn_date = _get_core_attr("handle_date_calculator", handle_date_calculator)
    fn_unanswered = _get_core_attr("handle_unanswered_question", handle_unanswered_question)
    fn_calendar = _get_core_attr("handle_google_calendar", handle_google_calendar)
    fn_lead_qual = _get_core_attr("handle_lead_qualified", handle_lead_qualified)

    for tool_call in t_calls:
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        
        if on_step:
            on_step(f"🛠️ Acionando ferramenta: {tool_name}", f"Argumentos: {json.dumps(tool_args, ensure_ascii=False)}")
        
        tool_call_counts[tool_name] = tool_call_counts.get(tool_name, 0) + 1

        # Limitador de segurança: no máximo 2 execuções por ferramenta neste turno se houver falha
        if tool_failure_counts.get(tool_name, 0) >= 2 or tool_call_counts[tool_name] > 2:
            tool_result = (
                f"AVISO DO SISTEMA: A ferramenta '{tool_name}' atingiu o limite máximo de tentativas (máximo 2 chamadas). "
                "INSTRUÇÃO OBRIGATÓRIA PARA SUA RESPOSTA: É terminantemente proibido tentar acionar esta ferramenta novamente. "
                "Peça desculpas ao cliente de forma simpática, informe que houve uma pequena instabilidade momentânea no sistema "
                "e prossiga com o atendimento respondendo às dúvidas dele normalmente."
            )
            openai_tools = [t for t in openai_tools if t.get("function", {}).get("name") != tool_name]
            messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": tool_name, "content": tool_result})
            tool_calls_log.append({
                "name": tool_name,
                "args": json.dumps(tool_args, ensure_ascii=False),
                "output": tool_result
            })
            continue

        # Caso Especial: Handoff
        if tool_name in ["transferir_atendimento", "transferir_suporte_humano"]:
            destino = tool_args.get("destino", "humano")
            motivo = tool_args.get("motivo", "Solicitado pelo usuário")
            
            handoff_data = {"handoff": True, "destino": destino, "motivo": motivo}
            summary = await fn_summary(history + [messages[-2]]) 
            handoff_data["summary"] = summary
            
            t_tool = next((t for t in tools if t.name == tool_name), None) if tools else None
            handoff_result = await fn_chatwoot(db, context_variables, t_tool, True, tool_args, history, config.id)
            
            tool_result = handoff_result
            messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": tool_name, "content": tool_result})
            last_response = "Entendi perfeitamente. Estou transferindo seu atendimento para nossa equipe especializada para que você receba o suporte adequado. Um momento, por favor! ✨"
            
            tool_calls_log.append({
                "name": tool_name,
                "args": json.dumps(tool_args, ensure_ascii=False),
                "output": tool_result
            })
            
            tool_calls_log.append({
                "name": "chatwoot:sincronizacao_etiquetas",
                "args": json.dumps({"is_human": True}, ensure_ascii=False),
                "output": handoff_result
            })
            
            detalhes_suporte = f"Destino: {destino}. Motivo: {motivo}."
            if handoff_result and isinstance(handoff_result, str) and "DETALHES:" in handoff_result:
                try:
                    partes = handoff_result.split("DETALHES: ")
                    if len(partes) > 1:
                        detalhes_etiquetas = partes[1].split(". INSTRUÇÃO")[0]
                        if detalhes_etiquetas and "Ação padrão" not in detalhes_etiquetas:
                            detalhes_suporte += f"\n🏷️ {detalhes_etiquetas}"
                except Exception as e_parse:
                    logger.warning(f"Erro ao parsear detalhes do handoff: {e_parse}")

            if on_step:
                on_step("🚑 Suporte Humano solicitado", detalhes_suporte)

            is_handoff_terminal = True
            break 

        # Execução de Webhooks/Internal Tools
        tool_result = "Erro: Ferramenta não encontrada."
        target_tool = next((t for t in tools if t.name == tool_name), None) if tools else None
        
        if tool_name == "internal_date_calculator":
            tool_result = await fn_date(json.dumps(tool_args))
        elif tool_name == "registrar_duvida_sem_resposta":
            tool_result = await fn_unanswered(db, context_variables, json.dumps(tool_args), history, config.id)
            if "AUTOMATICAMENTE TRANSFERIDO PARA O SUPORTE HUMANO" in str(tool_result):
                handoff_data = {"handoff": True, "destino": "humano", "motivo": f"Dúvida sem resposta acionada > 1 vez: {tool_args.get('pergunta')}"}
            
            # Opção B: Resposta Terminal via Micro-Prompt Ultraleve (gpt-4o-mini)
            # Evita o segundo turno pesado (~20.000 tokens) no modelo principal
            from .unanswered_micro_responder import generate_unanswered_micro_response
            
            unanswered_q = tool_args.get("pergunta", "")
            raw_user_msg = (context_variables or {}).get("raw_user_message")
            if not raw_user_msg:
                user_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
                if user_msgs:
                    raw_user_msg = user_msgs[-1].get("content", "")
                elif history:
                    u_h = [h for h in history if isinstance(h, dict) and h.get("role") == "user"]
                    if u_h:
                        raw_user_msg = u_h[-1].get("content", "")
            
            rag_ctx = (context_variables or {}).get("rag_context", "")
            
            micro_resp, micro_usage = await generate_unanswered_micro_response(
                user_message=str(raw_user_msg or unanswered_q),
                unanswered_question=unanswered_q,
                agent_config=config,
                tool_output=str(tool_result),
                rag_context=rag_ctx,
                on_step=on_step
            )
            
            if total_usage is not None:
                total_usage.mini_prompt += micro_usage.get("prompt_tokens", 0)
                total_usage.mini_completion += micro_usage.get("completion_tokens", 0)
            
            last_response = micro_resp
            is_handoff_terminal = True
            
            messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": tool_name, "content": tool_result})
            tool_calls_log.append({
                "name": tool_name,
                "args": json.dumps(tool_args, ensure_ascii=False),
                "output": tool_result
            })
            if on_step:
                on_step(f"✅ Ferramenta {tool_name} finalizada (Micro-Prompt terminal)", f"Retorno: {tool_result}")
            break
        elif tool_name == "google_calendar_manager":
            tool_result = await fn_calendar(db, context_variables, tool_args)
        elif tool_name == "lead_qualificado":
            tool_result = await fn_lead_qual(db, context_variables, json.dumps(tool_args), config.id, on_step=on_step)
        elif tool_name == "transferir_robo":
            tool_result = await fn_chatwoot(db, context_variables, target_tool, False, tool_args, history, config.id)
            tool_calls_log.append({
                "name": "chatwoot:sincronizacao_etiquetas",
                "args": json.dumps({"is_human": False}, ensure_ascii=False),
                "output": tool_result
            })
        elif target_tool:
            try:
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    res = await http_client.post(target_tool.webhook_url, json={**tool_args, **context_variables})
                    tool_result = res.text
            except Exception as e:
                logger.error(f"Erro na execução da ferramenta {tool_name}: {str(e)}")
                tool_result = (
                    "ERRO: A ferramenta encontrou uma instabilidade temporária. "
                    "INSTRUÇÃO PARA IA: Peça desculpas ao usuário de forma elegante, diga que houve uma instabilidade "
                    "passageira e peça para ele enviar a solicitação novamente em instantes. "
                    "NÃO EXIBA DETALHES TÉCNICOS DO ERRO."
                )
        
        is_tool_error = (
            isinstance(tool_result, str) and (
                tool_result.startswith("ERRO") 
                or tool_result.startswith("Erro") 
                or "instabilidade temporária" in tool_result.lower()
                or "instabilidade momentânea" in tool_result.lower()
            )
        )

        if is_tool_error:
            tool_failure_counts[tool_name] = tool_failure_counts.get(tool_name, 0) + 1
            if tool_failure_counts[tool_name] >= 2:
                openai_tools = [t for t in openai_tools if t.get("function", {}).get("name") != tool_name]
                tool_result += (
                    "\n\n⚠️ LIMITE DE TENTATIVAS ATINGIDO (2/2): Esta ferramenta falhou pela 2ª vez consecutiva e foi bloqueada. "
                    "NÃO tente chamá-la novamente. Peça desculpas educadamente ao cliente informando que houve uma instabilidade passageira no sistema "
                    "e continue a conversa normalmente."
                )
            else:
                tool_result += (
                    "\n\n⚠️ AVISO: Ocorreu uma instabilidade na execução. Você pode tentar chamá-la no máximo mais 1 única vez para testar. "
                    "Se falhar novamente, não tente mais e avise o cliente com simpatia sobre a instabilidade passageira."
                )
        else:
            if tool_name == "lead_qualificado":
                openai_tools = [t for t in openai_tools if t.get("function", {}).get("name") != "lead_qualificado"]

        if on_step and tool_name != "lead_qualificado":
            on_step(f"✅ Ferramenta {tool_name} finalizada", f"Retorno: {tool_result}")
        
        messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": tool_name, "content": tool_result})
        
        tool_calls_log.append({
            "name": tool_name,
            "args": json.dumps(tool_args, ensure_ascii=False),
            "output": tool_result
        })

    return is_handoff_terminal, handoff_data, last_response, openai_tools
