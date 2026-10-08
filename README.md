# 🤖 Plataforma de Agentes de IA para Automação

Esta é uma solução completa e profissional de nível corporativo para criação, gerenciamento, monitoramento e treinamento de agentes de IA. A plataforma integra múltiplos motores de linguagem (LLMs), RAG (Retrieval-Augmented Generation), otimização de cache de prompts, automações de calendário e agendamento, tratamento inteligente de webhooks e dashboards analíticos de ponta.

---

## 🏗️ Estrutura do Ecossistema

O projeto é estruturado de forma modular e escalável, dividido em três frentes principais:

1. **Backend (Python / FastAPI):**
   - Roteamento inteligente de mensagens (`Pre-Router AI`) para classificação rápida de intenções.
   - Integração com APIs externas (OpenAI GPT-4o, GPT-4o-Audio, Whisper, Chatwoot, ZapVoice).
   - Filas de tarefas assíncronas utilizando **Celery** e **Redis** para processamento resiliente de webhooks e disparos em segundo plano.
   - Banco de dados PostgreSQL (SQLite em modo de teste/desenvolvimento) gerenciado via SQLAlchemy.

2. **Frontend (React / Vite / Vanilla CSS):**
   - Dashboard Admin moderno e responsivo com estética **Glassmorphism Premium** e Dark Mode.
   - Componente `PromptEditor` avançado com suporte a condicionais interativas e alternância de Prompt Caching (Estático vs. Dinâmico).
   - `ChatPlayground` para testes em tempo real de personas dos agentes de IA, incluindo recursos de gravação e transcrição de áudio via Web Speech API / Whisper, além do painel de debug "Raio-X" com meta-análise e auditoria de respostas baseada em LLM.
   - Painel Whitelabel customizável para geração rápida de snippets de widgets de chat.

3. **Automação de Webhooks (Chatwoot & Vendas):**
   - Criação e registro automático de webhooks no Chatwoot via API com um clique.
   - Rota unificada de captura de conversões/vendas (`POST /sales/receive`) compatível com plataformas líderes de mercado (Hotmart, Kiwify).
   - Pipeline robusta com regras de negócio personalizadas por agente (ex: tratamento empático de emojis negativos, desduplicação de histórico de contexto e ignorar/parsear mensagens automáticas).

---

## 💡 Como Funciona o Projeto (Arquitetura e Recursos)

### 1. Triagem e Roteamento Inteligente (Pre-Router AI)
Antes do agente de IA principal gerar uma resposta detalhada (que consome mais tokens e tempo), as mensagens recebidas passam pelo `Pre-Router AI`. Ele classifica a mensagem em frações de segundo:
- Se for uma saudação curta ou mensagem trivial, responde imediatamente usando modelos de baixo custo.
- Se for uma mensagem automática de ausência ou catálogo comercial, isola e evita a contaminação do histórico do cliente no RAG.
- Se o cliente enviar emojis negativos consecutivos (como 👎 ou 😡), a IA detecta, insere tags de feedback e realiza a transição amigável para atendimento humano se necessário.

### 2. Otimização de Custos com Prompt Caching (Estático vs. Dinâmico)
A plataforma divide os prompts dos agentes de IA em duas seções chaveadas:
- **Prompt Estático:** Onde ficam as diretrizes permanentes da persona e as bases de conhecimento (RAG). Esse bloco é enviado como cabeçalho para habilitar o **Prompt Caching** da API da OpenAI, reduzindo os custos de tokens de entrada em até 50%.
- **Prompt Dinâmico:** Contém as variáveis de contexto, condicionais baseadas em qualificação e datas temporárias. Ele é concatenado ao final do prompt para garantir que alterações frequentes de contexto não invalidem o cache estático.

### 3. Assistente de Projeto e Auditoria Financeira
- **Ativação por Tags:** Através de palavras-chave como `#projeto`, o agente muda temporariamente de persona para fornecer métricas consolidadas sobre leads qualificados, vendas recentes e análise de objeções registradas nos últimos 7 dias.
- **Relatório de Custos:** Um painel financeiro no admin consolida o custo de processamento de cada interação por agente, filtrando automaticamente registros zerados e exibindo os valores convertidos para BRL.

### 4. Gravação e Transcrição em Tempo Real
No ambiente de testes `ChatPlayground`, o usuário pode utilizar o microfone para conversar com o robô. O sistema utiliza a `Web Speech API` para fornecer feedback visual instantâneo do texto falado no input. Ao terminar, o áudio binário é processado com alta fidelidade no Whisper-1 da OpenAI com conversão automática fallback resiliente via `ffmpeg` no backend.

### 5. Resposta Direta no 1º Atendimento e RAG Multicamada
- **Desvio de Mensagem Padrão:** Quando um lead envia uma pergunta ou dúvida na primeira mensagem (ou vinda de anúncios), o sistema desativa a saudação genérica inicial e responde diretamente à dúvida utilizando o RAG.
- **Resolução de Bases (`knowledge_base_ids`):** Suporte completo para vincular múltiplas bases de conhecimento por array de IDs com fallback direto no banco SQL.
- **Raio-X do Pensamento:** Inspeção detalhada de cada etapa da pipeline (Pre-Router, RAG, Injeção de Prompt e Resposta Final) no Playground.

### 6. Editor Expandido In-Place e Painel Lateral Ocultável
- **Editor Expandido (`⤢`):** Expansão in-place da caixa de mensagem no chat com visual Neon Indigo, suporte a parágrafos e contagem em tempo real de caracteres.
- **Painel Ocultável (`◀ Ocultar Painel`):** Barra lateral limpa sem fundo cinza transparente, com botão de ocultar/exibir para expandir o chat para 100% da largura.

### 7. Gestão de Encerramentos Passivos e Confirmações (Pre-Router)
- **Detecção de Expressões de Conclusão:** O sistema reconhece expressões de encerramento como `"Ta bom"`, `"Tá bom"`, `"Ta bem"`, `"Tudo bem"`, `"Ok"`, `"Entendi"`, `"Beleza"`, `"Ótimo"`, `"Maravilha"` e responde de forma empática e amigável (ex: *"Combinado! Se precisar de qualquer ajuda, estou por aqui. 😊"*).
- **Proteção Anti-Reenvio de Links:** O Pre-Router e o módulo de Query Enrichment são terminantemente bloqueados de reescrever encerramentos como se fossem novos pedidos de compra, evitando envios duplicados de links de checkout da Kiwify ou listagens repetidas de formas de pagamento.

### 8. Transbordo Resiliente de Suporte Humano e Fallback de Resposta
- **Continuidade do 2º Turno:** Na 2ª ocorrência de dúvida ausente (`registrar_duvida_sem_resposta`), a IA registra o transbordo para o suporte humano e prossegue para formular a resposta amigável ao cliente, respondendo perguntas conhecidas e avisando sobre o especialista humano.
- **Salvaguarda contra Respostas em Branco:** Caso o modelo de linguagem retorne conteúdo vazio durante o handoff, o sistema aciona automaticamente uma mensagem de fallback acolhedora em vez de enviar balões vazios.

### 9. Consulta de Pipeline em Produção
- Consulte o guia completo em [`COMO_CONSULTAR_PIPELINE_PRODUCAO.md`](COMO_CONSULTAR_PIPELINE_PRODUCAO.md) para inspecionar passo a passo via API REST (`GET /webhooks/{webhook_id}/events/{event_id}`) cada etapa de execução do agente (Debounce, Bot Defense, Pre-Router, RAG, Tool Calls e Resposta Final).

### 10. Segurança e Hashing de Senhas (Argon2id + Pepper)
- **Proteção Anti-GPU (Memory-Hard):** As senhas dos usuários utilizam o algoritmo **Argon2id** (padrão ouro RFC 9106 / OWASP), exigindo 64 MB de memória RAM por cálculo para inviabilizar ataques de força bruta paralelos via GPU/ASIC.
- **Pepper Global no `.env` (`PASSWORD_PEPPER`):** Aplicação de HMAC-SHA256 com chave secreta mantida fora do banco de dados, blindando as credenciais mesmo em caso de vazamento completo do banco.
- **Migração Transparente:** Usuários antigos em Bcrypt são validados com retrocompatibilidade e promovidos automaticamente para Argon2id + Pepper no momento do login.

### 11. Cache Semântico de Respostas Aprovadas (Custo Zero & Multi-Query)
- **Respostas Instantâneas a Custo R$ 0,00:** Armazena pares de Perguntas e Respostas Aprovadas com vetores de embedding. Dúvidas recorrentes dos clientes são respondidas diretamente pelo cache em milissegundos, com 0 tokens consumidos de LLM.
- **Central de Mineração de Dúvidas dos Leads:** Aba inteligente que lista em tempo real as dúvidas reais enviadas pelos leads nos webhooks, separando entre `💡 Sem Cache (Candidatas)` e `⚡ No Cache`, permitindo cadastrar novas respostas ou vincular dúvidas como variações de respostas existentes em 1 clique.
- **Sincronização em Tempo Real:** Ao adicionar ou vincular uma dúvida ao cache, o sistema a reconhece dinamicamente e remove-a imediatamente da fila de pendências.
- **Descarte de Dúvidas Irrelevantes (Não Vale a Pena):** Botão para marcar perguntas como descartadas para o cache, com popup centralizado de confirmação (backdrop escuro, bloqueio de clique externo e confirmação segura).
- **Popup Gigante de Edição em Tela Cheia (⛶ Maximizar Campo):** Editor amplo em modal de tela cheia (95vw x 88vh) com contadores de caracteres e palavras para formular respostas ricas e confortáveis.
- **Limiar de Similaridade Individual por Pergunta:** Além da sensibilidade padrão configurada no agente (ex: 85% ou 92%), cada pergunta cadastrada pode ter um limiar individual personalizado (ex: 98% para respostas que exigem mensagem quase idêntica).
- **Suporte a Múltiplas Perguntas no Mesmo Envio (Multi-Query Cache):** Mensagens que contêm mais de uma dúvida (ex: *"Olá, quais valores? Como funciona o curso? É online ou presencial?"*) são desmembradas automaticamente. Quando todas as dúvidas possuem respostas no cache, as respostas aprovadas são combinadas e entregues de forma harmoniosa com Custo Zero. Se apenas parte das dúvidas estiver no cache, as respostas homologadas entram como respostas pré-resolvidas no prompt para o LLM apenas complementar o que falta, economizando tokens e tempo.
- **Transparência de Custos no Histórico (De Graça vs Paga):** A tabela de histórico de conversas dos leads e webhooks destaca claramente com badges se cada mensagem foi entregue **⚡ De Graça (Cache Semântico · R$ 0,00)**, **⚡ Cache Parcial + IA**, **💳 Paga (IA · R$ 0,22)** ou **🔄 Follow-Up**, trazendo controle financeiro em tempo real.

### 12. Funil de Qualificação & Disparo Condicional de Fechamento por Lead Score
- **Etapas Customizáveis de Qualificação:** Cadastro de perguntas sequenciais com critérios individuais de conclusão e sincronização automática de etiquetas no ZapVoice/Chatwoot.
- **Pergunta / Ação Final Pós-Qualificação (Fechamento):** Diretriz de fechamento para a IA formular logo após a conclusão das perguntas (ex: pedir permissão para enviar o link do curso).
- **Regra de Permissão em Dois Passos:** A IA é terminantemente proibida de enviar links ou páginas de checkout na mesma mensagem em que pergunta se pode enviá-lo; o envio ocorre estritamente no turno seguinte, após o consentimento/afirmação do lead.
- **Disparo Condicional por Temperatura do Lead (`qualification_final_action_trigger`):**
  - `🌟 Todas` (`all`): Dispara para todos os leads que concluírem as etapas, independente do score.
  - `🔥 Quente` (`hot`): Dispara a pergunta de fechamento somente se o lead for classificado como Quente 🔥.
  - `🔥⚡ Quente/Morno` (`hot_warm`): Dispara para leads Quentes 🔥 ou Mornos ⚡.
  - `⚡ Morno` (`warm`): Dispara exclusivamente para leads Mornos ⚡.
  - `❄️ Frio` (`cold`): Dispara para leads Frios ❄️ (pesquisa/reativação).
