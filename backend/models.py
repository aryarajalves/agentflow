from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, Table, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from database import Base

# Tabela de associação para Muitos-para-Muitos entre Agentes e Ferramentas
agent_tools = Table(
    "agent_tools",
    Base.metadata,
    Column("agent_id", Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), primary_key=True),
    Column("tool_id", Integer, ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True),
)

# Tabela de associação para Muitos-para-Muitos entre Agentes e Bases de Conhecimento
agent_knowledge_bases = Table(
    "agent_knowledge_bases",
    Base.metadata,
    Column("agent_id", Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), primary_key=True),
    Column("knowledge_base_id", Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
)

class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="SET NULL"), nullable=True, index=True) # Link to agent
    session_id = Column(String, index=True, nullable=True) # New: Identify memory scope
    user_message = Column(Text)
    agent_response = Column(Text)
    model_used = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cached_tokens = Column(Integer, default=0, nullable=True)
    cost_usd = Column(Float)
    cost_brl = Column(Float)
    handoff_to = Column(String, nullable=True) # Ex: "suporte", "vendas", "humano"
    debug_info = Column(Text, nullable=True) # JSON stored as string
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("idx_interaction_logs_agent_time", "agent_id", "timestamp"),
        Index("idx_interaction_logs_session_time", "session_id", "timestamp"),
    )

class SessionSummary(Base):
    __tablename__ = "session_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, unique=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"))
    summary_text = Column(Text)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    cost_brl = Column(Float, default=0.0)
    is_test_session = Column(Boolean, default=False)
    test_report = Column(JSON, nullable=True) # Armazena o JSON do relatório do tester
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class KnowledgeBaseModel(Base):
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, default="Nova Base")
    description = Column(Text, nullable=True)
    kb_type = Column(String, default="qa")
    question_label = Column(String, default="Pergunta")
    answer_label = Column(String, default="Resposta")
    metadata_label = Column(String, default="Metadado")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    items = relationship("KnowledgeItemModel", back_populates="knowledge_base", cascade="all, delete-orphan")
    
    # Legacy link (1-to-N)
    agents = relationship("AgentConfigModel", back_populates="linked_knowledge_base")
    
    # New M2M link
    linked_agents = relationship("AgentConfigModel", secondary=agent_knowledge_bases, back_populates="knowledge_bases")

from pgvector.sqlalchemy import Vector

class KnowledgeItemModel(Base):
    __tablename__ = "knowledge_items"
    
    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"))
    question = Column(Text)
    answer = Column(Text)
    metadata_val = Column(Text)
    category = Column(String, nullable=True, default="Geral")
    source_metadata = Column(Text, nullable=True) # JSON store for page_number, source_file, etc.
    question_variations = Column(JSON, nullable=True, default=list) # Formas alternativas de perguntar
    embedding = Column(Vector(1536), nullable=True) # OpenAI small is 1536 dims
    parent_id = Column(Integer, ForeignKey("knowledge_items.id", ondelete="SET NULL"), nullable=True)
    
    knowledge_base = relationship("KnowledgeBaseModel", back_populates="items")
    children = relationship("KnowledgeItemModel", backref="parent", remote_side=[id])

    __table_args__ = (
        Index("idx_knowledge_items_kb_id", "knowledge_base_id"),
        Index("idx_knowledge_items_parent_id", "parent_id"),
    )

