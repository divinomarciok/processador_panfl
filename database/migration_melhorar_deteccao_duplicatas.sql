-- Migration: Melhorar Detecção de Duplicatas
-- Data: 2025-10-16
-- Descrição: Evita falsos positivos na detecção de duplicatas

-- ============================================================
-- 1. FUNÇÃO PARA DETECTAR PALAVRAS DIFERENCIADAS
-- ============================================================

-- Função que identifica palavras que indicam produtos DIFERENTES
CREATE OR REPLACE FUNCTION tem_palavras_diferenciadas(
    nome1 TEXT,
    nome2 TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    -- Lista de palavras que indicam VARIAÇÕES de produto
    palavras_diferenciadoras TEXT[] := ARRAY[
        'dupla', 'tripla', 'simples',
        'com osso', 'sem osso',
        'com tampa', 'sem tampa',
        'integral', 'desnatado', 'semidesnatado',
        'diet', 'zero', 'light',
        'grande', 'pequeno', 'medio',
        'kg', 'g', 'l', 'ml',
        'peça', 'pedaço', 'fatia', 'fatiado', 'fatiada',
        'pack', 'unidade', 'caixa'
    ];
    palavra TEXT;
    nome1_lower TEXT;
    nome2_lower TEXT;
BEGIN
    nome1_lower := LOWER(nome1);
    nome2_lower := LOWER(nome2);

    -- Verificar se uma palavra diferenciadora está em um nome mas não no outro
    FOREACH palavra IN ARRAY palavras_diferenciadoras
    LOOP
        -- Se a palavra está em um mas não no outro, são produtos DIFERENTES
        IF (nome1_lower LIKE '%' || palavra || '%' AND nome2_lower NOT LIKE '%' || palavra || '%')
           OR (nome2_lower LIKE '%' || palavra || '%' AND nome1_lower NOT LIKE '%' || palavra || '%')
        THEN
            RETURN TRUE;  -- Tem palavras diferenciadas (NÃO é duplicata)
        END IF;
    END LOOP;

    RETURN FALSE;  -- Não tem palavras diferenciadas (pode ser duplicata)
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION tem_palavras_diferenciadas IS
'Detecta se dois nomes têm palavras que indicam produtos DIFERENTES (ex: dupla vs tripla)';

-- ============================================================
-- 2. ATUALIZAR VIEW DE DUPLICATAS POTENCIAIS
-- ============================================================

-- Recriar view com filtros mais inteligentes
DROP VIEW IF EXISTS vw_duplicatas_potenciais;

CREATE VIEW vw_duplicatas_potenciais AS
SELECT
    p1.id as produto1_id,
    p1.nome as produto1_nome,
    p1.marca as produto1_marca,
    p2.id as produto2_id,
    p2.nome as produto2_nome,
    p2.marca as produto2_marca,
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

  -- ✨ NOVO: Apenas produtos da MESMA marca (ou ambos sem marca)
  AND (
      (p1.marca IS NULL AND p2.marca IS NULL)  -- Ambos sem marca
      OR (p1.marca IS NOT NULL AND p2.marca IS NOT NULL AND LOWER(p1.marca) = LOWER(p2.marca))  -- Mesma marca
  )

  -- ✨ NOVO: NÃO tem palavras diferenciadas
  AND NOT tem_palavras_diferenciadas(p1.nome, p2.nome)

  AND (
      1.0 - (
          levenshtein(p1.nome_normalizado, p2.nome_normalizado)::DECIMAL /
          GREATEST(LENGTH(p1.nome_normalizado), LENGTH(p2.nome_normalizado))
      )
  ) >= 0.80
ORDER BY similaridade DESC;

COMMENT ON VIEW vw_duplicatas_potenciais IS
'Identifica produtos potencialmente duplicados (mesma marca, sem palavras diferenciadas)';

-- ============================================================
-- 3. CRIAR VIEW DE PRODUTOS RELACIONADOS (NÃO DUPLICATAS)
-- ============================================================

-- View para produtos RELACIONADOS mas não duplicados
-- (mesma família, marcas diferentes ou variações)
CREATE OR REPLACE VIEW vw_produtos_relacionados AS
SELECT
    p1.id as produto1_id,
    p1.nome as produto1_nome,
    p1.marca as produto1_marca,
    p2.id as produto2_id,
    p2.nome as produto2_nome,
    p2.marca as produto2_marca,
    1.0 - (
        levenshtein(p1.nome_normalizado, p2.nome_normalizado)::DECIMAL /
        GREATEST(LENGTH(p1.nome_normalizado), LENGTH(p2.nome_normalizado))
    ) AS similaridade,
    CASE
        WHEN p1.marca IS NOT NULL AND p2.marca IS NOT NULL AND LOWER(p1.marca) != LOWER(p2.marca)
            THEN 'marca_diferente'
        WHEN tem_palavras_diferenciadas(p1.nome, p2.nome)
            THEN 'variacao_produto'
        ELSE 'outro'
    END as tipo_relacao
FROM produtos_tabela p1
CROSS JOIN produtos_tabela p2
WHERE p1.id < p2.id
  AND p1.nome_normalizado IS NOT NULL
  AND p2.nome_normalizado IS NOT NULL
  AND levenshtein(p1.nome_normalizado, p2.nome_normalizado) BETWEEN 1 AND 5
  AND (
      1.0 - (
          levenshtein(p1.nome_normalizado, p2.nome_normalizado)::DECIMAL /
          GREATEST(LENGTH(p1.nome_normalizado), LENGTH(p2.nome_normalizado))
      )
  ) >= 0.70

  -- Produtos relacionados MAS não duplicatas
  AND (
      -- Marcas diferentes
      (p1.marca IS NOT NULL AND p2.marca IS NOT NULL AND LOWER(p1.marca) != LOWER(p2.marca))
      -- OU tem palavras diferenciadas
      OR tem_palavras_diferenciadas(p1.nome, p2.nome)
  )
ORDER BY similaridade DESC;

COMMENT ON VIEW vw_produtos_relacionados IS
'Produtos similares mas NÃO duplicados (marcas diferentes ou variações do produto)';

-- ============================================================
-- 4. TESTAR FUNÇÃO
-- ============================================================

-- Testar função com exemplos
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TESTES DA FUNÇÃO tem_palavras_diferenciadas()';
    RAISE NOTICE '========================================';

    -- Casos que DEVEM retornar TRUE (NÃO são duplicatas)
    RAISE NOTICE 'Casos que NÃO são duplicatas (esperado: TRUE):';
    RAISE NOTICE '  Folha Dupla vs Folha Tripla: %', tem_palavras_diferenciadas('Papel Higiênico Folha Dupla', 'Papel Higiênico Folha Tripla');
    RAISE NOTICE '  Com Osso vs Sem Osso: %', tem_palavras_diferenciadas('Pernil Suíno Com Osso', 'Pernil Suíno Sem Osso');
    RAISE NOTICE '  Com Tampa vs Sem Tampa: %', tem_palavras_diferenciadas('Leite Caixinha com Tampa', 'Leite Caixinha sem Tampa');

    RAISE NOTICE '';
    RAISE NOTICE 'Casos que SÃO duplicatas (esperado: FALSE):';
    RAISE NOTICE '  Fatiado vs Fatiada: %', tem_palavras_diferenciadas('Queijo Mussarela Fatiado', 'Queijo Mussarela Fatiada');
    RAISE NOTICE '  Kabotiá vs Cabotiá: %', tem_palavras_diferenciadas('Abóbora Kabotiá', 'Abóbora Cabotiá');
    RAISE NOTICE '  Laminados vs Laminado: %', tem_palavras_diferenciadas('Biscoito Laminados', 'Biscoito Laminado');

    RAISE NOTICE '========================================';
END $$;

-- ============================================================
-- 5. RELATÓRIO DE VALIDAÇÃO
-- ============================================================

DO $$
DECLARE
    v_duplicatas_antes INTEGER;
    v_duplicatas_depois INTEGER;
    v_relacionados INTEGER;
BEGIN
    -- Contar duplicatas na nova view
    SELECT COUNT(*) INTO v_duplicatas_depois FROM vw_duplicatas_potenciais;
    SELECT COUNT(*) INTO v_relacionados FROM vw_produtos_relacionados;

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RELATÓRIO DE VALIDAÇÃO';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✓ Função tem_palavras_diferenciadas() criada';
    RAISE NOTICE '✓ View vw_duplicatas_potenciais atualizada';
    RAISE NOTICE '✓ View vw_produtos_relacionados criada';
    RAISE NOTICE '';
    RAISE NOTICE 'ESTATÍSTICAS:';
    RAISE NOTICE '  Duplicatas potenciais (filtradas): %', v_duplicatas_depois;
    RAISE NOTICE '  Produtos relacionados (não duplicatas): %', v_relacionados;
    RAISE NOTICE '';
    RAISE NOTICE 'PRÓXIMOS PASSOS:';
    RAISE NOTICE '  1. Verificar duplicatas: SELECT * FROM vw_duplicatas_potenciais;';
    RAISE NOTICE '  2. Ver produtos relacionados: SELECT * FROM vw_produtos_relacionados LIMIT 10;';
    RAISE NOTICE '  3. Re-executar: python scripts/listar_duplicatas.py';
    RAISE NOTICE '========================================';
END $$;