- **Editor Ampliado (⛶ Maximizar):** Modal de tela cheia para formular diretrizes ricas e sugestões rápidas de fechamento em um clique.
- **Etiquetagem Condicional à Qualificação de Fato & Uso Exclusivo do Dropdown:**
  - O lead só recebe etiquetas de qualificação (no banco de dados e no ZapVoice) se for qualificado de fato, de acordo com o critério de temperatura/score configurado no gatilho.

### 13. Múltiplos Funis de Qualificação & Direcionamento via API para Disparos
- **Criação de Funis Específicos por Objetivo:** Permite criar múltiplos funis independentes de qualificação (ex: "Venda de Mentoria", "Imersão Presencial", "Curso Online", "Reativação de Base") para um mesmo agente de IA.
- **Isolamento Completo de Dados por Funil:** Cada funil possui seu próprio conjunto de:
  - Etapas de perguntas investigativas (`questions`).
  - Etiquetas exclusivas de qualificação do ZapVoice/Chatwoot (`labels`).
  - Critério customizado de lead scoring (`criteria`).
  - Pergunta/Ação final de fechamento (`final_action`).
  - Gatilho por temperatura do lead (`final_action_trigger`).
- **Barra de Gestão no Painel Admin (`QualificationFunnelsBar`):**
  - Dropdown com seleção instantânea do funil ativo.
  - Indicador visual do funil principal (`⭐ Padrão`).
  - Ações para criar novos funis (`➕ Novo Funil`), renomear (`✏️ Renomear`) e excluir funis personalizados (`🗑️ Excluir` com confirmação segura e retorno automático ao padrão).
  - Modal centralizado com backdrop escuro e validação em tempo real de nomes e identificadores.
- **Direcionamento via API para Disparos (`POST /api/leads/assign-funnel`):**
  - Endpoint dedicado para vincular contatos específicos (números de telefone) a um funil no momento em que receberem um disparo:
  ```json
  POST /api/leads/assign-funnel
  {
    "agent_id": 36,
    "funnel_id": "mentoria",
    "phones": ["5511999999999", "5511888888888"]
  }
  ```
  - Quando os contatos responderem ao disparo, a IA executa exclusivamente as etapas e regras do funil atribuído (`active_qualification_funnel_id`). Leads não associados a nenhum funil específico seguem automaticamente o funil Padrão (`funnel_default`).

### 14. Variações de Perguntas na Base de Conhecimento (Question Variations & Composite Embedding)
- **Múltiplas Formas de Fazer a Mesma Pergunta:** Permite cadastrar variações e formulações alternativas para qualquer pergunta da Base de Conhecimento (ex: *"O certificado tem validade no MEC?"*, *"O diploma é aprovado pelo MEC?"* para a pergunta principal *"O certificado é reconhecido pelo MEC?"*).
- **Vetor Semântico Composto:** Recalcula o embedding semântico via `text-embedding-3-small` unindo a pergunta principal e todas as suas variações (`pergunta + "\n" + "\n".join(variacoes)`), maximizando a taxa de acerto e o recall da busca no pgvector sem poluir o catálogo com itens duplicados.
- **Indexação em Full-Text Search (FTS) & Pre-Router:** As variações são indexadas no índice de busca textual PostgreSQL e incorporadas nos módulos de Rerank Agêntico e no catálogo de referência do Pre-Router AI.
- **Interface com Tags e Contagem:**
  - Componente de chips/tags com numeração dinâmica (`#1`, `#2`), adição rápida via `Enter` e remoção em um clique.
  - Disponível tanto no modal de edição (`EditItemModal`) quanto no formulário de criação de novos itens (`AddItemForm`).
  - Badge visual `🔀 +N variações` na tabela de itens de conhecimento, com busca e filtragem instantânea pelas palavras das variações.

### 15. Abas de Organização na Tela de Integrações Globais
- **Navegação por Categorias:** Organização da tela `/integrations` em abas modernas de alta legibilidade no padrão Glassmorphism:
  - `☀️ Todas`: Visão unificada com contador dinâmico de integrações disponíveis.
  - `📅 Produtividade & Agendas`: Focado em ferramentas de agenda (Google Calendar).
  - `💬 Comunicação & Mensageria`: Focado em ferramentas de canais e mensagens (WhatsApp ZapJords / Webhooks).
- **Badges Dinâmicos e Contadores:** Destaque visual do status e quantidade de integrações ativas com transições suaves.

### 16. Múltiplos Fluxos de Follow-Up Automático por Produto / Esteira & Direcionamento via API
- **Esteiras Independentes por Produto:** Permite criar múltiplos fluxos de follow-up automáticos para diferentes produtos ou esteiras de venda (ex: Low Ticket, Mentoria VIP, VSL Produto X, High Ticket) dentro do mesmo webhook.
- **Barra de Gestão de Fluxos (`FollowupFunnelsBar`):**
  - Dropdown com seleção instantânea do produto/fluxo ativo para edição dos passos.
  - Indicador do fluxo principal (`⭐ Padrão`).
  - Criação de novos fluxos de follow-up (`➕ Novo Fluxo`) com identificador único (`followup_id`) para chamadas via API.
  - Renomeação rápida (`✏️ Renomear`) e exclusão segura (`🗑️ Excluir`): contatos que estavam percorrendo o fluxo excluído são migrados automaticamente para o fluxo padrão no Passo #1.
  - Popups centralizados com backdrop escuro e sem fechamento acidental por clique externo.
- **Sub-Abas Internas de Organização do Follow-Up:**
  - `💬 Passos & Esteiras`: Seleção do produto/esteira ativa e edição de todos os passos e mensagens.
  - `🌙 Janela Comercial`: Configuração do Não Perturbe e horários permitidos de disparo diário.
  - `🎯 Gatilhos Inteligentes`: Regras de cancelamento por resposta, etiquetas de compra e tags ZapVoice.
  - `🚪 Regras de CRM`: Definição de tempo limite de abandono para mover leads para "Não Converteu / Desistiu".
- **Sub-Abas Internas por Passo (`FollowupStepCard`):** Cada passo possui suas próprias abas de configuração interna para eliminar a rolagem vertical: `💬 Mensagem` (seleção de IA, Fixa ou Template WhatsApp), `🎯 Público-Alvo` (Re-tentativas, Remarketing D+1, Compradores ou Todos) e `🎥 Mídia` (Áudio PTT humanizado, Vídeo, Imagem ou Documento).
- **Ocultação Inteligente Quando Desativado:** Caso o interruptor mestre de Follow-Up Automático esteja desativado, toda a área inferior (sub-abas, esteiras, passos e regras) é completamente ocultada da tela, mantendo uma visualização minimalista e livre de distrações visuais.
- **Direcionamento via API (`POST /leads/assign-followup` e `POST /leads/assign-funnel`):**
  - Endpoint dedicado para vincular contatos de disparos em massa a um fluxo específico de produto:
  ```json
  POST /leads/assign-followup
  {
    "followup_id": "mentoria_vip",
    "phones": ["5511999999999", "5511888888888"]
  }
  ```
  - Ao ser atribuído a um novo produto, o progresso do lead é resetado para o Passo #1 (`followup_step = 0`), garantindo o envio sequencial completo do novo produto.
- **Worker & Pipeline de Execução:**
  - O Celery Beat (`tasks.py`) processa os passos de cada produto de forma isolada, filtrando leads pelo seu `active_followup_funnel_id`.
  - O modal de inspeção de pipeline (`FollowupPipelineModal`) e os cartões de leads (`LeadCard`) exibem com clareza o badge do produto ativo (`📦 mentoria_vip`).

---

## 🚀 Como Iniciar (Setup Local)

