# ---------------------------------------------------------------------------
# Utilitarios de captura
# ---------------------------------------------------------------------------

def _perguntar_opcao(mensagem, opcoes, default=""):
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

def _validar_snapshots(snapshots):
    validos, rejeitados = [], []
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

def _verificar_conexao_serial(porta, baudrate):
    import os
    try:
        return os.path.exists(porta)
    except Exception:
        return False
