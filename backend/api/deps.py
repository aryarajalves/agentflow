import os
import logging
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from api.services.auth_service import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

# --- API KEY AUTHENTICATION ---
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_AUTH_HEADER = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_key(
    api_key: str = Security(_API_KEY_HEADER),
    db: AsyncSession = Depends(get_db)
):
    """Dependência que valida a API Key enviada no header X-API-Key."""
    expected = os.getenv("AGENT_API_KEY", "")
    if not api_key:
        if not expected:
            return
        logger.warning("AUTH: API Key ausente na requisição.")
        raise HTTPException(
            status_code=403,
            detail="API Key ausente. Envie o header X-API-Key correto."
        )

    if expected and api_key == expected:
        return

    # Validação da chave individual por usuário ativo
    try:
        from sqlalchemy import select
        from models import UserModel
        result = await db.execute(
            select(UserModel).where(UserModel.api_key == api_key, UserModel.status == "ATIVO")
        )
        user = result.scalar_one_or_none()
        if user:
            return
    except Exception as e:
        logger.error(f"Erro ao verificar api_key de usuário no banco: {e}")

    logger.warning(f"AUTH: API Key inválida! Recebida: {str(api_key)[:8] if api_key else 'None'}...")
    raise HTTPException(
        status_code=403,
        detail="API Key inválida ou ausente. Envie o header X-API-Key correto."
    )

async def get_current_user(token: str = Depends(_AUTH_HEADER)):
    if not token:
        logger.warning("AUTH: Token ausente na requisição")
        raise HTTPException(status_code=401, detail="Token ausente")
    try:
        # Remover 'Bearer ' se presente
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Validar o token com leeway de 60 segundos
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={"leeway": 60}
        )
        user_email: str = payload.get("sub")
        
        if user_email is None:
            logger.warning("AUTH: Payload do token sem 'sub'")
            raise HTTPException(status_code=401, detail="Token inválido")
            
        return user_email
    except JWTError as e:
        logger.warning(f"AUTH: Falha na validação do JWT: {str(e)}")
        now = datetime.now(timezone.utc).timestamp()
        logger.info(f"AUTH: [Debug] Current UTC timestamp: {now}")
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
