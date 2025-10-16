-- Migration: Sistema Anti-Duplicação com Fuzzy Search + Aliases
-- Data: 2025-10-16
-- Descrição: Adiciona normalização aprimorada, tabela de aliases e busca fuzzy

-- ============================================================
-- 1. INSTALAR EXTENSÃO PARA FUZZY SEARCH
-- ============================================================

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMENT ON EXTENSION fuzzystrmatch IS 'Funções para busca fuzzy (soundex, levenshtein, metaphone)';
COMMENT ON EXTENSION pg_trgm IS 'Funções para busca por similaridade de trigramas';

-- ============================================================
-- 2. MELHORAR FUNÇÃO NORMALIZAR_NOME
-- ============================================================

-- Função aprimorada para normalizar nomes de produtos
-- Remove acentos, caracteres especiais, espaços extras
CREATE OR REPLACE FUNCTION normalizar_nome(texto TEXT)
RETURNS TEXT AS $$
DECLARE
    resultado TEXT;
BEGIN
    IF texto IS NULL OR TRIM(texto) = '' THEN
        RETURN NULL;
    END IF;

    -- 1. Converter para lowercase
    resultado := LOWER(texto);

    -- 2. Remover acentos usando unaccent (se disponível) ou TRANSLATE
    BEGIN
        -- Tentar usar unaccent (mais robusto)
        CREATE EXTENSION IF NOT EXISTS unaccent;
        resultado := unaccent(resultado);
    EXCEPTION WHEN OTHERS THEN
        -- Fallback: usar TRANSLATE
        resultado := TRANSLATE(resultado,
            'áàâãäéèêëíìîïóòôõöúùûüçñ',
            'aaaaaeeeeiiiiooooouuuucn'
        );
    END;

    -- 3. Remover caracteres especiais (manter apenas letras, números e espaços)
    resultado := REGEXP_REPLACE(resultado, '[^a-z0-9\s]', '', 'g');

    -- 4. Remover espaços múltiplos
    resultado := REGEXP_REPLACE(resultado, '\s+', ' ', 'g');

    -- 5. Trim inicial e final
    resultado := TRIM(resultado);

    RETURN resultado;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION normalizar_nome IS
'Normaliza nome de produto: remove acentos, caracteres especiais e espaços extras';

-- ============================================================
-- 3. ATUALIZAR NOMES NORMALIZADOS EXISTENTES
-- ============================================================

-- Atualizar produtos existentes com nova função de normalização
UPDATE produtos_tabela
SET nome_normalizado = normalizar_nome(nome)
WHERE nome_normalizado != normalizar_nome(nome)
   OR nome_normalizado IS NULL;

-- ============================================================
-- 4. CRIAR TABELA DE ALIASES/SINÔNIMOS
-- ============================================================

