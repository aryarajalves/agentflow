import logging
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from models import AgentConfigModel, ToolModel, KnowledgeBaseModel, InteractionLog, PromptDraftModel
from api.schemas import (
    AgentConfig, PromptDraft, BulkAgentDeleteRequest, 
    PromptAdvisorRequest, PromptRefineRequest, MessageRequest, MessageResponse
)
from api.deps import get_db, verify_api_key
from api.services.cost_service import calculate_ai_cost
from api.services.agent_service import db_to_pydantic_agent
from agent import get_openai_client, process_message

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Agents"])

@router.get("/agents", response_model=List[AgentConfig])
async def list_agents(db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(
        select(AgentConfigModel)
        .options(selectinload(AgentConfigModel.tools), selectinload(AgentConfigModel.knowledge_bases))
        .order_by(AgentConfigModel.id)
    )
    db_agents = result.scalars().all()
    
    return [db_to_pydantic_agent(a) for a in db_agents]
    return agents

@router.post("/agents", response_model=AgentConfig)
async def create_agent(config: AgentConfig, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    db_config = AgentConfigModel(
        name=config.name,
        description=config.description,
        model=config.model,
        fallback_model=config.fallback_model,
        temperature=config.temperature,
        top_p=config.top_p,
        top_k=config.top_k,
        presence_penalty=config.presence_penalty,
        frequency_penalty=config.frequency_penalty,
        safety_settings=config.safety_settings,
        model_settings=json.dumps(config.model_settings) if config.model_settings else "{}",
        is_active=config.is_active,
        date_awareness=config.date_awareness,
        date_awareness_past_days=config.date_awareness_past_days,
        date_awareness_future_days=config.date_awareness_future_days,
        system_prompt=config.system_prompt,
        dynamic_prompt=config.dynamic_prompt,
        pre_router_prompt=config.pre_router_prompt,
        context_window=config.context_window,
        knowledge_base=json.dumps(config.knowledge_base),
        rag_retrieval_count=config.rag_retrieval_count,
        rag_translation_enabled=config.rag_translation_enabled,
        rag_multi_query_enabled=config.rag_multi_query_enabled,
        rag_rerank_enabled=config.rag_rerank_enabled,
        rag_agentic_eval_enabled=config.rag_agentic_eval_enabled,
        rag_parent_expansion_enabled=config.rag_parent_expansion_enabled,
        rag_relevance_threshold=config.rag_relevance_threshold,
        rag_kb_routing_enabled=config.rag_kb_routing_enabled,
        rag_kb_routing_variable=config.rag_kb_routing_variable,
        security_competitor_blacklist=config.security_competitor_blacklist,
        security_forbidden_topics=config.security_forbidden_topics,
        security_discount_policy=config.security_discount_policy,
        security_language_complexity=config.security_language_complexity,
        security_pii_filter=config.security_pii_filter,
        security_validator_ia=config.security_validator_ia,
        security_bot_protection=config.security_bot_protection,
        security_max_messages_per_session=config.security_max_messages_per_session,
        security_semantic_threshold=config.security_semantic_threshold,
        security_loop_count=config.security_loop_count,
        ui_primary_color=config.ui_primary_color,
        ui_header_color=config.ui_header_color,
        ui_chat_title=config.ui_chat_title,
        ui_welcome_message=config.ui_welcome_message,
        initial_message=config.initial_message,
        initial_question_message=config.initial_question_message,
        initial_ignore_message=config.initial_ignore_message,
        inbox_capture_enabled=config.inbox_capture_enabled,
        greeting_mode=config.greeting_mode,
        question_mode=config.question_mode,
        ad_mode=config.ad_mode,
        qualification_questions=config.qualification_questions,
        qualification_labels=config.qualification_labels,
        qualification_criteria=config.qualification_criteria,
        qualification_final_action=config.qualification_final_action,
        qualification_final_action_trigger=config.qualification_final_action_trigger or "all",
        qualification_funnels=getattr(config, 'qualification_funnels', None),
        unanswered_handoff_limit=config.unanswered_handoff_limit if config.unanswered_handoff_limit is not None else 2,
        unanswered_question_prompt=config.unanswered_question_prompt,
        router_enabled=config.router_enabled,
        router_simple_model=config.router_simple_model,
        router_complex_model=config.router_complex_model,
        handoff_enabled=config.handoff_enabled,
        response_translation_enabled=config.response_translation_enabled,
        response_translation_fallback_lang=config.response_translation_fallback_lang or "portuguese",
        tool_prompts=config.tool_prompts,
        semantic_cache_enabled=config.semantic_cache_enabled if config.semantic_cache_enabled is not None else True,
        semantic_cache_threshold=config.semantic_cache_threshold or 0.92
    )

    if config.tool_ids:
        res_tools = await db.execute(select(ToolModel).where(ToolModel.id.in_(config.tool_ids)))
        db_config.tools = res_tools.scalars().all()

    if config.knowledge_base_ids:
        res_kbs = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.id.in_(config.knowledge_base_ids)))
        db_config.knowledge_bases = res_kbs.scalars().all()

    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return await get_agent(db_config.id, db)

