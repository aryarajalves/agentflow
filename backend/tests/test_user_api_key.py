import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import HTTPException
from models import UserModel
from api.deps import verify_api_key
from api.routers.auth import generate_user_api_key, revoke_user_api_key, get_me

@pytest.mark.asyncio
async def test_generate_and_revoke_api_key():
    # Simula um usuário no banco de dados
    mock_user = UserModel(
        id=1,
        name="Teste Usuário",
        email="teste@exemplo.com",
        password="hash",
        role="Usuário",
        status="ATIVO",
        api_key=None
    )

    # Mock do db session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result

    # 1. Gerar API Key
    res_gen = await generate_user_api_key(current_email="teste@exemplo.com", db=mock_db)
    assert res_gen["success"] is True
    assert res_gen["api_key"].startswith("ag_live_")
    assert mock_user.api_key == res_gen["api_key"]
    assert mock_db.commit.called

    # 2. Get Me deve retornar a api_key
    res_me = await get_me(current_email="teste@exemplo.com", db=mock_db)
    assert res_me["api_key"] == res_gen["api_key"]

    # 3. Revogar API Key
    res_rev = await revoke_user_api_key(current_email="teste@exemplo.com", db=mock_db)
    assert res_rev["success"] is True
    assert mock_user.api_key is None
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_verify_api_key_with_user_key():
    # Mock de usuário ativo com API Key
    mock_user = UserModel(
        id=2,
        name="Lead Manager",
        email="lead@exemplo.com",
        password="hash",
        role="Admin",
        status="ATIVO",
        api_key="ag_live_123456789abcdef"
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result

    # Chave válida deve passar sem exceção
    await verify_api_key(api_key="ag_live_123456789abcdef", db=mock_db)

    # Chave inválida deve levantar HTTPException 403
    mock_result.scalar_one_or_none.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(api_key="ag_live_chave_errada", db=mock_db)
    assert exc_info.value.status_code == 403
