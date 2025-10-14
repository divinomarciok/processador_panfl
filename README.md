# Sistema de Extração de Preços de Panfletos

Sistema completo em Python para extrair dados de panfletos de supermercado usando LLM (GPT-4 Vision ou Claude) e armazenar em PostgreSQL.

## Características

- Extração automática de produtos e preços de imagens de panfletos
- Suporte para OpenAI GPT-4 Vision, Anthropic Claude e Google Gemini
- Armazenamento estruturado em PostgreSQL
- Processamento em lote de múltiplas imagens
- Exportação para CSV
- Sistema de retry automático
- Validação de dados extraídos
- Estatísticas e relatórios

## Requisitos

- Python 3.8+
- PostgreSQL 12+
- Conta OpenAI (para GPT-4 Vision) OU Conta Anthropic (para Claude) OU Conta Google (para Gemini)

## Instalação

### 1. Clone ou baixe o projeto

```bash
cd app_precos_claude
```

### 2. Crie e ative ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o PostgreSQL

Certifique-se de que o PostgreSQL está rodando e crie o banco:

```bash
psql -U postgres
CREATE DATABASE databasev1;
CREATE USER user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE databasev1 TO user;
\q
```

### 5. Configure as variáveis de ambiente

Copie o arquivo de exemplo e edite com suas credenciais:

```bash
cp .env.example .env
```

Edite `.env`:

```env
# Banco de dados
DB_HOST=localhost
DB_NAME=databasev1
DB_USER=user
DB_PASS=password
DB_PORT=5432

# API Keys (escolha uma)
OPENAI_API_KEY=sk-...
# OU
ANTHROPIC_API_KEY=sk-ant-...
# OU
GEMINI_API_KEY=...

# Qual LLM usar
LLM_PROVIDER=openai  # ou anthropic ou gemini
```

### 6. Inicialize o schema do banco

```bash
python main.py --init-schema
```

## Uso

### Processar uma imagem

```bash
python main.py panfleto.jpg
```

### Processar múltiplas imagens de uma pasta

```bash
python main.py --folder imagens/
```

### Exportar dados para CSV

```bash
python main.py --export dados.csv
```

### Processar e exportar

```bash
python main.py panfleto.jpg --export resultado.csv
```

### Ver estatísticas do banco

```bash
python main.py --stats
```

### Modo silencioso

```bash
python main.py panfleto.jpg --quiet
```

## Argumentos da Linha de Comando

| Argumento | Descrição |
|-----------|-----------|
| `imagem` | Caminho da imagem a processar (posicional) |
| `--image, -i` | Caminho da imagem a processar (alternativa) |
| `--folder, -f` | Pasta com múltiplas imagens |
| `--export, -e` | Exportar dados para CSV |
| `--stats, -s` | Mostrar estatísticas do banco |
| `--init-schema` | Inicializar schema do banco |
| `--quiet, -q` | Modo silencioso |

## Estrutura do Projeto

```
app_precos_claude/
├── src/                     # Código fonte principal
│   ├── __init__.py          # Inicializador do pacote
│   ├── database.py          # Módulo de conexão e operações do banco
│   └── panfleto_processor.py # Processamento de imagens e LLM
├── database/                # Scripts SQL
│   ├── schema.sql           # Schema inicial do banco
│   └── migration_*.sql      # Migrations
├── scripts/                 # Scripts utilitários e testes
│   ├── test_connection.py   # Teste de conexão
│   ├── test_panfletos.py    # Teste de processamento
│   ├── exemplos.py          # Exemplos de uso
│   └── setup.sh             # Script de setup
├── docs/                    # Documentação adicional
├── panfletos/               # Pasta para imagens
├── main.py                  # Script principal CLI
├── requirements.txt         # Dependências Python
├── .env.example             # Exemplo de configuração
└── README.md                # Este arquivo
```

## Estrutura do Banco de Dados

### Tabelas Principais

**produtos_tabela**
- Catálogo de produtos extraídos
- Campos: id, nome, marca, categoria, codigo_barras, descricao

**supermercados**
- Cadastro de supermercados
- Campos: id, nome, rede, cidade, estado

**precos_panfleto**
- Histórico de preços
- Campos: produto_id, supermercado_id, preco, preco_original, em_promocao, validade, etc.

**imagens_processadas**
- Log de imagens processadas
- Campos: id, nome_arquivo, status, dados_json, erro_mensagem

### Views Úteis

**vw_melhores_precos**
- Lista produtos com menor preço atual por supermercado

**vw_estatisticas_supermercado**
- Estatísticas agregadas por supermercado

## Formato de Dados Extraídos

A LLM retorna dados no seguinte formato JSON:

```json
{
  "supermercado": "Atacadão",
  "data_validade_inicio": "2025-01-15",
  "data_validade_fim": "2025-01-20",
  "produtos": [
    {
      "nome": "Picanha Bovina",
      "marca": "Friboi",
      "categoria": "Carnes",
      "preco": 79.90,
      "preco_original": 89.90,
      "em_promocao": true,
      "unidade": "kg",
      "descricao_adicional": "Peça inteira",
      "confianca": 0.95
    }
  ]
}
```

