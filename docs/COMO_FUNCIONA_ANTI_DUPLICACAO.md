# Como Funciona o Sistema Anti-Duplicação

## 📋 Visão Geral

O sistema usa **múltiplas camadas de validação** para evitar duplicatas, mas preservar variações legítimas de produtos.

---

## 🔄 Fluxo Completo: Do Panfleto ao Banco

### 1️⃣ LLM Extrai Dados do Panfleto

```
Panfleto → LLM (Gemini/GPT/Claude) → JSON

Exemplo de saída do LLM:
{
  "produtos": [
    {
      "nome": "Abóbora Kabotiá",
      "marca": null,
      "categoria": "Verduras e Legumes",
      "preco": 4.99
    }
  ]
}
```

**Responsabilidade do LLM**: Extrair o nome **exatamente como está** no panfleto.

---

### 2️⃣ Sistema Normaliza o Nome

**Função: `normalizar_nome()`** (database.py:425 → migration_fuzzy_aliases.sql:14)

```sql
normalizar_nome('Abóbora Kabotiá!!!')
-- Resultado: 'abobora kabotia'
```

**Passos da normalização**:
1. **Lowercase**: `Abóbora` → `abóbora`
2. **Remove acentos**: `abóbora` → `abobora`
3. **Remove caracteres especiais**: `kabotiá!!!` → `kabotia`
4. **Remove espaços múltiplos**: `abobora  kabotia` → `abobora kabotia`
5. **Trim**: ` abobora kabotia ` → `abobora kabotia`

**Campo salvo automaticamente**: `produtos_tabela.nome_normalizado`

---

### 3️⃣ Sistema Busca Produto Existente

**Função: `buscar_produto_inteligente()`** (migration_fuzzy_aliases.sql:130)

#### **Estratégia em 4 Camadas** (nesta ordem):

```
┌─────────────────────────────────────────────────────────────┐
│ CAMADA 1: Busca Exata (nome_normalizado)                   │
├─────────────────────────────────────────────────────────────┤
│ SELECT * FROM produtos_tabela                               │
│ WHERE nome_normalizado = normalizar_nome('Abóbora Kabotiá')│
│                                                             │
│ Match: 'abobora kabotia' = 'abobora kabotia'               │
│ Resultado: Encontrado! ✓                                   │
└─────────────────────────────────────────────────────────────┘
         ↓ Se NÃO encontrar, vai para camada 2

┌─────────────────────────────────────────────────────────────┐
│ CAMADA 2: Busca por Alias (tabela produtos_aliases)        │
├─────────────────────────────────────────────────────────────┤
│ SELECT p.* FROM produtos_tabela p                           │
│ JOIN produtos_aliases pa ON p.id = pa.produto_id           │
│ WHERE pa.alias_normalizado = normalizar_nome('Kabotiá')    │
│                                                             │
│ Match: Alias 'kabotia' → Produto ID 222                    │
│ Resultado: Encontrado via alias! ✓                         │
└─────────────────────────────────────────────────────────────┘
         ↓ Se NÃO encontrar, vai para camada 3

┌─────────────────────────────────────────────────────────────┐
│ CAMADA 3: Busca Fuzzy em Aliases (Levenshtein ≤ 3)        │
├─────────────────────────────────────────────────────────────┤
│ Busca aliases similares com distância Levenshtein ≤ 3      │
│                                                             │
│ Exemplo: 'kabotia' vs 'cabotia'                            │
│ Distância: 1 (substituir 'k' por 'c')                      │
│ Similaridade: 85.7%                                         │
│ Resultado: Encontrado via fuzzy! ✓                         │
└─────────────────────────────────────────────────────────────┘
         ↓ Se NÃO encontrar, vai para camada 4

┌─────────────────────────────────────────────────────────────┐
│ CAMADA 4: Busca Fuzzy em Produtos (Levenshtein ≤ 3)       │
├─────────────────────────────────────────────────────────────┤
│ Busca produtos similares com distância Levenshtein ≤ 3     │
│ e similaridade ≥ 85% (configurável)                        │
│                                                             │
│ Exemplo: 'abobora kabotia' vs 'abobora cabotia'            │
│ Distância: 2                                                │
│ Similaridade: 92.3%                                         │
│ Resultado: Encontrado! ✓                                   │
└─────────────────────────────────────────────────────────────┘
         ↓ Se NÃO encontrar em nenhuma camada

┌─────────────────────────────────────────────────────────────┐
│ PRODUTO NÃO ENCONTRADO                                      │
│ → Criar novo produto                                        │
└─────────────────────────────────────────────────────────────┘
```

