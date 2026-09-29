"""
core/logging_setup.py — Log persistente em arquivo (sobrevive a reinício/recriação de container).

Problema que isso resolve: o Visualizador de Logs lê o console (stdout) do Docker,
mas esse console fica preso ao ID do container — se o container for RECRIADO
(deploy de nova versão, `docker stack deploy`, etc.), o histórico de log some,
mesmo que o container só tenha sido "reiniciado" do ponto de vista do usuário.

A solução é gravar os logs também em arquivo, dentro de um volume Docker montado
em /app/logs, que persiste independente do ciclo de vida do container.

Uso: chamar configure_logging("backend") (ou "worker"/"beat") o mais cedo possível
no processo, antes de qualquer outro módulo chamar logging.basicConfig() — como
configuramos os handlers do logger raiz diretamente, chamadas posteriores a
basicConfig() nos outros módulos do projeto viram no-op (Python só aplica
basicConfig se o logger raiz ainda não tiver handlers), então isso também
uniformiza o formato de log do projeto inteiro.
"""
import os
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from core.timezone import get_brasilia_tz

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


class BrasiliaFormatter(logging.Formatter):
    """Formatter que garante que o timestamp do log %(asctime)s seja emitido no fuso de Brasília."""

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone(get_brasilia_tz())
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime(DATE_FORMAT)


def configure_logging(component_name: str = "backend"):
    global _configured
    if _configured:
        return
    _configured = True

    log_dir = os.getenv("LOG_FILE_DIR", "/app/logs")
    formatter = BrasiliaFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Atualiza handlers existentes ou adiciona console handler se nenhum existir
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(formatter)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    # Silencia loggers externos excessivamente verbosos para evitar spam no terminal
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{component_name}.log")
        # 20MB x 5 arquivos por componente — persistente no volume /app/logs
        file_handler = RotatingFileHandler(log_path, maxBytes=20 * 1024 * 1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
        logging.getLogger(__name__).info(f"📁 Log persistente ativo em {log_path}")
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"⚠️ Não foi possível gravar log em arquivo ({log_dir}): {e}. "
            "Verifique se o volume está montado em /app/logs."
        )
