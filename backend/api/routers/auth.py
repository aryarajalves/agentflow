import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

import uuid
from datetime import datetime, timezone, timedelta
from models import UserModel, UserInviteModel
from api.schemas import LoginRequest, UserCreate, UserUpdate, UserInviteCreate, UserInviteResponse, UserRegister
from api.deps import get_db, verify_api_key, get_current_user
from api.services.auth_service import (
    get_password_hash, 
    verify_password, 
    needs_password_rehash,
    create_access_token
)
from api.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication"])

@router.get(
    "/users/me",
    dependencies=[Depends(verify_api_key)],
    summary="Obter Dados do Usuário Logado",
    description="Retorna o perfil completo do usuário autenticado, incluindo permissões de acesso, dados de marca branca (White-Label) e status da Chave de API ativa."
)
async def get_me(current_email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.email == current_email))
    user = result.scalar_one_or_none()
    if not user:
        # Fallback para admin fixo do .env caso não esteja no banco
        from dotenv import dotenv_values
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        env_vars = dotenv_values(env_path) if os.path.exists(env_path) else {}
        admin_email = env_vars.get("ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL") or "admin@agente.com"
        
        if current_email == admin_email:
            return {"id": 0, "name": "Admin Super", "email": admin_email, "role": "Super Admin", "company_name": None, "company_logo": None, "company_logo_size": "medium", "api_key": None}
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "company_name": user.company_name,
        "company_logo": user.company_logo,
        "company_logo_size": user.company_logo_size,
        "api_key": user.api_key
    }

@router.put(
    "/users/me",
    dependencies=[Depends(verify_api_key)],
    summary="Atualizar Perfil e White-Label",
    description="Atualiza informações cadastrais do usuário (nome, senha) ou configurações de marca branca (nome da empresa, logo e tamanho na barra lateral)."
)
async def update_me(user_update: UserUpdate, current_email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.email == current_email))
    user = result.scalar_one_or_none()
    
    from dotenv import dotenv_values
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    env_vars = dotenv_values(env_path) if os.path.exists(env_path) else {}
    admin_email = env_vars.get("ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL") or "admin@agente.com"
    is_env_admin = (current_email == admin_email)

    if not user:
        if is_env_admin:
            admin_pass = env_vars.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD") or "admin123"
            user = UserModel(
                name=user_update.name or "Admin Super",
                email=admin_email,
                password=get_password_hash(admin_pass),
                role="Super Admin",
                status="ATIVO"
            )
            db.add(user)
        else:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    update_data = user_update.model_dump(exclude_unset=True)
    if is_env_admin or (user and user.role == "Super Admin"):
        if "name" in update_data:
            user.name = update_data["name"]
        if "company_name" in update_data:
            user.company_name = update_data["company_name"]
        if "company_logo" in update_data:
            user.company_logo = update_data["company_logo"]
        if "company_logo_size" in update_data:
            user.company_logo_size = update_data["company_logo_size"]
    else:
        if "password" in update_data and update_data["password"]:
            update_data["password"] = get_password_hash(update_data["password"])
            
        for key, value in update_data.items():
            if value is not None:
                setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "company_name": user.company_name,
        "company_logo": user.company_logo,
        "company_logo_size": user.company_logo_size,
        "api_key": user.api_key
    }

@router.post(
    "/users/me/generate-api-key",
    dependencies=[Depends(verify_api_key)],
    summary="Gerar / Regenerar Chave de API",
    description="Gera uma chave de alta entropia com prefixo 'ag_live_' para autenticar requisições de outros sistemas ou interfaces externas."
)
async def generate_user_api_key(current_email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.email == current_email))
    user = result.scalar_one_or_none()
    
    from dotenv import dotenv_values
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    env_vars = dotenv_values(env_path) if os.path.exists(env_path) else {}
    admin_email = env_vars.get("ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL") or "admin@agente.com"
    is_env_admin = (current_email == admin_email)

    if not user:
        if is_env_admin:
            admin_pass = env_vars.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD") or "admin123"
            user = UserModel(
                name="Admin Super",
                email=admin_email,
                password=get_password_hash(admin_pass),
                role="Super Admin",
                status="ATIVO"
            )
            db.add(user)
        else:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    import secrets
    new_api_key = f"ag_live_{secrets.token_hex(24)}"
    user.api_key = new_api_key
    await db.commit()
    await db.refresh(user)

    return {
        "success": True,
        "api_key": user.api_key,
        "message": "Nova Chave de API gerada com sucesso!"
    }

