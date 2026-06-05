#!/bin/bash
# ============================================================================
# Setup do Banco de Dados LigadoAI (PostgreSQL + pgvector)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  LigadoAI - Setup do Banco de Dados"
echo "=========================================="
echo ""

# Verifica se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Instale Docker primeiro:"
    echo "   https://docs.docker.com/engine/install/"
    exit 1
fi

# Verifica se Docker Compose está instalado
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose não encontrado."
    exit 1
fi

echo "🐳 Iniciando PostgreSQL com pgvector..."
echo ""

cd "$PROJECT_DIR"

# Sobe o container
docker compose up -d postgres

# Aguarda o banco ficar pronto
echo ""
echo "⏳ Aguardando banco de dados ficar pronto..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U ligadoai -d ligadoai &> /dev/null; then
        echo "✅ Banco de dados pronto!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "❌ Timeout aguardando banco de dados."
        echo "   Verifique os logs: docker compose logs postgres"
        exit 1
    fi
    sleep 1
done

echo ""
echo "📦 Schema inicial já foi aplicado via docker-entrypoint-initdb.d"
echo ""

# Instala dependencias Python
echo "🐍 Instalando dependencias Python (asyncpg, pgvector)..."
cd "$PROJECT_DIR"
if [ -d ".venv" ]; then
    .venv/bin/pip install asyncpg pgvector 2>/dev/null || true
    echo "✅ Dependencias instaladas no .venv existente"
else
    echo "ℹ️  Nenhum .venv encontrado. Execute 'pip install asyncpg pgvector' manualmente."
fi

echo ""
echo "=========================================="
echo "  ✅ Setup concluido!"
echo "=========================================="
echo ""
echo "  Host: localhost"
echo "  Porta: 5432"
echo "  Banco: ligadoai"
echo "  Usuario: ligadoai"
echo "  Senha: ligadoai"
echo ""
echo "  DSN: postgresql://ligadoai:ligadoai@localhost:5432/ligadoai"
echo ""
echo "  Comandos uteis:"
echo "    docker compose ps              # Status dos containers"
echo "    docker compose logs postgres   # Logs do banco"
echo "    docker compose down            # Parar banco"
echo "    docker compose up -d           # Iniciar banco"
echo ""
