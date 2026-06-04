# LigadoAI Terminal Chat - Critica e Melhorias

Data da analise: 2026-06-04

## Resumo executivo

A proposta em `LigadoAI_Terminal_Chat.md` e viavel, mas esta mais ambiciosa do que o primeiro ciclo precisa e tem alguns desalinhamentos com o contrato real do OpenTracy atual.

O melhor caminho e tratar o LigadoAI Terminal como um cliente fino: ele deve cuidar da experiencia de terminal, memoria local, configuracao, bootstrap e chamadas HTTP. O OpenTracy deve continuar responsavel por agente, modelo, rota, traces, canal API e ciclo de vida MCP.

Os principais ajustes necessarios sao:

- Usar o endpoint publico real do backend: `POST /v1/api/<agent_id>/chat`.
- Fazer bootstrap explicito de agente, token, rota DeepSeek e MCP antes do chat.
- Nao gerenciar subprocessos MCP dentro do terminal; registrar MCP no agente e deixar o runtime abrir os servidores.
- Corrigir a estrategia de historico, porque o `generate` atual recebe `history`, mas nao usa esse historico no prompt do LLM.
- Corrigir a configuracao de segredo DeepSeek por agente, porque o endpoint de secrets atualmente expõe `anthropic` e `openai`, mas nao aceita `deepseek` no modelo de request.
- Alinhar timeouts: o backend do canal API usa 30s hoje; o documento fala em 60s.

## Evidencias encontradas no projeto

Arquivos revisados:

- `opentracy-terminal-chat/docs/LigadoAI_Terminal_Chat.md`
- `opentracy-terminal-chat/tracy_chat.py`
- `OpenTracy/README.md`
- `OpenTracy/agent/agent.yaml`
- `OpenTracy/agent/pipeline/route.yaml`
- `OpenTracy/agent/pipeline/generate.yaml`
- `OpenTracy/agents/registry.json`
- `OpenTracy/agents/_default/pipeline/route.yaml`
- `OpenTracy/backend/channels/api/handler.ts`
- `OpenTracy/backend/channels/agents/handler.ts`
- `OpenTracy/runtime/server.py`
- `OpenTracy/runtime/agents/registry.py`
- `OpenTracy/runtime/agents/secrets.py`
- `OpenTracy/runtime/agents/mcp.py`
- `OpenTracy/runtime/mcp/client.py`
- `OpenTracy/techniques/prompt_strategies/impl.py`
- `OpenTracy/techniques/memory/impl.py`
- `OpenTracy/corpora/ingest.py`
- `OpenTracy/corpora/store.py`

## Viabilidade

### O que ja esta bem encaminhado

A ideia de uma CLI separada do core do OpenTracy e correta. O proprio OpenTracy ja separa runtime, backend, agente, traces, corpora e canais. Manter o terminal fora de `OpenTracy/` reduz risco de quebrar o motor.

O uso do backend HTTP tambem e correto. O backend expoe `POST /v1/api/<agent_id>/chat`, que encaminha para o runtime em `POST /api/<agent_id>/chat`. Esse caminho ja autentica com Bearer token e roda o agente correto.

DeepSeek tambem esta suportado na camada de geracao. `OpenTracy/techniques/prompt_strategies/impl.py` identifica modelos `deepseek-*` e usa o SDK OpenAI com `base_url` padrao `https://api.deepseek.com`.

MCP tambem ja existe no runtime. A configuracao vive em `agents/<id>/mcp.json`, e `runtime/mcp/client.py` descobre ferramentas e executa tool calls durante o `generate`.

### O que ainda impede uma implementacao limpa

O MVP atual `tracy_chat.py` chama:

```bash
uv run python -m runtime --quiet <prompt>
```

Isso funciona como prova de conceito, mas recompila/roda o runtime por turno e nao usa o canal API, token, traces por sessao, multiagente nem MCP por agente da forma pretendida.

O documento assume `session_id` no endpoint publico, mas o contrato atual do canal API aceita `request`, `history` e `channel`; `session_id` existe em `POST /run`, nao em `POST /api/<agent_id>/chat`.

