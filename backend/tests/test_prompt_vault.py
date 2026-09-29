import pytest
import time
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_prompt_vault_entry(client: AsyncClient):
    """Testa criação manual de um snapshot no Cofre de Prompts e busca por ID."""
    ts = int(time.time())
    payload = {
        "name": f"Prompt Teste {ts}",
        "description": "Backup manual de teste unitário",
        "backup_type": "manual",
        "system_prompt": "Você é um atendente especializado em suporte.",
        "pre_router_prompt": "Regras de triagem customizadas para o teste.",
        "unanswered_question_prompt": "Por favor, aguarde enquanto verificamos.",
    }
    
    # Criar
    create_res = await client.post("/prompt-vault", json=payload)
    assert create_res.status_code == 201
    vault_item = create_res.json()
    assert vault_item["name"] == payload["name"]
    assert vault_item["system_prompt"] == payload["system_prompt"]
    assert vault_item["backup_type"] == "manual"
    vault_id = vault_item["id"]

    # Buscar por ID
    get_res = await client.get(f"/prompt-vault/{vault_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == vault_id
    assert get_res.json()["name"] == payload["name"]


@pytest.mark.asyncio
async def test_list_prompt_vault_filtering(client: AsyncClient):
    """Testa listagem no Cofre de Prompts com filtro por texto e por tipo."""
    ts = int(time.time())
    unique_keyword = f"Kwd_{ts}"
    payload = {
        "name": f"Prompt Especial {unique_keyword}",
        "backup_type": "manual",
        "system_prompt": f"System prompt contendo {unique_keyword}",
    }
    res = await client.post("/prompt-vault", json=payload)
    assert res.status_code == 201

    # Busca com filtro de texto
    search_res = await client.get(f"/prompt-vault?search={unique_keyword}")
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert any(unique_keyword in item["name"] for item in results)

    # Busca por tipo
    type_res = await client.get("/prompt-vault?backup_type=manual")
    assert type_res.status_code == 200
    assert all(item["backup_type"] == "manual" for item in type_res.json())


@pytest.mark.asyncio
async def test_automatic_pre_deletion_backup_on_agent_delete(client: AsyncClient):
    """
    Testa o backup de segurança automático pré-exclusão:
    Ao deletar um agente, o backend deve salvar uma cópia completa dos prompts no Cofre de Prompts.
    """
    ts = int(time.time())
    agent_name = f"Agente Sensível {ts}"
    agent_prompt = f"Prompt valioso do agente que não pode ser perdido {ts}"
    pre_router = f"Pre-Router prompt crítico {ts}"

    # 1. Cria o agente
    agent_res = await client.post("/agents", json={
        "name": agent_name,
        "model": "gpt-4o-mini",
        "system_prompt": agent_prompt,
        "pre_router_prompt": pre_router,
        "is_active": True
    })
    assert agent_res.status_code == 200
    agent_data = agent_res.json()
    agent_id = agent_data["id"]

    # 2. Deleta o agente
    del_res = await client.delete(f"/agents/{agent_id}")
    assert del_res.status_code == 200

    # 3. Confirma que o agente foi deletado
    get_agent = await client.get(f"/agents/{agent_id}")
    assert get_agent.status_code == 404

    # 4. Confirma que o snapshot pré-exclusão foi gerado no Cofre de Prompts
    vault_res = await client.get(f"/prompt-vault?search={agent_name}&backup_type=pre_deletion")
    assert vault_res.status_code == 200
    vault_items = vault_res.json()
    assert len(vault_items) >= 1

    saved_backup = vault_items[0]
    assert saved_backup["backup_type"] == "pre_deletion"
    assert saved_backup["source_agent_name"] == agent_name
    assert saved_backup["system_prompt"] == agent_prompt
    assert saved_backup["pre_router_prompt"] == pre_router
    assert "[Backup Pré-Exclusão]" in saved_backup["name"]


@pytest.mark.asyncio
async def test_restore_prompt_from_vault_to_agent(client: AsyncClient):
    """Testa a restauração de um prompt guardado no cofre para um agente existente."""
    ts = int(time.time())
    
    # 1. Cria um item no cofre
    vault_res = await client.post("/prompt-vault", json={
        "name": f"Prompt Otimizado {ts}",
        "backup_type": "manual",
        "system_prompt": f"System prompt restaurado com maestria {ts}",
        "pre_router_prompt": f"Pre-router restaurado {ts}",
    })
    assert vault_res.status_code == 201
    vault_id = vault_res.json()["id"]

    # 2. Cria um agente com prompt antigo
    agent_res = await client.post("/agents", json={
        "name": f"Agente Alvo {ts}",
        "system_prompt": "Prompt antigo e simples",
        "pre_router_prompt": "Pre-router antigo",
    })
    assert agent_res.status_code == 200
    agent_id = agent_res.json()["id"]

    # 3. Executa a restauração
    restore_res = await client.post(
        f"/prompt-vault/{vault_id}/restore/{agent_id}",
        json={"restore_system_prompt": True, "restore_pre_router": True}
    )
    assert restore_res.status_code == 200
    restored_agent = restore_res.json()
    assert restored_agent["system_prompt"] == f"System prompt restaurado com maestria {ts}"
    assert restored_agent["pre_router_prompt"] == f"Pre-router restaurado {ts}"


@pytest.mark.asyncio
async def test_delete_prompt_vault_entry(client: AsyncClient):
    """Testa exclusão de um item do cofre de prompts."""
    ts = int(time.time())
    create_res = await client.post("/prompt-vault", json={
        "name": f"Prompt Temporário {ts}",
        "system_prompt": "Prompt a ser excluído",
    })
    assert create_res.status_code == 201
    vault_id = create_res.json()["id"]

    # Exclui
    del_res = await client.delete(f"/prompt-vault/{vault_id}")
    assert del_res.status_code == 200

    # Confirma que não existe mais
    get_res = await client.get(f"/prompt-vault/{vault_id}")
    assert get_res.status_code == 404
