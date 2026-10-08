import json
from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- AUTH & USER SCHEMAS ---

class LoginRequest(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    name: str = "Novo Usuário"
    email: str
    password: str
    role: str = "Usuário"
    status: str = "ATIVO"
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    company_logo_size: Optional[str] = "medium"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    company_logo_size: Optional[str] = None

class UserInviteCreate(BaseModel):
    role: str = "Usuário"
    validity_hours: int = 24

class UserInviteResponse(BaseModel):
    id: int
    token: str
    role: str
    expires_at: datetime
    is_used: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        import re
        if len(v) < 10:
            raise ValueError("A senha deve ter no mínimo 10 caracteres.")
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("A senha deve conter pelo menos uma letra.")
        if not re.search(r'[0-9]', v):
            raise ValueError("A senha deve conter pelo menos um número.")
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError("A senha deve conter pelo menos um caractere especial (!@#$%^&* etc).")
        return v


# --- KNOWLEDGE BASE SCHEMAS ---

class KnowledgeItem(BaseModel):
    id: Optional[int] = None
    question: str
    answer: str
    metadata_val: Optional[str] = None
    category: Optional[str] = "Geral"
    source_metadata: Optional[str] = None
    question_variations: Optional[List[str]] = []
    model_config = ConfigDict(from_attributes=True)

    @field_validator('question_variations', mode='before')
    @classmethod
    def _coerce_variations(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed if x]
            except Exception:
                return []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []

# Variante "detalhada" do KnowledgeItem: inclui o vetor de embedding.
# Usada apenas em endpoints de item único (GET/PUT /knowledge-items/{id}) para não
# inflar o payload da listagem geral de bases (que retorna dezenas de itens de uma vez).
class KnowledgeItemDetail(KnowledgeItem):
    embedding: Optional[List[float]] = None

    # pgvector retorna numpy.ndarray (não list) quando numpy está instalado;
    # convertemos aqui para garantir serialização JSON válida.
    @field_validator('embedding', mode='before')
    @classmethod
    def _coerce_embedding(cls, v):
        if v is None:
            return None
        if hasattr(v, 'tolist'):
            return v.tolist()
        return list(v)

class KnowledgeBase(BaseModel):
    id: Optional[int] = None
    name: str = "Nova Base"
    description: Optional[str] = None
    kb_type: str = "qa"
    question_label: str = "Pergunta"
    answer_label: str = "Resposta"
    metadata_label: str = "Metadado"
    items: List[KnowledgeItem] = []
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class GenerateQAFromTranscriptionRequest(BaseModel):
    text: str
    total_questions: Optional[int] = 5
    model: Optional[str] = "gpt-4o-mini"
    task_id: Optional[int] = None

class GenerateChunksFromTranscriptionRequest(BaseModel):
    text: str
    chunk_size: Optional[int] = 1200
    overlap: Optional[int] = 150

class ProcessLessonTranscriptionRequest(BaseModel):
    text: str
    total_questions: Optional[int] = 5
    chunk_size: Optional[int] = 1200
    overlap: Optional[int] = 150
    model: Optional[str] = "gpt-4o-mini"
    video_title: Optional[str] = None
    module_name: Optional[str] = None
    chapter_name: Optional[str] = None
    topics: Optional[List[str] | str] = None
    chapters: Optional[List[str] | str] = None
    extra_metadata: Optional[Dict[str, Any] | str] = None
    category_qa: Optional[str] = "Treinamento"
    category_chunks: Optional[str] = "Transcrição"
    task_id: Optional[int] = None
    auto_save: Optional[bool] = True

class AddBatchKnowledgeItemsRequest(BaseModel):
    items: List[KnowledgeItem]

class AddVariationRequest(BaseModel):
    variation: Optional[str] = None
    variations: Optional[List[str]] = []

# --- AGENT & CONFIG SCHEMAS ---

class AgentConfig(BaseModel):
    id: Optional[int] = None
    name: str = "Novo Agente"
    description: Optional[str] = None
    model: str = "gpt-5.2"
    fallback_model: Optional[str] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    top_k: Optional[int] = 40
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    safety_settings: Optional[str] = "standard"
    model_settings: Dict[str, Any] = {}
    is_active: bool = True
    date_awareness: bool = False
    date_awareness_past_days: Optional[int] = 7
    date_awareness_future_days: Optional[int] = 7
    system_prompt: str = "Você é um assistente útil e inteligente."
    dynamic_prompt: Optional[str] = ""
    pre_router_prompt: Optional[str] = None
    context_window: int = 5
    knowledge_base: list = []
    knowledge_base_id: Optional[int] = None
    knowledge_base_ids: List[int] = []
    semantic_cache_enabled: Optional[bool] = True
    semantic_cache_threshold: Optional[float] = 0.92
    knowledge_bases: List[Dict[str, Any]] = []
    rag_retrieval_count: int = 5
    rag_translation_enabled: bool = False
    rag_multi_query_enabled: bool = True
    rag_rerank_enabled: bool = True
    rag_agentic_eval_enabled: bool = True
    rag_parent_expansion_enabled: bool = False
    rag_relevance_threshold: float = 0.0
    rag_kb_routing_enabled: bool = False
    rag_kb_routing_variable: Optional[str] = None
    tool_ids: List[int] = []
    simulated_time: Optional[str] = None
    security_competitor_blacklist: Optional[str] = None
    security_forbidden_topics: Optional[str] = None
    security_discount_policy: Optional[str] = None
    security_language_complexity: str = "standard"
    security_pii_filter: bool = False
    security_validator_ia: bool = False
    security_bot_protection: bool = False
    security_max_messages_per_session: int = 20
    security_semantic_threshold: float = 0.85
    security_loop_count: int = 3
    ui_primary_color: str = "#6366f1"
    ui_header_color: str = "#0f172a"
    ui_chat_title: str = "Suporte Inteligente"
    ui_welcome_message: str = "Olá! Como posso te ajudar hoje?"
    initial_message: Optional[str] = None
    initial_question_message: Optional[str] = None
    initial_ignore_message: Optional[str] = None
    inbox_capture_enabled: bool = True
    greeting_mode: str = "prompt"
    question_mode: str = "panel"
    ad_mode: str = "panel"
    qualification_questions: Optional[str] = None
    qualification_labels: Optional[str] = None
    qualification_criteria: Optional[str] = None
    qualification_final_action: Optional[str] = None
    qualification_final_action_trigger: Optional[str] = "all"
    qualification_funnels: Optional[Any] = None
    unanswered_handoff_limit: Optional[int] = 2
    unanswered_question_prompt: Optional[str] = None
    router_enabled: bool = False
    router_simple_model: str = "gpt-5-mini"
    router_simple_fallback_model: Optional[str] = None
    router_complex_model: str = "gpt-5.2"
    router_complex_fallback_model: Optional[str] = None
    handoff_enabled: bool = False
    response_translation_enabled: bool = False
    response_translation_fallback_lang: str = "portuguese"
    tool_prompts: Optional[Dict[str, str]] = None
    model_config = ConfigDict(from_attributes=True)

class AssignFunnelRequest(BaseModel):
    phones: List[str]
    funnel_id: Optional[str] = None
    followup_id: Optional[str] = None
    agent_id: Optional[int] = None

class AssignFollowupRequest(BaseModel):
    phones: List[str]
    followup_id: str
    webhook_config_id: Optional[int] = None

class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    agent_id: Optional[int] = None
    context_variables: Optional[Dict[str, Any]] = None
    model_override: Optional[str] = None
    system_prompt_override: Optional[str] = None
    image_url: Optional[str] = None

class MessageResponse(BaseModel):
    response: str
    cost_usd: float
    cost_brl: float
    input_tokens: int
    output_tokens: int
    cached_tokens: Optional[int] = 0
    tool_calls: Optional[List[Dict[str, Any]]] = None
    audio: Optional[str] = None
    handoff_data: Optional[Dict[str, Any]] = None
    debug: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None
    model_used: Optional[str] = None
    model_role: Optional[str] = None
    from_semantic_cache: Optional[bool] = False
    cached_similarity: Optional[float] = None
    cached_original_query: Optional[str] = None
    semantic_cache: Optional[Dict[str, Any]] = None
    from_question_funnel: Optional[bool] = False
    funnel_steps: Optional[List[Dict[str, Any]]] = None
    question_funnel: Optional[Dict[str, Any]] = None
    error: bool = False
    system_error: Optional[str] = None

class ToolCreate(BaseModel):
    name: str
    description: str
    parameters_schema: str  # JSON string
    webhook_url: Optional[str] = None
    labels_to_add: Optional[str] = None  # JSON list
    labels_to_remove: Optional[str] = None  # JSON list
    confirmation_message: Optional[str] = None

class ToolResponse(ToolCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PromptDraft(BaseModel):
    id: Optional[int] = None
    agent_id: Optional[int] = None
    prompt_text: str
    version_name: Optional[str] = None
    description: Optional[str] = None
    character_count: Optional[int] = 0
    token_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class GlobalContextVariable(BaseModel):
    id: Optional[int] = None
    key: str
    value: Optional[str] = None
    type: Optional[str] = "string"
    description: Optional[str] = None
    is_default: Optional[bool] = False
    extraction_method: Optional[str] = "integration"
    extraction_prompt: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- MEDIA & TRANSCRIPTION SCHEMAS ---

class TranscriptionProcessRequest(BaseModel):
    text: str
    config: Dict[str, Any]

class BulkDeleteTranscriptionRequest(BaseModel):
    task_ids: List[int]

class TranscriptionRenameRequest(BaseModel):
    filename: str

class TranscriptionFolderRequest(BaseModel):
    name: str

class TranscriptionMoveRequest(BaseModel):
    folder_id: Optional[int] = None

class ManualTranscriptionRequest(BaseModel):
    filename: str
    text: str
    folder_id: Optional[int] = None

class TranscriptionContentUpdateRequest(BaseModel):
    text: str

# --- KNOWLEDGE BASE SCHEMAS ---

class BatchUpdateRequest(BaseModel):
    item_ids: List[int]
    question: Optional[str] = None
    answer: Optional[str] = None
    metadata_val: Optional[str] = None
    category: Optional[str] = None

class BatchDeleteRequest(BaseModel):
    item_ids: List[int]

class BulkSummarizeRequest(BaseModel):
    item_ids: List[int]
    question: str
    metadata_val: str
    category: str = "Geral"

class AnswerToPromptRequest(BaseModel):
    agent_id: int
    answer: str
    question: Optional[str] = None

# --- ANALYTICS SCHEMAS ---

class DashboardStats(BaseModel):
    total_agents: int
    total_knowledge_bases: int
    total_interactions: int
    total_cost: float
    model_config = ConfigDict(from_attributes=True)

class FinancialReportItem(BaseModel):
    date: str
    agent_id: Optional[int]
    agent_name: Optional[str]
    total_messages: int
    total_tokens: int
    total_cost: float
    avg_cost_per_message: float
    unique_sessions: int

class FinancialReport(BaseModel):
    items: List[FinancialReportItem]
    grand_total_cost: float

# --- RAG & SEARCH SCHEMAS ---

class RAGSimulationRequest(BaseModel):
    query: str
    translation_enabled: bool = False
    multi_query_enabled: bool = False
    rerank_enabled: bool = False
    agentic_eval_enabled: bool = False
    parent_expansion_enabled: bool = False
    limit: int = 5
    relevance_threshold: float = 0.0

class CoverageCheckRequest(BaseModel):
    questions: List[str]

class MergeItemsRequest(BaseModel):
    item_ids: List[int]

# --- PROMPT ADVISOR & ARENA ---

class PromptAdvisorRequest(BaseModel):
    prompt_content: str
    initial_message: Optional[str] = None
    initial_question_message: Optional[str] = None
    ignore_messages: Optional[List[str]] = None
    user_query: str
    history: List[Dict[str, str]] = []

class PromptRefineRequest(BaseModel):
    prompt_content: str
    history: List[Dict[str, str]]
    user_instructions: Optional[str] = None

# --- SESSION & INTERACTION SCHEMAS ---

class DeleteSessionsRequest(BaseModel):
    session_ids: List[str]

class SessionPreview(BaseModel):
    session_id: Optional[str] = None
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    start_time: Optional[datetime] = None
    last_interaction: Optional[datetime] = None
    message_count: Optional[int] = 0
    summary: Optional[str] = None
    total_cost: Optional[float] = 0.0
    is_test_session: Optional[bool] = False

class SessionMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime
    cost: float
    tokens: int
    input_tokens: Optional[int] = 0
    output_tokens: Optional[int] = 0
    cached_tokens: Optional[int] = 0
    model: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None
    from_semantic_cache: Optional[bool] = False
    cached_similarity: Optional[float] = None
    cached_original_query: Optional[str] = None

# --- FEEDBACK & FINE-TUNING SCHEMAS ---

class FeedbackCreate(BaseModel):
    agent_id: int
    interaction_log_id: Optional[int] = None
    user_message: str
    original_response: str
    rating: str = "negative"
    corrected_response: Optional[str] = None
    system_prompt_snapshot: Optional[str] = None
    correction_note: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    agent_id: int
    interaction_log_id: Optional[int]
    user_message: str
    original_response: Optional[str]
    corrected_response: Optional[str]
    rating: str
    correction_note: Optional[str]
    exported_to_finetune: bool
    finetune_job_id: Optional[str]
    model_config = ConfigDict(from_attributes=True)

class FeedbackUpdate(BaseModel):
    user_message: Optional[str] = None
    corrected_response: Optional[str] = None
    correction_note: Optional[str] = None

class FineTuneJobCreate(BaseModel):
    agent_id: int
    base_model: str = "gpt-4o-mini-2024-07-18"
    n_epochs: int = 3
    suffix: Optional[str] = None

# --- SUPPORT & UNANSWERED SCHEMAS ---

class AnswerUnansweredRequest(BaseModel):
    answer: str
    knowledge_base_id: int
    question: Optional[str] = None

class SupportSummaryRequest(BaseModel):
    session_id: str
    agent_id: int

class BulkDeleteSupportRequest(BaseModel):
    ids: List[int]

# --- MISC SCHEMAS ---

class GenerateUploadUrlRequest(BaseModel):
    filename: str
    content_type: Optional[str] = None
    kb_id: Optional[int] = None

class ConfirmUploadRequest(BaseModel):
    task_id: int
    kb_id: Optional[int] = None
    config: Dict[str, Any] = {}

class BulkAgentDeleteRequest(BaseModel):
    agent_ids: List[int]

class BulkResolveRequest(BaseModel):
    ids: List[int]

class AnswerToPromptRequest(BaseModel):
    agent_id: int
    answer: str
    question: Optional[str] = None

# --- TESTER SCHEMAS ---

class TesterProvocationRequest(BaseModel):
    session_id: Optional[str] = None
    persona_prompt: str
    history: List[Dict[str, str]]
    agent_id: Optional[int] = None
    agent_prompt: Optional[str] = None
    is_dynamic: Optional[bool] = False

class TesterEvaluationRequest(BaseModel):
    session_id: Optional[str] = None
    agent_id: Optional[int] = None
    persona_prompt: str
    history: List[Dict[str, str]]
    agent_prompt: Optional[str] = None

class TesterSentimentRequest(BaseModel):
    history: List[Dict[str, str]]


# --- EXPLAIN RESPONSE SCHEMAS ---

class ExplainRequest(BaseModel):
    user_message: str
    agent_response: str
    resolved_prompt: Optional[str] = None
    pre_router: Optional[Dict[str, Any]] = None

class ExplainFactor(BaseModel):
    title: str
    explanation: str
    section: str  # 'static' | 'dynamic' | 'injected' | 'rag' | 'general'
    relevance: str  # 'high' | 'medium' | 'low'

class ExplainResponse(BaseModel):
    factors: List[ExplainFactor]
    summary: str
    cost_usd: Optional[float] = 0.0
    cost_brl: Optional[float] = 0.0

class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str

class ExplainDebateRequest(BaseModel):
    user_message: str
    agent_response: str
    resolved_prompt: Optional[str] = None
    pre_router: Optional[Dict[str, Any]] = None
    question: str
    debate_history: List[ChatMessage] = []

class ExplainDebateResponse(BaseModel):
    response: str
    cost_usd: float
    cost_brl: float
    debate_history: List[ChatMessage]


# --- SOURCE ATTRIBUTION SCHEMAS ---

class SourceLink(BaseModel):
    type: str  # 'knowledge_base' | 'agent_prompt' | 'dynamic_prompt' | 'context_variable' | 'general'
    url: Optional[str] = None
    label: str

class SourceSegment(BaseModel):
    segment_index: int
    text: str
    source_type: str  # 'knowledge_base' | 'system_prompt' | 'dynamic_prompt' | 'context_variable' | 'general_reasoning'
    source_title: str
    source_snippet: Optional[str] = None
    kb_id: Optional[int] = None
    kb_item_id: Optional[int] = None
    agent_id: Optional[int] = None
    confidence: Optional[float] = 1.0
    explanation: Optional[str] = None
    link: Optional[SourceLink] = None

class SourceAttributionRequest(BaseModel):
    user_message: str
    agent_response: str
    agent_id: Optional[int] = None
    resolved_prompt: Optional[str] = None
    rag_items: Optional[List[Dict[str, Any]]] = None
    context_variables: Optional[Dict[str, Any]] = None
    pre_router: Optional[Dict[str, Any]] = None

class SourceAttributionResponse(BaseModel):
    segments: List[SourceSegment]
    summary: str
    cost_usd: Optional[float] = 0.0
    cost_brl: Optional[float] = 0.0


# --- SCHEMAS COFRE DE PROMPTS (PROMPT VAULT) ---
class PromptVaultCreate(BaseModel):
    name: str
    description: Optional[str] = None
    source_agent_id: Optional[int] = None
    backup_type: Optional[str] = "manual"
    system_prompt: Optional[str] = ""
    dynamic_prompt: Optional[str] = ""
    pre_router_prompt: Optional[str] = None
    unanswered_question_prompt: Optional[str] = None
    tool_prompts: Optional[Dict[str, Any]] = None
    extra_metadata: Optional[Dict[str, Any]] = None

class PromptVaultUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class PromptVaultResponse(BaseModel):
    id: int
    client_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    source_agent_id: Optional[int] = None
    source_agent_name: Optional[str] = None
    backup_type: str
    system_prompt: str
    dynamic_prompt: Optional[str] = None
    pre_router_prompt: Optional[str] = None
    unanswered_question_prompt: Optional[str] = None
    tool_prompts: Optional[Dict[str, Any]] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class PromptVaultRestoreRequest(BaseModel):
    target_agent_id: Optional[int] = None
    restore_system_prompt: bool = True
    restore_pre_router: bool = True
    restore_dynamic: bool = True
    restore_unanswered: bool = True
    restore_tool_prompts: bool = True


