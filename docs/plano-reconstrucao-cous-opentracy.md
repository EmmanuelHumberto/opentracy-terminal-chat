# Plano de Reconstrucao Cous + OpenTracy

Data: 2026-06-08

Este documento consolida a decisao arquitetural discutida para reconstruir o Cous com uma base limpa e evoluir o OpenTracy para receber uma vertical de conhecimento persistente, previsivel e desacoplada.

## 1. Diagnostico

O Cous atual funcionou como laboratorio, mas acumulou responsabilidades demais:

- interface terminal;
- loop de chat;
- comandos;
- conversao de documentos;
- OCR;
- chunking;
- embeddings;
- escrita no PostgreSQL;
- reload de FAISS no OpenTracy;
- memoria local;
- medicao/captura;
- relatorios;
- bootstrap de servicos.

Isso causou sintomas reais:

- `/indexar` travando a maquina;
- modelos de embedding pesados ou invalidos;
- corpus indexado mas nao visivel pelo agente;
- FAISS em memoria perdido apos restart do runtime;
- metadados errados, como `coreless` virando fabricante;
- mistura de schema antigo e schema novo;
- acoplamento entre terminal, banco, embedding e RAG.

A conclusao e: o Cous atual deve ser usado como material de consulta, nao como fundacao da nova arquitetura.

Regra operacional:

```text
O diretorio opentracy-terminal-chat e legado congelado.
Nao corrigir, estender ou adaptar esse codigo como novo Cous.
Usar apenas para inventariar comportamento, comandos, configuracoes e experiencia de uso.
```

## 2. Decisao Principal

O OpenTracy deve ser o dono do conhecimento.

O Cous deve ser cliente fino.

Fluxo alvo:

```text
Usuario
  -> Cous Terminal
    -> OpenTracy API
      -> Knowledge Vertical
        -> Banco
        -> Embeddings
        -> Indice vetorial
        -> RAG
        -> LLM
```

Regra:

```text
Cous inicia a entrada de conhecimento.
OpenTracy processa, valida, persiste, indexa e consulta.
```

O Cous nao deve:

- abrir PostgreSQL;
- carregar SentenceTransformer;
- conhecer FAISS;
- gerar embeddings;
- manipular tabela `chunks`;
- fazer reload manual de corpus;
- decidir schema de conhecimento.

O Cous pode:

- receber comando `/indexar`;
- enviar arquivo, pasta ou caminho para o OpenTracy;
- mostrar progresso;
- listar documentos;
- buscar documentos;
- remover documentos;
- enviar perguntas ao chat;
- renderizar respostas.

## 3. O Que E O OpenTracy

OpenTracy e um runtime/framework para agentes de IA treinaveis.

Componentes principais:

- `runtime/`: servidor FastAPI que executa o agente.
- `agent/`: configuracao, prompt e pipeline do agente.
- `techniques/`: blocos como RAG, reranking, memoria e prompt strategies.
- `corpora/`: acumulador de conhecimento/RAG.
- `traces/`: registro das interacoes.
- `evals/`, `harness/`, `experiments/`: estrutura para avaliar e melhorar o agente.
- `backend/` e `ui/`: gateway, canais e interface web.

No uso do Cous:

```text
Cous = interface terminal
OpenTracy = cerebro/agente/runtime/RAG/ferramentas/traces
LLM = modelo gerador
Banco/corpus = memoria tecnica persistente
```

## 4. Banco No OpenTracy

Um banco no OpenTracy e um avanco, desde que seja implementado como vertical propria.

Beneficios:

- persistencia real do corpus;
- restart do runtime sem perda de conhecimento;
- auditoria de documentos;
- listagem, remocao e reindexacao;
- metadados ricos;
- status de validacao;
- versionamento de corpus;
- busca hibrida;
- reutilizacao por outros clientes alem do Cous.

Banco seria uma decisao ruim se:

- o Cous continuar dono dele;
- o runtime depender de reload manual em memoria;
- schema de conhecimento ficar misturado com medicao/chat;
- nao houver migrations versionadas;
- detalhes de banco vazarem para o RAG ou para o terminal.

## 5. Estado Atual Do OpenTracy

O OpenTracy nao precisa ser reescrito.

Ele ja tem:

- runtime HTTP;
- pipeline de agente;
- RAG;
- reranking;
- prompt strategies;
- traces;
- corpora local;
- embeddings;
- FAISS.

O que precisa ser adicionado:

- vertical `knowledge`;
- repository PostgreSQL;
- migrations;
- contratos HTTP;
- servicos de ingestao;
- busca hibrida;
- versionamento de corpus;
- integracao limpa com o pipeline RAG.

## 6. Problemas Especificos Encontrados

### 6.1 Corpus Em Memoria

Foi criado um endpoint emergencial:

```text
POST /corpus/reload
```

Ele recebe chunks e vetores do Cous e carrega um `CorpusMemoryStore`.

Isso ajudou no curto prazo, mas nao e arquitetura final, porque:

- o runtime reiniciado perde o indice;
- o OpenTracy nao sabe reconstruir sozinho seu corpus;
- o Cous continua responsavel por banco, embedding e reload;
- o payload completo de chunks/vetores pode ficar pesado.

Decisao:

```text
Manter a ideia como aprendizado.
Nao usar CorpusMemoryStore como fonte principal definitiva.
```

### 6.2 Schema Conflitante

Existe um schema antigo no Cous com:

```text
documentos_conhecimento
  id BIGSERIAL
  caminho
  conteudo
  chunk_vetor VECTOR(1536)
```

E existe uma migracao v2 melhor com:

```text
documentos_conhecimento
  id UUID
  fabricante
  modelo
  tipo
  frontmatter JSONB
  conteudo_md
  hash_conteudo

chunks
  chunk_id
  documento_id
  texto
  vetor FLOAT4[]
```

A migracao v2 e melhor conceitualmente, mas ainda esta no Cous e usa `DROP TABLE`.

Decisao:

```text
Usar a migracao v2 como rascunho conceitual.
Criar novo schema versionado dentro do OpenTracy.
Nao reaproveitar DROP TABLE destrutivo.
```

### 6.3 Conversores E OCR

OpenTracy puro hoje ingere principalmente:

```text
.md
.txt
```

O Cous atual possui ferramentas melhores:

```text
.pdf  -> PyMuPDF + OCR
.docx -> python-docx
.xlsx -> openpyxl
.jpg/.png/.bmp/.tiff -> OCR
.zip -> extrai e converte
```

Decisao:

```text
Migrar essas capacidades para adapters limpos na vertical knowledge do OpenTracy.
Nao copiar o codigo como esta.
```

## 7. Arquitetura Alvo

Estrutura proposta:

```text
OpenTracy/
  knowledge/
    __init__.py

    domain/
      document.py
      chunk.py
      corpus_version.py
      metadata.py
      errors.py

    application/
      index_document.py
      index_directory.py
      remove_document.py
      search_knowledge.py
      rebuild_index.py
      get_status.py

    ports/
      document_converter.py
      embedding_provider.py
      knowledge_repository.py
      vector_index.py
      metadata_extractor.py
      content_validator.py
      unit_of_work.py

    infrastructure/
      postgres/
        repository.py
        unit_of_work.py
        migrations/
          001_create_knowledge.sql
          002_create_corpus_versions.sql

      vector/
        faiss_index.py
        pgvector_index.py

      embeddings/
        sentence_transformer_provider.py
        openai_embedding_provider.py

      conversion/
        markdown_converter.py
        text_converter.py
        pdf_converter.py
        image_ocr_converter.py
        docx_converter.py
        xlsx_converter.py
        zip_converter.py

      metadata/
        frontmatter_extractor.py
        heuristic_extractor.py

    api/
      routes.py
      schemas.py

    tests/
      test_chunking.py
      test_metadata.py
      test_index_document.py
      test_search.py
```

Direcao das dependencias:

```text
api -> application -> domain
application -> ports
infrastructure -> ports
```

O dominio nao depende de FastAPI, PostgreSQL, FAISS, SentenceTransformer ou Cous.

## 8. Entidades De Dominio

### KnowledgeDocument

```text
id
source_uri
canonical_path
title
manufacturer
model
category
document_type
content_hash
status
metadata
created_at
updated_at
```

### KnowledgeChunk

```text
id
document_id
chunk_index
text
text_hash
metadata
```

### KnowledgeEmbedding

```text
chunk_id
embedding_model
dimension
vector
created_at
```

### CorpusVersion

```text
id
version
status
document_count
chunk_count
embedding_model
vector_dimension
created_at
```

Separacao obrigatoria:

```text
manufacturer  = Portescap, Faulhaber, Maxon
category      = coreless, brushless, rotary
document_type = manual, datasheet, artigo, laudo, medicao
```

`coreless` nunca deve ser fabricante.

## 9. Schema Recomendado

### knowledge_documents

```sql
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_uri TEXT NOT NULL,
    canonical_path TEXT,
    title TEXT,
    manufacturer TEXT,
    model TEXT,
    category TEXT,
    document_type TEXT,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    error_details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### knowledge_chunks

```sql
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### knowledge_embeddings

```sql
CREATE TABLE knowledge_embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES knowledge_chunks(id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    vector_raw FLOAT4[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Observacao:

```text
Nao usar FLOAT4[] como indice vetorial principal.
```

Motivo:

- modelos diferentes podem gerar 384, 768, 1024 ou 1536 dimensoes;
- uma coluna `VECTOR(384)` amarra o schema ao modelo atual;
- trocar modelo exigiria migration destrutiva ou uma nova coluna/tabela;
- `dimension` em `knowledge_embeddings` e `knowledge_corpus_versions` so faz sentido se o schema aceitar dimensoes variaveis.
- `FLOAT4[]` sozinho perde busca vetorial nativa, ANN eficiente e otimizacoes do pgvector.

Decisao:

```text
Usar `knowledge_embeddings.vector_raw FLOAT4[]` como armazenamento bruto/portavel.
Usar pgvector/FAISS como indice derivado versionado para busca real.
```

Indices derivados possiveis:

```text
knowledge_embeddings.vector_raw -> FAISS por corpus_version/modelo
knowledge_embeddings.vector_raw -> pgvector materializado por corpus_version/modelo
```

Se pgvector for usado, criar tabelas/indices versionados por modelo ou dimensao:

```text
knowledge_vector_index_all_minilm_l6_v2 VECTOR(384)
knowledge_vector_index_bge_base VECTOR(768)
```

Ou por versao de corpus:

```text
knowledge_vector_index_v42 VECTOR(384)
knowledge_vector_index_v43 VECTOR(768)
```

Assim o banco continua flexivel e o indice fica versionado.

### knowledge_corpus_versions

```sql
CREATE TABLE knowledge_corpus_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version BIGSERIAL UNIQUE,
    status TEXT NOT NULL,
    document_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    embedding_model TEXT NOT NULL,
    vector_dimension INTEGER NOT NULL,
    chunking_strategy TEXT NOT NULL,
    ranking_strategy TEXT NOT NULL,
    prompt_version TEXT,
    converter_version TEXT,
    ocr_profile TEXT,
    schema_version TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Recomendacao:

