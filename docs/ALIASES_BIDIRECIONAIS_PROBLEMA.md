# ⚠️ Problema com Aliases Bidirecionais

## 🐛 O Erro

O script antigo `popular_aliases_INCORRETO_NAO_USAR.py` tinha um **erro fundamental de lógica**: criava **aliases bidirecionais** entre produtos duplicados.

### Como funcionava (ERRADO):

```
Produto 222: "Abóbora Cabotiá"
Produto 435: "Abóbora Kabotiá"

Script antigo criava:
├─ Alias 1: produto_id=222 → alias="Abóbora Kabotiá"
└─ Alias 2: produto_id=435 → alias="Abóbora Cabotiá"
```

**Resultado**: Ambos os produtos continuavam **separados** no banco!

```sql
SELECT id, nome FROM produtos_tabela WHERE id IN (222, 435);

 id  | nome
-----+-------------------
 222 | Abóbora Cabotiá
 435 | Abóbora Kabotiá    ← DUPLICATA!
```

### Por que está errado:

1. **Produtos duplicados permanecem no banco** (não resolve o problema)
2. **Busca retorna resultados duplicados** (produto pode ser encontrado 2x)
3. **Dados de preços ficam fragmentados** entre produtos
4. **Estatísticas ficam incorretas** (conta produtos duplicados)

---

## ✅ A Solução Correta

O script novo `popular_aliases_CORRETO.py` **mescla** produtos ao invés de criar aliases bidirecionais.

### Como funciona (CORRETO):

```
Produto 222: "Abóbora Cabotiá"
Produto 435: "Abóbora Kabotiá"

Script novo faz:
1. Atualiza preços: produto_id 435 → 222
2. Deleta aliases do produto 435
3. Cria 1 alias: produto_id=222 → alias="Abóbora Kabotiá"
4. Deleta produto 435
```

**Resultado**: Apenas **1 produto** no banco!

```sql
SELECT id, nome FROM produtos_tabela WHERE id IN (222, 435);

 id  | nome
-----+-------------------
 222 | Abóbora Cabotiá    ← ÚNICO produto

SELECT * FROM produtos_aliases WHERE produto_id = 222;

 id | produto_id | alias             | origem | confianca
----+------------+-------------------+--------+----------
 10 | 222        | Abóbora Kabotiá   | auto   | 1.0
```

### Por que está correto:

1. ✅ **Produto duplicado é removido** (resolve o problema)
2. ✅ **Busca retorna resultado único** (sem duplicatas)
3. ✅ **Todos os preços ficam no mesmo produto**
4. ✅ **Estatísticas corretas**
5. ✅ **Busca por qualquer variação funciona** via alias

---

## 📊 Comparação

| Aspecto | Aliases Bidirecionais ❌ | Mesclagem ✅ |
|---------|-------------------------|-------------|
| **Produtos no banco** | 2 (duplicados) | 1 (único) |
| **Aliases criados** | 2 (um em cada) | 1 (no produto mantido) |
| **Busca** | Retorna 2 produtos | Retorna 1 produto |
| **Preços** | Fragmentados | Consolidados |
| **Resolve duplicação** | ❌ Não | ✅ Sim |

---

## 🔧 O Que Foi Feito

### 1. Criado Script Correto

```bash
scripts/popular_aliases_CORRETO.py
```

- Mescla produtos duplicados
- Cria apenas 1 alias unidirecional
- Remove produto duplicado do banco

### 2. Renomeado Script Antigo

```bash
scripts/popular_aliases_INCORRETO_NAO_USAR.py
```

- Script antigo foi renomeado com aviso claro
- **NÃO deve ser usado!**

### 3. Criado Link Simbólico

```bash
scripts/popular_aliases.py → popular_aliases_CORRETO.py
```

- Comando `python scripts/popular_aliases.py` agora executa o script **correto**

### 4. Corrigidos Aliases Existentes

Script `corrigir_aliases_bidirecionais.py` foi executado e corrigiu:

- ✅ **6 produtos mesclados**
- ✅ **2 aliases incorretos removidos** (produtos diferentes)
- ✅ **0 aliases bidirecionais restantes**

---

## 🎯 Como Usar o Script Correto

### Modo Interativo (recomendado)

```bash
python scripts/popular_aliases.py
```

- Mostra cada duplicata
- Pede confirmação manual
- Permite revisar antes de mesclar

### Modo Automático (alta confiança)

```bash
python scripts/popular_aliases.py --auto
```

- Mescla automaticamente duplicatas com similaridade ≥95%
- Pede confirmação antes de iniciar
- **Cuidado**: Deleta produtos permanentemente!

### Apenas Relatório

```bash
python scripts/popular_aliases.py --relatorio
```

- Mostra estatísticas sem fazer alterações
- Útil para verificar estado atual

---

## 📝 Exemplo Prático

### Antes (Script Incorreto):

```sql
-- Produtos duplicados permanecem
SELECT id, nome FROM produtos_tabela WHERE nome LIKE '%Queijo Mussarela%';

 id  | nome
-----+---------------------------
 264 | Queijo Mussarela Fatiado
 370 | Queijo Mussarela Fatiada   ← DUPLICATA

-- Aliases bidirecionais
SELECT produto_id, alias FROM produtos_aliases WHERE produto_id IN (264, 370);

 produto_id | alias
------------+---------------------------
 264        | Queijo Mussarela Fatiada
 370        | Queijo Mussarela Fatiado
```

### Depois (Script Correto):

```sql
-- Apenas 1 produto
SELECT id, nome FROM produtos_tabela WHERE nome LIKE '%Queijo Mussarela%';

 id  | nome
-----+---------------------------
 264 | Queijo Mussarela Fatiado   ← ÚNICO

-- Apenas 1 alias unidirecional
SELECT produto_id, alias FROM produtos_aliases WHERE produto_id = 264;

 produto_id | alias
------------+---------------------------
 264        | Queijo Mussarela Fatiada
```

**Busca funciona para ambas as variações:**

```python
# Buscar "Queijo Mussarela Fatiado" → Encontra produto 264
# Buscar "Queijo Mussarela Fatiada" → Encontra produto 264 (via alias)
```

---

## ⚠️ Importante

1. **NUNCA use `popular_aliases_INCORRETO_NAO_USAR.py`**
2. Use sempre `popular_aliases.py` (aponta para o script correto)
3. No modo automático, produtos são **deletados permanentemente**
4. Faça backup antes de executar em produção

---

**Última atualização**: 2025-10-16
**Status**: ✅ Problema identificado e corrigido
