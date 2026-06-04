# LigadoAI Terminal Chat

CLI interativa para conversar com o OpenTracy via terminal, usando DeepSeek como provedor LLM.

## Requisitos

- Python >= 3.11
- OpenTracy rodando (`make up` em `/home/hiatus/Projetos/ligadotattoo/OpenTracy`)
- Agente `ligadoai-terminal` criado no OpenTracy
- Canal API conectado e token salvo
- `DEEPSEEK_API_KEY` no `.env` do OpenTracy

## Instalacao

```bash
uv sync
```

## Configuracao

Edite `config.toml` se necessario. O padrao aponta para `localhost:8002` (backend).

Token do canal API deve ficar em `~/.ligadoai/api_token` com permissao 0600.

## Uso

```bash
# Normal
uv run python -m app.main

# Modo mock (sem OpenTracy)
uv run python -m app.main --mock
```

## Comandos

| Comando | Descricao |
|---|---|
| `/ajuda` | Lista comandos |
| `/sair` | Encerra |
| `/limpar` | Limpa tela |
| `/resumo` | Forca resumo da sessao |
| `/memoria` | Status da memoria |
| `/novo` | Nova sessao |
| `/listar` | Lista sessoes |
| `/carregar <id>` | Carrega sessao |
| `/status` | Status do OpenTracy |

## Estrutura

```
app/              # CLI
ligadoai_tools/   # MCP servers (Fase 3+)
conversations/    # Historico JSONL
memory/           # Resumos Markdown
logs/             # Logs JSONL
knowledge/        # Documentos fonte (Fase 4)
knowledge_md/     # Documentos convertidos (Fase 4)
```
