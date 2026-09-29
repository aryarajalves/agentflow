import logging
from datetime import datetime, timezone
import pytest
from core.logging_setup import configure_logging, BrasiliaFormatter, LOG_FORMAT, DATE_FORMAT
from core.timezone import get_brasilia_tz

def test_configure_logging_setup():
    """Valida que configure_logging aplica formato com timestamp e silencia bibliotecas verbosas."""
    configure_logging("test_component")

    # 1. Verifica silenciamento de httpx, httpcore e urllib3
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    assert logging.getLogger("urllib3").level == logging.WARNING

    # 2. Verifica se o formato inclui timestamp (asctime) e usa BrasiliaFormatter
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0

    handler = root_logger.handlers[0]
    assert handler.formatter is not None
    assert isinstance(handler.formatter, BrasiliaFormatter)
    assert "%(asctime)s" in handler.formatter._fmt
    assert "%(levelname)s" in handler.formatter._fmt
    assert handler.formatter.datefmt == DATE_FORMAT

    # 3. Testa formatação de um registro de log real com timestamp convertido para Brasília
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=25,
        msg="Teste de mensagem formatada",
        args=(),
        exc_info=None
    )
    # Fixa um timestamp conhecido (ex: 12:00:00 UTC deve ser 09:00:00 em Brasília)
    utc_dt = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    record.created = utc_dt.timestamp()

    formatted = handler.formatter.format(record)
    assert "2026-09-29 09:00:00" in formatted
    assert "[INFO]" in formatted
    assert "[test_logger]" in formatted
    assert "Teste de mensagem formatada" in formatted


def test_brasilia_formatter_standalone():
    """Valida que BrasiliaFormatter converte timestamps UTC para o fuso UTC-3."""
    formatter = BrasiliaFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    record = logging.LogRecord(
        name="worker_test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=10,
        msg="Aviso de teste",
        args=(),
        exc_info=None
    )
    # 15:30:00 UTC = 12:30:00 Brasília
    utc_dt = datetime(2026, 9, 29, 15, 30, 0, tzinfo=timezone.utc)
    record.created = utc_dt.timestamp()
    formatted = formatter.format(record)
    assert "2026-09-29 12:30:00" in formatted
    assert "[WARNING]" in formatted
    assert "[worker_test]" in formatted
    assert "Aviso de teste" in formatted

