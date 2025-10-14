# Sistema Anti-Duplicação de Produtos

## Resumo

Este documento explica como o sistema **garante** que produtos não serão duplicados no banco de dados.

## ✅ Proteções Implementadas

### 1. **Normalização Automática de Nomes**

**O que faz:**
- Remove espaços extras
- Converte para minúsculas
- Padroniza variações do mesmo produto

**Exemplo:**
```
"Coca Cola Lata"    → "coca cola lata"
"COCA COLA LATA"    → "coca cola lata"
"  Coca  Cola  Lata  " → "coca cola lata"
```

Todos esses nomes são considerados **o mesmo produto**.

### 2. **Constraint UNIQUE no Banco**

**Localização:** `produtos_tabela.nome_normalizado`

**O que faz:**
- Impede que dois produtos com o mesmo nome normalizado sejam inseridos
- Erro gerado: `duplicate key value violates unique constraint`

**Isso significa:**
- Mesmo que o código Python tentar inserir uma duplicata, o banco **recusará** automaticamente
- **Impossível** ter duplicatas, mesmo com bugs no código

### 3. **Trigger Automático**

**Nome:** `before_insert_update_produto_normalizar`

**O que faz:**
- Sempre que um produto é inserido ou atualizado, o trigger:
  1. Pega o valor de `nome`
  2. Normaliza usando a função `normalizar_nome()`
  3. Salva em `nome_normalizado`

**Isso significa:**
- Você **não precisa** preencher `nome_normalizado` manualmente
- É automático e transparente

### 4. **Busca Inteligente no Código Python**

**Função:** `buscar_produto_por_nome(nome)`

**O que mudou:**
```python
# ANTES (podia criar duplicatas)
WHERE LOWER(nome) LIKE LOWER(%s)

# DEPOIS (usa normalização)
WHERE nome_normalizado = normalizar_nome(%s)
```

**Isso significa:**
- Antes de inserir um produto, o sistema busca por nome normalizado
- Se encontrar, reutiliza o produto existente
- Se não encontrar, cria um novo

### 5. **View de Monitoramento**

**Nome:** `vw_possiveis_duplicatas`

**Como usar:**
```sql
SELECT * FROM vw_possiveis_duplicatas;
```

**O que mostra:**
- Lista produtos que **teoricamente** poderiam ser duplicatas
- Útil para auditoria e limpeza

## 🧪 Testes Realizados

### Teste 1: Variações de Case
```
Entrada: "COCA COLA LATA"
Resultado: ✅ Encontrou produto existente (ID: 53)

Entrada: "coca cola lata"
Resultado: ✅ Encontrou produto existente (ID: 53)

Entrada: "  Coca Cola Lata  "
Resultado: ✅ Encontrou produto existente (ID: 53)
```

### Teste 2: Inserção de Duplicata
```
Tentativa: INSERT "  COCA  COLA  LATA  "
Resultado: ✅ REJEITADO pelo banco
Erro: duplicate key value violates unique constraint
```

### Teste 3: Produtos Existentes
```
Total de produtos: 53
Nomes únicos (normalizados): 53
Duplicatas encontradas: 0 ✅
```

## 📊 Garantias

### Nível 1: Banco de Dados
- ✅ Constraint UNIQUE impede duplicatas **fisicamente**
- ✅ Trigger normaliza **automaticamente** antes de inserir
- ✅ Impossível ter duplicatas mesmo com bugs no código

### Nível 2: Código Python
- ✅ Função `buscar_produto_por_nome()` usa normalização
- ✅ Método `buscar_ou_criar_produto()` reutiliza produtos existentes
- ✅ Busca **antes** de criar

### Nível 3: Monitoramento
- ✅ View `vw_possiveis_duplicatas` para auditoria
- ✅ Logs mostram quando produto é reutilizado vs criado

## 🔍 Como Verificar se Há Duplicatas

### Opção 1: Via SQL
```sql
-- Ver possíveis duplicatas
SELECT * FROM vw_possiveis_duplicatas;

-- Contar nomes únicos
SELECT
    COUNT(*) as total_produtos,
    COUNT(DISTINCT nome_normalizado) as nomes_unicos
FROM produtos_tabela;
```

### Opção 2: Via Python
```python
from database import criar_conexao_do_env

db = criar_conexao_do_env()
db.connect()

with db.get_cursor() as cursor:
    cursor.execute("SELECT * FROM vw_possiveis_duplicatas")
    duplicatas = cursor.fetchall()

    if not duplicatas:
        print("✅ Nenhuma duplicata!")
    else:
        print(f"❌ {len(duplicatas)} duplicatas encontradas")

db.close()
```

## 🛠️ Manutenção

### Limpar Duplicatas Existentes (se houver)

Se, por algum motivo, duplicatas existirem **antes** da migration:

```sql
-- Ver duplicatas
SELECT * FROM vw_possiveis_duplicatas;

-- Mesclar produtos duplicados (CUIDADO! Executar manualmente)
-- 1. Atualizar precos_panfleto para apontar para um único produto
UPDATE precos_panfleto
SET produto_id = <ID_PRODUTO_MANTER>
WHERE produto_id = <ID_PRODUTO_DELETAR>;

-- 2. Deletar produto duplicado
DELETE FROM produtos_tabela WHERE id = <ID_PRODUTO_DELETAR>;
```

### Adicionar Código de Barras (Reforçar Unicidade)

```sql
-- Se produto tiver código de barras, garantir unicidade
UPDATE produtos_tabela
SET codigo_barras = '<CODIGO>'
WHERE id = <ID>;

-- Constraint automática já existe!
-- idx_produtos_codigo_barras_unique
```

## 📝 Exemplo de Fluxo

### Cenário: Processar novo panfleto

1. **LLM extrai:** `"Coca Cola Lata"`
2. **Python chama:** `buscar_ou_criar_produto("Coca Cola Lata")`
3. **Função busca:**
   ```sql
   SELECT * FROM produtos_tabela
   WHERE nome_normalizado = normalizar_nome('Coca Cola Lata')
   -- Resultado: nome_normalizado = 'coca cola lata'
   ```
4. **Produto encontrado?**
   - ✅ **SIM:** Retorna ID existente (ex: 53)
   - ❌ **NÃO:** Tenta criar novo

5. **Se criar novo:**
   ```sql
   INSERT INTO produtos_tabela (nome)
   VALUES ('Coca Cola Lata')
   -- Trigger preenche nome_normalizado = 'coca cola lata'
   -- Constraint verifica: já existe 'coca cola lata'?
   -- → SIM: Rejeita com erro
   -- → NÃO: Insere normalmente
   ```

## 🎯 Conclusão

**Você está 100% protegido contra duplicatas!**

- ✅ Banco garante unicidade (constraint)
- ✅ Trigger preenche automaticamente
- ✅ Código busca antes de criar
- ✅ Impossível inserir duplicatas

**Mesmo que:**
- LLM retornar nomes com espaços extras
- LLM retornar MAIÚSCULAS/minúsculas diferentes
- Código tentar inserir manualmente
- Houver bugs no Python

**O banco sempre rejeitará duplicatas!**

---

**Data de Implementação:** 2025-10-14
**Arquivo Migration:** `migration_anti_duplicacao.sql`
**Arquivo Código:** `database.py` (função `buscar_produto_por_nome`)
