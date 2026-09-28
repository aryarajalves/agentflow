import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text, or_
from models import WebhookEventModel, WebhookConfigModel

logger = logging.getLogger(__name__)


def retrieve_context_history(db, event, db_agent, raw_phone, clean_phone, event_id):
    """Recupera o histórico de mensagens anteriores para injeção de contexto formatado como mensagens da sessão."""
    import webhook_tasks
    history = []
    if db_agent.context_window > 0:
        try:
            lead_internal_id = None
            if isinstance(event.webhook_config, dict) and 'leads_table' in event.webhook_config:
                leads_table = event.webhook_config['leads_table']
            else:
                config = db.query(WebhookConfigModel).filter(WebhookConfigModel.id == event.webhook_config_id).first()
                leads_table = config.leads_table if config else None

            if leads_table:
                try:
                    query = text(f"SELECT id FROM {leads_table} WHERE telefone = :tel LIMIT 1")
                    res = db.execute(query, {"tel": event.telefone}).fetchone()
                    if res:
                        lead_internal_id = res[0]
                except Exception:
                    pass
        except Exception as e_sum:
            logger.error(f"Erro ao resolver lead para contexto: {e_sum}")
        
        try:
            search_phones = [raw_phone, clean_phone, f"+{clean_phone}"]
            search_phones = list(dict.fromkeys([p for p in search_phones if p]))
            tel_suffix = clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone

            past_events = db.query(WebhookEventModel).filter(
                WebhookEventModel.webhook_config_id == event.webhook_config_id,
                or_(
                    WebhookEventModel.telefone.in_(search_phones),
                    WebhookEventModel.telefone.like(f"%{tel_suffix}")
                ),
                WebhookEventModel.id != event_id,
                WebhookEventModel.status.in_(["completed", "processed", "delivered", "success"]),
                or_(
                    WebhookEventModel.is_automatic.is_(None),
                    WebhookEventModel.is_automatic == False
                )
            ).order_by(WebhookEventModel.created_at.desc()).limit(100).all()

            past_events.reverse()
            seen_msgs = set()
            for pe in past_events:
                is_agent_event = (pe.dono and pe.dono.lower() in ['agente', 'bot']) or (pe.event_type == 'followup')
                
                if is_agent_event:
                    agent_text = (pe.agent_response or "").strip()
                    if (not agent_text or agent_text.startswith("Modo Silencioso")) and pe.mensagem:
                        raw_msg = pe.mensagem.strip()
                        if not (raw_msg.startswith("🔄") or raw_msg.startswith("[Follow-Up") or raw_msg.startswith("[Disparo")):
                            agent_text = raw_msg
                    
                    if agent_text and not agent_text.startswith("Modo Silencioso") and agent_text not in seen_msgs:
                        history.append({"role": "assistant", "content": agent_text})
                        seen_msgs.add(agent_text)
                else:
                    if pe.mensagem:
                        user_msg = pe.mensagem.strip()
                        if user_msg and not (user_msg.startswith("🔄 [Follow-Up") or user_msg.startswith("[Follow-Up")) and user_msg not in seen_msgs:
                            history.append({"role": "user", "content": user_msg})
                            seen_msgs.add(user_msg)
                    if pe.agent_response:
                        resp_clean = pe.agent_response.strip()
                        if resp_clean and not resp_clean.startswith("Modo Silencioso") and resp_clean not in seen_msgs:
                            history.append({"role": "assistant", "content": resp_clean})
                            seen_msgs.add(resp_clean)

            deduped_history = []
            for msg in history:
                if not deduped_history:
                    deduped_history.append(msg)
                else:
                    last_msg = deduped_history[-1]
                    if msg.get("role") == last_msg.get("role") and msg.get("content", "").strip() == last_msg.get("content", "").strip():
                        continue
                    deduped_history.append(msg)
            history = deduped_history

            if len(history) > (db_agent.context_window * 2):
                history = history[-(db_agent.context_window * 2):]

            if history:
                num_pairs = len(past_events)
                webhook_tasks._add_step(
                    db,
                    event_id,
                    "🧠 Memória de Contexto",
                    f"Injetadas {num_pairs} interações brutas ({len(history)} mensagens) como contexto.",
                    metadata={
                        "messages": history,
                        "total_messages": len(history),
                        "num_interactions": num_pairs,
                        "context_window": getattr(db_agent, 'context_window', 5)
                    }
                )
        except Exception as e:
            logger.error(f"Erro ao recuperar histórico para contexto: {e}")
            webhook_tasks._add_step(db, event_id, "⚠️ Erro na Memória", "Não foi possível carregar o histórico ou resumo anterior.")
            
    return history


async def get_project_assistant_context(db, config):
    """
    Consolida as métricas do projeto para o Assistente de Projeto.
    Retorna leads no mês, vendas no mês e suportes acionados na semana.
    """
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    start_of_week = now - timedelta(days=7)
    
    # 1. Leads no mês
    leads_count = 0
    if config.leads_table:
        try:
            leads_res = await db.execute(
                text(f"SELECT COUNT(*) FROM {config.leads_table} WHERE created_at >= :start_of_month"),
                {"start_of_month": start_of_month}
            )
            leads_count = leads_res.scalar() or 0
        except Exception as e:
            logger.warning(f"Erro ao contar leads no mês: {e}")
            
    # 2. Vendas no mês
    sales_count = 0
    sales_total = 0.0
    try:
        sales_res = await db.execute(
            text("SELECT COUNT(*), SUM(valor) FROM sales WHERE created_at >= :start_of_month"),
            {"start_of_month": start_of_month}
        )
        row = sales_res.fetchone()
        if row:
            sales_count = row[0] or 0
            sales_total = float(row[1] or 0.0)
    except Exception as e:
        logger.warning(f"Erro ao contar vendas no mês: {e}")
        
    # 3. Suportes na semana
    support_requests_list = []
    try:
        support_res = await db.execute(
            text("SELECT user_name, contact_phone, user_email, status, created_at FROM support_requests WHERE created_at >= :start_of_week"),
            {"start_of_week": start_of_week}
        )
        for r in support_res.fetchall():
            support_requests_list.append({
                "nome": r[0] or "Sem nome",
                "telefone": r[1] or "Sem telefone",
                "email": r[2] or "Sem email",
                "status": r[3] or "Aberto",
                "data": r[4].strftime("%d/%m/%Y %H:%M") if r[4] else "Desconhecida"
            })
    except Exception as e:
        logger.warning(f"Erro ao buscar suportes na semana: {e}")
        
    # 4. Leads frios/mornos para análise de conversão
    leads_for_conversion = []
    if config.leads_table:
        try:
            conversion_res = await db.execute(text(f"""
                SELECT contato_nome, telefone, lead_classification, lead_justification 
                FROM {config.leads_table} 
                WHERE lead_classification IS NOT NULL AND lead_classification != ''
                ORDER BY created_at DESC LIMIT 10
            """))
            for r in conversion_res.fetchall():
                leads_for_conversion.append({
                    "nome": r[0] or "Sem nome",
                    "telefone": r[1] or "Sem telefone",
                    "classificacao": r[2] or "Desconhecida",
                    "justificativa": r[3] or "Sem justificativa"
                })
        except Exception as e:
            logger.warning(f"Erro ao buscar leads para análise de conversão: {e}")
            
    return {
        "leads_count": leads_count,
        "sales_count": sales_count,
        "sales_total": sales_total,
        "support_requests": support_requests_list,
        "leads_for_conversion": leads_for_conversion
    }