O documento tambem assume que enviar `history` basta para continuidade. Hoje o executor coloca `history` em `Context`, mas a tecnica `prompt_strategies/direct` monta a chamada ao LLM somente com documentos recuperados e `context.request`. Ou seja: o historico e persistido em trace, mas nao entra no prompt do modelo nessa variante.

## Critica ao documento atual

### 1. Arquitetura correta, mas com duplicacao de responsabilidades

O documento diz que as ferramentas devem ser MCP Tools registradas no OpenTracy, mas ao mesmo tempo propoe `app/mcp_manager.py` para gerenciar subprocessos MCP.

Esse ponto deve ser simplificado. Se as ferramentas sao registradas no OpenTracy, o terminal nao deve manter o ciclo de vida dos subprocessos. O runtime ja faz isso ao ler `agents/<id>/mcp.json`.

Recomendacao:

- Remover `app/mcp_manager.py` do caminho critico.
- Manter MCP servers no projeto do terminal, por exemplo `ligadoai_tools/filesystem_server.py`.
- Registrar esses servers via `POST /v1/agents/<id>/mcp`.
- Deixar o OpenTracy iniciar, descobrir e chamar ferramentas.

### 2. Bootstrap do agente esta subespecificado

O documento diz "Criacao automatica na inicializacao do terminal", mas nao define o fluxo exato.

O OpenTracy atual tem registry multiagente. A CLI deve:

1. Verificar se backend e runtime estao ativos.
2. Listar agentes com `GET /v1/agents`.
3. Procurar `ligadoai-terminal`.
4. Criar com `POST /v1/agents` se nao existir.
5. Ativar com `POST /v1/agents/<id>/activate`.
6. Configurar rota para `deepseek-chat` e `deepseek-reasoner`.
7. Configurar segredo DeepSeek ou validar fallback em `.env`.
8. Conectar canal API com `POST /v1/agents/<id>/channels/api/connect` ou reutilizar token local.
9. Registrar MCP servers.
10. Descobrir ferramentas com `GET /v1/agents/<id>/mcp/tools`.

Sem esse bootstrap, a CLI pode conversar com o agente errado.

### 3. Divergencia entre `agent/` e `agents/_default/`

Foi encontrado:

- `OpenTracy/agent/pipeline/route.yaml` usa `deepseek-chat` e `deepseek-reasoner`.
- `OpenTracy/agents/_default/pipeline/route.yaml` ainda usa modelos Claude.
- `OpenTracy/agents/registry.json` aponta `_default` como ativo.

Isso e relevante porque o canal API opera por `agent_id`. Ao chamar `ligadoai-terminal`, esse agente precisa existir em `OpenTracy/agents/`. Ao chamar `_default`, a rota pode nao ser a rota DeepSeek esperada dependendo de ativacao/copia entre `agents/<id>` e `agent/`.

Recomendacao:

- Criar um agente dedicado `ligadoai-terminal`.
- Nao depender implicitamente de `_default`.
- Na inicializacao, validar a rota efetiva e falhar com mensagem clara se o modelo ativo nao for DeepSeek.

### 4. Configuracao DeepSeek por agente tem lacuna

`runtime.agents.secrets.PROVIDERS` conhece `deepseek`, mas `AgentSecretsUpdateRequest` em `runtime/server.py` atualmente declara apenas:

```python
anthropic: Optional[str] = None
openai: Optional[str] = None
```

Assim, o endpoint `PUT /v1/agents/<id>/secrets` nao e suficiente para gravar `DEEPSEEK_API_KEY` por agente sem ajuste no OpenTracy. O funcionamento atual pode depender do `.env` global.

Recomendacao:

- Curto prazo: documentar que `DEEPSEEK_API_KEY` deve estar no `.env` do OpenTracy.
- Melhor caminho: corrigir o OpenTracy para aceitar `deepseek: Optional[str]` no request de secrets.
- A CLI deve checar `GET /v1/agents/<id>/secrets` e orientar o usuario quando DeepSeek estiver ausente.

### 5. Historico e memoria precisam ser tratados no prompt

O documento define memoria local e envio de `history`. Isso nao e suficiente no estado atual do runtime.

