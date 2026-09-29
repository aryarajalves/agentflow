import logging
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload

from database import get_db
from api.deps import verify_api_key
from models import PromptVaultModel, AgentConfigModel
from api.schemas import (
    PromptVaultCreate,
    PromptVaultUpdate,
    PromptVaultResponse,
    PromptVaultRestoreRequest,
    AgentConfig,
)
from api.services.agent_service import db_to_pydantic_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompt-vault", tags=["Prompt Vault"])


async def create_pre_deletion_backup(agent: AgentConfigModel, db: AsyncSession) -> PromptVaultModel:
    """
    Cria automaticamente um snapshot de segurança no Cofre de Prompts antes de excluir um agente.
    Garante que nenhum prompt seja perdido em exclusões acidentais.
    """
    try:
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        vault_entry = PromptVaultModel(
            client_id=getattr(agent, "client_id", None),
            name=f"[Backup Pré-Exclusão] {agent.name}",
            description=f"Snapshot de segurança gerado automaticamente antes da exclusão do agente em {now_str}.",
            source_agent_id=agent.id,
            source_agent_name=agent.name,
            backup_type="pre_deletion",
            system_prompt=agent.system_prompt or "",
            dynamic_prompt=agent.dynamic_prompt or "",
            pre_router_prompt=agent.pre_router_prompt,
            unanswered_question_prompt=agent.unanswered_question_prompt,
            tool_prompts=agent.tool_prompts,
            extra_metadata={
                "model": agent.model,
                "temperature": agent.temperature,
                "qualification_questions": agent.qualification_questions,
                "qualification_criteria": agent.qualification_criteria,
                "qualification_final_action": agent.qualification_final_action,
                "qualification_final_action_trigger": agent.qualification_final_action_trigger,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        db.add(vault_entry)
        await db.flush()
        logger.info(f"🛡️ [PROMPT VAULT] Snapshot pré-exclusão criado com sucesso para o agente '{agent.name}' (ID: {agent.id}).")
        return vault_entry
    except Exception as e:
        logger.error(f"❌ [PROMPT VAULT] Falha ao criar backup pré-exclusão para agente '{agent.name}': {e}", exc_info=True)
        # Não bloqueamos a exclusão do agente caso o log de backup falhe criticamente
        return None


@router.get("", response_model=List[PromptVaultResponse])
async def list_prompt_vault(
    search: Optional[str] = Query(None, description="Busca por nome do backup ou agente de origem"),
    backup_type: Optional[str] = Query(None, description="Filtro por tipo: 'manual', 'pre_deletion', 'auto'"),
    source_agent_id: Optional[int] = Query(None, description="Filtrar por agente de origem"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """
    Lista todos os prompts guardados no Cofre com suporte a busca textual e filtros.
    """
    query = select(PromptVaultModel)

    if backup_type:
        query = query.where(PromptVaultModel.backup_type == backup_type)

    if source_agent_id:
        query = query.where(PromptVaultModel.source_agent_id == source_agent_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                PromptVaultModel.name.ilike(term),
                PromptVaultModel.source_agent_name.ilike(term),
                PromptVaultModel.description.ilike(term),
                PromptVaultModel.system_prompt.ilike(term),
            )
        )

    query = query.order_by(desc(PromptVaultModel.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return items


@router.post("", response_model=PromptVaultResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt_vault_entry(
    payload: PromptVaultCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """
    Cria uma nova entrada no Cofre de Prompts.
    Se informado source_agent_id e o system_prompt não for fornecido, os dados são puxados do agente.
    """
    source_name = None
    system_prompt = payload.system_prompt or ""
    dynamic_prompt = payload.dynamic_prompt or ""
    pre_router_prompt = payload.pre_router_prompt
    unanswered_prompt = payload.unanswered_question_prompt
    tool_prompts = payload.tool_prompts
    extra_metadata = payload.extra_metadata or {}

    if payload.source_agent_id:
        res = await db.execute(select(AgentConfigModel).where(AgentConfigModel.id == payload.source_agent_id))
        agent = res.scalars().first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agente de origem não encontrado.")
        
        source_name = agent.name
        # Se os campos de prompt estiverem vazios no payload, captura do agente
        if not system_prompt:
            system_prompt = agent.system_prompt or ""
        if not dynamic_prompt and agent.dynamic_prompt:
            dynamic_prompt = agent.dynamic_prompt
        if pre_router_prompt is None:
            pre_router_prompt = agent.pre_router_prompt
        if unanswered_prompt is None:
            unanswered_prompt = agent.unanswered_question_prompt
        if tool_prompts is None:
            tool_prompts = agent.tool_prompts
        
        if "model" not in extra_metadata:
            extra_metadata["model"] = agent.model
            extra_metadata["temperature"] = agent.temperature

    if not system_prompt.strip() and not (pre_router_prompt and pre_router_prompt.strip()):
        raise HTTPException(
            status_code=400,
            detail="O prompt a ser salvo no cofre não pode estar totalmente vazio."
        )

    vault_entry = PromptVaultModel(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        source_agent_id=payload.source_agent_id,
        source_agent_name=source_name,
        backup_type=payload.backup_type or "manual",
        system_prompt=system_prompt,
        dynamic_prompt=dynamic_prompt,
        pre_router_prompt=pre_router_prompt,
        unanswered_question_prompt=unanswered_prompt,
        tool_prompts=tool_prompts,
        extra_metadata=extra_metadata,
    )

    db.add(vault_entry)
    await db.commit()
    await db.refresh(vault_entry)

    logger.info(f"🛡️ [PROMPT VAULT] Novo backup '{vault_entry.name}' (ID: {vault_entry.id}) salvo com sucesso.")
    return vault_entry


@router.get("/{vault_id}", response_model=PromptVaultResponse)
async def get_prompt_vault_entry(
    vault_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """
    Retorna os detalhes completos de um prompt no cofre.
    """
    res = await db.execute(select(PromptVaultModel).where(PromptVaultModel.id == vault_id))
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Registro do Cofre de Prompts não encontrado.")
    return entry


@router.put("/{vault_id}", response_model=PromptVaultResponse)
async def update_prompt_vault_entry(
    vault_id: int,
    payload: PromptVaultUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """
    Atualiza título ou notas de um prompt no cofre.
    """
    res = await db.execute(select(PromptVaultModel).where(PromptVaultModel.id == vault_id))
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Registro do Cofre de Prompts não encontrado.")

    if payload.name is not None and payload.name.strip():
        entry.name = payload.name.strip()
    if payload.description is not None:
        entry.description = payload.description.strip() if payload.description.strip() else None

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{vault_id}")
async def delete_prompt_vault_entry(
    vault_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """
    Remove uma entrada do Cofre de Prompts.
    """
    res = await db.execute(select(PromptVaultModel).where(PromptVaultModel.id == vault_id))
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Registro do Cofre de Prompts não encontrado.")

    await db.delete(entry)
    await db.commit()
    logger.info(f"🗑️ [PROMPT VAULT] Registro ID {vault_id} removido do cofre.")
    return {"message": "Registro do Cofre de Prompts removido com sucesso.", "id": vault_id}


@router.post("/{vault_id}/restore/{agent_id}", response_model=AgentConfig)
async def restore_prompt_to_agent(
    vault_id: int,
    agent_id: int,
    options: PromptVaultRestoreRequest = PromptVaultRestoreRequest(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """
    Restaura e aplica o pacote de prompts do cofre em um agente existente.
    """
    # 1. Busca o item no cofre
    res_vault = await db.execute(select(PromptVaultModel).where(PromptVaultModel.id == vault_id))
    vault_entry = res_vault.scalars().first()
    if not vault_entry:
        raise HTTPException(status_code=404, detail="Registro do Cofre de Prompts não encontrado.")

    # 2. Busca o agente alvo com relacionamentos pré-carregados
    res_agent = await db.execute(
        select(AgentConfigModel)
        .options(
            selectinload(AgentConfigModel.tools),
            selectinload(AgentConfigModel.knowledge_bases),
        )
        .where(AgentConfigModel.id == agent_id)
    )
    agent = res_agent.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente de destino não encontrado.")

    # 3. Aplica conforme opções selecionadas
    if options.restore_system_prompt and vault_entry.system_prompt:
        agent.system_prompt = vault_entry.system_prompt

    if options.restore_dynamic and vault_entry.dynamic_prompt is not None:
        agent.dynamic_prompt = vault_entry.dynamic_prompt

    if options.restore_pre_router and vault_entry.pre_router_prompt is not None:
        agent.pre_router_prompt = vault_entry.pre_router_prompt

    if options.restore_unanswered and vault_entry.unanswered_question_prompt is not None:
        agent.unanswered_question_prompt = vault_entry.unanswered_question_prompt

    if options.restore_tool_prompts and vault_entry.tool_prompts is not None:
        agent.tool_prompts = vault_entry.tool_prompts

    agent.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(agent)

    logger.info(f"🔄 [PROMPT VAULT] Prompt '{vault_entry.name}' restaurado com sucesso no agente '{agent.name}' (ID: {agent.id}).")
    return db_to_pydantic_agent(agent)
