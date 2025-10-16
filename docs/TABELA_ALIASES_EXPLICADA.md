# Como Funciona a Tabela de Aliases

## 📋 Estrutura Completa

```sql
CREATE TABLE produtos_aliases (
    id SERIAL PRIMARY KEY,                    -- ID único do alias
    produto_id INTEGER NOT NULL,              -- ID do produto principal
    alias VARCHAR(255) NOT NULL,              -- Nome alternativo (original)
    alias_normalizado VARCHAR(255) NOT NULL,  -- Nome normalizado (auto-preenchido)
    origem VARCHAR(50) DEFAULT 'manual',      -- Como foi criado
    confianca DECIMAL(3,2) DEFAULT 1.0,       -- Nível de confiança (0-1)
    created_at TIMESTAMP DEFAULT NOW(),       -- Data de criação
    created_by VARCHAR(100) DEFAULT 'system'  -- Quem criou
);
```

---

## 🔑 Campos Explicados

### 1. `id` (SERIAL)
- **O que é**: Identificador único do alias
- **Exemplo**: 1, 2, 3...
- **Auto-gerado**: Sim

### 2. `produto_id` (INTEGER) **[CAMPO PRINCIPAL]**
- **O que é**: ID do produto na tabela `produtos_tabela`
- **Exemplo**: 222 (aponta para "Abóbora Cabotiá")
- **Relacionamento**:
  ```sql
  FOREIGN KEY (produto_id) REFERENCES produtos_tabela(id)
  ```

### 3. `alias` (VARCHAR) **[NOME ALTERNATIVO]**
- **O que é**: Nome alternativo pelo qual o produto também pode ser encontrado
- **Exemplo**: `"Abóbora Kabotiá"`
- **Mantém**: Acentos, capitalização, formato original

### 4. `alias_normalizado` (VARCHAR) **[BUSCA AUTOMÁTICA]**
- **O que é**: Versão normalizada do alias (preenchido automaticamente)
- **Exemplo**: `"abobora kabotia"` (sem acentos, lowercase)
- **Auto-preenchido**: Sim (trigger `before_insert_update_alias_normalizar`)
- **Usado para**: Busca rápida e comparação

### 5. `origem` (VARCHAR)
- **O que é**: Como o alias foi criado
- **Valores possíveis**:
  - `'manual'` - Criado manualmente por humano
  - `'auto'` - Criado automaticamente pelo script
  - `'llm'` - Sugerido pelo LLM (futuro)
- **Padrão**: `'manual'`

### 6. `confianca` (DECIMAL)
- **O que é**: Nível de confiança do alias (0.0 a 1.0)
- **Interpretação**:
  - `1.0` - Certeza absoluta (criado manualmente)
  - `0.95` - Alta confiança (similaridade ≥95%)
  - `0.90` - Boa confiança (similaridade 90-94%)
  - `0.80` - Média confiança (similaridade 80-89%)
- **Padrão**: `1.0`

### 7. `created_at` (TIMESTAMP)
- **O que é**: Data e hora de criação do alias
- **Exemplo**: `2025-10-16 03:04:12`
- **Auto-preenchido**: Sim (NOW())

### 8. `created_by` (VARCHAR)
- **O que é**: Quem/o que criou o alias
- **Valores comuns**:
  - `'script'` - Criado pelo script `popular_aliases.py`
  - `'admin'` - Criado manualmente por administrador
  - `'system'` - Criado pelo sistema
- **Padrão**: `'system'`

---

## 🎯 Como Funciona na Prática

### Exemplo 1: Alias Bidirecionais

Quando dois produtos são detectados como duplicatas, o sistema cria **2 aliases** (um para cada):

