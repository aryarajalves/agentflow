"""
api/main.py — Ponto de entrada da API modular.

Este módulo monta a aplicação FastAPI e registra todos os sub-roteadores.
O main.py legado pode importar `app` daqui como proxy de compatibilidade.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from core.logging_setup import configure_logging

# Configura o formato de log global persistente com data e hora
configure_logging("backend")
logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from api.limiter import limiter
from api.routers import auth, agents, knowledge, analytics, media, sessions, tools, variables, feedback, chat, tester, integrations, inbox, leads, objections, backups, sales, semantic_cache, question_funnels, transcriptions, prompt_vault
from fastapi import WebSocket, WebSocketDisconnect
from core.websocket import manager

logger = logging.getLogger(__name__)


import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / Shutdown lifecycle."""
    logger.info("🚀 API Modular iniciando...")
    janitor_task = None
    try:
        from database import init_db
        await init_db()
        logger.info("✅ Banco de dados inicializado.")
        
        # Inicializar Redis para WebSocket Pub/Sub
        await manager.init_redis()

        # Inicializar Worker Janitor de Limpeza do Pool em Background
        async def _db_janitor_loop():
            from database.connection import run_pool_janitor
            while True:
                await asyncio.sleep(45)
                await run_pool_janitor()

        janitor_task = asyncio.create_task(_db_janitor_loop())
        logger.info("🧹 [JANITOR DB] Worker de monitoramento do pool ativado (intervalo: 45s).")
    except Exception as e:
        logger.warning(f"⚠️ Falha na inicialização do banco/janitor: {e}")
    
    yield
    
    if janitor_task:
        janitor_task.cancel()
        try:
            await janitor_task
        except asyncio.CancelledError:
            pass
    logger.info("🛑 API Modular encerrando...")


API_DESCRIPTION = """
### 🚀 Bem-vindo à API Oficial do AgenteFlow!

O **AgenteFlow** é uma plataforma corporativa avançada para **criação, gestão, monitoramento e automação de Agentes de Inteligência Artificial**, especializada em atendimento conversacional consultivo (WhatsApp/ZapVoice), vendas automáticas, qualificação de leads e bases de conhecimento com RAG (Retrieval-Augmented Generation) de alta fidelidade.

---

### 🌟 Principais Módulos da Plataforma:

1. **🧠 Agentes de IA e Personas Multimodais:**
   - Criação e parametrização de agentes com modelos de ponta (OpenAI GPT-4o, GPT-5, Whisper).
   - Otimização com **Prompt Caching** (divisão em prompt estático e dinâmico) para redução drástica de custos de tokens.
   - **Pre-Router AI**: Triagem e classificação ultrarrápida de mensagens antes da chamada do agente principal.

2. **📚 Bases de Conhecimento e RAG Semântico (pgvector):**
   - Ingestão inteligente de documentos, planilhas, PDFs e transcrições de aulas.
   - Busca vetorial semântica com similaridade de cosseno, multi-query, re-ranking e preservação de metadados ricos.

3. **🎬 Processamento de Aulas e Transcrições:**
   - Endpoint híbrido de alta performance para fatiamento de aulas em blocos contínuos (chunks) e extração de perguntas & respostas didáticas.
   - Suporte completo a metadados: **Módulo**, **Nome da Aula**, **Capítulos**, **Tópicos Principais** e dados livres.

4. **⚡ Automação de WhatsApp e Webhooks (ZapVoice):**
   - Envio de áudios humanizados PTT com delay configurável.
   - Reconhecimento inteligente de comprovantes de pagamento e prints de tela via OCR.
   - Réguas de follow-up pós-atendimento e cancelamento automático por compra confirmada.

5. **🛡️ Segurança e Autenticação de API:**
   - Integração simples via cabeçalho `X-API-Key: ag_live_...` com chaves individuais por usuário gerenciáveis no painel.

---

### 🔑 Como Testar os Endpoints no Swagger:
1. Clique no botão verde **Authorize 🔓** no canto superior direito.
2. Insira a sua chave no campo **X-API-Key** (`ag_live_...`).
3. Clique em **Authorize** e teste qualquer endpoint diretamente pela interface interativa.
"""

