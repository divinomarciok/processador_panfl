# Guia: Sistema Anti-Duplicação com Fuzzy + Aliases

## 📋 Visão Geral

Sistema de 4 camadas para evitar produtos duplicados:

1. **Normalização aprimorada** - Remove acentos, caracteres especiais
2. **Tabela de aliases** - Sinônimos manuais ou automáticos
3. **Busca fuzzy** - Detecta variações ortográficas (Levenshtein)
4. **Busca inteligente** - Combina todas as estratégias

## 🚀 Instalação

### 1. Aplicar Migration

```bash
cd /home/divinopc/repos/softwareclaude/app_precos_claude

# Conectar ao PostgreSQL
psql -U user -d databasev1

# Executar migration
\i database/migration_fuzzy_aliases.sql
```

**O que a migration faz**:
- ✅ Instala extensões `fuzzystrmatch` e `pg_trgm`
- ✅ Melhora função `normalizar_nome()` (remove acentos)
- ✅ Cria tabela `produtos_aliases`
- ✅ Cria funções de busca fuzzy
- ✅ Cria função mestra `buscar_produto_inteligente()`
- ✅ Atualiza `nome_normalizado` em produtos existentes

### 2. Verificar Instalação

```sql
-- Ver relatório de instalação (gerado automaticamente)
-- Deve mostrar:
-- ✓ Extensões instaladas
-- ✓ Funções criadas
-- ✓ Total de produtos e aliases

-- Testar normalização
SELECT normalizar_nome('Abóbora Kabotia 500g');
-- Resultado esperado: 'abobora kabotia 500g'

-- Ver duplicatas potenciais
SELECT * FROM vw_duplicatas_potenciais LIMIT 10;
```

## 🔧 Como Funciona

### Fluxo de Busca `buscar_produto_inteligente()`

```
Recebe: "Abobora Cabotia"

┌─────────────────────────────────────┐
│ 1. BUSCA EXATA (nome_normalizado)  │
│    ❌ Não encontrado                │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ 2. BUSCA POR ALIAS (exato)         │
│    ✓ Encontrado via alias!          │
│    "Kabotia" → Produto ID 123       │
└─────────────────────────────────────┘
           ↓
      RETORNA produto ID 123
```

**Se não encontrar**:
```
3. BUSCA FUZZY EM ALIASES
   - Procura aliases similares (Levenshtein ≤ 3)
   - Exemplo: "Caботia" match com "Cabotia"

4. BUSCA FUZZY EM PRODUTOS
   - Procura produtos similares (similaridade ≥ 85%)
   - Exemplo: "Abobra Cabotia" match com "Abóbora Cabotiá"
```

### Função `normalizar_nome()` Aprimorada

**Antes**:
```sql
normalizar_nome('Abóbora Kabotia!!!')
-- Resultado: 'abóbora kabotia!!!'  ❌ Mantém acentos e pontuação
```

**Depois**:
```sql
normalizar_nome('Abóbora Kabotia!!!')
-- Resultado: 'abobora kabotia'  ✅ Remove acentos e caracteres especiais
```

**Transformações**:
1. Lowercase: `Abóbora` → `abóbora`
2. Remove acentos: `abóbora` → `abobora`
3. Remove caracteres especiais: `kabotia!!!` → `kabotia`
4. Remove espaços múltiplos: `abobora  kabotia` → `abobora kabotia`
5. Trim: ` abobora kabotia ` → `abobora kabotia`

## 📊 Tabela de Aliases

### Estrutura

```sql
CREATE TABLE produtos_aliases (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER,           -- ID do produto principal
    alias VARCHAR(255),            -- Nome alternativo
    alias_normalizado VARCHAR(255), -- Nome normalizado (auto-preenchido)
    origem VARCHAR(50),            -- 'manual', 'auto', 'llm'
    confianca DECIMAL(3,2),        -- 0.0 a 1.0
    created_at TIMESTAMP,
    created_by VARCHAR(100)
);
```

### Como a Tabela é Preenchida

#### 1️⃣ Automaticamente (Script)

```bash
# Modo interativo (revisa cada duplicata)
python scripts/popular_aliases.py

# Modo automático (apenas alta confiança ≥90%)
python scripts/popular_aliases.py --auto

# Gerar relatório
python scripts/popular_aliases.py --relatorio
```

