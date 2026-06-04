# LigadoAI Terminal Chat - Proposta Oficial de Implementacao

Data da versao: 2026-06-04

Este documento substitui todas as versoes anteriores e consolida a proposta oficial para implementar o LigadoAI Terminal Chat integrado ao OpenTracy.

---

## 1. Decisao tecnica

A proposta procede.

O LigadoAI Terminal Chat deve ser implementado como um cliente fino do OpenTracy. A CLI cuida da experiencia de terminal, configuracao, historico local, resumo, comandos de operador e chamadas HTTP. O OpenTracy continua responsavel por agente, roteamento de modelo, DeepSeek, traces, canal API, CorpusStore e execucao de MCP Tools.

Decisoes principais:

- Usar o backend HTTP do OpenTracy, nao chamar `uv run python -m runtime` por turno.
- Usar `POST /v1/api/<agent_id>/chat` para conversa.
- Nao implementar `mcp_manager.py` no terminal. MCP e registrado por agente e executado pelo runtime.
- Comecar a Fase 1 com agente e token ja provisionados, com validacao forte.
- Implementar bootstrap automatico apenas na Fase 2.
- Na Fase 1, achatar resumo + historico recente dentro de `request`, porque o `history` enviado ao OpenTracy ainda nao entra no prompt do LLM.
- Tratar escrita em arquivos como fase posterior, sempre com confirmacao e backup.
- Estimar tamanho de contexto por caracteres (nao tokens). Decisao deliberada: sem dependencia de `tiktoken`. Razao e limites documentados na secao de memoria.
- Padronizar formato de erro das MCP tools com schema estruturado. Todas as tools devem retornar o mesmo envelope de erro. Definido na secao de MCP Tools.

---

## 2. Escopo

### 2.1 Incluido

- CLI interativa em Python.
- Interface Rich.
- Cliente HTTP para OpenTracy.
- Configuracao via `config.toml`, incluindo secao `[mcp]`.
- Token do canal API em arquivo seguro, nunca no `config.toml`.
- Historico local JSONL.
- Resumo por sessao com estimativa de tamanho por caracteres.
- Comandos de terminal.
- Logs JSONL.
- Modo mock.
- Bootstrap de validacao na Fase 1.
- Bootstrap automatico de agente/token/MCP na Fase 2.
- MCP servers read-only para arquivos e busca na Fase 3, com formato de erro padronizado.
- Conversao e ingest de documentos na Fase 4, com contratos de falha parcial definidos.

### 2.2 Fora do escopo inicial

- Substituir o runtime do OpenTracy.
- Executar ferramentas locais diretamente pela CLI por decisao do modelo.
- Gerenciar subprocessos MCP dentro do terminal.
- Escrita de arquivos na Fase 1.
- Integracao WhatsApp, painel web ou multiusuario.
- Ferramentas industriais complexas antes da base do terminal estar estavel.

---

## 3. Contratos reais do OpenTracy

### 3.1 Servicos

| Servico | URL padrao | Observacao |
|---|---|---|
| Runtime | `http://localhost:8001` | FastAPI, possui `/health`, `/run`, `/api/<agent_id>/chat` |
| Backend | `http://localhost:8002` | Hono gateway, possui `/health`, `/v1/*` |
| UI | `http://localhost:5174` | Opcional para configuracao visual |

Subida padrao no OpenTracy:

```bash
cd /home/hiatus/Projetos/ligadotattoo/OpenTracy
make up
```

### 3.2 Chat publico

Endpoint oficial da CLI:

```http
POST /v1/api/<agent_id>/chat
Authorization: Bearer <agent_api_token>
Content-Type: application/json
```

Payload suportado hoje:

```json
{
  "request": "...",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "channel": "terminal"
}
```

Resposta suportada hoje:

```json
{
  "response": "...",
  "trace_id": "...",
  "duration_ms": 1234.5,
  "success": true,
  "error": null
}
```

Importante:

- `session_id` nao existe no contrato publico atual.
- `tool_calls` nao vem na resposta.
- O timeout do backend para esse canal e 30s.
- Em OSS local, se `BACKEND_API_KEYS` estiver configurado, `/v1/api/*` pode conflitar com o Bearer token do agente. Ver a secao de patches de compatibilidade.

### 3.3 Agentes

Endpoints relevantes:

```http
GET  /v1/agents
POST /v1/agents
GET  /v1/agents/<id>
POST /v1/agents/<id>/activate
GET  /v1/agents/<id>/channels/api
POST /v1/agents/<id>/channels/api/connect
POST /v1/agents/<id>/channels/api/rotate
DELETE /v1/agents/<id>/channels/api
GET  /v1/agents/<id>/mcp
POST /v1/agents/<id>/mcp
GET  /v1/agents/<id>/mcp/tools
GET  /v1/agents/<id>/secrets
PUT  /v1/agents/<id>/secrets
```