@router.get("/agents/pre-router-default-prompt")
async def get_pre_router_default_prompt(_: None = Depends(verify_api_key)):
    """Retorna o template padrão do Pre-Router (parte customizável, sem o rodapé
    fixo de schema JSON), usado para popular a aba 'Pre-Router' quando o agente
    não tem um prompt customizado, e para o botão 'Restaurar Padrão' no editor."""
    from agent_core.logic.pre_router import DEFAULT_PRE_ROUTER_PROMPT_TEMPLATE
    return {"prompt": DEFAULT_PRE_ROUTER_PROMPT_TEMPLATE}

@router.get("/agents/{agent_id}", response_model=AgentConfig)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(
        select(AgentConfigModel)
        .options(selectinload(AgentConfigModel.tools), selectinload(AgentConfigModel.knowledge_bases))
        .where(AgentConfigModel.id == agent_id)
    )
    a = result.scalars().first()
    if not a: raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentConfig(
        id=a.id,
        name=a.name,
        description=a.description,
        model=a.model,
        fallback_model=a.fallback_model,
        temperature=a.temperature,
        top_p=a.top_p,
        top_k=a.top_k,
        presence_penalty=a.presence_penalty,
        frequency_penalty=a.frequency_penalty,
        safety_settings=a.safety_settings,
        model_settings=json.loads(a.model_settings) if a.model_settings else {},
        is_active=a.is_active,
        date_awareness=a.date_awareness,
        date_awareness_past_days=a.date_awareness_past_days,
        date_awareness_future_days=a.date_awareness_future_days,
        system_prompt=a.system_prompt,
        dynamic_prompt=a.dynamic_prompt,
        pre_router_prompt=a.pre_router_prompt,
        context_window=a.context_window,
        knowledge_base=json.loads(a.knowledge_base) if a.knowledge_base else [],
        knowledge_base_id=a.knowledge_base_id,
        knowledge_base_ids=[kb.id for kb in a.knowledge_bases],
        rag_retrieval_count=a.rag_retrieval_count,
        rag_translation_enabled=a.rag_translation_enabled,
        rag_multi_query_enabled=a.rag_multi_query_enabled,
        rag_rerank_enabled=a.rag_rerank_enabled,
        rag_agentic_eval_enabled=a.rag_agentic_eval_enabled,
        rag_parent_expansion_enabled=a.rag_parent_expansion_enabled,
        rag_relevance_threshold=a.rag_relevance_threshold or 0.0,
        rag_kb_routing_enabled=getattr(a, 'rag_kb_routing_enabled', False) or False,
        rag_kb_routing_variable=getattr(a, 'rag_kb_routing_variable', None),
        semantic_cache_enabled=a.semantic_cache_enabled if a.semantic_cache_enabled is not None else True,
        semantic_cache_threshold=a.semantic_cache_threshold or 0.92,
        tool_ids=[t.id for t in a.tools],
        simulated_time=a.simulated_time,
        security_competitor_blacklist=a.security_competitor_blacklist,
        security_forbidden_topics=a.security_forbidden_topics,
        security_discount_policy=a.security_discount_policy,
        security_language_complexity=a.security_language_complexity,
        security_pii_filter=a.security_pii_filter,
        security_validator_ia=a.security_validator_ia,
        security_bot_protection=a.security_bot_protection,
        security_max_messages_per_session=a.security_max_messages_per_session,
        security_semantic_threshold=a.security_semantic_threshold,
        security_loop_count=a.security_loop_count,
        ui_primary_color=a.ui_primary_color,
        ui_header_color=a.ui_header_color,
        ui_chat_title=a.ui_chat_title,
        ui_welcome_message=a.ui_welcome_message,
        initial_message=a.initial_message,
        initial_question_message=a.initial_question_message,
        initial_ignore_message=a.initial_ignore_message,
        inbox_capture_enabled=a.inbox_capture_enabled,
        greeting_mode=a.greeting_mode or "prompt",
        question_mode=a.question_mode or "panel",
        ad_mode=a.ad_mode or "panel",
        qualification_questions=a.qualification_questions,
        qualification_labels=a.qualification_labels,
        qualification_criteria=a.qualification_criteria,
        qualification_final_action=a.qualification_final_action,
        qualification_final_action_trigger=getattr(a, 'qualification_final_action_trigger', 'all') or 'all',
        qualification_funnels=getattr(a, 'qualification_funnels', None),
        router_enabled=a.router_enabled,
        router_simple_model=a.router_simple_model,
        router_complex_model=a.router_complex_model,
        handoff_enabled=a.handoff_enabled,
        response_translation_enabled=a.response_translation_enabled,
        response_translation_fallback_lang=a.response_translation_fallback_lang or "portuguese"
    )

