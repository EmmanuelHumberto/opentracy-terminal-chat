#!/bin/bash
# ============================================================================
# Instalacao completa LigadoAI (Docker + Dependencias Python)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  Instalacao Completa - LigadoAI"
echo "=========================================="
echo ""

# ---- 1. DOCKER ----
echo "📦 [1/3] Instalando Docker..."
if command -v docker &> /dev/null; then
    echo "   ✅ Docker ja instalado: $(docker --version 2>/dev/null || echo 'ok')"
else
    echo "   ⚠️  Docker nao encontrado. Deseja instalar? (s/N)"
    read -r resposta
    if [[ "$resposta" =~ ^[Ss]$ ]]; then
        bash "$SCRIPT_DIR/instalar_docker.sh"
        echo "   ℹ️  Execute 'newgrp docker' ou faça logout/login apos a instalacao"
    else
        echo "   ⏭️  Pulando instalacao do Docker"
        echo "   Instale manualmente: https://docs.docker.com/engine/install/"
    fi
fi
echo ""

# ---- 2. VIRTUAL ENV ----
echo "📦 [2/3] Configurando ambiente virtual..."
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "   ✅ .venv criado"
else
    echo "   ✅ .venv ja existe"
fi

source .venv/bin/activate
echo "   🐍 Python: $(python --version)"
echo ""

# ---- 3. DEPENDENCIAS PYTHON ----
echo "📦 [3/3] Instalando dependencias Python..."
pip install --upgrade pip -q

# Instala dependencias principais
echo "   Instalando rich, httpx, pydantic..."
pip install rich httpx pydantic -q

# Instala asyncpg e pgvector
echo "   Instalando asyncpg, pgvector..."
pip install asyncpg pgvector -q

# Instala dependencias de documentos
echo "   Instalando pymupdf, python-docx, openpyxl..."
pip install pymupdf python-docx openpyxl -q

# Instala OCR
echo "   Instalando pytesseract, Pillow..."
pip install pytesseract Pillow -q

echo ""
echo "   ✅ Dependencias instaladas!"
echo ""

# ---- VERIFICACAO FINAL ----
echo "=========================================="
echo "  ✅ Instalacao concluida!"
echo "=========================================="
echo ""
echo "📋 Resumo:"
python -c "
import rich; print(f'  rich: {rich.__version__}')
import httpx; print(f'  httpx: {httpx.__version__}')
import pydantic; print(f'  pydantic: {pydantic.__version__}')
import asyncpg; print(f'  asyncpg: {asyncpg.__version__}')
" 2>/dev/null || echo "  ⚠️  Algumas bibliotecas podem nao ter sido instaladas"

echo ""
echo "🚀 Proximos passos:"
echo ""
if command -v docker &> /dev/null; then
    echo "  1. bash scripts/setup_banco.sh   # Subir PostgreSQL"
    echo "  2. source .venv/bin/activate     # Ativar ambiente"
    echo "  3. liga-chat                     # Iniciar chat"
else
    echo "  1. Instalar Docker manualmente"
    echo "  2. bash scripts/setup_banco.sh"
    echo "  3. source .venv/bin/activate"
    echo "  4. liga-chat"
fi
echo ""