### 3.4 DeepSeek

O OpenTracy ja suporta modelos `deepseek-*` no `prompt_strategies/direct`.

Modelos da CLI:

- `deepseek-chat`: modelo padrao.
- `deepseek-reasoner`: modelo de raciocinio/escalacao.

Segredo:

- O provider `deepseek` existe em `runtime/agents/secrets.py`.
- O endpoint `PUT /v1/agents/<id>/secrets` ainda nao aceita campo `deepseek`.
- Ate o patch ser aplicado, usar `DEEPSEEK_API_KEY` no `.env` global do OpenTracy ou gravar o secret por outro mecanismo controlado.

### 3.5 MCP

O runtime le `agents/<id>/mcp.json`, descobre ferramentas com `list_tools_for_agent()` e executa tool calls dentro do `generate`.

Portanto:

- A CLI nao deve manter processo MCP vivo.
- A CLI pode fornecer os MCP servers como modulos executaveis.
- O OpenTracy registra esses servers via `/v1/agents/<id>/mcp`.
- O runtime inicia os servidores `stdio` quando descobre/chama ferramentas.

---

## 4. Lacunas atuais do OpenTracy

Estas lacunas nao impedem um MVP, mas devem ser registradas antes da implementacao.

### 4.1 `history` nao entra no prompt do LLM

O executor recebe `history` e o preserva em traces, mas `prompt_strategies/direct` monta a chamada ao modelo usando documentos recuperados + `context.request`. `context.history` nao e enviado como mensagens ao LLM.

Mitigacao Fase 1:

- O terminal monta um `request` enriquecido com resumo + ultimas mensagens + pergunta atual.

Patch recomendado:

- Alterar `prompt_strategies/direct` para enviar `context.history` como mensagens reais ao provedor.

### 4.2 `session_id` ausente no canal API

`session_id` existe em `POST /run`, mas nao em `POST /api/<agent_id>/chat`.

Mitigacao Fase 1:

- Usar sessao local da CLI.
- Logar `trace_id` retornado.

Patch recomendado:

- Adicionar `session_id` em `ApiChatRequest` e repassar para `executor.run(..., session_id=session_id)`.

### 4.3 Secrets nao aceitam `deepseek` via endpoint

`PROVIDERS` conhece `deepseek`, mas `AgentSecretsUpdateRequest` so declara `anthropic` e `openai`.

Mitigacao Fase 1:

- Exigir `DEEPSEEK_API_KEY` no `.env` do OpenTracy.

Patch recomendado:

- Adicionar `deepseek: Optional[str] = None` ao `AgentSecretsUpdateRequest`.

### 4.4 Possivel conflito entre `BACKEND_API_KEYS` e canal API em OSS

Em OSS local, o backend aplica `apiKeyAuth` em `/v1/*`. O canal `/v1/api/<agent_id>/chat` tambem usa `Authorization: Bearer <agent_api_token>`. Se `BACKEND_API_KEYS` estiver definido, o middleware pode rejeitar o token do agente antes do handler do canal API.

Mitigacao Fase 1:

- Rodar dev local sem `BACKEND_API_KEYS`, ou chamar runtime direto apenas em modo tecnico controlado.

Patch recomendado:

- No backend OSS, pular `apiKeyAuth` para `/v1/api/*`, como ja acontece com `tenantAuth` no modo multi-tenant.
- Alternativa: aceitar backend key em header separado, por exemplo `X-Backend-Api-Key`, preservando `Authorization` para o token do agente.

Atencao: este conflito deve ser resolvido antes de qualquer ambiente que nao seja estritamente local. Em staging ou producao com `BACKEND_API_KEYS` definido, a CLI simplesmente nao funcionara sem o patch.

### 4.5 Tool calls nao aparecem na resposta

O generate guarda tool calls em `ctx.state["tool_calls"]`, mas `ApiChatResponse` nao expoe isso.

Mitigacao Fase 1:

- Logar apenas `trace_id`, latencia, sucesso/erro e tamanhos.

Patch recomendado:

- Persistir `tool_calls` em `ExecutionRecord.metadata` e expor em endpoint de trace, nao necessariamente na resposta de chat.

---

## 5. Requisitos de implementacao

### 5.1 Requisitos funcionais

RF-01: A CLI deve iniciar com `uv run python -m app.main`.

RF-02: A CLI deve carregar `config.toml` e aplicar defaults seguros quando campos opcionais estiverem ausentes.

RF-03: A CLI deve validar backend `/health` e runtime `/health` antes do chat.