**Exemplo de execução**:
```
Duplicata 1/10
======================================================================
Produto 1: Abóbora Kabotia (ID: 123)
Produto 2: Abobora Cabotia (ID: 456)
Similaridade: 92.3% (distância: 2)

Criar aliases bidirecionais? [s/N/q(sair)]: s
✓ Alias criado: 'Abobora Cabotia' → Produto ID 123
✓ Alias criado: 'Abóbora Kabotia' → Produto ID 456
```

**O que acontece**:
- Produto 123 ganha alias "Abobora Cabotia"
- Produto 456 ganha alias "Abóbora Kabotia"
- Agora ambos os nomes apontam para os mesmos produtos!

#### 2️⃣ Manualmente (SQL)

```sql
-- Adicionar alias manualmente
INSERT INTO produtos_aliases (produto_id, alias, origem, confianca, created_by)
VALUES (123, 'Kabotia', 'manual', 1.0, 'admin');

-- Ou usar função auxiliar
SELECT adicionar_alias(
    p_produto_id := 123,
    p_alias := 'Kabotia',
    p_origem := 'manual',
    p_confianca := 1.0
);
```

#### 3️⃣ Via LLM (Futuro)

Possível adicionar prompt ao LLM para sugerir aliases:
```python
# No processamento do panfleto
if produto_novo:
    # LLM pode sugerir aliases
    aliases_sugeridos = dados_llm.get('aliases', [])
    for alias in aliases_sugeridos:
        adicionar_alias(produto_id, alias, origem='llm', confianca=0.8)
```

### Exemplos de Uso

```sql
-- Buscar produto usando alias
SELECT * FROM buscar_produto_por_alias('Kabotia');

-- Busca inteligente (tenta tudo)
SELECT * FROM buscar_produto_inteligente('Abobora Cabotia');

-- Ver aliases de um produto
SELECT * FROM produtos_aliases WHERE produto_id = 123;

-- Ver produtos com mais aliases
SELECT
    p.nome,
    COUNT(pa.id) as total_aliases
FROM produtos_tabela p
LEFT JOIN produtos_aliases pa ON p.id = pa.produto_id
GROUP BY p.id, p.nome
ORDER BY total_aliases DESC
LIMIT 10;
```

## 🔍 Busca Fuzzy (Levenshtein)

### Como Funciona

**Distância de Levenshtein**: Número mínimo de operações (inserir, deletar, substituir) para transformar uma string em outra.

```
"Kabotia" → "Cabotia"
Operação: Substituir 'K' por 'C'
Distância: 1 ✅ (muito similar)

"Abobora" → "Aboboa"
Operações: Inserir 'r', deletar 'a'
Distância: 2 ✅ (similar)

"Coca Cola" → "Pepsi"
Distância: 8 ❌ (muito diferente)
```

### Similaridade (0 a 1)

```
Similaridade = 1 - (distância_levenshtein / comprimento_maior)

Exemplo:
"Kabotia" (7 chars) vs "Cabotia" (7 chars)
Distância: 1
Similaridade: 1 - (1 / 7) = 0.857 = 85.7%
```

### Configuração

```python
# Em src/database.py
produto = db.buscar_produto_por_nome(
    nome="Abobora Cabotia",
    margem=0.85  # Similaridade mínima (85%)
)
```

**Recomendações**:
- `margem=0.95` - Muito restritivo (apenas erros de digitação)
- `margem=0.85` - **Recomendado** (variações ortográficas)
- `margem=0.75` - Muito permissivo (pode gerar falsos positivos)

## 📈 Monitoramento e Manutenção

### Relatório de Duplicatas

```bash
# Ver duplicatas potenciais
python scripts/popular_aliases.py --relatorio
```

Saída:
```
======================================================================
RELATÓRIO DE ALIASES E DUPLICATAS
======================================================================
Total de produtos: 1250
Total de aliases: 47
Duplicatas potenciais (≥80%): 12

Aliases por origem:
  - auto: 35
  - manual: 10
  - llm: 2

Produtos com mais aliases:
  - Abóbora Cabotiá: 3 aliases
  - Coca-Cola Lata: 2 aliases
======================================================================
```