```text
Usar FLOAT4[] como armazenamento bruto inicial.
Usar pgvector como indice materializado principal quando disponivel.
Versionar estrategia de chunking, ranking, prompt, conversao e OCR.
```

## 10. Contratos HTTP

API minima:

```text
POST   /knowledge/index
GET    /knowledge/jobs/{id}
POST   /knowledge/jobs/{id}/cancel
GET    /knowledge/status
GET    /knowledge/documents
GET    /knowledge/documents/{id}
DELETE /knowledge/documents/{id}
POST   /knowledge/search
POST   /knowledge/rebuild-index
POST   /chat
GET    /health
```

Autenticacao:

```text
Todas as rotas de escrita e leitura sensivel devem exigir autenticacao.
```

Para ambiente local/interno, o minimo aceitavel:

```text
Authorization: Bearer <OPENTRACY_KNOWLEDGE_TOKEN>
```

Opcoes futuras:

- mTLS entre Cous e OpenTracy;
- token por cliente;
- escopos como `knowledge:read`, `knowledge:write`, `chat:send`;
- allowlist de origem para uso local.

Mesmo em rede local, a base de conhecimento nao deve ficar aberta sem token.

### POST /knowledge/index

Request:

```json
{
  "source_uri": "/path/to/file.pdf",
  "content_type": "application/pdf",
  "metadata": {
    "manufacturer": "Faulhaber",
    "model": "2616",
    "category": "brushless",
    "document_type": "datasheet"
  },
  "options": {
    "force": false
  }
}
```

Response inicial:

```json
{
  "job_id": "uuid",
  "document_id": "uuid",
  "status": "processing",
  "message": "Documento recebido para indexacao."
}
```

O endpoint nao deve bloquear ate converter, chunkar, embeddar e persistir. Ele agenda um job e retorna rapido.

### GET /knowledge/jobs/{id}

Response em processamento:

```json
{
  "job_id": "uuid",
  "status": "processing",
  "stage": "embedding",
  "progress": {
    "current": 8,
    "total": 18
  }
}
```

Response concluida:

```json
{
  "job_id": "uuid",
  "document_id": "uuid",
  "status": "indexed",
  "chunks": 18,
  "content_hash": "sha256...",
  "corpus_version": 42
}
```

Response com falha:

```json
{
  "job_id": "uuid",
  "document_id": "uuid",
  "status": "failed",
  "error": {
    "code": "ocr_failed",
    "message": "OCR nao extraiu texto suficiente."
  }
}
```

### POST /knowledge/search

Request:

```json
{
  "query": "motor brushless Faulhaber 2616",
  "top_k": 8,
  "filters": {
    "manufacturer": "Faulhaber"
  }
}
```

Response:

```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "score": 0.87,
      "text": "...",
      "source_uri": "...",
      "metadata": {
        "manufacturer": "Faulhaber",
        "model": "2616"
      }
    }
  ]
}
```

## 11. Fluxo De Indexacao

```text
POST /knowledge/index
  -> CreateKnowledgeJobUseCase
    -> KnowledgeJobRepository
    -> KnowledgeQueue
    -> retorna job_id/status=processing
```

Processamento em background:

```text
KnowledgeIndexWorker
  -> IndexDocumentUseCase
    -> DocumentConverter
    -> ContentValidator
    -> MetadataExtractor
    -> Chunker
    -> EmbeddingProvider
    -> KnowledgeRepository
    -> VectorIndex
    -> CorpusVersionService
```

Passos:

1. Receber documento, caminho ou upload.
2. Registrar job/documento como `processing`.
3. Retornar `job_id` imediatamente.
4. Worker converte para texto/Markdown.
5. Validar qualidade minima.
6. Extrair metadados.
7. Calcular hash do conteudo.
8. Se o hash ja existe e `force=false`, marcar job como `skipped`.
9. Dividir em chunks.
10. Gerar embeddings.
11. Persistir documento, chunks e embeddings.
12. Atualizar indice vetorial derivado.
13. Criar nova versao de corpus.
14. Marcar documento como `indexed`.
15. Cliente consulta `GET /knowledge/jobs/{id}` ate concluir.

Em caso de erro:

```text
status = failed
error_details = {...}
```

Essa decisao evita repetir o problema do `/indexar` travando. PDFs grandes, imagens com OCR e ZIPs devem sempre rodar via job/polling.

### Mecanismo De Fila

Fase inicial:

```text
FastAPI BackgroundTasks apenas para prototipo local e arquivos pequenos.
```

Fase recomendada para uso real:

```text
arq + Redis
```

Motivos:

- combina bem com Python async;
- e mais simples que Celery para este caso;
- permite retries, timeout, concorrencia controlada e jobs separados;
- evita prender CPU/OCR dentro do processo HTTP.

Alternativas aceitaveis:

```text
RQ
Dramatiq
Celery
Redis Streams
RabbitMQ
```

Regra:

```text
O mecanismo de fila deve implementar a porta `KnowledgeQueue`.
```

Assim a aplicacao nao fica acoplada a Redis, Celery ou BackgroundTasks.

### Estados Do Job

```text
queued
running
processing
indexed
skipped
failed
cancel_requested
cancelled
duplicate
```

### Politica De Concorrencia E Duplicidade

Chave de idempotencia:

```text
source_uri + content_hash + embedding_model + chunking_strategy
```

Regras:

- se um job identico ja estiver `queued`, `running` ou `processing`, retornar o `job_id` existente com status `duplicate`;
- se o documento ja estiver indexado e `force=false`, retornar `skipped`;
- se `force=true`, criar novo job e nova `corpus_version`;
- jobs para o mesmo `source_uri` devem usar lock por documento;
- o ultimo job concluido nao deve apagar resultado de outro job mais novo;
- cancelamento deve ser cooperativo: o worker consulta `cancel_requested` entre etapas.

### Delecao Logica

`DELETE /knowledge/documents/{id}` deve ser soft delete por padrao.

Estados de documento:

```text
processing
indexed
failed
deleted
superseded
```

Regras:

- `DELETE` marca `status=deleted`;
- chunks e embeddings podem permanecer para auditoria, mas saem da busca;
- hard delete deve existir apenas como operacao administrativa explicita;
- toda delecao cria nova `corpus_version`;
- traces antigos continuam reproduziveis porque o documento ainda pode ser auditado.

## 12. Contratos Internos

### DocumentConverter

```python
class DocumentConverter:
    async def convert(self, source) -> ConvertedDocument:
        ...
```

### EmbeddingProvider

```python
class EmbeddingProvider:
    @property
    def model_name(self) -> str:
        ...

    @property
    def dimension(self) -> int:
        ...

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...
```

Politica de embedding:

```text
Default local inicial: sentence-transformers/all-MiniLM-L6-v2
Dimensao esperada: 384
Modo: carregamento lazy no OpenTracy, nunca no Cous
```

Motivo:

- e leve o suficiente para uso local;
- ja foi validado na experiencia do Cous;
- evita modelos de 400MB+ como default;
- reduz risco de travar a maquina no terminal.

Fallback:

```text
Se o provider local falhar, o job deve falhar de forma explicita.
Nao trocar automaticamente para outro modelo sem registrar nova corpus_version.
```

Troca automatica de provider muda o espaco vetorial e pode misturar embeddings incompativeis. Se houver fallback para OpenAI ou outro provider, ele deve gerar uma nova versao de corpus com `embedding_model` e `dimension` diferentes.

### KnowledgeRepository

```python
class KnowledgeRepository:
    async def upsert_document(self, document):
        ...

    async def replace_chunks(self, document_id, chunks, embeddings):
        ...

    async def get_document(self, document_id):
        ...

    async def list_documents(self, filters):
        ...

    async def delete_document(self, document_id):
        ...
```

### VectorIndex

```python
class VectorIndex:
    async def upsert_embeddings(self, embeddings):
        ...

    async def delete_document(self, document_id):
        ...

    async def search(self, query_vector, top_k, filters=None):
        ...

    async def rebuild(self):
        ...
```

### KnowledgeSearchPort

```python
class KnowledgeSearchPort:
    async def search(self, query: str, top_k: int, filters=None):
        ...
```

O RAG deve depender desse contrato, nao de PostgreSQL diretamente.

## 13. Conversao E OCR

Conversores planejados:

```text
MarkdownConverter
TextConverter
PdfConverter
ImageOcrConverter
DocxConverter
XlsxConverter
ZipConverter
```

Resultado padrao:

```text
ConversionResult
  success
  text
  source_uri
  detected_format
  warnings
  errors
  ocr_used
  ocr_confidence
  pages
```

Dependencias Python:

```text
pymupdf
pytesseract
Pillow
python-docx
openpyxl
```

Dependencias de sistema:

```text
tesseract-ocr
tesseract-ocr-por
tesseract-ocr-eng
```

Ordem recomendada:

1. `.md`
2. `.txt`
3. `.pdf`
4. imagens com OCR
5. `.docx`
6. `.xlsx`
7. `.zip`

Politica operacional de OCR:

```text
OCR deve rodar em worker dedicado ou fila separada.
```

Motivos:

- OCR e lento;
- consome CPU;
- pode processar paginas/imagens em lote;
- pode bloquear outros jobs se compartilhar a mesma fila;
- precisa de timeouts e limites por arquivo.

Filas recomendadas:

```text
knowledge_index_queue
knowledge_ocr_queue
knowledge_rebuild_queue
```

Limites iniciais:

```text
ocr_max_concurrency = 1 ou 2 em maquina local
ocr_page_timeout_seconds = 60
ocr_max_pages_without_text_warning = configuravel
```

PDFs escaneados e ZIPs com muitas imagens devem ser classificados como jobs de alto custo.

## 14. Politica De Chunking

Default inicial:

```text
Estrutura primeiro, tamanho depois.
```

Estrategia:

1. Preservar secoes de Markdown quando possivel.
2. Quebrar por blocos semanticos: titulo, subtitulo, tabela, paragrafo.
3. Aplicar janela deslizante somente quando o bloco exceder o limite.
4. Manter overlap moderado entre chunks longos.
5. Guardar metadados de pagina/secao/tabela no chunk.

Configuracao inicial:

```text
chunk_size_tokens = 450
overlap_tokens = 80
min_chunk_chars = 120
max_chunk_tokens = 700
```

Parametros por `document_type`:

```text
datasheet:
  chunk_size_tokens = 450
  overlap_tokens = 100
  preservar_tabelas = true

manual:
  chunk_size_tokens = 600
  overlap_tokens = 80

laudo:
  chunk_size_tokens = 500
  overlap_tokens = 60

medicao:
  chunk_size_tokens = 400
  overlap_tokens = 40
```

Regra importante:

```text
Tabelas tecnicas nao devem ser cortadas no meio quando possivel.
```

Datasheets dependem muito de tabelas. Se a tabela for grande, ela deve virar chunks por linhas/grupos com cabecalho repetido.

## 15. Busca Hibrida

A busca deve combinar:

```text
semantic_score
+ lexical_score
+ metadata_boost
+ source/title/model boost
```

