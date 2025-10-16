-- Migration: Adicionar coluna categoria_sugerida
-- Data: 2025-10-15
-- Descrição: Captura a categoria original sugerida pelo LLM antes do mapeamento
--            para análise futura e melhoria do sistema de categorização

-- ============================================================================
-- MIGRATION UP
-- ============================================================================

-- Adicionar coluna categoria_sugerida
ALTER TABLE produtos_tabela
ADD COLUMN IF NOT EXISTS categoria_sugerida VARCHAR(100);

-- Criar índice para busca eficiente
CREATE INDEX IF NOT EXISTS idx_produtos_categoria_sugerida
ON produtos_tabela(categoria_sugerida);

-- Adicionar comentário explicativo
COMMENT ON COLUMN produtos_tabela.categoria_sugerida IS
'Categoria original sugerida pelo LLM antes do mapeamento inteligente. Usado para análise e melhoria do sistema de categorização.';

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

-- Verificar se a coluna foi criada
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'produtos_tabela'
        AND column_name = 'categoria_sugerida'
    ) THEN
        RAISE NOTICE 'Migration aplicada com sucesso: coluna categoria_sugerida criada';
    ELSE
        RAISE EXCEPTION 'Erro: coluna categoria_sugerida não foi criada';
    END IF;
END $$;

-- ============================================================================
-- QUERIES ÚTEIS PARA ANÁLISE
-- ============================================================================

-- Top 20 categorias sugeridas mais frequentes (não mapeadas para "Outros")
-- SELECT
--     categoria_sugerida,
--     COUNT(*) as qtd,
--     STRING_AGG(DISTINCT nome, ', ' ORDER BY nome LIMIT 3) as exemplos
-- FROM produtos_tabela
-- WHERE categoria = 'Outros' AND categoria_sugerida IS NOT NULL
-- GROUP BY categoria_sugerida
-- ORDER BY qtd DESC
-- LIMIT 20;

-- Produtos com categoria sugerida diferente da mapeada
-- SELECT nome, marca, categoria_sugerida, categoria
-- FROM produtos_tabela
-- WHERE categoria_sugerida IS NOT NULL
--   AND LOWER(TRIM(categoria_sugerida)) != LOWER(TRIM(categoria))
-- ORDER BY created_at DESC
-- LIMIT 50;

-- Estatísticas de mapeamento
-- SELECT
--     CASE
--         WHEN categoria = 'Outros' THEN 'Não Mapeada'
--         WHEN categoria_sugerida IS NULL THEN 'Sem Sugestão'
--         WHEN LOWER(TRIM(categoria_sugerida)) = LOWER(TRIM(categoria)) THEN 'Exata'
--         ELSE 'Mapeada'
--     END as tipo_mapeamento,
--     COUNT(*) as quantidade,
--     ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM produtos_tabela), 2) as percentual
-- FROM produtos_tabela
-- GROUP BY tipo_mapeamento
-- ORDER BY quantidade DESC;

-- ============================================================================
-- ROLLBACK (caso necessário)
-- ============================================================================

-- Para reverter esta migration, execute:
-- DROP INDEX IF EXISTS idx_produtos_categoria_sugerida;
-- ALTER TABLE produtos_tabela DROP COLUMN IF EXISTS categoria_sugerida;
-- RAISE NOTICE 'Rollback aplicado: coluna categoria_sugerida removida';