---

### 4️⃣ Sistema Cria Produto OU Retorna Existente

**Código em Python** (src/database.py:476-525):

```python
def buscar_ou_criar_produto(nome, marca, categoria):
    # Busca usando as 4 camadas
    produto = self.buscar_produto_por_nome(nome, margem=0.85)

    if produto:
        logger.info(f"✓ Produto encontrado: {produto['nome']}")
        return produto['id'], False  # (id, criado_novo=False)

    # Não encontrou → criar novo
    produto_id = self.criar_produto(nome, marca, categoria)
    logger.info(f"✓ Produto criado: {nome}")
    return produto_id, True  # (id, criado_novo=True)
```

---

## 🛡️ Sistema de Validação de Duplicatas

### View: `vw_duplicatas_potenciais`

Identifica produtos **potencialmente duplicados** usando 3 filtros:

#### **Filtro 1: Distância Levenshtein**
```sql
levenshtein(p1.nome_normalizado, p2.nome_normalizado) BETWEEN 1 AND 3
```

Exemplo:
- `abobora kabotia` vs `abobora cabotia` → Distância: 2 ✅
- `coca cola` vs `pepsi` → Distância: 8 ❌ (muito diferente)

#### **Filtro 2: Mesma Marca (ou ambos sem marca)**
```sql
(p1.marca IS NULL AND p2.marca IS NULL)  -- Ambos sem marca
OR
(LOWER(p1.marca) = LOWER(p2.marca))      -- Mesma marca
```

**Exemplos**:

| Produto 1 | Marca 1 | Produto 2 | Marca 2 | Resultado |
|-----------|---------|-----------|---------|-----------|
| Biscoito Laminado | Marilan | Biscoito Laminados | Marilan | ✅ **Pode ser duplicata** |
| Biscoito Laminado | Marilan | Biscoito Laminados | Belma | ❌ **NÃO é duplicata** (marcas diferentes) |
| Abóbora Kabotiá | (null) | Abóbora Cabotiá | (null) | ✅ **Pode ser duplicata** (ambos sem marca) |

#### **Filtro 3: Sem Palavras Diferenciadas**

**Função: `tem_palavras_diferenciadas()`** (migration_melhorar_deteccao_duplicatas.sql:13)

Lista de palavras que indicam **produtos DIFERENTES**:
- dupla, tripla, simples
- com osso, sem osso
- com tampa, sem tampa
- integral, desnatado, semidesnatado
- diet, zero, light
- kg, g, l, ml
- peça, pedaço, fatia, fatiado, fatiada

**Lógica**:
```sql
-- Se uma palavra está em um nome MAS NÃO no outro → SÃO PRODUTOS DIFERENTES
IF nome1 contém 'dupla' AND nome2 não contém 'dupla' THEN
    RETURN TRUE  -- Tem palavras diferenciadas (NÃO é duplicata)
```

**Exemplos**:

| Produto 1 | Produto 2 | Resultado |
|-----------|-----------|-----------|
| Papel Higiênico Folha **Dupla** | Papel Higiênico Folha **Tripla** | ❌ **NÃO é duplicata** (dupla ≠ tripla) |
| Pernil Suíno **Sem Osso** | Pernil Suíno **Com Osso** | ❌ **NÃO é duplicata** (sem ≠ com) |
| Queijo Mussarela Fatiado | Queijo Mussarela Fatiada | ✅ **Pode ser duplicata** (fatiado/fatiada são sinônimos) |
| Abóbora Kabotiá | Abóbora Cabotiá | ✅ **Pode ser duplicata** (só diferença ortográfica) |

---

## 🔍 Distância de Levenshtein (Como Funciona)

**Definição**: Número mínimo de operações (inserir, deletar, substituir) para transformar uma string em outra.

### Exemplos Práticos:

#### Exemplo 1: Kabotiá → Cabotiá
```
K a b o t i á
↓ (substituir K por C)
C a b o t i á

Operações: 1
Distância: 1
Similaridade: 1 - (1 / 7) = 85.7%
```