class AgentConfigModel(Base):
    __tablename__ = "agent_config"

    id = Column(Integer, primary_key=True)
    name = Column(String, default="Novo Agente") # Nome do agente
    description = Column(Text, nullable=True) # Descrição do agente
    model = Column(String, default="gpt-5.2")
    fallback_model = Column(String, nullable=True)  # Modelo de backup
    temperature = Column(Float, default=1.0)  # Controle de criatividade (0-2)
    top_p = Column(Float, default=1.0)  # Controle de diversidade (0-1)
    top_k = Column(Integer, default=40)
    presence_penalty = Column(Float, default=0.0)
    frequency_penalty = Column(Float, default=0.0)
    safety_settings = Column(String, default="standard")
    is_active = Column(Boolean, default=True)  # Status do agente
    date_awareness = Column(Boolean, default=False)  # Consciência temporal (datas reais)
    date_awareness_past_days = Column(Integer, default=7, nullable=True)  # Dias passados no contexto temporal
    date_awareness_future_days = Column(Integer, default=7, nullable=True)  # Dias futuros no contexto temporal
    system_prompt = Column(Text, default="Você é um assistente útil e inteligente.")
    dynamic_prompt = Column(Text, default="", nullable=True)
    pre_router_prompt = Column(Text, nullable=True)  # Prompt customizado do Pre-Router; se vazio/nulo, usa DEFAULT_PRE_ROUTER_PROMPT_TEMPLATE (agent_core/logic/pre_router.py)
    context_window = Column(Integer, default=5)
    knowledge_base = Column(Text, default="[]") # Legacy JSON list of FAQs
    simulated_time = Column(String, nullable=True) # HH:MM for time override
    
    # RAG Settings
    rag_retrieval_count = Column(Integer, default=5) # New: Top-K config
    rag_translation_enabled = Column(Boolean, default=False)
    rag_multi_query_enabled = Column(Boolean, default=True)
    rag_rerank_enabled = Column(Boolean, default=True)
    rag_agentic_eval_enabled = Column(Boolean, default=True)
    rag_parent_expansion_enabled = Column(Boolean, default=False)
    rag_relevance_threshold = Column(Float, default=0.0)  # Relevância mínima (0-1) para um item ser enviado ao contexto do RAG. 0 = sem filtro.
    rag_kb_routing_enabled = Column(Boolean, default=False)  # Roteamento Agêntico de Bases
    rag_kb_routing_variable = Column(String, nullable=True)  # Nome da variável de contexto usada para guiar o roteamento (ex: curso_interesse)
    # Semantic Cache Settings
    semantic_cache_enabled = Column(Boolean, default=True)
    semantic_cache_threshold = Column(Float, default=0.92)  # Similaridade mínima (0.70 a 0.99)
    tool_prompts = Column(JSON, nullable=True)  # Prompts customizados por ferramenta
    
    # Security Guardrails
    security_competitor_blacklist = Column(Text, nullable=True) # Ex: "Coca-Cola, Pepsi"
    security_forbidden_topics = Column(Text, nullable=True) # Ex: "Politics, Religion"
    security_discount_policy = Column(Text, nullable=True) # Ex: "Max 10%"
    security_language_complexity = Column(String, default="standard") # standard, simple, technical
    security_pii_filter = Column(Boolean, default=False) # Strip email/cpf?
    security_validator_ia = Column(Boolean, default=False)
    
    # Bot-to-Bot Defense (Anti-Loop)
    security_bot_protection = Column(Boolean, default=False)
    security_max_messages_per_session = Column(Integer, default=20)
    security_semantic_threshold = Column(Float, default=0.85)
    security_loop_count = Column(Integer, default=3)
    
    # UI Customization
    ui_primary_color = Column(String, default="#6366f1")
    ui_header_color = Column(String, default="#0f172a")
    ui_chat_title = Column(String, default="Suporte Inteligente")
    ui_welcome_message = Column(Text, default="Olá! Como posso te ajudar hoje?")
    initial_message = Column(Text, nullable=True)
    initial_question_message = Column(Text, nullable=True)
    initial_ignore_message = Column(Text, nullable=True) # Mensagem de anúncio para ignorar como pergunta
    inbox_capture_enabled = Column(Boolean, default=True)
    
    # Greeting and dynamic flow modes: "prompt" (default) or "panel"
    greeting_mode = Column(String, default="prompt")
    question_mode = Column(String, default="panel")
    ad_mode = Column(String, default="panel")

    
    # Cost Router
    router_enabled = Column(Boolean, default=False)
    router_simple_model = Column(String, default="gpt-4o-mini")
    router_simple_fallback_model = Column(String, nullable=True)
    router_complex_model = Column(String, default="gpt-4o")
    router_complex_fallback_model = Column(String, nullable=True)

    # Response Translation
    response_translation_enabled = Column(Boolean, default=False)
    response_translation_fallback_lang = Column(String, default="portuguese")

    # Legacy FK (Single KB)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True)
    linked_knowledge_base = relationship("KnowledgeBaseModel", back_populates="agents")
    
    # New M2M Relationship
    knowledge_bases = relationship("KnowledgeBaseModel", secondary=agent_knowledge_bases, back_populates="linked_agents")
    
    # Relacionamento com as ferramentas selecionadas
    tools = relationship("ToolModel", secondary=agent_tools, back_populates="agents")
    
    # Relacionamento com rascunhos de prompt
    prompt_drafts = relationship("PromptDraftModel", back_populates="agent", cascade="all, delete-orphan")
    
    handoff_enabled = Column(Boolean, default=False) # Permite que este agente use a ferramenta de handoff
    model_settings = Column(Text, default="{}") # JSON store for per-slot configurations (temperature, top_p, etc)
    qualification_questions = Column(Text, nullable=True) # JSON array de perguntas para qualificação de lead
    qualification_labels = Column(Text, nullable=True) # JSON array de etiquetas a serem aplicadas no Chatwoot
    qualification_criteria = Column(Text, nullable=True) # Diretrizes e critérios do lead scoring
    qualification_final_action = Column(Text, nullable=True) # Pergunta / Prompt final de fechamento após qualificação
    qualification_final_action_trigger = Column(String(100), default="all", nullable=True) # Condição de disparo do fechamento (all, hot, hot_warm, warm, cold)
    qualification_funnels = Column(JSON, nullable=True) # Lista de múltiplos funis de qualificação independentes
    unanswered_handoff_limit = Column(Integer, default=2, nullable=True) # Limite de dúvidas sem resposta antes de transferir para suporte humano (0 ou NULL desativa)
    unanswered_question_prompt = Column(Text, nullable=True) # Diretriz personalizada de resposta ao chamar registrar_duvida_sem_resposta

    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ToolModel(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text)
    parameters_schema = Column(Text) # Stored as JSON string
    webhook_url = Column(String, nullable=True)
    labels_to_add = Column(Text, nullable=True) # JSON list of labels to add
    labels_to_remove = Column(Text, nullable=True) # JSON list of labels to remove
    confirmation_message = Column(Text, nullable=True) # Mensagem enviada ao acionar a ferramenta
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relacionamento reverso com agentes
    agents = relationship("AgentConfigModel", secondary=agent_tools, back_populates="tools")

