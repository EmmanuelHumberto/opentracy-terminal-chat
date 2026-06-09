#!/usr/bin/env python3
"""Executa a migracao SQL da base de conhecimento usando asyncpg.

Uso:
    uv run python scripts/run_migration.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg


MIGRACAO = Path(__file__).resolve().parent / "sql" / "migracao_v2.sql"


async def main() -> None:
    if not MIGRACAO.is_file():
        print(f"Erro: arquivo de migracao nao encontrado: {MIGRACAO}")
        sys.exit(1)

    sql = MIGRACAO.read_text(encoding="utf-8")

    print(f"Conectando em localhost:5432/ligadoai como ligadoai...")
    try:
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            database="ligadoai",
            user="ligadoai",
            password="ligadoai",
        )
    except Exception as exc:
        print(f"Erro ao conectar: {exc}")
        print("Verifique se o PostgreSQL esta rodando: pg_isready -h localhost")
        sys.exit(1)

    try:
        await conn.execute(sql)
        print("Migracao executada com sucesso.")

        # Verifica se as tabelas foram criadas
        tabelas = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('documentos_conhecimento', 'chunks')
            ORDER BY table_name
        """)
        for t in tabelas:
            print(f"  ✅ Tabela {t['table_name']} criada")

    except Exception as exc:
        print(f"Erro na migracao: {exc}")
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
