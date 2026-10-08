# 📖 Guia de Integração da API: Bases de Conhecimento e Transcrições

Este documento descreve detalhadamente todos os endpoints disponíveis na API para que qualquer aplicação externa (LMS, plataformas de membros, plataformas de vídeo, scripts de automação ou CRMs) possa se conectar, **criar ou escolher bases de conhecimento**, **enviar transcrições de aulas com metadados completos** e **alimentar o motor de IA (RAG)** de forma 100% automatizada.

---

## 🔑 1. Autenticação e Ambientes

Todas as requisições autenticadas devem incluir a Chave de API no cabeçalho HTTP:

```http
X-API-Key: ag_live_sua_chave_de_api
Content-Type: application/json
```

> 💡 **Como obter a sua Chave de API:**
> Acesse o painel da aplicação, abra as **Configurações de Perfil** (ícone de engrenagem na barra lateral) e clique na aba **🔑 Chave API**. Gere sua chave (`ag_live_...`) e copie-a.

### 🌐 URLs Base dos Ambientes

| Ambiente | URL Base | Observações |
| :--- | :--- | :--- |
| **Desenvolvimento Local** | `http://localhost:8002` | Para chamadas dentro da mesma máquina/rede |
| **Produção / Servidor** | `https://backendagente.aryaraj.shop` | Túnel Cloudflare / Domínio público oficial |

---

## 📋 2. Gerenciamento de Bases de Conhecimento

### 2.1 Listar Bases de Conhecimento (Escolher Base Existente)
Retorna todas as bases cadastradas na conta para que a interface externa possa exibi-las em um seletor (dropdown).

- **Método:** `GET`
- **Rota:** `/knowledge-bases`

#### Exemplo cURL:
```bash
curl -X GET "http://localhost:8002/knowledge-bases" \
  -H "X-API-Key: ag_live_sua_chave_de_api"
```

#### Exemplo de Resposta (Status 200 OK):
```json
[
  {
    "id": 1,
    "name": "Base de Vendas e FAQ",
    "description": "Perguntas frequentes comerciais",
    "kb_type": "qa",
    "question_label": "Pergunta",
    "answer_label": "Resposta",
    "metadata_label": "Metadado",
    "items": []
  },
  {
    "id": 2,
    "name": "Aulas do Curso Completo",
    "description": "Transcrições e materiais das aulas",
    "kb_type": "qa",
    "question_label": "Pergunta",
    "answer_label": "Resposta",
    "metadata_label": "Metadado",
    "items": []
  }
]
```

---

### 2.2 Criar Nova Base de Conhecimento
Cria uma nova base e retorna o objeto com o `id` gerado.

- **Método:** `POST`
- **Rota:** `/knowledge-bases`

#### Parâmetros do Corpo (JSON):
| Campo | Tipo | Obrigatório | Padrão | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `name` | `string` | **Sim** | `"Nova Base"` | Nome exclusivo da base de conhecimento |
| `description` | `string` | Não | `null` | Breve resumo sobre o conteúdo da base |
| `kb_type` | `string` | Não | `"qa"` | Tipo da base: `"qa"` (perguntas e respostas) ou `"chunks"` |

#### Exemplo cURL:
```bash
curl -X POST "http://localhost:8002/knowledge-bases" \
  -H "X-API-Key: ag_live_sua_chave_de_api" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Curso de Tráfego Pago 2026",
    "description": "Conteúdo das aulas transcritas com P&R didáticas",
    "kb_type": "qa"
  }'
```

#### Exemplo de Resposta (Status 200 OK):
```json
{
  "id": 3,
  "name": "Curso de Tráfego Pago 2026",
  "description": "Conteúdo das aulas transcritas com P&R didáticas",
  "kb_type": "qa",
  "question_label": "Pergunta",
  "answer_label": "Resposta",
  "metadata_label": "Metadado",
  "items": []
}
```

---

### 2.3 Obter Detalhes e Itens de uma Base
- **Método:** `GET`
- **Rota:** `/knowledge-bases/{kb_id}`

```bash
curl -X GET "http://localhost:8002/knowledge-bases/3" \
  -H "X-API-Key: ag_live_sua_chave_de_api"
```

---

### 2.4 Excluir Base de Conhecimento
- **Método:** `DELETE`
- **Rota:** `/knowledge-bases/{kb_id}`

```bash
curl -X DELETE "http://localhost:8002/knowledge-bases/3" \
  -H "X-API-Key: ag_live_sua_chave_de_api"
```

---

## 🎬 3. Envio de Transcrições com Metadados Enriquecidos

