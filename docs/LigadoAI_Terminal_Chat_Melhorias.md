# Relatório Técnico — TCC LigadoTattoo
**Repositórios analisados:** `firmware-tattoo-machine` · `opentracy-terminal-chat`
**Data da análise:** junho de 2025
**Última revisão:** 2026-06-05 — Correções aplicadas (ver abaixo)

---

## Sumário executivo

O projeto é composto por dois repositórios complementares com objetivos distintos: o firmware embarcado no ESP32-S3 captura e publica medições físicas das máquinas de tatuagem; o Cous CLI consome essas informações via assistente especializado com RAG. Ambos apresentam arquitetura bem pensada, documentação acima da média para projetos de TCC e disciplina de testes evidente.

Os problemas identificados se dividem em três categorias: **bugs confirmados** (comportamento incorreto já em produção), **riscos arquiteturais** (código correto hoje, mas que vai quebrar com o crescimento do projeto) e **melhorias de qualidade** (código confuso, código morto, acoplamentos desnecessários).

Nenhum dos problemas listados invalida o projeto. Todos têm correção direta.

---

## Tabela de prioridades

| \# | Repositório | Problema | Severidade | Esforço | Status |
|----|-------------|----------|-----------|---------|--------|
| 1 | Cous CLI | Bug: `action` em `tool_write_file` sempre retorna `"updated"` | 🔴 Bug | Baixo | ✅ Corrigido |
| 2 | Cous CLI | Paths hardcoded para `/home/hiatus/...` | 🔴 Não portável | Baixo | ✅ Corrigido |
| 3 | Firmware | Task única — starvation do sensor durante render de UI | 🔴 Risco arquitetural | Médio | ⏳ Pendente |
| 4 | Firmware | Core depende de `ui_runtime` em compile-time sempre | 🟡 Acoplamento | Médio | ⏳ Pendente |
| 5 | Cous CLI | `knowledge/` completamente vazia | 🟡 Funcional | Alto\* | ⏳ Pendente |
| 6 | Cous CLI | `_cmd_tools` bypassa `OpenTracyClient` | 🟡 Inconsistência | Baixo | ✅ Corrigido |
| 7 | Cous CLI | `_build_enriched_request()` — código morto | 🟡 Limpeza | Baixo | ✅ Corrigido |
| 8 | Firmware | Parse de texto frágil na waveform | 🟡 Fragilidade | Baixo | ⏳ Pendente |
| 9 | Cous CLI | Naming confuso: `max_tokens_before_summary` | 🟢 Clareza | Baixo | ✅ Corrigido |
| 10 | Firmware | `storage/` e `comm/` vazios sem placeholder de erro | 🟢 Futuro | Baixo | ⏳ Pendente |

\* _esforço alto porque envolve curadoria de conteúdo, não só código._

---

## Correções Aplicadas (2026-06-05)

### Cous CLI — Problemas do repositório `opentracy-terminal-chat`

#### 🔴 Bug 1 — ✅ Corrigido: `tool_write_file`: campo `action` sempre retornava `"updated"`

**Arquivo:** `ligadoai_tools/filesystem_server.py`

**O que era:** A verificação `resolved.exists()` era feita **após** a escrita do arquivo, então sempre retornava `True`.

**Correção:** Capturado `file_existed = resolved.exists()` **antes** da escrita. O campo `action` agora retorna `"created"` para arquivos novos e `"updated"` para sobrescritas.

#### 🔴 Bug 2 — ✅ Corrigido: Paths hardcoded para `/home/hiatus/...`

**Arquivos:** `app/chat.py`, `app/bootstrap.py`, `app/config.py`, `config.toml`

**O que era:** `OPENTRACY_ROOT` e `TERMINAL_ROOT` hardcoded em `chat.py` e `bootstrap.py`.

**Correção:** 
- Adicionada seção `[paths]` no `config.toml` com `opentracy_root` e `terminal_root`
- Criada classe `PathsConfig` no `config.py` com properties que expandem `~`
- `chat.py` e `bootstrap.py` agora usam `config.paths.opentracy_path`

#### 🟡 Risco 3 — ✅ Corrigido: `_cmd_tools` bypassava `OpenTracyClient`

**Arquivos:** `app/opentracy_client.py`, `app/chat.py`

**O que era:** Usava `httpx.get()` direto com timeout hardcoded de 10s, sem tratamento de 401/429/502.

**Correção:**
- Adicionado método `list_tools(auth_token)` ao `OpenTracyClient` com tratamento padronizado de erros
- `_cmd_tools` agora usa `ctx.client.list_tools(ctx.auth_token)`

#### 🟡 Risco 4 — ✅ Corrigido: `_build_enriched_request()` era código morto

**Arquivo:** `app/chat.py`

**O que era:** Função definida mas nunca chamada no `run_chat_loop`.

**Correção:** Agora é usada condicionalmente no loop principal:
```python
if ctx.config.memory.flatten_history_into_request:
    request_payload = _build_enriched_request(summary, recent, user_input)
    history_payload = None
else:
    request_payload = user_input
    history_payload = history
```

#### 🟢 Melhoria 6 — ✅ Corrigido: Naming confuso `max_tokens_before_summary`

**Arquivos:** `config.toml`, `app/config.py`

**O que era:** Campo chamado `max_tokens_before_summary = 4000` mas internamente multiplicado por 4 para 16.000 chars.

**Correção:** Renomeado para `max_chars_before_summary = 16000` — o valor é usado diretamente, sem conversão.

---

*Relatório original: junho de 2025. Correções aplicadas: 2026-06-05.*
