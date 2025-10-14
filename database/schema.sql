-- Schema para sistema de extração de preços de panfletos
-- Database: databasev1

-- Tabela de produtos
CREATE TABLE IF NOT EXISTS produtos_tabela (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    marca VARCHAR(100),
    categoria VARCHAR(100),
    codigo_barras VARCHAR(13),
    descricao TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices para busca eficiente
CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos_tabela(LOWER(nome));
CREATE INDEX IF NOT EXISTS idx_produtos_marca ON produtos_tabela(LOWER(marca));
CREATE INDEX IF NOT EXISTS idx_produtos_codigo_barras ON produtos_tabela(codigo_barras);

-- Tabela de supermercados
CREATE TABLE IF NOT EXISTS supermercados (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    rede VARCHAR(100),
    cidade VARCHAR(100),
    estado CHAR(2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(nome, cidade, estado)
);

-- Índice para busca de supermercados
CREATE INDEX IF NOT EXISTS idx_supermercados_nome ON supermercados(LOWER(nome));

-- Tabela de imagens processadas
CREATE TABLE IF NOT EXISTS imagens_processadas (
    id SERIAL PRIMARY KEY,
    nome_arquivo VARCHAR(255),
    caminho_arquivo TEXT,
    supermercado_nome VARCHAR(255),
    data_panfleto DATE,
    status VARCHAR(50) DEFAULT 'pendente',
    texto_extraido TEXT,
    dados_json JSONB,
    erro_mensagem TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

-- Índices para imagens
CREATE INDEX IF NOT EXISTS idx_imagens_status ON imagens_processadas(status);
CREATE INDEX IF NOT EXISTS idx_imagens_data ON imagens_processadas(data_panfleto);
CREATE INDEX IF NOT EXISTS idx_imagens_dados_json ON imagens_processadas USING GIN (dados_json);

-- Tabela de preços extraídos
CREATE TABLE IF NOT EXISTS precos_panfleto (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER REFERENCES produtos_tabela(id) ON DELETE CASCADE,
    supermercado_id INTEGER REFERENCES supermercados(id) ON DELETE CASCADE,
    imagem_id INTEGER REFERENCES imagens_processadas(id) ON DELETE CASCADE,
    preco DECIMAL(10, 2) NOT NULL,
    preco_original DECIMAL(10, 2),
    em_promocao BOOLEAN DEFAULT FALSE,
    validade_inicio DATE,
    validade_fim DATE,
    unidade VARCHAR(50),
    descricao_adicional TEXT,
    confianca DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para preços
CREATE INDEX IF NOT EXISTS idx_precos_produto ON precos_panfleto(produto_id);
CREATE INDEX IF NOT EXISTS idx_precos_supermercado ON precos_panfleto(supermercado_id);
CREATE INDEX IF NOT EXISTS idx_precos_imagem ON precos_panfleto(imagem_id);
CREATE INDEX IF NOT EXISTS idx_precos_data ON precos_panfleto(validade_inicio, validade_fim);
CREATE INDEX IF NOT EXISTS idx_precos_promocao ON precos_panfleto(em_promocao);

-- Trigger para atualizar updated_at em produtos_tabela
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_produtos_updated_at BEFORE UPDATE
    ON produtos_tabela FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View útil: Produtos com menor preço atual
CREATE OR REPLACE VIEW vw_melhores_precos AS
SELECT
    p.id,
    p.nome,
    p.marca,
    p.categoria,
    pp.preco,
    pp.preco_original,
    pp.em_promocao,
    s.nome as supermercado,
    pp.validade_inicio,
    pp.validade_fim,
    pp.created_at
FROM produtos_tabela p
INNER JOIN precos_panfleto pp ON p.id = pp.produto_id
INNER JOIN supermercados s ON pp.supermercado_id = s.id
WHERE pp.validade_fim >= CURRENT_DATE OR pp.validade_fim IS NULL
ORDER BY p.nome, pp.preco ASC;

-- View: Estatísticas por supermercado
CREATE OR REPLACE VIEW vw_estatisticas_supermercado AS
SELECT
    s.id,
    s.nome,
    COUNT(DISTINCT pp.produto_id) as total_produtos,
    COUNT(pp.id) as total_precos,
    AVG(pp.preco) as preco_medio,
    MIN(pp.preco) as menor_preco,
    MAX(pp.preco) as maior_preco,
    SUM(CASE WHEN pp.em_promocao THEN 1 ELSE 0 END) as total_promocoes
FROM supermercados s
LEFT JOIN precos_panfleto pp ON s.id = pp.supermercado_id
GROUP BY s.id, s.nome;

-- Comentários nas tabelas
COMMENT ON TABLE produtos_tabela IS 'Catálogo de produtos extraídos dos panfletos';
COMMENT ON TABLE supermercados IS 'Cadastro de supermercados identificados';
COMMENT ON TABLE imagens_processadas IS 'Log de imagens processadas e seus dados brutos';
COMMENT ON TABLE precos_panfleto IS 'Histórico de preços extraídos dos panfletos';

COMMENT ON COLUMN precos_panfleto.confianca IS 'Nível de confiança da extração (0-1)';
COMMENT ON COLUMN imagens_processadas.dados_json IS 'JSON bruto retornado pela LLM';
COMMENT ON COLUMN imagens_processadas.status IS 'Status: pendente, processado, erro, sem_produtos';