-- Tabela para armazenar aliases (sinônimos) de produtos
CREATE TABLE IF NOT EXISTS produtos_aliases (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos_tabela(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    alias_normalizado VARCHAR(255) NOT NULL,
    origem VARCHAR(50) DEFAULT 'manual',  -- manual, auto, llm
    confianca DECIMAL(3,2) DEFAULT 1.0,   -- 0.0 a 1.0
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system',
    UNIQUE(alias_normalizado, produto_id)
);

-- Índices para busca eficiente
CREATE INDEX IF NOT EXISTS idx_aliases_produto_id ON produtos_aliases(produto_id);
CREATE INDEX IF NOT EXISTS idx_aliases_normalizado ON produtos_aliases(alias_normalizado);
CREATE INDEX IF NOT EXISTS idx_aliases_origem ON produtos_aliases(origem);

-- Índice GIN para busca trigrama (fuzzy)
CREATE INDEX IF NOT EXISTS idx_aliases_trgm ON produtos_aliases USING GIN (alias_normalizado gin_trgm_ops);

COMMENT ON TABLE produtos_aliases IS 'Tabela de aliases/sinônimos para identificação de produtos duplicados';
COMMENT ON COLUMN produtos_aliases.origem IS 'Origem do alias: manual (humano), auto (gerado automaticamente), llm (sugerido por LLM)';
COMMENT ON COLUMN produtos_aliases.confianca IS 'Nível de confiança do alias (0-1)';

-- ============================================================
-- 5. TRIGGER PARA AUTO-PREENCHER ALIAS_NORMALIZADO
-- ============================================================

-- Função trigger para normalizar alias automaticamente
CREATE OR REPLACE FUNCTION trigger_normalizar_alias()
RETURNS TRIGGER AS $$
BEGIN
    -- Normalizar alias ao inserir/atualizar
    NEW.alias_normalizado := normalizar_nome(NEW.alias);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger
DROP TRIGGER IF EXISTS before_insert_update_alias_normalizar ON produtos_aliases;
CREATE TRIGGER before_insert_update_alias_normalizar
    BEFORE INSERT OR UPDATE OF alias
    ON produtos_aliases
    FOR EACH ROW
    EXECUTE FUNCTION trigger_normalizar_alias();

COMMENT ON TRIGGER before_insert_update_alias_normalizar ON produtos_aliases IS
'Auto-preenche alias_normalizado antes de insert/update';

-- ============================================================
-- 6. FUNÇÃO PARA BUSCAR PRODUTO POR ALIAS
-- ============================================================

-- Busca produto usando tabela de aliases
CREATE OR REPLACE FUNCTION buscar_produto_por_alias(p_nome TEXT)
RETURNS TABLE(
    id INTEGER,
    nome VARCHAR(255),
    nome_normalizado VARCHAR(255),
    marca VARCHAR(100),
    categoria VARCHAR(100),
    origem_match VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.nome,
        p.nome_normalizado,
        p.marca,
        p.categoria,
        'alias'::VARCHAR(50) as origem_match
    FROM produtos_tabela p
    INNER JOIN produtos_aliases pa ON p.id = pa.produto_id
    WHERE pa.alias_normalizado = normalizar_nome(p_nome)
    ORDER BY pa.confianca DESC, p.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION buscar_produto_por_alias IS
'Busca produto usando tabela de aliases/sinônimos';

-- ============================================================
-- 7. FUNÇÃO PARA BUSCA FUZZY (LEVENSHTEIN)
-- ============================================================

-- Busca produtos similares usando distância de Levenshtein
CREATE OR REPLACE FUNCTION buscar_produto_fuzzy(
    p_nome TEXT,
    p_threshold DECIMAL DEFAULT 0.85,
    p_max_distancia INTEGER DEFAULT 3
)
RETURNS TABLE(
    id INTEGER,
    nome VARCHAR(255),
    nome_normalizado VARCHAR(255),
    marca VARCHAR(100),
    categoria VARCHAR(100),
    similaridade DECIMAL,
    distancia_levenshtein INTEGER,
    origem_match VARCHAR(50)
) AS $$
DECLARE
    v_nome_normalizado TEXT;
BEGIN
    v_nome_normalizado := normalizar_nome(p_nome);

    RETURN QUERY
    SELECT
        p.id,
        p.nome,
        p.nome_normalizado,
        p.marca,
        p.categoria,
        -- Calcular similaridade (0 a 1)
        1.0 - (
            levenshtein(v_nome_normalizado, p.nome_normalizado)::DECIMAL /
            GREATEST(LENGTH(v_nome_normalizado), LENGTH(p.nome_normalizado))
        ) AS similaridade,
        levenshtein(v_nome_normalizado, p.nome_normalizado) AS distancia_levenshtein,
        'fuzzy'::VARCHAR(50) as origem_match
    FROM produtos_tabela p
    WHERE p.nome_normalizado IS NOT NULL
      AND levenshtein(v_nome_normalizado, p.nome_normalizado) <= p_max_distancia
      AND v_nome_normalizado != p.nome_normalizado  -- Evitar match exato (já tratado antes)
      AND (
          1.0 - (
              levenshtein(v_nome_normalizado, p.nome_normalizado)::DECIMAL /
              GREATEST(LENGTH(v_nome_normalizado), LENGTH(p.nome_normalizado))
          )
      ) >= p_threshold
    ORDER BY similaridade DESC, p.created_at DESC
    LIMIT 5;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION buscar_produto_fuzzy IS
'Busca produtos similares usando distância de Levenshtein (fuzzy matching)';

-- ============================================================
-- 8. FUNÇÃO PARA BUSCA FUZZY EM ALIASES
-- ============================================================

-- Busca aliases similares usando distância de Levenshtein
CREATE OR REPLACE FUNCTION buscar_alias_fuzzy(
    p_nome TEXT,
    p_threshold DECIMAL DEFAULT 0.85,
    p_max_distancia INTEGER DEFAULT 3
)
RETURNS TABLE(
    id INTEGER,
    nome VARCHAR(255),
    nome_normalizado VARCHAR(255),
    marca VARCHAR(100),
    categoria VARCHAR(100),
    similaridade DECIMAL,
    distancia_levenshtein INTEGER,
    alias_encontrado VARCHAR(255),
    origem_match VARCHAR(50)
) AS $$
DECLARE
    v_nome_normalizado TEXT;
BEGIN
    v_nome_normalizado := normalizar_nome(p_nome);

    RETURN QUERY
    SELECT
        p.id,
        p.nome,
        p.nome_normalizado,
        p.marca,
        p.categoria,
        -- Calcular similaridade (0 a 1)
        1.0 - (
            levenshtein(v_nome_normalizado, pa.alias_normalizado)::DECIMAL /
            GREATEST(LENGTH(v_nome_normalizado), LENGTH(pa.alias_normalizado))
        ) AS similaridade,
        levenshtein(v_nome_normalizado, pa.alias_normalizado) AS distancia_levenshtein,
        pa.alias AS alias_encontrado,
        'alias_fuzzy'::VARCHAR(50) as origem_match
    FROM produtos_tabela p
    INNER JOIN produtos_aliases pa ON p.id = pa.produto_id
    WHERE pa.alias_normalizado IS NOT NULL
      AND levenshtein(v_nome_normalizado, pa.alias_normalizado) <= p_max_distancia
      AND v_nome_normalizado != pa.alias_normalizado
      AND (
          1.0 - (
              levenshtein(v_nome_normalizado, pa.alias_normalizado)::DECIMAL /
              GREATEST(LENGTH(v_nome_normalizado), LENGTH(pa.alias_normalizado))
          )
      ) >= p_threshold
    ORDER BY similaridade DESC, pa.confianca DESC, p.created_at DESC
    LIMIT 5;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION buscar_alias_fuzzy IS
'Busca aliases similares usando distância de Levenshtein (fuzzy matching em aliases)';

-- ============================================================
-- 9. FUNÇÃO MESTRA: BUSCAR PRODUTO COM TODAS AS ESTRATÉGIAS
-- ============================================================

-- Função que tenta todas as estratégias de busca em ordem
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
    RETURN QUERY
    SELECT * FROM buscar_produto_por_alias(p_nome);

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
'Busca produto usando múltiplas estratégias: exato → alias → fuzzy alias → fuzzy produto';

-- ============================================================
-- 10. FUNÇÃO PARA POPULAR ALIASES AUTOMATICAMENTE
-- ============================================================

-- Adiciona alias automaticamente para um produto
CREATE OR REPLACE FUNCTION adicionar_alias(
    p_produto_id INTEGER,
    p_alias VARCHAR(255),
    p_origem VARCHAR(50) DEFAULT 'auto',
    p_confianca DECIMAL DEFAULT 0.9
)
RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO produtos_aliases (produto_id, alias, origem, confianca)
    VALUES (p_produto_id, p_alias, p_origem, p_confianca)
    ON CONFLICT (alias_normalizado, produto_id) DO NOTHING;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION adicionar_alias IS
'Adiciona alias para um produto (ignora se já existe)';

-- ============================================================
-- 11. VIEW PARA ANÁLISE DE DUPLICATAS POTENCIAIS
-- ============================================================

-- View para identificar produtos que podem ser duplicatas
CREATE OR REPLACE VIEW vw_duplicatas_potenciais AS
SELECT
    p1.id as produto1_id,
    p1.nome as produto1_nome,
    p2.id as produto2_id,
    p2.nome as produto2_nome,
    1.0 - (
        levenshtein(p1.nome_normalizado, p2.nome_normalizado)::DECIMAL /
        GREATEST(LENGTH(p1.nome_normalizado), LENGTH(p2.nome_normalizado))
    ) AS similaridade,
    levenshtein(p1.nome_normalizado, p2.nome_normalizado) AS distancia
FROM produtos_tabela p1
CROSS JOIN produtos_tabela p2
WHERE p1.id < p2.id  -- Evitar duplicar comparações
  AND p1.nome_normalizado IS NOT NULL
  AND p2.nome_normalizado IS NOT NULL
  AND levenshtein(p1.nome_normalizado, p2.nome_normalizado) BETWEEN 1 AND 3
  AND (
      1.0 - (
          levenshtein(p1.nome_normalizado, p2.nome_normalizado)::DECIMAL /
          GREATEST(LENGTH(p1.nome_normalizado), LENGTH(p2.nome_normalizado))
      )
  ) >= 0.80
ORDER BY similaridade DESC;

COMMENT ON VIEW vw_duplicatas_potenciais IS
'Identifica produtos potencialmente duplicados (similaridade >= 80%)';

-- ============================================================
-- 12. RELATÓRIO DE VALIDAÇÃO
-- ============================================================

DO $$
DECLARE
    v_total_produtos INTEGER;
    v_total_aliases INTEGER;
    v_duplicatas_potenciais INTEGER;
BEGIN
    -- Contar produtos
    SELECT COUNT(*) INTO v_total_produtos FROM produtos_tabela;

    -- Contar aliases
    SELECT COUNT(*) INTO v_total_aliases FROM produtos_aliases;

    -- Contar duplicatas potenciais
    SELECT COUNT(*) INTO v_duplicatas_potenciais FROM vw_duplicatas_potenciais;

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RELATÓRIO DE INSTALAÇÃO';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✓ Extensões instaladas: fuzzystrmatch, pg_trgm';
    RAISE NOTICE '✓ Função normalizar_nome() atualizada';
    RAISE NOTICE '✓ Tabela produtos_aliases criada';
    RAISE NOTICE '✓ Funções de busca criadas:';
    RAISE NOTICE '  - buscar_produto_por_alias()';
    RAISE NOTICE '  - buscar_produto_fuzzy()';
    RAISE NOTICE '  - buscar_alias_fuzzy()';
    RAISE NOTICE '  - buscar_produto_inteligente()';
    RAISE NOTICE '';
    RAISE NOTICE 'ESTATÍSTICAS:';
    RAISE NOTICE '  - Total de produtos: %', v_total_produtos;
    RAISE NOTICE '  - Total de aliases: %', v_total_aliases;
    RAISE NOTICE '  - Duplicatas potenciais: %', v_duplicatas_potenciais;
    RAISE NOTICE '';
    RAISE NOTICE 'PRÓXIMOS PASSOS:';
    RAISE NOTICE '  1. Executar: SELECT * FROM vw_duplicatas_potenciais;';
    RAISE NOTICE '  2. Popular tabela de aliases (ver script Python)';
    RAISE NOTICE '  3. Atualizar código Python para usar buscar_produto_inteligente()';
    RAISE NOTICE '========================================';
END $$;
