def _cmd_medicao(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Mostra detalhes de uma sessao de medicao."""
    if not args:
        print_error("Uso: /medicao <id_da_sessao>")
        return True

    from app.repositorio_medicoes import RepositorioMedicoesPG
    from app.renderer import _console
    from rich.table import Table
    from rich.panel import Panel

    repo = RepositorioMedicoesPG(ctx.config.banco)

    try:
        asyncio.run(repo.conectar())
        sessao = asyncio.run(repo.buscar_sessao(args.strip()))
        asyncio.run(repo.desconectar())
    except Exception as exc:
        print_error(f"Erro ao buscar sessao: {exc}")
        return True

    if not sessao:
        print_error(f"Sessao nao encontrada: {args.strip()}")
        return True

    _console.print()
    _console.print(Panel.fit(
        f"[bold]Sessao: {sessao['id']}[/]",
        border_style="cyan",
    ))

    table = Table(box=None, show_header=False)
    table.add_column("Campo", style="bold", width=20)
    table.add_column("Valor")

    for campo, valor in [
        ("Fabricante", sessao.get("fabricante")),
        ("Modelo", sessao.get("modelo")),
        ("N Serie", sessao.get("numero_serie")),
        ("Tipo Maquina", sessao.get("tipo_maquina")),
        ("Motor", sessao.get("tipo_motor")),
        ("Transmissao", sessao.get("sistema_transmissao")),
        ("Curso", f"{sessao.get('curso_nominal_mm', '-')}mm"),
        ("Tipo", sessao.get("tipo_coleta")),
        ("Peca Subst.", sessao.get("peca_substituida")),
        ("Tecnico", sessao.get("tecnico")),
        ("Duracao", f"{sessao.get('duracao_seg', 0):.1f}s"),
        ("Snapshots", str(sessao.get("total_snapshots", 0))),
        ("Hall", str(sessao.get("total_hall", 0))),
        ("Power", str(sessao.get("total_power", 0))),
        ("Vibracao", str(sessao.get("total_vibration", 0))),
        ("Curso", str(sessao.get("total_course", 0))),
        ("Aprovado", "✅ Sim" if sessao.get("aprovado") else "❌ Nao" if sessao.get("aprovado") == 0 else "⏳ Pendente"),
        ("Data", sessao.get("created_at", "")[:19]),
    ]:
        if valor is not None and valor != "" and valor != "-":
            table.add_row(campo, str(valor))

    _console.print()
    _console.print(table)
    _console.print()
    return True
