#!/usr/bin/env python3
"""Teste rapido de conexao com o banco PostgreSQL."""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretorio raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.repositorio_medicoes import RepositorioMedicoesPG


async def testar():
    print("=" * 50)
    print("  Teste de Conexao - PostgreSQL LigadoAI")
    print("=" * 50)
    print()

    # Carrega config
    config = load_config()
    print(f"📋 Configuracao:")
    print(f"   Host: {config.banco.host}")
    print(f"   Porta: {config.banco.port}")
    print(f"   Banco: {config.banco.database}")
    print(f"   Usuario: {config.banco.user}")
    print(f"   DSN: {config.banco.dsn}")
    print()

    # Tenta conectar
    print("🔌 Conectando ao banco...")
    repo = RepositorioMedicoesPG(config.banco)

    try:
        await repo.conectar()
        print("   ✅ Conectado com sucesso!")
        print()

        # Lista tabelas
        async with repo._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            print(f"   📊 Tabelas encontradas ({len(rows)}):")
            for row in rows:
                print(f"      - {row['table_name']}")

        print()

        # Testa estatisticas
        print("📊 Estatisticas do banco:")
        stats = await repo.estatisticas_globais()
        print(f"   Sessoes: {stats['total_sessoes']}")
        print(f"   Snapshots: {stats['total_snapshots']}")
        print(f"   Aprovadas: {stats['aprovadas']}")
        print(f"   Reprovadas: {stats['reprovadas']}")

        print()
        print("=" * 50)
        print("  ✅ Teste concluido com sucesso!")
        print("=" * 50)

    except ConnectionRefusedError:
        print("   ❌ Conexao recusada!")
        print()
        print("   O banco PostgreSQL esta rodando?")
        print("   Execute: bash scripts/setup_banco.sh")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        print()
        print("   Verifique se o Docker esta rodando e o banco foi iniciado.")
        print("   Execute: bash scripts/setup_banco.sh")
        sys.exit(1)
    finally:
        await repo.desconectar()


if __name__ == "__main__":
    asyncio.run(testar())
