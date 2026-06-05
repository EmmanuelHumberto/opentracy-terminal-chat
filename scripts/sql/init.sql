-- ============================================================================
-- LigadoAI - Schema do Banco de Dados (PostgreSQL + pgvector)
-- Versao: 1.0.0
-- ============================================================================

-- Habilita extensao pgvector para busca semantica
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- 1. Sessoes de Medicao
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessoes_medicao (
    id                  TEXT PRIMARY KEY,        -- "med_20260605_143022"

    -- Identificacao da maquina
    fabricante          TEXT,
    modelo              TEXT,
    numero_serie        TEXT,
    tipo_maquina        TEXT,                    -- bobina, rotativa, pen
    tipo_motor          TEXT,                    -- nucleo, coreless, brushless
    sistema_transmissao TEXT,                    -- direct-drive-fixo, swash-drive-ajustavel

    -- Curso
    curso_nominal_mm    REAL,
    curso_min_mm        REAL,                    -- NULL se fixo
    curso_max_mm        REAL,                    -- NULL se fixo

    -- Metadados da coleta
    tipo_coleta         TEXT,                    -- desempenho, reparo, calibracao
    peca_substituida    TEXT,
    observacoes         TEXT,
    tecnico             TEXT,

    -- Configuracao serial
    porta_serial        TEXT,
    baudrate            INTEGER,
    duracao_seg         REAL,

    -- Estatisticas da captura
    total_snapshots     INTEGER DEFAULT 0,
    total_hall          INTEGER DEFAULT 0,
    total_power         INTEGER DEFAULT 0,
    total_vibration     INTEGER DEFAULT 0,
    total_course        INTEGER DEFAULT 0,

    -- Qualidade da serial
    linhas_validas      INTEGER DEFAULT 0,
    linhas_invalidas    INTEGER DEFAULT 0,
    linhas_ignoradas    INTEGER DEFAULT 0,
    bytes_recebidos     INTEGER DEFAULT 0,
    taxa_media_hz       REAL DEFAULT 0.0,

    -- Resultado do diagnostico
    aprovado            INTEGER,                 -- 1 = aprovado, 0 = reprovado, NULL = pendente
    diagnostico_json    TEXT,

    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_sessoes_fabricante ON sessoes_medicao(fabricante);
CREATE INDEX IF NOT EXISTS idx_sessoes_modelo ON sessoes_medicao(modelo);
CREATE INDEX IF NOT EXISTS idx_sessoes_tipo_coleta ON sessoes_medicao(tipo_coleta);
CREATE INDEX IF NOT EXISTS idx_sessoes_data ON sessoes_medicao(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessoes_aprovado ON sessoes_medicao(aprovado);

-- ============================================================================
-- 2. Snapshots de Medicao
-- ============================================================================
CREATE TABLE IF NOT EXISTS snapshots_medicao (
    id              BIGSERIAL PRIMARY KEY,
    sessao_id       TEXT NOT NULL REFERENCES sessoes_medicao(id) ON DELETE CASCADE,
    timestamp_us    BIGINT,
    tipo            TEXT NOT NULL,               -- hall_snapshot, power_snapshot, vibration_snapshot, course_snapshot
    dados_json      JSONB NOT NULL,              -- JSON completo do snapshot
    valido          INTEGER DEFAULT 1,           -- 1 = passou na validacao, 0 = rejeitado
    erros_validacao JSONB,                       -- lista de erros, se houver
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_snapshots_sessao ON snapshots_medicao(sessao_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_tipo ON snapshots_medicao(tipo);
CREATE INDEX IF NOT EXISTS idx_snapshots_valido ON snapshots_medicao(valido);
CREATE INDEX IF NOT EXISTS idx_snapshots_sessao_tipo ON snapshots_medicao(sessao_id, tipo);

-- ============================================================================
-- 3. Parametros Ideais (Faixas Normais)
-- ============================================================================
CREATE TABLE IF NOT EXISTS parametros_ideais (
    id              BIGSERIAL PRIMARY KEY,

    -- Identificacao da maquina
    fabricante          TEXT NOT NULL,
    modelo              TEXT NOT NULL,
    tipo_maquina        TEXT,
    tipo_motor          TEXT,
    sistema_transmissao TEXT,
    curso_nominal_mm    REAL,
    tipo_coleta         TEXT NOT NULL DEFAULT 'desempenho',

    -- Frequencia (Hall)
    freq_min_hz             REAL,
    freq_max_hz             REAL,
    duty_min_permille       REAL,
    duty_max_permille       REAL,
    rpm_min                 REAL,
    rpm_max                 REAL,

    -- Consumo (INA219)
    corrente_min_ma         REAL,
    corrente_max_ma         REAL,
    potencia_min_mw         REAL,
    potencia_max_mw         REAL,
    tensao_min_mv           REAL,
    tensao_max_mv           REAL,

    -- Vibracao (MPU6050)
    vibracao_leve_max_mg        REAL,
    vibracao_moderada_max_mg    REAL,
    vibracao_alta_max_mg        REAL,
    vibracao_muito_alta_min_mg  REAL,

    -- Curso (MLX90393)
    curso_min_mm            REAL,
    curso_max_mm            REAL,

    -- Metadados
    amostras_coletadas      INTEGER DEFAULT 0,
    confianca_permille      INTEGER DEFAULT 500,   -- 0-1000
    fonte                   TEXT,                   -- "manual", "calibracao", "knowledge"

    -- Timestamps
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),

    -- Garantia de unicidade
    UNIQUE(fabricante, modelo, tipo_motor, sistema_transmissao, curso_nominal_mm, tipo_coleta)
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_parametros_fabricante ON parametros_ideais(fabricante);
CREATE INDEX IF NOT EXISTS idx_parametros_modelo ON parametros_ideais(modelo);
CREATE INDEX IF NOT EXISTS idx_parametros_confianca ON parametros_ideais(confianca_permille DESC);

-- ============================================================================
-- 4. Diagnosticos Rapidos
-- ============================================================================
CREATE TABLE IF NOT EXISTS diagnosticos_rapidos (
    id              BIGSERIAL PRIMARY KEY,
    sintoma         TEXT NOT NULL,               -- "vibracao excessiva"
    causa           TEXT NOT NULL,               -- "folga no conjunto excêntrico"
    solucao         TEXT NOT NULL,               -- "apertar parafuso M4 com torque 2.5 Nm"
    fabricante      TEXT,                        -- NULL = generico
    modelo          TEXT,                        -- NULL = generico
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_diag_rapido_sintoma ON diagnosticos_rapidos(sintoma);
CREATE INDEX IF NOT EXISTS idx_diag_rapido_fabricante ON diagnosticos_rapidos(fabricante);

-- ============================================================================
-- 5. Documentos da Base de Conhecimento (com vetor semantico)
-- ============================================================================
CREATE TABLE IF NOT EXISTS documentos_conhecimento (
    id              BIGSERIAL PRIMARY KEY,
    caminho         TEXT NOT NULL,               -- caminho relativo em knowledge/
    titulo          TEXT,
    conteudo        TEXT NOT NULL,               -- markdown original
    chunk_index     INTEGER DEFAULT 0,           -- indice do chunk (0 = documento completo)
    chunk_texto     TEXT,                        -- texto do chunk para busca
    chunk_vetor     VECTOR(1536),                -- embedding para busca semantica
    metadados       JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_docs_caminho ON documentos_conhecimento(caminho);
CREATE INDEX IF NOT EXISTS idx_docs_vetor ON documentos_conhecimento
    USING ivfflat (chunk_vetor vector_cosine_ops)
    WITH (lists = 100);

-- ============================================================================
-- Funcao para atualizar updated_at automaticamente
-- ============================================================================
CREATE OR REPLACE FUNCTION atualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers
CREATE TRIGGER trg_sessoes_updated_at
    BEFORE UPDATE ON sessoes_medicao
    FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();

CREATE TRIGGER trg_parametros_updated_at
    BEFORE UPDATE ON parametros_ideais
    FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();

-- ============================================================================
-- Dados iniciais: Diagnosticos rapidos genericos
-- ============================================================================
INSERT INTO diagnosticos_rapidos (sintoma, causa, solucao) VALUES
    ('nao liga', 'Fonte sem alimentacao ou fusivel queimado', 'Verificar fonte e cabo USB. Testar com outra fonte.'),
    ('nao liga', 'Conexao do motor interrompida', 'Reconectar os fios do motor. Verificar solda nos terminais.'),
    ('nao liga', 'Interruptor com defeito', 'Testar continuidade do interruptor com multimetro. Substituir se necessario.'),
    ('vibracao excessiva', 'Rolamento desgastado ou danificado', 'Substituir rolamento. Verificar se ha folga lateral.'),
    ('vibracao excessiva', 'Eixo empenado ou desbalanceado', 'Verificar retilineidade do eixo. Substituir se necessario.'),
    ('vibracao excessiva', 'Conjunto excêntrico com folga', 'Apertar parafuso M4 com torque de 2.5 Nm. Verificar encaixe.'),
    ('superaquecimento', 'Motor operando acima da tensao nominal', 'Reduzir tensao da fonte. Verificar faixa recomendada pelo fabricante.'),
    ('superaquecimento', 'Atrito excessivo no mecanismo', 'Lubrificar rolamento e verificar alinhamento do conjunto.'),
    ('superaquecimento', 'Corrente elevada por curto no enrolamento', 'Medir resistencia do motor. Substituir se fora da especificacao.'),
    ('ruido anormal', 'Parafuso solto na carcaça', 'Apertar todos os parafusos da carcaça com torque adequado.'),
    ('ruido anormal', 'Rolamento seco ou gasto', 'Lubrificar ou substituir rolamento.'),
    ('consumo irregular', 'Escova do motor desgastada (coreless)', 'Substituir motor coreless. Escovas nao sao substituiveis.'),
    ('consumo irregular', 'Conexao eletrica com mau contato', 'Verificar soldas e conectores. Limpar oxidacao.'),
    ('curso inconsistente', 'Regulagem de curso descalibrada', 'Reajustar o curso conforme especificacao do fabricante.'),
    ('curso inconsistente', 'Mola do sistema de transmissao fadigada', 'Substituir mola. Verificar curso nominal apos troca.')
ON CONFLICT DO NOTHING;