@router.put("/agents/{agent_id}", response_model=AgentConfig)
async def update_agent(agent_id: int, config: AgentConfig, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(
        select(AgentConfigModel)
        .options(selectinload(AgentConfigModel.tools), selectinload(AgentConfigModel.knowledge_bases))
        .where(AgentConfigModel.id == agent_id)
    )
    db_config = result.scalars().first()
    if not db_config: raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    db_config.name = config.name
    db_config.description = config.description
    db_config.model = config.model
    db_config.fallback_model = config.fallback_model
    db_config.temperature = config.temperature
    db_config.top_p = config.top_p
    db_config.top_k = config.top_k
    db_config.presence_penalty = config.presence_penalty
    db_config.frequency_penalty = config.frequency_penalty
    db_config.safety_settings = config.safety_settings
    db_config.model_settings = json.dumps(config.model_settings) if config.model_settings else "{}"
    db_config.is_active = config.is_active
    db_config.date_awareness = config.date_awareness
    db_config.date_awareness_past_days = config.date_awareness_past_days
    db_config.date_awareness_future_days = config.date_awareness_future_days
    db_config.system_prompt = config.system_prompt
    db_config.dynamic_prompt = config.dynamic_prompt
    db_config.pre_router_prompt = config.pre_router_prompt
    db_config.context_window = config.context_window
    db_config.knowledge_base = json.dumps(config.knowledge_base)
    db_config.rag_retrieval_count = config.rag_retrieval_count
    db_config.rag_translation_enabled = config.rag_translation_enabled
    db_config.rag_multi_query_enabled = config.rag_multi_query_enabled
    db_config.rag_rerank_enabled = config.rag_rerank_enabled
    db_config.rag_agentic_eval_enabled = config.rag_agentic_eval_enabled
    db_config.rag_parent_expansion_enabled = config.rag_parent_expansion_enabled
    db_config.rag_relevance_threshold = config.rag_relevance_threshold
    db_config.rag_kb_routing_enabled = config.rag_kb_routing_enabled
    db_config.rag_kb_routing_variable = config.rag_kb_routing_variable
    db_config.security_competitor_blacklist = config.security_competitor_blacklist
    db_config.security_forbidden_topics = config.security_forbidden_topics
    db_config.security_discount_policy = config.security_discount_policy
    db_config.security_language_complexity = config.security_language_complexity
    db_config.security_pii_filter = config.security_pii_filter
    db_config.security_bot_protection = config.security_bot_protection
    db_config.security_max_messages_per_session = config.security_max_messages_per_session
    db_config.security_semantic_threshold = config.security_semantic_threshold
    db_config.security_loop_count = config.security_loop_count
    db_config.security_validator_ia = config.security_validator_ia
    db_config.ui_primary_color = config.ui_primary_color
    db_config.ui_header_color = config.ui_header_color
    db_config.ui_chat_title = config.ui_chat_title
    db_config.ui_welcome_message = config.ui_welcome_message
    db_config.initial_message = config.initial_message
    db_config.initial_question_message = config.initial_question_message
    db_config.initial_ignore_message = config.initial_ignore_message
    db_config.inbox_capture_enabled = config.inbox_capture_enabled
    db_config.greeting_mode = config.greeting_mode
    db_config.question_mode = config.question_mode
    db_config.ad_mode = config.ad_mode
    db_config.qualification_questions = config.qualification_questions
    db_config.qualification_labels = config.qualification_labels
    db_config.qualification_criteria = config.qualification_criteria
    db_config.qualification_final_action = config.qualification_final_action
    db_config.qualification_final_action_trigger = config.qualification_final_action_trigger or "all"
    if config.qualification_funnels is not None:
        db_config.qualification_funnels = config.qualification_funnels
    if config.unanswered_handoff_limit is not None:
        db_config.unanswered_handoff_limit = config.unanswered_handoff_limit
    db_config.unanswered_question_prompt = config.unanswered_question_prompt
    db_config.router_enabled = config.router_enabled
    db_config.router_simple_model = config.router_simple_model
    db_config.router_complex_model = config.router_complex_model
    db_config.handoff_enabled = config.handoff_enabled
    db_config.response_translation_enabled = config.response_translation_enabled
    db_config.response_translation_fallback_lang = config.response_translation_fallback_lang or "portuguese"
    db_config.tool_prompts = config.tool_prompts
    if config.semantic_cache_enabled is not None:
        db_config.semantic_cache_enabled = config.semantic_cache_enabled
    if config.semantic_cache_threshold is not None:
        db_config.semantic_cache_threshold = config.semantic_cache_threshold

    # Sync Tools
    if config.tool_ids is not None:
        res_tools = await db.execute(select(ToolModel).where(ToolModel.id.in_(config.tool_ids)))
        db_config.tools = res_tools.scalars().all()

    # Sync Knowledge Bases
    if config.knowledge_base_ids is not None:
        res_kbs = await db.execute(select(KnowledgeBaseModel).where(KnowledgeBaseModel.id.in_(config.knowledge_base_ids)))
        db_config.knowledge_bases = res_kbs.scalars().all()

    await db.commit()
    return await get_agent(agent_id, db)

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(AgentConfigModel).where(AgentConfigModel.id == agent_id))
    agent = result.scalars().first()
    if not agent: raise HTTPException(status_code=404, detail="Agent not found")
    
    # 🛡️ Snapshot de Segurança Pré-Exclusão no Cofre de Prompts
    try:
        from api.routers.prompt_vault import create_pre_deletion_backup
        await create_pre_deletion_backup(agent, db)
    except Exception as e:
        logger.warning(f"Não foi possível criar backup pré-exclusão no cofre: {e}")

    await db.delete(agent)
    await db.commit()
    return {"message": "Agent deleted"}

