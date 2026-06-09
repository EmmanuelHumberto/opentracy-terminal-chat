def _cmd_medicoes(*, ctx: ChatContext, **_: Any) -> bool:
    """Lista sessoes de medicao salvas."""
    from app.repositorio_medicoes import RepositorioMedicoesPG
    from app.renderer import _console
    from rich.table import Table

    repo = RepositorioMedicoesPG(ctx.config.banco)

    try:
        asyncio.run(repo.conectar())
        sessoes = asyncio.run(repo.listar_sessoes())
        asyncio.run(repo.desconectar())
    except Exception as exc:
        print_error(f"Erro ao listar sessoes: {exc}")
        return True

    if not sessoes:
        print_info("Nenhuma sessao de medicao encontrada.")
        return True

    table = Table(title="Sessoes de Medicao", box=None, show_header=True)
    table.add_column("ID", style="bold cyan", width=22)
    table.add_column("Fabricante", width=14)
    table.add_column("Modelo", width=18)
    table.add_column("Tipo", width=12)
    table.add_column("Snapshots", justify="right", width=10)
    table.add_column("Status", width=10)
    table.add_column("Data", width=20)

    for s in sessoes:
        status = "✅" if s.get("aprovado") else "❌" if s.get("aprovado") == 0 else "⏳"
        table.add_row(
            s["id"][:20],
            s.get("fabricante") or "-",
            s.get("modelo") or "-",
            s.get("tipo_coleta") or "-",
            str(s.get("total_snapshots", 0)),
            status,
            (s.get("created_at") or "-")[:19],
        )

    _console.print()
    _console.print(table)
    _console.print()
    print_info("Use /medicao <id> para ver detalhes ou /laudo <id> para gerar laudo.")
    return True
