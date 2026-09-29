import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from main import app
from webhooks.import_chat_modules.helpers import is_system_or_badge_message

@pytest.mark.unit
def test_is_system_or_badge_message_detection():
    # Mensagens de badges de sistema do ZapVoice que devem ser ignoradas
    assert is_system_or_badge_message({
        "content": "O atendente Super Admin adicionou marcador(es): robo, whatsapp",
        "sender_type": "system"
    }) is True

    assert is_system_or_badge_message({
        "content": "Marcador(es) adicionado(s): aluno",
        "sender_type": "system"
    }) is True

    assert is_system_or_badge_message({
        "content": "🚀 Funil iniciado para o contato",
        "sender_type": "system"
    }) is True

    # Mensagens conversacionais reais que NUNCA devem ser ignoradas
    assert is_system_or_badge_message({
        "content": "Olá, gostaria de saber mais informações",
        "sender_type": "contact"
    }) is False

    assert is_system_or_badge_message({
        "content": "Nosso curso conta com suporte completo!",
        "sender_type": "agent"
    }) is False

    # Template WhatsApp oficial NUNCA é badge
    assert is_system_or_badge_message({
        "content": "Olá! Seja bem-vindo à Bússola Astrológica",
        "message_type": "template",
        "sender_type": "system"
    }) is False

    # Mensagens de Arquivo / Mídia Não Suportada devem ser tratadas como sistema/badge e ignoradas
    assert is_system_or_badge_message({
        "content": "📎 Arquivo (unsupported) recebido",
        "sender_type": "contact"
    }) is True

    assert is_system_or_badge_message({
        "content": "Arquivo (unsupported) recebido",
        "sender_type": "contact"
    }) is True

    assert is_system_or_badge_message({
        "content": "(unsupported)",
        "sender_type": "contact"
    }) is True

    assert is_system_or_badge_message({
        "message_type": "unsupported",
        "content": "qualquer conteudo"
    }) is True
