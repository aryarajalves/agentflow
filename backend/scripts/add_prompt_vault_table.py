import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append("/app")
from sqlalchemy import text
from database.connection import engine_sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Cria a tabela prompt_vaults para o Cofre de Prompts se não existir."""
    logger.info("Verificando criação da tabela prompt_vaults...")
    with engine_sync.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS prompt_vaults (
                    id SERIAL PRIMARY KEY,
                    client_id INTEGER,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    source_agent_id INTEGER,
                    source_agent_name VARCHAR(255),
                    backup_type VARCHAR(50) NOT NULL DEFAULT 'manual',
                    system_prompt TEXT NOT NULL DEFAULT '',
                    dynamic_prompt TEXT DEFAULT '',
                    pre_router_prompt TEXT,
                    unanswered_question_prompt TEXT,
                    tool_prompts JSON,
                    extra_metadata JSON,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_prompt_vault_client_id ON prompt_vaults(client_id);
                CREATE INDEX IF NOT EXISTS idx_prompt_vault_backup_type ON prompt_vaults(backup_type);
                CREATE INDEX IF NOT EXISTS idx_prompt_vault_created_at ON prompt_vaults(created_at);
            """))
            conn.commit()
            logger.info("✅ Tabela prompt_vaults e índices criados com sucesso.")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erro ao criar tabela prompt_vaults: {e}")

if __name__ == "__main__":
    migrate()