A tecnica `memory` e no-op, e `prompt_strategies/direct` nao inclui `context.history` nas mensagens do LLM. O MVP `tracy_chat.py` contorna isso ao achatar o historico dentro do proprio prompt enviado como `request`.

Recomendacao para a Fase 1:

- Manter historico local JSONL.
- Enviar ao OpenTracy um `request` ja enriquecido com resumo + ultimas mensagens + pergunta atual.
- Continuar enviando `history` para traces, mas nao depender dele para memoria sem patch no OpenTracy.

Recomendacao estrutural:

- Ajustar `prompt_strategies/direct` para montar mensagens reais com `context.history`:
  - `system`: prompt do agente.
  - mensagens anteriores: `context.history`.
  - mensagem atual: `context.request` com contexto RAG quando houver.

### 6. `session_id` nao esta no canal API publico

O documento propoe:

```json
{"request": "...", "history": [...], "session_id": "..."}
```

Mas `ApiChatRequest` do runtime nao inclui `session_id`. O campo existe em `RunRequest`, usado por `POST /run`.

Recomendacao:

- Para a CLI via backend, nao prometer `session_id` ate o contrato ser estendido.
- Usar o `trace_id` retornado como correlacao minima.
- Se agrupamento por sessao for requisito, adicionar `session_id` ao `ApiChatRequest` e repassar para `executor.run(..., session_id=session_id)`.

### 7. Timeout e budget estao desalinhados

O documento propoe `timeout = 60` e budget `max_latency_ms: 60000`.

Hoje o backend do canal API usa `TIMEOUT_MS = 30_000`. Se o terminal esperar 60s, a chamada pode ser encerrada pelo backend antes.

Tambem nao ha evidencia de que `budget.max_latency_ms` e `budget.max_cost_usd` interrompam execucao no executor atual; eles aparecem como configuracao do agente, mas o executor nao aplica esses limites no caminho de chat.

Recomendacao:

- Configurar o terminal com timeout padrao de 30s para o canal API atual.
- Se precisar de 60s, ajustar o backend.
- Tratar budget como metadado ate haver enforcement real.

### 8. Base de conhecimento esta correta, mas a fase esta tarde

O documento propoe usar CorpusStore, o que esta alinhado com OpenTracy. O ingest atual aceita `.md` e `.txt`, cria chunks, embeddings e salva em `corpora/indexed/`.

Porem a Fase 5 fala em RAG, enquanto o objetivo inicial inclui base tecnica e documentos. Se essa base for uma promessa central do terminal, ela deve entrar antes.

Recomendacao:

- Fase 1: chat sem RAG.
- Fase 2: filesystem/search MCP read-only.
- Fase 3: conversao de documentos para `.md`.
- Fase 4: ingest em `OpenTracy/corpora/indexed`.
- Fase 5: ativar/validar retrieve/rerank ou expor `query_knowledge_base` como MCP.

### 9. Segurança deve viver nos MCP servers

O documento lista boas regras de seguranca, mas precisa deixar claro onde elas serao aplicadas.

Como o modelo chama ferramentas via OpenTracy, a seguranca precisa estar dentro dos MCP servers e na configuracao registrada no agente. Nao basta validar no terminal, porque o terminal nao esta no caminho da chamada de ferramenta.

Recomendacao:

- Comecar com ferramentas read-only.
- Adiar `write_file` para uma fase posterior.
- Canonicalizar paths com `Path.resolve()`.
- Bloquear symlinks que escapem de `allowed_dir`.
- Limitar bytes retornados por tool.
- Redigir segredos (`API_KEY`, `TOKEN`, `.env`, `secrets.env`, `api.json`) nos outputs.
- Registrar logs sem conteudo integral de arquivos sensiveis.
- Separar `allowed_read_dirs` e `allowed_write_dirs`.

### 10. Logs prometem informacao que a resposta nao entrega

O documento fala em logar `tool_call`, mas o endpoint publico retorna basicamente `response`, `trace_id`, `duration_ms`, `success` e `error`.

As tool calls sao colocadas em `ctx.state["tool_calls"]`, mas nao aparecem claramente no `ApiChatResponse`. Portanto o terminal nao tem como logar tool calls de forma confiavel apenas com a resposta do chat.

