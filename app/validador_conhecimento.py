"""Validador de documentos de conhecimento.

Valida arquivos Markdown com frontmatter YAML antes da ingestao no banco.
Segue o mesmo contrato do validador serial de medicoes: estrutura de erro
tipado, criterios de rejeicao explicitos, tres resultados possiveis.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml


# ------------------------------------------------------------------ #
# Tipos de erro
# ------------------------------------------------------------------ #

@dataclass
class ErroValidacao:
    """Um erro ou aviso de validacao."""
    campo: str
    mensagem: str
    severidade: str  # "erro" | "aviso"


@dataclass
class ResultadoValidacao:
    """Resultado da validacao de um documento."""
    aprovado: bool = False
    rejeitado: bool = False
    avisos: list[ErroValidacao] = field(default_factory=list)
    erros: list[ErroValidacao] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)
    conteudo: str = ""
    hash_conteudo: str = ""

    @property
    def status(self) -> str:
        if self.rejeitado:
            return "rejeitado"
        if self.avisos:
            return "aviso"
        if self.aprovado:
            return "aprovado"
        return "pendente"

    def adicionar_erro(self, campo: str, mensagem: str) -> None:
        self.erros.append(ErroValidacao(campo=campo, mensagem=mensagem, severidade="erro"))
        self.rejeitado = True

    def adicionar_aviso(self, campo: str, mensagem: str) -> None:
        self.avisos.append(ErroValidacao(campo=campo, mensagem=mensagem, severidade="aviso"))


# ------------------------------------------------------------------ #
# Constantes
# ------------------------------------------------------------------ #

CAMPOS_OBRIGATORIOS = ["fabricante", "modelo", "tipo"]

TIPOS_VALIDOS = [
    "motor",
    "maquina",
    "manual",
    "sistema",
    "artigo",
    "documento",
]

FRONTMATTER_DELIMITER = "---"


# ------------------------------------------------------------------ #
# Validador
# ------------------------------------------------------------------ #

class ValidadorConhecimento:
    """Valida documentos Markdown com frontmatter YAML.

    Uso:
        validador = ValidadorConhecimento()
        resultado = validador.validar(conteudo_md, source_path="motor.md")

        if resultado.aprovado:
            # segue para o KnowledgeSyncer
            ...
    """

    def validar(self, conteudo_md: str, source_path: str = "") -> ResultadoValidacao:
        """Valida um documento Markdown completo.

        Args:
            conteudo_md: Conteudo Markdown completo (incluindo frontmatter).
            source_path: Caminho do arquivo original (para mensagens de erro).

        Returns:
            ResultadoValidacao com status, frontmatter extraido e hash.
        """
        resultado = ResultadoValidacao()

        # ------------------------------------------------------------------ #
        # 1. Extrair frontmatter YAML
        # ------------------------------------------------------------------ #
        linhas = conteudo_md.split("\n")
        frontmatter: dict[str, Any] = {}
        corpo_inicio = 0

        if linhas and linhas[0].strip() == FRONTMATTER_DELIMITER:
            # Encontrar delimitador de fechamento
            fim = -1
            for i in range(1, len(linhas)):
                if linhas[i].strip() == FRONTMATTER_DELIMITER:
                    fim = i
                    break

            if fim == -1:
                resultado.adicionar_erro(
                    "frontmatter",
                    f"Delimitador de fechamento '---' nao encontrado ({source_path})"
                )
                return resultado

            yaml_str = "\n".join(linhas[1:fim])
            try:
                frontmatter = yaml.safe_load(yaml_str)
                if not isinstance(frontmatter, dict):
                    resultado.adicionar_erro(
                        "frontmatter",
                        f"Frontmatter YAML deve ser um dicionario, recebeu {type(frontmatter).__name__} ({source_path})"
                    )
                    return resultado
            except yaml.YAMLError as exc:
                resultado.adicionar_erro(
                    "frontmatter",
                    f"YAML invalido: {exc} ({source_path})"
                )
                return resultado

            corpo_inicio = fim + 1
        else:
            resultado.adicionar_erro(
                "frontmatter",
                f"Frontmatter YAML ausente — o arquivo deve comecar com '---' ({source_path})"
            )
            return resultado

        # ------------------------------------------------------------------ #
        # 2. Conteudo apos o frontmatter
        # ------------------------------------------------------------------ #
        corpo = "\n".join(linhas[corpo_inicio:]).strip()
        if not corpo:
            resultado.adicionar_erro(
                "conteudo",
                f"Conteudo vazio apos o frontmatter ({source_path})"
            )
            return resultado

        # ------------------------------------------------------------------ #
        # 3. Campos obrigatorios
        # ------------------------------------------------------------------ #
        for campo in CAMPOS_OBRIGATORIOS:
            if campo not in frontmatter or not str(frontmatter.get(campo, "")).strip():
                resultado.adicionar_erro(
                    campo,
                    f"Campo obrigatorio '{campo}' ausente ou vazio ({source_path})"
                )

        if resultado.rejeitado:
            return resultado

        # ------------------------------------------------------------------ #
        # 4. Tipo valido
        # ------------------------------------------------------------------ #
        tipo = str(frontmatter.get("tipo", "")).strip().lower()
        if tipo not in TIPOS_VALIDOS:
            resultado.adicionar_aviso(
                "tipo",
                f"Tipo '{tipo}' nao reconhecido. Tipos validos: {', '.join(TIPOS_VALIDOS)} ({source_path})"
            )

        # ------------------------------------------------------------------ #
        # 5. Faixas numericas coerentes
        # ------------------------------------------------------------------ #
        freq_min = frontmatter.get("frequencia_min_hz")
        freq_max = frontmatter.get("frequencia_max_hz")
        if freq_min is not None and freq_max is not None:
            try:
                freq_min = float(freq_min)
                freq_max = float(freq_max)
                if freq_min <= 0 or freq_max <= 0:
                    resultado.adicionar_aviso(
                        "frequencia",
                        f"Frequencias devem ser positivas: min={freq_min}, max={freq_max} ({source_path})"
                    )
                elif freq_min >= freq_max:
                    resultado.adicionar_erro(
                        "frequencia",
                        f"frequencia_min_hz ({freq_min}) deve ser menor que frequencia_max_hz ({freq_max}) ({source_path})"
                    )
            except (ValueError, TypeError):
                resultado.adicionar_aviso(
                    "frequencia",
                    f"Valores de frequencia nao numericos: min={freq_min}, max={freq_max} ({source_path})"
                )

        # Validar outros campos numericos (devem ser positivos se presentes)
        campos_numericos = [
            ("torque_mnm", "Torque (mNm)"),
            ("potencia_w", "Potencia (W)"),
            ("rpm_max", "RPM maximo"),
            ("peso_g", "Peso (g)"),
            ("diametro_mm", "Diametro (mm)"),
            ("comprimento_mm", "Comprimento (mm)"),
        ]
        for campo_nome, campo_label in campos_numericos:
            valor = frontmatter.get(campo_nome)
            if valor is not None:
                try:
                    valor = float(valor)
                    if valor <= 0:
                        resultado.adicionar_aviso(
                            campo_nome,
                            f"{campo_label} deve ser positivo: {valor} ({source_path})"
                        )
                except (ValueError, TypeError):
                    resultado.adicionar_aviso(
                        campo_nome,
                        f"{campo_label} nao numerico: {valor} ({source_path})"
                    )

        # ------------------------------------------------------------------ #
        # 6. Encoding UTF-8 (ja garantido pelo Python ao ler o arquivo)
        #    Verificamos se ha caracteres de substituicao (indicativo de
        #    problema de encoding na leitura)
        # ------------------------------------------------------------------ #
        if "\ufffd" in conteudo_md:
            resultado.adicionar_aviso(
                "encoding",
                f"Caracteres de substituicao Unicode detectados — possivel problema de encoding ({source_path})"
            )

        # ------------------------------------------------------------------ #
        # 7. Hash do conteudo (SHA-256)
        # ------------------------------------------------------------------ #
        hash_conteudo = hashlib.sha256(conteudo_md.encode("utf-8")).hexdigest()

        # ------------------------------------------------------------------ #
        # Resultado final
        # ------------------------------------------------------------------ #
        resultado.aprovado = not resultado.rejeitado
        resultado.frontmatter = frontmatter
        resultado.conteudo = corpo
        resultado.hash_conteudo = hash_conteudo

        return resultado


def formatar_resultado(resultado: ResultadoValidacao, source_path: str = "") -> str:
    """Formata um ResultadoValidacao para exibicao no terminal.

    Args:
        resultado: Resultado da validacao.
        source_path: Caminho do arquivo (para contexto).

    Returns:
        String formatada pronta para exibicao.
    """
    linhas: list[str] = []

    if resultado.aprovado and not resultado.avisos:
        fabricante = resultado.frontmatter.get("fabricante", "?")
        modelo = resultado.frontmatter.get("modelo", "?")
        tipo = resultado.frontmatter.get("tipo", "?")
        linhas.append(f"✅ Aprovado  fabricante={fabricante}  modelo={modelo}  tipo={tipo}")
    elif resultado.aprovado:
        fabricante = resultado.frontmatter.get("fabricante", "?")
        modelo = resultado.frontmatter.get("modelo", "?")
        tipo = resultado.frontmatter.get("tipo", "?")
        linhas.append(f"⚠️ Aprovado com avisos  fabricante={fabricante}  modelo={modelo}  tipo={tipo}")
        for aviso in resultado.avisos:
            linhas.append(f"   ⚠ {aviso.campo}: {aviso.mensagem}")
    else:
        linhas.append(f"❌ Rejeitado — {source_path}")
        for erro in resultado.erros:
            linhas.append(f"   ❌ {erro.campo}: {erro.mensagem}")

    return "\n".join(linhas)