RF-04: A CLI deve validar que `agent_id` existe no OpenTracy.

RF-05: A CLI deve validar que existe token de canal API local ou orientar como conectar/rotacionar o token.

RF-06: A CLI deve enviar mensagens para `POST /v1/api/<agent_id>/chat`.

RF-07: A CLI deve manter historico local em JSONL por sessao.

RF-08: A CLI deve montar request enriquecido com resumo + ultimas mensagens enquanto o OpenTracy nao usar `history` nativamente.

RF-09: A CLI deve suportar comandos `/ajuda`, `/sair`, `/limpar`, `/memoria`, `/novo`, `/listar`, `/carregar`, `/resumo`, `/status`.

RF-10: A CLI deve ter modo mock sem OpenTracy.

RF-11: A CLI deve logar chamadas e erros em JSONL.

RF-12: A Fase 2 deve criar/validar agente e canal API de forma idempotente.

RF-13: A Fase 3 deve registrar MCP servers read-only via OpenTracy.

RF-14: A Fase 4 deve converter documentos para Markdown e acionar ingest no CorpusStore.

### 5.2 Requisitos nao funcionais

RNF-01: Nenhuma chave deve ser gravada em logs.

RNF-02: Token de canal API deve ficar em arquivo com permissao `0600`.

RNF-03: Timeout padrao do cliente deve ser 30s.

RNF-04: Retentativas devem ocorrer apenas para falhas de conexao e 429, nunca para timeout de geracao ja enviado.

RNF-05: Ferramentas de filesystem devem ser read-only nas primeiras fases.

RNF-06: Caminhos devem ser canonicalizados com `Path.resolve()`.

RNF-07: Symlinks que escapem de diretoria permitida devem ser bloqueados.

RNF-08: Saida de ferramentas deve ter limite de bytes conforme `max_tool_output_bytes`.

RNF-09: O terminal deve funcionar sem UI web.

RNF-10: O projeto deve ser modular o suficiente para testar cliente HTTP, memoria, comandos e safety isoladamente.

RNF-11: Toda MCP tool deve retornar erros usando o schema padronizado definido na secao 12.3. Nunca propagar excecao crua ao modelo.

RNF-12: A estrategia de estimativa de tamanho de contexto deve ser por contagem de caracteres, sem dependencia de tokenizador externo. O limite `max_tokens_before_summary` e tratado como `max_chars_before_summary` internamente. Documentado na secao 9.3.

---

## 6. Estrutura oficial do projeto

```text
opentracy-terminal-chat/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── chat.py
│   ├── config.py
│   ├── opentracy_client.py
│   ├── bootstrap.py
│   ├── memory.py
│   ├── renderer.py
│   ├── command_router.py
│   ├── auth.py
│   └── logger.py
├── ligadoai_tools/
│   ├── __init__.py
│   ├── filesystem_server.py
│   ├── search_server.py
│   ├── document_server.py
│   ├── knowledge.py
│   └── safety.py
├── knowledge/
├── knowledge_md/
├── conversations/
├── memory/
├── logs/
├── tests/
├── config.toml
├── pyproject.toml
└── README.md
```

Removido da proposta:

- `app/mcp_manager.py`

Motivo: o lifecycle MCP e responsabilidade do runtime do OpenTracy.

---

## 7. Configuracao

Arquivo `config.toml`:

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
# Limite de tamanho de contexto expresso em caracteres, nao em tokens.
# Decisao deliberada: sem dependencia de tiktoken ou outro tokenizador.
# Razao de conversao assumida: ~4 chars por token (conservador para portugues tecnico).
# Portanto max_tokens_before_summary = 4000 equivale a ~16000 chars.
# O campo e tratado internamente como max_chars_before_summary = max_tokens_before_summary * 4.
max_tokens_before_summary = 4000
summary_max_chars = 2500
flatten_history_into_request = true

[security]
allowed_read_dirs = ["~/LigadoAI"]
allowed_write_dirs = []
max_file_size = 10485760
max_tool_output_bytes = 65536
block_secrets = true

[mcp]
# Configuracoes aplicadas a todos os MCP servers registrados via OpenTracy.
# O runtime do OpenTracy e responsavel por iniciar e encerrar os processos stdio.
# Estes valores sao usados pelo bootstrap (Fase 2) ao montar o payload de registro.
tool_timeout_seconds = 30
max_restarts_per_server = 3
restart_backoff_seconds = 5
log_tool_errors = true

[knowledge]
source_dir = "knowledge"
output_dir = "knowledge_md"
chunk_size = 512
overlap = 50
ingest_target = "../OpenTracy/corpora/indexed"

