import json
import logging
import re
from datetime import datetime
from ...clients import get_openai_client

logger = logging.getLogger(__name__)

async def handle_date_calculator(func_args_str):
    try:
        func_args = json.loads(func_args_str)
        desc = func_args.get("date_description")
        mini_client = get_openai_client()
        now_str = datetime.now().strftime("%Y-%m-%d (%A)")
        mini_response = await mini_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Calcule a data exata. Hoje é {now_str}. Retorne: 'YYYY-MM-DD (Dia da Semana)'."},
                {"role": "user", "content": f"Qual a data de: {desc}?"}
            ],
            temperature=0.0
        )
        return mini_response.choices[0].message.content
    except Exception as e: return f"Erro ao calcular data: {str(e)}"

async def handle_unanswered_question(db, context_variables, func_args_str, history, agent_id):
    try:
        from models import UnansweredQuestionModel
        func_args = json.loads(func_args_str)
        question = func_args.get("pergunta")
        
        # ID original da sessão (do playground/chat) — antes de sobrescrever com o telefone
        original_session_id = context_variables.get("session_id") or ""
        
        # Prioriza o telefone real do contato se estiver disponível nas variáveis de contexto
        session_id = context_variables.get("contact_phone") or original_session_id or "Desconhecida"
        
        # Identificar a origem (se tem webhook_config_id, account_id ou conversation_id, veio de integração zapjords/chatwoot)
        is_integration = any(k in context_variables for k in ["webhook_config_id", "account_id", "conversation_id", "zapvoice_url", "zapjords"])
        source_val = "zapvoice" if is_integration else "chat"
        
        # Preservar o session_id original no contexto para rastreabilidade
        meta_line = f"SESSION_ID_ORIGINAL: {original_session_id}\n" if original_session_id and original_session_id != session_id else ""
        context_text = f"Sessão: {session_id}\n{meta_line}Histórico:\n" + "\n".join([f"{m.get('role')}: {m.get('content')}" for m in history[-5:]])
        
        new_q = UnansweredQuestionModel(
            agent_id=agent_id, 
            session_id=session_id, 
            question=question, 
            context=context_text, 
            status="PENDENTE",
            source=source_val
        )
        if db:
            db.add(new_q)
            await db.commit()
            await db.refresh(new_q)

            # Notifica o painel/inbox em tempo real via WebSocket
            try:
                from core.websocket import manager as ws_manager
                await ws_manager.broadcast({
                    "type": "unanswered_question_created",
                    "action": "create",
                    "question_id": new_q.id,
                    "agent_id": new_q.agent_id,
                    "question": new_q.question,
                    "session_id": new_q.session_id,
                    "status": new_q.status,
                    "source": new_q.source,
                    "created_at": new_q.created_at.isoformat() if getattr(new_q, "created_at", None) else None
                })
            except Exception as ws_err:
                logger.warning(f"Erro ao emitir broadcast de nova dúvida no inbox: {ws_err}")

            # Consultar configurações do agente (limite de dúvidas sem resposta e prompt customizado)
            handoff_limit = 2
            custom_resp_prompt = None
            if agent_id:
                from models import AgentConfigModel
                from sqlalchemy import select
                agent_stmt = select(
                    AgentConfigModel.unanswered_handoff_limit,
                    AgentConfigModel.unanswered_question_prompt
                ).where(AgentConfigModel.id == agent_id)
                agent_res = await db.execute(agent_stmt)
                agent_row = agent_res.first()
                if agent_row:
                    handoff_limit = agent_row.unanswered_handoff_limit
                    custom_resp_prompt = agent_row.unanswered_question_prompt

            from sqlalchemy import select, func
            count_stmt = select(func.count()).select_from(UnansweredQuestionModel).where(
                UnansweredQuestionModel.agent_id == agent_id,
                UnansweredQuestionModel.session_id == session_id
            )
            count_res = await db.execute(count_stmt)
            total_unanswered = count_res.scalar() or 0

            # Validação do transbordo humano:
            # Se handoff_limit for 0 ou None, o robô NUNCA transfere para suporte humano por dúvidas não respondidas.
            is_handoff_active = (handoff_limit is not None and handoff_limit > 0)
            if is_handoff_active and total_unanswered >= handoff_limit:
                from agent_core.tools.handlers.chatwoot import handle_chatwoot_handoff
                handoff_args = {"motivo": f"Dúvida sem resposta registrada {total_unanswered} vezes na mesma conversa: {question}"}
                await handle_chatwoot_handoff(db, context_variables, None, True, handoff_args, history, agent_id)
                return (
                    f"ATENÇÃO: O limite de {handoff_limit} dúvida(s) sem resposta foi atingido nesta conversa. "
                    "O atendimento foi AUTOMATICAMENTE TRANSFERIDO PARA O SUPORTE HUMANO. "
                    "INSTRUÇÃO OBRIGATÓRIA DE RESPOSTA: Responda APENAS sobre a pergunta feita nesta mensagem atual. "
                    "É TERMINANTEMENTE PROIBIDO re-responder perguntas que o usuário fez em turnos anteriores do histórico "
                    "ou ficar recapitulando/mencionando dúvidas passadas já tratadas. "
                    "Se e somente se o usuário fez mais de uma pergunta DENTRO DESTA MESMA MENSAGEM ATUAL e você já possui a resposta para alguma das outras perguntas no contexto RAG/Prompt, inclua essa resposta no texto final. "
                    "Ao final da mensagem, informe de forma educada que a dúvida ausente (ou o atendimento) foi direcionada para um especialista humano."
                )

            if custom_resp_prompt and custom_resp_prompt.strip():
                return (
                    f"Dúvida registrada com sucesso para a equipe. "
                    f"DIRETRIZ OBRIGATÓRIA DE RESPOSTA AO CLIENTE: {custom_resp_prompt.strip()} "
                    "ATENÇÃO CRÍTICA DE ESCOPO: Responda APENAS sobre a pergunta feita nesta mensagem atual. "
                    "É TERMINANTEMENTE PROIBIDO re-responder perguntas que o usuário fez em turnos anteriores do histórico (ex: quem é o professor, dados ou apresentações já respondidas) "
                    "e é ESTRITAMENTE PROIBIDO citar ou recapitular dúvidas passadas (ex: 'também já encaminhei sua dúvida anterior'). "
                    "Se e somente se o usuário fez mais de uma pergunta na MESMA mensagem atual e você souber responder alguma das outras pelo contexto/RAG, responda-a normalmente."
                )

            return "Dúvida registrada para nossa equipe."
        return "Erro: Sem conexão com banco."
    except Exception as e: return f"Erro ao registrar dúvida: {str(e)}"