### 3.1 Endpoint Híbrido Principal: P&R + Chunks com Salvamento Direto
Este é o endpoint recomendado para automações com aulas. Ele processa o texto integral da transcrição gerando simultaneamente:
1. **5 Perguntas e Respostas Didáticas** formuladas por IA com base no texto.
2. **Chunks Contínuos da Aula** (blocos contínuos preservando o contexto original).
3. **Embeddings Vetoriais (OpenAI pgvector)** calculados automaticamente para busca semântica em milissegundos.
4. **Metadados Completos da Aula** (módulo, aula, tópicos, capítulos) anexados a cada item criado.

- **Método:** `POST`
- **Rota:** `/knowledge-bases/{kb_id}/generate-qa-and-chunks`

#### Parâmetros do Corpo (JSON):
| Campo | Tipo | Obrigatório | Padrão | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `text` | `string` | **Sim** | - | Texto puro da transcrição da aula |
| `video_title` | `string` | Não | `null` | Título ou nome da aula/vídeo |
| `module_name` | `string` | Não | `null` | Nome do módulo (ex: `"Módulo 01 - Fundamentos"`) |
| `chapter_name` | `string` | Não | `null` | Capítulo da aula |
| `chapters` | `list[str]` ou `str` | Não | `null` | Lista de capítulos ou divisões temporais da aula |
| `topics` | `list[str]` ou `str` | Não | `null` | **Tópicos principais da aula:** orienta a IA a focar nessas dúvidas ao gerar o Q&A e fica gravado como metadado |
| `extra_metadata` | `dict` ou `str` | Não | `null` | Dados adicionais livres (ex: link da aula, duração, id no LMS) |
| `total_questions` | `int` | Não | `5` | Número de perguntas/respostas a gerar |
| `chunk_size` | `int` | Não | `1200` | Tamanho máximo em caracteres de cada trecho |
| `overlap` | `int` | Não | `150` | Sobreposição entre trechos para continuidade de contexto |
| `model` | `string` | Não | `"gpt-4o-mini"` | Modelo de IA para formular as perguntas |
| `category_qa` | `string` | Não | `"Treinamento"` | Categoria dos itens de P&R |
| `category_chunks` | `string` | Não | `"Transcrição"` | Categoria dos blocos contínuos |
| `auto_save` | `boolean` | Não | `true` | Se `true`, calcula vetores e salva no banco. Se `false`, retorna prévia sem salvar |

#### Exemplo cURL:
```bash
curl -X POST "http://localhost:8002/knowledge-bases/3/generate-qa-and-chunks" \
  -H "X-API-Key: ag_live_sua_chave_de_api" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Fala galera, nesta aula vamos aprender como criar e instalar o Pixel do Facebook no seu site, configurar as entradas DNS de tipo A e CNAME na Cloudflare e verificar a propagação...",
    "video_title": "Aula 03 - Pixel, DNS e Domínio Próprio",
    "module_name": "Módulo 01 - Infraestrutura de Tráfego",
    "chapter_name": "Capítulo 02 - Apontamentos Técnicos",
    "chapters": [
      "00:00 - Introdução",
      "04:10 - Criação do Pixel na Meta",
      "09:30 - Entradas DNS na Cloudflare",
      "15:00 - Validação e Teste"
    ],
    "topics": [
      "Pixel do Facebook",
      "Cloudflare",
      "Configuração de DNS (Tipo A e CNAME)",
      "Verificação de Domínio"
    ],
    "extra_metadata": {
      "plataforma": "Kiwify",
      "duracao": "18min",
      "link_aula": "https://meucurso.com/aula/102"
    },
    "total_questions": 5,
    "chunk_size": 1200,
    "overlap": 150,
    "model": "gpt-4o-mini",
    "auto_save": true
  }'
```

#### Exemplo de Resposta (Status 200 OK):
```json
{
  "message": "Sucesso! 5 perguntas/respostas e 4 trechos adicionados com sucesso à base #3.",
  "kb_id": 3,
  "qa_count": 5,
  "chunks_count": 4,
  "total_saved": 9,
  "qa_items": [
    {
      "question": "Como configuro as entradas DNS na Cloudflare para o domínio?",
      "answer": "Acesse a aba DNS na Cloudflare, adicione uma entrada do tipo A apontando para o IP do servidor e uma CNAME para o subdomínio correspondente.",
      "category": "Treinamento",
      "metadata_val": "Vídeo: Aula 03 - Pixel, DNS e Domínio Próprio | Módulo: Módulo 01 - Infraestrutura de Tráfego | Capítulo: Capítulo 02 - Apontamentos Técnicos | Capítulos: 00:00 - Introdução, 04:10 - Criação do Pixel na Meta, 09:30 - Entradas DNS na Cloudflare, 15:00 - Validação e Teste | Tópicos: Pixel do Facebook, Cloudflare, Configuração de DNS (Tipo A e CNAME), Verificação de Domínio | plataforma: Kiwify | duracao: 18min | link_aula: https://meucurso.com/aula/102"
    }
  ],
  "chunk_items": [
    {
      "question": "Trecho da Aula #1 (Aula 03 - Pixel, DNS e Domínio Próprio)",
      "answer": "Fala galera, nesta aula vamos aprender como criar e instalar o Pixel do Facebook no seu site...",
      "category": "Transcrição",
      "metadata_val": "Vídeo: Aula 03 - Pixel, DNS e Domínio Próprio | Módulo: Módulo 01 - Infraestrutura de Tráfego | Capítulo: Capítulo 02 - Apontamentos Técnicos | Capítulos: 00:00 - Introdução, 04:10 - Criação do Pixel na Meta, 09:30 - Entradas DNS na Cloudflare, 15:00 - Validação e Teste | Tópicos: Pixel do Facebook, Cloudflare, Configuração de DNS (Tipo A e CNAME), Verificação de Domínio | plataforma: Kiwify | duracao: 18min | link_aula: https://meucurso.com/aula/102"
    }
  ],
  "model_used": "gpt-4o-mini",
  "cost_usd": 0.000192,
  "cost_brl": 0.001037
}
```