[ui]
theme = "dark"
show_timestamp = true
show_trace_id = true
show_cost = false
```

Regras obrigatorias:

- Nao salvar `api_token` em `config.toml`. O arquivo pode ser versionado com seguranca se essa regra for respeitada.
- O campo `api_token_file` aponta para o caminho do arquivo de token, nunca para o valor do token.
- Os valores de `[mcp]` sao passados como parametros ao registrar servidores via `/v1/agents/<id>/mcp`. Nao controlam diretamente o runtime.

---

## 8. Fluxo de execucao da Fase 1

### 8.1 Pre-condicoes

- OpenTracy instalado.
- Runtime e backend rodando.
- Agente `ligadoai-terminal` criado ou `_default` explicitamente configurado para uso.
- Canal API conectado e token salvo em `~/.ligadoai/api_token`.
- `DEEPSEEK_API_KEY` configurado no `.env` do OpenTracy ou secret por agente configurado manualmente.

### 8.2 Inicializacao

1. Carregar config.
2. Carregar token.
3. Validar `GET <backend_url>/health`.
4. Validar `GET <runtime_url>/health`.
5. Validar agente com `GET /v1/agents`.
6. Validar canal API com `GET /v1/agents/<id>/channels/api` quando permitido.
7. Abrir sessao local.
8. Entrar no loop interativo.

### 8.3 Turno de chat

1. Ler input do usuario.
2. Se input iniciar com `/`, executar comando local.
3. Salvar mensagem do usuario no JSONL local.
4. Carregar resumo da sessao.
5. Carregar ultimas N mensagens.
6. Montar request enriquecido.
7. Enviar para `POST /v1/api/<agent_id>/chat`.
8. Renderizar Markdown da resposta.
9. Salvar resposta no JSONL local.
10. Logar evento com `trace_id`.

Request enriquecido:

```text
Voce esta em uma conversa tecnica continua.
Use o resumo e as ultimas mensagens apenas como contexto.
Responda a mensagem atual do usuario.

Resumo da sessao:
{summary}

Ultimas mensagens:
{recent_history}

Mensagem atual do usuario:
{user_message}
```

Payload HTTP:

```json
{
  "request": "<request enriquecido>",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "channel": "terminal"
}
```

---

## 9. Memoria

### 9.1 Formatos

Historico:

```text
conversations/<session_id>.jsonl
```

Linha JSONL:

```json
{
  "time": "2026-06-04T12:00:00-03:00",
  "role": "user",
  "content": "...",
  "trace_id": null
}
```

Resumo:

```text
memory/<session_id>_summary.md
```

Indice de sessoes:

```text
conversations/sessions.json
```

### 9.2 Politica de resumo

Gerar resumo quando:

- mais de 10 mensagens novas desde o ultimo resumo; ou
- tamanho estimado do contexto exceder o limite calculado (ver 9.3); ou
- usuario executar `/resumo`.

Prompt de resumo:

```text
Voce resume conversas tecnicas em portugues.
Mantenha assunto principal, decisoes, dados tecnicos, pendencias e proximos passos.
Limite: 3 paragrafos curtos.

Resumo anterior:
{previous_summary}

Novas mensagens:
{messages}

