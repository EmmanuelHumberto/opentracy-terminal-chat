# ============================================================
# LigadoAI Terminal Chat - Aliases
# ============================================================

export LIGADOAI_TERMINAL="/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat"
export LIGADOAI_OPENTRACY="/home/hiatus/Projetos/ligadotattoo/OpenTracy"

# --- Ativar ambiente ---
alias liga="cd $LIGADOAI_TERMINAL && source .venv/bin/activate"
alias liga-opentracy="cd $LIGADOAI_OPENTRACY && source .venv/bin/activate"

# --- Iniciar chat ---
alias liga-chat="cd $LIGADOAI_TERMINAL && source .venv/bin/activate && python3 -m app.main"
alias liga-chat-mock="cd $LIGADOAI_TERMINAL && source .venv/bin/activate && python3 -m app.main --mock"

# --- Servidor OpenTracy ---
alias liga-up="cd $LIGADOAI_OPENTRACY && make up"
alias liga-down="cd $LIGADOAI_OPENTRACY && make down"
alias liga-restart="cd $LIGADOAI_OPENTRACY && make down && make up"

# --- Indexar ---
alias liga-indexar="cd $LIGADOAI_TERMINAL && source .venv/bin/activate && python3 -c \"
from ligadoai_tools.document_server import convert_directory
from pathlib import Path
r = convert_directory(Path('knowledge'), Path('knowledge_md'))
print(f'Convertidos: {r[\"converted\"]}, Erros: {r[\"errors\"]}, Parciais: {r[\"partials\"]}')
\""

# --- Logs ---
alias liga-logs="tail -f $LIGADOAI_TERMINAL/logs/terminal-*.jsonl"
alias liga-logs-runtime="tail -f $LIGADOAI_OPENTRACY/.run/runtime.log"
alias liga-logs-backend="tail -f $LIGADOAI_OPENTRACY/.run/backend.log"

# --- Status ---
alias liga-status="cd $LIGADOAI_TERMINAL && source .venv/bin/activate && python3 -c \"
import httpx
for name, url in [('Backend', 'http://localhost:8002/health'), ('Runtime', 'http://localhost:8001/health')]:
    try:
        r = httpx.get(url, timeout=5)
        print(f'{name}: {\"OK\" if r.is_success else \"FALHA\"}')
    except Exception as e:
        print(f'{name}: OFF')
\""

# --- Consultar aliases ---
alias consulta="echo '===============================================================================' && echo '  LIGADOAI - Cous Terminal Chat' && echo '  Lista completa de comandos disponiveis' && echo '===============================================================================' && echo && echo '  AMBIENTE' && echo '  ---------------------------------------------------------------------------' && echo '  liga             Ativa o ambiente Python do terminal chat (entra na pasta e ativa o .venv)' && echo '  liga-opentracy   Ativa o ambiente Python do OpenTracy' && echo && echo '  CHAT' && echo '  ---------------------------------------------------------------------------' && echo '  liga-chat        Inicia o chat com o assistente Cous (conectado ao OpenTracy)' && echo '  liga-chat-mock   Inicia o chat em modo offline (sem OpenTracy, para testes)' && echo && echo '  SERVIDOR' && echo '  ---------------------------------------------------------------------------' && echo '  liga-up          Sobe o OpenTracy (runtime porta 8001 + backend porta 8002 + UI)' && echo '  liga-down        Para todos os servicos do OpenTracy' && echo '  liga-restart     Reinicia o OpenTracy (executa down + up)' && echo && echo '  CONHECIMENTO' && echo '  ---------------------------------------------------------------------------' && echo '  liga-indexar     Converte documentos da pasta knowledge/ para Markdown' && echo '                  e ingere no CorpusStore do OpenTracy para consulta via chat' && echo && echo '  LOGS' && echo '  ---------------------------------------------------------------------------' && echo '  liga-logs        Mostra logs do terminal chat em tempo real' && echo '  liga-logs-runtime  Mostra logs do runtime do OpenTracy' && echo '  liga-logs-backend  Mostra logs do backend do OpenTracy' && echo && echo '  DIAGNOSTICO' && echo '  ---------------------------------------------------------------------------' && echo '  liga-status      Verifica se o backend (8002) e runtime (8001) estao online' && echo '==============================================================================='"
