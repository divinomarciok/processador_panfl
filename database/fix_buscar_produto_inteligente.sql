-- Fix: Corrige incompatibilidade de tipos na função buscar_produto_inteligente
-- Data: 2025-10-16
-- Problema: buscar_produto_por_alias retorna 6 colunas, mas buscar_produto_inteligente espera 7

-- ============================================================
-- CORRIGIR FUNÇÃO buscar_produto_inteligente
-- ============================================================

CREATE OR REPLACE FUNCTION buscar_produto_inteligente(
    p_nome TEXT,
    p_threshold_fuzzy DECIMAL DEFAULT 0.85
)
RETURNS TABLE(
    id INTEGER,
    nome VARCHAR(255),
    nome_normalizado VARCHAR(255),
    marca VARCHAR(100),
    categoria VARCHAR(100),
    similaridade DECIMAL,
    origem_match VARCHAR(50)
) AS $$
DECLARE
    v_resultado RECORD;
BEGIN
    -- 1. BUSCA EXATA (nome_normalizado)
    SELECT
        p.id, p.nome, p.nome_normalizado, p.marca, p.categoria,
        1.0::DECIMAL as similaridade,
        'exato'::VARCHAR(50) as origem_match
    INTO v_resultado
    FROM produtos_tabela p
    WHERE p.nome_normalizado = normalizar_nome(p_nome)
    LIMIT 1;

    IF FOUND THEN
        RETURN QUERY SELECT
            v_resultado.id, v_resultado.nome, v_resultado.nome_normalizado,
            v_resultado.marca, v_resultado.categoria, v_resultado.similaridade,
            v_resultado.origem_match;
        RETURN;
    END IF;

    -- 2. BUSCA POR ALIAS (exato)
    -- CORRIGIDO: Adicionar coluna similaridade explicitamente
    RETURN QUERY
    SELECT
        pa.id,
        pa.nome,
        pa.nome_normalizado,
        pa.marca,
        pa.categoria,
        1.0::DECIMAL as similaridade,  -- Match exato por alias
        pa.origem_match
    FROM buscar_produto_por_alias(p_nome) pa;

    IF FOUND THEN
        RETURN;
    END IF;

    -- 3. BUSCA FUZZY EM ALIASES
    RETURN QUERY
    SELECT
        ba.id, ba.nome, ba.nome_normalizado, ba.marca, ba.categoria,
        ba.similaridade, ba.origem_match
    FROM buscar_alias_fuzzy(p_nome, p_threshold_fuzzy) ba
    LIMIT 1;

    IF FOUND THEN
        RETURN;
    END IF;

    -- 4. BUSCA FUZZY EM PRODUTOS
    RETURN QUERY
    SELECT
        bf.id, bf.nome, bf.nome_normalizado, bf.marca, bf.categoria,
        bf.similaridade, bf.origem_match
    FROM buscar_produto_fuzzy(p_nome, p_threshold_fuzzy) bf
    LIMIT 1;

    -- Se nada encontrado, retorna vazio
    RETURN;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION buscar_produto_inteligente IS
'Busca produto usando múltiplas estratégias: exato → alias → fuzzy alias → fuzzy produto (CORRIGIDO)';

-- ============================================================
-- RELATÓRIO
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'FIX APLICADO COM SUCESSO';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✓ Função buscar_produto_inteligente() corrigida';
    RAISE NOTICE '✓ Agora retorna corretamente 7 colunas com similaridade';
    RAISE NOTICE '';
    RAISE NOTICE 'TESTE:';
    RAISE NOTICE '  SELECT * FROM buscar_produto_inteligente(''teste'');';
    RAISE NOTICE '========================================';
END $$;
