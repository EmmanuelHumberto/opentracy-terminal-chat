#!/bin/bash
# ============================================================================
# Teste rapido da instalacao do LigadoAI
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  Teste de Instalacao - LigadoAI"
echo "=========================================="
echo ""

erros=0

# 1. Verifica Python
echo "🔍 Python..."
if command -v python3 &> /dev/null; then
    PYTHON=$(command -v python3)
    echo "   Python: $($PYTHON --version)"
else
    echo "   ❌ Python3 nao encontrado"
    erros=$((erros+1))
fi

# 2. Verifica Docker
echo "🔍 Docker..."
if command -v docker &> /dev/null; then
    echo "   Docker: $(docker --version 2>/dev/null || echo 'sem permissao')"
    if docker ps &> /dev/null; then
        echo "   ✅ Docker funcionando"
    else
        echo "   ⚠️  Docker instalado mas sem permissao (faça logout/login)"
    fi
else
    echo "   ❌ Docker nao encontrado"
    erros=$((erros+1))
fi

# 3. Verifica Docker Compose
echo "🔍 Docker Compose..."
if docker compose version &> /dev/null; then
    echo "   ✅ Docker Compose: $(docker compose version)"
else
    echo "   ❌ Docker Compose nao encontrado"
    erros=$((erros+1))
fi

# 4. Verifica dependencias Python
echo "🔍 Dependencias Python..."
cd "$PROJECT_DIR"

if [ -f "pyproject.toml" ]; then
    # Tenta importar as principais
    $PYTHON -c "import rich; print('   ✅ rich:', rich.__version__)" 2>/dev/null || echo "   ❌ rich faltando"
    $PYTHON -c "import httpx; print('   ✅ httpx:', httpx.__version__)" 2>/dev/null || echo "   ❌ httpx faltando"
    $PYTHON -c "import pydantic; print('   ✅ pydantic:', pydantic.__version__)" 2>/dev/null || echo "   ❌ pydantic faltando"
    $PYTHON -c "import asyncpg; print('   ✅ asyncpg:', asyncpg.__version__)" 2>/dev/null || echo "   ❌ asyncpg faltando (pip install asyncpg)"
fi

# 5. Verifica estrutura de pastas
echo "🔍 Estrutura do projeto..."
for pasta in "app" "scripts/sql" "knowledge"; do
    if [ -d "$PROJECT_DIR/$pasta" ]; then
        echo "   ✅ $pasta/"
    else
        echo "   ❌ $pasta/ nao encontrada"
        erros=$((erros+1))
    fi
done

# 6. Verifica arquivos principais
echo "🔍 Arquivos principais..."
for arquivo in "app/chat.py" "app/captura_serial.py" "app/repositorio_medicoes.py" \
               "app/formulario_coleta.py" "app/laudo_tecnico.py" "app/config.py" \
               "config.toml" "docker-compose.yml" "scripts/sql/init.sql"; do
    if [ -f "$PROJECT_DIR/$arquivo" ]; then
        echo "   ✅ $arquivo"
    else
        echo "   ❌ $arquivo faltando"
        erros=$((erros+1))
    fi
done

echo ""
echo "=========================================="
if [ "$erros" -eq 0 ]; then
    echo "  ✅ Todos os testes passaram!"
    echo ""
    echo "  Proximo passo:"
    echo "    bash scripts/instalar_docker.sh   # Se Docker nao estiver instalado"
    echo "    bash scripts/setup_banco.sh       # Subir PostgreSQL"
    echo "    liga-chat                         # Iniciar o chat"
else
    echo "  ⚠️  $erros erro(s) encontrado(s)"
fi
echo "=========================================="
echo ""