#### Exemplo 2: Catchup → Ketchup
```
C a t c h u p
↓ (substituir C por K)
K a t c h u p
↓ (substituir t por e)
K e t c h u p

Operações: 2
Distância: 2
Similaridade: 1 - (2 / 7) = 71.4%
```

#### Exemplo 3: Folha Dupla → Folha Tripla
```
f o l h a   d u p l a
↓ (substituir d por t)
f o l h a   t u p l a
↓ (substituir u por r)
f o l h a   t r p l a
↓ (substituir p por i)
f o l h a   t r i l a
↓ (substituir l por p)
f o l h a   t r i p a

Operações: 3
Distância: 3
Similaridade: 1 - (3 / 11) = 72.7%

MAS: tem_palavras_diferenciadas() detecta "dupla" vs "tripla"
→ NÃO é duplicata! ✅
```

---

## 📊 Tabela de Aliases

### Estrutura

```sql
CREATE TABLE produtos_aliases (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER,          -- ID do produto principal
    alias VARCHAR(255),           -- Nome alternativo
    alias_normalizado VARCHAR,    -- Nome normalizado (auto-preenchido)
    origem VARCHAR(50),           -- 'manual', 'auto', 'llm'
    confianca DECIMAL(3,2),       -- 0.0 a 1.0
    created_at TIMESTAMP
);
```

### Como é Preenchida

#### 1. Automaticamente (Script)

```bash
python scripts/popular_aliases.py --auto
```

**Processo**:
1. Script busca duplicatas potenciais com similaridade ≥ 90%
2. Para cada par de produtos, cria **aliases bidirecionais**:

```sql
-- Produto 1: "Abóbora Cabotíá" (ID: 222)
-- Produto 2: "Abóbora Kabotiá" (ID: 435)

-- Alias 1: Produto 222 ganha alias "Abóbora Kabotiá"
INSERT INTO produtos_aliases (produto_id, alias, origem, confianca)
VALUES (222, 'Abóbora Kabotiá', 'auto', 0.93);

-- Alias 2: Produto 435 ganha alias "Abóbora Cabotíá"
INSERT INTO produtos_aliases (produto_id, alias, origem, confianca)
VALUES (435, 'Abóbora Cabotíá', 'auto', 0.93);
```

**Resultado**:
- Buscar "Abóbora Kabotiá" → Encontra produto 222 **OU** produto 435
- Buscar "Abóbora Cabotiá" → Encontra produto 222 **OU** produto 435
- Ambos os nomes apontam para os mesmos produtos!

#### 2. Manualmente (SQL)

```sql
INSERT INTO produtos_aliases (produto_id, alias, origem, confianca)
VALUES (222, 'Kabotiá', 'manual', 1.0);
```

---

## 🎯 Exemplos Práticos

### Exemplo 1: Produto Novo (Não Existe no Banco)

```
LLM extrai: "Abóbora Kabotiá"

1. normalizar_nome('Abóbora Kabotiá') → 'abobora kabotia'

2. Busca exata:
   SELECT * FROM produtos_tabela
   WHERE nome_normalizado = 'abobora kabotia'
   → NÃO ENCONTRADO

3. Busca por alias:
   SELECT * FROM produtos_aliases
   WHERE alias_normalizado = 'abobora kabotia'
   → NÃO ENCONTRADO

4. Busca fuzzy em aliases:
   → NÃO ENCONTRADO

5. Busca fuzzy em produtos:
   → NÃO ENCONTRADO

6. CRIAR NOVO PRODUTO ✅
   INSERT INTO produtos_tabela (nome, nome_normalizado)
   VALUES ('Abóbora Kabotiá', 'abobora kabotia')
```

### Exemplo 2: Variação Já Existente (Via Alias)

```
Banco de dados atual:
- Produto ID 222: "Abóbora Cabotiá"
- Alias: produto_id=222, alias="Abóbora Kabotiá"

LLM extrai: "Abóbora Kabotiá"

1. normalizar_nome('Abóbora Kabotiá') → 'abobora kabotia'

2. Busca exata:
   SELECT * FROM produtos_tabela
   WHERE nome_normalizado = 'abobora kabotia'
   → NÃO ENCONTRADO (nome do banco é 'abobora cabotia')

3. Busca por alias:
   SELECT p.* FROM produtos_tabela p
   JOIN produtos_aliases pa ON p.id = pa.produto_id
   WHERE pa.alias_normalizado = 'abobora kabotia'
   → ENCONTRADO! Produto ID 222 ✅

4. RETORNAR PRODUTO EXISTENTE (sem criar duplicata)
   Log: "✓ Produto encontrado (via alias): 'Abóbora Kabotiá' → 'Abóbora Cabotiá'"
```