@router.delete(
    "/users/me/revoke-api-key",
    dependencies=[Depends(verify_api_key)],
    summary="Revogar Chave de API",
    description="Revoga a chave de API ativa do usuário logado, desativando o acesso de qualquer integração externa que a utilize."
)
async def revoke_user_api_key(current_email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.email == current_email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    user.api_key = None
    await db.commit()
    return {"success": True, "message": "Chave de API revogada com sucesso."}

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)):
    from dotenv import dotenv_values
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    env_vars = dotenv_values(env_path) if os.path.exists(env_path) else {}

    admin_email = env_vars.get("ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL") or "admin@agente.com"
    admin_password = env_vars.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
    
    if admin_email and admin_password:
        if req.email == admin_email:
            if req.password == admin_password:
                access_token = create_access_token(data={"sub": admin_email})
                return {"success": True, "token": access_token, "user": {"name": "Admin Super", "role": "Super Admin"}}

    try:
        result = await db.execute(select(UserModel).where(UserModel.email == req.email))
        db_user = result.scalar_one_or_none()
        if db_user:
            is_valid = False
            if db_user.password.startswith("$argon2") or db_user.password.startswith("$2b$") or db_user.password.startswith("$2a$"):
                is_valid = verify_password(req.password, db_user.password)
                if is_valid and needs_password_rehash(db_user.password):
                    # Migração transparente automática para Argon2id + Pepper
                    db_user.password = get_password_hash(req.password)
                    await db.commit()
            else:
                is_valid = (db_user.password == req.password)
                if is_valid:
                    db_user.password = get_password_hash(req.password)
                    await db.commit()
            
            if is_valid:
                access_token = create_access_token(data={"sub": db_user.email})
                return {"success": True, "token": access_token, "user": {"name": db_user.name, "role": db_user.role, "id": db_user.id}}
    except Exception as e:
        logger.error(f"Erro no login ao acessar DB: {e}")

    raise HTTPException(status_code=401, detail="Email ou senha incorretos")

@router.get("/users", dependencies=[Depends(verify_api_key), Depends(get_current_user)])
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).order_by(UserModel.id.desc()))
    users = result.scalars().all()
    return users

@router.post("/users", dependencies=[Depends(verify_api_key), Depends(get_current_user)])
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    if user.role == "Super Admin":
        raise HTTPException(status_code=400, detail="Não é permitido criar usuários com o cargo de Super Admin.")
        
    user_data = user.model_dump()
    user_data["password"] = get_password_hash(user.password)
    db_user = UserModel(**user_data)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.put("/users/{user_id}", dependencies=[Depends(verify_api_key), Depends(get_current_user)])
