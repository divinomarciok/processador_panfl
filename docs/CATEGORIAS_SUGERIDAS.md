# Categorias Sugeridas - Análise e Melhoria do Sistema de Categorização

## Visão Geral

A partir da versão 1.1.0, o sistema captura a **categoria original** sugerida pelo LLM antes do mapeamento inteligente. Isso permite identificar padrões, analisar quais categorias não estão sendo mapeadas corretamente, e melhorar continuamente o sistema de categorização.

## Como Funciona

### Fluxo de Dados

1. **LLM Sugere Categoria**: Quando o LLM processa um panfleto, ele sugere uma categoria baseada na análise da imagem (ex: "Achocolatados e Misturas para Bebidas")

2. **Sistema Mapeia**: O sistema tenta mapear essa categoria usando o `MAPEAMENTO_CATEGORIAS` em `src/database.py`

3. **Categorias Armazenadas**:
   - `categoria_sugerida`: A categoria original do LLM (preservada)
   - `categoria`: A categoria mapeada para o banco (ou "Outros" se não encontrada)
   - `categoria_id`: Foreign key para a tabela `categorias`

4. **Análise Futura**: Você pode consultar as categorias sugeridas mais frequentes e decidir:
   - Adicionar ao mapeamento inteligente
   - Criar nova categoria no banco
   - Melhorar o prompt do LLM

## Comandos

### Analisar Categorias Sugeridas

```bash
python main.py --categorias-sugeridas

# Ou a forma abreviada
python main.py --cat
```

**Saída esperada:**

```
🏷️  ANÁLISE DE CATEGORIAS SUGERIDAS:
============================================================

📊 Estatísticas de Mapeamento:
------------------------------------------------------------
  Mapeada             :    45 produtos (60.0%)
  Não Mapeada         :    20 produtos (26.7%)
  Exata               :     8 produtos (10.7%)
  Sem Sugestão        :     2 produtos ( 2.7%)

🔍 Top 20 Categorias Não Mapeadas (classificadas como 'Outros'):
------------------------------------------------------------

  Categoria Sugerida                    |   Qtd | Exemplos de Produtos
  --------------------------------------+-------+-----------------------------------
  Achocolatados e Misturas para Bebidas |    15 | Nesquik Morango | Toddy | Nescau
  Snacks e Aperitivos                   |    12 | Doritos | Ruffles | Cheetos
  Alimentos Congelados                  |    10 | Lasanha Sadia | Pizza | Nuggets
  ...

💡 Dica: Adicione estas categorias ao MAPEAMENTO_CATEGORIAS
   ou crie novas categorias no banco de dados.
```

## Como Melhorar o Mapeamento

### Opção 1: Adicionar ao Mapeamento Inteligente

Edite `src/database.py` e adicione ao dicionário `MAPEAMENTO_CATEGORIAS`:

```python
MAPEAMENTO_CATEGORIAS = {
    # ... mapeamentos existentes ...

    # Novo mapeamento
    'achocolatados e misturas para bebidas': 'Bebidas',
    'achocolatados': 'Bebidas',
    'misturas para bebidas': 'Bebidas',

    # Snacks
    'snacks e aperitivos': 'Doces e Sobremesas',
    'snacks': 'Doces e Sobremesas',
    'aperitivos': 'Doces e Sobremesas',
}
```

**Vantagens:**
- Rápido e simples
- Não requer alteração no banco de dados
- Funciona imediatamente para novos produtos

### Opção 2: Criar Nova Categoria no Banco

Se a categoria sugerida é válida e merece ser uma categoria separada:

1. Conecte ao PostgreSQL:
```bash
psql -U user -d databasev1
```

2. Insira a nova categoria:
```sql
INSERT INTO categorias (nome, descricao, icone, ativo)
VALUES ('Achocolatados', 'Achocolatados e misturas para bebidas', '🍫', true);
```

3. Adicione ao mapeamento (para produtos futuros):
```python
MAPEAMENTO_CATEGORIAS = {
    'achocolatados e misturas para bebidas': 'Achocolatados',
    'achocolatados': 'Achocolatados',
}
```

## Queries SQL Úteis

### Top 20 categorias sugeridas não mapeadas

```sql
SELECT
    categoria_sugerida,
    COUNT(*) as quantidade,
    STRING_AGG(DISTINCT nome, ', ' ORDER BY nome LIMIT 3) as exemplos
FROM produtos_tabela
WHERE categoria = 'Outros' AND categoria_sugerida IS NOT NULL
GROUP BY categoria_sugerida
ORDER BY quantidade DESC
LIMIT 20;
```

### Produtos com categoria sugerida diferente da mapeada

```sql
SELECT nome, marca, categoria_sugerida, categoria
FROM produtos_tabela
WHERE categoria_sugerida IS NOT NULL
  AND LOWER(TRIM(categoria_sugerida)) != LOWER(TRIM(categoria))
ORDER BY created_at DESC
LIMIT 50;
```

### Estatísticas de mapeamento

```sql
SELECT
    CASE
        WHEN categoria = 'Outros' THEN 'Não Mapeada'
        WHEN categoria_sugerida IS NULL THEN 'Sem Sugestão'
        WHEN LOWER(TRIM(categoria_sugerida)) = LOWER(TRIM(categoria)) THEN 'Exata'
        ELSE 'Mapeada'
    END as tipo_mapeamento,
    COUNT(*) as quantidade,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM produtos_tabela), 2) as percentual
FROM produtos_tabela
GROUP BY tipo_mapeamento
ORDER BY quantidade DESC;
```

