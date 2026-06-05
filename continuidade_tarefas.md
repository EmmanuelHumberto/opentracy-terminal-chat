# Continuidade de Tarefas - Cous Terminal Chat

## Contexto Global

### O Projeto
**Cous** (titã da inteligência na mitologia grega) é um assistente técnico especializado em máquinas de tatuagem. Funciona como um CLI interativo que se conecta ao OpenTracy (backend + runtime) usando DeepSeek como LLM, com memória persistente, ferramentas MCP, OCR, indexação de conhecimento e escrita de relatórios.

### Arquitetura
```
CLI (Cous) → HTTP → OpenTracy Backend (8002) → OpenTracy Runtime (8001) → DeepSeek LLM
```
- Cliente fino: `app/` (main.py, chat.py, bootstrap.py, config.py, memory.py, opentracy_client.py, renderer.py, auth.py, logger.py, command_router.py)
- MCP Servers: `ligadoai_tools/` (filesystem_server, search_server, document_server, safety)
- OpenTracy: `/home/hiatus/Projetos/ligadotattoo/OpenTracy`

### Status das Fases
| Fase | Status |
|------|--------|
| Fase 1 - CLI HTTP funcional | ✅ Completa |
| Fase 2 - Bootstrap automático | ✅ Completa |
| Fase 3 - MCP read-only + /tools | ✅ Completa |
| Fase 4 - Documentos e CorpusStore | ✅ Completa |
| Fase 5 - Escrita controlada | ✅ Completa |
| Patch DeepSeek OpenTracy | ✅ Já existia |
| Aliases + consulta + nome Cous | ✅ Configurado |

### Correções Aplicadas (2026-06-05)
Com base no relatório `docs/LigadoAI_Terminal_Chat_Melhorias.md`:

| # | Problema | Status | Arquivos modificados |
|---|----------|--------|---------------------|
| 1 | Bug `action` em `write_file` sempre retornava `"updated"` | ✅ Corrigido | `ligadoai_tools/filesystem_server.py` |
| 2 | Paths hardcoded `/home/hiatus/...` | ✅ Corrigido | `config.toml`, `app/config.py`, `app/chat.py`, `app/bootstrap.py` |
| 3 | `_cmd_tools` bypassava `OpenTracyClient` | ✅ Corrigido | `app/opentracy_client.py` (+ `list_tools()`), `app/chat.py` |
| 4 | `_build_enriched_request()` era código morto | ✅ Corrigido | `app/chat.py` (agora usado condicionalmente) |
| 5 | `knowledge/` vazia | 🟡 Pendente | (próxima tarefa) |
| 6 | `max_tokens_before_summary` confuso | ✅ Corrigido | `config.toml`, `app/config.py` |

### Comandos Úteis
- `liga-chat` - Inicia o chat com Cous
- `liga-up` / `liga-down` / `liga-restart` - Gerencia o OpenTracy
- `liga-indexar` - Converte e indexa documentos knowledge/ → CorpusStore
- `liga-status` - Verifica se serviços estão online
- `consulta` - Lista todos os aliases com descrições
- `/tools` no chat - Lista MCP tools disponíveis

### Arquivos Modificados (último commit pendente)
- `README.md` - Atualizado com nome Cous, Fase 5, aliases
- `app/chat.py` - Comando /tools corrigido (usa OpenTracyClient), paths via config, _build_enriched_request integrado
- `app/renderer.py` - Nome do assistente alterado para "Cous"
- `app/config.py` - Adicionado PathsConfig, renomeado max_chars_before_summary
- `app/bootstrap.py` - Paths via config ao invés de hardcoded
- `app/opentracy_client.py` - Adicionado método list_tools()
- `ligadoai_tools/filesystem_server.py` - Bug do action corrigido
- `config.toml` - Adicionado [paths], renomeado max_chars_before_summary
- `aliases.sh` - Novo, com descrições detalhadas no consulta
- `fix_bashrc.py` - Script auxiliar

## Estrutura da Base de Conhecimento (knowledge/)

Criada em 2026-06-04. Organização atual:

```
knowledge/
├── 01-motores/
│   ├── nucleo/           # Motores com núcleo (iron core)
│   ├── coreless/         # Motores coreless (2016, 1827, 2610...)
│   └── brushless/        # Motores brushless
├── 02-sistemas-mecanicos/
│   ├── direct-drive-fixo/
│   ├── direct-drive-variavel/
│   ├── swash-drive-fixo/
│   └── swash-drive-variavel/
├── 03-maquinas/
│   ├── bobina/
│   ├── rotativa/
│   └── pen/
├── 04-cartuchos/
│   ├── rl/               # Round Liner
│   ├── rs/               # Round Shader
│   └── magnum/           # M1, M2, Curved, Stacked
├── 05-fontes/
│   ├── lineares/
│   └── chaveadas/
├── 06-manuais/
│   ├── fontes/
│   ├── maquinas/
│   └── fabricantes/      # FK Irons, Cheyenne, Bishop, AWA, WOS, DKLAB, Dragonhawk, Mast, EZ, Aston, Ink Machine
├── 07-baterias/
├── 08-medicoes/
│   ├── frequencia/       # Hz, RPM, ciclo (Hall ATS177)
│   ├── consumo/          # Tensão, corrente, potência (INA219)
│   ├── curso/            # Deslocamento magnético (MLX90393)
│   └── vibracao/         # RMS, pico, espectral (MPU6050)
├── 09-diagnosticos/
└── desenhos-tecnicos/
```

## Próxima Tarefa (RETOMAR DAQUI)

**Preencher a base de conhecimento em `knowledge/` com conteúdo técnico.**

A estrutura de pastas está criada, mas vazia (apenas arquivos .gitkeep). O próximo passo é adicionar documentos Markdown, PDFs, imagens e manuais em cada categoria.

### Sugestão de ordem:
1. Criar documentos Markdown com conhecimento técnico sobre sistemas mecânicos (direct drive vs swash drive)
2. Adicionar datasheets de motores coreless (2016, 1827, 2610)
3. Criar documentos de diagnóstico para sintomas genéricos (não liga, vibração excessiva, superaquecimento, etc.)
4. Adicionar manuais dos fabricantes
5. Indexar tudo com `liga-indexar` e testar a qualidade das respostas

### Observações importantes:
- A arquitetura do conhecimento vai mudar ainda conforme evoluir
- O cliente final é leigo (tatuador que não entende de engenharia)
- O objetivo é que o Cous consiga diagnosticar problemas a partir de sintomas genéricos
- Após a base de conhecimento sólida, o próximo passo é preparar para atendimento ao público (site/WhatsApp)
