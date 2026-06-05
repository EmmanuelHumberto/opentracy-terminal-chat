"""Captura de dados TMA_DATA da serial do firmware ESP32-S3.

Le as linhas TMA_DATA publicadas pelo firmware, faz parse JSON
e retorna dicionarios estruturados para cada tipo de snapshot.
"""

from __future__ import annotations

import json
import os
import select
import termios
import time
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Callable, Optional


BAUD_RATES = {
    9600: termios.B9600,
    19200: termios.B19200,
    38400: termios.B38400,
    57600: termios.B57600,
    115200: termios.B115200,
    230400: termios.B230400,
    460800: termios.B460800,
    921600: termios.B921600,
}

TMA_PREFIX = "TMA_DATA "


@dataclass
class SessaoConfig:
    """Configuracao da sessao de medicao, preenchida pelo usuario."""

    fabricante: str = ""
    modelo: str = ""
    numero_serie: str = ""
    tipo_maquina: str = ""
    tipo_motor: str = ""
    sistema_transmissao: str = ""
    curso_nominal_mm: Optional[float] = None
    curso_min_mm: Optional[float] = None
    curso_max_mm: Optional[float] = None
    tipo_coleta: str = "desempenho"  # desempenho, reparo, pos-reparo, homologacao, bancada
    peca_substituida: str = ""
    observacoes: str = ""
    tecnico: str = ""
    porta_serial: str = ""
    baudrate: int = 115200
    duracao_seg: float = 30.0
    verticais: Optional[list[str]] = None


@dataclass
class Estatisticas:
    """Estatisticas calculadas para uma grandeza."""

    media: float = 0.0
    mediana: float = 0.0
    minimo: float = 0.0
    maximo: float = 0.0
    desvio_padrao: float = 0.0
    amostras: int = 0


def configurar_serial(fd: int, baudrate: int) -> None:
    """Configura a porta serial com os parametros corretos."""
    speed = BAUD_RATES.get(baudrate)
    if speed is None:
        raise ValueError(f"Baudrate nao suportado: {baudrate}")

    attrs = termios.tcgetattr(fd)
    attrs[0] = 0  # iflag
    attrs[1] = 0  # oflag
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL  # cflag
    attrs[3] = 0  # lflag
    attrs[4] = speed  # ispeed
    attrs[5] = speed  # ospeed
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def iterar_linhas(stream: BinaryIO, deadline: Optional[float] = None, callback: Callable = None):
    """Itera sobre linhas da serial, chamando callback para cada TMA_DATA."""
    buffer = bytearray()

    while True:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            timeout = min(0.5, remaining)
        else:
            timeout = 0.5

        ready, _, _ = select.select([stream], [], [], timeout)
        if not ready:
            continue

        chunk = stream.read(256)
        if not chunk:
            if buffer:
                linha = buffer.decode("utf-8", errors="replace").strip()
                if linha:
                    yield linha
            return

        buffer.extend(chunk)
        while b"\n" in buffer:
            raw_line, _, rest = buffer.partition(b"\n")
            buffer = bytearray(rest)
            linha = raw_line.decode("utf-8", errors="replace").strip()
            if linha:
                yield linha


def parse_tma_data(linha: str) -> Optional[dict[str, Any]]:
    """Faz parse de uma linha TMA_DATA. Retorna dict ou None se invalido."""
    if TMA_PREFIX not in linha:
        return None

    payload = linha.split(TMA_PREFIX, 1)[1]
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def capturar(
    porta: str,
    baudrate: int = 115200,
    duracao_seg: float = 30.0,
    callback: Optional[Callable[[dict[str, Any]], None]] = None,
) -> list[dict[str, Any]]:
    """Captura TMA_DATA da serial.

    Args:
        porta: Caminho da porta serial (ex: /dev/ttyACM0)
        baudrate: Taxa de transmissao
        duracao_seg: Duracao da captura em segundos
        callback: Funcao chamada para cada snapshot (para UI em tempo real)

    Returns:
        Lista de snapshots capturados
    """
    snapshots: list[dict[str, Any]] = []
    fd = os.open(porta, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)

    try:
        configurar_serial(fd, baudrate)
        deadline = time.monotonic() + duracao_seg

        with os.fdopen(fd, "rb", buffering=0, closefd=False) as stream:
            for linha in iterar_linhas(stream, deadline):
                snapshot = parse_tma_data(linha)
                if snapshot:
                    snapshots.append(snapshot)
                    if callback:
                        callback(snapshot)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass

    return snapshots


def calcular_estatisticas(valores: list[float]) -> Estatisticas:
    """Calcula estatisticas basicas para uma lista de valores."""
    if not valores:
        return Estatisticas()

    n = len(valores)
    valores_ordenados = sorted(valores)
    media = sum(valores) / n

    # Mediana
    if n % 2 == 1:
        mediana = float(valores_ordenados[n // 2])
    else:
        mediana = (valores_ordenados[n // 2 - 1] + valores_ordenados[n // 2]) / 2

    # Desvio padrao
    variancia = sum((v - media) ** 2 for v in valores) / n

    return Estatisticas(
        media=media,
        mediana=mediana,
        minimo=float(valores_ordenados[0]),
        maximo=float(valores_ordenados[-1]),
        desvio_padrao=variancia ** 0.5,
        amostras=n,
    )


def agrupar_por_tipo(snapshots: list[dict]) -> dict[str, list[dict]]:
    """Agrupa snapshots por tipo (hall, power, vibration, course)."""
    grupos: dict[str, list[dict]] = {}
    for s in snapshots:
        tipo = s.get("type", "unknown")
        if tipo not in grupos:
            grupos[tipo] = []
        grupos[tipo].append(s)
    return grupos


def extrair_valores(snapshots: list[dict], campos: list[str]) -> dict[str, list[float]]:
    """Extrai valores numericos de campos especificos dos snapshots."""
    resultado: dict[str, list[float]] = {campo: [] for campo in campos}
    for s in snapshots:
        for campo in campos:
            valor = s.get(campo)
            if isinstance(valor, (int, float)):
                resultado[campo].append(float(valor))
    return resultado