class PromptDraftModel(Base):
    __tablename__ = "prompt_drafts"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), nullable=False)
    prompt_text = Column(Text, nullable=False)
    version_name = Column(String, nullable=True) # Ex: "Rascunho de Segunda"
    description = Column(Text, nullable=True) # Descrição da versão
    character_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    agent = relationship("AgentConfigModel", back_populates="prompt_drafts")

class UserMemoryModel(Base):
    __tablename__ = "user_memory"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, index=True) # ID da sessão ou WhatsApp do usuário
    key = Column(String, index=True) # Nome do fato (ex: 'nome_cliente', 'objetivo_vida')
    value = Column(Text) # Valor do fato extraído
    confidence = Column(Float, default=1.0) # Nível de certeza da IA
    source_message = Column(Text, nullable=True) # Trecho original para referência
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("session_id", "key", name="uq_user_memory_session_key"),
        Index("idx_user_memory_session_updated", "session_id", "updated_at"),
    )

class FeedbackLog(Base):
    """Armazena pares de treinamento para o pipeline de fine-tuning.
    Cada registro representa uma interação avaliada por um humano.
    """
    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, index=True)
    interaction_log_id = Column(Integer, ForeignKey("interaction_logs.id", ondelete="SET NULL"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), nullable=False)

    # O par de treinamento (matéria-prima do fine-tuning)
    user_message = Column(Text, nullable=False)           # A pergunta do usuário
    original_response = Column(Text, nullable=True)       # O que o agente respondeu (pode ser bom ou ruim)
    corrected_response = Column(Text, nullable=True)      # A resposta ideal definida pelo humano
    system_prompt_snapshot = Column(Text, nullable=True)  # Snapshot do system prompt no momento

    # Classificação do feedback
    rating = Column(String, default="negative")           # 'positive' | 'negative'
    correction_note = Column(Text, nullable=True)         # Nota opcional do revisor

    # Controle do pipeline de exportação e treinamento
    exported_to_finetune = Column(Boolean, default=False)
    finetune_job_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class GoogleTokensModel(Base):
    """Armazena tokens de autenticação do Google Calendar para cada agente."""
    __tablename__ = "google_tokens"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), unique=True, nullable=True)
    
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_uri = Column(String, default="https://oauth2.googleapis.com/token")
    client_id = Column(String, nullable=True)
    client_secret = Column(String, nullable=True)
    scopes = Column(Text, nullable=True)
    expiry = Column(DateTime(timezone=True), nullable=True)
    default_event_color = Column(String, nullable=True)
    add_user_email = Column(Boolean, default=False, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    agent = relationship("AgentConfigModel")

class GlobalContextVariableModel(Base):
    __tablename__ = "global_context_variables"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    type = Column(String, default="string") # Novo campo: string, number, boolean
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    extraction_method = Column(String, default="integration")
    extraction_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False) # Armazena hash Argon2id (com Pepper global configurado no ambiente)
    role = Column(String, default="Usuário") # "Super Admin", "Admin", "Usuário"
    status = Column(String, default="ATIVO") # "ATIVO", "INATIVO"
    company_name = Column(String, nullable=True)
    company_logo = Column(Text, nullable=True)
    company_logo_size = Column(String, nullable=True, default="medium")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class UserInviteModel(Base):
    __tablename__ = "user_invites"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False) # "Admin", "Usuário"
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class UnansweredQuestionModel(Base):
    __tablename__ = "unanswered_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(String, index=True, nullable=True)
    question = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    status = Column(String, default="PENDENTE") # PENDENTE, RESPONDIDA, DESCARTADA
    source = Column(String, nullable=True) # 'chat' ou 'chatwoot' ou 'playground' ou 'api'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class SupportRequestModel(Base):
    __tablename__ = "support_requests"
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="SET NULL"))
    webhook_config_id = Column(Integer, ForeignKey("webhook_configs.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String, nullable=False)
    user_name = Column(String)
    user_email = Column(String)
    contact_phone = Column(String)
    status = Column(String, default="OPEN")
    summary = Column(Text)
    reason = Column(Text)
    account_id = Column(String, nullable=True)
    conversation_id = Column(String, nullable=True)
    extracted_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class WebhookConfigModel(Base):
    __tablename__ = "webhook_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    memory_token = Column(String, unique=True, nullable=True, index=True)
    leads_table = Column(String, nullable=False, default="leads")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    disable_ai_responses = Column(Boolean, default=False) # Se True, salva dados/memória mas bloqueia resposta do agente de IA
    delay_seconds = Column(Integer, default=30)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="SET NULL"), nullable=True)
    blocked_messages = Column(Text, nullable=True)  # JSON array of strings
    allowed_contacts = Column(Text, nullable=True)  # JSON array of phone numbers; empty = all allowed
    zapvoice_url = Column(String, nullable=True)        # Ex: http://localhost:8000
    zapvoice_api_token = Column(String, nullable=True)  # User access token / API key
    zapvoice_client_id = Column(String, nullable=True)   # ID do cliente no ZapVoice
    labels_on_message = Column(Text, nullable=True)     # JSON array: etiquetas adicionadas em toda msg
    delete_keywords = Column(Text, nullable=True)       # JSON array: palavras que disparam deleção
    delete_message = Column(Text, nullable=True)        # Mensagem enviada antes de deletar o contato
    delete_labels = Column(Text, nullable=True)         # JSON array: etiquetas que substituirão as atuais no reset
    response_delay_seconds = Column(Integer, default=0) # Delay em segundos antes de enviar resposta ao usuário
    split_response_enabled = Column(Boolean, default=True) # Se True, quebra a resposta da IA em várias mensagens (por \n\n); se False, envia em bloco único
    window_close_label = Column(String, nullable=True)   # Etiqueta a remover no Chatwoot quando janela 24h expirar
    followup_enabled = Column(Boolean, default=False)    # Ativar follow-up automático
    followup_steps = Column(Text, nullable=True)         # JSON: [{delay_hours}, ...]
    followup_funnels = Column(Text, nullable=True)       # JSON: [{id, name, is_default, steps: [...]}, ...]
    followup_business_hours = Column(Text, nullable=True) # JSON: {enabled, start, end, weekdays, saturday, sunday}
    followup_cancel_label = Column(String, nullable=True) # Etiqueta(s) no ZapVoice para desativar 100% o follow-up/disparos
    followup_required_label = Column(String, nullable=True) # Etiqueta(s) no ZapVoice necessárias para ativar o follow-up
    followup_add_label = Column(String, nullable=True) # Etiqueta no ZapVoice adicionada à conversa ao enviar follow-up
    followup_on_reply = Column(String, default="stop", nullable=True) # Comportamento ao responder: 'stop' (encerrar), 'continue_next' (avançar), 'restart' (reiniciar)
    abandonment_delay_value = Column(Integer, default=24, nullable=True) # Tempo de inatividade após última tentativa para mover a 'Não Converteu'
    abandonment_delay_unit = Column(String(20), default="hours", nullable=True) # 'minutes', 'hours', 'days'
    purchased_label = Column(String, nullable=True) # Etiqueta no ZapVoice que indica compra realizada / aluno
    ignore_by_label = Column(String, nullable=True)     # Se o contato tiver essa etiqueta, a automação para
    negative_feedback_label = Column(String, nullable=True) # Etiqueta aplicada ao contato no primeiro emoji negativo
    
    # Automação de Suporte Humano (Handoff)
    handoff_labels_to_add = Column(Text, nullable=True)     # JSON: ["etiqueta1", ...]
    handoff_labels_to_remove = Column(Text, nullable=True)  # JSON: ["etiqueta2", ...]
    handoff_keyword = Column(String, nullable=True)         # Palavra-chave para acionar suporte humano
    handoff_message = Column(Text, nullable=True)           # Mensagem enviada ao usuário ao acionar
    
    # Automação de Retorno ao Agente (Robô Handoff)
    ai_handoff_labels_to_add = Column(Text, nullable=True)     # JSON: ["etiqueta1", ...]
    ai_handoff_labels_to_remove = Column(Text, nullable=True)  # JSON: ["etiqueta2", ...]
    ai_handoff_keyword = Column(String, nullable=True)         # Palavra-chave para retornar ao robô
    ai_handoff_message = Column(Text, nullable=True)           # Mensagem enviada ao retornar
    
    # Media Processing Controls
    process_audio = Column(Boolean, default=True)
    process_image = Column(Boolean, default=True)
    
    # Multi-Agent Support
    secondary_agent_ids = Column(Text, nullable=True) # JSON array of IDs
    
    # Memory Sync Configuration
    memory_sync_enabled = Column(Boolean, default=False)
    memory_phone_path = Column(String, default="phone")
    memory_name_path = Column(String, nullable=True)
    memory_mappings = Column(Text, nullable=True) # JSON array: [{"path": "json.field", "key": "memory_key"}]
    
    # Assistente de Projeto
    project_assistant_label = Column(String, nullable=True)
    project_assistant_keyword = Column(String, nullable=True)
    project_assistant_deactivate_keyword = Column(String, nullable=True)
    project_assistant_entry_message = Column(Text, nullable=True)
    project_assistant_exit_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    events = relationship("WebhookEventModel", back_populates="webhook_config", cascade="all, delete-orphan")
    agent = relationship("AgentConfigModel", foreign_keys=[agent_id])


