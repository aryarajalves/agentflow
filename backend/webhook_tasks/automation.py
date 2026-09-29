import json
import logging
import asyncio
import re
from sqlalchemy.orm import joinedload
from celery_app import app
from models import WebhookEventModel, WebhookConfigModel, AgentConfigModel
from webhook_services import auto_migrate_webhook_columns, resolve_grouped_media
from .traps import handle_traps_and_validations
from .pipeline_ai import execute_agent_pipeline
from .dispatch import handle_post_execution_and_dispatch

logger = logging.getLogger(__name__)

@app.task(bind=True, name="webhook_tasks.process_webhook_automation")
def process_webhook_automation(self, event_id: int):
    """Orquestrador principal do pipeline de automação de webhooks."""
    import webhook_tasks
    db = webhook_tasks.SessionLocal()
    try:
        # 1. AUTO-MIGRAÇÃO DE COLUNAS
        webhook_tasks.auto_migrate_webhook_columns(db)

        event = db.query(WebhookEventModel).filter(WebhookEventModel.id == event_id).first()
        if not event:
            return

        if event.status in ("cancelled", "grouped"):
            logger.info(f"⏭️ Ignorando evento {event_id} (Status: {event.status})")
            return

        event.status = "processing"
        db.commit()

        is_simulated = False
        if event.raw_payload:
            try:
                p_data = json.loads(event.raw_payload)
                if isinstance(p_data, dict) and p_data.get("simulated"):
                    is_simulated = True
            except Exception:
                pass
        
        webhook_tasks._add_step(db, event_id, "🚀 Iniciando Pipeline", "A tarefa de automação foi iniciada pelo worker." + (" (Modo Simulação MOCK)" if is_simulated else ""))

        config = db.query(WebhookConfigModel).filter(WebhookConfigModel.id == event.webhook_config_id).first()
        if not config:
            return

        if not config.agent_id:
            webhook_tasks._add_step(db, event_id, "⚠️ Sem agente configurado", "Configure um agente nas configurações do webhook para continuar.")
            event = db.query(WebhookEventModel).filter(WebhookEventModel.id == event_id).first()
            event.status = "completed"
            db.commit()
            return

        # 2. RESOLUÇÃO DE MÍDIAS AGRUPADAS
        if "[AUDIO PENDENTE]" in (event.mensagem or "") or "[IMAGE PENDENTE]" in (event.mensagem or ""):
            webhook_tasks.resolve_grouped_media(db, event, config, event_id)

        msg_type = (event.message_type or "text").lower()
        msg_text = (event.mensagem or "").strip().lower()
        if (
            "(unsupported)" in msg_text
            or "[unsupported]" in msg_text
            or "arquivo (unsupported)" in msg_text
            or msg_type == "unsupported"
        ):
            webhook_tasks._add_step(
                db,
                event_id,
                "🚫 Arquivo não suportado ignorado",
                "A mensagem recebida é um evento/arquivo não suportado pelo WhatsApp/Chatwoot (ex: '📎 Arquivo (unsupported) recebido'). Descartando automação sem responder ao usuário."
            )
            event = db.query(WebhookEventModel).filter(WebhookEventModel.id == event_id).first()
            event.status = "ignored"
            event.is_automatic = True
            db.commit()
            return

        if msg_type in ["video", "document"]:
            webhook_tasks._add_step(db, event_id, f"🚫 Mídia não suportada ({msg_type})", "Não foi possível enviar pro agente já que é um tipo mídia que não aceita.")
            event.status = "completed"
            db.commit()
            return

        if msg_type == "text":
            webhook_tasks._add_step(db, event_id, "📝 Mensagem de texto", "Tipo de mensagem identificado como texto. Continuando pipeline...")

        db_agent = db.query(AgentConfigModel).options(
            joinedload(AgentConfigModel.knowledge_bases)
        ).filter(AgentConfigModel.id == config.agent_id).first()
        if not db_agent:
            webhook_tasks._add_step(db, event_id, "❌ Agente não encontrado", f"ID: {config.agent_id}")
            event = db.query(WebhookEventModel).filter(WebhookEventModel.id == event_id).first()
            event.status = "error"
            db.commit()
            return

        # 3. TRAPS E VALIDAÇÕES PRÉVIAS
        should_stop, lead_internal_id, last_msg, lead_created_at = handle_traps_and_validations(db, event, config, event_id)
        if should_stop:
            return

        agent_config = webhook_tasks._build_agent_config(db_agent)
        webhook_tasks._add_step(db, event_id, "🤖 Conectando ao agente", f"Agente: {db_agent.name}")

        mensagem = event.mensagem or ""
        if event.legenda and not event.legenda.startswith("❌ Erro técnico:"):
            mensagem = f"[Legenda do Usuário]: {event.legenda}\n\n[Análise/Resumo da Mídia]: {mensagem}"

        raw_phone = event.telefone or ""
        clean_phone = re.sub(r"\D", "", raw_phone)
        session_id = str(lead_internal_id) if lead_internal_id else f"tel_{clean_phone}"

        webhook_tasks._add_step(db, event_id, "📨 Mensagem enviada ao agente", mensagem)

        # 4. RECUPERAÇÃO DE HISTÓRICO
        history = webhook_tasks.retrieve_context_history(db, event, db_agent, raw_phone, clean_phone, event_id)

        # 5. EXECUÇÃO DO AGENTE DE IA
        async def _run():
            async with webhook_tasks.async_session_worker() as async_db:
                return await execute_agent_pipeline(
                    db=db,
                    event=event,
                    config=config,
                    db_agent=db_agent,
                    agent_config=agent_config,
                    history=history,
                    mensagem=mensagem,
                    raw_phone=raw_phone,
                    clean_phone=clean_phone,
                    session_id=session_id,
                    lead_internal_id=lead_internal_id,
                    lead_created_at=lead_created_at,
                    event_id=event_id,
                    is_simulated=is_simulated,
                    async_db=async_db
                )

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = executor.submit(lambda: asyncio.run(_run())).result()
            else:
                result = asyncio.run(_run())
        except Exception as ai_err:
            logger.error(f"❌ Erro crítico na execução da IA: {ai_err}")
            webhook_tasks._add_step(db, event_id, "❌ Falha na IA", f"Ocorreu um erro ao processar a mensagem com o agente: {str(ai_err)}")
            raise ai_err

        # 6. PÓS-PROCESSAMENTO E DISPARO
        handle_post_execution_and_dispatch(
            db=db,
            event=event,
            config=config,
            db_agent=db_agent,
            result=result,
            history=history,
            session_id=session_id,
            lead_internal_id=lead_internal_id,
            event_id=event_id,
            is_simulated=is_simulated
        )

    except Exception as e:
        logger.error(f"Erro ao processar webhook event {event_id}: {e}")
        try:
            webhook_tasks._add_step(db, event_id, "❌ Erro no processamento", str(e)[:300])
            ev = db.query(WebhookEventModel).filter(WebhookEventModel.id == event_id).first()
            if ev:
                ev.status = "error"
                ev.legenda = f"❌ Erro técnico: {str(e)[:200]}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
