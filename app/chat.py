"""Loop principal do chat.

Coordena: input do usuario, command_router, memoria, cliente HTTP,
renderizacao e logs.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.command_router import CommandRouter
from app.config import Config
from app.logger import JsonlLogger
from app.memory import SessionManager
from app.opentracy_client import OpenTracyClient, OpenTracyError
from app.renderer import (
    print_assistant_message,
    print_divider,
    print_error,
    print_help,
    print_info,
    print_memory_status,
    print_session_list,
    print_status,
    print_status_bar,
    print_success,
    print_thinking,
    print_trace_id,
    print_warning,
    print_welcome,
    clear_screen,
    prompt_input,
    print_snapshot_capturado,
    print_inicio_captura,
    print_fim_captura,
    print_diagnostico_completo,
    print_laudo_salvo,
    _console,
)


class ChatContext:
    """Estado compartilhado entre o loop de chat e os comandos."""

    def __init__(
        self,
        config: Config,
        client: OpenTracyClient,
        sessions: SessionManager,
        logger: JsonlLogger,
        router: CommandRouter,
        auth_token: str,
    ) -> None:
        self.config = config
        self.client = client
        self.sessions = sessions
        self.logger = logger
        self.router = router
        self.auth_token = auth_token
        self.last_trace_id: Optional[str] = None
        self.base_dir: Path = Path(__file__).resolve().parent.parent
        self.corpus_client: Any = None  # CorpusClient — lazy init no startup
        self.runtime_proc: Any = None   # subprocess.Popen do runtime (se auto-iniciado)


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def _format_messages(messages: list[dict]) -> str:
    """Formata mensagens para o prompt de resumo."""
    lines = []
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content", "")
        lines.append(f"[{role}]: {content[:200]}")
    return "\n".join(lines)


def _apply_summary(ctx: ChatContext, session: Any, summary: str) -> None:
    """Aplica o resumo e limpa historico recente."""
    session.save_summary(summary)
    session.trim_history_after_summary(keep_last=2)
    ctx.logger.log_event(
        event="summary_applied",
        session_id=ctx.sessions.current_id,
        metadata={"summary_length": len(summary)},
    )


# ---------------------------------------------------------------------------
# Comandos basicos
# ---------------------------------------------------------------------------


def _cmd_ajuda(*, ctx: ChatContext, **_: Any) -> bool:
    print_help()
    return True


def _cmd_sair(*, ctx: ChatContext, **_: Any) -> bool:
    return False


def _cmd_limpar(*, ctx: ChatContext, **_: Any) -> bool:
    clear_screen()
    return True


def _cmd_resumo(*, ctx: ChatContext, **_: Any) -> bool:
    session = ctx.sessions.current
    messages = session.get_all()
    if not messages:
        print_info("Nenhuma mensagem para resumir.")
        return True

    previous = session.load_summary()
    recent = session.get_recent(ctx.config.memory.max_history)

    prompt_parts = [
        "Voce resume conversas tecnicas em portugues.",
        "Mantenha assunto principal, decisoes, dados tecnicos, pendencias e proximos passos.",
        f"Limite: {ctx.config.memory.summary_max_chars} caracteres, 3 paragrafos curtos.",
    ]
    if previous:
        prompt_parts.append(f"\nResumo anterior:\n{previous}")
    prompt_parts.append(f"\nNovas mensagens:\n{_format_messages(recent)}")
    prompt_parts.append("\nResumo atualizado:")

    summary_prompt = "\n".join(prompt_parts)
    print_info("Gerando resumo...")

    try:
        result = ctx.client.chat(summary_prompt, auth_token=ctx.auth_token)
    except OpenTracyError as exc:
        print_error(f"Falha ao gerar resumo: {exc}")
        return True

    summary = (result.get("response") or "").strip()
    if summary:
        _apply_summary(ctx, session, summary)
        print_info("Resumo atualizado. Historico compactado.")
    else:
        print_error("Resumo veio vazio.")
    return True


def _cmd_memoria(*, ctx: ChatContext, **_: Any) -> bool:
    session = ctx.sessions.current
    messages = session.get_all()
    summary = session.load_summary()
    print_memory_status(
        session_id=ctx.sessions.current_id,
        message_count=len(messages),
        has_summary=summary is not None,
        history_file=str(session.history_path),
        summary_file=str(session.summary_path) if summary else None,
    )
    return True


def _cmd_novo(*, ctx: ChatContext, **_: Any) -> bool:
    sid = ctx.sessions.create_session()
    print_info(f"Nova sessao: {sid}")
    return True


def _cmd_listar(*, ctx: ChatContext, **_: Any) -> bool:
    sessions = ctx.sessions.list_sessions()
    print_session_list(sessions)
    return True


def _cmd_carregar(*, args: str, ctx: ChatContext, **_: Any) -> bool:
    if not args:
        print_error("Uso: /carregar <id_da_sessao>")
        return True
    success = ctx.sessions.load_session(args.strip())
    if success:
        print_info(f"Sessao carregada: {args.strip()}")
    else:
        print_error(f"Sessao nao encontrada: {args.strip()}")
    return True


def _cmd_status(*, ctx: ChatContext, **_: Any) -> bool:
    backend_ok = ctx.client.check_backend_health()
    runtime_ok = ctx.client.check_runtime_health()
    agent_ok = False
    try:
        agents = ctx.client.list_agents(ctx.auth_token)
        agent_ok = any(a.get("id") == ctx.config.opentracy.agent_id for a in agents)
    except OpenTracyError:
        pass
    token_ok = bool(ctx.auth_token)
    print_status(
        backend_ok=backend_ok,
        runtime_ok=runtime_ok,
        agent_ok=agent_ok,
        token_ok=token_ok,
        agent_id=ctx.config.opentracy.agent_id,
        last_trace=ctx.last_trace_id,
    )
    return True


# ------------------------------------------------------------------ #
# Inferencia de frontmatter a partir da estrutura de diretorios
# ------------------------------------------------------------------ #

# Mapeia nome do diretorio de nivel 1 → tipo para o frontmatter
_TIPO_POR_DIRETORIO: dict[str, str] = {
    "01-motores": "motor",
    "02-sistemas-mecanicos": "sistema",
    "03-maquinas": "maquina",
    "04-cartuchos": "documento",
    "05-fontes": "documento",
    "06-manuais": "manual",
    "07-baterias": "documento",
    "08-medicoes": "documento",
    "09-diagnosticos": "documento",
    "10-artigos-cientificos": "artigo",
    "desenhos-tecnicos": "documento",
}

# Formatos que o document_server consegue converter
_FORMATOS_CONVERSIVEIS = {".pdf", ".docx", ".xlsx", ".txt", ".jpg", ".png", ".bmp", ".tiff", ".zip"}
_CATEGORIAS_NAO_FABRICANTE = {
    "brushless",
    "coreless",
    "nucleo",
    "rotativa",
    "bobina",
    "pen",
    "direct-drive-fixo",
    "direct-drive-variavel",
    "swash-drive-fixo",
    "swash-drive-variavel",
}
_FABRICANTES_POR_TEXTO = {
    "portescap": "Portescap",
    "faulhaber": "Faulhaber",
    "maxon": "Maxon",
    "dklab": "dklab",
    "cheyenne": "cheyenne",
}


def _inferir_frontmatter(caminho_arquivo: Path, raiz: Path, conteudo: str = "") -> dict[str, str]:
    """Infere frontmatter YAML a partir da estrutura de diretorios.

    Ex: knowledge/01-motores/brushless/cheyenne/hawk.pdf
        → {fabricante: cheyenne, modelo: hawk, tipo: motor}
    """
    try:
        rel = caminho_arquivo.relative_to(raiz)
    except ValueError:
        rel = caminho_arquivo

    partes = rel.parts

    # Tipo: primeiro nivel de diretorio (ex: "01-motores" → "motor")
    tipo = "documento"
    if len(partes) >= 1:
        tipo = _TIPO_POR_DIRETORIO.get(partes[0], "documento")

    # Fabricante: penultimo nivel se houver 3+ niveis, exceto categorias
    # tecnicas como "coreless"/"brushless", que nao sao fabricantes.
    fabricante = "desconhecido"
    if len(partes) >= 3:
        candidato = partes[-2]
        if candidato.lower() not in _CATEGORIAS_NAO_FABRICANTE:
            fabricante = candidato

    if fabricante == "desconhecido" and conteudo:
        conteudo_lower = conteudo.lower()
        for marcador, nome in _FABRICANTES_POR_TEXTO.items():
            if marcador in conteudo_lower:
                fabricante = nome
                break

    # Modelo: nome do arquivo sem extensao
    modelo = caminho_arquivo.stem

    return {
        "fabricante": fabricante,
        "modelo": modelo,
        "tipo": tipo,
    }


def _gerar_md_com_frontmatter(texto: str, frontmatter: dict[str, str]) -> str:
    """Gera um Markdown com frontmatter YAML a partir de texto puro."""
    linhas_yaml = [f"{k}: {v}" for k, v in frontmatter.items()]
    yaml_str = "\n".join(linhas_yaml)
    return f"---\n{yaml_str}\n---\n\n{texto}"


def _converter_arquivos(alvo: Path, ctx: ChatContext) -> list[Path]:
    """Converte PDF/DOCX/XLSX/ZIP/etc para .md e retorna a lista de .md resultantes.

    Para diretorios, usa convert_directory() que preserva a estrutura de subpastas.
    Para arquivos unicos, usa convert_file().
    """
    import tempfile

    from ligadoai_tools.document_server import convert_directory, convert_file

    saida = Path(tempfile.mkdtemp(prefix="cous_index_"))
    raiz_conhecimento = ctx.base_dir / "knowledge"

    if alvo.is_dir():
        print_info(f"Convertendo documentos de {alvo}...")
        resultado = convert_directory(alvo, saida, recursive=True)
    else:
        print_info(f"Convertendo {alvo.name}...")
        resultado = convert_file(alvo, saida)

    erros = resultado.get("errors", 0)
    if erros > 0:
        for err in resultado.get("error_details", []):
            msg = err.get("error", {}).get("message", "desconhecido")
            print_error(f"  Erro: {msg}")

    convertidos = resultado.get("converted", 0)
    print_info(f"Convertidos: {convertidos} arquivos, {erros} erros")

    if convertidos == 0:
        return []

    # Coleta .md gerados
    arquivos_md = sorted(saida.rglob("*.md"))
    if not arquivos_md:
        arquivos_md = sorted(saida.rglob("*.txt"))

    # Para cada .md sem frontmatter, injeta frontmatter inferido
    for md_file in arquivos_md:
        conteudo = md_file.read_text(encoding="utf-8")
        if conteudo.startswith("---"):
            continue  # ja tem frontmatter

        # Tenta inferir da estrutura original (caminho relativo dentro de knowledge/)
        fm = _inferir_frontmatter(md_file, saida, conteudo)
        novo_conteudo = _gerar_md_com_frontmatter(conteudo, fm)
        md_file.write_text(novo_conteudo, encoding="utf-8")

    return arquivos_md


def _cmd_indexar(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Indexa documentos de conhecimento no PG e recarrega FAISS do OpenTracy.

    Modos:
        /indexar                          — converte knowledge/ e indexa tudo
        /indexar <arquivo.md>             — valida frontmatter YAML e indexa
        /indexar <pasta/>                 — indexa .md da pasta (ou converte se tiver PDFs)
        /indexar <arquivo.pdf>            — converte + infere frontmatter + indexa
        /indexar --dry-run <arquivo>      — apenas valida, sem persistir
    """
    dry_run = False
    caminho_str = args.strip()

    if caminho_str.startswith("--dry-run"):
        dry_run = True
        caminho_str = caminho_str[len("--dry-run"):].strip()

    # Modo legado: sem argumentos → processa knowledge/
    if not caminho_str:
        alvo = ctx.base_dir / "knowledge"
    else:
        alvo = Path(caminho_str)
        if not alvo.is_absolute():
            alvo = Path.cwd() / alvo
        alvo = alvo.resolve()

    if not alvo.exists():
        print_error(f"Arquivo ou pasta nao encontrado: {alvo}")
        return True

    # Determina se precisa de conversao
    precisa_conversao = False
    if alvo.is_dir():
        # Verifica se ha arquivos nao-.md na pasta
        for ext in _FORMATOS_CONVERSIVEIS:
            if list(alvo.rglob(f"*{ext}")):
                precisa_conversao = True
                break
    elif alvo.suffix.lower() in _FORMATOS_CONVERSIVEIS:
        precisa_conversao = True

    # Fase 1: Conversao (se necessario)
    if precisa_conversao:
        arquivos_md = _converter_arquivos(alvo, ctx)
        if not arquivos_md:
            print_error("Nenhum arquivo convertido.")
            return True
    else:
        # Coleta .md existentes
        if alvo.is_dir():
            arquivos_md = sorted(alvo.rglob("*.md"))
        elif alvo.suffix == ".md":
            arquivos_md = [alvo]
        else:
            print_error(f"Formato nao suportado: {alvo.suffix}. Use .md, .pdf, .docx, .xlsx, .zip")
            return True

    if not arquivos_md:
        print_error("Nenhum arquivo .md encontrado.")
        return True

    # Fase 2: Validacao
    from app.validador_conhecimento import ValidadorConhecimento, formatar_resultado

    validador = ValidadorConhecimento()
    aprovados: list[Any] = []
    rejeitados = 0
    avisos = 0

    for arquivo in arquivos_md:
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except Exception as exc:
            print_error(f"  Erro ao ler {arquivo.name}: {exc}")
            rejeitados += 1
            continue

        resultado = validador.validar(conteudo, source_path=str(arquivo))
        saida = formatar_resultado(resultado, source_path=arquivo.name)
        print_info(saida)

        if resultado.rejeitado:
            rejeitados += 1
        elif resultado.avisos:
            avisos += 1
            if not dry_run:
                aprovados.append((resultado, str(arquivo)))
        elif resultado.aprovado:
            if not dry_run:
                aprovados.append((resultado, str(arquivo)))

    print_info(f"Total: {len(aprovados)} aprovados, {avisos} avisos, {rejeitados} rejeitados")

    if dry_run:
        print_info("Dry-run: nada foi persistido.")
        return True

    if not aprovados:
        print_info("Nenhum documento aprovado para indexar.")
        return True

    # Fase 3: Persistencia no PG + reload FAISS
    async def _persistir_e_reload() -> None:
        from app.knowledge_syncer import KnowledgeSyncer
        from app.corpus_client import CorpusClient, CorpusReloadError

        syncer = KnowledgeSyncer(ctx.config.banco, ctx.config.corpus)
        try:
            await syncer.conectar()

            for resultado, source_path in aprovados:
                doc_id = await syncer.sincronizar(resultado, source_path=source_path)
                if doc_id:
                    print_success(f"  Indexado: {source_path} → {doc_id[:8]}...")
                else:
                    print_error(f"  Falha ao indexar: {source_path}")
        finally:
            await syncer.desconectar()

        corpus = CorpusClient(ctx.config.banco, ctx.config.corpus)
        try:
            result = await corpus.reload_from_pg()
            print_success(
                f"FAISS recarregado: {result['loaded']} chunks, "
                f"dim={result['dimension']}"
            )
        except CorpusReloadError as exc:
            print_error(f"Falha ao recarregar FAISS: {exc}")
            print_warning(
                "Os documentos foram persistidos no PG, mas o FAISS nao "
                "foi atualizado. Tente /indexar novamente ou verifique "
                "se o OpenTracy runtime esta rodando."
            )
        finally:
            await corpus.close()

    try:
        asyncio.run(_persistir_e_reload())
    except Exception as exc:
        print_error(f"Erro na indexacao: {exc}")
        return True

    ctx.logger.log_event(
        event="indexar",
        session_id=ctx.sessions.current_id,
        metadata={"arquivos": len(aprovados), "dry_run": dry_run},
    )
    print_success("Base de conhecimento indexada com sucesso!")
    return True


def _cmd_indexados(*, ctx: ChatContext, **_: Any) -> bool:
    """Lista documentos indexados no banco de conhecimento (PG)."""
    async def _listar() -> list[dict]:
        from app.knowledge_syncer import KnowledgeSyncer
        syncer = KnowledgeSyncer(ctx.config.banco, ctx.config.corpus)
        try:
            await syncer.conectar()
            return await syncer.listar_documentos()
        finally:
            await syncer.desconectar()

    try:
        docs = asyncio.run(_listar())
    except Exception as exc:
        print_error(f"Erro ao consultar banco: {exc}")
        return True

    if not docs:
        print_info("Nenhum documento indexado.")
        return True

    from rich.table import Table
    table = Table(title="Documentos Indexados", box=None, show_header=True)
    table.add_column("ID", style="bold cyan", width=10)
    table.add_column("Fabricante", width=14)
    table.add_column("Modelo", width=18)
    table.add_column("Tipo", width=12)
    table.add_column("Status", width=10)
    table.add_column("Chunks", justify="right", width=7)
    table.add_column("Data", width=20)

    for d in docs:
        status_icon = {"aprovado": "✅", "aviso": "⚠️", "rejeitado": "❌"}.get(d["status"], "❓")
        table.add_row(
            d["id"][:8],
            d.get("fabricante") or "-",
            d.get("modelo") or "-",
            d.get("tipo") or "-",
            status_icon,
            str(d.get("n_chunks", 0)),
            (d.get("indexado_em") or "-")[:19],
        )

    _console.print()
    _console.print(table)
    _console.print()
    print_info(f"Total: {len(docs)} documento(s)")
    return True


