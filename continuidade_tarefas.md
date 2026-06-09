# Continuidade — Sessões 2026-06-05 + 2026-06-07

---

## Sessão 2026-06-07 — Arquitetura da Base de Conhecimento

### Decisões tomadas (refinamento do plano)

1. **Furo #5 (firmware) descartado**: as 4 verticais (Hall, Power, MLX, MPU) publicam via serial. Logs estavam desabilitados durante análise, não é bug.
2. **Modelo de embedding**: `paraphrase-multilingual-MiniLM-L12-v2` (384d) no lugar do L6 (inglês). Resolve cross-language PT↔EN/DE.
3. **Retrieve híbrido**: filtro SQL por frontmatter (fabricante, modelo, tipo) antes do FAISS — reduz espaço de busca, aumenta precisão.
4. **Limpeza de chunks**: strip de comentários HTML, delimitadores e metadados antes de embeddar.
5. **OpenTracy modificado**: `POST /corpus/reload` em vez de filesystem — contrato HTTP explícito, sem intermediário em disco.
6. **OpenTracy NÃO conhece o banco**: recebe arrays de floats e strings via HTTP. Zero dependência de PostgreSQL.
7. **Sem healthcheck automático**: só mensagem de erro explícita no reload + comando `/status`.
8. **backend flag**: `config.toml` → `[corpus] backend = "postgresql" | "filesystem"` para dev local.

### Fase 1 — Cous (CONCLUÍDA ✅)

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `scripts/sql/migracao_v2.sql` | NOVO | Schema: `documentos_conhecimento` (UUID, frontmatter JSONB, hash, status) + `chunks` (FLOAT4[384]) |
| `app/validador_conhecimento.py` | NOVO | 5 regras (YAML, campos obrigatórios, faixas, UTF-8, conteúdo), saída aprovado/rejeitado/aviso |
| `app/knowledge_syncer.py` | NOVO | Chunker + embedder multilíngue + upsert PG por hash + limpeza HTML + `listar_chunks_ativos()` |
| `app/config.py` | EDITADO | `CorpusConfig` (backend, embedder_model, chunk_size, overlap) + campo `corpus` no `Config` |
| `config.toml` | EDITADO | `vector_dimension = 384`, seção `[corpus]` |
| `pyproject.toml` | EDITADO | +`sentence-transformers>=2.0`, +`pyyaml>=6.0` |

### Fase 2 — OpenTracy (CONCLUÍDA ✅ — 2026-06-07)

Repositório: `/home/hiatus/Projetos/ligadotattoo/OpenTracy`

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `corpora/memory_store.py` | NOVO | Singleton FAISS em memória. `reload(chunks, vectors)` atômico com `asyncio.Lock`. Interface: `size`, `query()`, `empty`. |
| `techniques/rag/impl.py` | EDITADO | `_load_store()` troca `CorpusStore.load()` → `CorpusMemoryStore.instance()`. Também removido `_store_mtime` do `__init__` e atualizada docstring. |
| `runtime/server.py` | EDITADO | Novo endpoint: `POST /corpus/reload`. Recebe `{chunks: [...], vectors: [[...], ...]}`, chama `CorpusMemoryStore.instance().reload()`, retorna `{loaded: N, dimension: D}`. |

**⚠️ Testes quebrados**: `techniques/rag/tests/test_dense.py` usava monkeypatches de filesystem (`corpora.store._DEFAULT_ROOT`). Com a troca para `CorpusMemoryStore`, esses testes precisam ser adaptados na **Fase 5** para usar `CorpusMemoryStore.instance().reload()` diretamente.

**NÃO mudar**: `corpora/store.py`, `corpora/ingest.py`, pipeline, reranker, router, testes existentes.

### Fase 3 — Cous: Integração (CONCLUÍDA ✅ — 2026-06-07)

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `app/corpus_client.py` | NOVO | Cliente HTTP: lê chunks do PG via `KnowledgeSyncer.listar_chunks_ativos()`, serializa, chama `POST /corpus/reload`. Fallback para vetores vazios. |
| `app/knowledge_syncer.py` | EDITADO | +`listar_documentos()` e +`remover_documento(doc_id)` para suporte aos comandos `/indexados` e `/remover`. |
| `app/chat.py` | EDITADO | `_cmd_indexar` reescrito: valida → syncer → corpus_client. `--dry-run` só valida. |
| `app/chat.py` | EDITADO | +`_cmd_indexados`: lista docs no PG (tabela Rich). +`_cmd_remover <id>`: remove doc + chunks + reload FAISS. |
| `app/chat.py` | EDITADO | Startup: `CorpusClient.ensure_loaded()` no `run_chat_loop()`. Falha não bloqueia o chat. |
| `app/chat.py` | EDITADO | `ChatContext.corpus_client`: referência lazy para o cliente HTTP. |
| `app/chat.py` | EDITADO | `build_router()`: registrados `/indexados` e `/remover`. |

### Fase 4 — Retrieve híbrido (CONCLUÍDA ✅ — 2026-06-07)

| Tarefa | Descrição |
|--------|-----------|
| Filtro em memória | `CorpusMemoryStore.query()` ganhou parâmetro `filtro: dict[str, str]`. Busca `k*3` candidatos no FAISS e pós-filtra contra `_manifest` (case-insensitive). Zero round-trip ao PG. |
| `_DenseRetriever` | Lê `context.state["filtro_corpus"]` e passa ao `store.query()`. |
| Limpeza de chunks | Já implementada no `knowledge_syncer._limpar_chunk()` — nenhuma ação necessária. |

**Como usar:** um estágio anterior no pipeline (ex.: extract de entidades) popula `context.state["filtro_corpus"]` com `{"fabricante": "Cheyenne", "tipo": "motor"}`. O RAG automaticamente restringe a busca. Sem filtro, comportamento idêntico ao anterior.

