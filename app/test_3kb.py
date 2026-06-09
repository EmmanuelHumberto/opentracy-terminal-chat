def _executar_captura_com_tratamento(config, repo, sessao_id):
    from app.captura_serial import capturar
    if not _verificar_conexao_serial(config.porta_serial, config.baudrate):
        print_error(f"Porta serial nao encontrada: {config.porta_serial}")
        print_info("Verifique se o cabo USB esta conectado e o firmware esta rodando.")
        opcao = _perguntar_opcao("Deseja tentar novamente ou cancelar?", ["tentar", "cancelar"], "tentar")
        if opcao == "tentar":
            return _executar_captura_com_tratamento(config, repo, sessao_id)
        return None
    print_inicio_captura(config)
    inicio = time.monotonic()
    snapshots_brutos = []
    falha_critica = False
    try:
        def callback(snapshot):
            snapshots_brutos.append(snapshot)
            if not config.verticais or snapshot.get("type") in config.verticais:
                print_snapshot_capturado(snapshot)
        snapshots_brutos = capturar(porta=config.porta_serial, baudrate=config.baudrate, duracao_seg=config.duracao_seg, callback=callback)
    except KeyboardInterrupt:
        print_info("\n\nCaptura interrompida pelo usuario.")
    except FileNotFoundError:
        falha_critica = True
        print_error(f"\nPorta serial {config.porta_serial} nao encontrada.")
    except PermissionError:
        falha_critica = True
        print_error(f"\nSem permissao para {config.porta_serial}.")
    except Exception as exc:
        falha_critica = True
        print_error(f"\nErro: {exc}")
    duracao = time.monotonic() - inicio
    print_fim_captura(len(snapshots_brutos), duracao)
    if snapshots_brutos:
        print_info("Validando integridade dos snapshots...")
        validos, rejeitados = _validar_snapshots(snapshots_brutos)
        if rejeitados:
            print_error(f"{len(rejeitados)} snapshots rejeitados.")
        print_info(f"  {len(validos)} validos, {len(rejeitados)} rejeitados")
    else:
        validos, rejeitados = [], []
    if falha_critica or not validos:
        print_info("\nNenhum dado valido foi capturado.")
        opcao = _perguntar_opcao("O que deseja fazer?", ["descartar", "repetir", "salvar_parciais"], "repetir")
        if opcao == "descartar":
            asyncio.run(repo.deletar_sessao(sessao_id))
            print_info("Dados descartados.")
            return None
        elif opcao == "repetir":
            print_info("Repetindo medicao...")
            return _executar_captura_com_tratamento(config, repo, sessao_id)
        elif opcao == "salvar_parciais":
            print_info("Salvando dados parciais...")
            return None
    return {"snapshots": validos, "rejeitados": rejeitados, "sessao_id": sessao_id, "duracao": duracao}
