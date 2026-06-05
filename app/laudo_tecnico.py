"""Geracao de laudos tecnicos e diagnosticos a partir de medicoes.

Gera documentos Markdown estruturados com:
- Dados da maquina e da sessao
- Estatisticas das medicoes
- Diagnostico comparativo com faixas normais
- Aprovacao/reprovacao por vertical
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.captura_serial import (
    SessaoConfig,
    Estatisticas,
    agrupar_por_tipo,
    extrair_valores,
    calcular_estatisticas,
)


# Faixas normais de operacao (valores de referencia)
# Fonte: knowledge/08-medicoes/faixas_normais/
FAIXAS_NORMAIS: dict[str, dict[str, tuple[float, float, str]]] = {
    "hall_snapshot": {
        "frequency_hz": (80.0, 150.0, "Hz"),
        "duty_permille": (300.0, 700.0, "permille (30-70%)"),
        "rpm_inferred": (4800.0, 9000.0, "RPM"),
    },
    "power_snapshot": {
        "bus_voltage_mv": (4000.0, 9000.0, "mV (4-9V)"),
        "current_ma": (300.0, 1200.0, "mA"),
        "power_mw": (1500.0, 10000.0, "mW"),
    },
    "vibration_snapshot": {
        "rms_norm_mg": (0.0, 30.0, "mg"),
        "peak_norm_mg": (0.0, 80.0, "mg"),
        "p2p_norm_mg": (0.0, 160.0, "mg"),
        "quality_permille": (700.0, 1000.0, "permille (70-100%)"),
    },
    "course_snapshot": {
        "course_mm": (2.0, 5.0, "mm"),
        "displacement_mm": (0.0, 1.0, "mm"),
        "quality_permille": (600.0, 1000.0, "permille (60-100%)"),
    },
}


def _status_para_icone(valor: float, minimo: float, maximo: float) -> tuple[str, str]:
    """Retorna (icone, status) para um valor comparado com a faixa normal."""
    if minimo <= valor <= maximo:
        return ("✅", "normal")
    if valor < minimo:
        return ("⬇️", "abaixo do esperado")
    return ("⬆️", "acima do esperado")


def _diagnosticar_vibracao(vib_stats: dict[str, Estatisticas]) -> list[str]:
    """Gera diagnosticos especificos para vibracao."""
    diagnosticos = []
    rms = vib_stats.get("rms_norm_mg")
    if rms and rms.media > 30:
        if rms.media > 60:
            diagnosticos.append(
                "🔴 Vibracao RMS critica (> 60 mg). Provaveis causas:\n"
                "   - Rolamento desgastado ou danificado\n"
                "   - Eixo empenado ou desbalanceado\n"
                "   - Conjunto excêntrico com folga excessiva\n"
                "   Recomendacao: substituir rolamento e verificar alinhamento do eixo"
            )
        else:
            diagnosticos.append(
                "🟡 Vibracao RMS elevada (30-60 mg). Provaveis causas:\n"
                "   - Inicio de desgaste no rolamento\n"
                "   - Pequena folga no mecanismo\n"
                "   - Lubrificacao insuficiente\n"
                "   Recomendacao: monitorar e lubrificar; programar revisao"
            )
    if rms and rms.media <= 30:
        diagnosticos.append("✅ Vibracao dentro do esperado para maquina em boas condicoes")

    qualidade = vib_stats.get("quality_permille")
    if qualidade and qualidade.media < 700:
        diagnosticos.append(
            "🟡 Qualidade vibracional baixa (< 70%). Possivel irregularidade no movimento."
        )

    return diagnosticos


def _diagnosticar_consumo(power_stats: dict[str, Estatisticas]) -> list[str]:
    """Gera diagnosticos especificos para consumo eletrico."""
    diagnosticos = []
    corrente = power_stats.get("current_ma")
    if corrente and corrente.media > 1200:
        diagnosticos.append(
            "🔴 Consumo elevado (> 1.2A). Provaveis causas:\n"
            "   - Motor com enrolamento em curto\n"
            "   - Atrito excessivo no mecanismo\n"
            "   - Fonte subdimensionada ou com defeito\n"
            "   Recomendacao: verificar integridade do motor e lubrificacao"
        )
    elif corrente and corrente.media < 300:
        diagnosticos.append(
            "⬇️ Consumo abaixo do esperado (< 300mA). Possivel:\n"
            "   - Tensao de alimentacao baixa\n"
            "   - Motor sem carga (desengatado)\n"
            "   Recomendacao: verificar tensao e acoplamento"
        )
    else:
        diagnosticos.append("✅ Consumo dentro da faixa normal de operacao")

    return diagnosticos


def _diagnosticar_frequencia(hall_stats: dict[str, Estatisticas]) -> list[str]:
    """Gera diagnosticos para frequencia e ciclo."""
    diagnosticos = []
    freq = hall_stats.get("frequency_hz")
    if freq:
        if freq.desvio_padrao > 5.0:
            diagnosticos.append(
                "🟡 Frequencia instavel (desvio padrao > 5 Hz). Possivel:\n"
                "   - Fonte chaveada com ruido\n"
                "   - Regulagem de velocidade com mau contato\n"
                "   - Motor coreless com escova gasta"
            )
        else:
            diagnosticos.append("✅ Frequencia estavel durante a medicao")

    duty = hall_stats.get("duty_permille")
    if duty:
        if duty.media < 300:
            diagnosticos.append(
                "⬇️ Duty cycle baixo (< 30%). Maquina pode estar operando\n"
                "   abaixo da tensao nominal ou com folga excessiva."
            )
        elif duty.media > 700:
            diagnosticos.append(
                "⬆️ Duty cycle alto (> 70%). Maquina operando no limite.\n"
                "   Verificar se a tensao aplicada e adequada."
            )

    return diagnosticos


def gerar_diagnostico(
    snapshots: list[dict],
    config: SessaoConfig,
) -> dict[str, Any]:
    """Gera diagnostico completo a partir dos snapshots capturados.

    Returns:
        dict com: aprovado, diagnosticos_por_vertical, resumo, recomendacoes
    """
    grupos = agrupar_por_tipo(snapshots)
    diagnosticos: dict[str, list[str]] = {}
    estatisticas: dict[str, dict[str, Estatisticas]] = {}
    aprovado = True

    for tipo_snapshot, lista in grupos.items():
        faixas = FAIXAS_NORMAIS.get(tipo_snapshot, {})
        campos = list(faixas.keys())
        valores = extrair_valores(lista, campos)

        stats = {}
        diag_list: list[str] = []
        for campo, vals in valores.items():
            if not vals:
                continue
            stat = calcular_estatisticas(vals)
            stats[campo] = stat

            faixa = faixas.get(campo)
            if faixa:
                minimo, maximo, unidade = faixa
                icone, status = _status_para_icone(stat.media, minimo, maximo)
                if status != "normal":
                    aprovado = False
                diag_list.append(
                    f"  {icone} {campo}: {stat.media:.1f} {unidade} "
                    f"(faixa normal: {minimo:.0f}-{maximo:.0f}) - {status}"
                )

        estatisticas[tipo_snapshot] = stats

        # Diagnosticos especificos por vertical
        if tipo_snapshot == "vibration_snapshot":
            diag_list.extend(_diagnosticar_vibracao(stats))
        elif tipo_snapshot == "power_snapshot":
            diag_list.extend(_diagnosticar_consumo(stats))
        elif tipo_snapshot == "hall_snapshot":
            diag_list.extend(_diagnosticar_frequencia(stats))

        if diag_list:
            diagnosticos[tipo_snapshot] = diag_list

    return {
        "aprovado": aprovado,
        "diagnosticos": diagnosticos,
        "estatisticas": estatisticas,
        "total_snapshots": len(snapshots),
        "total_hall": len(grupos.get("hall_snapshot", [])),
        "total_power": len(grupos.get("power_snapshot", [])),
        "total_vibration": len(grupos.get("vibration_snapshot", [])),
        "total_course": len(grupos.get("course_snapshot", [])),
    }


def gerar_laudo_markdown(
    sessao_id: str,
    config: SessaoConfig,
    snapshots: list[dict],
    diagnostico: dict[str, Any],
) -> str:
    """Gera um laudo tecnico completo em Markdown.

    O laudo pode ser salvo como PDF, impresso ou enviado ao cliente.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    status_global = "APROVADO" if diagnostico["aprovado"] else "REPROVADO"

    linhas = [
        f"# Laudo Técnico - Máquina de Tatuagem",
        f"",
        f"**Data do laudo:** {agora}",
        f"**Sessão:** {sessao_id}",
        f"**Técnico:** {config.tecnico or 'N/A'}",
        f"",
        f"---",
        f"",
        f"## 1. Dados da Máquina",
        f"",
        f"| Campo | Valor |",
        f"|-------|-------|",
        f"| Fabricante | {config.fabricante or 'N/A'} |",
        f"| Modelo | {config.modelo or 'N/A'} |",
        f"| Nº Série | {config.numero_serie or 'N/A'} |",
        f"| Tipo de Coleta | {config.tipo_coleta} |",
        f"| Peça Substituída | {config.peca_substituida or 'N/A'} |",
        f"| Observações | {config.observacoes or 'N/A'} |",
        f"",
        f"---",
        f"",
        f"## 2. Resultado Global",
        f"",
        f"**Status: {status_global}**",
        f"",
        f"Snapshots capturados: {diagnostico['total_snapshots']}",
        f"",
        f"| Vertical | Snapshots |",
        f"|----------|-----------|",
        f"| Frequência (Hall) | {diagnostico['total_hall']} |",
        f"| Consumo (INA219) | {diagnostico['total_power']} |",
        f"| Vibração (MPU6050) | {diagnostico['total_vibration']} |",
        f"| Curso (MLX90393) | {diagnostico['total_course']} |",
        f"",
        f"---",
        f"",
        f"## 3. Diagnóstico por Vertical",
        f"",
    ]

    for tipo_snapshot, diag_list in diagnostico.get("diagnosticos", {}).items():
        nome_vertical = {
            "hall_snapshot": "Frequência e Ciclo (Hall ATS177)",
            "power_snapshot": "Consumo Elétrico (INA219)",
            "vibration_snapshot": "Vibração Mecânica (MPU6050)",
            "course_snapshot": "Curso e Deslocamento (MLX90393)",
        }.get(tipo_snapshot, tipo_snapshot)

        linhas.append(f"### {nome_vertical}")
        linhas.append("")
        for d in diag_list:
            linhas.append(d)
        linhas.append("")

    linhas.extend([
        f"---",
        f"",
        f"## 4. Estatísticas Detalhadas",
        f"",
    ])

    for tipo_snapshot, stats in diagnostico.get("estatisticas", {}).items():
        nome_vertical = {
            "hall_snapshot": "Hall ATS177",
            "power_snapshot": "INA219",
            "vibration_snapshot": "MPU6050",
            "course_snapshot": "MLX90393",
        }.get(tipo_snapshot, tipo_snapshot)

        linhas.append(f"### {nome_vertical}")
        linhas.append("")
        linhas.append("| Grandeza | Média | Mín | Máx | Desv. Pad. | Amostras |")
        linhas.append("|----------|-------|-----|-----|------------|----------|")
        for campo, stat in stats.items():
            linhas.append(
                f"| {campo} | {stat.media:.2f} | {stat.minimo:.2f} | "
                f"{stat.maximo:.2f} | {stat.desvio_padrao:.2f} | {stat.amostras} |"
            )
        linhas.append("")

    linhas.extend([
        f"---",
        f"",
        f"## 5. Observações Finais",
        f"",
        f"{config.observacoes or 'Nenhuma observacao adicional.'}",
        f"",
        f"---",
        f"",
        f"*Laudo gerado automaticamente pelo Cous Terminal Chat em {agora}*",
        f"",
    ])

    return "\n".join(linhas)


def salvar_laudo(conteudo: str, sessao_id: str, dir_laudos: Path) -> Path:
    """Salva o laudo em arquivo Markdown."""
    dir_laudos.mkdir(parents=True, exist_ok=True)
    caminho = dir_laudos / f"laudo_{sessao_id}.md"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho
