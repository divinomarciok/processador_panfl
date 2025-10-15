-- Criar Índice Único para nome_normalizado
-- Data: 2025-10-15
-- Descrição: Previne duplicatas futuras após mesclagem

-- Verificar se ainda há duplicatas
DO $$
DECLARE
    v_count INTEGER;
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
        RAISE EXCEPTION 'Ainda existem % grupos de duplicatas! Execute a mesclagem primeiro.', v_count;
    ELSE
        RAISE NOTICE '✓ Nenhuma duplicata encontrada. Criando índice único...';
    END IF;
END $$;

-- Criar índice único
CREATE UNIQUE INDEX IF NOT EXISTS idx_produtos_nome_normalizado_unique
ON produtos_tabela(nome_normalizado)
WHERE nome_normalizado IS NOT NULL;

-- Verificar criação
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_produtos_nome_normalizado_unique'
    ) THEN
        RAISE NOTICE '✅ Índice único criado com sucesso!';
        RAISE NOTICE '   Nome: idx_produtos_nome_normalizado_unique';
        RAISE NOTICE '   Tabela: produtos_tabela';
        RAISE NOTICE '   Coluna: nome_normalizado';
    ELSE
        RAISE WARNING '❌ Falha ao criar índice único';
    END IF;
END $$;
