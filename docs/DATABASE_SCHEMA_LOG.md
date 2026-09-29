
# Log de Alterações no Banco de Dados

Este arquivo registra todas as alterações manuais de schema (ALTER TABLE) realizadas no projeto.

| Data | Tabela | Coluna(s) | Script de Migração | Descrição |
|------|--------|-----------|--------------------|-----------|
| 2026-05-10 | webhook_configs | labels_on_message | add_labels_on_message_column.py | Adição de suporte para etiquetas automáticas em cada mensagem. |
| 2026-05-11 | TODAS | Varias (TIMESTAMP) | migrate_all_timezones.py | Conversão global de TIMESTAMP para TIMESTAMPTZ para suporte a fuso horário de Brasília. |
| 2026-05-11 | prompt_drafts | description | add_prompt_draft_description.py | Adição de campo de descrição para versões de prompt. |
| 2026-05-13 | support_requests | webhook_config_id | add_webhook_id_to_support.py | Vincular suportes ao canal de origem para automação de retorno. |
| 2026-05-15 | scheduled_triggers, message_status | TODAS | create_trigger_tables.py | Criação das tabelas base para o sistema de disparos e follow-up, corrigindo erro de deleção de contatos. |
| 2026-05-17 | webhook_configs | delete_labels | add_delete_labels_column.py | Adição de campo para substituir as etiquetas do Chatwoot no reset/auto-deleção do contato. |
| 2026-05-17 | users | company_name, company_logo, company_logo_size | add_whitelabel_columns.py | Colunas de customização para a funcionalidade de White-label (marca branca). |
| 2026-05-19 | agent_config, leads | qualification_labels, respostas_qualificacao | add_qualification_responses_column.py | Adição de colunas para suporte a qualificação de leads e armazenamento de respostas. |
| 2026-05-19 | webhook_configs | chatwoot_inbox_id | add_chatwoot_inbox_id_column.py | Adição de suporte para filtrar webhooks do Chatwoot por ID do Inbox. |
| 2026-05-21 | agent_config, leads | qualification_criteria, lead_score, lead_classification, lead_justification | add_lead_score_columns.py | Colunas para suporte a Lead Scoring (critérios, pontuação, classificação e justificativa). |
| 2026-05-21 | TODAS (Leads) | qualified_by_agent_id | add_qualified_by_agent_id_column.py | Coluna para rastrear qual agente realizou a qualificação do lead. |
| 2026-05-21 | user_invites | TODAS | create_user_invites_table.py | Criação da tabela de convites de usuários expiráveis. |
| 2026-05-22 | webhook_events | is_automatic | add_is_automatic_column.py | Adição de coluna para identificar se a mensagem do webhook é de envio automático do contato. |
| 2026-05-22 | webhook_configs | negative_feedback_label | add_negative_feedback_label_column.py | Adição de campo configurável para a etiqueta de feedback negativo (1º emoji negativo). |
| 2026-05-28 | agent_config | greeting_mode, question_mode, ad_mode | add_greeting_modes_columns.py | Adição de colunas para configurar o comportamento dinâmico (Painel/Prompt) de saudações, perguntas e anúncios. |
| 2026-06-01 | agent_config | date_awareness_past_days, date_awareness_future_days | add_date_awareness_custom_days.py | Adição de suporte a quantidade de dias anteriores e posteriores customizados no prompt de Consciência Temporal. |
| 2026-06-02 | webhook_configs, sales | project_assistant_*, TODAS | create_backup_tables.py | Criação das tabelas de configuração de backup e histórico de execuções no S3. |
| 2026-06-12 | agent_config | dynamic_prompt | add_dynamic_prompt_column.py | Adição de coluna para o prompt dinâmico do agente de IA (Prompt Caching). |
| 2026-06-12 | interaction_logs | cached_tokens | add_cached_tokens_column.py | Adição de coluna para rastrear tokens que vieram do cache nas interações da IA. |
| 2026-06-13 | global_context_variables | extraction_method, extraction_prompt | add_auto_extract_fields.py | Adição de suporte para variáveis de contexto com extração automática com IA. |
| 2026-06-19 | backup_configs | backup_folder | add_backup_folder_column.py | Adição de campo para configurar a pasta do backup customizada no S3 do Backblaze. |
| 2026-06-29 | webhook_configs | zapvoice_url, zapvoice_api_token, zapvoice_client_id | add_zapvoice_columns.py | Adição de suporte para credenciais da API do ZapVoice e client_id no lugar do Chatwoot. |
| 2026-07-14 | webhook_configs | split_response_enabled | add_split_response_column.py | Adição de opção para controlar se a resposta da IA é enviada em bloco único ou quebrada em várias mensagens por linha. Default TRUE (mantém o comportamento atual). |
| 2026-07-14 | agent_config | rag_relevance_threshold | add_rag_relevance_threshold_column.py | Adição de limiar mínimo de relevância (0-1) que um item da base de conhecimento precisa atingir para ser realmente enviado como contexto ao RAG. Default 0.0 (sem filtro, mantém o comportamento atual). |
| 2026-07-14 | agent_config | pre_router_prompt | e3f4a5b6c7d8_add_pre_router_prompt_column.py (alembic, já existente na cadeia de migrations, apenas não estava mapeada em `models.py`) | Prompt customizável do Pre-Router (IA de triagem antes do agente principal), editável na 3ª aba "Pre-Router" do editor de prompt. Nullable, sem default: quando vazio, o backend usa em runtime o `DEFAULT_PRE_ROUTER_PROMPT_TEMPLATE` (agent_core/logic/pre_router.py). **ATENÇÃO:** como o projeto usa `Base.metadata.create_all` no startup (sem Alembic ativo), esta coluna só é criada automaticamente em bancos NOVOS. Se este agente já roda em produção com um banco existente, é necessário rodar `alembic upgrade head` manualmente (a migration já existe e é idempotente — verifica se a coluna já existe antes de adicionar) ou adicionar a coluna via ALTER TABLE manual. |
| 2026-07-14 | agent_config | tool_prompts | add_tool_prompts_column.py | Coluna JSON para armazenar os prompts customizados por ferramenta do pre-router. |
| 2026-07-15 | google_tokens | default_event_color, add_user_email | add_google_calendar_config_fields.py | Adição de colunas de configuração padrão de cor e convite de e-mail do usuário para eventos criados no Google Agenda. |
| 2026-07-15 | calendar_events | TODAS | create_calendar_events_table.py | Criação da tabela para persistir localmente as informações dos agendamentos (event_id, telefone, email, titulo, data_horario). |
| 2026-07-16 | leads, webhook_events | webhook_config_id, telefone, ultima_mensagem_em | add_leads_performance_indexes.py | Criação de índices de busca (BTree) para otimizar dramaticamente a performance de paginação e contagem no modal LeadsModal. |
| 2026-07-27 | webhook_configs | disable_ai_responses | add_disable_ai_responses_column.py | Opção de Modo Silencioso para gravar leads e memória mas pausar o envio de mensagens do agente de IA. |
| 2026-07-28 | webhook_events | ÍNDICES (sem colunas novas) | add_webhook_events_indexes.py | Adição de 3 índices compostos para otimizar queries de histórico de disparos: `(webhook_config_id, telefone)`, `(webhook_config_id, status, event_type)` e `(webhook_config_id, created_at DESC)`. Resolve lentidão no modal de Histórico de Disparo. |
| 2026-08-10 | webhook_configs | followup_cancel_label, followup_required_label | add_followup_trigger_labels_columns.py | Colunas para cancelamento automático por etiqueta do lead e segmentação por etiqueta necessária no Follow-up Automático. |
| 2026-08-10 | webhook_configs | followup_add_label | add_followup_add_label_column.py | Coluna para armazenar a etiqueta a ser adicionada na conversa do ZapVoice ao enviar mensagem de Follow-up Automático. |
| 2026-08-15 | webhook_configs | followup_on_reply | add_followup_on_reply_column.py | Opção para controlar comportamento de Follow-up ao receber resposta do lead: 'stop' (encerrar follow-up), 'continue_next' (avançar sem repetir), 'restart' (reiniciar). |
| 2026-08-20 | knowledge_items, interaction_logs, webhook_events, user_memory, scheduled_triggers, leads | ÍNDICES VETORIAIS (HNSW, GIN), ÍNDICES COMPOSTOS, CONSTRAINT UNIQUE, TABELA LEADS | alembic: `f9a8b7c6d5e4_database_optimization_and_indexes.py` | Reativação do Alembic com autogenerate completo de models, criação de índice pgvector HNSW (cosseno) e FTS GIN na base de conhecimento, índices compostos e constraint UNIQUE de memória. |
| 2026-08-26 | webhook_configs | purchased_label | add_purchased_label_column.py | Coluna para armazenar a etiqueta de compra confirmada / aluno no ZapVoice para cancelamento de follow-ups e atualização de CRM. |
| 2026-08-26 | webhook_configs | abandonment_delay_value, abandonment_delay_unit | add_abandonment_delay_columns.py | Colunas para configurar o tempo de inatividade após o último disparo de follow-up/re-tentativa antes de considerar que o lead Não Converteu / Desistiu no CRM. |
| 2026-09-01 | agent_config, semantic_caches | semantic_cache_enabled, semantic_cache_threshold, TODAS (tabela semantic_caches) | add_semantic_cache_table.py | Criação da tabela `semantic_caches` para cache semântico de respostas aprovadas com 👍 e colunas de controle no `agent_config` (enabled e threshold). |
| 2026-09-01 | semantic_caches | alternate_queries, alternate_embeddings | add_alternate_queries_to_semantic_cache.py | Adição de suporte a múltiplas perguntas alternativas / variações de gatilho para a mesma resposta aprovada no cache semântico. |
| 2026-09-02 | semantic_caches | similarity_threshold | add_similarity_threshold_to_semantic_cache.py | Adição de coluna para limiar mínimo de similaridade individual por pergunta/resposta no cache semântico (NULL usa o padrão do agente). |
| 2026-09-02 | semantic_caches | category_tag | add_category_tag_to_semantic_cache.py | Adição de coluna para vincular perguntas/respostas a um produto específico ou categoria (ex: 'Método Laser Day', NULL para Geral/Todos). |
| 2026-09-02 | agent_config | qualification_final_action | add_qualification_final_action_column.py | Adição de pergunta / ação final de fechamento e direcionamento (CTA) executada pela IA logo após o lead responder todas as etapas do funil de qualificação. |
| 2026-09-03 | agent_config | unanswered_handoff_limit, unanswered_question_prompt | add_unanswered_question_config_columns.py | Configuração do limite de dúvidas sem resposta na mesma conversa antes do transbordo humano (0 ou NULL para nunca transferir por dúvidas) e modelo/diretriz de resposta personalizada para a ferramenta `registrar_duvida_sem_resposta`. |
| 2026-09-04 | agent_config | qualification_final_action_trigger | add_qualification_final_action_trigger_column.py | Adição de condição de disparo da pergunta/ação final de fechamento pós-qualificação (all, hot, hot_warm, warm, cold ou array JSON). |
| 2026-09-04 | agent_config, leads | qualification_funnels (agent_config), active_qualification_funnel_id (leads) | add_qualification_funnels_columns.py | Suporte a múltiplos funis de qualificação independentes (armazenados em JSON no agente) e atribuição de funil ativo por contato via API para disparos específicos (Mentoria, Evento Presencial, Curso, etc.). |
| 2026-09-04 | knowledge_items | question_variations | add_question_variations_column.py | Adição de coluna JSON para armazenar múltiplas variações e formas alternativas da mesma pergunta na Base de Conhecimento, melhorando o vetor de busca e a indexação FTS. |
| 2026-09-05 | webhook_configs, leads | followup_funnels (webhook_configs), active_followup_funnel_id (leads) | add_followup_funnels_columns.py | Suporte a múltiplos fluxos de follow-up independentes por produto (armazenados em JSON no webhook) e atribuição de fluxo de follow-up ativo por contato via API para disparos em massa. |
| 2026-09-14 | agent_config | rag_multi_query_enabled (DEFAULT TRUE), rag_parent_expansion_enabled (DEFAULT FALSE) | update_rag_defaults.py | Atualização dos valores padrão de RAG: MULTIQUERY passa a ser ativo por padrão (DEFAULT TRUE) e PARENTEXPANSION passa a ser desativado por padrão (DEFAULT FALSE). |
| 2026-09-15 | question_funnels, leads | TODAS (question_funnels), executed_question_funnels (leads) | add_question_funnels_tables.py | Criação da tabela `question_funnels` para funis de conversão por dúvida (áudio humanizado PTT e mensagens sequenciais com delays) e coluna `executed_question_funnels` para rastrear histórico por lead. |
| 2026-09-29 | prompt_vaults | TODAS | add_prompt_vault_table.py | Criação da tabela `prompt_vaults` para o Cofre de Prompts, desacoplando os backups de prompts do ciclo de vida dos agentes e preservando o pacote completo de prompts em exclusões acidentais. |