Resumo atualizado:
```

Na Fase 1, o resumo e feito chamando o mesmo endpoint do agente. Em modo mock, gerar resumo deterministico simples para testes.

### 9.3 Estrategia de estimativa de tamanho de contexto

A CLI nao usa tokenizador externo. O tamanho do contexto e estimado por contagem de caracteres.

Razao de conversao assumida: 4 caracteres por token, conservador para portugues tecnico (frases longas, termos compostos, acentuacao).

Formula de calculo:

```python
estimated_tokens = total_chars / 4
```

Limite operacional:

```python
max_chars = config.memory.max_tokens_before_summary * 4
# Ex.: 4000 * 4 = 16000 chars
```

O que e contado no total de caracteres antes de disparar resumo:

- `len(summary)` do resumo anterior.
- `sum(len(msg["content"]) for msg in recent_history)`.
- `len(user_message)` da mensagem atual.

Consequencias conhecidas da aproximacao:

- Ingles e codigo tendem a ter mais tokens por char que o portugues. A estimativa pode disparar o resumo um pouco tarde nesses casos, nunca cedo demais.
- Nao ha risco de erro de contexto excedido no LLM por essa razao, porque o request enriquecido tambem tem `summary_max_chars = 2500` como teto.

Se a precisao de token for necessaria em versao futura, substituir pela funcao `len(encoding.encode(text))` do `tiktoken` sem mudar o restante da logica — o calculo esta isolado em `memory.py`.

---

## 10. Comandos da CLI

| Comando | Fase | Funcao |
|---|---:|---|
| `/ajuda` | 1 | Lista comandos |
| `/sair` | 1 | Encerra |
| `/limpar` | 1 | Limpa tela |
| `/memoria` | 1 | Mostra sessao, arquivo, mensagens e resumo |
| `/resumo` | 1 | Forca resumo |
| `/novo` | 1 | Cria nova sessao local |
| `/listar` | 1 | Lista sessoes |
| `/carregar <id>` | 1 | Carrega sessao |
| `/status` | 1 | Mostra health, agente, token e ultimo trace |
| `/tools` | 3 | Lista MCP Tools descobertas |
| `/indexar` | 4 | Converte e ingere base tecnica |

---

## 11. Bootstrap automatico

O bootstrap automatico entra na Fase 2.

### 11.1 Modo Fase 1

Fase 1 nao cria nem altera agente. Ela apenas valida.

Se faltar agente/token, mostrar erro objetivo:

```text
Agente ligadoai-terminal nao encontrado.
Crie o agente no OpenTracy ou execute a Fase 2 de bootstrap automatico.
```

### 11.2 Modo Fase 2

Fluxo idempotente:

1. `GET /health` backend.
2. `GET /health` runtime.
3. `GET /v1/agents`.
4. Se `ligadoai-terminal` nao existir, `POST /v1/agents`.
5. `POST /v1/agents/ligadoai-terminal/activate`.
6. Validar ou ajustar rota `small=deepseek-chat`.
7. Validar `big=deepseek-reasoner` quando houver endpoint de rota por agente.
8. Validar segredo DeepSeek.
9. `GET /v1/agents/<id>/channels/api`.
10. Se desconectado, `POST /v1/agents/<id>/channels/api/connect`.
11. Salvar token em `~/.ligadoai/api_token` com permissao `0600`.
12. Registrar MCP servers read-only quando Fase 3 estiver ativa, usando os valores de `[mcp]` do `config.toml` no payload de registro.
13. Descobrir tools com `GET /v1/agents/<id>/mcp/tools`.

Payload sugerido para criacao do agente:

```json
{
  "name": "ligadoai-terminal",
  "model": "deepseek-chat",
  "prompt": "Voce e um assistente tecnico da Ligado IoT para manutencao, diagnostico, documentacao e analise industrial. Responda em portugues, seja objetivo e cite limites quando nao tiver dados suficientes.",
  "tools": [],
  "channels": ["api"]
}
```

---

## 12. MCP Tools

### 12.1 Regra de arquitetura

MCP servers ficam no projeto do terminal, mas sao registrados no OpenTracy. O runtime abre os processos e executa as chamadas. A CLI nao mantem processos MCP vivos.

### 12.2 Configuracao de servidores via `[mcp]`

Os valores definidos em `[mcp]` no `config.toml` sao usados pelo bootstrap ao montar o payload de registro de cada servidor via `POST /v1/agents/<id>/mcp`. Nao sao parametros diretos do runtime — sao metadados de configuracao que o OpenTracy pode usar para gerenciar reinicializacoes e timeouts.

Uso no bootstrap:

```python
mcp_payload = {
    "name": server_name,
    "transport": "stdio",
    "command": "uv",
    "args": [...],
    "env": {...},
    "enabled": True,
    "description": "...",
    "timeout_seconds": config.mcp.tool_timeout_seconds,
    "max_restarts": config.mcp.max_restarts_per_server,
    "restart_backoff_seconds": config.mcp.restart_backoff_seconds,
}
```

### 12.3 Schema padronizado de erro para MCP tools

Todas as tools dos servidores `ligadoai_fs`, `ligadoai_search` e futuros servidores devem retornar erros usando este schema. Nunca propagar excecao crua ao modelo.

Schema de erro:

```json
{
  "error": {
    "code": "<codigo_snake_case>",
    "message": "<descricao legivel em portugues>",
    "recoverable": true,
    "detail": "<informacao adicional opcional, sem segredos>"
  }
}
```

Codigos de erro obrigatorios:

| Codigo | Significado | `recoverable` |
|---|---|---|
| `path_not_allowed` | Caminho fora de `allowed_read_dirs` | false |
| `path_traversal` | Tentativa de path traversal detectada | false |
| `symlink_escape` | Symlink aponta para fora da area permitida | false |
| `secret_file_blocked` | Arquivo bloqueado por conter segredo | false |
| `file_too_large` | Arquivo excede `max_file_size` | false |
| `output_truncated` | Saida excedeu `max_tool_output_bytes`, retornado parcialmente | true |
| `file_not_found` | Arquivo ou diretorio nao encontrado | true |
| `permission_denied` | Sem permissao de leitura no OS | false |
| `conversion_partial` | Conversor extraiu parte do documento (Fase 4) | true |
| `conversion_failed` | Conversor nao conseguiu processar o arquivo (Fase 4) | false |

Exemplo de retorno correto de erro em Python:

```python
def _error(code: str, message: str, recoverable: bool, detail: str = "") -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
            "detail": detail,
        }
    }