### Queries Úteis

```sql
-- 1. Ver duplicatas não resolvidas
SELECT * FROM vw_duplicatas_potenciais
WHERE similaridade >= 0.85
ORDER BY similaridade DESC;

-- 2. Produtos sem aliases (candidatos a duplicação)
SELECT p.*
FROM produtos_tabela p
LEFT JOIN produtos_aliases pa ON p.id = pa.produto_id
WHERE pa.id IS NULL
  AND p.created_at > NOW() - INTERVAL '7 days'
ORDER BY p.created_at DESC;

-- 3. Testar busca inteligente
SELECT
    nome, similaridade, origem_match
FROM buscar_produto_inteligente('Abobora Kabotia', 0.85);

-- 4. Estatísticas de matches
SELECT
    origem_match,
    COUNT(*) as total
FROM (
    SELECT buscar_produto_inteligente('Teste', 0.85) as resultado
    FROM produtos_tabela
    LIMIT 100
) sub
GROUP BY origem_match;
```

## 🛠️ Workflow Recomendado

### Pós-Processamento de Panfleto

```bash
# 1. Processar panfleto normalmente
python main.py panfletos/novo_panfleto.jpg

# 2. Ver duplicatas geradas (se houver)
python scripts/popular_aliases.py --relatorio

# 3. Revisar e criar aliases (modo interativo)
python scripts/popular_aliases.py --similaridade 0.85

# 4. (Opcional) Mesclar duplicatas reais
python scripts/mesclar_duplicatas.py
```

### Manutenção Semanal

```bash
# Executar automaticamente (cron job)
0 2 * * 0 cd /app && python scripts/popular_aliases.py --auto --similaridade 0.90
```

## 🎯 Casos de Uso

### Exemplo 1: Variações Ortográficas

**Problema**: "Abóbora Kabotia", "Abobora Cabotia", "Kabotia"

**Solução**:
1. Normalização: Todos viram `abobora kabotia` ou `kabotia`
2. Fuzzy: Detecta `kabotia` ≈ `cabotia` (85% similar)
3. Alias: Cria "Kabotia" → Produto principal

**Resultado**: 3 nomes diferentes → 1 produto único ✅

### Exemplo 2: Marcas com Hífen

**Problema**: "Coca Cola", "Coca-Cola", "CocaCola"

**Solução**:
1. Normalização: Todos viram `coca cola` ou `cocacola`
2. Fuzzy: Detecta similaridade
3. Alias: Criar manualmente "Coca Cola" e "CocaCola" → "Coca-Cola"

### Exemplo 3: Abreviações

**Problema**: "Óleo de Soja Liza", "Oleo Soja Liza", "Liza Soja"

**Solução**:
- Criar aliases manualmente:
```sql
SELECT adicionar_alias(produto_id, 'Oleo Soja Liza', 'manual', 1.0);
SELECT adicionar_alias(produto_id, 'Liza Soja', 'manual', 0.9);
```

## 🚨 Troubleshooting

### Problema: Migration falha em `CREATE EXTENSION unaccent`

**Solução**: Extensão não disponível, mas código usa fallback automático com `TRANSLATE`.

```sql
-- Verificar se unaccent está disponível
SELECT * FROM pg_available_extensions WHERE name = 'unaccent';

-- Se não disponível, a função usa TRANSLATE (já implementado)
```

### Problema: Muitos falsos positivos (produtos diferentes sendo mesclados)

**Solução**: Aumentar threshold de similaridade

```python
# Em src/database.py
produto = db.buscar_produto_por_nome(nome, margem=0.90)  # De 0.85 para 0.90
```

### Problema: Duplicatas não detectadas

**Solução**:
1. Verificar normalização: `SELECT normalizar_nome('Produto X');`
2. Reduzir threshold: `margem=0.80`
3. Criar aliases manualmente

## 📚 Referências

- **Levenshtein Distance**: https://en.wikipedia.org/wiki/Levenshtein_distance
- **PostgreSQL fuzzystrmatch**: https://www.postgresql.org/docs/current/fuzzystrmatch.html
- **PostgreSQL pg_trgm**: https://www.postgresql.org/docs/current/pgtrgm.html

---

**Última atualização**: 2025-10-16
