-- Migration: Sistema Anti-Duplicação de Produtos
-- Data: 2025-10-14
-- Descrição: Adiciona constraints, índices e funções para evitar produtos duplicados

-- ============================================================
-- 1. FUNÇÃO DE NORMALIZAÇÃO DE NOME
-- ============================================================

-- Função para normalizar nomes de produtos
-- Remove espaços extras, converte para lowercase, remove acentos
CREATE OR REPLACE FUNCTION normalizar_nome(texto TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Remove espaços extras, converte para lowercase e trim
    RETURN LOWER(TRIM(REGEXP_REPLACE(texto, '\s+', ' ', 'g')));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION normalizar_nome IS 'Normaliza nome de produto removendo espaços extras e convertendo para lowercase';

-- ============================================================
-- 2. ADICIONAR COLUNA NOME_NORMALIZADO
-- ============================================================

-- Adicionar coluna para armazenar nome normalizado
ALTER TABLE produtos_tabela
ADD COLUMN IF NOT EXISTS nome_normalizado VARCHAR(255);

-- Preencher coluna com nomes normalizados existentes
UPDATE produtos_tabela
SET nome_normalizado = normalizar_nome(nome)
WHERE nome_normalizado IS NULL;

-- Criar índice único na coluna normalizada
CREATE UNIQUE INDEX IF NOT EXISTS idx_produtos_nome_normalizado_unique
ON produtos_tabela(nome_normalizado);

COMMENT ON COLUMN produtos_tabela.nome_normalizado IS 'Nome do produto normalizado (lowercase, sem espaços extras) - ÚNICO';

-- ============================================================
-- 3. TRIGGER PARA AUTO-PREENCHER NOME_NORMALIZADO
-- ============================================================

-- Função trigger para normalizar nome automaticamente
CREATE OR REPLACE FUNCTION trigger_normalizar_nome_produto()
RETURNS TRIGGER AS $$
BEGIN
    -- Sempre que nome for inserido ou atualizado, normalizar
    NEW.nome_normalizado := normalizar_nome(NEW.nome);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger BEFORE INSERT/UPDATE
DROP TRIGGER IF EXISTS before_insert_update_produto_normalizar ON produtos_tabela;
CREATE TRIGGER before_insert_update_produto_normalizar
    BEFORE INSERT OR UPDATE OF nome
    ON produtos_tabela
    FOR EACH ROW
    EXECUTE FUNCTION trigger_normalizar_nome_produto();

COMMENT ON TRIGGER before_insert_update_produto_normalizar ON produtos_tabela IS
'Auto-preenche nome_normalizado antes de insert/update';

-- ============================================================
-- 4. FUNÇÃO PARA BUSCAR PRODUTO COM NORMALIZAÇÃO
-- ============================================================

-- Função para buscar produto de forma segura (evita duplicatas)
CREATE OR REPLACE FUNCTION buscar_produto_por_nome_normalizado(
    p_nome TEXT,
    p_marca TEXT DEFAULT NULL,
    p_categoria_id INTEGER DEFAULT NULL
)
RETURNS TABLE(
    id INTEGER,
    nome VARCHAR(255),
    marca VARCHAR(100),
    categoria VARCHAR(100),
    categoria_id INTEGER,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.nome,
        p.marca,
        p.categoria,
        p.categoria_id,
        p.created_at
    FROM produtos_tabela p
    WHERE p.nome_normalizado = normalizar_nome(p_nome)
    -- Se marca for fornecida, considerar na busca (opcional)
    AND (p_marca IS NULL OR p.marca IS NULL OR LOWER(p.marca) = LOWER(p_marca))
    ORDER BY p.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION buscar_produto_por_nome_normalizado IS
'Busca produto usando nome normalizado, evitando duplicatas';

-- ============================================================
-- 5. ADICIONAR COLUNA CODIGO_UNICO (OPCIONAL)
-- ============================================================

-- Para produtos com código de barras, garantir unicidade
CREATE UNIQUE INDEX IF NOT EXISTS idx_produtos_codigo_barras_unique
ON produtos_tabela(codigo_barras)
WHERE codigo_barras IS NOT NULL AND codigo_barras != '';

COMMENT ON INDEX idx_produtos_codigo_barras_unique IS
'Garante que códigos de barras sejam únicos (quando preenchidos)';

-- ============================================================
-- 6. VIEW PARA DETECÇÃO DE POSSÍVEIS DUPLICATAS
-- ============================================================

-- View para identificar produtos que podem ser duplicatas
CREATE OR REPLACE VIEW vw_possiveis_duplicatas AS
SELECT
    p1.id as produto1_id,
    p1.nome as produto1_nome,
    p1.marca as produto1_marca,
    p1.categoria as produto1_categoria,
    p2.id as produto2_id,
    p2.nome as produto2_nome,
    p2.marca as produto2_marca,
    p2.categoria as produto2_categoria,
    p1.nome_normalizado as nome_normalizado_comum
FROM produtos_tabela p1
INNER JOIN produtos_tabela p2 ON p1.nome_normalizado = p2.nome_normalizado
WHERE p1.id < p2.id  -- Evitar comparar produto consigo mesmo e duplicar resultados
ORDER BY p1.nome_normalizado, p1.id;

COMMENT ON VIEW vw_possiveis_duplicatas IS
'Identifica produtos que podem ser duplicatas baseado em nome normalizado';

-- ============================================================
-- 7. ESTATÍSTICAS DE VALIDAÇÃO
-- ============================================================

-- Verificar se há violações de unicidade pendentes
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Contar produtos com mesmo nome_normalizado
    SELECT COUNT(*) INTO v_count
    FROM (
        SELECT nome_normalizado, COUNT(*) as qtd
        FROM produtos_tabela
        GROUP BY nome_normalizado
        HAVING COUNT(*) > 1
    ) duplicados;

    IF v_count > 0 THEN
        RAISE WARNING 'Encontrados % grupos de produtos com nomes duplicados!', v_count;
        RAISE NOTICE 'Execute: SELECT * FROM vw_possiveis_duplicatas; para ver detalhes';
    ELSE
        RAISE NOTICE '✓ Nenhum produto duplicado encontrado';
    END IF;
END $$;

-- ============================================================
-- RELATÓRIO FINAL
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
    'Produtos com Código de Barras' as metrica,
    COUNT(*)::TEXT as valor
FROM produtos_tabela
WHERE codigo_barras IS NOT NULL AND codigo_barras != ''

UNION ALL

SELECT
    'Nomes Únicos (Normalizados)' as metrica,
    COUNT(DISTINCT nome_normalizado)::TEXT as valor
FROM produtos_tabela;