Recomendacao:

- Logar no terminal: timestamp, session local, request id local, `trace_id`, latencia, sucesso/erro e tamanho de entrada/saida.
- Para tool calls, buscar detalhes por trace se o endpoint expuser essa informacao.
- Alternativamente, ajustar o OpenTracy para persistir `tool_calls` em `ExecutionRecord.metadata`.

## Arquitetura recomendada revisada

```text
opentracy-terminal-chat/
├── app/
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
│   ├── filesystem_server.py
│   ├── search_server.py
│   ├── document_server.py
│   └── safety.py
├── knowledge/
├── knowledge_md/
├── conversations/
├── memory/
├── logs/
├── config.toml
├── pyproject.toml
└── README.md
```

Mudancas em relacao ao documento original:

- `mcp_manager.py` sai do caminho critico.
- Entra `bootstrap.py` para preparar OpenTracy.
- MCP servers permanecem como executaveis locais, mas o lifecycle e do runtime.
- `knowledge.py` pode existir, mas como comando de conversao/ingest, nao como substituto do CorpusStore.

## Configuracao recomendada

```toml
[opentracy]
backend_url = "http://localhost:8002"
runtime_url = "http://localhost:8001"
agent_id = "ligadoai-terminal"
timeout = 30

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
block_secrets = true

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

Observacao: nao manter `api_token` aberto em `config.toml`. Preferir `~/.ligadoai/api_token` com permissao `0600`.

## Fluxo de bootstrap recomendado

1. `GET /health` no backend ou runtime.
2. `GET /v1/agents`.
3. Se `ligadoai-terminal` nao existir, `POST /v1/agents` com:

```json
{
  "name": "ligadoai-terminal",
  "model": "deepseek-chat",
  "prompt": "Voce e um assistente tecnico da Ligado IoT...",
  "tools": [],
  "channels": ["api"]
}
```

4. `POST /v1/agents/ligadoai-terminal/activate`.
5. Ajustar rota para small/big DeepSeek. Criacao de agente atual troca `small`, mas pode manter `big` herdado do seed.
6. Validar segredo DeepSeek.
7. `POST /v1/agents/ligadoai-terminal/channels/api/connect` se nao houver token local.
8. Registrar MCP servers:

```json
{
  "name": "ligadoai_fs",
  "transport": "stdio",
  "command": "uv",
  "args": ["run", "python", "-m", "ligadoai_tools.filesystem_server"],
  "env": {
    "LIGADOAI_ALLOWED_DIR": "/home/hiatus/LigadoAI"
  },
  "enabled": true,
  "description": "Ferramentas read-only para arquivos autorizados."
}
```

9. `GET /v1/agents/ligadoai-terminal/mcp/tools`.
10. Iniciar loop de chat.

## Fluxo de chat recomendado para a Fase 1

Enquanto o OpenTracy nao usar `context.history` no prompt:

1. Carregar resumo da sessao.
2. Carregar ultimas mensagens.
3. Montar um request enriquecido:

```text
Voce esta em uma conversa tecnica continua.

Resumo da sessao:
...

Ultimas mensagens:
Usuario: ...
Assistente: ...