async def update_user(user_id: int, user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if user.role == "Super Admin" and db_user.role != "Super Admin":
        raise HTTPException(status_code=400, detail="Não é permitido elevar outros usuários para o cargo de Super Admin.")
        
    update_data = user.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["password"] = get_password_hash(update_data["password"])
        
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.delete("/users/{user_id}", dependencies=[Depends(verify_api_key), Depends(get_current_user)])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if db_user.role == "Super Admin":
        raise HTTPException(status_code=400, detail="O Super Admin do sistema não pode ser removido.")
        
    await db.delete(db_user)
    await db.commit()
    return {"success": True}

@router.post("/system/reset-database", dependencies=[Depends(verify_api_key), Depends(get_current_user)])
async def reset_database(db: AsyncSession = Depends(get_db)):
    """
    AÇÃO CRÍTICA: Limpa todos os dados do sistema.
    """
    from sqlalchemy import text
    try:
        tables = [
            "interaction_logs", "session_summaries", "feedback_logs",
            "prompt_drafts", "agent_tools", "agent_knowledge_bases",
            "knowledge_items", "knowledge_bases", "google_tokens",
            "user_memory", "global_context_variables", "agent_config",
            "tools"
        ]
        
        # Tenta TRUNCATE em bloco primeiro (mais rápido e reseta IDs)
        try:
            # PostgreSQL permite truncar várias tabelas de uma vez com CASCADE
            tables_str = ", ".join(tables)
            await db.execute(text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE"))
            
            # Limpeza total de usuários (O acesso Super Admin continua via .env)
            await db.execute(text("DELETE FROM users"))
            
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning(f"Truncate falhou (provavelmente lock), tentando via Delete: {e}")
            
            # Fallback: Deleta um por um se o truncate falhar
            for table in tables:
                try:
                    await db.execute(text(f"DELETE FROM {table}"))
                except Exception as del_err:
                    logger.warning(f"Erro ao deletar {table}: {del_err}")
            
            # Limpeza total de usuários no fallback também
            await db.execute(text("DELETE FROM users"))
            await db.commit()
            
        return {"status": "success", "message": "All data wiped"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/invites", response_model=UserInviteResponse, dependencies=[Depends(verify_api_key), Depends(get_current_user)])
async def create_invite(invite: UserInviteCreate, db: AsyncSession = Depends(get_db)):
    # Criar expiração baseada em validity_hours
    expires_at = datetime.now(timezone.utc) + timedelta(hours=invite.validity_hours)
    token = str(uuid.uuid4())
    
    db_invite = UserInviteModel(
        token=token,
        role=invite.role,
        expires_at=expires_at,
        is_used=False
    )
    db.add(db_invite)
    await db.commit()
    await db.refresh(db_invite)
    return db_invite

@router.get("/users/invites", response_model=List[UserInviteResponse], dependencies=[Depends(verify_api_key), Depends(get_current_user)])
async def get_invites(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(UserInviteModel)
        .where(UserInviteModel.is_used == False)
        .where(UserInviteModel.expires_at > now)
        .order_by(UserInviteModel.id.desc())
    )
    invites = result.scalars().all()
    return invites

@router.delete("/users/invites/{token}", dependencies=[Depends(verify_api_key), Depends(get_current_user)])
async def delete_invite(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserInviteModel).where(UserInviteModel.token == token))
    db_invite = result.scalar_one_or_none()
    if not db_invite:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    
    await db.delete(db_invite)
    await db.commit()
    return {"success": True}

@router.get("/users/invites/validate/{token}")
async def validate_invite(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserInviteModel).where(UserInviteModel.token == token))
    db_invite = result.scalar_one_or_none()
    if not db_invite:
        raise HTTPException(status_code=404, detail="Convite inválido ou não encontrado")
    
    if db_invite.is_used:
        raise HTTPException(status_code=400, detail="Este convite já foi utilizado")
        
    expires_at_utc = db_invite.expires_at.replace(tzinfo=timezone.utc) if db_invite.expires_at.tzinfo is None else db_invite.expires_at
    if expires_at_utc < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Este convite expirou")
        
    return {
        "valid": True,
        "role": db_invite.role,
        "expires_at": db_invite.expires_at
    }

@router.post("/users/register/{token}")
async def register_user(token: str, reg: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserInviteModel).where(UserInviteModel.token == token))
    db_invite = result.scalar_one_or_none()
    if not db_invite:
        raise HTTPException(status_code=404, detail="Convite inválido ou não encontrado")
    
    if db_invite.is_used:
        raise HTTPException(status_code=400, detail="Este convite já foi utilizado")
        
    expires_at_utc = db_invite.expires_at.replace(tzinfo=timezone.utc) if db_invite.expires_at.tzinfo is None else db_invite.expires_at
    if expires_at_utc < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Este convite expirou")
        
    # Verificar se o e-mail já está em uso
    email_result = await db.execute(select(UserModel).where(UserModel.email == reg.email))
    existing_user = email_result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Este e-mail já está em uso")
        
    # Criar usuário
    hashed_password = get_password_hash(reg.password)
    db_user = UserModel(
        name=reg.name,
        email=reg.email,
        password=hashed_password,
        role=db_invite.role,
        status="ATIVO"
    )
    db.add(db_user)
    
    # Marcar convite como usado
    db_invite.is_used = True
    
    await db.commit()
    await db.refresh(db_user)
    
    return {"success": True, "user_id": db_user.id}


