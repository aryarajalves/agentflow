#!/bin/sh
set -e

# Garante fuso horário de Brasília (UTC-3) por padrão
export TZ="${TZ:-America/Sao_Paulo}"

# Garante que binários instalados via pip estejam no PATH
export PATH="/usr/local/bin:$PATH"

echo "⏳ Aguardando o banco de dados ficar disponível..."

# Extrai host e porta da DATABASE_URL (formato: postgresql+asyncpg://user:pass@host:port/db)
DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+).*|\1|')
DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_PORT=${DB_PORT:-5432}

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
  echo "   Banco não disponível ainda, tentando novamente em 2s..."
  sleep 2
done

echo "✅ Banco de dados disponível."

if [ "$RUN_MIGRATIONS" = "true" ] || [ -z "$1" ]; then
  echo "🛠️ Verificando/Criando banco de dados se necessário..."
  python -c "import asyncio; import models; from database import init_db; asyncio.run(init_db())"

  echo "🔄 Rodando migrações (alembic upgrade head)..."
  python -c "from alembic.config import main; main(argv=['upgrade', 'head'])"
  echo "✅ Migrações concluídas."
else
  echo "⏭️ Pulando inicialização e migrações do banco (executando como serviço de apoio: $1)."
fi

echo "🚀 Iniciando aplicação ou worker..."

if [ "$#" -gt 0 ]; then
  # Se argumentos foram passados (ex: pelo docker-compose command), executa-os
  exec "$@"
else
  # Comando padrão: Iniciar Gunicorn
  exec python -m gunicorn api.main:app -w "${GUNICORN_WORKERS:-4}" -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 600
fi
