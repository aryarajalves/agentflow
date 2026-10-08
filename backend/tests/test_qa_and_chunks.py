import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from models import KnowledgeBaseModel, KnowledgeItemModel
from sqlalchemy import select, delete

@pytest.mark.asyncio
async def test_generate_qa_and_chunks_auto_save_true(client: AsyncClient, db_session):
    """Valida o processamento conjunto de P&R + Chunks com persistência automática no banco."""
    # 1. Setup da base de teste
    kb = KnowledgeBaseModel(name="Base Teste Aula Híbrida", description="Base para teste de P&R + Chunks")
    db_session.add(kb)
    await db_session.commit()
    await db_session.refresh(kb)
    kb_id = kb.id

    mock_qa = [
        {"pergunta": "O que é este módulo?", "resposta": "Este módulo introduz o curso.", "categoria": "Treinamento"},
        {"pergunta": "Como acessar o material?", "resposta": "O material está no link abaixo.", "categoria": "Treinamento"}
    ]
    mock_chunks = [
        {"text": "Primeiro trecho longo da aula que aborda a introdução e boas vindas."},
        {"text": "Segundo trecho longo da aula que ensina como acessar o material."}
    ]

    async def mock_batch_embeddings(texts):
        return [[0.05] * 1536 for _ in texts], None

    with patch("smart_importer.generate_global_qa", new_callable=AsyncMock) as mock_qa_gen, \
         patch("smart_importer.chunk_text") as mock_chunk_gen, \
         patch("api.routers.transcriptions.get_batch_embeddings", side_effect=mock_batch_embeddings):

        mock_qa_gen.return_value = (mock_qa, {"input_tokens": 50, "output_tokens": 30})
        mock_chunk_gen.return_value = mock_chunks

        payload = {
            "text": "Texto completo da transcrição da aula de exemplo.",
            "total_questions": 2,
            "chunk_size": 1200,
            "overlap": 150,
            "video_title": "Aula 01 - Fundamentos",
            "module_name": "Módulo 1",
            "auto_save": True
        }

        response = await client.post(f"/knowledge-bases/{kb_id}/generate-qa-and-chunks", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["qa_count"] == 2
        assert data["chunks_count"] == 2
        assert data["total_saved"] == 4
        assert "Aula 01 - Fundamentos" in data["chunk_items"][0]["question"]

        # Verificar no banco de dados se os 4 itens foram persistidos na KB
        stmt = select(KnowledgeItemModel).where(KnowledgeItemModel.knowledge_base_id == kb_id)
        res = await db_session.execute(stmt)
        items_in_db = res.scalars().all()
        assert len(items_in_db) == 4

        # Limpar itens criados
        await db_session.execute(delete(KnowledgeItemModel).where(KnowledgeItemModel.knowledge_base_id == kb_id))
        await db_session.execute(delete(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id))
        await db_session.commit()

@pytest.mark.asyncio
async def test_generate_qa_and_chunks_preview_mode(client: AsyncClient, db_session):
    """Valida o modo prévia (auto_save=False) onde retorna a lista sem gravar no banco."""
    kb = KnowledgeBaseModel(name="Base Teste Preview", description="Base para teste de prévia")
    db_session.add(kb)
    await db_session.commit()
    await db_session.refresh(kb)
    kb_id = kb.id

    mock_qa = [{"pergunta": "Pergunta Teste?", "resposta": "Resposta Teste.", "categoria": "Treinamento"}]
    mock_chunks = [{"text": "Trecho da transcrição sem gravação."}]

    with patch("smart_importer.generate_global_qa", new_callable=AsyncMock) as mock_qa_gen, \
         patch("smart_importer.chunk_text") as mock_chunk_gen:

        mock_qa_gen.return_value = (mock_qa, {})
        mock_chunk_gen.return_value = mock_chunks

        payload = {
            "text": "Texto de prévia da transcrição.",
            "total_questions": 1,
            "video_title": "Aula Preview",
            "auto_save": False
        }

        response = await client.post(f"/knowledge-bases/{kb_id}/generate-qa-and-chunks", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["qa_count"] == 1
        assert data["chunks_count"] == 1
        assert "total_count" in data

        # Verificar que NADA foi salvo no banco
        stmt = select(KnowledgeItemModel).where(KnowledgeItemModel.knowledge_base_id == kb_id)
        res = await db_session.execute(stmt)
        items_in_db = res.scalars().all()
        assert len(items_in_db) == 0

        # Limpeza
        await db_session.execute(delete(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id))
        await db_session.commit()

@pytest.mark.asyncio
async def test_generate_qa_and_chunks_validation(client: AsyncClient):
    """Valida erros de validação: base inexistente e texto vazio."""
    # 1. Base inexistente
    res_404 = await client.post(
        "/knowledge-bases/99999999/generate-qa-and-chunks",
        json={"text": "Transcrição válida.", "auto_save": True}
    )
    assert res_404.status_code == 404

    # 2. Texto vazio
    res_400 = await client.post(
        "/knowledge-bases/1/generate-qa-and-chunks",
        json={"text": "   ", "auto_save": True}
    )
    # Deve falhar com 400 ou 404
    assert res_400.status_code in [400, 404]

@pytest.mark.asyncio
async def test_generate_qa_and_chunks_with_enriched_metadata(client: AsyncClient, db_session):
    """Valida o envio de metadados enriquecidos: topics, chapters e extra_metadata."""
    kb = KnowledgeBaseModel(name="Base Teste Metadados Ricos", description="Teste de metadados")
    db_session.add(kb)
    await db_session.commit()
    await db_session.refresh(kb)
    kb_id = kb.id

    mock_qa = [
        {"pergunta": "Como configurar o Pixel?", "resposta": "Vá nas configurações de negócio.", "categoria": "Treinamento"}
    ]
    mock_chunks = [
        {"text": "Trecho da aula sobre Pixel e Domínio."}
    ]

    async def mock_batch_embeddings(texts):
        return [[0.01] * 1536 for _ in texts], None

    with patch("smart_importer.generate_global_qa", new_callable=AsyncMock) as mock_qa_gen, \
         patch("smart_importer.chunk_text") as mock_chunk_gen, \
         patch("api.routers.transcriptions.get_batch_embeddings", side_effect=mock_batch_embeddings):

        mock_qa_gen.return_value = (mock_qa, {"input_tokens": 40, "output_tokens": 20})
        mock_chunk_gen.return_value = mock_chunks

        payload = {
            "text": "Transcrição completa da aula de tráfego pago.",
            "total_questions": 1,
            "video_title": "Aula 02 - Pixel e Domínio",
            "module_name": "Módulo 01",
            "chapter_name": "Capítulo 02",
            "topics": ["Pixel", "DNS", "Domínio Próprio"],
            "chapters": ["00:00 Intro", "05:00 Configuração"],
            "extra_metadata": {"duracao": "15min", "plataforma": "Meta"},
            "auto_save": True
        }

        response = await client.post(f"/knowledge-bases/{kb_id}/generate-qa-and-chunks", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["qa_count"] == 1
        assert data["chunks_count"] == 1

        # Verificar se user_suggestions foi passado para o mock de IA
        mock_qa_gen.assert_called_once()
        _, kwargs = mock_qa_gen.call_args
        assert "Pixel, DNS, Domínio Próprio" in kwargs.get("user_suggestions", "")

        # Verificar no banco se os metadados contêm os tópicos, capítulos e dados extras
        stmt = select(KnowledgeItemModel).where(KnowledgeItemModel.knowledge_base_id == kb_id)
        res = await db_session.execute(stmt)
        items = res.scalars().all()
        assert len(items) == 2
        for it in items:
            assert "Vídeo: Aula 02 - Pixel e Domínio" in it.metadata_val
            assert "Tópicos: Pixel, DNS, Domínio Próprio" in it.metadata_val
            assert "Capítulos: 00:00 Intro, 05:00 Configuração" in it.metadata_val
            assert "duracao: 15min" in it.metadata_val

        # Limpeza
        await db_session.execute(delete(KnowledgeItemModel).where(KnowledgeItemModel.knowledge_base_id == kb_id))
        await db_session.execute(delete(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id))
        await db_session.commit()

