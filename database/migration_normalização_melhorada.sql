-- Migration: Normalização Melhorada (Remove Acentos)
-- Data: 2025-10-15
-- Descrição: Atualiza função normalizar_nome para remover acentos e caracteres especiais

-- ============================================================
-- 1. MELHORAR FUNÇÃO NORMALIZAR_NOME (COM REMOÇÃO DE ACENTOS)
-- ============================================================

-- Instalar extensão unaccent se não existir (necessário para remover acentos)
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Função melhorada para normalizar nomes
-- Remove acentos, espaços extras, caracteres especiais e converte para lowercase
CREATE OR REPLACE FUNCTION normalizar_nome(texto TEXT)
RETURNS TEXT AS $$
BEGIN
    IF texto IS NULL OR TRIM(texto) = '' THEN
        RETURN NULL;
    END IF;

    RETURN LOWER(
        TRIM(
            REGEXP_REPLACE(
                unaccent(texto),  -- Remove acentos
                '[^a-z0-9\s]',    -- Remove caracteres especiais (mantém letras, números e espaços)
                '',
                'gi'
            )
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION normalizar_nome IS
'Normaliza nome removendo acentos, caracteres especiais, espaços extras e convertendo para lowercase';

-- ============================================================
-- 2. REMOVER ÍNDICE ÚNICO TEMPORARIAMENTE
-- ============================================================

-- Precisamos remover o índice único para poder atualizar produtos duplicados
DROP INDEX IF EXISTS idx_produtos_nome_normalizado_unique;

-- ============================================================
-- 3. ATUALIZAR TODOS OS NOMES NORMALIZADOS EXISTENTES
-- ============================================================

-- Atualizar todos os nomes com a nova normalização
UPDATE produtos_tabela
SET nome_normalizado = normalizar_nome(nome);

-- Verificar quantos grupos de duplicatas existem após normalização
DO $$
DECLARE
    v_count INTEGER;
    v_exemplo RECORD;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM (
        SELECT nome_normalizado, COUNT(*) as qtd
        FROM produtos_tabela
        WHERE nome_normalizado IS NOT NULL
        GROUP BY nome_normalizado
        HAVING COUNT(*) > 1
    ) duplicados;

    IF v_count > 0 THEN
        RAISE WARNING 'Encontrados % grupos de produtos duplicados!', v_count;
        RAISE NOTICE 'Execute o script de mesclagem para corrigir';

        -- Mostrar alguns exemplos
        RAISE NOTICE '';
        RAISE NOTICE '--- EXEMPLOS DE DUPLICATAS ---';
        FOR v_exemplo IN
            SELECT nome_normalizado, COUNT(*) as qtd,
                   STRING_AGG(nome, ' | ' ORDER BY id) as nomes_originais
            FROM produtos_tabela
            WHERE nome_normalizado IS NOT NULL
            GROUP BY nome_normalizado
            HAVING COUNT(*) > 1
            LIMIT 5
        LOOP
            RAISE NOTICE 'Nome normalizado: % (% ocorrências)', v_exemplo.nome_normalizado, v_exemplo.qtd;
            RAISE NOTICE '  Nomes originais: %', v_exemplo.nomes_originais;
        END LOOP;
    ELSE
        RAISE NOTICE '✓ Nenhuma duplicata encontrada! Criando índice único...';

        -- Se não há duplicatas, criar índice único
        CREATE UNIQUE INDEX IF NOT EXISTS idx_produtos_nome_normalizado_unique
        ON produtos_tabela(nome_normalizado)
        WHERE nome_normalizado IS NOT NULL;
    END IF;
END $$;

-- ============================================================
-- 4. VIEW PARA DETECTAR DUPLICATAS COM DETALHES
-- ============================================================

CREATE OR REPLACE VIEW vw_duplicatas_detalhadas AS
SELECT
    nome_normalizado,
    COUNT(*) as quantidade_duplicatas,
    STRING_AGG(DISTINCT nome, ' | ' ORDER BY nome) as nomes_originais,
    STRING_AGG(id::TEXT, ', ' ORDER BY id) as ids,
    STRING_AGG(marca, ', ' ORDER BY id) as marcas,
    COUNT(DISTINCT marca) as quantidade_marcas,
    MIN(created_at) as primeira_criacao,
    MAX(created_at) as ultima_criacao
FROM produtos_tabela
WHERE nome_normalizado IS NOT NULL
GROUP BY nome_normalizado
HAVING COUNT(*) > 1
ORDER BY quantidade_duplicatas DESC, nome_normalizado;

COMMENT ON VIEW vw_duplicatas_detalhadas IS
'Mostra produtos duplicados com detalhes completos para análise e mesclagem';

-- ============================================================
-- 5. RELATÓRIO DE VALIDAÇÃO
-- ============================================================

SELECT
    'Total de Produtos' as metrica,
    COUNT(*)::TEXT as valor
FROM produtos_tabela

UNION ALL

SELECT
    'Produtos com Nome Normalizado' as metrica,
    COUNT(*)::TEXT as valor
FROM produtos_tabela
WHERE nome_normalizado IS NOT NULL

UNION ALL

SELECT
    'Nomes Únicos (Normalizados)' as metrica,
    COUNT(DISTINCT nome_normalizado)::TEXT as valor
FROM produtos_tabela
WHERE nome_normalizado IS NOT NULL

UNION ALL

SELECT
    'Grupos de Duplicatas' as metrica,
    COUNT(*)::TEXT as valor
FROM (
    SELECT nome_normalizado
    FROM produtos_tabela
    WHERE nome_normalizado IS NOT NULL
    GROUP BY nome_normalizado
    HAVING COUNT(*) > 1
) dup;

-- ============================================================
-- INSTRUÇÕES PARA PRÓXIMOS PASSOS
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '================================================';
    RAISE NOTICE 'MIGRATION CONCLUÍDA';
    RAISE NOTICE '================================================';
    RAISE NOTICE '';
    RAISE NOTICE '1. Verificar duplicatas:';
    RAISE NOTICE '   SELECT * FROM vw_duplicatas_detalhadas;';
    RAISE NOTICE '';
    RAISE NOTICE '2. Para mesclar duplicatas, execute:';
    RAISE NOTICE '   python scripts/mesclar_duplicatas.py';
    RAISE NOTICE '';
    RAISE NOTICE '3. Após mesclar, criar índice único:';
    RAISE NOTICE '   CREATE UNIQUE INDEX idx_produtos_nome_normalizado_unique';
    RAISE NOTICE '   ON produtos_tabela(nome_normalizado);';
    RAISE NOTICE '';
END $$;