## Uso Programático

Você também pode usar os módulos diretamente em seu código:

```python
from dotenv import load_dotenv
from src.database import criar_conexao_do_env, PanfletoDatabase
from src.panfleto_processor import processar_panfleto

# Carregar variáveis de ambiente
load_dotenv()

# Conectar ao banco
db_conn = criar_conexao_do_env()
db_conn.connect()
db = PanfletoDatabase(db_conn)

# Processar panfleto
dados = processar_panfleto("panfleto.jpg")

# Salvar no banco
stats = db.salvar_panfleto_completo(
    nome_arquivo="panfleto.jpg",
    caminho_arquivo="/caminho/completo/panfleto.jpg",
    dados_json=dados
)

print(f"Salvos {stats['precos_salvos']} preços")

# Fechar conexão
db_conn.close()
```

## Exemplos de Consultas SQL

### Produtos mais baratos por categoria

```sql
SELECT
    p.categoria,
    p.nome,
    MIN(pp.preco) as menor_preco,
    s.nome as supermercado
FROM produtos_tabela p
INNER JOIN precos_panfleto pp ON p.id = pp.produto_id
INNER JOIN supermercados s ON pp.supermercado_id = s.id
WHERE pp.validade_fim >= CURRENT_DATE
GROUP BY p.categoria, p.nome, s.nome
ORDER BY p.categoria, menor_preco;
```

### Promoções ativas

```sql
SELECT
    p.nome,
    s.nome as supermercado,
    pp.preco_original,
    pp.preco,
    ROUND(((pp.preco_original - pp.preco) / pp.preco_original * 100)::numeric, 2) as desconto_percentual
FROM precos_panfleto pp
INNER JOIN produtos_tabela p ON pp.produto_id = p.id
INNER JOIN supermercados s ON pp.supermercado_id = s.id
WHERE pp.em_promocao = TRUE
    AND pp.validade_fim >= CURRENT_DATE
ORDER BY desconto_percentual DESC;
```

### Histórico de preços de um produto

```sql
SELECT
    s.nome as supermercado,
    pp.preco,
    pp.validade_inicio,
    pp.created_at
FROM precos_panfleto pp
INNER JOIN produtos_tabela p ON pp.produto_id = p.id
INNER JOIN supermercados s ON pp.supermercado_id = s.id
WHERE LOWER(p.nome) LIKE '%arroz%'
ORDER BY pp.created_at DESC;
```

## Troubleshooting

### Erro de conexão com o banco

```
Verifique se o PostgreSQL está rodando:
sudo systemctl status postgresql

Verifique as credenciais no .env
```

### Erro de API key inválida

```
Certifique-se de que a API key está correta no .env
Verifique se o LLM_PROVIDER está configurado corretamente
```

### Imagem muito grande

```
O sistema redimensiona automaticamente para 2048px
Configure MAX_IMAGE_SIZE no .env se necessário
```

### JSON inválido da LLM

```
O sistema tenta extrair JSON automaticamente do texto
Aumenta tentativas com RETRY_ATTEMPTS no .env
```

## Limitações Conhecidas

- Imagens muito complexas podem ter extração incompleta
- Produtos com nomes muito parecidos podem ser tratados como duplicatas
- Preços em formatos não padrão podem não ser reconhecidos
- Dependência de APIs externas (OpenAI/Anthropic)

## Melhorias Futuras

- [ ] Interface web com Flask/FastAPI
- [ ] Sistema de matching mais inteligente de produtos
- [ ] Suporte para OCR local (Tesseract) como fallback
- [ ] Cache de imagens já processadas
- [ ] Sistema de notificação de promoções
- [ ] API REST para consultas
- [ ] Dashboard de visualização
- [ ] Suporte para múltiplos idiomas

## Custos Estimados

### OpenAI GPT-4 Vision
- ~$0.01 por imagem (depende do tamanho)
- 100 imagens = ~$1.00

### Anthropic Claude
- ~$0.008 por imagem (depende do tamanho)
- 100 imagens = ~$0.80

### Google Gemini
- Gratuito até 60 requisições/minuto
- ~$0.002-0.005 por imagem no plano pago
- 100 imagens = ~$0.20-0.50

## Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça um fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## Licença

Este projeto é fornecido como está, para uso educacional e comercial.

## Suporte

Para problemas ou dúvidas:
- Abra uma issue no repositório
- Consulte a documentação do PostgreSQL
- Consulte a documentação da OpenAI/Anthropic

## Changelog

### v1.0.0 (2025-01-13)
- Versão inicial
- Suporte para OpenAI e Anthropic
- Processamento em lote
- Exportação para CSV
- Sistema de retry
- Validação de dados

## Autor

Sistema desenvolvido para extração automatizada de preços de panfletos de supermercado.

---

**Nota**: Lembre-se de nunca commitar o arquivo `.env` com suas credenciais!