```
┌─────────────────────────────────────────────────────────────┐
│ produtos_tabela                                             │
├──────┬─────────────────────────────────────────────────────┤
│ ID   │ Nome                                                 │
├──────┼─────────────────────────────────────────────────────┤
│ 222  │ Abóbora Cabotiá                                      │
│ 435  │ Abóbora Kabotiá                                      │
└──────┴─────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ produtos_aliases                                                             │
├────┬───────────┬──────────────────┬─────────────────────┬────────┬──────────┤
│ ID │ produto_id│ alias            │ alias_normalizado   │ origem │ confianca│
├────┼───────────┼──────────────────┼─────────────────────┼────────┼──────────┤
│ 10 │ 222       │ Abóbora Kabotiá  │ abobora kabotia     │ auto   │ 0.93     │
│ 11 │ 435       │ Abóbora Cabotiá  │ abobora cabotia     │ auto   │ 0.93     │
└────┴───────────┴──────────────────┴─────────────────────┴────────┴──────────┘
```

**Resultado**:
- Buscar "Abóbora Kabotiá" → Pode encontrar produto 222 **OU** produto 435
- Buscar "Abóbora Cabotiá" → Pode encontrar produto 222 **OU** produto 435
- **Ambos os nomes** levam aos **mesmos produtos**!

---

### Exemplo 2: Busca Usando Alias

```sql
-- LLM extrai: "Abóbora Kabotiá"
-- Sistema normaliza: "abobora kabotia"

-- Passo 1: Busca exata em produtos_tabela
SELECT * FROM produtos_tabela
WHERE nome_normalizado = 'abobora kabotia';
-- Resultado: Produto 435 ✓

-- Passo 2 (se não encontrar): Busca em aliases
SELECT p.* FROM produtos_tabela p
JOIN produtos_aliases pa ON p.id = pa.produto_id
WHERE pa.alias_normalizado = 'abobora kabotia';
-- Resultado: Produto 222 ✓ (via alias)
```

---

### Exemplo 3: Dados Reais do Banco

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Alias ID: 10                                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ produto_id:        222                                                       │
│ Produto (real):    "Abóbora Cabotiá"                                         │
│ Alias (nome alt):  "Abóbora Kabotiá"        ← Nome alternativo              │
│ alias_normalizado: "abobora kabotia"         ← Usado na busca               │
│ origem:            auto                      ← Criado automaticamente        │
│ confianca:         0.93                      ← 93% de certeza                │
│ created_by:        script                    ← Criado pelo popular_aliases.py│
│ created_at:        2025-10-16 03:04:12       ← Quando foi criado             │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Interpretação**:
- O produto **real** no banco é "Abóbora Cabotiá" (ID 222)
- Mas ele **também pode ser encontrado** pelo nome "Abóbora Kabotiá"
- Confiança: 93% (similaridade entre os nomes)
- Foi criado automaticamente pelo script

---

## 🔄 Fluxo de Criação de Alias

### Automático (Script)

```bash
python scripts/popular_aliases.py --auto
```

**Processo**:

```
1. Script busca duplicatas potenciais (similaridade ≥90%)
   ├─ Produto 222: "Abóbora Cabotiá"
   └─ Produto 435: "Abóbora Kabotiá"
   └─ Similaridade: 93.3%

2. Para cada par, cria 2 aliases bidirecionais:

   ┌─────────────────────────────────────────────────────┐
   │ INSERT INTO produtos_aliases (                      │
   │   produto_id,                                       │
   │   alias,                                            │
   │   origem,                                           │
   │   confianca,                                        │
   │   created_by                                        │
   │ ) VALUES (                                          │
   │   222,                     -- Produto principal     │
   │   'Abóbora Kabotiá',       -- Nome alternativo     │
   │   'auto',                  -- Origem               │
   │   0.93,                    -- Confiança (93%)      │
   │   'script'                 -- Criado pelo script   │
   │ );                                                  │
   └─────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────┐
   │ INSERT INTO produtos_aliases (                      │
   │   produto_id,                                       │
   │   alias,                                            │
   │   origem,                                           │
   │   confianca,                                        │
   │   created_by                                        │
   │ ) VALUES (                                          │
   │   435,                     -- Produto principal     │
   │   'Abóbora Cabotiá',       -- Nome alternativo     │
   │   'auto',                  -- Origem               │
   │   0.93,                    -- Confiança (93%)      │
   │   'script'                 -- Criado pelo script   │
   │ );                                                  │
   └─────────────────────────────────────────────────────┘

3. Trigger preenche automaticamente:
   ├─ alias_normalizado = normalizar_nome(alias)
   ├─ created_at = NOW()
   └─ (outros campos já foram informados)
```