def _cmd_remover(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Remove um documento do banco de conhecimento e recarrega FAISS.

    Uso: /remover <id_do_documento>
    """
    doc_id = args.strip()
    if not doc_id:
        print_error("Uso: /remover <id_do_documento>")
        print_info("Use /indexados para ver os IDs disponiveis.")
        return True

    async def _remover_e_reload() -> None:
        from app.knowledge_syncer import KnowledgeSyncer
        from app.corpus_client import CorpusClient, CorpusReloadError

        syncer = KnowledgeSyncer(ctx.config.banco, ctx.config.corpus)
        try:
            await syncer.conectar()
            removido = await syncer.remover_documento(doc_id)
        finally:
            await syncer.desconectar()

        if not removido:
            print_error(f"Documento nao encontrado: {doc_id}")
            return

        print_success(f"Documento removido: {doc_id[:8]}...")

        # Recarrega FAISS
        corpus = CorpusClient(ctx.config.banco, ctx.config.corpus)
        try:
            result = await corpus.reload_from_pg()
            print_success(
                f"FAISS recarregado: {result['loaded']} chunks, "
                f"dim={result['dimension']}"
            )
        except CorpusReloadError as exc:
            print_error(f"Falha ao recarregar FAISS: {exc}")
            print_warning("O documento foi removido do PG, mas o FAISS nao foi atualizado.")
        finally:
            await corpus.close()

    try:
        asyncio.run(_remover_e_reload())
    except ValueError as exc:
        print_error(str(exc))
    except Exception as exc:
        print_error(f"Erro ao remover documento: {exc}")

    ctx.logger.log_event(
        event="remover_documento",
        session_id=ctx.sessions.current_id,
        metadata={"doc_id": doc_id},
    )
    return True


def _cmd_tools(*, ctx: ChatContext, **_: Any) -> bool:
    """Lista as MCP tools registradas no agente."""
    try:
        tools = ctx.client.list_tools(ctx.auth_token)
    except OpenTracyError as exc:
        print_error(f"Erro ao consultar tools: {exc}")
        return True

    if not tools:
        print_info("Nenhuma MCP tool registrada.")
        return True

    from app.renderer import _console
    from rich.table import Table
    table = Table(title="MCP Tools", box=None, show_header=True)
    table.add_column("Tool", style="bold cyan")
    table.add_column("Descricao")
    for t in tools:
        name = t.get("tool_name") or t.get("name") or t.get("qualified_name", "?")
        table.add_row(name, t.get("description", "-"))
    _console.print()
    _console.print(table)
    _console.print()
    return True


# ---------------------------------------------------------------------------
# Utilitarios de captura
# ---------------------------------------------------------------------------


def _perguntar_opcao(mensagem: str, opcoes: list[str], default: str = "") -> str:
    """Pergunta ao usuario qual opcao deseja."""
    opcoes_str = "(" + "/".join(opcoes) + ")"
    prompt = f"{mensagem} {opcoes_str} [{default}]: " if default else f"{mensagem} {opcoes_str}: "
    _console.print()
    _console.print(f"[bold yellow]{prompt}[/]", end="")
    resposta = input().strip().lower()
    if not resposta and default:
        return default
    if resposta in opcoes:
        return resposta
    _console.print(f"[red]Opcao invalida. Escolha entre: {', '.join(opcoes)}[/]")
    return _perguntar_opcao(mensagem, opcoes, default)


def _validar_snapshots(snapshots: list[dict]) -> tuple[list[dict], list[dict]]:
    """Valida integridade dos snapshots."""
    validos = []
    rejeitados = []
    for s in snapshots:
        erros = []
        tipo = s.get("type")
        if not tipo:
            erros.append("sem tipo")
            rejeitados.append(s)
            continue
        if s.get("timestamp_us") is None:
            erros.append("sem timestamp")
        if tipo == "hall_snapshot" and not isinstance(s.get("frequency_hz"), (int, float)):
            erros.append("frequency_hz invalido")
        elif tipo == "power_snapshot" and not isinstance(s.get("bus_voltage_mv"), (int, float)):
            erros.append("bus_voltage_mv invalido")
        elif tipo == "vibration_snapshot" and not isinstance(s.get("rms_norm_mg"), (int, float)):
            erros.append("rms_norm_mg invalido")
        elif tipo == "course_snapshot" and not isinstance(s.get("course_mm"), (int, float)):
            erros.append("course_mm invalido")
        if erros:
            s["_erros_validacao"] = erros
            rejeitados.append(s)
        else:
            validos.append(s)
    return validos, rejeitados


def _verificar_conexao_serial(porta: str, baudrate: int) -> bool:
    """Verifica se a porta serial esta acessivel."""
    import os
    try:
        return os.path.exists(porta)
    except Exception:
        return False


def _executar_captura_com_tratamento(config: Any, repo: Any, sessao_id: str) -> Optional[dict]:
    """Executa a captura com tratamento de erros e opcoes pos-falha."""
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
    snapshots_brutos: list[dict] = []
    falha_critica = False

    try:
        def callback(snapshot: dict) -> None:
            snapshots_brutos.append(snapshot)
            verticais = getattr(config, "verticais", None)
            if not verticais or snapshot.get("type") in verticais:
                print_snapshot_capturado(snapshot)

        snapshots_brutos = capturar(
            porta=config.porta_serial,
            baudrate=config.baudrate,
            duracao_seg=config.duracao_seg,
            callback=callback,
        )
    except KeyboardInterrupt:
        print_info("\n\nCaptura interrompida pelo usuario.")
    except FileNotFoundError:
        falha_critica = True
        print_error(f"\nPorta serial {config.porta_serial} nao encontrada ou desconectada.")
    except PermissionError:
        falha_critica = True
        print_error(f"\nSem permissao de acesso a porta serial {config.porta_serial}.")
    except Exception as exc:
        falha_critica = True
        print_error(f"\nErro inesperado: {exc}")

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


# ---------------------------------------------------------------------------
# Comandos de medicao
# ---------------------------------------------------------------------------


def _cmd_capturar(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Inicia captura de metricas da maquina via serial."""
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


def _cmd_medicoes(*, ctx: ChatContext, **_: Any) -> bool:
    """Lista sessoes de medicao salvas."""
    from app.repositorio_medicoes import RepositorioMedicoesPG
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


def _cmd_medicao(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Mostra detalhes de uma sessao de medicao."""
    if not args:
        print_error("Uso: /medicao <id_da_sessao>")
        return True

    from app.repositorio_medicoes import RepositorioMedicoesPG
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
    _console.print(Panel.fit(f"[bold]Sessao: {sessao['id']}[/]", border_style="cyan"))

    info_table = Table(box=None, show_header=False)
    info_table.add_column("Campo", style="bold", width=20)
    info_table.add_column("Valor")

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
        ("Data", (sessao.get("created_at") or "")[:19]),
    ]:
        if valor is not None and valor != "" and valor != "-":
            info_table.add_row(campo, str(valor))

    _console.print()
    _console.print(info_table)
    _console.print()
    return True


def _cmd_laudo(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Gera laudo tecnico de uma sessao."""
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

    config = SessaoConfig(
        fabricante=sessao.get("fabricante") or "",
        modelo=sessao.get("modelo") or "",
        numero_serie=sessao.get("numero_serie") or "",
        tipo_maquina=sessao.get("tipo_maquina") or "",
        tipo_motor=sessao.get("tipo_motor") or "",
        sistema_transmissao=sessao.get("sistema_transmissao") or "",
        curso_nominal_mm=sessao.get("curso_nominal_mm"),
        curso_min_mm=sessao.get("curso_min_mm"),
        curso_max_mm=sessao.get("curso_max_mm"),
        tipo_coleta=sessao.get("tipo_coleta") or "desempenho",
        peca_substituida=sessao.get("peca_substituida") or "",
        observacoes=sessao.get("observacoes") or "",
        tecnico=sessao.get("tecnico") or "",
        porta_serial=sessao.get("porta_serial") or "",
        baudrate=sessao.get("baudrate") or 115200,
        duracao_seg=sessao.get("duracao_seg") or 30.0,
    )

    diagnostico = gerar_diagnostico(snapshots, config)
    laudo_dir = ctx.base_dir / "reports" / "laudos"
    laudo_md = gerar_laudo_markdown(args.strip(), config, snapshots, diagnostico)
    caminho_laudo = salvar_laudo(laudo_md, args.strip(), laudo_dir)

    print_diagnostico_completo(diagnostico)
    print_laudo_salvo(str(caminho_laudo))
    return True


# ---------------------------------------------------------------------------
# Builder e loop principal
# ---------------------------------------------------------------------------


def build_router() -> CommandRouter:
    """Constroi e registra todos os comandos no roteador."""
    router = CommandRouter()
    router.register("ajuda", _cmd_ajuda, description="Mostra ajuda")
    router.register("sair", _cmd_sair, description="Encerra o programa")
    router.register("limpar", _cmd_limpar, description="Limpa a tela")
    router.register("resumo", _cmd_resumo, description="Forca atualizacao do resumo")
    router.register("memoria", _cmd_memoria, description="Status da memoria")
    router.register("novo", _cmd_novo, description="Nova sessao")
    router.register("listar", _cmd_listar, description="Lista sessoes")
    router.register("carregar", _cmd_carregar, description="Carrega sessao")
    router.register("status", _cmd_status, description="Status do OpenTracy")
    router.register("tools", _cmd_tools, description="Lista MCP tools")
    router.register("indexar", _cmd_indexar, description="Indexa documentos no PG + FAISS")
    router.register("indexados", _cmd_indexados, description="Lista documentos indexados")
    router.register("remover", _cmd_remover, description="Remove documento do indice")
    router.register("capturar", _cmd_capturar, description="Inicia captura de metricas")
    router.register("medicoes", _cmd_medicoes, description="Lista sessoes de medicao")
    router.register("medicao", _cmd_medicao, description="Detalhes de uma sessao")
    router.register("laudo", _cmd_laudo, description="Gera laudo de uma sessao")
    return router


def run_chat_loop(ctx: ChatContext) -> None:
    """Loop principal do chat."""
    print_welcome(ctx.config.opentracy.agent_id, ctx.sessions.current_id)

    # --- Startup: carrega base de conhecimento no FAISS do OpenTracy ---
    if ctx.config.corpus.backend == "postgresql":
        async def _startup_corpus() -> None:
            from app.corpus_client import CorpusClient, CorpusReloadError
            ctx.corpus_client = CorpusClient(ctx.config.banco, ctx.config.corpus)
            try:
                result = await ctx.corpus_client.ensure_loaded()
                print_info(
                    f"Base de conhecimento carregada: {result['loaded']} chunks, "
                    f"dim={result['dimension']}"
                )
            except CorpusReloadError as exc:
                print_warning(f"Base de conhecimento nao carregada: {exc}")
                print_info("O chat funciona normalmente, mas sem RAG. "
                           "Use /indexar para popular a base.")
            except Exception as exc:
                print_warning(f"Erro ao carregar base de conhecimento: {exc}")

        try:
            asyncio.run(_startup_corpus())
        except Exception:
            pass  # Falha no carregamento da base nao bloqueia o chat

    while True:
        user_input = prompt_input()
        if not user_input:
            continue

        # Calcula uso de memoria para a barra de status
        session = ctx.sessions.current
        messages = session.get_all()
        total_chars = sum(len(m.get("content", "")) for m in messages)

        if user_input.startswith("/"):
            cmd_name = user_input[1:].strip().split(maxsplit=1)[0].lower()
            if not cmd_name:
                continue

            known_commands = [name.lstrip("/") for name, _ in ctx.router.list_commands()]
            if cmd_name not in known_commands:
                print_error(f"Comando desconhecido: /{cmd_name}")
                print_info("Digite /ajuda para ver os comandos disponiveis.")
                continue

            try:
                should_continue = ctx.router.dispatch(user_input, ctx=ctx)
                if not should_continue:
                    break
            except Exception as exc:
                print_error(f"Erro no comando /{cmd_name}: {exc}")
        else:
            session.add_message("user", user_input)
            ctx.logger.log_event(
                event="user_message",
                session_id=ctx.sessions.current_id,
                metadata={"content_preview": user_input[:100]},
            )

            if total_chars > ctx.config.memory.max_chars_before_summary:
                print_warning("Memória cheia — resumindo...")
                _cmd_resumo(ctx=ctx)

            # --- Spinner enquanto aguarda ---
            print_thinking()

            try:
                result = ctx.client.chat(user_input, auth_token=ctx.auth_token)
            except OpenTracyError as exc:
                print_error(f"Erro na comunicacao com OpenTracy: {exc}")
                session.add_message("assistant", f"Erro: {exc}")
                continue

            response_text = result.get("response", "")
            trace_id = result.get("trace_id")
            if trace_id:
                ctx.last_trace_id = trace_id
                if ctx.config.ui.show_trace_id:
                    print_trace_id(trace_id)

            session.add_message("assistant", response_text)
            print_assistant_message(response_text)
            ctx.logger.log_event(
                event="assistant_response",
                session_id=ctx.sessions.current_id,
                metadata={"trace_id": trace_id, "response_length": len(response_text)},
            )

        # --- Barra de status apos cada interacao ---
        mem_pct = min(100.0, (total_chars / ctx.config.memory.max_chars_before_summary * 100.0)) if ctx.config.memory.max_chars_before_summary > 0 else 0.0
        print_status_bar(
            agent_id=ctx.config.opentracy.agent_id,
            session_id=ctx.sessions.current_id,
            memory_pct=mem_pct,
            trace_id=ctx.last_trace_id,
        )

    print_info("Chat encerrado.")