tags_metadata = [
    {
        "name": "Health",
        "description": "Verificação de conectividade, status operacional e integridade dos serviços.",
    },
    {
        "name": "Authentication",
        "description": "Gestão de perfil, credenciais de acesso e emissão/revogação de Chaves de API (`X-API-Key`).",
    },
    {
        "name": "Knowledge Base",
        "description": "Gerenciamento de bases de conhecimento, cálculo de embeddings vetoriais, busca RAG e importação de documentos.",
    },
    {
        "name": "Transcriptions",
        "description": "Processamento inteligente de transcrições de aulas, geração híbrida de P&R didáticas e chunks com metadados.",
    },
    {
        "name": "Agents",
        "description": "Criação, clonagem, configuração de personas, prompts estáticos/dinâmicos e parâmetros dos agentes de IA.",
    },
    {
        "name": "Leads",
        "description": "Gestão de contatos capturados, qualificação, tags de CRM e controle de réguas de follow-up.",
    },
    {
        "name": "Sales",
        "description": "Histórico de transações e vendas integradas via plataformas de checkout (Kiwify, Hotmart, etc.).",
    },
    {
        "name": "webhooks",
        "description": "Configuração de automações, instâncias de conexão com canais de mensagem e réguas de atendimento.",
    },
    {
        "name": "Question Funnels",
        "description": "Funis de conversão por dúvida com sequências de áudios humanizados PTT e continuidade conversacional.",
    },
    {
        "name": "Prompt Vault",
        "description": "Cofre de prompts, versionamento de personas e backups de segurança pré-exclusão.",
    },
    {
        "name": "Semantic Cache",
        "description": "Cache semântico de respostas frequentes para economia de até 90% em tokens e latência zero.",
    },
    {
        "name": "Analytics",
        "description": "Métricas de conversão, custos de tokens por modelo e relatórios operacionais em tempo real.",
    },
    {
        "name": "Chat",
        "description": "Sessões de conversa, histórico em tempo real e playground interativo de atendimento.",
    },
    {
        "name": "Integrations",
        "description": "Conexões externas e chaves de provedores de IA (OpenAI, Anthropic, Gemini, Groq).",
    },
    {
        "name": "Inbox",
        "description": "Caixas de entrada integradas e canais de comunicação com clientes.",
    },
    {
        "name": "Objections",
        "description": "Base estruturada de quebra de objeções e diretrizes de contorno para a IA.",
    },
]

app = FastAPI(
    title="AgenteFlow",
    description=API_DESCRIPTION,
    version="2.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# --- RATE LIMITING ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
cors_origins = [o.strip() for o in raw_origins if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True if cors_origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL EXCEPTION HANDLER ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"ERRO GLOBAL: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor", "error": str(exc)},
    )

# --- HEALTH CHECK & STATUS PAGE ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backend do Projeto: AgenteFlow - Status</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0a0f;
            --card-bg: rgba(20, 18, 30, 0.45);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #8b5cf6;
            --primary-glow: rgba(139, 92, 246, 0.15);
            --accent: #00f2fe;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: relative;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(139, 92, 246, 0.1) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(0, 242, 254, 0.06) 0%, transparent 40%);
        }

        .glow-orb {
            position: absolute;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, var(--primary-glow) 0%, transparent 70%);
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 1;
            pointer-events: none;
            filter: blur(40px);
        }

        .container {
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 520px;
            padding: 24px;
        }

        .status-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-radius: 28px;
            padding: 40px 32px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .status-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 24px 60px rgba(139, 92, 246, 0.15);
        }

        .logo-area {
            display: flex;
            justify-content: center;
            margin-bottom: 24px;
        }

        .logo-circle {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4);
            animation: pulse-glow 3s infinite ease-in-out;
        }

        .logo-circle svg {
            width: 40px;
            height: 40px;
            fill: #ffffff;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(120deg, #ffffff, #d8b4fe, #a5f3fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }

        .subtitle {
            font-size: 15px;
            color: var(--text-muted);
            margin-bottom: 32px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }

        .badge-status {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: var(--success);
            padding: 8px 18px;
            border-radius: 100px;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 32px;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.05);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 0 0 var(--success-glow);
            animation: pulse-dot 1.8s infinite cubic-bezier(0.66, 0, 0, 1);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 28px;
            text-align: left;
        }

        .stat-item {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 16px;
        }

        .stat-label {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-main);
        }

        .footer {
            margin-top: 24px;
            text-align: center;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.25);
            letter-spacing: 0.3px;
        }

        @keyframes pulse-glow {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4);
            }
            50% {
                transform: scale(1.03);
                box-shadow: 0 12px 32px rgba(139, 92, 246, 0.6), 0 0 15px rgba(0, 242, 254, 0.2);
            }
        }

        @keyframes pulse-dot {
            0% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            }
            70% {
                transform: scale(1);
                box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
            }
            100% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
            }
        }
    </style>