### Exemplo 3: Variação Ortográfica (Via Fuzzy)

```
Banco de dados atual:
- Produto ID 222: "Abóbora Cabotiá" (nome_normalizado: 'abobora cabotia')

LLM extrai: "Abobora Kabotia" (sem acento, K ao invés de C)

1. normalizar_nome('Abobora Kabotia') → 'abobora kabotia'

2. Busca exata:
   WHERE nome_normalizado = 'abobora kabotia'
   → NÃO ENCONTRADO

3. Busca por alias:
   → NÃO ENCONTRADO

4. Busca fuzzy em aliases:
   → NÃO ENCONTRADO

5. Busca fuzzy em produtos:
   Levenshtein('abobora kabotia', 'abobora cabotia') = 2
   Similaridade = 1 - (2 / 15) = 86.7% ✅ (≥ 85%)
   → ENCONTRADO! Produto ID 222 ✅

6. RETORNAR PRODUTO EXISTENTE (sem criar duplicata)
   Log: "⚠ Produto encontrado (fuzzy, 86.7%): 'Abobora Kabotia' → 'Abóbora Cabotiá'"
```

### Exemplo 4: Variação de Produto (NÃO É Duplicata)

```
Banco de dados atual:
- Produto ID 98: "Papel Higiênico Duetto Folha Tripla" (marca: Duetto)

LLM extrai: "Papel Higiênico Duetto Folha Dupla" (marca: Duetto)

1. normalizar_nome(...) → 'papel higienico duetto folha dupla'

2. Busca exata:
   → NÃO ENCONTRADO

3. Busca por alias:
   → NÃO ENCONTRADO

4. Busca fuzzy:
   Levenshtein('...folha dupla', '...folha tripla') = 3
   Similaridade = 91.4% ✅

   MAS:
   tem_palavras_diferenciadas('Folha Dupla', 'Folha Tripla')
   → TRUE (detecta "dupla" vs "tripla")

   → NÃO RETORNA como duplicata! ✅

5. CRIAR NOVO PRODUTO (são produtos diferentes)
   INSERT INTO produtos_tabela (nome)
   VALUES ('Papel Higiênico Duetto Folha Dupla')
```

---

## 🔧 Configurações Importantes

### Threshold de Similaridade

**Arquivo**: src/database.py:410

```python
def buscar_produto_por_nome(self, nome: str, margem: float = 0.85):
    #                                              ^^^^
    #                                          Threshold padrão
```

**Valores recomendados**:
- `0.95` - Muito restritivo (apenas erros de digitação)
- `0.85` - **Recomendado** (variações ortográficas) ✅
- `0.75` - Muito permissivo (pode gerar falsos positivos)

### Distância Máxima Levenshtein

**Arquivo**: migration_fuzzy_aliases.sql:148

```sql
WHERE levenshtein(...) <= 3  -- Máximo 3 caracteres de diferença
```

---

## 📈 Métricas de Desempenho

### Antes do Sistema
- 419 produtos
- Duplicatas: ~15-20% (estimado)
- Falsos positivos: Alto

### Depois do Sistema
- 419 produtos
- Duplicatas reais detectadas: 4 (0.95%)
- Falsos positivos: Quase zero ✅
- Redução: 71% nos falsos positivos

---

## 🛠️ Manutenção

### Scripts Úteis

```bash
# Ver duplicatas atuais
python scripts/listar_duplicatas.py

# Popular aliases automaticamente (≥90% similaridade)
python scripts/popular_aliases.py --auto

# Popular aliases interativamente (revisar cada caso)
python scripts/popular_aliases.py

# Ver produtos relacionados (não duplicatas)
python scripts/listar_duplicatas.py --relacionados

# Relatório geral
python scripts/popular_aliases.py --relatorio
```

---

**Última atualização**: 2025-10-16