### Produtos com categoria sugerida = X

```sql
SELECT nome, marca, categoria, created_at
FROM produtos_tabela
WHERE categoria_sugerida = 'Achocolatados e Misturas para Bebidas'
ORDER BY created_at DESC;
```

## Workflow Recomendado

### Após processar vários panfletos:

1. **Analise as categorias sugeridas:**
   ```bash
   python main.py --categorias-sugeridas
   ```

2. **Identifique padrões:**
   - Categorias com alta frequência que estão como "Outros"
   - Categorias que deveriam ser mapeadas juntas
   - Categorias que são válidas e merecem existir

3. **Tome ação:**
   - Adicione mapeamentos ao `MAPEAMENTO_CATEGORIAS`
   - Crie novas categorias no banco se necessário
   - Melhore o prompt do LLM se as sugestões estiverem ruins

4. **Reprocesse (opcional):**
   - Se quiser atualizar produtos antigos, você pode criar um script
   - Ou simplesmente deixar os novos produtos usarem o mapeamento melhorado

## Estrutura do Banco de Dados

### Coluna `categoria_sugerida`

- **Tipo**: `VARCHAR(100)`
- **NULL**: Aceita (produtos antigos não têm)
- **Índice**: Sim (`idx_produtos_categoria_sugerida`)
- **Propósito**: Análise e melhoria do sistema

### Relação com outras colunas

```
produtos_tabela
├── categoria_sugerida (VARCHAR)    ← Original do LLM
├── categoria (VARCHAR)             ← Nome da categoria mapeada
└── categoria_id (INTEGER FK)       ← ID da tabela categorias
```

## Exemplos de Uso

### Cenário 1: LLM sugere categoria que existe no mapeamento

```python
# LLM retorna: "bebidas em pó"
# Sistema mapeia para: "Bebidas"
# Resultado no banco:
{
    "categoria_sugerida": "bebidas em pó",
    "categoria": "Bebidas",
    "categoria_id": 2  # ID de "Bebidas"
}
```

### Cenário 2: LLM sugere categoria desconhecida

```python
# LLM retorna: "Produtos Gourmet"
# Sistema NÃO encontra mapeamento
# Resultado no banco:
{
    "categoria_sugerida": "Produtos Gourmet",
    "categoria": "Outros",
    "categoria_id": 15  # ID de "Outros"
}
```

### Cenário 3: LLM sugere categoria exata

```python
# LLM retorna: "Carnes"
# Sistema encontra categoria exata
# Resultado no banco:
{
    "categoria_sugerida": "Carnes",
    "categoria": "Carnes",
    "categoria_id": 3  # ID de "Carnes"
}
```

## Boas Práticas

### ✅ Faça

- Analise categorias sugeridas regularmente (a cada 50-100 panfletos processados)
- Adicione mapeamentos para categorias frequentes
- Use nomes descritivos e consistentes
- Teste mapeamentos após adicionar

### ❌ Não Faça

- Não crie categorias muito específicas ("Nesquik Morango 380g")
- Não ignore categorias com alta frequência
- Não apague a coluna `categoria` (mantida por compatibilidade)
- Não processe panfletos antes de aplicar a migration

## Troubleshooting

### Problema: Comando retorna "Sem Sugestão" para todos os produtos

**Causa**: Produtos foram criados antes da migration

**Solução**: Processe novos panfletos após aplicar a migration

---

### Problema: Categoria sugerida não aparece na análise

**Causa**: Pode estar mapeada automaticamente

**Solução**: Use a segunda seção do relatório "Categorias Mapeadas Automaticamente"

---

### Problema: Erro ao aplicar migration

**Causa**: Coluna já existe ou conflito

**Solução**:
```sql
-- Verificar se coluna existe
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'produtos_tabela'
  AND column_name = 'categoria_sugerida';
```

---

## Migration

A migration `database/migration_categoria_sugerida.sql` adiciona:

1. Coluna `categoria_sugerida VARCHAR(100)`
2. Índice `idx_produtos_categoria_sugerida`
3. Comentário explicativo
4. Verificações de segurança

### Aplicar Migration

```bash
# Via script Python
python -c "
from dotenv import load_dotenv; load_dotenv()
from src.database import criar_conexao_do_env, PanfletoDatabase

db_conn = criar_conexao_do_env()
db_conn.connect()
db = PanfletoDatabase(db_conn)

with open('database/migration_categoria_sugerida.sql', 'r', encoding='utf-8') as f:
    migration_sql = f.read()

with db.db.get_cursor(dict_cursor=False) as cursor:
    cursor.execute(migration_sql)

print('✅ Migration aplicada!')
db_conn.close()
"

# Ou via psql
psql -U user -d databasev1 -f database/migration_categoria_sugerida.sql
```

### Rollback (se necessário)

```sql
DROP INDEX IF EXISTS idx_produtos_categoria_sugerida;
ALTER TABLE produtos_tabela DROP COLUMN IF EXISTS categoria_sugerida;
```

## Roadmap Futuro

- [ ] Interface web para gerenciar mapeamentos
- [ ] Sugestão automática de mapeamentos baseada em frequência
- [ ] Machine learning para melhorar mapeamento
- [ ] Exportar relatório de categorias em PDF
- [ ] Dashboard visual de categorias

## Suporte

Para dúvidas ou problemas:
- Verifique logs em `src/database.py:472-473`
- Consulte queries SQL de exemplo acima
- Revise CHANGELOG.md para mudanças recentes

---

**Versão**: 1.1.0
**Data**: 2025-10-15
**Autor**: Sistema de Análise de Preços