async def handle_lead_qualified(db, context_variables, func_args_str, agent_id, on_step=None):
    try:
        from models import AgentConfigModel, WebhookConfigModel
        from zapvoice_utils import sync_conversation_labels
        from sqlalchemy import select
        
        func_args = json.loads(func_args_str)
        respostas = func_args.get("respostas", {})
        
        # 1. Print destacado no console do backend
        print("\n" + "="*80)
        print("🎯 LEAD QUALIFICADO IDENTIFICADO!")
        print(f"Agente ID: {agent_id}")
        print(f"Contato: {context_variables.get('contact_name')} ({context_variables.get('contact_phone')})")
        print("Respostas Coletadas:")
        print(json.dumps(respostas, ensure_ascii=False, indent=2))
        print("="*80 + "\n", flush=True)
        
        logger.info(f"Lead qualificado identificado para agente {agent_id}. Respostas: {json.dumps(respostas, ensure_ascii=False)}")
        
        leads_table = context_variables.get("leads_table")
        phone = context_variables.get("contact_phone")
        active_funnel_id = context_variables.get("active_qualification_funnel_id")
        
        agent = None
        wh = None
        to_add = []
        active_funnel = {}
        lead_score = 0
        lead_classification = "Indefinido"
        class_lower = "indefinido"
        allowed_triggers = ["all"]
        is_actually_qualified = True
        labels_to_apply = []
        to_remove = []
        
        if db:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import AsyncSession
            import inspect
            from agent_core.logic.qualification_prompt import resolve_active_qualification_funnel

            async def _safe_execute(stmt, params=None):
                res = db.execute(stmt, params) if params else db.execute(stmt)
                if inspect.isawaitable(res):
                    return await res
                return res

            # Buscar o agente para obter as configurações do funil ativo
            agent_res = await _safe_execute(select(AgentConfigModel).where(AgentConfigModel.id == agent_id))
            agent = agent_res.scalars().first()
            
            active_funnel = resolve_active_qualification_funnel(agent, active_funnel_id)
            trigger = active_funnel.get("final_action_trigger", "all") if isinstance(active_funnel, dict) else "all"
            if not isinstance(trigger, str):
                trigger = "all"
            trigger = trigger.strip() if trigger else "all"

            try:
                trigger_str = str(trigger).strip()
                if trigger_str.startswith("["):
                    allowed_triggers = [str(x).lower().strip() for x in json.loads(trigger_str)]
                else:
                    allowed_triggers = [x.lower().strip() for x in trigger_str.split(",") if x.strip()]
            except Exception:
                allowed_triggers = [str(trigger).lower().strip()]
            if not allowed_triggers:
                allowed_triggers = ["all"]
            
            raw_labels = active_funnel.get("labels") or []
            if isinstance(raw_labels, str):
                try:
                    to_add = json.loads(raw_labels)
                except Exception:
                    to_add = [l.strip() for l in raw_labels.split(",") if l.strip()]
            elif isinstance(raw_labels, list):
                to_add = [str(x).strip() for x in raw_labels if str(x).strip()]
            else:
                to_add = []
                
            # Buscar webhook para credenciais e ID da config
            wh_res = await _safe_execute(
                select(WebhookConfigModel)
                .where(WebhookConfigModel.agent_id == agent_id)
                .limit(1)
            )
            wh = wh_res.scalars().first()
            if not wh:
                wh_sec_res = await _safe_execute(
                    select(WebhookConfigModel)
                    .where(WebhookConfigModel.secondary_agent_ids.like(f"%{agent_id}%"))
                    .limit(1)
                )
                wh = wh_sec_res.scalars().first()
        
        # 2. Salvar no banco de dados na coluna respostas_qualificacao do lead correspondente
        if db and leads_table and phone:
            from sqlalchemy import text
            from lead_scoring_service import calculate_lead_score
            
            # Calcular o score e a classificação usando a IA com os critérios do funil ativo
            funnel_criteria = active_funnel.get("criteria")
            score_data = await calculate_lead_score(db, agent_id, respostas, criteria=funnel_criteria)
            lead_score = score_data.get("lead_score", 0)
            lead_classification = score_data.get("lead_classification", "Frio ❄️")
            lead_justification = score_data.get("lead_justification", "")
            
            respostas_str = json.dumps(respostas, ensure_ascii=False)

            # Avaliar condição de qualificação e gatilho de fechamento do funil ativo
            trigger = active_funnel.get("final_action_trigger", "all")
            if not isinstance(trigger, str):
                trigger = "all"
            trigger = trigger.strip() if trigger else "all"

            allowed_triggers = []
            try:
                trigger_str = str(trigger).strip()
                if trigger_str.startswith("["):
                    allowed_triggers = [str(x).lower().strip() for x in json.loads(trigger_str)]
                else:
                    allowed_triggers = [x.lower().strip() for x in trigger_str.split(",") if x.strip()]
            except Exception:
                allowed_triggers = [str(trigger).lower().strip()]

            class_lower = (lead_classification or "").strip().lower()
            is_cold_or_disqualified = "frio" in class_lower or "desqualificado" in class_lower

            # Só deve etiquetar esse lead caso ele se qualificar de fato:
            # - Se trigger for hot (Apenas Quente): deve ser quente e não frio
            # - Se trigger for warm (Apenas Morno): deve ser morno e não frio
            # - Se trigger for cold (Apenas Frio): deve ser frio
            # - Se trigger for hot_warm (Quente ou Morno): deve ser quente ou morno e não frio
            # - Se trigger for all (Todas as classificações): deve ser aprovado (não desqualificado/frio)
            if any(k in allowed_triggers for k in ("hot", "quente")):
                is_actually_qualified = ("quente" in class_lower) and not is_cold_or_disqualified
            elif any(k in allowed_triggers for k in ("warm", "morno")):
                is_actually_qualified = ("morno" in class_lower) and not is_cold_or_disqualified
            elif any(k in allowed_triggers for k in ("cold", "frio")):
                is_actually_qualified = is_cold_or_disqualified
            elif "hot_warm" in allowed_triggers:
                is_actually_qualified = ("quente" in class_lower or "morno" in class_lower) and not is_cold_or_disqualified
            else:  # "all", "todas", "sempre"
                is_actually_qualified = not is_cold_or_disqualified

            # Etiquetas que serão adicionadas se o lead qualificou de fato
            if is_actually_qualified:
                labels_to_apply = [x for x in to_add if x]
                logger.info(f"Lead {phone} QUALIFICADO de fato ({lead_classification}). Etiquetas a aplicar: {labels_to_apply}")
            else:
                labels_to_apply = []
                logger.info(f"Lead {phone} NÃO qualificado de fato ({lead_classification}). Nenhuma etiqueta de qualificação será aplicada.")

            # Etiquetas a remover no ZapVoice (respeita apenas o configurado no funil ou desqualificação)
            to_remove = []
            raw_labels_remove = active_funnel.get("labels_to_remove") or [] if isinstance(active_funnel, dict) else []
            if isinstance(raw_labels_remove, str):
                try:
                    to_remove = json.loads(raw_labels_remove)
                except Exception:
                    to_remove = [l.strip() for l in raw_labels_remove.split(",") if l.strip()]
            elif isinstance(raw_labels_remove, list):
                to_remove = [str(x).strip() for x in raw_labels_remove if str(x).strip()]
            else:
                to_remove = []

            if not is_actually_qualified:
                for item in to_add:
                    if item not in to_remove:
                        to_remove.append(item)
            
            # Buscar lead existente para ler etiquetas atuais e evitar sobrescrever labels já aplicadas
            existing_labels = []
            try:
                lead_query = f"SELECT labels, respostas_qualificacao FROM {leads_table} WHERE telefone = :phone"
                lead_res = await _safe_execute(text(lead_query), {"phone": phone})
                lead_row = lead_res.fetchone()
                if lead_row:
                    if lead_row[1] and str(lead_row[1]).strip():
                        logger.info(f"Lead com telefone {phone} já qualificado anteriormente. Ignorando chamada repetida de lead_qualificado.")
                        if on_step:
                            try:
                                on_step(
                                    "🎯 Lead Qualificado (Finalização do Funil)",
                                    f"ℹ️ **Contato já qualificado anteriormente.**\n\nAs respostas coletadas já haviam sido registradas no banco para o telefone `{phone}`.",
                                    metadata={"already_qualified": True}
                                )
                            except TypeError:
                                on_step(
                                    "🎯 Lead Qualificado (Finalização do Funil)",
                                    f"ℹ️ **Contato já qualificado anteriormente.**\n\nAs respostas coletadas já haviam sido registradas no banco para o telefone `{phone}`."
                                )
                        return "Lead já qualificado anteriormente. Nenhuma ação necessária."
                    if lead_row[0]:
                        raw_labels = lead_row[0]
                        try:
                            parsed = json.loads(raw_labels)
                            if isinstance(parsed, list):
                                existing_labels = [str(x) for x in parsed]
                            else:
                                existing_labels = [str(raw_labels)]
                        except Exception:
                            existing_labels = [x.strip() for x in raw_labels.split(",") if x.strip()]
            except Exception as e_read_labels:
                logger.error(f"Erro ao ler etiquetas existentes do lead: {e_read_labels}")
            
            # Montar etiquetas finais locais:
            # - Remove 'qualificado' legado se não estiver no dropdown to_add
            # - Se não qualificou de fato, remove as etiquetas de qualificação do dropdown caso existam
            final_labels = []
            for lbl in existing_labels:
                if lbl.strip().lower() == "qualificado" and "qualificado" not in to_add:
                    continue
                if not is_actually_qualified and lbl in to_add:
                    continue
                if lbl not in final_labels:
                    final_labels.append(lbl)

            for item in labels_to_apply:
                if item not in final_labels:
                    final_labels.append(item)
            
            final_labels_json = json.dumps(final_labels, ensure_ascii=False)
            
            # Tentar fazer o UPDATE primeiro
            update_query = f"""
                UPDATE {leads_table} SET 
                    respostas_qualificacao = :respostas,
                    lead_score = :lead_score,
                    lead_classification = :lead_classification,
                    lead_justification = :lead_justification,
                    qualified_by_agent_id = :qualified_by_agent_id,
                    labels = :labels,
                    updated_at = CURRENT_TIMESTAMP
                WHERE telefone = :phone
            """
            result = await _safe_execute(text(update_query), {
                "respostas": respostas_str,
                "phone": phone,
                "labels": final_labels_json,
                "lead_score": lead_score,
                "lead_classification": lead_classification,
                "lead_justification": lead_justification,
                "qualified_by_agent_id": agent_id
            })
            
            # Se nenhuma linha foi atualizada (rowcount é 0 ou None), criamos o lead
            if result is None or getattr(result, "rowcount", 0) == 0:
                logger.info(f"Lead com telefone {phone} não encontrado na tabela {leads_table}. Criando novo lead...")
                
                # Campos extras
                conta_id = context_variables.get("account_id") or context_variables.get("conta_id")
                inbox_id = context_variables.get("inbox_id")
                inbox_nome = context_variables.get("inbox_nome")
                conversa_id = context_variables.get("conversation_id") or context_variables.get("conversa_id")
                mensagem_id = context_variables.get("mensagem_id")
                contato_id = context_variables.get("contact_id") or context_variables.get("contato_id")
                contato_nome = context_variables.get("contact_name") or context_variables.get("contato_nome")
                
                insert_query = f"""
                    INSERT INTO {leads_table} (
                        webhook_config_id, qualified_by_agent_id, conta_id, inbox_id, inbox_nome, conversa_id,
                        mensagem_id, contato_id, telefone, labels, contato_nome,
                        respostas_qualificacao, lead_score, lead_classification, lead_justification,
                        pode_enviar_mensagem, updated_at, created_at
                    ) VALUES (
                        :webhook_config_id, :qualified_by_agent_id, :conta_id, :inbox_id, :inbox_nome, :conversa_id,
                        :mensagem_id, :contato_id, :telefone, :labels, :contato_nome,
                        :respostas, :lead_score, :lead_classification, :lead_justification,
                        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """
                await _safe_execute(text(insert_query), {
                    "webhook_config_id": wh.id if wh else None,
                    "qualified_by_agent_id": agent_id,
                    "conta_id": str(conta_id) if conta_id is not None else None,
                    "inbox_id": str(inbox_id) if inbox_id is not None else None,
                    "inbox_nome": str(inbox_nome) if inbox_nome is not None else None,
                    "conversa_id": str(conversa_id) if conversa_id is not None else None,
                    "mensagem_id": str(mensagem_id) if mensagem_id is not None else None,
                    "contato_id": str(contato_id) if contato_id is not None else None,
                    "telefone": phone,
                    "labels": final_labels_json,
                    "contato_nome": contato_nome,
                    "respostas": respostas_str,
                    "lead_score": lead_score,
                    "lead_classification": lead_classification,
                    "lead_justification": lead_justification
                })
                
            await db.commit()
            logger.info(f"Respostas de qualificação e Lead Score processados com sucesso na tabela {leads_table} para o telefone {phone}")
            
        # 3. Adicionar as etiquetas no ZapVoice (Chat)
        zv_url = None
        api_token = None
        account_id = context_variables.get("account_id") or context_variables.get("conta_id")
        conversation_id = context_variables.get("conversation_id") or context_variables.get("conversa_id")

        if db:
            import os
            if wh and wh.zapvoice_url and wh.zapvoice_api_token:
                zv_url = wh.zapvoice_url.rstrip("/")
                api_token = wh.zapvoice_api_token
            else:
                zv_url = os.getenv("ZAPVOICE_URL")
                api_token = os.getenv("ZAPVOICE_API_TOKEN")
                if zv_url:
                    zv_url = zv_url.rstrip("/")
                if not account_id:
                    account_id = os.getenv("ZAPVOICE_CLIENT_ID") or os.getenv("CHATWOOT_ACCOUNT_ID")
            
            # Tentar recuperar account_id no banco com o último evento se ainda for nulo
            if not account_id and wh:
                from models import WebhookEventModel
                evt_result = await _safe_execute(
                    select(WebhookEventModel.conta_id)
                    .where(WebhookEventModel.webhook_config_id == wh.id)
                    .where(WebhookEventModel.conta_id.isnot(None))
                    .order_by(WebhookEventModel.created_at.desc())
                    .limit(1)
                )
                db_account_id = evt_result.scalar()
                if db_account_id:
                    account_id = db_account_id

        # 4. Avaliar condição de disparo da Pergunta / Ação Final (qualification_final_action_trigger)
        should_trigger_closing = False
        lead_classification_str = (lead_classification or "").strip()
        funnel_final_action = active_funnel.get("final_action") if 'active_funnel' in locals() and active_funnel else (getattr(agent, 'qualification_final_action', None) if agent else None)

        if funnel_final_action and str(funnel_final_action).strip():
            if "all" in allowed_triggers or "sempre" in allowed_triggers or "todas" in allowed_triggers:
                should_trigger_closing = True
            elif any(k in allowed_triggers for k in ("hot", "quente")) and "quente" in class_lower:
                should_trigger_closing = True
            elif any(k in allowed_triggers for k in ("warm", "morno")) and "morno" in class_lower:
                should_trigger_closing = True
            elif any(k in allowed_triggers for k in ("cold", "frio")) and "frio" in class_lower:
                should_trigger_closing = True
            elif "hot_warm" in allowed_triggers and ("quente" in class_lower or "morno" in class_lower):
                should_trigger_closing = True

        proibicao_termos = (
            "🚫 SIGILO ABSOLUTO (NUNCA MENCIONE QUALIFICAÇÃO): É expressamente proibido dizer ao cliente frases como 'você está qualificado para prosseguir', 'seus dados foram aprovados' ou usar termos técnicos como 'qualificação', 'etiquetas' ou 'score'. Apenas agradeça as informações fornecidas e prossiga de forma humana e acolhedora."
        )

        if should_trigger_closing and funnel_final_action:
            instruction_closing = (
                f"\n\n🚨 [INSTRUÇÃO OBRIGATÓRIA DE RESPOSTA - QUALIFICAÇÃO CONCLUÍDA]:\n"
                f"O lead concluiu a qualificação e a ferramenta 'lead_qualificado' foi executada com sucesso!\n"
                f"Sua resposta final ao usuário DEVE cumprir RIGOROSAMENTE as regras abaixo:\n"
                f"1. Agradeça calorosamente pelos dados fornecidos pelo lead (ex: pelo e-mail/nome). {proibicao_termos}\n"
                f"2. SE o usuário fez alguma dúvida nesta mesma mensagem, responda com clareza antes de concluir.\n"
                f"3. 🚨 PERGUNTA DE FECHAMENTO OBRIGATÓRIA: Você DEVE concluir a mensagem formulando a pergunta de fechamento baseada EXCLUSIVAMENTE nesta diretriz: '{str(funnel_final_action).strip()}'.\n"
                f"   - Esta pergunta de fechamento é OBRIGATÓRIA e SUBSTITUI qualquer pergunta genérica como 'Posso ajudar com mais alguma dúvida?' de <Primeira_Resposta> ou regras que dizem para não perguntar no final.\n"
                f"   - ⚠️ REGRA DE DOIS PASSOS (NUNCA ENVIE O LINK ANTES DO 'SIM'): Como a diretriz pede para perguntar se pode enviar o link (ex: 'Pergunte se eu posso enviar o link do curso...'), você DEVE FAZER APENAS A PERGUNTA nesta resposta! NÃO envie o link, URL ou checkout agora. O link informado na diretriz servirá apenas para o próximo turno após o usuário confirmar que quer receber o link."
            )
        else:
            instruction_closing = (
                f"\n\n[INSTRUÇÃO DE RESPOSTA - QUALIFICAÇÃO CONCLUÍDA]:\n"
                f"1. Agradeça calorosamente pelos dados fornecidos. {proibicao_termos}\n"
                f"2. SE o usuário fez alguma dúvida nesta mensagem, responda antes de concluir.\n"
                f"3. Conclua com simpatia e cordialidade deixando nossa equipe à disposição para qualquer dúvida futura (NÃO faça oferta de fechamento nem envie link de checkout)."
            )

        if not (db and leads_table and phone) and to_add and not labels_to_apply:
            labels_to_apply = [x for x in to_add if x]

        # Montar diagnóstico detalhado da etapa para o pipeline
        funnel_name = active_funnel.get("name", "Padrão / Principal") if isinstance(active_funnel, dict) else "Padrão / Principal"
        funnel_id_str = active_funnel.get("id", "funnel_default") if isinstance(active_funnel, dict) else "funnel_default"

        if is_actually_qualified:
            if labels_to_apply:
                labels_str = ", ".join([f"`{lbl}`" for lbl in labels_to_apply])
                status_labels = f"• **Etiquetas Aplicadas no Contato:** {labels_str}"
            else:
                status_labels = "• **Etiquetas Aplicadas no Contato:** Nenhuma etiqueta configurada para este funil."
        else:
            status_labels = f"• **Etiquetas de Qualificação:** Nenhuma etiqueta aplicada (o contato foi avaliado como {lead_classification} e não atingiu a condição de qualificação do funil)."

        if to_remove:
            removidas_str = ", ".join([f"`{lbl}`" for lbl in to_remove])
            status_labels += f"\n• **Etiquetas Removidas (Higienização):** {removidas_str}"

        respostas_text = ""
        if respostas and isinstance(respostas, dict):
            respostas_itens = "\n".join([f"  - **{k}:** {v}" for k, v in respostas.items()])
            respostas_text = f"\n\n📋 **Dados Coletados nas Etapas:**\n{respostas_itens}"

        score_display = f" (Score: {lead_score}/100)" if lead_score is not None else ""
        step_detail = (
            f"🎯 **Finalização do Funil de Qualificação**\n\n"
            f"• **Funil Ativo:** {funnel_name} (`{funnel_id_str}`)\n"
            f"• **Classificação do Lead:** {lead_classification}{score_display}\n"
            f"{status_labels}"
            f"{respostas_text}"
        )

        step_metadata = {
            "labels_applied": labels_to_apply if is_actually_qualified else [],
            "labels_removed": to_remove,
            "lead_classification": lead_classification,
            "lead_score": lead_score,
            "funnel_id": funnel_id_str,
            "funnel_name": funnel_name
        }

        if on_step:
            try:
                on_step("🎯 Lead Qualificado (Finalização do Funil)", step_detail, metadata=step_metadata)
            except TypeError:
                on_step("🎯 Lead Qualificado (Finalização do Funil)", step_detail)

        if zv_url and api_token and account_id and conversation_id:
            try:
                conv_id_num = int(conversation_id) if str(conversation_id).isdigit() else 0
                if conv_id_num > 0:
                    if labels_to_apply or to_remove:
                        await sync_conversation_labels(
                            zapvoice_url=zv_url,
                            client_id=str(account_id),
                            conversation_id=conv_id_num,
                            token=api_token,
                            to_add=labels_to_apply,
                            to_remove=to_remove
                        )
            except Exception as e_sync:
                logger.error(f"Erro ao sincronizar etiquetas no ZapVoice: {e_sync}")
        
        if is_actually_qualified:
            # Persistir estado de lead já qualificado no contexto e na memória da sessão
            if context_variables:
                context_variables["lead_already_qualified"] = True
            
            sid = context_variables.get("session_id") if context_variables else None
            if db and sid:
                try:
                    from models import UserMemoryModel
                    from sqlalchemy.ext.asyncio import AsyncSession
                    import inspect
                    stmt_qm = select(UserMemoryModel).where(
                        UserMemoryModel.session_id == str(sid),
                        UserMemoryModel.key == "lead_already_qualified"
                    )
                    res_raw = db.execute(stmt_qm)
                    res_qm = await res_raw if inspect.isawaitable(res_raw) else res_raw
                    if hasattr(res_qm, "scalars") and not res_qm.scalars().first():
                        db.add(UserMemoryModel(
                            session_id=str(sid),
                            key="lead_already_qualified",
                            value="True",
                            source_message="lead_qualificado"
                        ))
                        commit_raw = db.commit()
                        if inspect.isawaitable(commit_raw):
                            await commit_raw
                except Exception as e_qm:
                    logger.warning(f"Erro ao salvar flag de qualificação em UserMemoryModel: {e_qm}")

            if labels_to_apply:
                return f"Operação 'lead_qualificado' concluída com sucesso no sistema interno. Etiquetas sincronizadas: {', '.join(labels_to_apply)}.{instruction_closing}"
            return f"Operação 'lead_qualificado' concluída com sucesso no sistema interno.{instruction_closing}"
        else:
            return f"Operação 'lead_qualificado' concluída no sistema interno (classificação: {lead_classification}). Nenhuma etiqueta de qualificação aplicada.{instruction_closing}"
            
    except Exception as e:
        logger.error(f"Erro ao processar lead qualificado: {e}")
        return (
            f"ERRO: Instabilidade temporária ao processar registro de qualificação ({str(e)}). "
            "INSTRUÇÃO: Se esta for a primeira tentativa com erro, tente no máximo mais 1 única vez. "
            "Se persistir ou falhar novamente, NÃO chame a ferramenta novamente. Peça desculpas ao cliente "
            "com gentileza informando que houve uma instabilidade momentânea no sistema e continue o atendimento naturalmente."
        )