### 1. Requisitos
- [Docker](https://www.docker.com/) e [Docker Compose](https://docs.docker.com/compose/install/) instalados.

### 2. Configuração de Variáveis
Crie um arquivo `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sua_chave_aqui
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ai_agent_db
POSTGRES_PORT_EXTERNAL=5433
```

### 3. Rodar a Aplicação
Suba os containers em modo de desenvolvimento:

```bash
docker-compose -f docker/docker-compose-local.yml up -d --build

docker-compose -f docker/docker-compose-local.yml up -d --build frontend backend

```

- **Frontend:** [http://localhost:5300](http://localhost:5300)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 17. Funis de Conversão por Dúvida (Áudios Humanizados PTT & Sequências Pré-Configuradas)
- **Disparo de Alta Conversão por Pergunta:** Para dúvidas frequentes e cruciais do lead (ex: *"como funciona o curso de vcs?"*, *"qual o formato das aulas?"*), permite disparar um funil pré-configurado contendo áudio humanizado gravado em primeira pessoa (PTT) acompanhado de mensagens e mídias sequenciais com delay, aumentando drasticamente a taxa de conversão do lead em vez de gerar um textão via IA.
- **Similaridade Semântica via Embeddings OpenAI:**
  - Matching de alta precisão através do cálculo de similaridade de cosseno contra a pergunta principal e suas variações alternativas cadastradas.
  - Limiar de sensibilidade configurável via slider (padrão inteligente: 82%).
- **Frequência de Disparo Inteligente:**
  - `👤 1x por lead (Recomendado)`: Dispara a sequência de conversão apenas na primeira vez que o lead fizer a pergunta. Caso o mesmo lead pergunte novamente em turnos futuros, a IA responde normalmente via RAG/LLM.
  - `♾️ Sempre que o lead perguntar`: Dispara o funil pré-configurado sempre que houver o match semântico.
- **Sequenciador de Passos com Delays:**
  - Suporte a passos encadeados com delays configuráveis em segundos (Passo 1: Áudio PTT; Passo 2: Mensagem de Texto após 3s; etc.).
  - Upload direto de áudios para o MinIO/S3 ou inserção de URLs externas.
- **Continuidade e Memória Conversacional da IA:**
  - A transcrição/resumo do áudio e as mensagens do funil são gravadas no histórico conversacional consolidado da sessão.
  - Nos turnos seguintes, a IA compreende exatamente o que foi dito no áudio e texto do funil, mantendo coerência absoluta nas respostas.
- **Custo R$ 0,00 de LLM & Raio-X Detalhado:**
  - O disparo do funil responde em frações de segundo com consumo zero de tokens de geração.
  - O `ChatPlayground` exibe o player de áudio interativo, balões individuais com delay e o diagnóstico visual completo via Raio-X.
### 18. Sincronização em Tempo Real & Filtros do Inbox de Dúvidas (WebSocket & Query Engine)
- **Atualização Instantânea Sem Refresh:** O Inbox de Dúvidas atualiza instantaneamente em tempo real via WebSockets (`/ws/events`). Quando o agente de IA não souber responder a uma dúvida durante um atendimento ativo com um lead ou usuário, a nova dúvida surge no painel imediatamente sem a necessidade de recarregar a página manualmente.
- **Broadcast Multi-Worker Resiliente:** Disparado pelo backend através da publicação no canal Redis (`websocket_broadcast`), garantindo sincronização perfeita tanto em instâncias FastAPI quanto em workers assíncronos do Celery.
- **Sincronia Bidirecional das Ações:** Ações de responder dúvida (RAG), ensinar no prompt do agente ou descarte (individual e em massa) propagam eventos em tempo real para sincronizar o status e contadores de todas as abas abertas.
- **Indicador de Conexão Ao Vivo:** O cabeçalho do Inbox conta com um badge dinâmico (`🟢 Ao vivo` / `🟡 Conectando`) que assegura a integridade da conexão do operador com o servidor.
- **Painel de Filtros Avançados:**
  - **Por Agente:** Permite selecionar um agente específico no dropdown dinâmico ou visualizar dúvidas de todos os agentes.
  - **Por Contato / Telefone:** Campo de pesquisa livre que busca pelo número de WhatsApp do lead, identificador numérico de lead nas tabelas de automação ou termos do histórico contextual.
  - **Por Origem da Dúvida:** Filtra dúvidas geradas em testes diretos (`💻 Chat Direto`) ou originadas em atendimentos reais do WhatsApp (`💬 Integração ZapJords`).
  - **Por Período (Data Inicial e Final):** Filtro por data de criação (`created_at`) cobrindo o dia completo em UTC/horário de Brasília.
  - **Botão de Limpeza em 1 Clique:** Redefine todos os filtros aplicados e reinicia a paginação de forma suave.

---

## 🧪 Suíte de Testes

Para garantir a estabilidade do sistema, você pode executar a suíte completa de testes (Backend e Frontend) de forma unificada.

### 1. Testes Locais (Rápido)
Ideal para o dia a dia de desenvolvimento. Requer as dependências instaladas localmente.
```bash
# Via PowerShell
./test_all.ps1

# Via NPM
npm test
```

### 2. Testes via Docker (Ambiente Real)
Recomendado antes de realizar commits ou deploy. Garante que o ambiente de teste seja idêntico ao de produção.
```bash
# Via PowerShell
./test_docker.ps1

# Via NPM
npm run test:docker
```

### 3. Testes Individuais
Se precisar rodar apenas uma parte específica:
```bash
# Apenas Backend
npm run test:backend

# Apenas Frontend
npm run test:frontend
```

## ✨ Novidades da Versão (v1.1.0)

Esta versão traz melhorias críticas de desempenho e segurança de contatos na automação de webhooks:
- **Filtro Real de Contatos Permitidos (Whitelist) e Mensagens Bloqueadas (Blacklist)**: Ativação e processamento estrito das regras de autorização de contatos no backend. Se "Contatos Permitidos" estiver ativo no painel, apenas os números listados (validando os últimos 8 dígitos) ou nomes correspondentes são respondidos, bloqueando todos os outros automaticamente. A lista de bloqueios também impede o processamento de conversas indesejadas.
- **Otimização de Desempenho e Velocidade da Lista de Contatos**: Remoção de subqueries aninhadas e lentas de dentro do SQL principal que faziam Full Table Scan. O cálculo de disparos e filtros de leads agora é computado de forma extremamente rápida em lote na memória (Python) para a página atual de leads, derrubando o tempo de carregamento da listagem de contatos de segundos para milissegundos.
- **Ordenação por Interações Recentes**: Contatos agora são exibidos na lista ordenados pela data da última mensagem (`ultima_mensagem_em DESC`), trazendo as conversas ativas no momento para o topo de forma dinâmica.
- **Suíte de Testes 100% Homologada**: Correção de tipagens de data no PostgreSQL (`datetime` em substituição de strings de mock) e URLs de endpoints de testes, garantindo que toda a suíte de testes de webhooks passe perfeitamente.

## ✨ Novidades da Versão (v2.5.0)

Esta versão traz a reformulação completa e observabilidade avançada do **Pipeline de Automação do AgenteFlow**, estruturada e implementada por Aryaraj:
- **Métricas de Latência e Performance por Etapa**: Exibição da duração individual em milissegundos/segundos de cada etapa da timeline (`⚡ 350ms`, `⚡ 1.8s`) e barra superior consolidada (`PipelineSummaryBar`) com Duração Total, Tokens Consumidos (com indicador de % de Cache), Custo Total em BRL e Status da Execução.
- **Diagnóstico Inteligente de Falhas (Smart Troubleshooting)**: Motor semântico que detecta automaticamente padrões de erro (`Connection refused`, `401 Unauthorized`, `429 Rate Limit`, `Timeout`) e exibe cards visuais com a causa raiz e sugestão prática de resolução (ex: orientando o uso de `http://host.docker.internal:8000` em ambiente Docker).
- **Barra de Ações Rápidas (`PipelineActionToolbar`)**: Botões de 1 clique para **Reprocessar / Reenviar Evento** (acionando a rota `/retry` do backend sem necessitar de nova mensagem do lead) e **Copiar Pipeline JSON** formatado para a área de transferência.
- **Filtros por Categorias (`PipelineFilterBar`)**: Abas com contadores dinâmicos para alternar rapidamente entre `Todos`, `🧠 IA & Decisões`, `🛠️ Ferramentas & Mídia` e `❌ Erros & Alertas`.
- **Suíte de Testes Automatizados Expandida**: Cobertura estrita no Vitest (`AutomationPipelineModal.test.jsx`) com 13 testes aprovados e no Pytest (`test_webhook_retry.py`) com 100% de aprovação.

## ✨ Novidades da Versão (v2.4.0)

Esta versão introduz a separação do prompt de instruções do sistema do agente em duas partes (Estático e Dinâmico), otimizando custos e latência por meio de **Prompt Caching**:
- **Prompt Estático (Prompt Cache):** Instruções fundamentais de persona, diretrizes de comportamento e base de conhecimento fixa, enviadas no início do prompt.
- **Prompt Dinâmico:** Instruções de variáveis de contexto, condicionais e regras temporárias, concatenadas no final para não invalidar o cache estático do prefixo.
- **Interface Chaveada (Abas):** Visualização e edição chaveadas no `PromptEditor` via botões `🔒 Estático (Prompt Cache)` e `⚡ Dinâmico`.
- **Script de Migração Automático:** Inclusão e verificação da coluna `dynamic_prompt` na tabela `agent_config` no banco de dados.

## ✨ Novidades da Versão (v2.3.0)

Esta versão traz o recurso de Assistente de Projeto integrado à automação e captura inteligente de conversões/vendas:
- **Assistente de Projeto via Etiqueta e Palavras-Chave**: Permite que o robô seja alternado de sua persona padrão de atendimento de produto para um assistente analítico e estratégico do projeto através de palavras-chave customizadas (ex: `#projeto` e `#sair_projeto`) que adicionam ou removem a tag configurada na integração.
- **Métricas e Relatórios Analíticos em Tempo Real**: Quando no modo assistente de projeto, a IA responde com dados consolidados do mês de leads, total e contagem de vendas na nova tabela do banco, solicitações recentes de suporte humano dos últimos 7 dias e uma análise inteligente de objeções com propostas de melhoria de conversão baseadas em contatos frios/mornos.
- **Webhook e Rota de Vendas (`POST /sales/receive`)**: Rota pública e unificada para capturar vendas diretas de plataformas como Hotmart e Kiwify para persistência no banco de dados local.
- **Configuração no Painel de Webhooks (Chatwoot)**: Novos inputs de configuração de palavra-chave de ativação/desativação, tag do assistente e mensagens personalizadas de entrada/saída direto no modal de edição.
- **Suíte de Testes Unitários de Backend**: Cobertura estrita desenvolvida em `backend/tests/test_project_assistant.py` garantindo o correto fluxo de rotas, banco e IA.

## ✨ Novidades da Versão (v2.3.0)

Esta versão traz a integração automatizada de webhooks do Chatwoot via API:
- **Gerenciamento de Webhooks via API**: Adicionado suporte para listar, criar e excluir webhooks diretamente na aba "Chatwoot" do modal de configurações de integração.
- **Registro Automático de Callback**: Cria webhooks no Chatwoot apontando automaticamente para a URL de recebimento público do backend com um único clique.
- **Suíte de Testes Automatizados**: Desenvolvido conjunto de testes unitários robustos em `backend/tests/test_chatwoot_webhooks.py` mockando as respostas de API do Chatwoot com isolamento completo.

## ✨ Novidades da Versão (v2.2.0)

Esta versão traz o colapso visual inteligente e edição interativa de blocos condicionais no Prompt Editor:
- **Colapso Inteligente de Condicionais**: Substituição visual automática de blocos condicionais multilinhas extensos (`[IF:...` até `[/IF]`) por uma única linha compactada no estilo Glassmorphism Neon com badge brilhante (`🔀 CONDICIONAL [expressão] ✏️ Clique para editar`). O parser de colapso e reconstrução foi flexibilizado para aceitar espaços adicionais em volta das reticências (`{...}` ou `{ ... }`).
- **Clique Direto Inline e Cursor Pointer**: Suporte completo a `pointer-events: auto` e `cursor: pointer` no botão `✏️ Editar` embutido na linha do editor, acompanhado de um efeito premium de hover com elevação e brilho suave rosa neon. Adicionado listener de cliques diretos no backdrop do editor, resolvendo problemas de simulação em testes do Vitest/Testing Library.
- **Edição Simplificada e Sem Botão "Voltar"**: Quando acessada a edição de um bloco condicional (`ConditionalBuilderModal`), a opção `⬅️ Voltar` é removida em modo de edição (`editMode = true`), restando apenas o botão `❌ Cancelar` para fechar o popup, limpando o fluxo de ações.
- **Mapeamento Bidirecional de Estado**: Algoritmo de parser robusto que reconstrói transparentemente o prompt completo e expandido ao sincronizar ou salvar com o backend/API, garantindo total integridade.
- **Suíte de Testes Ampliada e 100% Corrigida**: Novos testes unitários no Vitest em `conditionalParser.test.js` e em `PromptEditor.test.jsx` corrigidos para validar a estabilidade lógica do colapso e reconstrução de blocos simples e combinados, e a usabilidade de cliques da UI.

## ✨ Novidades da Versão (v2.1.0)

Esta versão traz o controle dinâmico (Painel vs Prompt) de saudações, perguntas e anúncios:
- **Modos de Saudação, Pergunta e Anúncio (Painel vs Prompt)**: Adição de botões seletores HSL Glassmorphic no editor de prompts do painel do agente para escolher se cada fluxo (Saudação curta "Oi", Resposta inicial à pergunta e mensagens de anúncio) deve seguir o padrão estático programado (Painel) ou ser delegado para a Inteligência Artificial (Prompt) com base no prompt de sistema do agente.
- **Injeção Dinâmica de Prompt no Pre-Router**: A IA do Pre-Router agora lê dinamicamente as novas diretrizes do agente principal, permitindo gerar respostas curtas contextuais personalizadas de forma rápida e integrada.
- **Suíte de Testes Dedicada**: Criação de cobertura de testes automatizados com o Pytest em `backend/tests/test_pre_router_modes.py` para certificar o funcionamento das rotas e comportamentos estático e dinâmico.

## ✨ Novidades da Versão (v2.0.0)

Esta versão traz estabilidade a nível de ecossistema, verificação de integridade e a nova página de status do backend:
- **Página de Status Premium na Raiz (`/`)**: Substituição da resposta de erro padrão `404/Not Found` na raiz do backend por uma interface de status extremamente moderna e premium (Dark Mode requintado com HSL-tailored colors, glassmorphism blur e um indicador em pulso verde neon). A página de status exibe a estabilidade de conexão, a versão da API (`v2.0.0`) e calcula a latência em milissegundos dinamicamente.
- **Suíte de Testes Dedicada**: Criação de cobertura de testes automatizados com o Pytest em `backend/tests/test_status_page.py` para certificar a saúde e as respostas esperadas na raiz da API.
- **Evolução de Orquestração Docker**: Provisionamento e rebuild com `--force-recreate` garantindo resiliência e estabilidade total no boot dos containers do projeto localmente.

## ✨ Novidades da Versão (v1.9.2)

Esta versão traz a modularização completa do Visualizador de Logs (`LogsViewer.jsx`), estruturada e implementada por Aryaraj:
- **Refatoração e Limites de Código**: Quebra do componente monolítico de 658 linhas em módulos desacoplados e especializados (< 500 linhas cada), garantindo alta manutenibilidade, Clean Code e conformidade com as regras de desenvolvimento do projeto.
- **Estrutura Modular (`LogsViewerModules/`)**:
  - `constants.js`: Constantes globais (níveis, cores, opções de tail/paginação) e funções de estilo reutilizáveis.
  - `LogsActionBar.jsx`: Barra de ações principal com seletor de dia (dropdown dinâmico com dias reais), linhas por container, botão Carregar Logs, Colar Manualmente, Limpar e contador de linhas totais.
  - `LogsFilterBar.jsx`: Seletor de containers (chips com status 🟢/⚪), filtros rápidos por tag, campos de horário (De/Até), busca com badges fixados (Enter) e chips de nível (CRITICAL/ERROR/WARNING/INFO/DEBUG) com contadores.
  - `LogsTable.jsx`: Tabela de logs com linhas coloridas por nível, seletor de linhas por vez, botões Atualizar/Copiar/Download e paginação (Anterior/Próxima).
  - `LogsPasteModal.jsx`: Modal para colar e analisar logs manualmente (parsing local sem chamar servidor).
- **Backup de Segurança**: Backup integral da versão legada preservado em `codigo_obsoleto/frontend/LogsViewer.backup.jsx`.
- **Suíte de Testes Unitários**: Cobertura completa de testes automatizados em `frontend/src/test/components/LogsViewer.test.jsx` com 100% de aprovação (6 de 6 testes passando).

---

## ✨ Novidades da Versão (v1.9.1)

Esta versão traz a modularização completa da interface de Gerenciamento de Backups (`Backups.jsx`), estruturada e implementada por Aryaraj:
- **Refatoração e Limites de Código**: Quebra do componente monolítico de quase 1.000 linhas em módulos desacoplados e especializados (< 500 linhas cada), garantindo alta manutenibilidade, Clean Code e conformidade com as regras de desenvolvimento do projeto.
- **Estrutura Modular (`BackupsModules/`)**:
  - `BackupStatsCards.jsx`: Métricas superiores (Último Backup, Próximo Backup e Retenção).
  - `BackupActionCards.jsx`: Painéis de ação rápida (Backup Manual e Importação/Upload de Backups Externos).
  - `BackupScheduleForm.jsx`: Formulário de Agendamento Automático com interruptor liga/desliga, seletor de frequência (horas/dias), valor de intervalo, pasta no Backblaze S3 e contagem de retenção.
  - `BackupHistoryList.jsx`: Tabela completa de histórico de backups no S3 (itens por página, botão refresh, barra de seleção e exclusão em lote, checkbox selecionar todos, itens com status/fixar/restaurar/download/excluir, e controles de paginação).
  - `BackupModals.jsx`: Modais de confirmação de exclusão individual, restauração do banco de dados e exclusão em lote.
- **Backup de Segurança**: Backup integral da versão legada preservado em `codigo_obsoleto/frontend/Backups.backup.jsx`.
- **Suíte de Testes Unitários**: Cobertura completa de testes automatizados em `frontend/src/test/components/Backups.test.jsx` com 100% de aprovação (6 de 6 testes passando).

---

## ✨ Novidades da Versão (v1.9.0)

Esta versão traz a modularização completa da arquitetura do balão de mensagens do playground (`MessageBubble.jsx`), estruturada e implementada por Aryaraj:
- **Refatoração e Limites de Código**: Quebra do componente monolítico de mais de 1.300 linhas em módulos desacoplados e especializados (< 500 linhas cada), garantindo alta manutenibilidade, Clean Code e conformidade com as regras de desenvolvimento do projeto.
- **Estrutura Modular (`MessageBubbleModules/`)**:
  - `UserMessageBubble.jsx`: Renderização otimizada das mensagens do usuário (fotos, mídias, formatação de texto e timestamp).
  - `LinkMessageBubble.jsx`: Exibição visual de links disparados pelo robô com detecção automática.
  - `MessageMetaBar.jsx`: Barra com estatísticas de consumo de tokens (IN/OUT/CACHED/TOTAL), cálculo dinâmico de custo em BRL, tempo de resposta, pílulas de modelo/fallback/segurança, botões de feedback e botão de alternância do Raio-X.
  - `ExplainResponseSection.jsx`: Seção "Por que essa resposta?", análise detalhada de fatores de influência de prompt, resumo explicativo, custos da auditoria e chat de debate em tempo real com a IA Auditora.
  - `PromptModal.jsx`: Modal flutuante para visualização de decisões do classificador Pre-Router e do Resolved Prompt do Sistema com botão de cópia.
  - `PreRouterDecisionView.jsx`: Sub-aba com filtros booleanos, intenções do lead, perguntas extraídas e histórico de memórias.
  - `ResolvedPromptView.jsx`: Sub-aba com divisão em blocos (Estático, Dinâmico, Injetado pelo Código, Variáveis de Contexto e Completo).
  - `DebugPanel.jsx`: Painel expansível de Raio-X que orquestra a TimelineView, Fontes RAG recuperadas, Prompt Final, ExplainResponseSection e Tradução automática.
- **Backup de Segurança**: Backup integral da versão legada preservado em `codigo_obsoleto/frontend/MessageBubble.backup.jsx`.
- **Suíte de Testes Unitários**: Cobertura completa de testes automatizados em `frontend/src/test/components/ChatPlayground/MessageBubble.test.jsx` com 100% de aprovação.

---

## ✨ Novidades da Versão (v1.8.9)

Esta versão traz a modularização completa da arquitetura do modal de edição e criação de integrações de Webhook (`EditWebhookModal.jsx`), estruturada e implementada por Aryaraj:
- **Refatoração e Limites de Código**: Quebra do componente monolítico de mais de 2.000 linhas em módulos desacoplados e especializados (< 500 linhas cada), garantindo alta manutenibilidade, Clean Code e conformidade com as regras de desenvolvimento do projeto.
- **Estrutura Modular (`EditWebhookTabs/`)**:
  - `GeralTab.jsx`: Sub-abas de identificação de instâncias, slugs de URL, tabela de leads e configurações de comportamento e envio (áudio, visão, debounce, delay de resposta e divisão de mensagens).
  - `FollowupTab.jsx`: Orquestrador completo de réguas de follow-up automático com passos sequenciais de atraso.
  - `FollowupStepCard.jsx`, `FollowupStepWhatsAppTemplate.jsx` e `FollowupStepMedia.jsx`: Submódulos dedicados à configuração detalhada de passos com suporte a IA Contextual, Templates Oficiais Meta/WhatsApp (ZapVoice) e Upload de Mídias/Áudios humanizados PTT.
  - `FollowupBusinessHours.jsx`: Proteção "Não Perturbe" e janela comercial inteligente com seleção de dias da semana.
  - `FollowupSmartTriggers.jsx`: Gatilhos inteligentes de etiquetas do ZapVoice (cancelamento, ativação obrigatória e aplicação pós-disparo).
  - `SegurancaTab.jsx`: Gestão de contatos autorizados, mensagens bloqueadas e palavras-chave de exclusão de dados (LGPD).
  - `ZapvoiceTab.jsx`: Gerenciamento de credenciais, sincronização automática de etiquetas, transbordo/suporte humano e assistente de projeto.
- **Backup de Segurança**: Backup integral da versão legada preservado em `codigo_obsoleto/frontend/EditWebhookModal.backup.jsx`.
- **Suíte de Testes Automatizados**: Inclusão de testes unitários no Vitest em `frontend/src/test/components/EditWebhookModal.test.jsx` cobrindo a renderização, navegação de abas e interação com subcomponentes.

---

## ✨ Novidades da Versão (v1.8.9) - Correção e Blindagem de Deduplicação de Webhooks

Esta versão traz a blindagem completa contra duplicação de mensagens e templates disparados por webhooks de memória e ecos do ZapVoice:
- **Deduplicação Inteligente Cruzada (Eco ZapVoice + Webhook de Memória)**: Resolução definitiva do problema de mensagens duplicadas (com 7 segundos de diferença) no histórico do lead. Agora o backend identifica e deduplica disparos quando o ZapVoice envia o eco de saída (`/webhook/receive`) e o funil/automação envia a confirmação para o Webhook de Memória (`/webhooks/memory`).
- **Compatibilidade de Nono Dígito e Prefixo Telefônico**: Busca inteligente por sufixo de 8 dígitos (`LIKE %suffix8`), permitindo que eventos sejam associados e deduplicados mesmo quando uma plataforma envia o telefone com o 9º dígito (`5585998259497`) e outra envia sem (`558598259497`).
- **Normalização Flexível de Texto e Quebras de Linha**: Algoritmo `texts_match_flexible` que compara textos de templates ignorando diferenças de quebras de linha (`\r\n` vs `\n`), espaços múltiplos ou cabeçalhos de mídia anexada.
- **Cache Local de Extração de Mídias/Documentos**: Evita timeouts e re-disparos (retries) automáticos de plataformas externas através de cache em memória para download e extração de PDFs/documentos.
- **Consolidação Visual no Histórico de Leads**: Filtro dinâmico na API (`events.py`) e no hook do frontend (`useLeadHistoryEvents.js`) que agrupa e oculta duplicatas históricas de templates disparadas em janelas de até 3 minutos para o mesmo contato.
- **Suíte de Testes Automatizados**: Inclusão de testes unitários no backend (`test_memory_webhook_deduplication.py`) e no frontend (`LeadHistory_TemplateDeduplication.test.jsx`) cobrindo cenários de chamadas consecutivas e cruzadas.

---

## ✨ Novidades da Versão (v1.8.8)

Esta versão traz o recurso completo de análise semântica e treinamento de RAG a partir das dúvidas de clientes:
- **Ranking Semântico de Dúvidas e Objeções (Clustering DBSCAN)**: Agrupamento automático e matemático local de mensagens dos usuários em grupos semânticos de dúvidas parecidas utilizando similaridade de cosseno nos embeddings armazenados, sem consumo de tokens de API.
- **Nomeação por IA e Geração de Scripts de Contrabalanço**: Uso de LLM (`gpt-4o-mini`) para gerar títulos amigáveis para as categorias e scripts persuasivos de 2-3 frases sugerindo respostas de quebra de objeção para cada grupo.
- **Aba de Visualização Premium Dark Mode e Roteamento**: Rota `/ranking-duvidas` e seu respectivo link na sidebar de Atendimento seguindo o design visual da plataforma (cards glassmorphic, badges de ranking brilhantes neon e barras de progresso HSL de volume).
- **Treinamento de RAG Integrado (1-Click)**: Modal interativo para adicionar perguntas e respostas ideais diretamente na base de conhecimento do agente.
- **Suíte de Testes Robustos**: Inclusão de testes automatizados unitários em `backend/tests/test_objections.py` cobrando a lógica de banco, endpoints e rate-limit.

---

## ✨ Novidades da Versão (v1.8.6)

Esta versão traz a filtragem e identificação visual de contatos que ainda não enviaram mensagens na plataforma:
- **Identificação de Contatos Sem Mensagens**: Exibição da badge `"⚠️ Sem Mensagens"` de forma proeminente nos cards de contatos capturados no painel de controle (modal de leads do webhook) quando a última interação contiver mensagem nula ou vazia.
- **Filtro de Interação no Webhook Manager**: Adição de um novo select de filtro no painel de contatos ("Interação"), permitindo que o administrador filtre rapidamente contatos entre "Todos", "Sem Mensagens" e "Com Mensagens" na interface, integrando as seleções com a paginação e busca existentes.
- **Resiliência e Portabilidade de Banco (SQLite e PostgreSQL)**: Ajuste da consulta raw da API no backend para calcular a expiração da janela de 24h e o tipo de retorno booleano de forma compatível e resiliente, operando sem problemas em SQLite (testes locais) e no PostgreSQL (ambiente de produção).
- **Suíte de Testes de Backend Ampliada**: Inclusão de testes automatizados com o Pytest em `backend/tests/test_webhook_leads.py` cobrindo o filtro de leads com e sem mensagens.

---

## ✨ Novidades da Versão (v1.8.5)

Esta versão traz o envio da saudação padrão para anúncios puros no primeiro contato de leads:
- **Envio de Saudação para Anúncios Puros**: Correção no fluxo de anúncios do webhook (`webhook_tasks.py`). Agora, contatos que iniciam conversas vindos de anúncios configurados e sem perguntas adicionais (anúncio puro) não são mais interrompidos com status `ignored`. A pipeline continua a execução e responde o lead com a saudação inicial do agente.
- **Limpeza do Histórico de Leads**: O trecho de anúncio correspondente continua sendo limpo na tabela local de leads (`leads_table`) para evitar poluição no RAG e histórico local.
- **Suíte de Testes Unitários Atualizada**: Atualização do teste `test_process_webhook_automation_ad_simple` em `backend/tests/test_ad_webhook_pipeline.py` para validar o status `completed` e a chamada de envio da saudação via Chatwoot.

---

## ✨ Novidades da Versão (v1.8.4)

Esta versão traz o tratamento inteligente e dinâmico de reações/emojis negativos enviados pelo cliente no Chatwoot:
- **Tratamento de Emojis Negativos no Chatwoot**: Integração programática no Pre-Router para detectar emojis negativos (ex: 👎, 🖕, 😡). 
- **Lógica de Etiqueta Dupla e Transição Humana**:
  - No primeiro envio consecutivo de emoji negativo, o robô responde de forma empática sem acionar a LLM principal e aplica a etiqueta de feedback negativo configurada no painel de webhooks (padrão: `feedback_negativo`). A automação de IA continua ativa.
  - No segundo envio consecutivo de emoji negativo (detectado pela presença da tag na conversa), o robô envia uma mensagem de transição amigável e aplica a etiqueta de ignorar (padrão: `humano`), pausando a automação da IA e passando o controle para o atendimento humano.
- **Configuração no Painel de Webhooks**: Campo configurável `"Feedback Negativo (1º emoji)"` adicionado na aba Chatwoot do modal de edição de webhook (com design Glassmorphism e seletor dinâmico de etiquetas).
- **Suíte de Testes Unitários e E2E**: Cobertura de testes unitários do backend (`test_negative_emojis.py`) e validação visual via automação de screenshots com Playwright.

---

## ✨ Novidades da Versão (v1.8.3)

Esta versão traz a funcionalidade de gravação e transcrição de áudio com feedback visual em tempo real no Chat Playground:
- **Feedback de Transcrição em Tempo Real (Web Speech API)**: Integração da SpeechRecognition API nativa do navegador no hook `useChat`. Ao gravar voz, o texto é transcrito localmente em tempo real e exibido dinamicamente na caixa de input de mensagem.
- **Transcrição de Alta Fidelidade com Fallback Resiliente**: Envio assíncrono do áudio binário gravado para o backend via endpoint `/transcribe-audio`, processado pelo Whisper-1 da OpenAI. Caso o navegador envie em um formato incompatível, o backend realiza a conversão automática via `ffmpeg` para MP3 em tempo de execução.
- **Envio Automotivo e Limpeza de Input**: Assim que a transcrição final do Whisper é obtida, a mensagem é disparada automaticamente no chat e a caixa de entrada é limpa.
- **Interrupção Silenciosa ao Enviar Texto**: Se o usuário enviar uma mensagem de texto manualmente (digitando ou enviando o texto da transcrição acumulado) enquanto a gravação de áudio estiver ativa, o sistema desliga o microfone e cancela a gravação na mesma hora de forma silenciosa, prevenindo envios duplicados ou redundantes do Whisper.
- **Suíte de Testes Unitários de Ponta a Ponta**: Cobertura estrita e completa com Vitest para o comportamento do SpeechRecognition/MediaRecorder no frontend e Pytest para os endpoints e rotas de fallback no backend.

---

## ✨ Novidades da Versão (v1.8.2)

Esta versão traz melhorias na detecção de mensagens automáticas e no fluxo de upload do histórico de transcrições:
- **Tratamento Amigável de Status de Envio (AssemblyAI)**: O frontend agora trata o status `completed` de uploads de áudio/vídeo, exibindo a badge `"⏳ Enviado"` no histórico de transcrições durante a transição em cache de 3 segundos, eliminando a exibição temporária da badge de erro `"❌ Erro no Envio"`.
- **Detecção de Mensagens Automáticas de Contatos**: A pipeline do Pre-Router AI detecta mensagens iniciais automáticas de contatos (como auto-responders comerciais ou mensagens de catálogo/ausência) e dispara a saudação inicial configurada (ou padrão) para o cliente.
- **Suíte de Testes Unitários de Frontend e Visual**: Inclusão de cobertura de testes no Vitest para o status `completed` no componente de tabela de transcrições, além de automação visual via Playwright.

---

## ✨ Novidades da Versão (v1.8.1)

Esta versão traz a sincronização proativa e resiliente dos contatos do ZapVoice:
- **Sincronização Proativa de Contatos e Etiquetas no ZapVoice**: Ao gerar e preparar o envio de uma resposta de IA ao Chatwoot, o sistema atualiza proativamente o contato do lead correspondente no banco de dados local Postgres (tabela configurada em `leads_table` no webhook). Os campos atualizados incluem o nome do contato, telefone, a última resposta enviada pelo agente, o timestamp da atualização e a lista de etiquetas ativas da conversa no Chatwoot.
- **Resiliência e Tolerância a Falhas de Conectividade**: Caso a chamada síncrona para obter etiquetas no Chatwoot falhe (falha de rede, timeout, ou erro de status HTTP), o fluxo é tolerante a falhas, realizando o update do lead sem alterar a coluna `labels`, preservando o conjunto de etiquetas pré-existente no banco local de dados.
- **Suíte de Testes Unitários de Integração e Atualização Proativa**: Criação de testes unitários que cobrem a função síncrona de consulta ao Chatwoot e garantem a correta execução da query SQL de atualização de leads nas tarefas em background (Celery).

## ✨ Novidades da Versão (v1.7.3)

Esta versão traz melhorias críticas de UI/UX e testes na interface de teste do chat (ChatPlayground):
- **Limpeza Imediata de Preview de Imagem**: O preview de imagens selecionadas na caixa de entrada do chat agora desaparece instantaneamente quando o usuário clica em enviar (ou aperta Enter), ao mesmo tempo em que a caixa de entrada de texto é limpa. O upload do arquivo ocorre de forma transparente em segundo plano, melhorando consideravelmente a percepção de performance e a experiência de uso.
- **Correção Estética de Preview de Imagem (Glassmorphism)**: Ajuste fino no container de preview utilizando Glassmorphism com efeito blur (`backdrop-filter: blur(10px)`), limites dimensionais estritos para imagens de alta resolução (`64px` x `64px` com `object-fit: cover`) e botão de remover com feedback hover suave.
- **Suíte de Testes do ChatPlayground Estabilizada**: Criação e atualização de testes unitários que cobrem a montagem do preview, metadados da imagem, e validação rigorosa de que o preview é limpo instantaneamente ao enviar a mensagem. Os testes foram atualizados com seletores e expressões regulares robustas.
## ✨ Novidades da Versão (v1.7.4)

Esta versão consolida grandes evoluções no sistema, incluindo o controle financeiro de custos e segurança de mensagens:
- **Filtragem de Custos Zerados no Painel Financeiro**: O endpoint `/financial/report` agora filtra e oculta automaticamente registros com custo de interações igual a `R$ 0.00`, limpando a visualização de agentes inativos.
- **Exibição de Custos Formatada com Duas Casas Decimais**: Ajuste completo na interface (frontend) para exibir valores de custos com exatamente 2 casas decimais (ex: `R$ 15.90` em vez de `R$ 15.9194` ou 4/5 casas decimais).
- **Detecção e Isolamento de Mensagens Automáticas**: O motor de triagem do Pre-Router AI identifica saudações e avisos automáticos externos, respondendo com fallback configurado e isolando estes eventos (`is_automatic=True`) para não contaminar o contexto RAG.
- **Respostas de Saudação de Continuação**: O robô agora envia saudações amigáveis curtas em interações contínuas para manter a naturalidade, evitando repetir a mensagem inicial longa do agente.
- **Flexibilização de Dúvidas Sem Resposta**: Regra de Ouro otimizada no Agente principal para permitir respostas contextuais ricas baseadas no prompt de sistema antes de recorrer à inbox de dúvidas sem resposta.
- **Fluxo Premium de Convites de Usuários**: Substituição do cadastro direto por convites expiráveis (7h, 14h, 24h e 48h) com tabela de gestão, revogação manual e tela de registro com Glassmorphism e tratamento de e-mail duplicado.
- **Tratamento e Descarte de Mensagens de Anúncio**: A pipeline de IA agora intercepta contatos cujo primeiro envio corresponda a um anúncio cadastrado. Se for anúncio puro (sem pergunta acoplada), o robô não envia resposta no Chatwoot, define o status do evento de webhook como `'ignored'`, limpa a coluna de mensagem na tabela local de leads e limpa o debounce de mensagens no Redis. Se a mensagem for mista (anúncio + pergunta), a pipeline remove a parte de anúncio e responde apenas à pergunta limpa, gravando no histórico local apenas a pergunta tratada.

---

## ✨ Novidades da Versão (v1.9.2)

Esta versão traz melhorias críticas de escalabilidade, velocidade e resiliência na importação de conversas do ZapJords/ZapVoice e na gestão de contatos:
- **Importação Resiliente de Conversas e Histórico do ZapJords**:
  - Modal de progresso com design Dark/Glassmorphism aprimorado, cronômetro de importação em tempo real, etapas detalhadas (Contatos e Histórico de Mensagens), barra de porcentagem precisa e backdrop escuro sem resíduos ou bordas azuis indesejadas no cancelamento.
  - Fallback automático de polling a cada 1.5s operando em conjunto com o WebSocket para assegurar que atualizações de progresso e conclusões sejam refletidas instantaneamente, mesmo em oscilações de rede.
  - Resolução rápida de rede interna Docker (`http://zapvoice_app:8000`) para contornar latências do túnel Cloudflare e acelerar a coleta de dados de mensagens.
  - Persistência do estado de conclusão no banco de dados para manter o histórico de importação concluído visível mesmo após reinicializações dos serviços.
- **Otimização de Consultas no Celery Beat (Follow-Ups)**:
  - Eliminação de gargalos N+1 na rotina periódica `check_followup_due` em `tasks.py`, consultando a API externa apenas quando as etiquetas locais não estiverem preenchidas.
- **Seleção Total de Leads e Ações em Lote**:
  - Correção na seleção de todos os contatos capturados (`/leads/ids` e `/leads/all-ids`), eliminando falhas na contagem total e permitindo operações em lote com confirmação segura.
  - Reconexão automática do canal WebSocket de Leads com recarregamento suave dos dados ao restabelecer a conexão.
- **Modularização Arquitetural e Limites de Código**:
  - Criação do hook customizado `useImportChat.js` desacoplando toda a lógica de controle e progresso de `useLeads.js` e mantendo a base de código do frontend estritamente abaixo do limite de 500 linhas.
  - Expansão de testes unitários no frontend (`useImportChat.test.jsx`, `ImportChatProgressModal.test.jsx`) e no backend (`test_import_zapjords_chat.py`, `test_zapjords_import_status.py`).

---

## ✨ Novidades da Versão (v1.9.1)

Esta versão traz o controle visual e funcional da pergunta/mensagem de continuação após a primeira dúvida do usuário:
- **Card de Continuação após 1ª Dúvida Respondida (1ª Mensagem)**: Na aba `Editor Prompt` → sub-aba `👋 Saudação & Consciência Temporal`, o gestor pode configurar exatamente qual pergunta ou mensagem de sondagem (`initial_question_message`) o agente enviará logo após responder à primeira dúvida do usuário (quando a primeira mensagem do contato já for uma pergunta direta).
- **Modos Prompt (IA) vs Painel (Texto Fixo)**: Alternância simplificada entre o modo dinâmico (onde a IA conduz pelo funil) e o modo fixo (onde anexa a pergunta definida no painel, limpando automaticamente perguntas genéricas redundantes da LLM).
- **Sugestões Rápidas de Sondagem**: Atalhos de 1 clique para perguntas clássicas de qualificação (*"Qual é o seu nome?"*, *"Você já trabalha na área ou está começando do zero?"*, etc.).
- **Modularização Arquitetural e Limites de Código**: Extração limpa do componente `TemporalSection.jsx`, mantendo todos os arquivos do módulo de configuração com menos de 300 linhas de código.

---

## ✨ Novidades da Versão (v1.9.0)

Esta versão traz evoluções fundamentais de estabilidade e contextualização da IA para disparos em massa e campanhas:
- **Priorização de template_content no Webhook**: O processamento do webhook agora prioriza o conteúdo real e textual da mensagem enviada (`template_content`) do ZapVoice ao invés do seu nome técnico nos disparos ativos, garantindo que o histórico reflita o texto exato recebido.
- **Identificação de Mensagens de Campanha no Contexto**: As mensagens ativas enviadas pelo robô em outras plataformas (disparos/campanhas) agora são injetadas no histórico da IA com o prefixo explicativo `[Mensagem Ativa de Campanha]: <texto>` para a IA diferenciar facilmente interações espontâneas de saudações em lote.
- **Ampliação do Limite de Varredura de Histórico**: O limite de leitura de registros recentes do banco de dados na memória de contexto do agente foi expandido para **100 mensagens** (antes limitado estritamente a 10). Isso garante que, mesmo sob forte volume de disparos sucessivos, as mensagens humanas reais e antigas não sejam ocultadas do contexto do LLM.
- **Flexibilização do Timeout da Pipeline**: O limite de exibição do status de carregamento da pipeline antes de disparar o alerta de timeout no frontend foi estendido de **45 para 90 segundos**, acomodando períodos de maior lentidão do provedor de IA e de APIs parceiras.
- **Resolução de Timezone no Celery**: Ajuste do import do módulo `timezone` em `tasks.py` para evitar quebras silenciosas no log das tarefas agendadas de backup do banco de dados.

---

## ✨ Novidades da Versão (v1.8.6)

Esta versão traz a nova ferramenta de meta-análise de respostas baseada em LLM no ChatPlayground:
- **Funcionalidade "Por que essa resposta?" no Raio-X**: Ao abrir o painel de debug "Raio-X" sob a resposta da IA no Chat Playground, o usuário agora tem acesso ao botão "🔬 Explicar Raciocínio". Este botão realiza uma chamada on-demand para meta-analisar o resolved_prompt, a pergunta do usuário e a resposta gerada usando o modelo `gpt-4o-mini`, explicando em português de forma detalhada o raciocínio central da IA.
- **Visualização Premium com Cards de Fatores**: A resposta do meta-analisador é renderizada na forma de cards elegantes divididos por categorias de prompt (📄 Estático, ⚡ Dinâmico, 🔌 Injetado, 📚 RAG, 🧠 Geral) e níveis de relevância visual (🔴 Alto, 🟡 Médio, 🟢 Baixo) com estados de loading polidos.
- **Chat de Debate da Resposta (IA Auditora)**: Adicionada a seção "Debater resposta com IA Auditora" que permite iniciar uma conversa interativa em tempo real com um modelo auditor para fazer perguntas de acompanhamento sobre a decisão e comportamento do bot frente ao prompt.
- **Contabilização de Custos de Análise e Debate**: A UI agora calcula dinamicamente e exibe de forma clara na conversa os gastos de tokens reais gerados pela análise da resposta e do debate interativo da resposta analisada em reais (BRL).
- **Suíte de Testes Unitários de Integração**: Testes de ponta a ponta criados e estabilizados no frontend (`MessageBubble.test.jsx`) com 7/7 testes vitest aprovados e no backend (`test_explain_response.py`) testando cenários de sucesso de explicação/debate, erro de API e de custos de tokens com pytest, todos aprovados.

---

## ✨ Novidades da Versão (v1.7.5)

Esta versão traz melhorias no encerramento de conversas após o registro de dúvidas sem resposta, além de refinamentos de UI/UX no painel de testes do chat:
- **Encerramento Amigável de Conversa após Registro de Dúvida**: Quando o robô informa que verificará uma pergunta com a equipe, respostas curtas contendo concordâncias (como "tá ótimo", "ok", "obrigado", "perfeito") agora encerram a conversa amigavelmente com uma confirmação conclusiva. Isso evita que o agente repita em loop a pergunta "como posso te ajudar com outro assunto agora?".
- **Nova Cobertura de Testes Unitários de Fluxo**: Inclusão de testes unitários em `backend/tests/test_initial_messages.py` para validar o comportamento conclusivo diante de concordâncias curtas no segundo turno.
- **Posicionamento e Estilização Premium do Toast de Reset**: O toast de notificação de reset de sessão ("Sessão resetada com sucesso!") no ChatPlayground foi reposicionado do rodapé da tela para o canto superior direito do viewport. A renderização agora utiliza React Portals para garantir posicionamento fixed perfeito no `document.body`, imune a transbordos ou transformações do contêiner pai, e adota design de Glassmorphism Premium com borda neon translúcida.
- **Sincronização de Expiração do Toast com Regras de Negócio**: O timeout de exibição do toast de reset no ChatPlayground foi sincronizado para 5 segundos (5000ms), atendendo às definições de negócio especificadas no projeto.
- **Suíte de Testes Unitários e Cobertura E2E de Frontend**: Inclusão de testes unitários em `ChatPlayground.test.jsx` com Vitest para simular o clique no botão "Resetar" e validar o surgimento do toast. O script de teste e2e com Playwright (`take_screenshot_chat.spec.js`) foi atualizado para validar o fluxo visual de ponta a ponta e coletar o screenshot comprobatório.



### Novidades Anteriores (v1.8.0)
- **Exclusão Parcial de Leads (Desqualificação)**: Permite desqualificar leads diretamente da listagem clicando no ícone de lixeira, abrindo um modal Premium de confirmação. A ação limpa as respostas de qualificação, score, justificativa, classificação e remove a tag `"qualificado"` do contato, sem deletar o contato do banco.
- **Identificação do Agente Qualificador**: Exibe um badge com o nome do agente robô responsável pela qualificação do lead no cabeçalho do card de lead qualificado (`🤖 Agente: Nome`).
- **Fuso Horário de Brasília**: Todas as datas de listagem e alteração de leads na tela de Lead Scoring são convertidas na API para o fuso horário de Brasília (`America/Sao_Paulo` / UTC-3).
- **Maximização das Diretrizes de Lead Scoring**: Inclusão de botão "Maximizar" ao lado do campo de texto de Diretrizes que abre um editor amplo em tela cheia (85% da largura da tela) com sincronização em tempo real e backdrop blur Premium.

### Novidades e Ajustes Recentes (v1.7.8)
- **Diagnóstico Detalhado de Raciocínio da Resposta no Pipeline (`AutomationPipelineModal`)**: No card "Resposta gerada pelo agente", foi adicionada a ferramenta de diagnóstico on-demand `🔬 Por que essa resposta? (Ver Motivo & Passo a Passo)`. Ao clicar, uma meta-análise profunda baseada em IA decompõe de maneira visual e didática:
  - **1ª Parte (Acolhimento / Reação)**: Identifica o trecho inicial e a regra ou motivo que levou à sua formulação.
  - **Própria Pergunta / Condução**: Destaca a pergunta feita ou próximo passo e a etapa do funil correspondente.
  - **Linha de Raciocínio Passo a Passo**: Sequência numerada detalhando como a IA interpretou a entrada do lead, checou o prompt e tomou a decisão final.
  - **Fatores e Regras do Prompt**: As diretrizes e restrições específicas que guiaram a resposta.
  - Os resultados do diagnóstico são persistidos no banco de dados nos metadados do evento para carregamento instantâneo em consultas futuras sem retrabalho da LLM.

### Novidades e Ajustes Recentes (v1.7.7)
- **Botão Maximizar Campo na Ação Final de Qualificação**: Adição de um botão dedicado `⛶ Maximizar Campo` posicionado diretamente acima da caixa de texto da diretriz/pergunta de fechamento na aba de Qualificação de Leads. Ao ser acionado, abre um modal amplo e centralizado na tela (94vw x 84vh, máx 1050px) em estilo Glassmorphism Premium com contadores de caracteres e palavras em tempo real, backdrop escuro com blur e botão de fechamento no cabeçalho.
- **Qualificação e Etiquetagem Automática no ZapVoice / Chatwoot**:
  - Quando a ação final de fechamento é configurada para o gatilho `🌟 Todas` (`all`), a conclusão com sucesso de todas as etapas de sondagem do funil qualifica o lead diretamente, sincronizando as etiquetas configuradas (`lead-qualificado`) na conversa do ZapVoice/Chatwoot.
  - Fallback inteligente no cálculo de pontuação (`lead_scoring_service.py`): quando o agente não possui critérios de qualificação personalizados (ex: funis voltados para captação de dados essenciais como Nome e E-mail), o sistema não aplica o antigo modelo de avaliação de mentoria (que penalizava leads com score 0 e classificação Frio); ao invés disso, atribui automaticamente score 100 e classificação `Quente 🔥`, garantindo a etiquetagem e avanço corretos no fluxo comercial.

### Novidades e Ajustes Recentes (v1.7.6)
- **Navegação de Mensagens no Modal do Pipeline (`AutomationPipelineModal`)**: Inclusão de controles dinâmicos de navegação (`◀ Anterior`, `Próxima ▶` e contador `X/Y`) no cabeçalho do Pipeline, acompanhado de badges de identificação em tempo real (`🟢 Última mensagem do usuário` vs `⏱️ Mensagem anterior (X de Y)`). Ao alternar entre mensagens, todo o diagnóstico de etapas, métricas de tokens, custos e passos da pipeline são sincronizados instantaneamente.
- **Extração Inteligente de Perguntas para Cache Semântico**: Remoção automática de apresentações pessoais (*"Me chamo X"*, *"Meu nome é Y"*, *"Sou o X"*) e saudações no pré-processamento de consultas para o cache semântico. Quando o usuário envia apresentações combinadas com dúvidas (ex: *"Me chamo Aryaraj, qual é o seu nome?"*), o sistema agora extrai a pergunta pura (*"Qual é o seu nome?"*) e a consulta com máxima precisão no cache semântico, eliminando falsos negativos de similaridade.

### Novidades e Ajustes Recentes (v1.7.2)
- **Correção de Falso Positivo na Verificação de Qualificação e Cache Semântico (Criado por Aryaraj)**: Corrigida a validação de qualificação prévia em `chat.py` e `cache_handler.py`, que verificava genericamente o termo `lead_qualificado` no `InteractionLog.debug_info`. Como o `debug_info` continha o `resolved_prompt` do sistema (que descreve as regras da ferramenta `lead_qualificado`), qualquer mensagem anterior da conversa disparava um falso positivo marcando o lead como já qualificado. A verificação agora valida estritamente a execução real da ferramenta (`tool_calls`) ou a persistência em `UserMemoryModel`. Com isso, quando ocorre hit no Cache Semântico em turnos intermediários de qualificação, o sistema aciona o modo `hit_qualification` com a resposta oficial pré-carregada e a IA engata imediatamente a próxima pergunta do funil de sondagem.
- **Resiliência e Conexão PostgreSQL**: Desativação inteligente de prepared statements em cache (`prepared_statement_cache_size=0`) para conexões assíncronas PostgreSQL, mitigando erros do tipo `InvalidCachedStatementError` após alterações dinâmicas de esquema.
- **Saudações Inteligentes com Histórico no Pre-Router**: O motor de triagem do `Pre-Router AI` agora classifica e responde corretamente com saudações diretas a cumprimentos curtos e isolados (como "oi", "olá", "oie", "bom dia"), mesmo que a conversa já contenha histórico de interações anteriores.
- **Sincronização de Etiquetas Chatwoot em Lote e Webhooks**: Integração e persistência bidirecional das etiquetas do Chatwoot no banco local de leads de forma automática nos webhooks, no pipeline de qualificação, e por meio da rota de sincronização em lote `/sync-all` para todos os leads.

### Novidades Anteriores (v1.7.0)
- **Tratamento e Remoção de Anúncios e Pergunta Inicial no Primeiro Contato**: Remoção automática e case-insensitive de mensagens de anúncios cadastrados (`ignore_messages`) na primeira interação de um lead. Se o lead enviar anúncio + uma pergunta, o robô responde à pergunta utilizando a IA e anexa a pergunta de início de atendimento (`initial_question_message`) no final da mensagem. Se o lead enviar apenas o anúncio (ou anúncio + saudação simples), o robô responde com a saudação padrão e anexa a pergunta inicial no final.
- **Tratamento Estrito de Erro de Envio no Webhook**: Casos de falha ou timeout de rede com a API do Chatwoot no envio de respostas agora marcam o status do evento de webhook como `error` (e não mais `completed`). Isso evita que envios malsucedidos contaminem o histórico de contexto do agente.
- **Desduplicação Consecutiva no Histórico de Contexto**: Implementação de filtragem automática no histórico do chat para remover mensagens consecutivas idênticas com o mesmo role e conteúdo. Isso impede que a IA alucine ou faça recapitulações indesejadas causadas por loops ou re-disparos de mensagens no banco.
- **Qualificação de Leads Avançada:** O agente coleta de forma sequencial dados como Nome, E-mail e Empresa, acionando o pipeline ao concluir a qualificação.
- **Integração Multitag Chatwoot:** Permite selecionar múltiplas etiquetas no frontend e sincronizá-las diretamente na conversa do contato no Chatwoot após a qualificação do lead.
- **Protocolo Resiliente de Dúvidas (Inbox):** Respostas em dois turnos para dúvidas inexistentes na base. O agente informa que buscará a equipe (Turno 1) e confirma o registro na Inbox ao receber concordâncias curtas (Turno 2), impedindo loops infinitos e alucinações.
- **Painel de Segurança do Agente Jaime (Melhorias de Estabilidade):**
  - **Injeção Ativa de Regras no Prompt:** Injeção automática das blacklists de concorrentes, tópicos proibidos, políticas de descontos e complexidade do estilo de linguagem (Simples / Padrão / Técnico) no system prompt do agente principal.
  - **Auditoria por IA (Double-Check):** Lógica secundária que audita as respostas com fallback resiliente encadeado de modelos (Modelo Simples -> Modelo Fallback Simples -> GPT-4o-Mini) e substitui respostas ofensivas ou fora da política por mensagens amigáveis de recusa.
  - **Proteção Anti-Loop (Bot Defense):** Novo serviço que limita o máximo de interações e detecta loops semânticos por similaridade de cosseno de embeddings de mensagens anteriores do lead, pausando a automação e aplicando etiquetas de handoff no Chatwoot.
- **Aba Whitelabel Customizada (Premium):** Alinhamento perfeito dos seletores de cores e inputs hexadecimais na mesma linha, design flutuante e responsivo para o botão de copiar snippet na caixa de código de instalação (snippet box), toast de feedback nativo (`app:toast`) ao copiar o código para a área de transferência, e remoção completa do botão de testar widget.
- **Ocultação de Habilidade no Frontend (Fluxo de Suporte):** Ocultação da ferramenta nativa `transferir_robo` na interface do dropdown de Habilidades nas configurações do Agente, mantendo-a totalmente integrada e acionável por meio do painel de Atendimento Humano (ao fechar/resolver o ticket para retornar o controle ao robô), com suporte robusto e tratamento nativo da sincronização de etiquetas Chatwoot mapeado na pipeline do backend.
- **Priorização do GPT-4o-Audio no Motor de Mídia**: O backend agora tenta transcrever arquivos de áudio enviados pelo cliente final usando o modelo premium de áudio `gpt-4o-audio-preview` com codificação base64, garantindo uma transcrição de altíssima fidelidade. Caso ocorra alguma falha ou alucinação, o pipeline de transcrição realiza um fallback automático e transparente para o `whisper-1`.
- **Resiliência e Tolerância a Falhas na Automação de Expiração de Janela 24h**: Ajuste na tarefa periódica `check_window_expiry` para ignorar erros de API ou timeouts com o Chatwoot sem afetar futuras execuções. A verificação do fuso horário agora é imune a conflitos entre bancos de dados PostgreSQL e SQLite local utilizando timezone nativo do banco.
- **Exibição Dinâmica e Premium de Etiquetas Chatwoot**: Integração visual no modal de contatos do Webhook Manager que parseia e renderiza as etiquetas (tags) sincronizadas do Chatwoot ao lado do telefone de cada contato na lista e na visão de accordion expandido com badges em estilo Glassmorphism Premium.

- **Importação de Contatos e Mensagens do ZapVoice / ZapJords:** Permite sincronizar todas as conversas do ZapJords diretamente para a base de contatos com zero custo de LLM, com modal de confirmação prévia, filtragem estrita de badges de sistema (ocultando eventos de funis e tags do atendente) e identificação dedicada nas respostas importadas com o badge `📥 Importação do ZapVoice` no histórico do lead.

### Novidades e Ajustes Recentes (v1.2.9) - Criado por Aryaraj
- **Descarte Automático de Arquivos e Mídias Não Suportadas (`📎 Arquivo (unsupported) recebido`)**:
  - Quando o contato envia um arquivo ou mídia não suportada que o Chatwoot/WhatsApp converte em texto técnico (`📎 Arquivo (unsupported) recebido`), o sistema trata a notificação como evento técnico de bot/sistema.
  - A mensagem é rejeitada na entrada das rotas de webhook (`/webhooks/receive/{token}` e `/webhooks/memory/{token}`) com status `system_badge_ignored`, descartada defensivamente na automação do Celery (`event.status = 'ignored'`) e silenciada no Pre-Router via atalho determinístico (`shortcut-logic` com `eh_mensagem_automatica = True`), garantindo que a IA nunca gere respostas para essas mensagens técnicas.
- **Deduplicação Temporal de Ecos e Webhooks de Memória**:
  - Resolução de duplicidade entre disparos de templates oficiais e ecos de saída (`is_out`) vindos do ZapVoice e webhooks de memória (`/webhooks/memory/{token}`), enriquecendo eventos recentes com o conteúdo de documentos anexados (`document_content`) sem poluir o histórico de conversas do lead.
- **Cofre de Prompts & Backup Automático Pré-Exclusão (`/prompt-vault`)**:
  - Nova área completa e segura para gestão de pacotes de prompts de agentes (Prompt Principal, Pre-Router, Prompt Dinâmico, Diretrizes de Dúvidas Sem Resposta e Ferramentas).
  - Snapshot automático pré-exclusão (`[Backup Pré-Exclusão] {Nome do Agente}`) criado silenciosamente antes de deletar qualquer agente do sistema.
  - Máscara inteligente de visualização para prompts extensos com alternância suave sem piscar a tela e sincronização perfeita de numeração de linhas no editor maximizado.
- **Treinamento de Dúvidas no Inbox por Variação de Pergunta Existente**:
  - No Inbox de Dúvidas Não Respondidas, o operador agora pode vincular dúvidas diretamente como novas variações de perguntas existentes na Base de Conhecimento, com contagem de variações em tempo real, recálculo de vetores semânticos e atualização instantânea via WebSocket.

---

### Novidades e Ajustes Recentes (v1.2.9) - Criado por Aryaraj
- **Otimização de Resposta Terminal com Micro-Prompt para Dúvidas Sem Resposta (Solução 1 - Opção B)**:
  - Quando a ferramenta `registrar_duvida_sem_resposta` é acionada, o sistema encerra o loop de execução de forma terminal, eliminando o 2º turno de ~20.000 tokens no modelo principal (`config.model`, ex: GPT-5-mini).
  - A resposta acolhedora ao lead é gerada pelo novo módulo [`unanswered_micro_responder.py`](file:///c:/Users/aryar/.gemini/antigravity/scratch/Projetos%20Serios/Projetos%20Principais/Cria%20Agente%20de%20IA%20Para%20Automacao/backend/agent_core/logic/unanswered_micro_responder.py) via `gpt-4o-mini` com um micro-prompt enxuto (~100 a 250 tokens), respeitando a persona do agente e a diretriz `unanswered_question_prompt`.
  - Suporte completo a mensagens compostas com múltiplas dúvidas: caso outra dúvida possua resposta confirmada no RAG, o trecho é incorporado e respondido no mesmo turno com precisão.
  - Redução de mais de 99% no consumo de tokens do segundo turno (de ~20.855 para ~150 tokens) e economia de mais de 50% no custo financeiro total da interação.
- **Cofre de Prompts (`/prompt-vault`) & Backup Automático de Segurança Pré-Exclusão**:
  - Nova área segura e desacoplada do ciclo de vida dos agentes para gerenciamento e restauração de prompts mestres (System Prompt, Pre-Router, Prompt Dinâmico, Dúvidas e Ferramentas).
  - Backup automático de segurança gerado silenciosamente antes da exclusão de qualquer agente com prefixo `[Backup Pré-Exclusão] {Nome do Agente}`.
  - Suporte a cópia com 1 clique, download (.json e .txt), restauração em agente existente ou criação de novo agente a partir do snapshot.
- **Descarte de Notificações de Mídias Não Suportadas (`📎 Arquivo (unsupported) recebido`)**:
  - Tratamento inteligente para descartar mensagens técnicas enviadas pelo WhatsApp/Chatwoot como `(unsupported)`, bloqueando imediatamente no webhook de entrada (`system_badge_ignored`), suprimindo no Pre-Router e descartando no Celery para evitar respostas automáticas indevidas da IA.
- **Treinamento de Dúvidas Sem Resposta como Variação de Pergunta Existente**:
  - No Inbox de Dúvidas, o operador pode vincular uma dúvida como nova variação semântica de uma pergunta existente da base selecionada, respeitando o teto de 8 variações e recalculando automaticamente os vetores de embedding.

---

### Novidades e Ajustes Recentes (v1.2.8) - Criado por Aryaraj
- **Modal de Visualização Completa Compacto e Adaptativo**:
  - Ajuste no modal de visualização de texto ampliado (`MaximizedTextModal`) para ter altura adaptativa ao conteúdo (`height: auto`), eliminando espaços vazios para textos curtos e expandindo suavemente até `60vh` (com rolagem estilizada `custom-scrollbar`) para respostas longas do agente.
- **Caixa de Seleção de Contatos Alinhada à Esquerda**:
  - Reposicionamento da caixa de seleção individual de cada lead para a esquerda, imediatamente antes do avatar do contato, criando alinhamento visual perfeito com o checkbox *"Selecionar Todos"* do cabeçalho.
  - Aumento das dimensões do checkbox para 24x24px com bordas de alto contraste, área de clique aprimorada e margem confortável para os botões de ação e exclusão no lado direito.

---

### Novidades e Ajustes Recentes (v1.2.7) - Criado por Aryaraj
- **Memória de Conteúdo de Mídia/Documento em Disparos de Template (`document_content`)**:
  - Quando o webhook de memória (`/webhooks/memory/{token}`) ou de recepção (`/webhooks/receive/{token}`) recebe um disparo de template contendo mídia anexada (`document_content`, `filename`, `media_url`), o sistema incorpora o texto integral extraído do documento ao registro do evento (`📄 [Conteúdo da Mídia/Documento Enviado (filename)]`), salva o conteúdo na memória estruturada de longo prazo do contato (`UserMemoryModel`) e o injeta automaticamente no histórico conversacional (`retrieve_context_history`) para que o agente de IA conheça todo o conteúdo do PDF/mídia enviado ao lead.
  - Caso um eco de saída tenha sido registrado segundos antes apenas com o `template_content`, a chegada subsequente do webhook com `document_content` enriquece automaticamente o evento existente sem duplicar registros.
- **Resolução de Texto Real em Disparos de Templates Oficiais do Follow-Up**:
  - Quando um passo de follow-up do tipo WhatsApp Template é disparado, o sistema agora resolve dinamicamente as variáveis do template (`{{1}}`, `{nome}`, `{primeiro_nome}`, `{telefone}`) com os dados do lead e exibe o texto amigável completo na coluna *Resposta IA* do histórico, eliminando a exibição crua de identificadores técnicos (`[Template Oficial]: pix_gerado`).
- **Eliminação de Triplicação e Deduplicação Inteligente de Ecos do ZapVoice**:
  - Implementação de filtro de deduplicação temporal (janela de 60 segundos) para mensagens de saída (`is_out`) e memórias de agentes recebidas do ZapVoice logo após um disparo de follow-up.
  - Garante que cada disparo de follow-up seja registrado exatamente uma única vez na tabela de histórico de conversas do contato.
- **Identificação Padronizada de Origem (`FOLLOW-UP`)**:
  - Disparos automáticos e manuais de follow-up agora recebem a tag e o badge visual dedicados `FOLLOW-UP`, facilitando a auditoria operacional e distinguindo claramente mensagens da régua contra respostas avulsas do robô ou do usuário.
- **Histórico Limpo em Passos Pulados Manualmente**:
  - Quando um passo de follow-up é pulado através da ação manual *⏭️ Pular Passo*, ele não é inserido no histórico de conversas do contato, mantendo o histórico 100% limpo e livre de falsos positivos de disparo.

### Novidades e Ajustes Recentes (v1.2.6) - Criado por Aryaraj
- **Continuidade Inteligente e Reinício de Temporizador no Follow-Up**:
  - Quando um contato envia uma mensagem enquanto está em um funil de follow-up ativo, o pipeline não é mais cancelado nem pausado indevidamente. O temporizador do passo atual é reiniciado mantendo o lead na mesma etapa.
  - O follow-up agora só é pausado ou cancelado estritamente caso o contato tenha comprado o produto/curso (via webhook ou intenção de compra confirmada), possua etiquetas de exclusão configuradas, ou declare desinteresse explícito de compra.
- **Detecção de Desinteresse Explícito no Pre-Router**:
  - Nova regra inteligente de detecção por atalhos (`_is_disinterest_declaration`) e LLM (`eh_desinteresse`), capturando manifestações como *"não tenho interesse"*, *"não quero comprar"*, *"pare de me mandar mensagem"*, *"pode cancelar"*, cancelando o follow-up de forma segura e registrando o motivo no histórico do lead.
- **Diagnóstico Transparente de Agendamento do Follow-Up na UI**:
  - Modal do Pipeline de Follow-Up enriquecido com detalhes de quando o temporizador começou a contar (`started_at`), estimativa exata do próximo disparo (`estimated_dispatch_at`) e badge visual informativo caso o temporizador tenha sido reiniciado por resposta do cliente (`reset_by_lead_message`).
- **Cálculo de Atraso em Tempo Real com Proteção de Horário Comercial**:
  - Ajuste do cálculo de contagem regressiva para respeitar tempos reais corridos (ex: 24h = dia seguinte no mesmo horário, e não 2 dias úteis acumulados), mantendo a proteção para que disparos só aconteçam dentro da janela de horário comercial configurada.
- **Ações Manuais no Passo Ativo de Follow-Up (Disparar Agora & Pular Passo)**:
  - Adição de dois botões de controle operacional rápido no card do passo que está atualmente ativo na Linha do Tempo:
    1. **🚀 Disparar Agora**: Força o envio imediato da mensagem configurada (IA, fixa ou template oficial WhatsApp) para o contato sem aguardar o temporizador, avançando o contato para a próxima etapa (`followup_step + 1`) e registrando o log do evento.
    2. **⏭️ Pular Passo**: Avança o contato para a etapa seguinte da régua sem disparar a mensagem atual, recalculando a contagem de tempo a partir do momento do pulo.
  - **Popups de Confirmação Seguros (Glassmorphism)**: Em ambos os casos, a interface exibe um popup modal centralizado na tela com backdrop escuro e blur, que não fecha por clique fora e conta com exatamente 1 botão de cancelamento e 1 botão de confirmação com spinner de carregamento e feedback instantâneo por toast.
- **Padronização de Fuso Horário nos Logs e Containers (Horário de Brasília - UTC-3)**:
  - Configuração do fuso `America/Sao_Paulo` nos containers de backend, worker e beat no `docker-compose-producao.yml` e `docker-compose-local.yml`.
  - Instalação e configuração de `tzdata` com `ENV TZ=America/Sao_Paulo` no `backend/Dockerfile` e inicialização no `backend/entrypoint.sh`.
  - Implementação do `BrasiliaFormatter` em `backend/core/logging_setup.py` e hooks no Celery (`setup_logging`) para garantir que os timestamps de console e arquivos de log persistentes (`/app/logs/*.log`) emitam o horário oficial de Brasília.
### Novidades e Ajustes Recentes (v1.3.0) - Criado por Aryaraj
- **Geração e Gestão de Chaves de API (API Key) para Integrações Externas**:
  - Implementação de suporte a chaves individuais por usuário (`UserModel.api_key`), permitindo que aplicações, webhooks e interfaces de terceiros consumam os endpoints protegidos do sistema através do header padrão `X-API-Key`.
  - Novos endpoints de autenticação e ciclo de vida de credenciais:
    - `POST /users/me/generate-api-key`: Gera chaves de alta entropia com prefixo padronizado `ag_live_...`.
    - `DELETE /users/me/revoke-api-key`: Revogação imediata da chave ativa do usuário autenticado.
    - `GET /users/me`: Retorna os dados completos do perfil com a `api_key` vinculada.
  - **Validação Resiliente e Híbrida (`verify_api_key`)**: Compatibilidade retroativa total com a chave mestre global do ambiente (`AGENT_API_KEY`) combinada à validação dinâmica das chaves individuais dos usuários ativos no banco PostgreSQL.
  - Script de migração de schema idempotente: [`backend/scripts/add_api_key_to_users.py`](backend/scripts/add_api_key_to_users.py) e registro em [`docs/DATABASE_SCHEMA_LOG.md`](docs/DATABASE_SCHEMA_LOG.md).

- **Reestruturação Modular em Abas do Modal de Configurações**:
  - Reorganização completa do `ProfileSettingsModal` sob a estética **Glassmorphism Premium**, dividindo as preferências em três abas especializadas:
    1. 👤 **Perfil**: Edição de Nome Completo, E-mail e Senha de acesso (com proteção de credenciais mestras para Super Admin).
    2. 🏢 **White-Label**: Nome da empresa, upload com pré-visualização e remoção de logotipo personalizado e controle de tamanho da marca na barra lateral.
    3. 🔑 **Chave API**: Monitoramento do status da chave (`🟢 Ativa`), campo de exibição protegido com botão de visualização em texto plano (👁️/🙈), cópia instantânea com feedback visual, botão de geração/regeneração com modal centralizado de confirmação contra ações acidentais, revogação e guia prático de integração com exemplo de envio de header.

- **Processamento de Aulas em Modo Duplo (Perguntas & Respostas + Chunks Semânticos)**:
  - Adição do endpoint `POST /knowledge-bases/{kb_id}/generate-qa-and-chunks` para ingerir transcrições de vídeo-aulas gerando simultaneamente até 5 perguntas frequentes com respostas pedagógicas e chunks de texto contínuo com overlap de contexto e embeddings OpenAI automáticos.
  - Integração no `TrainingModal` com a opção "Ambos (P&R + Chunks)", enriquecendo a precisão da busca RAG vetorial e textual (FTS) das bases de conhecimento.

- **Auditoria e Cobertura de Testes Unitários (100% de Sucesso)**:
  - Backend: `backend/tests/test_user_api_key.py` e `backend/tests/test_qa_and_chunks.py`.
  - Frontend: `frontend/src/test/components/ProfileSettingsModal.test.jsx` e `frontend/src/test/components/TrainingModalBoth.test.jsx`.

---

## 📦 Deploy e Imagens Docker

*(Aviso: Conforme as regras do projeto, nunca gerar ou dar push em tags `latest` no Docker Hub; use sempre tags de versão estritas.)*

### Backend
1. **Build:** `docker build -t aryalvesfernandes/configuraagente:backend-1.2.9 ./backend`
2. **Push:** `docker push aryalvesfernandes/configuraagente:backend-1.2.9`

### Frontend
1. **Build:** `docker build --target production -t aryalvesfernandes/configuraagente:frontend-1.2.9 ./frontend`
2. **Push:** `docker push aryalvesfernandes/configuraagente:frontend-1.2.9`





---

## 📂 Organização de Pastas
- `/backend`: Lógica central, APIs e **suíte de testes**.
- `/frontend`: Dashboard e Interface do Usuário.
- `/docs`: Planos de implementação e evoluções (Arquivado).
- `/widget`: Script para integração do chat em sites externos.
- [`GUIA_API_BASE_DE_CONHECIMENTO.md`](./GUIA_API_BASE_DE_CONHECIMENTO.md): Manual e especificação completa da API REST para criação de bases, envio de transcrições com metadados (módulos, tópicos, capítulos) e integração com aplicações externas.