class WebhookEventModel(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    webhook_config_id = Column(Integer, ForeignKey("webhook_configs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=True)
    message_type = Column(String, nullable=True, default="text")
    conta_id = Column(String, nullable=True, index=True)
    inbox_id = Column(String, nullable=True)
    inbox_nome = Column(String, nullable=True)
    conversa_id = Column(String, nullable=True, index=True)
    mensagem_id = Column(String, nullable=True)
    contato_id = Column(String, nullable=True)
    telefone = Column(String, nullable=True, index=True)
    labels = Column(Text, nullable=True)
    contato_nome = Column(String, nullable=True)
    mensagem = Column(Text, nullable=True)
    link = Column(Text, nullable=True)
    raw_payload = Column(Text, nullable=True)
    status = Column(String, default="received")
    task_id = Column(String, nullable=True)
    processing_steps = Column(Text, nullable=True)
    agent_response = Column(Text, nullable=True)
    legenda = Column(Text, nullable=True)
    dono = Column(String, nullable=True) # agente | usuario
    scheduled_at = Column(DateTime(timezone=True), nullable=True) # Data/Hora para execução após debounce
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_automatic = Column(Boolean, default=False, nullable=True)

    webhook_config = relationship("WebhookConfigModel", back_populates="events")

    __table_args__ = (
        Index("idx_webhook_events_config_created", "webhook_config_id", "created_at"),
        Index("idx_webhook_events_config_phone", "webhook_config_id", "telefone"),
        Index("idx_webhook_events_config_status_event", "webhook_config_id", "status", "event_type"),
    )


class TranscriptionFolder(Base):
    """Pastas para organizar as transcrições."""
    __tablename__ = "transcription_folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
 
class TranscriptionTaskModel(Base):
    """Armazena o histórico e status das transcrições de áudio/vídeo."""
    __tablename__ = "transcription_tasks"
 
    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=True) # Nome do arquivo no bucket
    status = Column(String, default="PENDING") # PENDING, PROCESSING, SUCCESS, FAILURE
    task_id = Column(String, nullable=True) # ID do Celery
    
    # Resultados
    result_text = Column(Text, nullable=True)
    duration = Column(Float, nullable=True)
    tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    
    # Organização
    folder_id = Column(Integer, ForeignKey("transcription_folders.id", ondelete="SET NULL"), nullable=True)
    
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    knowledge_base = relationship("KnowledgeBaseModel")
    folder = relationship("TranscriptionFolder")

class ScheduledTrigger(Base):
    """Gatilhos de automação agendados ou disparos em massa."""
    __tablename__ = "scheduled_triggers"

    id = Column(Integer, primary_key=True, index=True)
    contact_phone = Column(String, index=True)
    status = Column(String, default="pending")  # pending, processing, completed, cancelled, failed
    
    # Contexto da Integração
    integration_id = Column(Integer, nullable=True)
    event_type = Column(String, nullable=True)
    product_name = Column(String, nullable=True)
    
    # Detalhes do Disparo
    failure_reason = Column(Text, nullable=True)
    conversation_id = Column(String, nullable=True)
    client_id = Column(Integer, nullable=True)
    template_name = Column(String, nullable=True)
    chatwoot_label = Column(String, nullable=True)
    skip_block_check = Column(Boolean, default=False)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_scheduled_triggers_status_created", "status", "created_at"),
        Index("idx_scheduled_triggers_phone", "contact_phone"),
    )

class MessageStatus(Base):
    """Status detalhado de cada mensagem enviada vinculada a um trigger."""
    __tablename__ = "message_status"

    id = Column(Integer, primary_key=True, index=True)
    trigger_id = Column(Integer, ForeignKey("scheduled_triggers.id", ondelete="CASCADE"))
    status = Column(String) # sent, delivered, read, failed
    error_message = Column(Text, nullable=True)
    message_id = Column(String, nullable=True) # ID da mensagem na plataforma externa
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserQuestionEmbedding(Base):
    __tablename__ = "user_question_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    interaction_log_id = Column(Integer, ForeignKey("interaction_logs.id", ondelete="CASCADE"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ObjectionCluster(Base):
    __tablename__ = "objection_clusters"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), nullable=False)
    cluster_label = Column(String, nullable=False) # Título resumido do grupo pela LLM
    representative_question = Column(Text, nullable=True) # Pergunta central do cluster
    suggested_script = Column(Text, nullable=True) # Roteiro sugerido pela LLM
    count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("ObjectionClusterMessage", back_populates="cluster", cascade="all, delete-orphan")


