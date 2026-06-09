def _cmd_capturar(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Inicia captura de metricas da maquina via serial."""
    from app.captura_serial import SessaoConfig
    from app.formulario_coleta import preencher_configuracao
    from app.laudo_tecnico import gerar_diagnostico, gerar_laudo_markdown, salvar_laudo
    from app.repositorio_medicoes import RepositorioMedicoesPG

    porta = args.strip() or "/dev/ttyACM0"

    try:
        config = preencher_configuracao(porta)
    except KeyboardInterrupt:
        print_info("Captura cancelada.")
        return True

    sessao_id = datetime.now().strftime("med_%Y%m%d_%H%M%S")
    repo = RepositorioMedicoesPG(ctx.config.banco)

    try:
        asyncio.run(repo.conectar())
        asyncio.run(repo.criar_sessao_com_config(sessao_id, config))

        resultado = _executar_captura_com_tratamento(config, repo, sessao_id)

        if resultado is None:
            print_info("Operacao finalizada sem gerar laudo.")
            asyncio.run(repo.desconectar())
            return True

        if "snapshots" in resultado:
            validos = resultado["snapshots"]
            diagnostico = gerar_diagnostico(validos, config)
            asyncio.run(repo.finalizar_sessao(
                sessao_id,
                diagnostico["aprovado"],
                json.dumps(diagnostico, ensure_ascii=False, default=str),
            ))

            print_diagnostico_completo(diagnostico)

            laudo_dir = ctx.base_dir / "reports" / "laudos"
            laudo_md = gerar_laudo_markdown(sessao_id, config, validos, diagnostico)
            caminho_laudo = salvar_laudo(laudo_md, sessao_id, laudo_dir)
            print_laudo_salvo(str(caminho_laudo))

        asyncio.run(repo.desconectar())

    except Exception as exc:
        print_error(f"Erro no fluxo de captura: {exc}")
        try:
            asyncio.run(repo.desconectar())
        except Exception:
            pass
        return True

    return True