@router.post("/agents/batch-delete")
async def batch_delete_agents(request: BulkAgentDeleteRequest, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    if not request.agent_ids: return {"message": "No agents to delete"}
    
    # 🛡️ Snapshot de Segurança Pré-Exclusão no Cofre de Prompts para cada agente
    try:
        from api.routers.prompt_vault import create_pre_deletion_backup
        agents_res = await db.execute(select(AgentConfigModel).where(AgentConfigModel.id.in_(request.agent_ids)))
        for agent in agents_res.scalars().all():
            await create_pre_deletion_backup(agent, db)
    except Exception as e:
        logger.warning(f"Não foi possível criar backups pré-exclusão em lote no cofre: {e}")

    await db.execute(delete(AgentConfigModel).where(AgentConfigModel.id.in_(request.agent_ids)))
    await db.commit()
    return {"message": f"Deleted {len(request.agent_ids)} agents"}

@router.post("/agents/{agent_id}/toggle_status")
async def toggle_agent_status(agent_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(AgentConfigModel).where(AgentConfigModel.id == agent_id))
    agent = result.scalars().first()
    if not agent: raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_active = not agent.is_active
    await db.commit()
    return {"message": f"Agent {'activated' if agent.is_active else 'paused'}", "is_active": agent.is_active}

@router.post("/agents/{agent_id}/duplicate", response_model=AgentConfig)
async def duplicate_agent(agent_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    """Duplica um agente existente com todas as suas configurações e associações."""
    result = await db.execute(
        select(AgentConfigModel)
        .options(selectinload(AgentConfigModel.tools), selectinload(AgentConfigModel.knowledge_bases))
        .where(AgentConfigModel.id == agent_id)
    )
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cols = {c.name: getattr(agent, c.name) for c in agent.__table__.columns if c.name != "id"}
    cols["name"] = f"{agent.name} (Cópia)"
    
    new_agent = AgentConfigModel(**cols)
    new_agent.tools = list(agent.tools)
    new_agent.knowledge_bases = list(agent.knowledge_bases)
    
    db.add(new_agent)
    await db.commit()
    await db.refresh(new_agent)

    reloaded = await db.execute(
        select(AgentConfigModel)
        .options(selectinload(AgentConfigModel.tools), selectinload(AgentConfigModel.knowledge_bases))
        .where(AgentConfigModel.id == new_agent.id)
    )
    saved_agent = reloaded.scalars().first()
    return db_to_pydantic_agent(saved_agent)

@router.post("/agents/{agent_id}/generate-description")
async def generate_agent_description(
    agent_id: int, 
    db: AsyncSession = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    """Gera uma descrição concisa do agente usando IA para contextualizar o roteador de mensagens (Pre-Router)."""
    result = await db.execute(
        select(AgentConfigModel)
        .options(selectinload(AgentConfigModel.tools), selectinload(AgentConfigModel.knowledge_bases))
        .where(AgentConfigModel.id == agent_id)
    )
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave OPENAI_API_KEY não configurada no servidor.")

    import openai
    client = openai.AsyncOpenAI(api_key=api_key)
    
    tools_summary = ", ".join([t.name for t in agent.tools]) if agent.tools else "Nenhuma"
    prompt = (
        f"Você é um assistente especialista em criar descrições curtas e operacionais de agentes de IA.\n"
        f"Analise as informações do agente abaixo e gere um resumo de 1 ou 2 frases curtas (máximo 160 caracteres) "
        f"descrevendo o papel, o nicho e quando este agente deve ser acionado pelo roteador de mensagens.\n\n"
        f"Nome: {agent.name}\n"
        f"Prompt do Sistema:\n{agent.system_prompt[:2000] if agent.system_prompt else 'Assistente geral'}\n"
        f"Ferramentas Disponíveis: {tools_summary}\n\n"
        f"Retorne APENAS a frase de descrição, sem aspas, sem introdução e sem explicações."
    )
    
    model_to_use = getattr(agent, "router_simple_model", None) or "gpt-4o-mini"
    
    try:
        completion = await client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        description = completion.choices[0].message.content.strip()
        if description.startswith('"') and description.endswith('"'):
            description = description[1:-1].strip()
            
        agent.description = description
        await db.commit()
        await db.refresh(agent)
        
        return {
            "description": agent.description,
            "message": "Descrição gerada com sucesso"
        }
    except Exception as e:
        logger.error(f"Erro ao gerar descrição do agente {agent_id} com IA: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao gerar descrição: {str(e)}")

# --- PROMPT VERSIONING (DRAFTS) ---

@router.get("/agents/{agent_id}/drafts", response_model=List[PromptDraft])
async def list_agent_drafts(agent_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(PromptDraftModel).where(PromptDraftModel.agent_id == agent_id).order_by(PromptDraftModel.created_at.desc()))
    return result.scalars().all()

@router.post("/agents/{agent_id}/drafts", response_model=PromptDraft)
async def create_agent_draft(agent_id: int, draft: PromptDraft, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    new_draft = PromptDraftModel(
        agent_id=agent_id,
        prompt_text=draft.prompt_text,
        version_name=draft.version_name or f"v{int(datetime.now(timezone.utc).timestamp())}",
        description=draft.description,
        character_count=len(draft.prompt_text),
        token_count=len(draft.prompt_text) // 4
    )
    db.add(new_draft)
    await db.commit()
    await db.refresh(new_draft)
    return new_draft

@router.put("/drafts/{draft_id}", response_model=PromptDraft)
async def update_agent_draft(draft_id: int, draft: PromptDraft, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(PromptDraftModel).where(PromptDraftModel.id == draft_id))
    db_draft = result.scalars().first()
    if not db_draft: raise HTTPException(status_code=404, detail="Draft not found")
    
    db_draft.version_name = draft.version_name
    db_draft.description = draft.description
    db_draft.prompt_text = draft.prompt_text
    db_draft.character_count = len(draft.prompt_text)
    db_draft.token_count = len(draft.prompt_text) // 4
    
    await db.commit()
    await db.refresh(db_draft)
    return db_draft

@router.delete("/drafts/{draft_id}")
async def delete_agent_draft(draft_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    result = await db.execute(select(PromptDraftModel).where(PromptDraftModel.id == draft_id))
    db_draft = result.scalars().first()
    if not db_draft: raise HTTPException(status_code=404, detail="Draft not found")
    
    await db.delete(db_draft)
    await db.commit()
    return {"message": "Draft deleted"}

@router.post("/agents/{agent_id}/drafts/{draft_id}/restore")
async def restore_agent_draft(agent_id: int, draft_id: int, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    # Busca o rascunho
    result = await db.execute(select(PromptDraftModel).where(PromptDraftModel.id == draft_id, PromptDraftModel.agent_id == agent_id))
    db_draft = result.scalars().first()
    if not db_draft: raise HTTPException(status_code=404, detail="Draft not found")
    
    # Busca o agente
    agent_result = await db.execute(select(AgentConfigModel).where(AgentConfigModel.id == agent_id))
    db_agent = agent_result.scalars().first()
    if not db_agent: raise HTTPException(status_code=404, detail="Agent not found")
    
    # Restaura o prompt
    db_agent.system_prompt = db_draft.prompt_text
    await db.commit()
    
    return {"message": "Prompt restored successfully", "system_prompt": db_agent.system_prompt}

# --- PROMPT ADVISOR (Consultor de Prompt) ---

@router.post("/api/prompt/advisor")
async def prompt_advisor(request: PromptAdvisorRequest, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    """
    Consultor especialista em engenharia de prompt.
    Analisa o conteúdo do prompt e responde perguntas do usuário sobre melhorias.
    """
    try:
        logger.info(f"🔮 Advisor: Iniciando análise para query: '{request.user_query[:50]}...'")

        context = (
            "Você é o Consultor Especialista em Engenharia de Prompt do 'Agente Jaime'.\n"
            "Sua missão é ajudar o usuário a refinar o prompt do agente de IA dele.\n\n"
            "CONTEÚDO ATUAL DO PROMPT:\n"
            "---\n"
            f"{request.prompt_content}\n"
            "---\n\n"
            "CONFIGURAÇÕES DE SAUDAÇÃO:\n"
            f"- Saudação Padrão: {request.initial_message or 'Não configurada'}\n"
            f"- Mensagem Pós-Pergunta: {request.initial_question_message or 'Não configurada'}\n"
            f"- Whitelist de Anúncios: {json.dumps(request.ignore_messages) if request.ignore_messages else 'Vazia'}\n\n"
            "HISTÓRICO DA CONVERSA:\n"
            f"{json.dumps(request.history, indent=2)}\n\n"
            "INSTRUÇÕES:\n"
            "1. Se o usuário mandar apenas uma saudação (ex: 'oi', 'olá', 'oie'), responda apenas com algo educado como "
            "'Olá! Sou seu Consultor de Prompt. Como posso ajudar você hoje?' e NÃO faça a análise do prompt ainda.\n"
            "2. Seja direto e profissional.\n"
            "3. Identifique ambiguidades, falta de instruções ou tom inadequado.\n"
            "4. Sugira melhorias específicas de estrutura ou conteúdo.\n"
            "5. Se o usuário solicitar uma alteração direta (ex: 'remova X', 'mude Y'), instrua-o a detalhar o que deseja "
            "no chat e clicar no botão 'Refinar Prompt Automaticamente' para que a mudança seja aplicada ao editor."
        )

        client = get_openai_client("gpt-4o")
        if not client:
            raise HTTPException(status_code=500, detail="OpenAI client not configured.")

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": request.user_query}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content
        in_tokens = response.usage.prompt_tokens
        out_tokens = response.usage.completion_tokens
        cost_usd, cost_brl = calculate_ai_cost("gpt-4o", in_tokens, out_tokens)

        # Log financeiro (não-crítico)
        try:
            db.add(InteractionLog(
                agent_id=None,
                session_id="advisor_chat",
                user_message=request.user_query,
                agent_response=content,
                model_used="gpt-4o",
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                cost_usd=cost_usd,
                cost_brl=cost_brl,
            ))
            await db.commit()
            logger.info("📊 Advisor: Log financeiro salvo.")
        except Exception as db_err:
            logger.warning(f"⚠️ Advisor: Falha ao salvar log financeiro: {db_err}")

        return {"content": content, "cost_brl": cost_brl}

    except Exception as e:
        logger.error(f"💥 Advisor: Erro crítico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno no Consultor: {str(e)}")


# --- PROMPT REFINE ---

@router.post("/api/prompt/refine")
async def refine_prompt(request: PromptRefineRequest, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    """
    Reescreve automaticamente o prompt aplicando as melhorias sugeridas no histórico
    e as instruções adicionais do usuário.
    """
    try:
        user_instr_clause = f"\nINSTRUÇÕES ADICIONAIS DO USUÁRIO:\n{request.user_instructions}\n" if request.user_instructions else ""

        context = f"""
        Você é o Engenheiro de Prompt Sênior do 'Agente Jaime'.
        Sua tarefa é REESCREVER o prompt do usuário aplicando as melhorias sugeridas no histórico e seguindo as instruções extras.

        PROMPT ATUAL:
        ---
        {request.prompt_content}
        ---

        HISTÓRICO DA DISCUSSÃO:
        {json.dumps(request.history, indent=2)}
        {user_instr_clause}
        DIRETRIZES DE REESCRITA:
        1. Mantenha o tom e a voz do agente original, mas corrija as falhas apontadas.
        2. Melhore a clareza, remova contradições e otimize a estrutura.
        3. Se houver 'INSTRUÇÕES ADICIONAIS DO USUÁRIO', elas têm PRIORIDADE MÁXIMA.

        FORMATO DE RESPOSTA OBRIGATÓRIO (JSON):
        Retorne um objeto JSON com exatamente estes dois campos:
        - "new_prompt": O novo conteúdo completo do prompt.
        - "summary": Um resumo curto em português das alterações realizadas.
        """
        client = get_openai_client("gpt-4o")

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": "Reescreva o prompt agora e forneça o resumo das alterações em formato JSON."}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        res_data = json.loads(response.choices[0].message.content)
        content = res_data.get("new_prompt")
        summary = res_data.get("summary")
        in_tokens = response.usage.prompt_tokens
        out_tokens = response.usage.completion_tokens
        cost_usd, cost_brl = calculate_ai_cost("gpt-4o", in_tokens, out_tokens)

        # Log financeiro
        db.add(InteractionLog(
            agent_id=None,
            session_id="prompt_refine",
            user_message="Refinamento automático de prompt",
            agent_response=summary,
            model_used="gpt-4o",
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            cost_usd=cost_usd,
            cost_brl=cost_brl,
        ))
        await db.commit()

        return {"new_prompt": content, "summary": summary, "cost_brl": cost_brl}

    except Exception as e:
        logger.error(f"Erro ao refinar prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- CHAT PLAYGROUND ---

@router.post("/api/chat/playground")
async def chat_playground(request: MessageRequest, db: AsyncSession = Depends(get_db), _: None = Depends(verify_api_key)):
    """Simula troca de mensagens com um agente (playground de teste)."""
    return await process_message(
        db=db,
        message=request.message,
        session_id=request.session_id or "playground",
        agent_id=request.agent_id,
        context_variables=request.context_variables or {},
        model_override=request.model_override,
        system_prompt_override=request.system_prompt_override
    )

# --- MODEL DISCOVERY ---

@router.get("/models")
async def list_models(_: None = Depends(verify_api_key)):
    from config_store import discover_models
    # Busca modelos reais das APIs (com cache de 1h)
    discovered = discover_models()
    return {
        "openai_connected": bool(os.getenv("OPENAI_API_KEY")),
        "gemini_connected": bool(os.getenv("GEMINI_API_KEY")),
        "anthropic_connected": bool(os.getenv("ANTHROPIC_API_KEY")),
        "models": [
            {
                "id": m["id"],
                "real_id": m["real_id"],
                "supports_tools": m["supports_tools"],
                "supports_temperature": m["supports_temperature"],
                "input": m.get("input", 0),
                "output": m.get("output", 0),
                "context_window": m.get("context_window", "Unknown"),
                "provider": m.get("provider", "openai"),
                "available_versions": m.get("available_versions", [])
            }
            for m in discovered
        ]
    }

@router.get("/fine-tuning/models")
async def list_finetuned_models(_: None = Depends(verify_api_key)):
    """Lista todos os modelos fine-tuned disponíveis na conta (para usar nos agentes)."""
    import openai
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []
        
    client = openai.AsyncOpenAI(api_key=api_key)
    try:
        models_page = await client.models.list()
        # Filtra apenas modelos que começam com ft: (fine-tuned) e ignora checkpoints na listagem padrão para não poluir
        ft_models = [m for m in models_page.data if m.id.startswith("ft:") and ":ckpt-" not in m.id]
        return [{"id": m.id, "created": m.created} for m in ft_models]
    except Exception as e:
        logger.error(f"Erro ao buscar modelos fine-tuning: {e}")
        return [] # Retorna lista vazia para não quebrar o frontend

@router.get("/agents/{agent_id}/chatwoot-labels")
async def get_chatwoot_labels(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Busca a lista de etiquetas disponíveis no ZapVoice/Chatwoot associado ao agente, com fallback."""
    from models import WebhookConfigModel, WebhookEventModel
    import httpx
    import os

    # 1. Buscar o webhook associado a este agente
    result = await db.execute(
        select(WebhookConfigModel)
        .where(WebhookConfigModel.agent_id == agent_id)
        .limit(1)
    )
    wh = result.scalars().first()
    if not wh or not wh.zapvoice_url:
        # Se não achou por agent_id, tentar buscar no secondary_agent_ids
        result_sec = await db.execute(
            select(WebhookConfigModel)
            .where(WebhookConfigModel.secondary_agent_ids.like(f"%{agent_id}%"))
            .limit(1)
        )
        wh = result_sec.scalars().first()

    # Se ainda não achou, pegar qualquer webhook configurado no banco com URL e Token como fallback global
    if not wh or not wh.zapvoice_url:
        result_any = await db.execute(
            select(WebhookConfigModel)
            .where(
                WebhookConfigModel.zapvoice_url.isnot(None) & (WebhookConfigModel.zapvoice_url != "")
            )
            .order_by(WebhookConfigModel.id.desc())
            .limit(1)
        )
        wh = result_any.scalars().first()

    zv_url = None
    zv_token = None
    zv_client_id = None

    if wh:
        zv_url = wh.zapvoice_url
        zv_token = wh.zapvoice_api_token
        zv_client_id = str(wh.zapvoice_client_id) if wh.zapvoice_client_id else None

    # Fallback para variáveis de ambiente
    if not zv_url:
        zv_url = os.getenv("ZAPVOICE_URL") or os.getenv("CHATWOOT_URL")
    if not zv_token:
        zv_token = os.getenv("ZAPVOICE_API_TOKEN") or os.getenv("CHATWOOT_API_TOKEN")

    if not zv_url or not zv_token:
        return []

    zv_url = zv_url.rstrip("/")

    # 1. Tentar ZapVoice primeiro (endpoint padrão /api/chat/labels)
    try:
        zap_api_url = zv_url
        if not zap_api_url.endswith("/api"):
            zap_api_url = f"{zap_api_url}/api"

        headers = {"Authorization": f"Bearer {zv_token}"}
        if zv_client_id:
            headers["X-Client-ID"] = zv_client_id

        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(f"{zap_api_url}/chat/labels", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    labels = []
                    for item in data:
                        if isinstance(item, dict):
                            title = item.get("name") or item.get("title") or item.get("label")
                            if title:
                                labels.append(title)
                        elif isinstance(item, str):
                            labels.append(item)
                    if labels:
                        return labels
    except Exception as e:
        logger.warning(f"Tentativa ZapVoice falhou ao buscar labels: {e}")

    # 2. Fallback para Chatwoot nativo (/api/v1/accounts/{account_id}/labels)
    try:
        account_id = os.getenv("CHATWOOT_ACCOUNT_ID") or "1"
        labels_url = f"{zv_url}/api/v1/accounts/{account_id}/labels"
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(labels_url, headers={"api_access_token": zv_token})
            if resp.status_code == 200:
                payload = resp.json()
                labels_data = payload.get("payload", payload) if isinstance(payload, dict) else payload
                if isinstance(labels_data, list):
                    return [l.get("title") for l in labels_data if isinstance(l, dict) and l.get("title")]
    except Exception as e:
        logger.error(f"Erro ao buscar labels no Chatwoot fallback: {e}")

    return []

