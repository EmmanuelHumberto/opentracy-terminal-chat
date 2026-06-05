"""Repositorio de medicoes em PostgreSQL + pgvector.

Armazena sessoes, snapshots, parametros ideais, diagnosticos rapidos
e documentos de conhecimento com busca semantica.

Schema completo conforme documentacao oficial (v1.0.0).
Decisao: PostgreSQL direto (sem migracao de SQLite).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import asyncpg

from app.config import BancoConfig


class ErroRepositorio(Exception):
    """Erro generico do repositorio."""


class SessaoNaoEncontrada(ErroRepositorio):
    """Sessao de medicao nao encontrada."""


class SnapshotInvalido(ErroRepositorio):
    """Snapshot com dados invalidos."""


class ParametroNaoEncontrado(ErroRepositorio):
    """Parametro ideal nao encontrado para a combinacao."""


class RepositorioMedicoesPG:
    """Armazena e consulta sessoes de medicao, snapshots, parametros e diagnosticos.

    Usa asyncpg para conexao assincrona com PostgreSQL.

    Uso:
        repo = RepositorioMedicoesPG(config.banco)
        await repo.conectar()
        try:
            await repo.criar_sessao(...)
            await repo.salvar_snapshots_validados(...)
        finally:
            await repo.desconectar()
    """

    def __init__(self, banco_config: BancoConfig):
        self.config = banco_config
        self._pool: Optional[asyncpg.Pool] = None

    # ------------------------------------------------------------------ #
    # Conexao
    # ------------------------------------------------------------------ #

    async def conectar(self) -> None:
        """Abre pool de conexoes e cria schema se necessario."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
            )
            await self._criar_schema()

    async def desconectar(self) -> None:
        """Fecha pool de conexoes."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def conectado(self) -> bool:
        return self._pool is not None

    def _assert_conectado(self) -> None:
        if self._pool is None:
            raise ErroRepositorio("Repositorio nao conectado. Chame .conectar() primeiro.")

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #

    async def _criar_schema(self) -> None:
        """Cria todas as tabelas e indices se nao existirem."""
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            # Habilita pgvector
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # 1. Sessoes de Medicao
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessoes_medicao (
                    id                  TEXT PRIMARY KEY,

                    fabricante          TEXT,
                    modelo              TEXT,
                    numero_serie        TEXT,
                    tipo_maquina        TEXT,
                    tipo_motor          TEXT,
                    sistema_transmissao TEXT,

                    curso_nominal_mm    REAL,
                    curso_min_mm        REAL,
                    curso_max_mm        REAL,

                    tipo_coleta         TEXT,
                    peca_substituida    TEXT,
                    observacoes         TEXT,
                    tecnico             TEXT,

                    porta_serial        TEXT,
                    baudrate            INTEGER,
                    duracao_seg         REAL,

                    total_snapshots     INTEGER DEFAULT 0,
                    total_hall          INTEGER DEFAULT 0,
                    total_power         INTEGER DEFAULT 0,
                    total_vibration     INTEGER DEFAULT 0,
                    total_course        INTEGER DEFAULT 0,

                    linhas_validas      INTEGER DEFAULT 0,
                    linhas_invalidas    INTEGER DEFAULT 0,
                    linhas_ignoradas    INTEGER DEFAULT 0,
                    bytes_recebidos     INTEGER DEFAULT 0,
                    taxa_media_hz       REAL DEFAULT 0.0,

                    aprovado            INTEGER,
                    diagnostico_json    TEXT,

                    created_at          TIMESTAMPTZ DEFAULT NOW(),
                    updated_at          TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Indices sessoes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessoes_fabricante
                    ON sessoes_medicao(fabricante)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessoes_modelo
                    ON sessoes_medicao(modelo)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessoes_tipo_coleta
                    ON sessoes_medicao(tipo_coleta)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessoes_data
                    ON sessoes_medicao(created_at DESC)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessoes_aprovado
                    ON sessoes_medicao(aprovado)
            """)

            # 2. Snapshots de Medicao
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots_medicao (
                    id              BIGSERIAL PRIMARY KEY,
                    sessao_id       TEXT NOT NULL REFERENCES sessoes_medicao(id)
                                    ON DELETE CASCADE,
                    timestamp_us    BIGINT,
                    tipo            TEXT NOT NULL,
                    dados_json      JSONB NOT NULL,
                    valido          INTEGER DEFAULT 1,
                    erros_validacao JSONB,
                    created_at      TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Indices snapshots
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_sessao
                    ON snapshots_medicao(sessao_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_tipo
                    ON snapshots_medicao(tipo)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_valido
                    ON snapshots_medicao(valido)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_sessao_tipo
                    ON snapshots_medicao(sessao_id, tipo)
            """)

            # 3. Parametros Ideais
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS parametros_ideais (
                    id              BIGSERIAL PRIMARY KEY,

                    fabricante          TEXT NOT NULL,
                    modelo              TEXT NOT NULL,
                    tipo_maquina        TEXT,
                    tipo_motor          TEXT,
                    sistema_transmissao TEXT,
                    curso_nominal_mm    REAL,
                    tipo_coleta         TEXT NOT NULL DEFAULT 'desempenho',

                    freq_min_hz             REAL,
                    freq_max_hz             REAL,
                    duty_min_permille       REAL,
                    duty_max_permille       REAL,
                    rpm_min                 REAL,
                    rpm_max                 REAL,

                    corrente_min_ma         REAL,
                    corrente_max_ma         REAL,
                    potencia_min_mw         REAL,
                    potencia_max_mw         REAL,
                    tensao_min_mv           REAL,
                    tensao_max_mv           REAL,

                    vibracao_leve_max_mg        REAL,
                    vibracao_moderada_max_mg    REAL,
                    vibracao_alta_max_mg        REAL,
                    vibracao_muito_alta_min_mg  REAL,

                    curso_min_mm            REAL,
                    curso_max_mm            REAL,

                    amostras_coletadas      INTEGER DEFAULT 0,
                    confianca_permille      INTEGER DEFAULT 500,
                    fonte                   TEXT,

                    created_at              TIMESTAMPTZ DEFAULT NOW(),
                    updated_at              TIMESTAMPTZ DEFAULT NOW(),

                    UNIQUE(fabricante, modelo, tipo_motor, sistema_transmissao,
                           curso_nominal_mm, tipo_coleta)
                )
            """)

            # Indices parametros
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_parametros_fabricante
                    ON parametros_ideais(fabricante)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_parametros_modelo
                    ON parametros_ideais(modelo)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_parametros_confianca
                    ON parametros_ideais(confianca_permille DESC)
            """)

            # 4. Diagnosticos Rapidos
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS diagnosticos_rapidos (
                    id              BIGSERIAL PRIMARY KEY,
                    sintoma         TEXT NOT NULL,
                    causa           TEXT NOT NULL,
                    solucao         TEXT NOT NULL,
                    fabricante      TEXT,
                    modelo          TEXT,
                    created_at      TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_diag_rapido_sintoma
                    ON diagnosticos_rapidos(sintoma)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_diag_rapido_fabricante
                    ON diagnosticos_rapidos(fabricante)
            """)

            # 5. Documentos da Base de Conhecimento (com vetor semantico)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documentos_conhecimento (
                    id              BIGSERIAL PRIMARY KEY,
                    caminho         TEXT NOT NULL,
                    titulo          TEXT,
                    conteudo        TEXT NOT NULL,
                    chunk_index     INTEGER DEFAULT 0,
                    chunk_texto     TEXT,
                    chunk_vetor     VECTOR(1536),
                    metadados       JSONB,
                    created_at      TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_docs_caminho
                    ON documentos_conhecimento(caminho)
            """)

            # Indice ivfflat para busca semantica (criado condicionalmente)
            try:
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_docs_vetor
                        ON documentos_conhecimento
                        USING ivfflat (chunk_vetor vector_cosine_ops)
                        WITH (lists = 100)
                """)
            except asyncpg.PostgresError:
                pass  # Pode falhar se nao houver dados ainda

            # Trigger para updated_at
            await conn.execute("""
                CREATE OR REPLACE FUNCTION atualizar_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """)

            # Triggers
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger
                        WHERE tgname = 'trg_sessoes_updated_at'
                    ) THEN
                        CREATE TRIGGER trg_sessoes_updated_at
                            BEFORE UPDATE ON sessoes_medicao
                            FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();
                    END IF;
                END $$;
            """)

            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger
                        WHERE tgname = 'trg_parametros_updated_at'
                    ) THEN
                        CREATE TRIGGER trg_parametros_updated_at
                            BEFORE UPDATE ON parametros_ideais
                            FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();
                    END IF;
                END $$;
            """)

            # Dados iniciais: Diagnosticos rapidos genericos
            await conn.execute("""
                INSERT INTO diagnosticos_rapidos (sintoma, causa, solucao) VALUES
                    ('nao liga', 'Fonte sem alimentacao ou fusivel queimado',
                     'Verificar fonte e cabo USB. Testar com outra fonte.'),
                    ('nao liga', 'Conexao do motor interrompida',
                     'Reconectar os fios do motor. Verificar solda nos terminais.'),
                    ('nao liga', 'Interruptor com defeito',
                     'Testar continuidade do interruptor com multimetro. Substituir se necessario.'),
                    ('vibracao excessiva', 'Rolamento desgastado ou danificado',
                     'Substituir rolamento. Verificar se ha folga lateral.'),
                    ('vibracao excessiva', 'Eixo empenado ou desbalanceado',
                     'Verificar retilineidade do eixo. Substituir se necessario.'),
                    ('vibracao excessiva', 'Conjunto excêntrico com folga',
                     'Apertar parafuso M4 com torque de 2.5 Nm. Verificar encaixe.'),
                    ('superaquecimento', 'Motor operando acima da tensao nominal',
                     'Reduzir tensao da fonte. Verificar faixa recomendada pelo fabricante.'),
                    ('superaquecimento', 'Atrito excessivo no mecanismo',
                     'Lubrificar rolamento e verificar alinhamento do conjunto.'),
                    ('superaquecimento', 'Corrente elevada por curto no enrolamento',
                     'Medir resistencia do motor. Substituir se fora da especificacao.'),
                    ('ruido anormal', 'Parafuso solto na carcaça',
                     'Apertar todos os parafusos da carcaça com torque adequado.'),
                    ('ruido anormal', 'Rolamento seco ou gasto',
                     'Lubrificar ou substituir rolamento.'),
                    ('consumo irregular', 'Escova do motor desgastada (coreless)',
                     'Substituir motor coreless. Escovas nao sao substituiveis.'),
                    ('consumo irregular', 'Conexao eletrica com mau contato',
                     'Verificar soldas e conectores. Limpar oxidacao.'),
                    ('curso inconsistente', 'Regulagem de curso descalibrada',
                     'Reajustar o curso conforme especificacao do fabricante.'),
                    ('curso inconsistente', 'Mola do sistema de transmissao fadigada',
                     'Substituir mola. Verificar curso nominal apos troca.')
                ON CONFLICT DO NOTHING
            """)

    # ================================================================== #
    # SESSOES
    # ================================================================== #

    async def criar_sessao(
        self,
        sessao_id: str,
        *,
        fabricante: str = "",
        modelo: str = "",
        numero_serie: str = "",
        tipo_maquina: str = "",
        tipo_motor: str = "",
        sistema_transmissao: str = "",
        curso_nominal_mm: Optional[float] = None,
        curso_min_mm: Optional[float] = None,
        curso_max_mm: Optional[float] = None,
        tipo_coleta: str = "desempenho",
        peca_substituida: str = "",
        observacoes: str = "",
        tecnico: str = "",
        porta_serial: str = "",
        baudrate: int = 115200,
        duracao_seg: float = 30.0,
    ) -> None:
        """Cria um registro de sessao de medicao."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO sessoes_medicao
                   (id, fabricante, modelo, numero_serie,
                    tipo_maquina, tipo_motor, sistema_transmissao,
                    curso_nominal_mm, curso_min_mm, curso_max_mm,
                    tipo_coleta, peca_substituida, observacoes, tecnico,
                    porta_serial, baudrate, duracao_seg)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                           $11, $12, $13, $14, $15, $16, $17)""",
                sessao_id,
                fabricante, modelo, numero_serie,
                tipo_maquina, tipo_motor, sistema_transmissao,
                curso_nominal_mm, curso_min_mm, curso_max_mm,
                tipo_coleta, peca_substituida, observacoes, tecnico,
                porta_serial, baudrate, duracao_seg,
            )

    async def criar_sessao_com_config(self, sessao_id: str, config: Any) -> None:
        """Cria sessao a partir de um objeto SessaoConfig.

        Metodo auxiliar para usar diretamente com o objeto config
        retornado pelo formulario_coleta.
        """
        await self.criar_sessao(
            sessao_id,
            fabricante=config.fabricante,
            modelo=config.modelo,
            numero_serie=config.numero_serie,
            tipo_maquina=getattr(config, 'tipo_maquina', ''),
            tipo_motor=getattr(config, 'tipo_motor', ''),
            sistema_transmissao=getattr(config, 'sistema_transmissao', ''),
            curso_nominal_mm=config.curso_nominal_mm,
            curso_min_mm=config.curso_min_mm,
            curso_max_mm=config.curso_max_mm,
            tipo_coleta=config.tipo_coleta,
            peca_substituida=config.peca_substituida,
            observacoes=config.observacoes,
            tecnico=config.tecnico,
            porta_serial=config.porta_serial,
            baudrate=config.baudrate,
            duracao_seg=config.duracao_seg,
        )

    # ================================================================== #
    # SNAPSHOTS
    # ================================================================== #

    async def salvar_snapshots_validados(
        self, sessao_id: str, snapshots: list[dict], rejeitados: list[dict] | None = None
    ) -> int:
        """Salva snapshots validados e rejeitados no banco."""
        self._assert_conectado()
        assert self._pool is not None

        total = 0
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Snapshots validos
                for s in snapshots:
                    await conn.execute(
                        """INSERT INTO snapshots_medicao
                           (sessao_id, timestamp_us, tipo, dados_json, valido)
                           VALUES ($1, $2, $3, $4, 1)""",
                        sessao_id,
                        s.get("timestamp_us"),
                        s.get("type", "unknown"),
                        json.dumps(s, ensure_ascii=False, default=str),
                    )
                    total += 1

                # Snapshots rejeitados
                if rejeitados:
                    for s in rejeitados:
                        erros = s.get("_erros_validacao", [])
                        await conn.execute(
                            """INSERT INTO snapshots_medicao
                               (sessao_id, timestamp_us, tipo, dados_json, valido, erros_validacao)
                               VALUES ($1, $2, $3, $4, 0, $5)""",
                            sessao_id,
                            s.get("timestamp_us"),
                            s.get("type", "unknown"),
                            json.dumps(s, ensure_ascii=False, default=str),
                            json.dumps(erros, ensure_ascii=False),
                        )
                        total += 1

            # Atualiza contadores na sessao
            await conn.execute(
                """UPDATE sessoes_medicao SET
                    total_snapshots = (SELECT COUNT(*) FROM snapshots_medicao WHERE sessao_id = $1 AND valido = 1),
                    total_hall = (SELECT COUNT(*) FROM snapshots_medicao WHERE sessao_id = $1 AND tipo = 'hall_snapshot' AND valido = 1),
                    total_power = (SELECT COUNT(*) FROM snapshots_medicao WHERE sessao_id = $1 AND tipo = 'power_snapshot' AND valido = 1),
                    total_vibration = (SELECT COUNT(*) FROM snapshots_medicao WHERE sessao_id = $1 AND tipo = 'vibration_snapshot' AND valido = 1),
                    total_course = (SELECT COUNT(*) FROM snapshots_medicao WHERE sessao_id = $1 AND tipo = 'course_snapshot' AND valido = 1)
                WHERE id = $1""",
                sessao_id,
            )

        return total

    async def finalizar_sessao(self, sessao_id: str, aprovado: bool, diagnostico_json: str) -> None:
        """Marca a sessao como finalizada com resultado do diagnostico."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                """UPDATE sessoes_medicao
                   SET aprovado = $1, diagnostico_json = $2, updated_at = NOW()
                   WHERE id = $3""",
                1 if aprovado else 0,
                diagnostico_json,
                sessao_id,
            )

    # ================================================================== #
    # CONSULTAS
    # ================================================================== #

    async def listar_sessoes(self) -> list[dict]:
        """Lista todas as sessoes de medicao, ordenadas por data."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, fabricante, modelo, tipo_coleta,
                    total_snapshots, aprovado, created_at
                   FROM sessoes_medicao
                   ORDER BY created_at DESC
                   LIMIT 100"""
            )
            return [dict(r) for r in rows]

    async def buscar_sessao(self, sessao_id: str) -> dict | None:
        """Busca uma sessao pelo ID. Retorna None se nao encontrada."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sessoes_medicao WHERE id = $1", sessao_id
            )
            return dict(row) if row else None

    async def buscar_snapshots_da_sessao(self, sessao_id: str) -> list[dict]:
        """Busca todos os snapshots de uma sessao."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT dados_json FROM snapshots_medicao
                   WHERE sessao_id = $1 AND valido = 1
                   ORDER BY timestamp_us""",
                sessao_id,
            )
            snapshots = []
            for r in rows:
                dados = r["dados_json"]
                if isinstance(dados, str):
                    dados = json.loads(dados)
                snapshots.append(dados)
            return snapshots

    async def deletar_sessao(self, sessao_id: str) -> None:
        """Deleta uma sessao e seus snapshots (CASCADE)."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM sessoes_medicao WHERE id = $1", sessao_id
            )

    async def estatisticas_globais(self) -> dict:
        """Retorna estatisticas globais do banco."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT
                    COUNT(*) as total_sessoes,
                    COALESCE(SUM(total_snapshots), 0) as total_snapshots,
                    COUNT(*) FILTER (WHERE aprovado = 1) as aprovadas,
                    COUNT(*) FILTER (WHERE aprovado = 0) as reprovadas
                   FROM sessoes_medicao"""
            )
            return dict(row) if row else {}

    # ================================================================== #
    # PARAMETROS IDEAIS
    # ================================================================== #

    async def salvar_parametros_ideais(
        self,
        fabricante: str,
        modelo: str,
        *,
        tipo_maquina: str = "",
        tipo_motor: str = "",
        sistema_transmissao: str = "",
        curso_nominal_mm: float | None = None,
        tipo_coleta: str = "desempenho",
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
        duty_min_permille: float | None = None,
        duty_max_permille: float | None = None,
        rpm_min: float | None = None,
        rpm_max: float | None = None,
        corrente_min_ma: float | None = None,
        corrente_max_ma: float | None = None,
        potencia_min_mw: float | None = None,
        potencia_max_mw: float | None = None,
        tensao_min_mv: float | None = None,
        tensao_max_mv: float | None = None,
        vibracao_leve_max_mg: float | None = None,
        vibracao_moderada_max_mg: float | None = None,
        vibracao_alta_max_mg: float | None = None,
        vibracao_muito_alta_min_mg: float | None = None,
        curso_min_mm: float | None = None,
        curso_max_mm: float | None = None,
        confianca_permille: int = 500,
        fonte: str = "manual",
    ) -> None:
        """Salva ou atualiza parametros ideais para uma maquina."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO parametros_ideais
                   (fabricante, modelo, tipo_maquina, tipo_motor,
                    sistema_transmissao, curso_nominal_mm, tipo_coleta,
                    freq_min_hz, freq_max_hz, duty_min_permille, duty_max_permille,
                    rpm_min, rpm_max, corrente_min_ma, corrente_max_ma,
                    potencia_min_mw, potencia_max_mw, tensao_min_mv, tensao_max_mv,
                    vibracao_leve_max_mg, vibracao_moderada_max_mg,
                    vibracao_alta_max_mg, vibracao_muito_alta_min_mg,
                    curso_min_mm, curso_max_mm,
                    confianca_permille, fonte)
                   VALUES ($1, $2, $3, $4, $5, $6, $7,
                           $8, $9, $10, $11, $12, $13, $14, $15,
                           $16, $17, $18, $19, $20, $21, $22, $23,
                           $24, $25, $26, $27)
                   ON CONFLICT (fabricante, modelo, tipo_motor, sistema_transmissao, curso_nominal_mm, tipo_coleta)
                   DO UPDATE SET
                    freq_min_hz = EXCLUDED.freq_min_hz,
                    freq_max_hz = EXCLUDED.freq_max_hz,
                    duty_min_permille = EXCLUDED.duty_min_permille,
                    duty_max_permille = EXCLUDED.duty_max_permille,
                    rpm_min = EXCLUDED.rpm_min,
                    rpm_max = EXCLUDED.rpm_max,
                    corrente_min_ma = EXCLUDED.corrente_min_ma,
                    corrente_max_ma = EXCLUDED.corrente_max_ma,
                    potencia_min_mw = EXCLUDED.potencia_min_mw,
                    potencia_max_mw = EXCLUDED.potencia_max_mw,
                    tensao_min_mv = EXCLUDED.tensao_min_mv,
                    tensao_max_mv = EXCLUDED.tensao_max_mv,
                    vibracao_leve_max_mg = EXCLUDED.vibracao_leve_max_mg,
                    vibracao_moderada_max_mg = EXCLUDED.vibracao_moderada_max_mg,
                    vibracao_alta_max_mg = EXCLUDED.vibracao_alta_max_mg,
                    vibracao_muito_alta_min_mg = EXCLUDED.vibracao_muito_alta_min_mg,
                    curso_min_mm = EXCLUDED.curso_min_mm,
                    curso_max_mm = EXCLUDED.curso_max_mm,
                    confianca_permille = EXCLUDED.confianca_permille,
                    fonte = EXCLUDED.fonte,
                    updated_at = NOW()""",
                fabricante, modelo, tipo_maquina, tipo_motor,
                sistema_transmissao, curso_nominal_mm, tipo_coleta,
                freq_min_hz, freq_max_hz, duty_min_permille, duty_max_permille,
                rpm_min, rpm_max, corrente_min_ma, corrente_max_ma,
                potencia_min_mw, potencia_max_mw, tensao_min_mv, tensao_max_mv,
                vibracao_leve_max_mg, vibracao_moderada_max_mg,
                vibracao_alta_max_mg, vibracao_muito_alta_min_mg,
                curso_min_mm, curso_max_mm,
                confianca_permille, fonte,
            )

    async def buscar_parametros_ideais(
        self,
        fabricante: str = "",
        modelo: str = "",
        tipo_motor: str = "",
        sistema_transmissao: str = "",
        curso_nominal_mm: float | None = None,
        tipo_coleta: str = "desempenho",
    ) -> dict | None:
        """Busca parametros ideais para uma combinacao de maquina."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM parametros_ideais
                   WHERE fabricante = $1 AND modelo = $2
                     AND tipo_motor = $3 AND sistema_transmissao = $4
                     AND ($5::real IS NULL OR curso_nominal_mm = $5)
                     AND tipo_coleta = $6
                   ORDER BY confianca_permille DESC
                   LIMIT 1""",
                fabricante, modelo, tipo_motor, sistema_transmissao,
                curso_nominal_mm, tipo_coleta,
            )
            return dict(row) if row else None

    # ================================================================== #
    # DIAGNOSTICOS RAPIDOS
    # ================================================================== #

    async def salvar_diagnostico_rapido(
        self,
        sintoma: str,
        causa: str,
        solucao: str,
        fabricante: str = "",
        modelo: str = "",
    ) -> None:
        """Salva um diagnostico rapido no banco."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO diagnosticos_rapidos (sintoma, causa, solucao, fabricante, modelo)
                   VALUES ($1, $2, $3, $4, $5)""",
                sintoma, causa, solucao,
                fabricante if fabricante else None,
                modelo if modelo else None,
            )

    async def buscar_diagnosticos_por_sintoma(
        self, sintoma: str, fabricante: str = "", modelo: str = ""
    ) -> list[dict]:
        """Busca diagnosticos rapidos por sintoma."""
        self._assert_conectado()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM diagnosticos_rapidos
                   WHERE sintoma = $1
                     AND ($2 = '' OR fabricante IS NULL OR fabricante = $2)
                     AND ($3 = '' OR modelo IS NULL OR modelo = $3)
                   ORDER BY
                     CASE WHEN fabricante IS NOT NULL THEN 0 ELSE 1 END,
                     created_at DESC""",
                sintoma, fabricante, modelo,
            )
            return [dict(r) for r in rows]
