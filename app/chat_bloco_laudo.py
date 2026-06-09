def _cmd_laudo(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    if not args:
        print_error("Uso: /laudo <id_da_sessao>")
        return True
    from app.repositorio_medicoes import RepositorioMedicoesPG
    from app.laudo_tecnico import gerar_diagnostico, gerar_laudo_markdown, salvar_laudo
    from app.captura_serial import SessaoConfig
    repo = RepositorioMedicoesPG(ctx.config.banco)
    try:
        asyncio.run(repo.conectar())
        sessao = asyncio.run(repo.buscar_sessao(args.strip()))
        if not sessao:
            print_error(f"Sessao nao encontrada: {args.strip()}")
            asyncio.run(repo.desconectar())
            return True
        snapshots = asyncio.run(repo.buscar_snapshots_da_sessao(args.strip()))
        asyncio.run(repo.desconectar())
    except Exception as exc:
        print_error(f"Erro ao buscar dados: {exc}")
        return True
    if not snapshots:
        print_error("Nenhum snapshot encontrado para esta sessao.")
        return True
    config = SessaoConfig(fabricante=sessao.get("fabricante") or "", modelo=sessao.get("modelo") or "", numero_serie=sessao.get("numero_serie") or "", tipo_maquina=sessao.get("tipo_maquina") or "", tipo_motor=sessao.get("tipo_motor") or "", sistema_transmissao=sessao.get("sistema_transmissao") or "", curso_nominal_mm=sessao.get("curso_nominal_mm"), curso_min_mm=sessao.get("curso_min_mm"), curso_max_mm=sessao.get("curso_max_mm"), tipo_coleta=sessao.get("tipo_coleta") or "desempenho", peca_substituida=sessao.get("peca_substituida") or "", observacoes=sessao.get("observacoes") or "", tecnico=sessao.get("tecnico") or "", porta_serial=sessao.get("porta_serial") or "", baudrate=sessao.get("baudrate") or 115200, duracao_seg=sessao.get("duracao_seg") or 30.0)
    diagnostico = gerar_diagnostico(snapshots, config)
    laudo_dir = ctx.base_dir / "reports" / "laudos"
    laudo_md = gerar_laudo_markdown(args.strip(), config, snapshots, diagnostico)
    caminho_laudo = salvar_laudo(laudo_md, args.strip(), laudo_dir)
    print_diagnostico_completo(diagnostico)
    print_laudo_salvo(str(caminho_laudo))
    return True