# Uso:
return _error("path_not_allowed", "Caminho fora da area autorizada.", False, str(resolved_path.parent))
```

O modelo recebe o campo `error.message` como parte da resposta da tool e pode decidir como reagir com base em `error.recoverable`. A CLI loga o evento completo com `code` e `detail`.

### 12.4 Fase 3: ferramentas read-only

Servidor `ligadoai_fs`:

- `read_file`
- `list_directory`
- `file_info`

Servidor `ligadoai_search`:

- `search_files`
- `grep`

Registro exemplo com parametros de `[mcp]`:

```json
{
  "name": "ligadoai_fs",
  "transport": "stdio",
  "command": "uv",
  "args": ["run", "python", "-m", "ligadoai_tools.filesystem_server"],
  "env": {
    "LIGADOAI_ALLOWED_READ_DIRS": "/home/hiatus/LigadoAI",
    "LIGADOAI_MAX_FILE_SIZE": "10485760"
  },
  "enabled": true,
  "description": "Ferramentas read-only para arquivos autorizados.",
  "timeout_seconds": 30,
  "max_restarts": 3,
  "restart_backoff_seconds": 5
}
```

### 12.5 Fase 4: conversores de documentos

Os conversores para `.pdf`, `.docx` e `.xlsx` devem usar os codigos `conversion_partial` e `conversion_failed` do schema de erro. Casos de borda conhecidos que podem retornar `conversion_partial`:

- PDFs com paginas de imagem sem texto extraivel (OCR nao e feito automaticamente na Fase 4).
- XLSXs com celulas mescladas que alteram o layout da tabela.
- DOCXs com tabelas aninhadas que serao achatadas na conversao para Markdown.

Em todos esses casos a tool retorna o conteudo extraido ate onde for possivel, com `recoverable: true` e `detail` indicando o que foi ignorado.

### 12.6 Fase 5: escrita controlada

So adicionar apos a Fase 4 estar estavel:

- `write_file`
- `patch_file`
- `create_backup`

Regras:

- confirmacao explicita do usuario;
- diretorio de escrita separado;
- backup antes de escrita;
- limite de tamanho;
- log do diff resumido;
- nunca escrever fora de `allowed_write_dirs`.

---

## 13. Seguranca

### 13.1 Filesystem

Regras obrigatorias:

- Resolver caminho absoluto com `Path.resolve()`.
- Bloquear path traversal.
- Bloquear symlink que escape de `allowed_read_dirs`.
- Bloquear `.env`, `secrets.env`, `secrets.enc.json`, `api.json`, `id_rsa`, `id_ed25519`.
- Limitar leitura por tamanho de arquivo.
- Limitar retorno da tool por bytes.
- Retornar erro usando o schema padronizado da secao 12.3, nunca excecao crua.

### 13.2 Segredos

Nao logar:

- `Authorization`
- `DEEPSEEK_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- conteudo de `.env`
- token `ot_*`

Mascaramento de token em logs e UI:

```text
ot_abc...xyz
```

### 13.3 Logs

Evento de chat:

```json
{
  "time": "2026-06-04T12:00:00-03:00",
  "event": "chat",
  "session_id": "default",
  "trace_id": "trace_...",
  "success": true,
  "duration_ms": 1234.5,
  "input_chars": 1200,
  "output_chars": 800
}
```

Evento de erro HTTP:

```json
{
  "time": "2026-06-04T12:00:00-03:00",
  "event": "error",
  "kind": "http_401",
  "message": "unauthorized",
  "session_id": "default"
}
```

Evento de erro de MCP tool:

```json
{
  "time": "2026-06-04T12:00:00-03:00",
  "event": "tool_error",
  "tool": "read_file",
  "error_code": "path_not_allowed",
  "recoverable": false,
  "session_id": "default",
  "trace_id": "trace_..."
}
```

---

## 14. Base de conhecimento

### 14.1 Conversao

Entrada:

```text
knowledge/
```

Saida:

```text
knowledge_md/
```

Formatos e contratos de falha parcial:

| Formato | Biblioteca | Fase | Falha parcial possivel |
|---|---|---:|---|
| `.md` | nativo | 4 | nao |
| `.txt` | nativo | 4 | nao |
| `.pdf` | PyMuPDF | 4 | sim — paginas de imagem sem texto |
| `.docx` | python-docx | 4 | sim — tabelas aninhadas achatadas |
| `.xlsx` | openpyxl | 4 | sim — celulas mescladas alteradas |

