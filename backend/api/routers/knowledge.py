from typing import List, Optional, Dict, Any
import json
import logging
import io
import time
import pandas as pd
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from models import KnowledgeBaseModel, KnowledgeItemModel, InteractionLog
from api.schemas import (
    KnowledgeBase, KnowledgeItem, KnowledgeItemDetail, BatchDeleteRequest,
    MergeItemsRequest, RAGSimulationRequest, CoverageCheckRequest,
    AddBatchKnowledgeItemsRequest, AddVariationRequest
)
from api.deps import get_db, verify_api_key
from rag_service import (
    get_embedding, get_batch_embeddings, calculate_coverage,
    call_rag_llm, search_knowledge_base, EmbeddingGenerationError
)
from smart_importer import chunk_text, generate_global_qa
from api.services.cost_service import calculate_ai_cost
from config_store import USD_TO_BRL

from api.services.knowledge_service import (
    MAX_QUESTION_VARIATIONS,
    get_item_embedding_text,
    clean_variations_list,
    validate_variations_count,
    export_knowledge_base_dict,
    parse_import_payload,
    process_variation_addition,
    process_variation_removal
)
from api.services.knowledge_parser import (
    extract_text_from_pdf,
    extract_text_from_docx,
    analyze_kb_file_content,
    analyze_kb_text_content
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Knowledge Base"])


# --- KNOWLEDGE BASE ENDPOINTS ---

@router.get(
    "/knowledge-bases",
    response_model=List[KnowledgeBase],
    summary="Listar Bases de Conhecimento",
    description="Retorna todas as bases de conhecimento cadastradas na conta, incluindo seus itens e configurações de rótulos."
)
async def list_knowledge_bases(db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(KnowledgeBaseModel).options(selectinload(KnowledgeBaseModel.items)))
    return result.scalars().all()


@router.post(
    "/knowledge-bases",
    response_model=KnowledgeBase,
    summary="Criar Base de Conhecimento",
    description="Cria uma nova base de conhecimento vazia com nome único, descrição e tipo (ex: 'qa' ou 'chunks')."
)
async def create_knowledge_base(kb: KnowledgeBase, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.name == kb.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Já existe uma base de conhecimento com este nome.")

    db_kb = KnowledgeBaseModel(name=kb.name, description=kb.description, kb_type=kb.kb_type)
    db.add(db_kb)
    await db.commit()
    
    result = await db.execute(
        select(KnowledgeBaseModel)
        .where(KnowledgeBaseModel.id == db_kb.id)
        .options(selectinload(KnowledgeBaseModel.items))
    )
    return result.scalars().one()


@router.get(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBase,
    summary="Obter Detalhes da Base de Conhecimento",
    description="Consulta as informações detalhadas de uma base de conhecimento e todos os seus itens cadastrados a partir do ID."
)
async def get_knowledge_base(kb_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(
        select(KnowledgeBaseModel)
        .where(KnowledgeBaseModel.id == kb_id)
        .options(selectinload(KnowledgeBaseModel.items))
    )
    kb = result.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    return kb


@router.put(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBase,
    summary="Atualizar Base de Conhecimento",
    description="Atualiza as informações cadastrais de uma base (nome, descrição, tipo e rótulos personalizados de campos)."
)
async def update_knowledge_base(kb_id: int, kb: KnowledgeBase, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id))
    db_kb = result.scalars().first()
    if not db_kb:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    
    if db_kb.name != kb.name:
        res_name = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.name == kb.name))
        if res_name.scalars().first():
            raise HTTPException(status_code=400, detail="Já existe uma base de conhecimento com este nome.")

    db_kb.name = kb.name
    db_kb.description = kb.description
    db_kb.kb_type = kb.kb_type
    db_kb.question_label = kb.question_label
    db_kb.answer_label = kb.answer_label
    db_kb.metadata_label = kb.metadata_label
    await db.commit()
    
    result = await db.execute(
        select(KnowledgeBaseModel)
        .where(KnowledgeBaseModel.id == kb_id)
        .options(selectinload(KnowledgeBaseModel.items))
    )
    return result.scalars().first()