</head>
<body>
    <div class="glow-orb"></div>
    <div class="container">
        <div class="status-card">
            <div class="logo-area">
                <div class="logo-circle">
                    <svg viewBox="0 0 24 24">
                        <path d="M12 2c1.1 0 2 .9 2 2v1.07c2.44.42 4.41 2.22 4.93 4.6l.07.33H20c1.1 0 2 .9 2 2v2c0 1.1-.9 2-2 2h-1c0 1.04-.44 1.97-1.15 2.63l.71.72c.39-.39 1.02-.39 1.41 0s.39 1.02 0 1.41l-1.41 1.41c-.39.39-1.02.39-1.41 0l-.72-.71c-.66.71-1.59 1.15-2.63 1.15v1c0 1.1-.9 2-2 2h-2c-1.1 0-2-.9-2-2v-1c-1.04 0-1.97-.44-2.63-1.15l-.72.71c-.39.39-1.02.39-1.41 0l-1.41-1.41c-.39-.39-.39-1.02 0-1.41l.71-.72C4.44 16.97 4 16.04 4 15H3c-1.1 0-2-.9-2-2v-2c0-1.1.9-2 2-2h1c0-1.04.44-1.97 1.15-2.63l-.71-.72c-.39.39-1.02.39-1.41 0s-.39-1.02 0-1.41l1.41-1.41c.39-.39 1.02-.39 1.41 0l.72.71C7.03 4.44 7.96 4 9 4V3c0-1.1.9-2 2-2h1zM9 11c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1zm6 0c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/>
                    </svg>
                </div>
            </div>
            <h1>Backend do Projeto: AgenteFlow</h1>
            <div class="subtitle" style="color: var(--success);">Sistema Ativo</div>
            
            <div class="badge-status" style="margin-bottom: 0;">
                <div class="pulse-dot"></div>
                SISTEMA OPERACIONAL
            </div>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)


@app.get(
    "/ping",
    tags=["Health"],
    summary="Verificação de Saúde (Health Check)",
    description="Retorna status operacional da API para monitoramento e validação de conectividade."
)
async def ping():
    return {"status": "ok", "message": "Backend is reachable"}

# --- STATIC FILES ---
try:
    app.mount("/static", StaticFiles(directory="widget"), name="static")
except Exception:
    logger.warning("⚠️ Diretório 'widget' não encontrado — /static não montado.")

try:
    os.makedirs("tmp_uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="tmp_uploads"), name="uploads")
except Exception:
    logger.warning("⚠️ Não foi possível montar /uploads.")

# --- ROUTERS ---
app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(knowledge.router)
app.include_router(transcriptions.router)
app.include_router(analytics.router)
app.include_router(media.router)
app.include_router(sessions.router)
app.include_router(tools.router)
app.include_router(variables.router)
app.include_router(feedback.router)
app.include_router(chat.router)
app.include_router(tester.router, include_in_schema=False)
app.include_router(integrations.router)
app.include_router(inbox.router)
app.include_router(leads.router)
app.include_router(objections.router)
app.include_router(backups.router, include_in_schema=False)
app.include_router(sales.router)
app.include_router(semantic_cache.router)
app.include_router(question_funnels.router)
app.include_router(prompt_vault.router)




# --- WEBSOCKET ---
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Mantém a conexão aberta. Podemos receber pings se necessário.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        manager.disconnect(websocket)

# Routers legados (importados do main.py original)
try:
    from prompt_lab import router as prompt_lab_router
    app.include_router(prompt_lab_router, include_in_schema=False)
except ImportError:
    logger.warning("⚠️ prompt_lab não encontrado.")

try:
    from session_analysis import router as analysis_router
    app.include_router(analysis_router, include_in_schema=False)
except ImportError:
    logger.warning("⚠️ session_analysis não encontrado.")

try:
    from webhooks.router import router as webhook_router
    app.include_router(webhook_router)
except ImportError:
    logger.warning("⚠️ webhooks.router não encontrado.")
