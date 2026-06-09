-- ============================================================================
-- LigadoAI - Migracao v2: Base de Conhecimento
-- Schema limpo: apenas fabricante/modelo/tipo como colunas fixas.
-- Todas as metricas (tensao, corrente, RPM, etc.) ficam no JSONB frontmatter.
-- Embedder: paraphrase-multilingual-MiniLM-L12-v2 (384 dimensoes)
-- ============================================================================

-- Recria do zero (se ja existir, perde dados — indexe novamente com /indexar)
DROP TABLE IF EXISTS documentos_conhecimento CASCADE;

-- ============================================================================
-- 1. Documentos de Conhecimento
-- ============================================================================
CREATE TABLE IF NOT EXISTS documentos_conhecimento (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificadores universais (indexados para filtro hibrido)
    fabricante          TEXT NOT NULL DEFAULT 'desconhecido',
    modelo              TEXT NOT NULL DEFAULT 'desconhecido',
    tipo                TEXT NOT NULL DEFAULT 'documento',
        -- motor | maquina | fonte | bateria | componente | placa
        -- artigo | desenho | laudo | medicao | manual | sistema | documento

    -- ★ TUDO que for especifico mora aqui (metricas, specs, campos extras)
    frontmatter         JSONB NOT NULL DEFAULT '{}',

    -- Conteudo Markdown original
    conteudo_md         TEXT NOT NULL,

    -- Hash SHA-256 para deteccao de mudancas (upsert inteligente)
    hash_conteudo       VARCHAR(64) NOT NULL,

    -- Status da validacao
    status_validacao    VARCHAR(16) NOT NULL DEFAULT 'pendente',
        -- pendente | aprovado | rejeitado | aviso

    -- Erros de validacao (se houver)
    erros_validacao     JSONB,

    -- Origem do arquivo (informativo)
    source_path         TEXT,

    -- Estatisticas de chunking
    n_chunks            INTEGER DEFAULT 0,

    -- Timestamps
    indexado_em         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indices para os 3 campos universais
CREATE INDEX IF NOT EXISTS idx_docs_fabricante ON documentos_conhecimento(fabricante);
CREATE INDEX IF NOT EXISTS idx_docs_modelo ON documentos_conhecimento(modelo);
CREATE INDEX IF NOT EXISTS idx_docs_tipo ON documentos_conhecimento(tipo);
CREATE INDEX IF NOT EXISTS idx_docs_status ON documentos_conhecimento(status_validacao);
CREATE INDEX IF NOT EXISTS idx_docs_hash ON documentos_conhecimento(hash_conteudo);
CREATE INDEX IF NOT EXISTS idx_docs_frontmatter ON documentos_conhecimento USING GIN (frontmatter);

-- ============================================================================
-- 2. Chunks (fragmentos com vetor semantico)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id            VARCHAR(32) PRIMARY KEY,    -- SHA-1 do texto do chunk

    -- Referencia ao documento pai
    documento_id        UUID NOT NULL REFERENCES documentos_conhecimento(id) ON DELETE CASCADE,

    -- Conteudo do chunk
    texto               TEXT NOT NULL,

    -- Embedding (384 dimensoes - MiniLM-L12 multilíngue)
    vetor               FLOAT4[] NOT NULL,

    -- Posicao do chunk dentro do documento
    chunk_index         INTEGER NOT NULL DEFAULT 0,
    n_chunks            INTEGER NOT NULL DEFAULT 1,

    -- Metadados herdados do frontmatter (para filtro hibrido na Fase 4)
    fabricante          TEXT,
    modelo              TEXT,
    tipo                TEXT,
    metadata            JSONB,

    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_chunks_documento ON chunks(documento_id);
CREATE INDEX IF NOT EXISTS idx_chunks_fabricante ON chunks(fabricante);
CREATE INDEX IF NOT EXISTS idx_chunks_tipo ON chunks(tipo);

-- ============================================================================
-- Funcao auxiliar: detecta documentos modificados (para reload seletivo)
-- ============================================================================
CREATE OR REPLACE FUNCTION documentos_modificados(desde TIMESTAMPTZ)
RETURNS TABLE (id UUID, fabricante TEXT, modelo TEXT, tipo TEXT, n_chunks INTEGER)
LANGUAGE SQL
AS $$
    SELECT d.id, d.fabricante, d.modelo, d.tipo, d.n_chunks
    FROM documentos_conhecimento d
    WHERE d.updated_at >= desde
      AND d.status_validacao = 'aprovado'
    ORDER BY d.updated_at DESC;
$$;