Exemplo:

```text
query = "Portescap 16DCT"
```

O ranking deve favorecer:

- chunks semanticamente proximos;
- texto contendo `16DCT`;
- metadata `manufacturer=Portescap`;
- titulo/source contendo `16DCT`;
- documentos aprovados e da versao atual do corpus.

Isso evita o problema de o embedding ignorar codigos curtos de modelos.

Formula inicial de referencia:

```text
final_score =
  (0.60 * semantic_score_normalized)
+ (0.25 * lexical_score_normalized)
+ (0.10 * metadata_score)
+ (0.05 * source_score)
```

Pesos configuraveis:

```text
semantic_weight = 0.60
lexical_weight = 0.25
metadata_weight = 0.10
source_weight = 0.05
```

Definicoes:

```text
semantic_score_normalized = similaridade vetorial normalizada entre 0 e 1
lexical_score_normalized = BM25 simples ou contagem ponderada normalizada
metadata_score = match exato/parcial em manufacturer/model/category/document_type
source_score = match em title/source_uri/canonical_path
```

Boosts recomendados:

```text
modelo exato no texto ou metadata: +0.20
fabricante exato: +0.12
document_type filtrado explicitamente: +0.08
termo presente no titulo/source: +0.08
```

Essa formula deve ser testada com golden tests e registrada nos traces para permitir ajuste reprodutivel.

Importante:

```text
Os pesos nao sao arquitetura fixa.
Eles pertencem a uma `ranking_strategy` versionada.
```

Exemplo:

```json
{
  "name": "hybrid_v1",
  "semantic_weight": 0.60,
  "lexical_weight": 0.25,
  "metadata_weight": 0.10,
  "source_weight": 0.05,
  "boosts": {
    "exact_model": 0.20,
    "exact_manufacturer": 0.12,
    "filtered_document_type": 0.08,
    "term_in_source": 0.08
  }
}
```

Quando os pesos mudarem, criar nova `ranking_strategy` e registrar isso em `knowledge_corpus_versions` e nos traces.

Benchmarks obrigatorios antes de estabilizar uma estrategia:

- queries por fabricante;
- queries por modelo curto;
- queries com erro de digitacao;
- queries comparativas;
- queries sem documento relevante.

## 16. Integracao Com RAG

O RAG do OpenTracy deve trocar o acesso direto ao store por uma interface:

```text
RAG -> KnowledgeSearchPort -> Search Implementation
```

Implementacoes possiveis:

```text
PgVectorKnowledgeSearch
FaissKnowledgeSearch
HybridKnowledgeSearch
```

O prompt deve receber contexto com metadados:

```text
[1] Fonte: ...
fabricante=...
modelo=...
tipo=...
conteudo...
```

O reranker nao deve zerar todos os documentos. Se filtrar tudo, deve manter fallback com os melhores hits iniciais.

## 17. Reconstrucao Do Indice Apos Restart

ADR-002 define que o banco e a fonte da verdade e o indice e estado derivado. A politica operacional deve ser explicita:

```text
Startup nao deve fazer rebuild completo sincrono.
```

Fluxo recomendado:

1. Runtime sobe rapidamente.
2. Knowledge vertical le a ultima `corpus_version` valida.
3. Se existir snapshot FAISS compativel, carrega em background.
4. Se nao existir snapshot, agenda `rebuild-index` em background.
5. Enquanto o indice nao estiver pronto, busca usa fallback por pgvector/lexical se disponivel.
6. `GET /knowledge/status` informa `index_status`.

Estados:

```text
index_status = ready | loading | rebuilding | stale | unavailable
```

Endpoint:

```text
POST /knowledge/rebuild-index
```

Esse endpoint deve criar job, nao bloquear ate terminar.

Resposta:

```json
{
  "job_id": "uuid",
  "status": "processing",
  "kind": "rebuild-index"
}
```

Regra:

```text
RAG nunca deve depender de reload manual feito pelo Cous.
```

## 18. Novo Cous

O novo repositorio local do Cous deve ser criado do zero. O legado em `opentracy-terminal-chat` deve ser tratado como referencia de produto, nao como base de codigo.

O Cous novo deve ter arquitetura simples:

```text
Cous/
  cli/
    terminal.py
    command_router.py
    renderer.py

  clients/
    opentracy_client.py
    knowledge_client.py

  application/
    session_service.py
    chat_service.py

  config.py
  main.py
```

Responsabilidade do novo Cous:

```text
Terminal fino + UX + sessao local + cliente HTTP autenticado.
```

Responsabilidades proibidas no novo Cous:

```text
PostgreSQL direto.
Embeddings.
SentenceTransformer.
FAISS.
OCR.
Conversao de PDF/DOCX/XLSX/ZIP.
Chunking.
Schema de conhecimento.
Reload manual de corpus.
```

Essas capacidades devem morar no OpenTracy, atras dos contratos da vertical `knowledge`.

### 18.1 Inventario Do Legado Que Deve Ser Preservado Como UX

Parametros de inicializacao observados no legado:

```text
--mock
--bootstrap
--no-runtime
--config <arquivo.toml>
```

Decisao para o novo Cous:

```text
Manter os parametros equivalentes quando fizerem sentido.
--mock deve usar clientes fake.
--bootstrap deve configurar autenticacao/canal no OpenTracy.
--no-runtime deve apenas impedir auto-start local.
--config deve carregar configuracao externa tipada.
```

Comandos de terminal a preservar ou redesenhar:

```text
/indexar <arquivo|pasta>
/indexados
/buscar <consulta>
/remover <document_id>
/status
/tools
/novo
/carregar
/listar
/resumo
/memoria
/limpar
/sair
```

Comandos tecnicos do fluxo de medicao herdados como requisitos de produto, mas nao como implementacao direta:

```text
/capturar [porta]
/medicoes
/medicao <id>
/laudo <id>
```

Esses comandos nao devem acessar PostgreSQL direto no novo Cous. Quando forem reconstruidos, devem chamar APIs do OpenTracy ou outra vertical propria de medicoes.

Comportamento de input a preservar:

```text
Mensagem sem "/" -> chat com o agente.
Mensagem com "/" -> dispatch de comando local.
Comando desconhecido -> erro claro e sugestao de /ajuda.
Entrada vazia -> ignora.
Ctrl-C ou EOF no prompt -> equivale a /sair.
```

Comportamento visual a preservar como experiencia, nao como codigo:

```text
Prompt "▸".
Painel de boas-vindas.
Ajuda com atalhos principais.
Status de backend/runtime/token/agente.
Indicador de pensamento durante chamada ao agente.
Renderizacao clara de erros, avisos, sucesso e trace_id.
Listagem tabular de sessoes/documentos.
```

### 18.2 Autenticacao Cous -> OpenTracy

A autenticacao deve nascer no novo Cous, nao ser remendada no legado.

Contrato minimo:

```text
Authorization: Bearer <token>
```

Regras:

```text
Todo request do novo Cous para OpenTracy deve carregar Authorization.
O token deve ser obtido no bootstrap ou configurado por arquivo/env.
O token deve ser salvo fora do config.toml, com permissao 0600 em POSIX.
Nenhum endpoint sensivel de knowledge deve aceitar request sem token.
Falha 401 deve renderizar mensagem clara: token ausente, invalido ou expirado.
Falha 403 deve renderizar mensagem clara: token valido sem permissao para a acao.
```

Configuracao proposta:

```toml
[opentracy]
backend_url = "http://localhost:8002"
runtime_url = "http://localhost:8001"
agent_id = "cous"
timeout = 30

[auth]
token_file = "~/.cous/opentracy_token"
```

Portas de cliente:

```text
OpenTracyClient
  chat(request, history)
  health()
  status()

KnowledgeClient
  index(path_or_upload, metadata, options) -> job_id
  get_job(job_id)
  list_documents()
  search(query, filters)
  delete_document(document_id)
```

Ambos usam o mesmo provedor de token.

### 18.3 Fluxo De Indexacao No Novo Cous

Cada comando chama API do OpenTracy.

Exemplo:

```text
/indexar knowledge/motores/faulhaber-2616.pdf
```

Internamente:

```text
Cous -> POST /knowledge/index
```

Fluxo completo:

```text
1. Cous valida apenas se o caminho existe e e legivel.
2. Cous envia o arquivo/caminho ao OpenTracy com Authorization.
3. OpenTracy cria job e responde imediatamente com job_id.
4. Cous faz polling em GET /knowledge/jobs/{job_id}.
5. Cous mostra progresso sem bloquear o terminal.
6. OpenTracy faz conversao, OCR, chunking, embedding e persistencia.
7. Cous apenas exibe sucesso, erro ou status final.
```

O novo Cous nao deve fazer `dry-run` local de validacao sem contrato do OpenTracy. Se existir dry-run, deve ser:

```text
POST /knowledge/index com options.dry_run = true
```

## 19. Documentacao Necessaria

Criar no OpenTracy:

```text
docs/knowledge/architecture.md
docs/knowledge/api.md
docs/knowledge/schema.md
docs/knowledge/indexing-flow.md
docs/knowledge/retrieval.md
docs/knowledge/metadata.md
docs/knowledge/operations.md
docs/knowledge/auth.md
docs/knowledge/jobs.md
```

Conteudo minimo:

- responsabilidades da vertical;
- contratos HTTP;
- schema do banco;
- exemplos de requests/responses;
- fluxo de indexacao;
- politica de metadados;
- politica de OCR;
- politica de autenticacao;
- modelo de jobs/polling;
- como reindexar;
- como debugar busca;
- garantias e limitacoes.

## 20. ADRs Recomendados

### ADR-001: OpenTracy Owns The Knowledge Corpus

Decisao:

```text
O corpus tecnico pertence ao OpenTracy.
Clientes externos, incluindo Cous, nao acessam o banco diretamente.
Todo acesso ocorre via API versionada.
```

Consequencias:

- OpenTracy e fonte unica da verdade para conhecimento.
- Cous fica leve e substituivel.
- RAG sobrevive a restart.
- Busca e indexacao podem ser testadas isoladamente.

### ADR-002: Vector Index Is Derived State

Decisao:

```text
O banco e a fonte da verdade.
FAISS/pgvector sao indices derivados e versionados.
```

Consequencias:

- indice pode ser reconstruido;
- versionamento de corpus fica possivel;
- falhas de indice nao apagam conhecimento.
- pgvector deve ser usado como indice materializado principal quando disponivel;
- `FLOAT4[]` e armazenamento bruto, nao mecanismo principal de busca.

### ADR-003: Metadata Fields Are Typed

Decisao:

```text
manufacturer, model, category e document_type sao campos distintos.
```

Consequencias:

- `coreless` nao vira fabricante;
- filtros ficam confiaveis;
- busca hibrida melhora.

### ADR-004: Indexing Is Job-Based

Decisao:

```text
Indexacao, OCR, ZIP e rebuild de indice rodam como jobs.
Endpoints de escrita retornam rapido com `job_id`.
```

Consequencias:

