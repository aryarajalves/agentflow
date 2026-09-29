"""Funções auxiliares para resolução de URLs, formatação de datas e filtros de badges."""

import os
from datetime import datetime, timezone


def resolve_fast_zapvoice_url(raw_url: str) -> str:
    """
    Substitui a URL pública da Cloudflare pela URL interna do Docker quando disponível,
    evitando que requisições em massa passem pelo túnel da internet (reduz latência de 2s para 10ms).
    """
    url = (raw_url or "").rstrip("/")
    if "api.aryaraj.shop" in url or "localhost:8000" in url or "127.0.0.1:8000" in url:
        return os.getenv("ZAPVOICE_INTERNAL_URL", "http://zapvoice_app:8000").rstrip("/")
    return url


def to_naive_datetime(dt):
    """Converte qualquer datetime ou string para datetime UTC naive (sem tzinfo) para colunas TIMESTAMP."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return datetime.utcnow()
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    return datetime.utcnow()


def to_aware_utc(dt):
    """Converte qualquer datetime ou string para datetime UTC aware (com tzinfo=timezone.utc)."""
    if dt is None:
        return datetime.now(timezone.utc)
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def is_system_or_badge_message(m: dict) -> bool:
    """
    Identifica se a mensagem é um badge ou evento de sistema (ex: marcadores adicionados,
    início de funil, logs de atendente) para não importar como resposta de agente.
    Templates do WhatsApp NUNCA são considerados badges.
    """
    if not isinstance(m, dict):
        return True

    msg_type = str(m.get("message_type") or "").strip().lower()
    meta = m.get("meta_data") if isinstance(m.get("meta_data"), dict) else {}
    content = str(m.get("content") or "").strip()

    # 1. WhatsApp Templates são mensagens legítimas enviadas ao lead (boas-vindas, confirmação de compra, etc.)
    if msg_type == "template" or meta.get("is_template") or content.startswith("[Template:"):
        return False

    sender_type = str(m.get("sender_type") or "").strip().lower()
    if sender_type in ("system", "badge", "event", "log", "system_event"):
        return True

    if msg_type in ("funnel_event", "system_event", "badge", "log", "tag_event", "label_event", "unsupported"):
        return True

    if not content:
        # Se não tem texto nem mídia, não é uma mensagem real
        return not bool(m.get("media_url"))

    content_lower = content.lower()

    # Mensagens técnicas de arquivos / mídias não suportadas (ex: '📎 Arquivo (unsupported) recebido')
    # Tratadas como notificação de sistema/bot e rejeitadas sem processamento
    if "(unsupported)" in content_lower or "[unsupported]" in content_lower or "arquivo (unsupported)" in content_lower:
        return True

    # Menções a marcadores / etiquetas do sistema
    if "marcador(es)" in content_lower:
        return True

    # Notificações de ação de atendente do ZapVoice (ex: 'O atendente Super Admin adicionou...')
    if "o atendente" in content_lower and ("adicionou" in content_lower or "removeu" in content_lower):
        return True

    # Notificações de início ou execução de funis
    if "🚀 funil" in content_lower or "funil em execução" in content_lower or "foi iniciado" in content_lower:
        return True

    return False