---

### Manual (SQL Direto)

```sql
-- Adicionar alias manualmente
INSERT INTO produtos_aliases (produto_id, alias, origem, confianca, created_by)
VALUES (222, 'Kabotiá', 'manual', 1.0, 'admin');

-- Ou usando função auxiliar
SELECT adicionar_alias(
    p_produto_id := 222,
    p_alias := 'Kabotiá',
    p_origem := 'manual',
    p_confianca := 1.0
);
```

---

## 🔍 Consultas Úteis

### Ver todos os aliases de um produto

```sql
SELECT
    pa.alias,
    pa.origem,
    pa.confianca,
    pa.created_at
FROM produtos_aliases pa
WHERE pa.produto_id = 222
ORDER BY pa.created_at DESC;
```

**Resultado**:
```
alias                origem    confianca    created_at
------------------   ------    ---------    -------------------
Abóbora Kabotiá      auto      0.93         2025-10-16 03:04:12
Kabotiá              manual    1.00         2025-10-16 10:30:00
```

### Ver produtos com mais aliases

```sql
SELECT
    p.id,
    p.nome,
    COUNT(pa.id) as total_aliases,
    STRING_AGG(pa.alias, ', ') as aliases
FROM produtos_tabela p
LEFT JOIN produtos_aliases pa ON p.id = pa.produto_id
GROUP BY p.id, p.nome
HAVING COUNT(pa.id) > 0
ORDER BY total_aliases DESC
LIMIT 10;
```

### Buscar produto por alias

```sql
SELECT
    p.*,
    pa.alias as encontrado_via_alias,
    pa.confianca
FROM produtos_tabela p
JOIN produtos_aliases pa ON p.id = pa.produto_id
WHERE pa.alias_normalizado = normalizar_nome('Kabotiá');
```

---

## ⚙️ Trigger Automático

Quando você insere um alias, o sistema **preenche automaticamente** o campo `alias_normalizado`:

```sql
-- Trigger
CREATE TRIGGER before_insert_update_alias_normalizar
    BEFORE INSERT OR UPDATE OF alias
    ON produtos_aliases
    FOR EACH ROW
    EXECUTE FUNCTION trigger_normalizar_alias();

-- Função do trigger
CREATE OR REPLACE FUNCTION trigger_normalizar_alias()
RETURNS TRIGGER AS $$
BEGIN
    NEW.alias_normalizado := normalizar_nome(NEW.alias);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Exemplo**:
```sql
INSERT INTO produtos_aliases (produto_id, alias)
VALUES (222, 'Abóbora Kabotiá!!!');

-- Trigger preenche automaticamente:
-- alias_normalizado = 'abobora kabotia'
```

---

## 📊 Índices para Performance

```sql
-- Índice no produto_id (para JOIN rápido)
CREATE INDEX idx_aliases_produto_id ON produtos_aliases(produto_id);

-- Índice no alias_normalizado (para busca rápida)
CREATE INDEX idx_aliases_normalizado ON produtos_aliases(alias_normalizado);

-- Índice GIN para busca fuzzy (trigramas)
CREATE INDEX idx_aliases_trgm ON produtos_aliases
USING GIN (alias_normalizado gin_trgm_ops);
```

---

## 🎯 Resumo

**A tabela de aliases funciona como um "dicionário de sinônimos"**:

| Produto Real (produtos_tabela) | Aliases (nomes alternativos) |
|-------------------------------|------------------------------|
| Abóbora Cabotiá (ID 222) | • Abóbora Kabotiá<br>• Kabotiá |
| Queijo Mussarela Fatiado (ID 264) | • Queijo Mussarela Fatiada |
| Contrafilé Bovino (ID 270) | • Contra Filé Bovino |

**Quando o LLM extrai qualquer um desses nomes, o sistema encontra o produto correto!** ✅

---

**Última atualização**: 2025-10-16