### Fase 5 — Migração do acervo (CONCLUÍDA ✅ — 2026-06-07)

| Ação | Status | Detalhes |
|------|--------|----------|
| Migrar `knowledge_md/` → PG | **Pulada** | Pasta estava vazia (só `.gitkeep` e subpastas sem arquivos). Nada a migrar. |
| Remover `knowledge_md/` | **Pendente manual** | Executar `rm -rf knowledge_md/` no terminal (ferramenta de deleção não disponível na sessão). |
| `KnowledgeConfig` | **Removido** | Classe, campo `Config.knowledge` e `resolve_paths()` removidos de `app/config.py`. |
| `[knowledge]` no `config.toml` | **Removido** | Seção `[knowledge]` e `knowledge_md` de `allowed_read_dirs` removidos. |
| `CorpusStore` / `ingest.py` | **Mantidos** | Permanecem como fallback com `backend = "filesystem"`. `corpora/indexed/` preservado. |

**🖥️ Ação manual necessária:**
```bash
cd /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat
rm -rf knowledge_md/
```

---

## Como retomar

1. Iniciar codewhale no diretório: `/home/hiatus/Projetos/ligadotattoo/`
2. Apontar para este arquivo: `opentracy-terminal-chat/continuidade_tarefas.md`
3. **Todas as 5 fases concluídas.** Verificar se há tarefas pendentes ou seguir para implementação de features adicionais.
4. **Extra (2026-06-07):** Conversão automática restaurada no `/indexar` — PDF/DOCX/XLSX/ZIP voltam a ser convertidos com inferência de frontmatter da estrutura de diretórios.

### Evidência do que já foi feito

**Fase 1 (Cous):**
```bash
ls -la scripts/sql/migracao_v2.sql        # 4381 bytes
ls -la app/validador_conhecimento.py      # 11073 bytes
ls -la app/knowledge_syncer.py            # 14298 bytes
grep "sentence-transformers" pyproject.toml
grep "corpus" config.toml
grep "CorpusConfig" app/config.py
```

**Fase 2 (OpenTracy):**
```bash
ls -la ../OpenTracy/corpora/memory_store.py          # NOVO ~5.5KB
grep "CorpusMemoryStore" ../OpenTracy/techniques/rag/impl.py
grep "corpus/reload" ../OpenTracy/runtime/server.py
```

**Fase 3 (Cous — Integração):**
```bash
ls -la app/corpus_client.py                          # NOVO ~6KB
grep "listar_documentos\|remover_documento" app/knowledge_syncer.py
grep "indexados\|remover\|CorpusClient\|ensure_loaded" app/chat.py
```

**Fase 4 (Retrieve híbrido):**
```bash
grep "filtro" ../OpenTracy/corpora/memory_store.py   # _aplicar_filtro + parâmetro no query()
grep "filtro_corpus" ../OpenTracy/techniques/rag/impl.py
```

**Fase 5 (Migração do acervo):**
```bash
grep -c "KnowledgeConfig" app/config.py               # 0 (removido)
grep -c "\[knowledge\]" config.toml                     # 0 (removido)
grep "knowledge_md" config.toml                         # 0 (removido de allowed_read_dirs)
```

**Extra — Conversão automática restaurada:**
```bash
grep "_inferir_frontmatter\|_converter_arquivos\|_FORMATOS_CONVERSIVEIS" app/chat.py
```

---

## Referência de Comandos do Chat

### Base de Conhecimento

| Comando | Descrição |
|---------|-----------|
| `/indexar` | Converte `knowledge/` (PDF/DOCX/XLSX/ZIP) e indexa tudo no PG + FAISS |
| `/indexar <arquivo.md>` | Valida frontmatter YAML e indexa no PG + FAISS |
| `/indexar <arquivo.pdf>` | Converte PDF → infere metadados → valida → indexa |
| `/indexar <pasta/>` | Indexa `.md` da pasta (converte PDFs se houver) |
| `/indexar --dry-run <arquivo>` | Apenas valida, sem persistir |
| `/indexados` | Lista documentos indexados (tabela com ID, fabricante, modelo, tipo, status) |
| `/remover <id>` | Remove documento do PG + recarrega FAISS |

### Sessões e Memória

| Comando | Descrição |
|---------|-----------|
| `/novo` | Cria nova sessão de conversa |
| `/listar` | Lista todas as sessões salvas |
| `/carregar <id>` | Carrega uma sessão existente |
| `/memoria` | Mostra uso de memória da sessão atual |
| `/resumo` | Força geração de resumo da conversa |

### Medições (Firmware)

| Comando | Descrição |
|---------|-----------|
| `/capturar [porta]` | Inicia captura de métricas da máquina via serial |
| `/medicoes` | Lista sessões de medição salvas |
| `/medicao <id>` | Mostra detalhes de uma sessão |
| `/laudo <id>` | Gera laudo técnico de uma sessão |

### Sistema

| Comando | Descrição |
|---------|-----------|
| `/ajuda` | Mostra todos os comandos disponíveis |
| `/status` | Verifica conexão com OpenTracy (backend + runtime + agente) |
| `/tools` | Lista ferramentas MCP registradas no agente |
| `/limpar` | Limpa a tela |
| `/sair` | Encerra o programa |

### Inicialização

```bash
# Tudo automático (runtime inicia junto)
uv run python -m app.main

# Sem auto-iniciar o runtime
uv run python -m app.main --no-runtime

# Bootstrap forçado
uv run python -m app.main --bootstrap

# Modo offline (sem OpenTracy)
uv run python -m app.main --mock
```