---

### 3.2 Gerar Apenas Perguntas e Respostas (Sem Chunks)
Gera uma lista de P&R didáticas a partir do texto enviado.

- **Método:** `POST`
- **Rota:** `/knowledge-bases/generate-qa-from-transcription`

#### Exemplo cURL:
```bash
curl -X POST "http://localhost:8002/knowledge-bases/generate-qa-from-transcription" \
  -H "X-API-Key: ag_live_sua_chave_de_api" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Texto completo da aula...",
    "total_questions": 5,
    "model": "gpt-4o-mini"
  }'
```

#### Exemplo de Resposta:
```json
{
  "items": [
    {
      "pergunta": "Qual a diferença entre campanha CBO e ABO?",
      "resposta": "No CBO o orçamento é distribuído pela IA a nível de campanha, enquanto no ABO o orçamento é definido manualmente em cada conjunto.",
      "categoria": "Documento"
    }
  ],
  "model": "gpt-4o-mini",
  "cost_usd": 0.00012,
  "cost_brl": 0.00065
}
```

---

### 3.3 Gerar Apenas Chunks de Texto (Sem IA)
Divide o texto em blocos menores com tamanho e sobreposição configuráveis sem consumir tokens de LLM.

- **Método:** `POST`
- **Rota:** `/knowledge-bases/generate-chunks-from-transcription`

```bash
curl -X POST "http://localhost:8002/knowledge-bases/generate-chunks-from-transcription" \
  -H "X-API-Key: ag_live_sua_chave_de_api" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Texto longo da transcrição...",
    "chunk_size": 1200,
    "overlap": 150
  }'
```

---

## ✍️ 4. Gestão Manual de Itens (Criar Avulso ou em Lote)

### 4.1 Adicionar Item Individual na Base
Adiciona uma pergunta/resposta ou trecho específico. O embedding vetorial é gerado automaticamente a partir da pergunta e de suas variações.

- **Método:** `POST`
- **Rota:** `/knowledge-bases/{kb_id}/items`

```bash
curl -X POST "http://localhost:8002/knowledge-bases/3/items" \
  -H "X-API-Key: ag_live_sua_chave_de_api" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "O que é CTR no tráfego pago?",
    "answer": "CTR (Click-Through Rate) é a porcentagem de cliques em relação ao número de impressões do anúncio.",
    "category": "Métricas",
    "metadata_val": "Módulo 2 | Aula 04",
    "question_variations": [
      "O que significa a métrica CTR?",
      "Como calcular o CTR?"
    ]
  }'
```

---

### 4.2 Adicionar Múltiplos Itens em Lote (Batch)
Permite salvar vários itens de uma única vez em uma só requisição.

- **Método:** `POST`
- **Rota:** `/knowledge-bases/{kb_id}/items/add-batch`

```bash
curl -X POST "http://localhost:8002/knowledge-bases/3/items/add-batch" \
  -H "X-API-Key: ag_live_sua_chave_de_api" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "question": "Qual o valor do curso?",
        "answer": "O investimento é de 12x de R$ 97,00 ou R$ 997,00 à vista.",
        "category": "Comercial",
        "metadata_val": "Preços 2026"
      },
      {
        "question": "Tem certificado de conclusão?",
        "answer": "Sim, emitido automaticamente após concluir 100% das aulas.",
        "category": "Certificados",
        "metadata_val": "Portal do Aluno"
      }
    ]
  }'
```

---

### 4.3 Atualizar Item Existente
- **Método:** `PUT`
- **Rota:** `/knowledge-items/{item_id}`

