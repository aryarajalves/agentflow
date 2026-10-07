import os
import io
import time
import json
import uuid
import shutil
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from database import async_session
from models import TranscriptionTaskModel, TranscriptionFolder, KnowledgeItemModel, KnowledgeBaseModel, InteractionLog
from api.deps import get_db, verify_api_key
from api.schemas import (
    GenerateUploadUrlRequest,
    ConfirmUploadRequest,
    TranscriptionProcessRequest,
    BulkDeleteTranscriptionRequest,
    TranscriptionRenameRequest,
    TranscriptionFolderRequest,
    GenerateQAFromTranscriptionRequest,
    GenerateChunksFromTranscriptionRequest,
    ProcessLessonTranscriptionRequest
)
from rag_service import get_embedding, get_batch_embeddings
from s3_service import s3_service
from api.services.knowledge_parser import background_s3_upload
from api.services.cost_service import calculate_ai_cost
from config_store import USD_TO_BRL
import smart_importer

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Transcriptions"])


@router.post("/knowledge-bases/generate-upload-url")
async def generate_upload_url(
    request: GenerateUploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    try:
        s3_key = f"transcriptions/{int(time.time())}_{request.filename}"
        put_url = s3_service.generate_presigned_put_url(s3_key, content_type=request.content_type, expiration=3600)
        if not put_url:
            raise HTTPException(status_code=500, detail="Erro ao gerar URL S3.")
        new_task = TranscriptionTaskModel(
            knowledge_base_id=request.kb_id,
            filename=request.filename,
            s3_key=s3_key,
            status="PENDING"
        )
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        return {"url": put_url, "s3_key": s3_key, "task_id": new_task.id}
    except Exception as e:
        logger.error(f"Erro generate_upload_url: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases/confirm-upload")
async def confirm_upload_endpoint(
    request: ConfirmUploadRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    from tasks import process_transcription_task
    task = await db.get(TranscriptionTaskModel, request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task não encontrada")
    process_transcription_task.delay(request.task_id, task.s3_key, request.config)
    return {"message": "Processamento iniciado.", "status": "PENDING"}


@router.post("/knowledge-bases/transcribe")
async def transcribe_video_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    config: str = Form("{}"),
    kb_id: Optional[int] = Form(None),
    _: None = Depends(verify_api_key)
):
    config_dict = json.loads(config)
    s3_key = f"transcriptions/{int(time.time())}_{file.filename}"
    temp_dir = os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    local_path = os.path.join(temp_dir, f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}")
    with open(local_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    async with async_session() as db:
        new_task = TranscriptionTaskModel(
            knowledge_base_id=kb_id,
            filename=file.filename,
            s3_key=s3_key,
            status="PENDING"
        )
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        task_id = new_task.id
    background_tasks.add_task(background_s3_upload, local_path, s3_key, task_id, config_dict)
    return {"message": "Transcrição iniciada.", "task_id": task_id, "status": "PENDING"}


@router.get("/transcription-tasks")
async def list_transcription_tasks(
    response: Response,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    folder_id: Optional[int] = Query(None),
    _: None = Depends(verify_api_key)
):
    offset = (page - 1) * limit
    stmt = select(TranscriptionTaskModel).where(TranscriptionTaskModel.status != "PENDING")
    if folder_id:
        stmt = stmt.where(TranscriptionTaskModel.folder_id == folder_id)
    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total_count = total_res.scalar()
    result = await db.execute(
        stmt.order_by(TranscriptionTaskModel.created_at.desc()).offset(offset).limit(limit)
    )
    return {"tasks": result.scalars().all(), "total": total_count, "page": page, "limit": limit}


@router.get("/transcription-folders")
async def list_transcription_folders(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    result = await db.execute(select(TranscriptionFolder).order_by(TranscriptionFolder.name))
    return result.scalars().all()


@router.post("/transcription-folders")
async def create_transcription_folder(
    request: TranscriptionFolderRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    new_folder = TranscriptionFolder(name=request.name)
    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)
    return new_folder


@router.delete("/transcription-folders/{folder_id}")
async def delete_transcription_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    folder = await db.get(TranscriptionFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    await db.delete(folder)
    await db.commit()
    return {"message": "Pasta removida."}


@router.post("/transcription-tasks/bulk-delete")
async def bulk_delete_transcription_tasks(
    request: BulkDeleteTranscriptionRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    res = await db.execute(
        select(TranscriptionTaskModel).where(TranscriptionTaskModel.id.in_(request.task_ids))
    )
    tasks = res.scalars().all()
    for task in tasks:
        if task.s3_key:
            s3_service.delete_file(task.s3_key)
        await db.delete(task)
    await db.commit()
    return {"message": f"{len(tasks)} registros removidos."}


@router.put("/transcription-tasks/{task_id}/rename")
async def rename_transcription_task(
    task_id: int,
    request: TranscriptionRenameRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    task = await db.get(TranscriptionTaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    task.filename = request.filename
    await db.commit()
    return {"message": "Tarefa renomeada com sucesso"}


@router.post("/transcription-tasks/{task_id}/retry")
async def retry_transcription_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    from tasks import process_transcription_task
    task = await db.get(TranscriptionTaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    task.status = "PENDING"
    task.error_message = None
    await db.commit()

    process_transcription_task.delay(task.id, task.s3_key, {})
    return {"message": "Processamento reiniciado."}


@router.post("/knowledge-bases/{kb_id}/process-transcription")
async def process_transcription_endpoint(
    kb_id: int,
    request: TranscriptionProcessRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    chunks = smart_importer.chunk_text(request.text, chunk_size=1200, overlap=150)
    for c in chunks:
        db.add(KnowledgeItemModel(
            knowledge_base_id=kb_id,
            question="Trecho",
            answer=c["text"],
            category="Transcrição"
        ))
    await db.commit()
    return {"message": "Processado"}


@router.post("/knowledge-bases/generate-qa-from-transcription")
async def generate_qa_from_transcription(
    request: GenerateQAFromTranscriptionRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    try:
        qa_list, usage = await smart_importer.generate_global_qa(
            request.text,
            total_questions=request.total_questions,
            model=request.model or "gpt-4o-mini"
        )

        model_used = usage.get("model", request.model or "gpt-4o-mini") if usage else (request.model or "gpt-4o-mini")
        cost_usd = 0.0

        if usage:
            input_tk = usage.get("input_tokens", 0)
            output_tk = usage.get("output_tokens", 0)
            cost_usd, cost_brl = calculate_ai_cost(model_used, input_tk, output_tk)

            task_filename = "N/A"
            if request.task_id:
                task_res = await db.execute(
                    select(TranscriptionTaskModel).where(TranscriptionTaskModel.id == request.task_id)
                )
                task = task_res.scalar_one_or_none()
                if task:
                    task.cost_usd = (task.cost_usd or 0.0) + cost_usd
                    task_filename = task.filename or "N/A"
                    logger.info(f"💰 Custo de extração de P&R de ${cost_usd:.6f} adicionado à tarefa {task.id}")

            new_log = InteractionLog(
                agent_id=None,
                session_id=f"SYS_EXTRACTION_KB_{request.task_id or 'unknown'}",
                user_message=f"Extração P&R (IA) - Arquivo: {task_filename}" if request.task_id else "Extração P&R (IA)",
                agent_response=f"Geração de {len(qa_list)} perguntas e respostas concluída via {model_used}.",
                model_used=model_used,
                input_tokens=input_tk,
                output_tokens=output_tk,
                cost_usd=cost_usd,
                cost_brl=cost_usd * USD_TO_BRL,
                timestamp=datetime.now(timezone.utc)
            )
            db.add(new_log)
            await db.commit()
            logger.info(f"📊 Extração registrada no financeiro: R$ {new_log.cost_brl:.4f} ({new_log.model_used})")

        return {
            "items": qa_list,
            "model": model_used,
            "cost_usd": cost_usd,
            "cost_brl": cost_usd * USD_TO_BRL
        }
    except Exception as e:
        logger.error(f"Erro em generate_qa_from_transcription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases/generate-chunks-from-transcription")
async def generate_chunks_from_transcription(
    request: GenerateChunksFromTranscriptionRequest,
    _: None = Depends(verify_api_key)
):
    try:
        chunks = smart_importer.chunk_text(request.text, chunk_size=request.chunk_size or 1200, overlap=request.overlap or 150)
        formatted_chunks = []
        for i, c in enumerate(chunks):
            formatted_chunks.append({
                "question": f"Trecho da Aula #{i + 1}",
                "answer": c["text"],
                "category": "Transcrição"
            })
        return formatted_chunks
    except Exception as e:
        logger.error(f"Erro em generate_chunks_from_transcription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases/{kb_id}/generate-qa-and-chunks")
async def generate_qa_and_chunks(
    kb_id: int,
    request: ProcessLessonTranscriptionRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """
    Processa a transcrição completa de uma aula gerando simultaneamente:
    1. Perguntas e Respostas didáticas via IA (padrão 5 questões).
    2. Chunks de texto contínuo sequenciais da aula.
    3. Se auto_save=True (padrão), salva tudo na base de conhecimento com embeddings calculados.
    """
    kb = await db.get(KnowledgeBaseModel, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Base de conhecimento não encontrada.")

    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="O texto da transcrição não pode ser vazio.")

    # 1. Metadados do vídeo / aula
    meta_parts = []
    if request.video_title:
        meta_parts.append(f"Vídeo: {request.video_title.strip()}")
    if request.module_name:
        meta_parts.append(f"Módulo: {request.module_name.strip()}")
    if request.chapter_name:
        meta_parts.append(f"Capítulo: {request.chapter_name.strip()}")
    metadata_val = " | ".join(meta_parts) if meta_parts else ""

    # 2. Gerar Perguntas e Respostas via IA
    qa_list = []
    usage = {}
    model_used = request.model or "gpt-4o-mini"
    cost_usd = 0.0
    cost_brl = 0.0

    try:
        qa_list, usage = await smart_importer.generate_global_qa(
            request.text,
            total_questions=request.total_questions or 5,
            model=model_used
        )
        if usage:
            input_tk = usage.get("input_tokens", 0)
            output_tk = usage.get("output_tokens", 0)
            cost_usd, cost_brl = calculate_ai_cost(model_used, input_tk, output_tk)
    except Exception as e:
        logger.error(f"Erro ao gerar P&R na transcrição: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar perguntas e respostas via IA: {str(e)}")

    # 3. Gerar Chunks de texto da aula
    raw_chunks = smart_importer.chunk_text(
        request.text,
        chunk_size=request.chunk_size or 1200,
        overlap=request.overlap or 150
    )

    formatted_qa = []
    for item in qa_list:
        q = (item.get("pergunta") or item.get("question") or "").strip()
        a = (item.get("resposta") or item.get("answer") or "").strip()
        cat = item.get("categoria") or item.get("category") or request.category_qa or "Treinamento"
        if q and a:
            formatted_qa.append({
                "question": q,
                "answer": a,
                "category": cat,
                "metadata_val": metadata_val
            })

    formatted_chunks = []
    lesson_prefix = f" ({request.video_title.strip()})" if request.video_title else ""
    for idx, c in enumerate(raw_chunks):
        c_text = c.get("text", "").strip() if isinstance(c, dict) else str(c).strip()
        if c_text:
            formatted_chunks.append({
                "question": f"Trecho da Aula #{idx + 1}{lesson_prefix}",
                "answer": c_text,
                "category": request.category_chunks or "Transcrição",
                "metadata_val": metadata_val
            })

    all_items_to_save = formatted_qa + formatted_chunks

    if not request.auto_save:
        return {
            "message": f"Prévia gerada: {len(formatted_qa)} P&R e {len(formatted_chunks)} trechos.",
            "kb_id": kb_id,
            "qa_count": len(formatted_qa),
            "chunks_count": len(formatted_chunks),
            "total_count": len(all_items_to_save),
            "qa_items": formatted_qa,
            "chunk_items": formatted_chunks,
            "model_used": model_used,
            "cost_usd": cost_usd,
            "cost_brl": cost_brl
        }

    # 4. Salvar com embeddings
    texts_for_embeddings = [it["question"] for it in all_items_to_save]
    try:
        embeddings, _ = await get_batch_embeddings(texts_for_embeddings)
    except Exception as e:
        logger.warning(f"Batch embedding fallback em generate_qa_and_chunks: {e}")
        embeddings = []
        for t in texts_for_embeddings:
            try:
                emb, _ = await get_embedding(t)
                embeddings.append(emb)
            except Exception:
                embeddings.append(None)

    saved_items = []
    for idx, it in enumerate(all_items_to_save):
        emb = embeddings[idx] if idx < len(embeddings) else None
        db_item = KnowledgeItemModel(
            knowledge_base_id=kb_id,
            question=it["question"],
            answer=it["answer"],
            category=it["category"],
            metadata_val=it["metadata_val"],
            embedding=emb
        )
        db.add(db_item)
        saved_items.append(db_item)

    # 5. Atualizar custo se task_id foi enviado e registrar log
    if request.task_id and cost_usd > 0:
        task_res = await db.execute(
            select(TranscriptionTaskModel).where(TranscriptionTaskModel.id == request.task_id)
        )
        t_model = task_res.scalar_one_or_none()
        if t_model:
            t_model.cost_usd = (t_model.cost_usd or 0.0) + cost_usd

    if cost_usd > 0:
        task_label = f"Arquivo: {request.video_title}" if request.video_title else "Aula Transcrita"
        log = InteractionLog(
            agent_id=None,
            session_id=f"SYS_QA_CHUNKS_KB_{kb_id}",
            user_message=f"Processamento Híbrido (P&R + Chunks) - {task_label}",
            agent_response=f"Criadas {len(formatted_qa)} P&R e {len(formatted_chunks)} trechos via {model_used}.",
            model_used=model_used,
            input_tokens=usage.get("input_tokens", 0) if usage else 0,
            output_tokens=usage.get("output_tokens", 0) if usage else 0,
            cost_usd=cost_usd,
            cost_brl=cost_brl,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log)

    await db.commit()

    return {
        "message": f"Sucesso! {len(formatted_qa)} perguntas/respostas e {len(formatted_chunks)} trechos adicionados com sucesso à base #{kb_id}.",
        "kb_id": kb_id,
        "qa_count": len(formatted_qa),
        "chunks_count": len(formatted_chunks),
        "total_saved": len(saved_items),
        "qa_items": formatted_qa,
        "chunk_items": formatted_chunks,
        "model_used": model_used,
        "cost_usd": cost_usd,
        "cost_brl": cost_brl
    }

