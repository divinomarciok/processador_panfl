-- Migration: Criar tabela de categorias e normalizar produtos
-- Data: 2025-10-14

-- 1. Criar tabela de categorias
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    icone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Inserir categorias simplificadas
INSERT INTO categorias (nome, descricao, icone) VALUES
    ('Bebidas', 'Bebidas em geral (refrigerantes, sucos, água, etc)', '🥤'),
    ('Bebidas Alcoólicas', 'Cervejas, vinhos, destilados e bebidas alcoólicas', '🍺'),
    ('Carnes', 'Carnes bovinas, suínas, aves e pescados', '🥩'),
    ('Frios e Laticínios', 'Queijos, presunto, iogurtes, leite e derivados', '🧀'),
    ('Frutas', 'Frutas frescas e in natura', '🍎'),
    ('Verduras e Legumes', 'Hortaliças, verduras e legumes frescos', '🥬'),
    ('Mercearia', 'Produtos secos (arroz, feijão, macarrão, óleos)', '🛒'),
    ('Panificação', 'Pães, bolos e produtos de padaria', '🍞'),
    ('Doces e Sobremesas', 'Chocolates, balas, bombons e sobremesas', '🍫'),
    ('Molhos e Temperos', 'Molhos, condimentos e temperos', '🧂'),
    ('Higiene Pessoal', 'Produtos de higiene e cuidados pessoais', '🧴'),
    ('Limpeza', 'Produtos de limpeza e higiene doméstica', '🧹'),
    ('Utilidades', 'Itens diversos e utilidades domésticas', '🔧'),
    ('Congelados', 'Produtos congelados', '❄️'),
    ('Outros', 'Produtos sem categoria específica', '📦')
ON CONFLICT (nome) DO NOTHING;

-- 3. Adicionar coluna categoria_id na tabela produtos_tabela
ALTER TABLE produtos_tabela
ADD COLUMN IF NOT EXISTS categoria_id INTEGER REFERENCES categorias(id);

-- 4. Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_produtos_categoria_id ON produtos_tabela(categoria_id);

-- 5. Atualizar produtos existentes com categoria_id baseado na categoria texto

-- Bebidas
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Bebidas')
WHERE categoria = 'Bebidas' AND categoria_id IS NULL;

-- Bebidas Alcoólicas
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Bebidas Alcoólicas')
WHERE categoria = 'Bebidas Alcoólicas' AND categoria_id IS NULL;

-- Carnes
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Carnes')
WHERE categoria = 'Carnes' AND categoria_id IS NULL;

-- Frios e Laticínios (unificar Frios e Laticínios)
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Frios e Laticínios')
WHERE categoria IN ('Frios', 'Laticínios') AND categoria_id IS NULL;

-- Frutas
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Frutas')
WHERE categoria = 'Frutas' AND categoria_id IS NULL;

-- Verduras e Legumes (unificar Verduras e Temperos frescos)
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Verduras e Legumes')
WHERE categoria IN ('Verduras', 'Temperos') AND categoria_id IS NULL;

-- Mercearia
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Mercearia')
WHERE categoria = 'Mercearia' AND categoria_id IS NULL;

-- Panificação
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Panificação')
WHERE categoria = 'Panificação' AND categoria_id IS NULL;

-- Doces e Sobremesas
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Doces e Sobremesas')
WHERE categoria = 'Doces' AND categoria_id IS NULL;

-- Molhos e Temperos
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Molhos e Temperos')
WHERE categoria = 'Molhos' AND categoria_id IS NULL;

-- Higiene Pessoal
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Higiene Pessoal')
WHERE categoria = 'Higiene Pessoal' AND categoria_id IS NULL;

-- Limpeza
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Limpeza')
WHERE categoria = 'Limpeza' AND categoria_id IS NULL;

-- Produtos sem categoria (NULL ou vazio)
UPDATE produtos_tabela
SET categoria_id = (SELECT id FROM categorias WHERE nome = 'Outros')
WHERE (categoria IS NULL OR categoria = '') AND categoria_id IS NULL;

-- 6. Relatório de resultados
SELECT
    c.nome as categoria,
    c.icone,
    COUNT(p.id) as total_produtos
FROM categorias c
LEFT JOIN produtos_tabela p ON p.categoria_id = c.id
GROUP BY c.id, c.nome, c.icone
ORDER BY total_produtos DESC, c.nome;