@router.delete(
    "/knowledge-bases/{kb_id}",
    summary="Excluir Base de Conhecimento",
    description="Remove permanentemente uma base de conhecimento e todos os seus itens associados do banco de dados."
)
async def delete_knowledge_base(kb_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id))
    kb = result.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    await db.delete(kb)
    await db.commit()
    return {"message": "Knowledge Base deleted"}


@router.post("/knowledge-bases/batch-delete")
async def batch_delete_knowledge_bases(request: BatchDeleteRequest, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    if not request.item_ids:
        return {"message": "No bases to delete"}
    await db.execute(delete(KnowledgeBaseModel).where(KnowledgeBaseModel.id.in_(request.item_ids)))
    await db.commit()
    return {"message": f"Deleted {len(request.item_ids)} knowledge bases"}


@router.post("/knowledge-bases/{kb_id}/propose-merge")
async def propose_kb_merge(kb_id: int, request: MergeItemsRequest, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    if len(request.item_ids) < 2:
        raise HTTPException(status_code=400, detail="Selecione ao menos 2 itens para mesclar.")
    try:
        res = await db.execute(select(KnowledgeItemModel).where(KnowledgeItemModel.id.in_(request.item_ids)))
        items = res.scalars().all()
        if not items:
            raise HTTPException(status_code=404, detail="Itens não encontrados.")
        
        context = "".join([f"VARIANTE {idx+1}:\nPergunta: {i.question}\nResposta: {i.answer}\n\n" for idx, i in enumerate(items)])
        prompt = f"Sintetize estas VARIANTES em 1 Pergunta e 1 Resposta JSON:\n{context}"
        
        response = await call_rag_llm(messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        return {"proposed": json.loads(response.choices[0].message.content), "original_ids": request.item_ids}
    except Exception as e:
        logger.error(f"Erro ao propor mesclagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases/{kb_id}/simulate-rag")
async def simulate_rag(kb_id: int, request: RAGSimulationRequest, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    try:
        result = await search_knowledge_base(
            db=db, query=request.query, kb_id=kb_id, limit=request.limit,
            model="gpt-4o-mini", fallback_model="gpt-4o-mini",
            force_translation=request.translation_enabled,
            force_multi_query=request.multi_query_enabled,
            force_rerank=request.rerank_enabled,
            force_agentic_eval=request.agentic_eval_enabled,
            force_parent_expansion=request.parent_expansion_enabled,
            similarity_threshold=request.relevance_threshold or 0.0
        )
        discarded_items = []
        if isinstance(result, tuple) and len(result) == 3:
            items, discarded_items, usage = result
        elif isinstance(result, tuple) and len(result) == 2:
            items, usage = result
        else:
            items, usage = result or [], None

        p_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        c_tok = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = p_tok + c_tok
        cost_usd = 0.0
        cost_brl = 0.0

        if total_tokens > 0:
            try:
                kb_res = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id))
                kb = kb_res.scalars().first()
                kb_name = kb.name if kb else f"Base #{kb_id}"

                model_used_name = "gpt-4o-mini" if c_tok > 0 else "text-embedding-3-small"
                cost_usd, cost_brl = calculate_ai_cost(model_used_name, p_tok, c_tok)
                if cost_usd == 0.0:
                    cost_usd = total_tokens * 0.00000002
                    cost_brl = cost_usd * USD_TO_BRL

                sim_log = InteractionLog(
                    agent_id=None,
                    session_id=f"SYS_RAG_SIMULATOR_KB_{kb_id}",
                    user_message=f"Simulador RAG ({kb_name}): {request.query[:120]}",
                    agent_response=f"Retornou {len(items or [])} itens ({len(discarded_items or [])} descartados).",
                    model_used=f"Simulador RAG ({model_used_name})",
                    input_tokens=p_tok,
                    output_tokens=c_tok,
                    cost_usd=cost_usd,
                    cost_brl=cost_brl,
                    timestamp=datetime.now(timezone.utc)
                )
                db.add(sim_log)
                await db.commit()
                logger.info(f"🪙 Simulador RAG registrado no financeiro: {total_tokens} tokens (R$ {cost_brl:.6f})")
            except Exception as e_log:
                logger.warning(f"Não foi possível gravar log financeiro do simulador: {e_log}")

        sub_queries = getattr(usage, "sub_queries", [request.query]) if usage else [request.query]
        grouped_results = getattr(usage, "grouped_results", []) if usage else []
        if not grouped_results:
            grouped_results = [{
                "sub_query": request.query,
                "items": items or [],
                "discarded_items": discarded_items or []
            }]

        return {
            "items": items or [],
            "discarded_items": discarded_items or [],
            "sub_queries": sub_queries,
            "grouped_results": grouped_results,
            "usage": {
                "prompt_tokens": p_tok,
                "completion_tokens": c_tok,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "cost_brl": cost_brl
            }
        }
    except Exception as e:
        logger.error(f"Erro no simulador de RAG (kb_id={kb_id}, query='{request.query}'): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao simular a busca RAG: {str(e)}")


@router.post("/knowledge-bases/{kb_id}/coverage")
async def check_coverage(kb_id: int, payload: CoverageCheckRequest, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    results = await calculate_coverage(db, payload.questions, kb_id)
    return {"results": results}


@router.post("/knowledge-bases/{kb_id}/upload")
async def upload_kb_file(kb_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    content = await file.read()
    filename = file.filename.lower()
    text = ""
    if filename.endswith(".pdf"):
        text = await extract_text_from_pdf(content)
    elif filename.endswith(".docx"):
        text = await extract_text_from_docx(content)
    else:
        text = content.decode("utf-8", errors="ignore")

    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
    for line in lines:
        db.add(KnowledgeItemModel(knowledge_base_id=kb_id, question=f"Informação de {file.filename}", answer=line, category="Upload"))
    await db.commit()
    return {"message": f"Extraído {len(lines)} itens do arquivo {file.filename}"}


@router.get("/knowledge-bases/{kb_id}/export")
async def export_knowledge_base(kb_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(
        select(KnowledgeBaseModel)
        .where(KnowledgeBaseModel.id == kb_id)
        .options(selectinload(KnowledgeBaseModel.items))
    )
    kb = result.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Base de conhecimento não encontrada")
    
    export_data = export_knowledge_base_dict(kb)
    filename = f"base_conhecimento_{kb_id}.json"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=json.dumps(export_data, ensure_ascii=False, indent=2), media_type="application/json", headers=headers)


@router.post("/knowledge-bases/{kb_id}/import")
async def import_knowledge_base_items(
    kb_id: int, 
    request: Request,
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    result = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id))
    kb = result.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Base de conhecimento não encontrada")
    
    raw_data = None
    if file:
        content = await file.read()
        try:
            raw_data = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Arquivo JSON inválido: {str(e)}")
    else:
        try:
            body = await request.body()
            if body:
                raw_data = json.loads(body.decode("utf-8"))
        except Exception:
            pass
            
    if not raw_data:
        raise HTTPException(status_code=400, detail="Nenhum arquivo ou JSON fornecido.")
        
    valid_items = parse_import_payload(raw_data)
    if not valid_items:
        raise HTTPException(status_code=400, detail="Nenhum item válido com 'pergunta' e 'resposta' encontrado no arquivo.")
        
    texts_to_embed = [get_item_embedding_text(i["question"], i["question_variations"]) for i in valid_items]
    try:
        embeddings, _ = await get_batch_embeddings(texts_to_embed)
    except Exception as e:
        logger.warning(f"Falha ao gerar batch embeddings no import: {e}. Usando fallback item a item.")
        embeddings = []
        for t in texts_to_embed:
            try:
                emb, _ = await get_embedding(t)
                embeddings.append(emb)
            except Exception:
                embeddings.append(None)
                
    imported_count = 0
    for idx, item in enumerate(valid_items):
        emb = embeddings[idx] if idx < len(embeddings) else None
        db_item = KnowledgeItemModel(
            knowledge_base_id=kb_id,
            question=item["question"],
            answer=item["answer"],
            category=item["category"],
            metadata_val=item["metadata_val"],
            question_variations=item["question_variations"],
            embedding=emb
        )
        db.add(db_item)
        imported_count += 1
        
    await db.commit()
    return {"message": f"Importação concluída! {imported_count} itens adicionados.", "imported_count": imported_count}


@router.post("/knowledge-bases/import-new", response_model=KnowledgeBase)
async def import_new_knowledge_base(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    content = await file.read()
    try:
        raw_data = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Arquivo JSON inválido: {str(e)}")
        
    if not isinstance(raw_data, dict):
        raise HTTPException(status_code=400, detail="O JSON de importação de nova base deve conter um objeto com os dados da base.")
        
    base_name = raw_data.get("name") or f"Base Importada {time.strftime('%d/%m/%Y %H:%M')}"
    res = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.name == base_name))
    if res.scalars().first():
        base_name = f"{base_name} ({time.strftime('%H%M%S')})"
        
    db_kb = KnowledgeBaseModel(
        name=base_name,
        description=raw_data.get("description") or "Base criada via importação completa de JSON.",
        kb_type=raw_data.get("kb_type") or "qa",
        question_label=raw_data.get("question_label") or "Pergunta",
        answer_label=raw_data.get("answer_label") or "Resposta",
        metadata_label=raw_data.get("metadata_label") or "Metadado"
    )
    db.add(db_kb)
    await db.commit()
    await db.refresh(db_kb)
    
    items_data = raw_data.get("items", [])
    valid_items = []
    for item in items_data:
        if isinstance(item, dict):
            q = item.get("question") or item.get("pergunta") or ""
            a = item.get("answer") or item.get("resposta") or ""
            cat = item.get("category") or item.get("categoria") or "Geral"
            meta = item.get("metadata_val") or item.get("metadata") or ""
            if q and a:
                valid_items.append({"question": q, "answer": a, "category": cat, "metadata_val": meta})
                
    if valid_items:
        questions = [i["question"] for i in valid_items]
        try:
            embeddings, _ = await get_batch_embeddings(questions)
        except Exception as e:
            logger.warning(f"Batch embedding fallback no import-new: {e}")
            embeddings = [None] * len(questions)
            
        for idx, item in enumerate(valid_items):
            emb = embeddings[idx] if idx < len(embeddings) else None
            db.add(KnowledgeItemModel(
                knowledge_base_id=db_kb.id,
                question=item["question"],
                answer=item["answer"],
                category=item["category"],
                metadata_val=item["metadata_val"],
                embedding=emb
            ))
        await db.commit()
        
    result = await db.execute(
        select(KnowledgeBaseModel)
        .where(KnowledgeBaseModel.id == db_kb.id)
        .options(selectinload(KnowledgeBaseModel.items))
    )
    return result.scalars().one()


# --- KNOWLEDGE ITEM ENDPOINTS ---

@router.post(
    "/knowledge-bases/{kb_id}/items",
    response_model=KnowledgeItem,
    summary="Criar Item de Conhecimento",
    description="Adiciona uma pergunta e resposta em uma base com cálculo de embedding vetorial (pgvector) a partir da pergunta e de suas variações."
)
async def add_knowledge_item(kb_id: int, item: KnowledgeItem, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    clean_vars = clean_variations_list(item.question_variations)
    validate_variations_count(len(clean_vars))
    text_to_embed = get_item_embedding_text(item.question, clean_vars)
    try:
        emb, _ = await get_embedding(text_to_embed)
    except EmbeddingGenerationError as e:
        logger.error(f"Falha ao gerar embedding ao criar item na base {kb_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Não foi possível gerar o vetor (embedding) do item: {e}")

    db_item = KnowledgeItemModel(
        knowledge_base_id=kb_id, 
        question=item.question, 
        answer=item.answer, 
        metadata_val=item.metadata_val, 
        category=item.category, 
        question_variations=clean_vars,
        embedding=emb
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.get("/knowledge-items/{item_id}", response_model=KnowledgeItemDetail)
async def get_knowledge_item(item_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(KnowledgeItemModel).where(KnowledgeItemModel.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/knowledge-items/{item_id}")
async def delete_knowledge_item(item_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(KnowledgeItemModel).where(KnowledgeItemModel.id == item_id))
    item = result.scalars().first()
    if item:
        await db.delete(item)
        await db.commit()
    return {"message": "Item deleted"}


@router.put("/knowledge-items/{item_id}", response_model=KnowledgeItemDetail)
async def update_knowledge_item(item_id: int, item: KnowledgeItem, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(KnowledgeItemModel).where(KnowledgeItemModel.id == item_id))
    db_item = result.scalars().first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    clean_vars = clean_variations_list(item.question_variations)
    validate_variations_count(len(clean_vars))
    text_to_embed = get_item_embedding_text(item.question, clean_vars)

    try:
        emb, _ = await get_embedding(text_to_embed)
        db_item.embedding = emb
    except EmbeddingGenerationError as e:
        logger.error(f"Falha ao recalcular embedding do item {item_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Não foi possível recalcular o vetor (embedding) do item: {e}")

    db_item.question = item.question
    db_item.answer = item.answer
    db_item.metadata_val = item.metadata_val
    db_item.category = item.category
    db_item.question_variations = clean_vars
    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.post("/knowledge-items/{item_id}/variations")
async def add_knowledge_item_variation(
    item_id: int, 
    request: AddVariationRequest, 
    db: AsyncSession = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    result = await db.execute(select(KnowledgeItemModel).where(KnowledgeItemModel.id == item_id))
    db_item = result.scalars().first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    updated_vars, added = process_variation_addition(
        db_item.question_variations,
        request.variation,
        request.variations
    )

    if not added:
        return {
            "message": "A variação já existia para este item.",
            "item_id": db_item.id,
            "question_variations": clean_variations_list(db_item.question_variations),
            "added": []
        }

    text_to_embed = get_item_embedding_text(db_item.question, updated_vars)
    try:
        emb, _ = await get_embedding(text_to_embed)
        db_item.embedding = emb
    except EmbeddingGenerationError as e:
        logger.error(f"Falha ao recalcular embedding para item {item_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Não foi possível recalcular o vetor (embedding): {e}")

    db_item.question_variations = list(updated_vars)
    flag_modified(db_item, "question_variations")
    await db.commit()
    await db.refresh(db_item)

    return {
        "message": "Variação adicionada com sucesso.",
        "item_id": db_item.id,
        "question_variations": db_item.question_variations,
        "added": added
    }


@router.delete("/knowledge-items/{item_id}/variations")
async def delete_knowledge_item_variation(
    item_id: int,
    variation: str = Query(..., description="Variação a remover"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    result = await db.execute(select(KnowledgeItemModel).where(KnowledgeItemModel.id == item_id))
    db_item = result.scalars().first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    updated_vars = process_variation_removal(db_item.question_variations, variation)

    text_to_embed = get_item_embedding_text(db_item.question, updated_vars)
    try:
        emb, _ = await get_embedding(text_to_embed)
        db_item.embedding = emb
    except EmbeddingGenerationError as e:
        logger.error(f"Falha ao recalcular embedding para item {item_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Não foi possível recalcular o vetor (embedding): {e}")

    db_item.question_variations = list(updated_vars)
    flag_modified(db_item, "question_variations")
    await db.commit()
    await db.refresh(db_item)

    return {
        "message": "Variação removida com sucesso.",
        "item_id": db_item.id,
        "question_variations": db_item.question_variations
    }


@router.post("/knowledge-bases/{kb_id}/items/bulk")
async def bulk_knowledge_items(kb_id: int, items: List[KnowledgeItem], db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(KnowledgeItemModel).where(KnowledgeItemModel.id.in_([i.id for i in items if i.id])))
    existing_items = {i.id: i for i in result.scalars().all()}
    for item in items:
        clean_vars = clean_variations_list(item.question_variations)
        if item.id in existing_items:
            db_item = existing_items[item.id]
            db_item.question = item.question
            db_item.answer = item.answer
            db_item.metadata_val = item.metadata_val
            db_item.category = item.category
            db_item.question_variations = clean_vars
        else:
            text_to_embed = get_item_embedding_text(item.question, clean_vars)
            emb, _ = await get_embedding(text_to_embed)
            db.add(KnowledgeItemModel(
                knowledge_base_id=kb_id, 
                question=item.question, 
                answer=item.answer, 
                metadata_val=item.metadata_val, 
                category=item.category, 
                question_variations=clean_vars,
                embedding=emb
            ))
            
    res_all = await db.execute(select(KnowledgeItemModel.id).where(KnowledgeItemModel.knowledge_base_id == kb_id))
    all_db_ids = set(res_all.scalars().all())
    ids_to_delete = all_db_ids - {i.id for i in items if i.id}
    if ids_to_delete:
        await db.execute(delete(KnowledgeItemModel).where(KnowledgeItemModel.id.in_(list(ids_to_delete))))
    await db.commit()
    return {"message": "Bulk sync completed"}


@router.post(
    "/knowledge-bases/{kb_id}/items/add-batch",
    summary="Adicionar Itens em Lote (Batch)",
    description="Permite cadastrar múltiplos itens de conhecimento de forma rápida em uma única chamada com cálculo de vetores semânticos."
)
async def add_batch_knowledge_items(
    kb_id: int,
    request: AddBatchKnowledgeItemsRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    try:
        added_count = 0
        for item in request.items:
            emb = None
            try:
                emb, _ = await get_embedding(item.question)
            except Exception as emb_err:
                logger.error(f"Erro ao gerar embedding para item: {emb_err}")
            
            db_item = KnowledgeItemModel(
                knowledge_base_id=kb_id,
                question=item.question,
                answer=item.answer,
                metadata_val=item.metadata_val,
                category=item.category or "Treinamento",
                embedding=emb
            )
            db.add(db_item)
            added_count += 1
            
        await db.commit()
        return {"message": f"Sucesso! {added_count} novos itens adicionados com sucesso."}
    except Exception as e:
        logger.error(f"Erro em add_batch_knowledge_items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- ANÁLISE E IMPORTAÇÃO DE ARQUIVOS ---

@router.post("/knowledge-bases/analyze-file")
async def analyze_kb_file(file: UploadFile = File(...), _: None = Depends(verify_api_key)):
    content = await file.read()
    return analyze_kb_file_content(content, file.filename)


@router.post("/knowledge-bases/analyze-text")
async def analyze_kb_text(text: str = Form(...), _: None = Depends(verify_api_key)):
    return analyze_kb_text_content(text)


@router.post("/knowledge-bases/{kb_id}/import-mapped")
async def import_mapped_file(
    kb_id: int,
    question_col: str = Form(...),
    answer_col: str = Form(...),
    category_col: str = Form(None),
    fixed_category: str = Form(None),
    metadata_col: str = Form(None),
    fixed_metadata: str = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    content = await file.read()
    filename = file.filename.lower()
    df = pd.read_csv(io.BytesIO(content)) if filename.endswith(".csv") else pd.read_excel(io.BytesIO(content))
    for _, row in df.iterrows():
        q = str(row[question_col])
        a = str(row[answer_col])
        cat = str(row[category_col]) if category_col and category_col in row else fixed_category
        meta = str(row[metadata_col]) if metadata_col and metadata_col in row else fixed_metadata
        emb, _ = await get_embedding(q)
        db.add(KnowledgeItemModel(
            knowledge_base_id=kb_id,
            question=q,
            answer=a,
            category=cat,
            metadata_val=meta,
            embedding=emb
        ))
    await db.commit()
    return {"message": "Importação concluída"}
