# Regras de Desenvolvimento - App Preços Claude

## Visão Geral do Projeto

Sistema de extração e análise de preços de panfletos de supermercado usando LLMs (OpenAI, Anthropic, Gemini) e PostgreSQL.

## Stack Tecnológica

- **Linguagem:** Python 3.12
- **Banco de Dados:** PostgreSQL
- **LLMs:** OpenAI GPT-4, Anthropic Claude, Google Gemini
- **Bibliotecas Principais:**
  - `psycopg2-binary` - PostgreSQL
  - `pillow` - Processamento de imagens
  - `openai`, `anthropic`, `google-generativeai` - APIs LLM
  - `python-dotenv` - Variáveis de ambiente

## Estrutura do Projeto

```
app_precos_claude/
├── src/                          # Código fonte principal
│   ├── __init__.py               # Inicializador do pacote
│   ├── database.py               # Módulo de banco de dados
│   └── panfleto_processor.py     # Processamento de imagens com LLM
├── database/                     # Scripts SQL
│   ├── schema.sql                # Schema inicial do banco
│   ├── migration_categorias.sql  # Migration de categorias
│   └── migration_anti_duplicacao.sql  # Migration anti-duplicação
├── scripts/                      # Scripts utilitários e testes
│   ├── test_connection.py        # Teste de conexão DB e LLM
│   ├── test_panfletos.py         # Teste de processamento
│   ├── exemplos.py               # Exemplos de uso programático
│   ├── list_gemini_models.py     # Lista modelos Gemini disponíveis
│   └── setup.sh                  # Script de setup do ambiente
├── docs/                         # Documentação adicional
│   ├── ARCHITECTURE.md           # Arquitetura do sistema
│   ├── ANTI_DUPLICACAO.md        # Documentação anti-duplicação
│   ├── GEMINI_SUPPORT.md         # Suporte ao Gemini
│   ├── PROJECT_SUMMARY.md        # Resumo do projeto
│   └── QUICK_START.md            # Guia rápido
├── panfletos/                    # Pasta com imagens de panfletos
├── main.py                       # Script principal CLI
├── .env                          # Variáveis de ambiente (NÃO commitar)
├── .env.example                  # Template de variáveis
├── requirements.txt              # Dependências Python
├── CLAUDE.md                     # Regras de desenvolvimento
├── CHANGELOG.md                  # Histórico de alterações
└── README.md                     # Documentação principal
```

## Padrões de Código

### Style Guide

- **PEP 8:** Seguir rigorosamente
- **Type Hints:** Usar em todas as funções
- **Docstrings:** Formato Google Style para classes e funções
- **Encoding:** UTF-8 em todos os arquivos
- **Line Length:** Máximo 100 caracteres

### Exemplo de Função Bem Documentada

```python
def processar_imagem(caminho: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Processa uma imagem de panfleto e extrai produtos.

    Args:
        caminho: Caminho completo para a imagem
        timeout: Tempo máximo de processamento em segundos

    Returns:
        Dict contendo produtos extraídos e metadados

    Raises:
        FileNotFoundError: Se a imagem não existir
        ValueError: Se a imagem for inválida
    """
    pass
```

### Logging

- Usar módulo `logging` padrão do Python
- Níveis: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Formato: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Tratamento de Erros

- Sempre usar `try/except` em operações de I/O e API
- Fazer retry em chamadas de API (máximo 3 tentativas)
- Logar erros com traceback completo
- Retornar mensagens de erro amigáveis ao usuário

## Banco de Dados

### Convenções de Nomenclatura

- **Tabelas:** snake_case, plural (ex: `produtos_tabela`, `categorias`)
- **Colunas:** snake_case (ex: `nome_produto`, `preco_original`)
- **Foreign Keys:** `tabela_id` (ex: `categoria_id`, `supermercado_id`)
- **Índices:** `idx_tabela_coluna` (ex: `idx_produtos_categoria_id`)

### Estrutura de Tabelas Principais

1. **categorias** - Categorias de produtos (normalizada)
2. **produtos_tabela** - Produtos únicos
3. **supermercados** - Redes de supermercado
4. **imagens_processadas** - Registro de imagens processadas
5. **precos_panfleto** - Preços extraídos dos panfletos

### Migrations

- Sempre criar arquivo SQL para migrations: `migration_YYYYMMDD_descricao.sql`
- Incluir rollback quando possível
- Testar em ambiente local antes de aplicar
- Documentar mudanças no CHANGELOG.md

## LLM Integration

### Providers Suportados

1. **OpenAI** - Modelo: `gpt-4o`
2. **Anthropic** - Modelo: `claude-3-5-sonnet-20241022`
3. **Gemini** - Modelo: `gemini-2.5-flash`

