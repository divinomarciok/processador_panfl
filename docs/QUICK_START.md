# Guia Rápido - Sistema de Extração de Panfletos

## Instalação Rápida

```bash
# 1. Setup automático
./setup.sh

# 2. Configure o .env
nano .env

# 3. Inicialize o banco
python main.py --init-schema

# 4. Teste a configuração
python test_connection.py
```

## Configuração Mínima (.env)

```env
DB_HOST=localhost
DB_NAME=databasev1
DB_USER=user
DB_PASS=password
DB_PORT=5432

OPENAI_API_KEY=sk-...
# OU ANTHROPIC_API_KEY=sk-ant-...
# OU GEMINI_API_KEY=...

LLM_PROVIDER=openai  # ou anthropic ou gemini
```

## Comandos Essenciais

### Processar uma imagem
```bash
python main.py panfleto.jpg
```

### Processar pasta inteira
```bash
python main.py --folder imagens/
```

### Ver estatísticas
```bash
python main.py --stats
```

### Exportar para CSV
```bash
python main.py --export dados.csv
```

### Processar e exportar
```bash
python main.py panfleto.jpg --export resultado.csv
```

## Uso Programático Básico

```python
from dotenv import load_dotenv
from database import criar_conexao_do_env, PanfletoDatabase
from panfleto_processor import processar_panfleto

load_dotenv()

# Conectar
db_conn = criar_conexao_do_env()
db_conn.connect()
db = PanfletoDatabase(db_conn)

# Processar
dados = processar_panfleto("panfleto.jpg")
stats = db.salvar_panfleto_completo(
    nome_arquivo="panfleto.jpg",
    caminho_arquivo="panfleto.jpg",
    dados_json=dados
)

print(f"Salvos {stats['precos_salvos']} preços")
db_conn.close()
```

## Consultas SQL Úteis

### Produtos mais baratos
```sql
SELECT p.nome, MIN(pp.preco) as preco, s.nome as supermercado
FROM precos_panfleto pp
JOIN produtos_tabela p ON pp.produto_id = p.id
JOIN supermercados s ON pp.supermercado_id = s.id
WHERE pp.validade_fim >= CURRENT_DATE
GROUP BY p.nome, s.nome
ORDER BY preco;
```

### Promoções ativas
```sql
SELECT p.nome, pp.preco_original, pp.preco,
       ROUND(((pp.preco_original - pp.preco) / pp.preco_original * 100)::numeric, 2) as desconto
FROM precos_panfleto pp
JOIN produtos_tabela p ON pp.produto_id = p.id
WHERE pp.em_promocao = TRUE
ORDER BY desconto DESC;
```

### Histórico de preços
```sql
SELECT s.nome as supermercado, pp.preco, pp.created_at
FROM precos_panfleto pp
JOIN produtos_tabela p ON pp.produto_id = p.id
JOIN supermercados s ON pp.supermercado_id = s.id
WHERE LOWER(p.nome) LIKE '%arroz%'
ORDER BY pp.created_at DESC;
```

## Estrutura de Arquivos

```
app_precos_claude/
├── main.py                    # Script principal
├── database.py                # Operações do banco
├── panfleto_processor.py      # Processamento + LLM
├── schema.sql                 # Schema do banco
├── test_connection.py         # Teste de configuração
├── exemplos.py                # Exemplos de uso
├── .env                       # Configurações (criar)
├── .env.example               # Exemplo de config
└── requirements.txt           # Dependências
```

## Troubleshooting Rápido

### Erro de conexão ao banco
```bash
# Verificar se PostgreSQL está rodando
sudo systemctl status postgresql

# Verificar credenciais no .env
```

### Erro de API key
```bash
# Verificar se a key está configurada
cat .env | grep API_KEY

# Testar conexão
python test_connection.py
```

### JSON inválido da LLM
```bash
# Aumentar tentativas no .env
RETRY_ATTEMPTS=5
```

## Formatos de Imagem Suportados

- JPG/JPEG
- PNG
- WebP
- BMP

## Limites e Custos

### OpenAI GPT-4 Vision
- ~$0.01 por imagem
- Limite: 2048x2048px

### Anthropic Claude
- ~$0.008 por imagem
- Limite: 2048x2048px

### Google Gemini
- Gratuito até 60 req/min
- ~$0.002-0.005 por imagem (plano pago)
- Limite: 2048x2048px

## Exemplos de Saída

### Processamento único
```
🔄 Processando: panfleto_atacadao.jpg
📸 Imagem carregada: 1920x1080px
🤖 Enviando para GPT-4 Vision...
✅ JSON recebido com 15 produtos

💾 Salvando no banco de dados...
  ✓ Imagem salva (ID: 42)
  ✓ Supermercado: Atacadão (ID: 3)

📦 Processando produtos:
  [1/15] Picanha Bovina (R$ 79,90) ✓
  [2/15] Cerveja Heineken (R$ 3,49) ✓
  ...

✅ Concluído!
   - 15 produtos salvos
   - 15 preços registrados
   - 3 produtos novos criados
```

### Estatísticas
```
📊 ESTATÍSTICAS DO BANCO DE DADOS:
--------------------------------------------------
  Total de produtos: 245
  Total de supermercados: 8
  Total de preços: 1.523
  Total de imagens: 47
  Preço médio: R$ 15,43
  Promoções ativas: 312
```

## Links Úteis

- README completo: [README.md](README.md)
- Exemplos: [exemplos.py](exemplos.py)
- Schema: [schema.sql](schema.sql)

## Suporte

Para problemas:
1. Execute `python test_connection.py`
2. Verifique os logs
3. Consulte o README.md

---

**Dica**: Use `python main.py --help` para ver todas as opções!