Em todos os casos de falha parcial, o conversor retorna o conteudo extraivel com aviso usando o schema de erro `conversion_partial` (recoverable: true).

### 14.2 Ingest

Usar `corpora.ingest` do OpenTracy:

```bash
cd /home/hiatus/Projetos/ligadotattoo/OpenTracy
uv run python -m corpora.ingest ../opentracy-terminal-chat/knowledge_md --chunk-size 512 --overlap 50
```

### 14.3 Uso no agente

O pipeline com `retrieve -> rerank -> route -> generate` ja existe no OpenTracy. Para a Fase 1, a CLI nao depende de RAG. Para a Fase 4, validar que o agente usado pela CLI esta com retrieve/rerank ativos ou expor `query_knowledge_base` como MCP.

---

## 15. Tratamento de erros

| Situacao | Acao |
|---|---|
| Backend offline | Mostrar comando `make up` e sair |
| Runtime offline | Mostrar comando `make runtime` ou `make up` e sair |
| Agente ausente | Orientar provisionamento ou bootstrap Fase 2 |
| Token ausente | Orientar conectar canal API |
| 401 | Diferenciar token do agente vs backend auth quando possivel |
| 402 | Mostrar limite/quota quando OpenTracy retornar |
| 429 | Aguardar `Retry-After` se existir, senao backoff curto |
| Timeout | Nao repetir automaticamente |
| 502 | Mostrar erro de runtime/backend |
| MCP tool falhou | Runtime retorna tool error ao modelo; CLI loga evento `tool_error` com code e recoverable |
| MCP tool `recoverable: false` | Logar e exibir mensagem de erro ao usuario |
| MCP tool `recoverable: true` | Logar silenciosamente; modelo decide como responder |
| Arquivo bloqueado | Tool retorna schema de erro com code adequado |
| Falha parcial de conversor | Tool retorna conteudo parcial com `conversion_partial` |

---

## 16. Dependencias

Python:

- `rich`
- `httpx`
- `pydantic`
- `tomli` para Python anterior a 3.11, se necessario
- `pytest`
- `pytest-mock`

Fase documentos:

- `pymupdf`
- `python-docx`
- `openpyxl`

Fase MCP:

- SDK MCP usado pelo OpenTracy/runtime ou pacote compativel para servidor stdio.

Nao incluido intencionalmente:

- `tiktoken`: estimativa de contexto e feita por caracteres (ver secao 9.3). Adicionar apenas se precisao de token se tornar requisito.

---

## 17. Testes

### 17.1 Unidade

- `config.py`: defaults, paths, erro de TOML, leitura de `[mcp]`.
- `auth.py`: leitura, escrita 0600, token ausente.
- `memory.py`: JSONL, resumo, sessoes, calculo de tamanho por chars, limites.
- `command_router.py`: parsing de comandos.
- `opentracy_client.py`: 200, 401, 429, 502, timeout.
- `safety.py`: path traversal, symlink escape, segredo bloqueado.
- `ligadoai_tools/*.py`: verificar que toda tool retorna schema de erro padronizado em todos os casos de falha.

### 17.2 Integracao mock

- Chat completo sem OpenTracy.
- Resumo automatico disparado por contagem de mensagens.
- Resumo automatico disparado por tamanho de chars.
- Troca de sessao.
- Logs gerados.
- Erros de tool retornados com schema correto no mock.

### 17.3 Integracao OpenTracy

- Health backend/runtime.
- Validacao de agente.
- Chamada real ao canal API com token.
- Trace id recebido.
- Registro MCP Fase 3 com parametros de `[mcp]`.
- Descoberta de tools Fase 3.
- Path traversal bloqueado em chamada real a tool.
- Ingest Fase 4.

---

## 18. Fases de implementacao

### Fase 0 - Compatibilidade OpenTracy

Nao bloqueia MVP se forem usadas mitigacoes, mas deve ser priorizada. O item 4.4 deve ser resolvido antes de qualquer ambiente nao-local.

- [ ] Adicionar `deepseek` em `AgentSecretsUpdateRequest`.
- [ ] Ajustar backend OSS para nao bloquear `/v1/api/*` quando `BACKEND_API_KEYS` estiver definido, ou separar header de backend auth.
- [ ] Opcional: adicionar `session_id` ao `ApiChatRequest`.
- [ ] Opcional: incluir `context.history` nas mensagens do LLM.
- [ ] Opcional: persistir `tool_calls` em metadata de trace.

### Fase 1 - CLI HTTP funcional