### Prompt Engineering

- Usar prompt consistente em `PROMPT_EXTRACAO` (panfleto_processor.py)
- Sempre solicitar JSON estruturado
- Incluir exemplos no prompt quando possível
- Validar resposta antes de parsear JSON

### Rate Limiting e Retry

- **Max Retries:** 3 tentativas
- **Backoff:** Exponencial (2s, 4s, 8s)
- **Timeout:** 30 segundos por requisição
- Logar todas as tentativas e falhas

## Processamento de Imagens

### Especificações

- **Tamanho Máximo:** 2048px (largura ou altura)
- **Formatos Suportados:** JPG, JPEG, PNG, WEBP, BMP
- **Qualidade JPEG:** 85%
- **Redimensionamento:** Manter aspect ratio

### Otimização

- Redimensionar antes de enviar para LLM
- Converter para RGB se necessário
- Comprimir com qualidade 85%

## Variáveis de Ambiente

Arquivo `.env` obrigatório com:

```bash
# Banco de Dados
DB_HOST=localhost
DB_NAME=databasev1
DB_USER=user
DB_PASS=password
DB_PORT=5432

# API Keys (escolher uma)
GEMINI_API_KEY=...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Provider LLM
LLM_PROVIDER=gemini  # opções: openai, anthropic, gemini

# Configurações
MAX_IMAGE_SIZE=2048
RETRY_ATTEMPTS=3
```

## Testing

### Scripts de Teste

- `scripts/test_connection.py` - Testa conexão com DB e LLM
- `scripts/test_panfletos.py` - Testa processamento sem DB
- Criar testes para novas funcionalidades

### Antes de Commitar

1. Rodar testes básicos
2. Verificar PEP 8
3. Atualizar CHANGELOG.md
4. Verificar se .env não está no commit

## Git Workflow

### Commits

- Mensagens em português
- Formato: `tipo: descrição breve`
- Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Exemplos:
```
feat: adiciona suporte ao Gemini 2.5 Flash
fix: corrige parser de JSON com caracteres especiais
docs: atualiza README com instruções de instalação
refactor: normaliza tabela de categorias
```

### Arquivos a Ignorar

- `.env` - **NUNCA COMMITAR**
- `venv/`, `__pycache__/`
- `*.pyc`, `*.pyo`
- Imagens de teste grandes

## Boas Práticas

### Performance

- Usar índices em colunas de busca frequente
- Fazer batch inserts quando possível
- Cachear resultados de queries pesadas
- Limitar resultados com LIMIT/OFFSET

### Segurança

- **NUNCA** commitar API keys
- Usar variáveis de ambiente para credentials
- Validar inputs do usuário
- Sanitizar queries SQL (usar placeholders)

### Código Limpo

- Funções pequenas (máximo 50 linhas)
- Uma responsabilidade por função
- Nomes descritivos de variáveis
- Evitar duplicação de código (DRY)

### Documentação

- Atualizar README quando adicionar features
- Documentar breaking changes no CHANGELOG
- Comentar código complexo
- Manter exemplos atualizados

## Comandos Úteis

```bash
# Ambiente virtual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Inicializar banco
python main.py --init-schema

# Processar imagem
python main.py imagem.jpg

# Processar pasta
python main.py --folder panfletos/

# Ver estatísticas
python main.py --stats

# Exportar CSV
python main.py --export dados.csv

# Testar conexões
python scripts/test_connection.py

# Testar processamento de panfleto
python scripts/test_panfletos.py imagem.jpg

# Ver exemplos de uso
python scripts/exemplos.py
```

## Troubleshooting Comum

### Erro de Conexão PostgreSQL
- Verificar se PostgreSQL está rodando
- Verificar credenciais no .env
- Testar com: `python scripts/test_connection.py`

### Erro de API LLM
- Verificar se API key está correta
- Verificar quota/limite de requisições
- Verificar nome do modelo (usar `python scripts/list_gemini_models.py`)

### Erro de JSON Inválido
- LLM pode retornar texto antes/depois do JSON
- Parser tenta extrair JSON do meio do texto
- Se persistir, revisar prompt ou aumentar temperatura

## Roadmap de Features

- [ ] Interface web (Streamlit/Gradio)
- [ ] Comparador de preços entre supermercados
- [ ] Alertas de promoções
- [ ] OCR nativo (alternativa ao LLM)
- [ ] Análise de tendências de preços
- [ ] API REST

## Contato e Suporte

- **Projeto:** Sistema de Análise de Preços
- **Versão:** 1.0.0
- **Última Atualização:** 2025-10-14

---

**IMPORTANTE:** Sempre ler este arquivo antes de iniciar desenvolvimento!