async def check_and_apply_qualification_fallback(db, context_variables, config, history, message, tool_calls_log, last_response="", on_step=None):
    """
    Garante que as etiquetas, o status de qualificação e a pergunta de fechamento sejam aplicados
    caso o modelo LLM apenas gere o texto final esquecendo de emitir o tool_call 'lead_qualificado'.
    """
    if any(tc.get("name") == "lead_qualificado" for tc in tool_calls_log):
        return last_response
        
    qq = getattr(config, "qualification_questions", None)
    if not qq:
        return last_response
        
    try:
        last_asst = ""
        if history:
            for h in reversed(history):
                r = h.get("role") if isinstance(h, dict) else getattr(h, "role", "")
                if r == "assistant":
                    last_asst = (h.get("content") if isinstance(h, dict) else getattr(h, "content", "")).lower()
                    break
                    
        # Se a última pergunta do assistente foi sobre e-mail e o usuário forneceu um e-mail válido
        is_email_answer = ("email" in last_asst or "e-mail" in last_asst) and ("@" in message and "." in message)
        
        if is_email_answer:
            respostas_payload = {"email": message.strip()}
            c_name = context_variables.get("contact_name") if context_variables else None
            if c_name:
                respostas_payload["nome"] = c_name
            res_str = await handle_lead_qualified(
                db, 
                context_variables, 
                json.dumps({"respostas": respostas_payload, "origem": "auto_completion"}), 
                config.id,
                on_step=on_step
            )
            tool_calls_log.append({
                "name": "lead_qualificado",
                "args": json.dumps({**respostas_payload, "auto_completed": True}, ensure_ascii=False),
                "output": res_str
            })

            # Atualizar last_response se a pergunta final de fechamento estiver ausente
            from ...logic.qualification_prompt import resolve_active_qualification_funnel
            active_funnel_id = context_variables.get("active_qualification_funnel_id") if context_variables else None
            active_funnel = resolve_active_qualification_funnel(config, active_funnel_id)
            final_action = active_funnel.get("final_action") or getattr(config, "qualification_final_action", None)
            
            if final_action and str(final_action).strip():
                final_action_str = str(final_action).strip()
                closing_q = ""
                first_line = final_action_str.split("\n")[0].strip()
                if "?" in first_line:
                    closing_q = first_line
                elif "pergunte se" in first_line.lower() or "pergunte se" in final_action_str.lower():
                    closing_q = "Posso enviar o link do curso para você?"
                elif "link" in final_action_str.lower():
                    closing_q = "Posso te enviar o link com mais detalhes?"
                else:
                    closing_q = first_line

                if closing_q:
                    clean_response = last_response or ""
                    generic_patterns = [
                        r"Se (tiver|houver|precisar|restar).*dúvida.*",
                        r"Qualquer dúvida.*",
                        r"Se precisar de algo mais.*",
                        r"Estou à disposição.*",
                        r"Fico à disposição.*",
                        r"Posso ajudar.*dúvida.*",
                    ]
                    for pat in generic_patterns:
                        clean_response = re.sub(pat, "", clean_response, flags=re.IGNORECASE).strip()
                    
                    if closing_q.lower() not in clean_response.lower():
                        if clean_response:
                            last_response = f"{clean_response}\n\n{closing_q}"
                        else:
                            name_part = f", {c_name}" if c_name else ""
                            last_response = f"Muito obrigado pelas informações{name_part}!\n\n{closing_q}"
    except Exception as err:
        logger.warning(f"Erro no fallback de lead_qualificado: {err}")

    return last_response