```bash
curl -X PUT "http://localhost:8002/knowledge-items/15" \
  -H "X-API-Key: ag_live_sua_chave_de_api" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o valor do curso atualizado?",
    "answer": "O valor é de R$ 1.297,00 à vista.",
    "category": "Comercial",
    "metadata_val": "Preços Atualizados",
    "question_variations": ["Qual o preço?"]
  }'
```

---

### 4.4 Excluir Item Existente
- **Método:** `DELETE`
- **Rota:** `/knowledge-items/{item_id}`

```bash
curl -X DELETE "http://localhost:8002/knowledge-items/15" \
  -H "X-API-Key: ag_live_sua_chave_de_api"
```

---

## 💻 5. Exemplos de Código para Outras Aplicações

### 5.1 Exemplo em Node.js / JavaScript (Fetch)

```javascript
const API_URL = 'http://localhost:8002'; // ou https://backendagente.aryaraj.shop
const API_KEY = 'ag_live_sua_chave_de_api';

async function enviarTranscricaoAula(kbId, aulaData) {
  const response = await fetch(`${API_URL}/knowledge-bases/${kbId}/generate-qa-and-chunks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify({
      text: aulaData.transcricao,
      video_title: aulaData.titulo,
      module_name: aulaData.modulo,
      chapter_name: aulaData.capitulo,
      chapters: aulaData.capitulos,
      topics: aulaData.topicos,
      extra_metadata: {
        id_externo: aulaData.id,
        link: aulaData.link
      },
      total_questions: 5,
      auto_save: true
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Falha na API: ${JSON.stringify(error)}`);
  }

  const result = await response.json();
  console.log(`✅ Sucesso! Total salvo: ${result.total_saved}`);
  return result;
}

// Exemplo de uso:
enviarTranscricaoAula(3, {
  titulo: 'Aula 04 - Criando Anúncios de Vídeo',
  modulo: 'Módulo 02 - Criativos',
  capitulo: 'Parte 1',
  topicos: ['Roteiro de VSL', 'Ganchos', 'Chamada para Ação'],
  transcricao: 'Texto completo transcrito do vídeo da aula 4...'
});
```

---

### 5.2 Exemplo em Python (`requests`)

```python
import requests

API_URL = "http://localhost:8002" # ou https://backendagente.aryaraj.shop
API_KEY = "ag_live_sua_chave_de_api"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def enviar_aula(kb_id: int, aula: dict):
    payload = {
        "text": aula["transcricao"],
        "video_title": aula["titulo"],
        "module_name": aula["modulo"],
        "chapter_name": aula.get("capitulo"),
        "chapters": aula.get("capitulos", []),
        "topics": aula.get("topicos", []),
        "extra_metadata": aula.get("metadados_extras", {}),
        "total_questions": 5,
        "auto_save": True
    }
    
    response = requests.post(
        f"{API_URL}/knowledge-bases/{kb_id}/generate-qa-and-chunks",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Sucesso: {data['qa_count']} P&R e {data['chunks_count']} trechos adicionados!")
        return data
    else:
        print(f"Erro {response.status_code}: {response.text}")
        return None

# Exemplo de chamada:
enviar_aula(
    kb_id=3,
    aula={
        "titulo": "Aula 05 - Públicos Personalizados",
        "modulo": "Módulo 03 - Segmentação",
        "topicos": ["Lookalike", "Público de Envolvimento", "Lista de Clientes"],
        "transcricao": "Nesta aula vamos aprender a subir listas de clientes no Facebook..."
    }
)
```

---

## ⚠️ 6. Tratamento de Erros e Códigos HTTP

| Código | Significado | Causa mais comum |
| :---: | :--- | :--- |
| `200 OK` | Sucesso | Requisição processada com êxito |
| `400 Bad Request` | Dados inválidos | O texto da transcrição está vazio ou JSON mal formatado |
| `403 Forbidden` | Autenticação Inválida | O header `X-API-Key` está ausente, incorreto ou revogado |
| `404 Not Found` | Não Encontrado | O `kb_id` informado não existe no banco de dados |
| `500 Server Error` | Erro interno | Falha inesperada durante a chamada ou falha de conexão com a OpenAI |
| `502 Bad Gateway` | Erro de Embedding | Não foi possível calcular o vetor (verifique sua chave da OpenAI no `.env`) |

---

## 🎯 7. Como o Agente de IA utiliza esses dados no Atendimento

Quando um lead ou aluno envia uma dúvida pelo WhatsApp/chat:
1. O motor **RAG** pesquisa no banco vetorial via similaridade de cosseno usando a pergunta e variações.
2. Ao localizar a resposta, o agente recebe o texto e a coluna `metadata_val`.
3. O robô responde de forma natural e com precisão cirúrgica, citando o **Módulo**, a **Aula** e os **Tópicos** onde o aluno encontra a solução completa.
