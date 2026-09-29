import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from models import UnansweredQuestionModel, KnowledgeBaseModel, KnowledgeItemModel, AgentConfigModel
from api.deps import get_db, verify_api_key
from rag_service import get_embedding

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Inbox"])

@router.get("/unanswered-questions")
async def list_unanswered_questions(
    status: str = Query("PENDENTE"),
    agent_id: Optional[int] = Query(None),
    phone: Optional[str] = Query(None),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    try:
        from sqlalchemy import and_, or_
        from datetime import time

        # Monta filtros base
        conditions = [UnansweredQuestionModel.status == status]

        if agent_id and isinstance(agent_id, int):
            conditions.append(UnansweredQuestionModel.agent_id == agent_id)

        if source and isinstance(source, str):
            source_lower = source.strip().lower()
            if source_lower == "chat":
                conditions.append(or_(
                    UnansweredQuestionModel.source == "chat",
                    UnansweredQuestionModel.source.is_(None)
                ))
            elif source_lower in ["zapvoice", "zapjords", "chatwoot"]:
                conditions.append(UnansweredQuestionModel.source.in_(["zapvoice", "zapjords", "chatwoot"]))
            else:
                conditions.append(UnansweredQuestionModel.source == source)

        if date_start and isinstance(date_start, str):
            try:
                start_dt = datetime.fromisoformat(date_start.replace("Z", "+00:00"))
                if len(date_start) <= 10:
                    start_dt = datetime.combine(start_dt.date(), time.min).replace(tzinfo=timezone.utc)
                conditions.append(UnansweredQuestionModel.created_at >= start_dt)
            except Exception as e_ds:
                logger.warning(f"Data inicial inválida: {date_start} - {e_ds}")

        if date_end and isinstance(date_end, str):
            try:
                end_dt = datetime.fromisoformat(date_end.replace("Z", "+00:00"))
                if len(date_end) <= 10:
                    end_dt = datetime.combine(end_dt.date(), time.max).replace(tzinfo=timezone.utc)
                conditions.append(UnansweredQuestionModel.created_at <= end_dt)
            except Exception as e_de:
                logger.warning(f"Data final inválida: {date_end} - {e_de}")

        # Se houver busca por telefone, encontrar session_ids correspondentes
        if phone and isinstance(phone, str) and phone.strip():
            clean_search = phone.strip()
            digits_only = "".join(filter(str.isdigit, clean_search))
            phone_patterns = [f"%{clean_search}%"]
            if digits_only and digits_only != clean_search:
                phone_patterns.append(f"%{digits_only}%")

            # Buscar possíveis IDs de leads e telefones vinculados
            matched_sessions = set()
            from models import WebhookEventModel
            from sqlalchemy import text

            # 1. Busca direta na tabela padrão de leads
            try:
                lead_query = select(text("id, telefone")).select_from(text("leads")).where(
                    or_(*[text(f"telefone LIKE '{p}'") for p in phone_patterns])
                )
                l_res = await db.execute(lead_query)
                for row in l_res.all():
                    if row[0]:
                        matched_sessions.add(str(row[0]))
                    if row[1]:
                        matched_sessions.add(str(row[1]))
            except Exception:
                pass

            # 2. Busca em webhook_events
            try:
                ev_res = await db.execute(
                    select(WebhookEventModel.contato_id, WebhookEventModel.telefone)
                    .where(or_(*[WebhookEventModel.telefone.like(p) for p in phone_patterns]))
                    .limit(100)
                )
                for c_id, t_num in ev_res.all():
                    if c_id:
                        matched_sessions.add(str(c_id))
                    if t_num:
                        matched_sessions.add(str(t_num))
            except Exception:
                pass

            # Cria cláusula OR para session_id ou context contendo o telefone
            session_match_conds = [
                UnansweredQuestionModel.session_id.like(f"%{clean_search}%"),
                UnansweredQuestionModel.context.like(f"%{clean_search}%")
            ]
            if digits_only and digits_only != clean_search:
                session_match_conds.append(UnansweredQuestionModel.session_id.like(f"%{digits_only}%"))
                session_match_conds.append(UnansweredQuestionModel.context.like(f"%{digits_only}%"))
            for ms in matched_sessions:
                session_match_conds.append(UnansweredQuestionModel.session_id == ms)
                session_match_conds.append(UnansweredQuestionModel.session_id == f"tel_{ms}")

            conditions.append(or_(*session_match_conds))

        # Conta o total de registros com os filtros
        count_stmt = (
            select(func.count())
            .select_from(UnansweredQuestionModel)
            .where(and_(*conditions))
        )
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Seleciona os registros paginados
        result = await db.execute(
            select(UnansweredQuestionModel)
            .where(and_(*conditions))
            .order_by(UnansweredQuestionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = result.scalars().all()

        # Enriquecer os registros decodificando o session_id numérico ou com tel_ para telefone real
        from models import WebhookEventModel, WebhookConfigModel
        from sqlalchemy import text
        enriched_items = []
        for q in items:
            phone = q.session_id
            if q.session_id:
                if q.session_id.startswith("tel_"):
                    phone = q.session_id[4:]
                elif q.session_id.isdigit():
                    # 1. Tenta buscar pelo ID do Lead na tabela 'leads' padrão
                    try:
                        lead_res = await db.execute(
                            text("SELECT telefone FROM leads WHERE id = :lid"),
                            {"lid": int(q.session_id)}
                        )
                        db_phone = lead_res.scalar()
                        if db_phone:
                            phone = db_phone
                    except Exception:
                        pass
                    
                    # 2. Se não encontrou na 'leads' padrão, tenta buscar pelas tabelas dos webhooks associados ao agente
                    if phone == q.session_id:
                        try:
                            wh_res = await db.execute(
                                select(WebhookConfigModel.leads_table)
                                .where(WebhookConfigModel.agent_id == q.agent_id)
                            )
                            tables = set(wh_res.scalars().all())
                            for table in tables:
                                if table and table != "leads":
                                    try:
                                        lead_res = await db.execute(
                                            text(f"SELECT telefone FROM {table} WHERE id = :lid"),
                                            {"lid": int(q.session_id)}
                                        )
                                        db_phone = lead_res.scalar()
                                        if db_phone:
                                            phone = db_phone
                                            break
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                    # 3. Fallback original: se ainda for o ID, tenta buscar por contato_id em webhook_events
                    if phone == q.session_id:
                        event_result = await db.execute(
                            select(WebhookEventModel.telefone)
                            .where(WebhookEventModel.contato_id == q.session_id)
                            .order_by(WebhookEventModel.created_at.desc())
                            .limit(1)
                        )
                        db_phone = event_result.scalar()
                        if db_phone:
                            phone = db_phone


            # Extrair SESSION_ID_ORIGINAL do contexto, se existir (salvo pelo handler de dúvidas)
            chat_session_id = None
            if q.context:
                for line in q.context.splitlines():
                    if line.startswith("SESSION_ID_ORIGINAL:"):
                        raw_val = line.replace("SESSION_ID_ORIGINAL:", "").strip()
                        if raw_val:
                            chat_session_id = raw_val
                        break

            # Buscar nome do agente se disponível
            agent_name = None
            if q.agent_id:
                try:
                    a_row = await db.get(AgentConfigModel, q.agent_id)
                    if a_row:
                        agent_name = a_row.name
                except Exception:
                    pass

            enriched_items.append({
                "id": q.id,
                "agent_id": q.agent_id,
                "agent_name": agent_name or (f"Agente #{q.agent_id}" if q.agent_id else "Geral"),
                "session_id": phone or q.session_id,
                "session_id_raw": q.session_id,
                "chat_session_id": chat_session_id,
                "question": q.question,
                "context": q.context,
                "status": q.status,
                "source": q.source,
                "created_at": q.created_at.isoformat() if q.created_at else None,
                "updated_at": q.updated_at.isoformat() if q.updated_at else None
            })


        return {"success": True, "items": enriched_items, "total": total}
    except Exception as e:
        logger.error(f"Erro ao listar dúvidas: {e}")
        return {"success": False, "items": [], "total": 0, "error": str(e)}

@router.post("/unanswered-questions/{question_id}/answer")
async def answer_question(
    question_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Responde uma dúvida e adiciona à base de conhecimento (RAG)."""
    q = await db.get(UnansweredQuestionModel, question_id)
    if not q: raise HTTPException(status_code=404, detail="Dúvida não encontrada")
    
    knowledge_base_id = payload.get("knowledge_base_id")
    answer = payload.get("answer")
    question_text = payload.get("question") or q.question
    
    if not knowledge_base_id or not answer:
        raise HTTPException(status_code=400, detail="ID da Base e Resposta são obrigatórios")
        
    # Adicionar ao RAG
    emb, _ = await get_embedding(question_text)
    new_item = KnowledgeItemModel(
        knowledge_base_id=knowledge_base_id,
        question=question_text,
        answer=answer,
        category="Inbox",
        embedding=emb
    )
    db.add(new_item)
    
    # Marcar como respondida
    q.status = "RESPONDIDA"
    await db.commit()

    try:
        from core.websocket import manager as ws_manager
        await ws_manager.broadcast({
            "type": "unanswered_question_updated",
            "action": "answer",
            "question_id": q.id,
            "status": "RESPONDIDA"
        })
    except Exception as ws_err:
        logger.warning(f"Erro ao emitir broadcast de dúvida respondida: {ws_err}")

    return {"success": True}

@router.post("/unanswered-questions/{question_id}/answer-as-variation")
async def answer_question_as_variation(
    question_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Responde uma dúvida vinculando-a como uma nova variação de pergunta em um item existente da Base (RAG)."""
    q = await db.get(UnansweredQuestionModel, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Dúvida não encontrada")
    
    knowledge_item_id = payload.get("knowledge_item_id")
    variation = (payload.get("variation") or payload.get("question") or q.question or "").strip()
    
    if not knowledge_item_id:
        raise HTTPException(status_code=400, detail="O ID da pergunta existente (knowledge_item_id) é obrigatório.")
    if not variation:
        raise HTTPException(status_code=400, detail="O texto da nova variação não pode ficar vazio.")
        
    item_res = await db.execute(select(KnowledgeItemModel).where(KnowledgeItemModel.id == int(knowledge_item_id)))
    db_item = item_res.scalars().first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Pergunta existente da base de conhecimento não encontrada.")

    from api.services.knowledge_service import process_variation_addition, get_item_embedding_text, clean_variations_list
    from sqlalchemy.orm.attributes import flag_modified

    try:
        updated_vars, added = process_variation_addition(
            db_item.question_variations,
            variation,
            None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar variação para item {knowledge_item_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    if added:
        text_to_embed = get_item_embedding_text(db_item.question, updated_vars)
        try:
            emb, _ = await get_embedding(text_to_embed)
            db_item.embedding = emb
        except Exception as e:
            logger.warning(f"Falha ao recalcular embedding para item {db_item.id}: {e}")
        
        db_item.question_variations = list(updated_vars)
        flag_modified(db_item, "question_variations")

    # Marca a dúvida do Inbox como RESPONDIDA
    q.status = "RESPONDIDA"
    await db.commit()
    await db.refresh(db_item)

    try:
        from core.websocket import manager as ws_manager
        await ws_manager.broadcast({
            "type": "unanswered_question_updated",
            "action": "answer",
            "question_id": q.id,
            "status": "RESPONDIDA"
        })
    except Exception as ws_err:
        logger.warning(f"Erro ao emitir broadcast de dúvida respondida como variação: {ws_err}")

    return {
        "success": True,
        "message": "Variação adicionada com sucesso!",
        "item_id": db_item.id,
        "question_variations": clean_variations_list(db_item.question_variations),
        "added": added
    }

@router.post("/unanswered-questions/{question_id}/answer-to-prompt")
async def answer_to_prompt(
    question_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Responde uma dúvida adicionando a instrução diretamente ao Prompt do Agente."""
    q = await db.get(UnansweredQuestionModel, question_id)
    if not q: raise HTTPException(status_code=404, detail="Dúvida não encontrada")
    
    agent_id = payload.get("agent_id")
    instruction = payload.get("instruction") or payload.get("answer") # Aceita ambos para compatibilidade
    
    if not agent_id or not instruction:
        logger.warning(f"Tentativa de salvar resposta no prompt falhou: agent_id={agent_id}, instruction_len={len(instruction) if instruction else 0}")
        raise HTTPException(status_code=400, detail="Agent ID e Instrução são obrigatórios")
        
    agent = await db.get(AgentConfigModel, agent_id)
    if not agent: raise HTTPException(status_code=404, detail="Agente não encontrado")

    question_text = payload.get("question") or q.question
    
    # Formata a instrução com Pergunta e Resposta pulando uma linha entre elas
    formatted_instruction = f"Pergunta: {question_text}\n\nResposta: {instruction}"
    
    # Contar quantas instruções do Inbox já existem
    count = agent.system_prompt.count("# INSTRUÇÃO ADICIONAL (Inbox):")
    
    # Adicionar ao final do System Prompt
    agent.system_prompt += f"\n\n# INSTRUÇÃO ADICIONAL (Inbox):\n{formatted_instruction}"
    
    # Marcar como respondida
    q.status = "RESPONDIDA"
    await db.commit()

    try:
        from core.websocket import manager as ws_manager
        await ws_manager.broadcast({
            "type": "unanswered_question_updated",
            "action": "answer",
            "question_id": q.id,
            "status": "RESPONDIDA"
        })
    except Exception as ws_err:
        logger.warning(f"Erro ao emitir broadcast de dúvida respondida no prompt: {ws_err}")
    
    warning = None
    if count >= 30:
        warning = f"Aviso: Este agente já possui {count + 1} instruções ensinadas via Inbox. Para melhor performance e economia, considere mover algumas informações para a Base de Conhecimento (RAG)."
        logger.warning(f"Limite de instruções do Inbox atingido para o agente {agent_id}: {count + 1} itens.")

    return {"success": True, "warning": warning}

@router.post("/unanswered-questions/{question_id}/discard")
async def discard_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Descarta uma dúvida sem responder."""
    q = await db.get(UnansweredQuestionModel, question_id)
    if not q: raise HTTPException(status_code=404, detail="Dúvida não encontrada")
    
    q.status = "DESCARTADA"
    await db.commit()

    try:
        from core.websocket import manager as ws_manager
        await ws_manager.broadcast({
            "type": "unanswered_question_updated",
            "action": "discard",
            "question_id": q.id,
            "status": "DESCARTADA"
        })
    except Exception as ws_err:
        logger.warning(f"Erro ao emitir broadcast de dúvida descartada: {ws_err}")

    return {"success": True}

@router.post("/unanswered-questions/bulk-discard")
async def bulk_discard_questions(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Descarta múltiplas dúvidas de uma vez."""
    ids = payload.get("ids")
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="Lista de IDs 'ids' é obrigatória")
        
    try:
        stmt = (
            update(UnansweredQuestionModel)
            .where(UnansweredQuestionModel.id.in_(ids))
            .values(status="DESCARTADA", updated_at=datetime.now(timezone.utc))
        )
        await db.execute(stmt)
        await db.commit()

        try:
            from core.websocket import manager as ws_manager
            await ws_manager.broadcast({
                "type": "unanswered_question_bulk_discarded",
                "action": "bulk_discard",
                "question_ids": ids,
                "status": "DESCARTADA"
            })
        except Exception as ws_err:
            logger.warning(f"Erro ao emitir broadcast de descarte em massa: {ws_err}")

        return {"success": True}
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro no descarte em massa: {e}")
        return {"success": False, "error": str(e)}