class ObjectionClusterMessage(Base):
    __tablename__ = "objection_cluster_messages"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("objection_clusters.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    cluster = relationship("ObjectionCluster", back_populates="messages")


class BackupConfigModel(Base):
    __tablename__ = "backup_configs"

    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Boolean, default=False)
    frequency_type = Column(String, default="hours")  # "hours" ou "days"
    interval_value = Column(Integer, default=6)
    retention_count = Column(Integer, default=30)
    backup_folder = Column(String, default="Backup_AgenteFlow")
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BackupHistoryModel(Base):
    __tablename__ = "backup_history"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    status = Column(String, default="success")  # "success", "failure", "running"
    error_message = Column(Text, nullable=True)
    is_pinned = Column(Boolean, default=False)  # Se True, não é deletado pela política de retenção
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SaleModel(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=True)
    telefone = Column(String, index=True, nullable=True)
    valor = Column(Float, default=0.0)
    plataforma = Column(String, nullable=True) # Hotmart, Kiwify, etc.
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True, unique=True, nullable=False)
    telefone = Column(String, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    titulo = Column(String, nullable=True)
    data_horario = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TestimonialCategoryModel(Base):
    __tablename__ = "testimonial_categories"
    __test__ = False

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=True)
    order_position = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TestimonialModel(Base):
    __tablename__ = "testimonials"
    __test__ = False

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    media_type = Column(String, nullable=False, index=True)  # 'image' ou 'video'
    file_size_bytes = Column(Integer, nullable=True)
    caption = Column(Text, nullable=True)
    order_position = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SentTestimonialModel(Base):
    __tablename__ = "sent_testimonials"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False, index=True)
    testimonial_id = Column(Integer, ForeignKey("testimonials.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class LeadModel(Base):
    """Modelo ORM unificado para a tabela oficial de leads."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    webhook_config_id = Column(Integer, ForeignKey("webhook_configs.id", ondelete="SET NULL"), nullable=True, index=True)
    qualified_by_agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="SET NULL"), nullable=True)
    conta_id = Column(String, nullable=True)
    inbox_id = Column(String, nullable=True)
    inbox_nome = Column(String, nullable=True)
    conversa_id = Column(String, nullable=True, index=True)
    mensagem_id = Column(String, nullable=True)
    contato_id = Column(String, nullable=True)
    telefone = Column(String, nullable=True, index=True)
    labels = Column(Text, nullable=True)
    contato_nome = Column(String, nullable=True)
    mensagem = Column(Text, nullable=True)
    message_type = Column(String(50), default="text", nullable=True)
    link = Column(Text, nullable=True)
    pode_enviar_mensagem = Column(Boolean, default=True)
    ultima_mensagem_em = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    window_close_processed = Column(Boolean, default=False)
    followup_step = Column(Integer, default=0)
    ultima_resposta_agente = Column(Text, nullable=True)
    ultima_resposta_agente_em = Column(DateTime(timezone=True), nullable=True)
    respostas_qualificacao = Column(Text, nullable=True)
    lead_score = Column(Integer, nullable=True)
    lead_classification = Column(String(50), nullable=True)
    lead_justification = Column(Text, nullable=True)
    active_qualification_funnel_id = Column(String(100), nullable=True) # Funil de qualificação específico atribuído via API para disparos
    active_followup_funnel_id = Column(String(100), nullable=True) # Fluxo de follow-up específico atribuído via API para disparos
    executed_question_funnels = Column(JSON, default=list, nullable=True) # Lista de IDs de QuestionFunnels já disparados para este contato
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_leads_webhook_config_id", "webhook_config_id"),
        Index("idx_leads_telefone", "telefone"),
        Index("idx_leads_ultima_msg", "ultima_mensagem_em"),
        Index("idx_leads_score", "lead_score"),
    )


class SemanticCacheModel(Base):
    """Modelo para armazenar pares de Pergunta -> Resposta Aprovada com Embedding para respostas instantâneas a Custo Zero."""
    __tablename__ = "semantic_caches"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, nullable=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), nullable=False, index=True)
    user_query = Column(Text, nullable=False)
    approved_response = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)
    alternate_queries = Column(JSON, default=list, nullable=True)
    alternate_embeddings = Column(JSON, default=list, nullable=True)
    usage_count = Column(Integer, default=0)
    similarity_threshold = Column(Float, nullable=True) # Similaridade mínima individual (None usa o padrão do agente)
    category_tag = Column(String(120), nullable=True, index=True) # Tag ou Produto vinculado (ex: 'Método Laser Day', None para Geral)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_semantic_cache_agent_id", "agent_id"),
        Index("idx_semantic_cache_client_id", "client_id"),
    )


class QuestionFunnelModel(Base):
    """Modelo para armazenar Funis Pré-Configurados por Dúvida (Áudio Humanizado + Mensagens com Delays)."""
    __tablename__ = "question_funnels"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    trigger_question = Column(Text, nullable=False)
    trigger_variations = Column(JSON, default=list, nullable=True) # Variações da pergunta
    similarity_threshold = Column(Float, default=0.82, nullable=True) # Similaridade mínima para ativação (padrão 82%)
    frequency_mode = Column(String(50), default="once_per_lead", nullable=True) # 'once_per_lead' ou 'always'
    is_active = Column(Boolean, default=True)
    embedding = Column(JSON, nullable=True) # Vetor de embedding da dúvida principal
    variation_embeddings = Column(JSON, default=list, nullable=True) # Vetores de embedding das variações
    steps = Column(JSON, default=list, nullable=False) # Lista de passos sequenciais [{step_number, type, media_url, delay_seconds, content, transcription}]
    total_executions = Column(Integer, default=0) # Contador de execuções
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_question_funnels_agent_id", "agent_id"),
    )


class PromptVaultModel(Base):
    """Modelo para o Cofre de Prompts - Armazenamento de Prompts desacoplado do ciclo de vida dos agentes."""
    __tablename__ = "prompt_vaults"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False) # Título ou identificador do backup
    description = Column(Text, nullable=True) # Descrição/notas
    source_agent_id = Column(Integer, nullable=True, index=True) # ID do agente de origem (sem cascade para persistir)
    source_agent_name = Column(String(255), nullable=True) # Nome persistido do agente
    backup_type = Column(String(50), default="manual", nullable=False) # 'manual', 'pre_deletion', 'auto'
    
    # Pacote Completo de Prompts
    system_prompt = Column(Text, nullable=False, default="")
    dynamic_prompt = Column(Text, nullable=True, default="")
    pre_router_prompt = Column(Text, nullable=True)
    unanswered_question_prompt = Column(Text, nullable=True)
    tool_prompts = Column(JSON, nullable=True)
    extra_metadata = Column(JSON, default=dict, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_prompt_vault_client_id", "client_id"),
        Index("idx_prompt_vault_backup_type", "backup_type"),
        Index("idx_prompt_vault_created_at", "created_at"),
    )