Mensagem atual do usuario:
...
```

4. Chamar:

```http
POST /v1/api/ligadoai-terminal/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "request": "<request enriquecido>",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "channel": "terminal"
}
```

5. Salvar resposta em JSONL local.
6. Logar `trace_id`, latencia e status.

## Fases revisadas

### Fase 1 - Cliente HTTP funcional

- Estrutura Python do projeto.
- `config.toml`.
- Cliente HTTP com retry e tratamento de 401/402/429/502.
- Armazenamento seguro do token.
- Chat Rich.
- Memoria JSONL local.
- Historico achatado no `request`.
- Comandos `/ajuda`, `/sair`, `/limpar`, `/memoria`.
- Modo mock.

### Fase 2 - Bootstrap OpenTracy

- Verificacao de backend/runtime.
- Criacao/ativacao idempotente do agente `ligadoai-terminal`.
- Validacao de rota DeepSeek.
- Conexao do canal API.
- Diagnostico claro para ausencia de `DEEPSEEK_API_KEY`.

### Fase 3 - MCP read-only

- `filesystem_server.py` com `read_file`, `list_directory`, `file_info`.
- `search_server.py` com `search_files` e `grep`.
- Registro via `/v1/agents/<id>/mcp`.
- Testes de path traversal, symlink escape e limite de tamanho.

### Fase 4 - Documentos e ingest

- Conversao PDF/DOCX/XLSX para Markdown.
- Ingest em `corpora/indexed`.
- Comando `/indexar`.
- Validacao de retrieve/rerank.

### Fase 5 - Memoria melhorada

- Resumo automatico.
- Multiplas sessoes.
- `/novo`, `/listar`, `/carregar`, `/resumo`.
- Opcional: patch no OpenTracy para usar `context.history` nativamente.

### Fase 6 - Ferramentas com escrita controlada

- `write_file` apenas com confirmacao.
- Backup antes de editar.
- Diretoria separada de escrita.
- Log de diffs resumidos.

### Fase 7 - Ferramentas industriais

- Analise de vibracao.
- Analise de motor.
- Relatorios tecnicos.
- Preferir microsservicos ou MCP servers dedicados.

## Melhorias sugeridas no documento original

Adicionar uma secao "Contrato real com OpenTracy" com:

- Backend: `http://localhost:8002`.
- Runtime: `http://localhost:8001`.
- Chat publico: `POST /v1/api/<agent_id>/chat`.
- Token: criado por `POST /v1/agents/<id>/channels/api/connect`.
- MCP: configurado em `agents/<id>/mcp.json` via endpoints `/v1/agents/<id>/mcp`.
- DeepSeek: modelos `deepseek-chat` e `deepseek-reasoner`; chave via `.env` global ou secrets por agente apos patch.

Adicionar uma secao "Limitacoes atuais do OpenTracy" com:

- `history` nao entra no prompt do LLM na variante `direct`.
- `session_id` nao existe no canal API publico.
- endpoint de secrets ainda nao aceita `deepseek`.
- backend API timeout atual e 30s.
- budget do agente nao parece ser enforceado no executor.

Adicionar uma secao "MVP recomendado" com escopo menor:

- chat via HTTP;
- memoria local;
- bootstrap de agente/token;
- DeepSeek validado;
- sem MCP na primeira entrega.

## Riscos principais

| Risco | Impacto | Mitigacao |
|---|---|---|
| CLI conversar com agente errado | Respostas usando modelo/config indevidos | Criar e ativar `ligadoai-terminal`; validar rota no bootstrap |
| Historico nao usado pelo LLM | Conversa sem continuidade | Achatar resumo + historico dentro de `request` |
| Token/API key mal armazenados | Vazamento de credenciais | Arquivo `0600`, nunca logar secrets, redacao em logs/tools |
| MCP com acesso amplo ao filesystem | Leitura/escrita indevida | Read-only primeiro, allowed dirs, canonicalizacao e bloqueio de symlinks |
| Timeout do backend menor que o cliente | Erros intermitentes em respostas longas | Alinhar timeout em 30s ou alterar backend |
| RAG prometido sem ingest ativo | Base tecnica nao aparece nas respostas | Entregar conversao + ingest antes de vender RAG como recurso |

## Conclusao

A proposta e tecnicamente viavel e combina bem com o OpenTracy, especialmente porque DeepSeek, API por agente, registry multiagente, traces, CorpusStore e MCP ja existem no projeto.

O ajuste mais importante e reduzir o terminal a uma camada de experiencia e orquestracao. O terminal nao deve virar um segundo runtime. Ele deve preparar o agente, chamar a API, manter memoria local e oferecer comandos de operador. Ferramentas, modelo, roteamento, traces e execucao devem continuar dentro do OpenTracy.

Antes de implementar todas as fases, vale corrigir dois pontos no OpenTracy: aceitar `deepseek` no endpoint de secrets e incluir `context.history` na chamada do LLM. Esses dois ajustes tornam a arquitetura da CLI muito mais limpa.
