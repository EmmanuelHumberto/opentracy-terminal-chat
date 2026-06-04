# LigadoAI Terminal Chat

CLI interativa para conversar com o [OpenTracy](https://github.com/opentracy) via terminal, usando **DeepSeek** como provedor LLM, com memória persistente, ferramentas MCP read-only e indexação de base de conhecimento técnica.

> **Status do projeto:** Fase 4 implementada (Documentos e CorpusStore)

---

## Proposta

O LigadoAI Terminal Chat é um **cliente fino** do OpenTracy. Ele cuida da experiência de terminal, configuração, histórico local, resumo de sessões, comandos de operador e chamadas HTTP. O OpenTracy continua responsável por:

- Agente e roteamento de modelo
- Chamadas ao DeepSeek (ou outro provedor)
- Traces e telemetria
- Canal API público
- Execução de ferramentas MCP
- CorpusStore (índice vetorial para busca em documentos)

### Arquitetura

```
┌─────────────────────────────────────────────────┐
│             LigadoAI Terminal Chat              │
│  (experiência de terminal, memória local,       │
│   bootstrap, comandos, conversão de docs)       │
└───────────────────────┬─────────────────────────┘
                        │ HTTP (POST /v1/api/<agent_id>/chat)
                        ▼
┌─────────────────────────────────────────────────┐
│               OpenTracy Backend                 │
│  (autenticação, proxy para runtime)             │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│               OpenTracy Runtime                 │
│  (agente, pipeline, LLM, MCP, traces)           │
└─────────────────────────────────────────────────┘
```

### Fluxo de uma mensagem

1. Usuário digita no terminal
2. CLI carrega resumo + histórico recente da sessão local
3. Monta um request enriquecido com contexto
4. Envia para `POST /v1/api/<agent_id>/chat` no backend do OpenTracy
5. OpenTracy processa (retrieve → rerank → route → generate)
6. Modelo pode chamar ferramentas MCP (ler arquivos, buscar, ver data/hora)
7. Resposta é renderizada em Markdown no terminal
8. Histórico e trace_id são salvos localmente

---

## Fases de Implementação

### ✅ Fase 1 - CLI HTTP funcional
- [x] Estrutura do projeto (`app/`, `pyproject.toml`, `config.toml`)
- [x] Configuração via `config.toml` com seção `[mcp]`
- [x] Autenticação com token do canal API (arquivo `0600`)
- [x] Cliente HTTP com tratamento de 401, 402, 429, 502 e timeout
- [x] Interface Rich com Markdown
- [x] Memória local JSONL por sessão
- [x] Request enriquecido (resumo + histórico achatado no prompt)
- [x] Comandos básicos: `/ajuda`, `/sair`, `/limpar`, `/resumo`, `/memoria`, `/novo`, `/listar`, `/carregar`, `/status`
- [x] Modo mock para testes sem OpenTracy
- [x] Logs estruturados em JSONL

### ✅ Fase 2 - Bootstrap automático
- [x] Health check do backend e runtime
- [x] Criação idempotente do agente no OpenTracy
- [x] Ativação do agente
- [x] Ajuste de rota para DeepSeek
- [x] Conexão do canal API e salvamento do token
- [x] Diagnóstico de ausência do `DEEPSEEK_API_KEY`

### ✅ Fase 3 - MCP read-only
- [x] `safety.py` — validação de caminhos, path traversal, symlink escape, bloqueio de secrets
- [x] `filesystem_server.py` — `read_file`, `list_directory`, `file_info`, `get_current_datetime`
- [x] `search_server.py` — `search_files` (glob), `grep` (regex)
- [x] Schema de erro padronizado para todas as tools
- [x] Registro automático dos MCP servers via bootstrap
- [x] Data/hora real injetada no system prompt do agente

### ✅ Fase 4 - Documentos e CorpusStore
- [x] Conversor `.md`/`.txt` — cópia direta
- [x] Conversor `.pdf` — PyMuPDF com `conversion_partial` para páginas sem texto
- [x] Conversor `.docx` — python-docx com `conversion_partial` para tabelas aninhadas
- [x] Conversor `.xlsx` — openpyxl com `conversion_partial` para células mescladas
- [x] Comando `/indexar` — converte e ingere no CorpusStore do OpenTracy
- [x] Log de eventos de indexação

### 📋 Fase 5 - Escrita controlada (próxima)
- [ ] `write_file` com confirmação do usuário
- [ ] Backup automático antes de editar
- [ ] Diretório separado de escrita
- [ ] Log de diffs resumidos

### 📋 Fase 6 - Ferramentas industriais (futuro)
- [ ] Análise de vibração
- [ ] Análise de motor
- [ ] Relatórios técnicos

---

## Requisitos

- **Python** >= 3.11
- **OpenTracy** rodando (`make up` em `/home/hiatus/Projetos/ligadotattoo/OpenTracy`)
- **DeepSeek API Key** configurada no `.env` do OpenTracy
- Dependências Python (ver `pyproject.toml`)

## Instalação

```bash
# Clonar o repositório
cd /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat

# Criar e ativar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependências
pip install rich httpx pydantic pymupdf python-docx openpyxl
```

## Configuração

Edite `config.toml` conforme necessário:

```toml
[opentracy]
backend_url = "http://localhost:8002"
runtime_url = "http://localhost:8001"
agent_id = "ligadoai-terminal"
timeout = 30

[auth]
api_token_file = "~/.ligadoai/api_token"

[model]
provider = "deepseek"
small = "deepseek-chat"
big = "deepseek-reasoner"
temperature = 0.3
max_tokens = 2048

[memory]
max_history = 10
max_tokens_before_summary = 4000
flatten_history_into_request = true

[security]
allowed_read_dirs = ["~/LigadoAI"]
allowed_write_dirs = []
max_file_size = 10485760
max_tool_output_bytes = 65536

[knowledge]
source_dir = "knowledge"
output_dir = "knowledge_md"
chunk_size = 512
overlap = 50
ingest_target = "../OpenTracy/corpora/indexed"
```

> **Importante:** O token do canal API **nunca** deve ficar no `config.toml`. Ele é salvo em `~/.ligadoai/api_token` com permissão `0600`.

## Uso

```bash
# Ativar ambiente
cd /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat
source .venv/bin/activate

# Iniciar chat normal
python3 -m app.main

# Modo mock (sem OpenTracy, para testes)
python3 -m app.main --mock

# Forçar bootstrap automático
python3 -m app.main --bootstrap
```

### Comandos do Chat

| Comando | Fase | Descrição |
|---|---|---|
| `/ajuda` | 1 | Lista todos os comandos disponíveis |
| `/sair` | 1 | Encerra o programa |
| `/limpar` | 1 | Limpa a tela do terminal |
| `/resumo` | 1 | Força atualização do resumo da sessão |
| `/memoria` | 1 | Mostra status da memória local |
| `/novo` | 1 | Inicia uma nova sessão de conversa |
| `/listar` | 1 | Lista sessões anteriores |
| `/carregar <id>` | 1 | Carrega uma sessão anterior pelo ID |
| `/status` | 1 | Mostra status do OpenTracy (backend, runtime, agente, token) |
| `/indexar` | 4 | Converte documentos em `knowledge/` para Markdown e ingere no CorpusStore |

### Indexação de Documentos

1. Coloque os arquivos na pasta `knowledge/`:
   ```bash
   cp ~/Documentos/manual.pdf knowledge/
   cp ~/Documentos/especificacao.docx knowledge/
   ```

2. No chat, execute:
   ```
   /indexar
   ```

3. O sistema:
   - Converte PDF, DOCX, XLSX, MD, TXT para Markdown
   - Extrai texto (com avisos de falha parcial para páginas sem OCR, tabelas aninhadas, células mescladas)
   - Indexa no CorpusStore do OpenTracy para busca semântica

Formatos suportados: `.md`, `.txt`, `.pdf`, `.docx`, `.xlsx`

---

## Estrutura do Projeto

```
opentracy-terminal-chat/
├── app/                    # CLI principal
│   ├── main.py             # Ponto de entrada
│   ├── chat.py             # Loop principal e comandos
│   ├── config.py           # Configuração (config.toml)
│   ├── opentracy_client.py # Cliente HTTP para OpenTracy
│   ├── bootstrap.py        # Bootstrap automático (Fase 2)
│   ├── memory.py           # Gerenciamento de sessões e resumos
│   ├── renderer.py         # Interface Rich (Markdown, tabelas)
│   ├── command_router.py   # Roteador de comandos (/comandos)
│   ├── auth.py             # Leitura/escrita segura de token
│   └── logger.py           # Logs estruturados JSONL
├── ligadoai_tools/         # MCP servers (Fase 3+)
│   ├── filesystem_server.py   # read_file, list_directory, file_info, get_current_datetime
│   ├── search_server.py       # search_files, grep
│   ├── document_server.py     # Conversores PDF/DOCX/XLSX para Markdown (Fase 4)
│   └── safety.py              # Validação de caminhos, schema de erros
├── knowledge/              # Documentos fonte (PDF, DOCX, XLSX, MD, TXT)
├── knowledge_md/           # Documentos convertidos para Markdown (gerado)
├── conversations/          # Histórico JSONL por sessão
├── memory/                 # Resumos de sessão em Markdown
├── logs/                   # Logs estruturados JSONL
├── tests/                  # Testes
├── config.toml             # Configuração
├── pyproject.toml          # Dependências e metadados
└── README.md               # Este arquivo
```

---

## Segurança

- Token do canal API armazenado em arquivo com permissão `0600`
- Nenhuma chave de API aparece em logs
- Path traversal e symlink escape são bloqueados nas tools MCP
- Arquivos de segredo (`.env`, `secrets.env`, `api.json`, chaves privadas) são bloqueados
- Limite de tamanho de arquivo lido e de bytes retornados por tool
- Schema de erro padronizado para todas as MCP tools (nunca propagam exceção crua)

---

## Tecnologias

- **Python** >= 3.11
- **Rich** — interface de terminal com Markdown e tabelas
- **httpx** — cliente HTTP com timeout e retry
- **Pydantic** — validação de configuração
- **PyMuPDF** — extração de texto de PDFs
- **python-docx** — conversão de documentos Word
- **openpyxl** — conversão de planilhas Excel
- **DeepSeek** — provedor LLM (via OpenTracy)
- **OpenTracy** — motor de agente, pipeline, MCP, CorpusStore
