# Cous - Terminal Chat para OpenTracy

CLI interativa para conversar com o [OpenTracy](https://github.com/opentracy) via terminal, usando **DeepSeek** como provedor LLM, com memória persistente, ferramentas MCP, OCR, indexação de conhecimento e escrita de relatórios.

> **Cous** — titã da inteligência na mitologia grega. Um assistente técnico especializado em análise e diagnóstico de máquinas de tatuagem.

> **Status do projeto:** Fase 5 implementada (Escrita controlada)

---

## Proposta

O **Cous** é um **cliente fino** do OpenTracy. Ele cuida da experiência de terminal, configuração, histórico local, resumo de sessões, comandos de operador e chamadas HTTP. O OpenTracy continua responsável por:

- Agente e roteamento de modelo
- Chamadas ao DeepSeek (ou outro provedor)
- Traces e telemetria
- Canal API público
- Execução de ferramentas MCP
- CorpusStore (índice vetorial para busca em documentos)

### Arquitetura

```
┌─────────────────────────────────────────────────┐
│                    Cous                          │
│  (experiência de terminal, memória local,       │
│   bootstrap, comandos, conversão de docs,       │
│   escrita de relatórios)                        │
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
3. Envia a pergunta pura para o OpenTracy (para o retrieve funcionar)
4. OpenTracy processa (retrieve → rerank → route → generate)
5. Modelo pode chamar ferramentas MCP (ler arquivos, buscar, escrever relatórios)
6. Resposta é renderizada em Markdown no terminal
7. Histórico e trace_id são salvos localmente

---

## Fases de Implementação

### ✅ Fase 1 - CLI HTTP funcional
- [x] Estrutura do projeto
- [x] Configuração via `config.toml`
- [x] Autenticação com token (arquivo `0600`)
- [x] Cliente HTTP com tratamento de erros
- [x] Interface Rich com Markdown
- [x] Memória local JSONL
- [x] Comandos básicos
- [x] Modo mock
- [x] Logs JSONL

### ✅ Fase 2 - Bootstrap automático
- [x] Health check
- [x] Criação/ativação de agente
- [x] Ajuste de rota DeepSeek
- [x] Conexão do canal API
- [x] Diagnóstico de chave ausente

### ✅ Fase 3 - MCP read-only
- [x] Leitura de arquivos
- [x] Listagem de diretórios
- [x] Busca textual (glob + regex)
- [x] Data/hora atual
- [x] Schema de erro padronizado

### ✅ Fase 4 - Documentos e CorpusStore
- [x] Conversão `.md`, `.txt`, `.pdf`, `.docx`, `.xlsx`
- [x] OCR em PDFs escaneados e imagens (Tesseract)
- [x] Comando `/indexar`
- [x] Ingest no CorpusStore
- [x] Recarga automática do índice

### ✅ Fase 5 - Escrita controlada
- [x] `write_file` com backup automático
- [x] Diretório segregado (`reports/`)
- [x] Bloqueio de arquivos de segredo
- [x] `create_backup`

---

## Requisitos

- **Python** >= 3.11
- **OpenTracy** rodando (`make up` em `/home/hiatus/Projetos/ligadotattoo/OpenTracy`)
- **DeepSeek API Key** configurada no `.env` do OpenTracy

## Instalação

```bash
cd /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Uso Rápido (Aliases)

Adicione ao `~/.bashrc`:

```bash
source /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/aliases.sh
```

Comandos disponíveis:

| Comando | Descrição |
|---|---|
| `consulta` | Lista todos os aliases |
| `liga-chat` | Inicia o chat |
| `liga-up` | Sobe o OpenTracy |
| `liga-down` | Para o OpenTracy |
| `liga-restart` | Reinicia o OpenTracy |
| `liga-indexar` | Indexa documentos |
| `liga-status` | Status dos serviços |
| `liga-logs` | Logs do terminal |

## Comandos do Chat

| Comando | Descrição |
|---|---|
| `/ajuda` | Lista comandos |
| `/sair` | Encerra |
| `/limpar` | Limpa tela |
| `/resumo` | Força resumo da sessão |
| `/memoria` | Status da memória |
| `/novo` | Nova sessão |
| `/listar` | Lista sessões |
| `/carregar <id>` | Carrega sessão |
| `/status` | Status do OpenTracy |
| `/indexar` | Converte documentos e ingere |

## Estrutura

```
├── app/                    # CLI principal
├── ligadoai_tools/         # MCP servers
│   ├── filesystem_server  # read, write, list, backup
│   ├── search_server      # grep, search
│   ├── document_server    # conversão de documentos
│   └── safety             # validação de caminhos
├── knowledge/             # Documentos fonte
├── knowledge_md/          # Documentos convertidos
├── reports/               # Relatórios gerados
├── conversations/         # Histórico
├── memory/                # Resumos
└── logs/                  # Logs JSONL
```

## Segurança

- Token em arquivo `0600`
- Nenhuma chave em logs
- Path traversal bloqueado
- Arquivos de segredo bloqueados
- Escrita apenas em diretórios autorizados
- Backup automático antes de sobrescrever
