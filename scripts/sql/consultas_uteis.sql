-- ============================================================================
-- LigadoAI - Consultas uteis para analise
-- ============================================================================

-- 1. Sessoes de uma maquina especifica
SELECT id, created_at, tipo_coleta, total_snapshots, aprovado
FROM sessoes_medicao
WHERE fabricante = 'FK Irons' AND modelo = 'Spektra Direct Drive'
ORDER BY created_at DESC;

-- 2. Parametros ideais para diagnostico
SELECT * FROM parametros_ideais
WHERE fabricante = 'FK Irons'
  AND modelo = 'Spektra Direct Drive'
  AND tipo_motor = 'brushless-coreless'
  AND sistema_transmissao = 'direct-drive-fixo'
  AND tipo_coleta = 'desempenho'
ORDER BY confianca_permille DESC
LIMIT 1;

-- 3. Estatisticas de aprovacao por fabricante
SELECT fabricante,
       COUNT(*) as total_sessoes,
       SUM(CASE WHEN aprovado = 1 THEN 1 ELSE 0 END) as aprovadas,
       ROUND(100.0 * SUM(CASE WHEN aprovado = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as taxa_aprovacao
FROM sessoes_medicao
WHERE aprovado IS NOT NULL
GROUP BY fabricante
ORDER BY total_sessoes DESC;

-- 4. Diagnosticos rapidos para um sintoma
SELECT causa, solucao, fabricante, modelo
FROM diagnosticos_rapidos
WHERE sintoma LIKE '%vibracao%'
ORDER BY fabricante NULLS LAST, modelo NULLS LAST;

-- 5. Busca semantica por similaridade (pgvector)
-- SELECT titulo, chunk_texto, 1 - (chunk_vetor <=> '[0.1, 0.2, ...]') as similaridade
-- FROM documentos_conhecimento
-- ORDER BY chunk_vetor <=> '[0.1, 0.2, ...]'
-- LIMIT 5;

-- 6. Ultimas 10 medicoes com diagnostico
SELECT s.id, s.fabricante, s.modelo, s.created_at,
       s.total_snapshots, s.aprovado,
       s.diagnostico_json::json->>'total_hall' as hall,
       s.diagnostico_json::json->>'total_power' as power,
       s.diagnostico_json::json->>'total_vibration' as vib,
       s.diagnostico_json::json->>'total_course' as curso
FROM sessoes_medicao s
WHERE s.diagnostico_json IS NOT NULL
ORDER BY s.created_at DESC
LIMIT 10;

-- 7. Maquinas mais medidas
SELECT fabricante, modelo, COUNT(*) as vezes_medida
FROM sessoes_medicao
WHERE fabricante IS NOT NULL
GROUP BY fabricante, modelo
ORDER BY vezes_medida DESC
LIMIT 20;

-- 8. Qualidade da coleta (taxa de dados)
SELECT id, fabricante, modelo,
       duracao_seg,
       total_snapshots,
       ROUND(total_snapshots / NULLIF(duracao_seg, 0), 1) as snapshots_por_segundo,
       linhas_validas, linhas_invalidas, linhas_ignoradas
FROM sessoes_medicao
WHERE duracao_seg > 0
ORDER BY created_at DESC
LIMIT 20;