- cliente nao trava em arquivos grandes;
- progresso pode ser exibido pelo Cous;
- falhas ficam auditaveis;
- operacoes longas podem ser retomadas ou reexecutadas.

### ADR-005: Queue Backend Is A Port

Decisao:

```text
Jobs usam a porta `KnowledgeQueue`.
BackgroundTasks e permitido apenas no prototipo local.
Uso real deve migrar para arq + Redis ou alternativa equivalente.
```

Consequencias:

- fila pode evoluir sem alterar casos de uso;
- OCR pode ter worker dedicado;
- timeouts, retries e concorrencia ficam configuraveis.

### ADR-006: Documents Use Soft Delete

Decisao:

```text
DELETE /knowledge/documents/{id} marca documento como `deleted`.
Hard delete e operacao administrativa explicita.
```

Consequencias:

- auditoria preservada;
- traces antigos continuam reproduziveis;
- delecao remove documento da busca sem apagar historico tecnico.

### ADR-007: Ranking Strategy Is Versioned

Decisao:

```text
Pesos de busca hibrida pertencem a uma `ranking_strategy` versionada.
```

Consequencias:

- benchmarks podem comparar estrategias;
- traces indicam com qual ranking a resposta foi gerada;
- ajustes de peso nao viram mudanca invisivel de comportamento.

### ADR-008: Knowledge Vertical Must Remain Isolated

Decisao:

```text
`knowledge/` e uma vertical isolada.
RAG, agent, traces, evals e chat acessam conhecimento por contratos.
```

Consequencias:

- OpenTracy nao vira um novo monolito acoplado;
- knowledge pode ser testado isoladamente;
- Cous e outros clientes continuam substituiveis.

## 21. Testes

Unitarios:

```text
chunker
metadata extractor
frontmatter parser
validator
embedding provider fake
repository contract
search ranking
converters
OCR quality handling
```

Integracao:

```text
indexa markdown
indexa PDF
indexa imagem com OCR
busca por fabricante
busca por modelo
remove documento
rebuild index
runtime reinicia e corpus continua disponivel
job de indexacao muda de processing para indexed
job de rebuild nao bloqueia startup
```

Golden tests:

```text
"Me fale do motor Faulhaber 2616"
"Quais documentos tenho sobre Portescap 16DCT?"
"Compare Portescap e Maxon"
"Liste documentos sobre coreless"
```

## 22. Plano De Implementacao

### Fase 1: Fundacao

- Criar `knowledge/`.
- Criar entidades de dominio.
- Criar portas.
- Criar DTOs/schemas.
- Criar migrations iniciais.
- Documentar contratos.

### Fase 2: Persistencia

- Implementar repository PostgreSQL.
- Implementar unit of work.
- Implementar soft delete.
- Implementar `knowledge_corpus_versions` com estrategias versionadas.
- Criar testes de repository.
- Criar endpoint `GET /knowledge/status`.

### Fase 3: Indexacao Basica

- Implementar conversor `.md`.
- Implementar conversor `.txt`.
- Implementar validator.
- Implementar chunker.
- Implementar embedding provider.
- Implementar `POST /knowledge/index` com retorno imediato de `job_id`.
- Implementar `GET /knowledge/jobs/{id}`.
- Implementar worker simples de indexacao.
- Implementar porta `KnowledgeQueue`.
- Usar `BackgroundTasks` apenas como backend inicial simples.
- Congelar novas features no Cous legado assim que esse fluxo estiver funcional.

### Fase 4: Busca

- Implementar `POST /knowledge/search`.
- Implementar busca via pgvector materializado quando disponivel.
- Manter FAISS como indice derivado alternativo.
- Adicionar busca lexical.
- Adicionar boost por metadata.
- Versionar `ranking_strategy`.
- Integrar com o RAG via `KnowledgeSearchPort`.

### Fase 5: Conversores Avancados

- Migrar PDF com PyMuPDF.
- Adicionar OCR para PDF escaneado.
- Adicionar OCR de imagens.
- Separar worker/fila de OCR.
- Adicionar DOCX.
- Adicionar XLSX.
- Adicionar ZIP.

### Fase 6: Cous Novo

- Criar novo repositorio local para o Cous fino.
- Usar `opentracy-terminal-chat` somente como consulta de UX e contratos existentes.
- Implementar cliente HTTP autenticado com `Authorization: Bearer <token>`.
- Implementar provedor de token com arquivo 0600 e suporte a env/config.
- Implementar `/indexar`, `/indexados`, `/buscar`, `/remover`, `/status`.
- Implementar polling de jobs para `/indexar`.
- Preservar parametros uteis: `--mock`, `--bootstrap`, `--no-runtime`, `--config`.
- Remover dependencia direta de banco/embedding/FAISS.
- Proibir OCR, conversao, chunking e embeddings no cliente.

### Fase 7: Hardening

- Versionar corpus.
- Rebuild assincro robusto.
- Logs estruturados.
- Metricas.
- Traces com `document_id`, `chunk_id`, `corpus_version`.
- Testes de regressao.

### Fase 8: Medicoes, Serial E Laudos Tecnicos

Esta fase e obrigatoria para reconstruir o Cous completo. Ela nao pertence a
`knowledge/`: e uma vertical propria de operacao tecnica.

Objetivo:

```text
Capturar medicoes reais do analisador via serial, associar a um cabecalho
tecnico completo, validar snapshots, persistir a sessao no OpenTracy e gerar
laudos consultaveis pelo agente.
```

Responsabilidades do Cous novo:

- Exibir formulario de cabecalho da medicao.
- Coletar inputs do operador com defaults e validacao basica.
- Chamar OpenTracy por HTTP autenticado.
- Mostrar progresso da captura.
- Mostrar resumo da sessao, snapshots validos/rejeitados e erros.
- Comandos previstos:
  - `/capturar [porta]`
  - `/medicoes`
  - `/medicao <id>`
  - `/laudo <id>`
  - `/parametros`
  - `/parametro <fabricante> <modelo>`

Responsabilidades do OpenTracy:

- Ser dono da vertical `measurements/`.
- Controlar sessoes de medicao.
- Ler serial ou coordenar worker local de captura.
- Validar snapshots `TMA_DATA`.
- Persistir sessoes, snapshots, diagnosticos e parametros ideais.
- Calcular estatisticas e diagnostico tecnico.
- Gerar laudo estruturado.
- Expor contratos HTTP estaveis para o Cous.
- Opcionalmente publicar sessoes/laudos aprovados na vertical `knowledge/`.

Campos minimos do cabecalho:

```text
fabricante
modelo
numero_serie
tipo_maquina
tipo_motor
sistema_transmissao
curso_nominal_mm
curso_min_mm
curso_max_mm
tipo_coleta        # desempenho, reparo, pos-reparo, homologacao, bancada
peca_substituida
observacoes
tecnico
porta_serial
baudrate
duracao_seg
verticais          # hall, power, vibration, course, etc.
```

Snapshots esperados do analisador:

```text
prefixo serial: TMA_DATA <json>
tipos: hall, power, vibration, course
campos comuns: timestamp_us, type, valores numericos por vertical
```

Contratos HTTP previstos:

```http
POST /measurements/sessions
POST /measurements/sessions/{id}/capture
GET  /measurements/sessions
GET  /measurements/sessions/{id}
GET  /measurements/sessions/{id}/snapshots
POST /measurements/sessions/{id}/diagnose
POST /measurements/sessions/{id}/report
GET  /measurements/parameters
PUT  /measurements/parameters/{id}
```

Entidades:

```text
MeasurementSession
MeasurementHeader
MeasurementSnapshot
MeasurementStats
MeasurementDiagnostic
IdealParameterProfile
TechnicalReport
```

Portas:

```text
SerialCapturePort
MeasurementRepository
SnapshotValidator
MeasurementAnalyzer
ReportRenderer
MeasurementQueue
```

Regras de arquitetura:

- Cous nao acessa serial diretamente se a captura for responsabilidade do OpenTracy.
- Se a serial precisar rodar no terminal por permissao/localidade, Cous atua como
  adapter local e envia snapshots para OpenTracy; a regra de negocio continua no
  OpenTracy.
- Banco de medicoes fica no OpenTracy, nao no Cous.
- Laudo aprovado pode virar documento em `knowledge/`, mas medicao bruta nao deve
  ser misturada com chunks de RAG sem curadoria.
- Falha de captura nao pode apagar cabecalho; o operador deve poder repetir a
  medicao preservando dados.
- Snapshots invalidos devem ser armazenados ou contabilizados com motivo, sem
  contaminar estatisticas aprovadas.

Migracao a partir do legado:

- Usar apenas como referencia:
  - `app/captura_serial.py`
  - `app/formulario_coleta.py`
  - `app/repositorio_medicoes.py`
  - `app/laudo_tecnico.py`
  - comandos `/capturar`, `/medicoes`, `/medicao`, `/laudo`
- Nao copiar acoplamento direto do Cous com banco.
- Recriar contratos e dominio com objetos pequenos, testes e portas claras.

Status inicial implementado:

```text
OpenTracy:
- measurements/domain com MeasurementHeader, MeasurementSession e MeasurementSnapshot
- validador basico de snapshots TMA_DATA
- analisador basico de sessao
- renderizador Markdown de laudo
- repositório em memoria para contratos e testes
- endpoints /measurements/sessions
- endpoints /measurements/sessions/{id}/snapshots
- endpoints /measurements/sessions/{id}/diagnose
- endpoints /measurements/sessions/{id}/report

Cous novo:
- cliente HTTP MeasurementsClient
- /medicoes
- /medicao <id>
- /laudo <id>
- /capturar reservado ate ligar SerialCapturePort
```

Proximo passo da Fase 8:

```text
Implementar PostgresMeasurementRepository e migrations.
Depois implementar SerialCapturePort local com leitura TMA_DATA.
```

## 23. Regras De Qualidade

- Modulos pequenos e com responsabilidade unica.
- Dominio sem dependencia de framework.
- Application orquestra casos de uso, nao faz I/O direto.
- Infrastructure implementa ports.
- Verticais acessam knowledge por contratos, nao por import direto de repositorio.
- API valida request/response.
- Nenhum acesso direto do Cous ao banco.
- Nenhum modelo pesado carregado no terminal.
- Nenhum reload manual obrigatorio para o RAG funcionar.
- Nenhuma indexacao longa bloqueando request HTTP.
- Toda rota sensivel protegida por token ou mecanismo equivalente.
- Nenhum `DROP TABLE` em migration operacional.
- Nenhum schema duplicado entre Cous e OpenTracy.

## 24. Resumo Executivo

Decisao final:

```text
Reescrever OpenTracy: nao.
Adicionar vertical knowledge no OpenTracy: sim.
Reescrever Cous como cliente fino: sim.
Migrar ferramentas de conversao/OCR do Cous para OpenTracy: sim, com adapters limpos.
Banco no OpenTracy: sim.
Banco no Cous: nao.
```

O Cous atual deve continuar como referencia de experiencia e regras reais. A nova base deve nascer com contratos claros, vertical de conhecimento isolada e OpenTracy como fonte unica da verdade para o corpus tecnico.