- [ ] Criar `pyproject.toml`.
- [ ] Criar estrutura `app/`.
- [ ] Implementar config com secao `[mcp]`.
- [ ] Implementar auth/token.
- [ ] Implementar cliente HTTP.
- [ ] Implementar renderer Rich.
- [ ] Implementar memoria local com estimativa por chars (secao 9.3).
- [ ] Implementar request enriquecido.
- [ ] Implementar comandos basicos incluindo `/status`.
- [ ] Implementar modo mock.
- [ ] Implementar logs JSONL com evento `tool_error`.
- [ ] Testes unitarios e mock.

Aceite da Fase 1:

- CLI abre, valida OpenTracy, envia mensagem e mostra resposta.
- Historico persiste entre execucoes.
- `/resumo`, `/novo`, `/listar`, `/carregar` funcionam.
- Nenhum segredo aparece em log.
- Estimativa de contexto por chars esta coberta por testes.

### Fase 2 - Bootstrap automatico

- [ ] Validar/listar agentes.
- [ ] Criar agente `ligadoai-terminal` se ausente.
- [ ] Ativar agente.
- [ ] Validar rota DeepSeek.
- [ ] Conectar canal API.
- [ ] Salvar token 0600.
- [ ] Diagnosticar DeepSeek ausente.

Aceite da Fase 2:

- Ambiente novo consegue preparar agente e token sem UI.
- Reexecutar bootstrap nao duplica agente nem quebra token existente.

### Fase 3 - MCP read-only

- [ ] Implementar `safety.py` com todos os codigos de erro do schema (secao 12.3).
- [ ] Implementar `filesystem_server.py` usando schema de erro padronizado.
- [ ] Implementar `search_server.py` usando schema de erro padronizado.
- [ ] Registrar MCP via OpenTracy com parametros de `[mcp]`.
- [ ] Descobrir tools.
- [ ] Testar path traversal e symlink escape com schema de erro correto.
- [ ] Testar que nenhuma tool propaga excecao crua.

Aceite da Fase 3:

- Modelo consegue ler/buscar arquivos permitidos via tool.
- Arquivos fora da area permitida retornam schema de erro com `path_not_allowed`.
- Todos os erros usam schema padronizado; nenhuma excecao crua chega ao modelo.

### Fase 4 - Documentos e CorpusStore

- [ ] Conversor `.pdf` com tratamento de `conversion_partial` para paginas de imagem.
- [ ] Conversor `.docx` com tratamento de `conversion_partial` para tabelas aninhadas.
- [ ] Conversor `.xlsx` com tratamento de `conversion_partial` para celulas mescladas.
- [ ] Comando `/indexar`.
- [ ] Rodar `corpora.ingest`.
- [ ] Validar retrieve/rerank.

Aceite da Fase 4:

- Documentos em `knowledge/` viram Markdown.
- Falhas parciais de conversao retornam conteudo parcial com schema `conversion_partial`.
- Corpus e indexado.
- Agente usa contexto da base tecnica.

### Fase 5 - Escrita controlada e ferramentas avancadas

- [ ] `write_file` com confirmacao.
- [ ] backup automatico.
- [ ] allowed write dirs.
- [ ] logs de diff.
- [ ] ferramentas industriais especificas.

---

## 19. Criterios de pronto para implementar

O documento esta pronto para implementacao quando:

- A arquitetura de cliente fino estiver aceita.
- O escopo da Fase 1 estiver limitado a HTTP + memoria + CLI.
- A estrategia de estimativa de contexto por caracteres estiver aceita (secao 9.3).
- O schema de erro padronizado das MCP tools estiver aceito (secao 12.3).
- Os parametros de `[mcp]` no `config.toml` estiverem aceitos (secao 7).
- O operador aceitar uma das duas opcoes para DeepSeek:
  - `DEEPSEEK_API_KEY` global no `.env` do OpenTracy; ou
  - patch de secrets antes da Fase 1.
- O operador aceitar uma das duas opcoes para auth local:
  - `BACKEND_API_KEYS` desabilitado em dev; ou
  - patch do backend para `/v1/api/*`.
- O agente `ligadoai-terminal` puder ser provisionado manualmente para Fase 1 ou automaticamente na Fase 2.

---

## 20. Proxima acao recomendada

Implementar Fase 0 minima no OpenTracy:

1. `deepseek` em `AgentSecretsUpdateRequest`.
2. bypass/ajuste de auth para `/v1/api/*` em OSS quando `BACKEND_API_KEYS` estiver definido.

Depois implementar a Fase 1 do terminal.

Se for necessario evitar qualquer alteracao no OpenTracy neste momento, a Fase 1 ainda pode iniciar com:

- `DEEPSEEK_API_KEY` no `.env` global do OpenTracy;
- backend sem `BACKEND_API_KEYS` em dev;
- agente/token provisionados manualmente;
- historico achatado no `request`.
