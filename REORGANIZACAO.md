# Reorganização do Projeto - App Preços Claude

## Data: 2025-10-14

## Resumo das Mudanças

O projeto foi reorganizado em uma estrutura de pastas mais clara e profissional, mantendo a simplicidade e sem exigir grandes alterações no código.

## Nova Estrutura

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
├── main.py                       # Script principal CLI (raiz)
├── .env                          # Variáveis de ambiente
├── .env.example                  # Template de variáveis
├── requirements.txt              # Dependências Python
├── CLAUDE.md                     # Regras de desenvolvimento
├── CHANGELOG.md                  # Histórico de alterações
└── README.md                     # Documentação principal
```

## Mudanças Realizadas

### 1. Código Fonte → `src/`
- ✅ `database.py` → `src/database.py`
- ✅ `panfleto_processor.py` → `src/panfleto_processor.py`
- ✅ Criado `src/__init__.py` para tornar src/ um pacote Python

### 2. Scripts SQL → `database/`
- ✅ `schema.sql` → `database/schema.sql`
- ✅ `migration_categorias.sql` → `database/migration_categorias.sql`
- ✅ `migration_anti_duplicacao.sql` → `database/migration_anti_duplicacao.sql`

### 3. Scripts Utilitários → `scripts/`
- ✅ `test_connection.py` → `scripts/test_connection.py`
- ✅ `test_panfletos.py` → `scripts/test_panfletos.py`
- ✅ `exemplos.py` → `scripts/exemplos.py`
- ✅ `list_gemini_models.py` → `scripts/list_gemini_models.py`
- ✅ `setup.sh` → `scripts/setup.sh`

### 4. Documentação → `docs/`
- ✅ `ARCHITECTURE.md` → `docs/ARCHITECTURE.md`
- ✅ `ANTI_DUPLICACAO.md` → `docs/ANTI_DUPLICACAO.md`
- ✅ `GEMINI_SUPPORT.md` → `docs/GEMINI_SUPPORT.md`
- ✅ `PROJECT_SUMMARY.md` → `docs/PROJECT_SUMMARY.md`
- ✅ `QUICK_START.md` → `docs/QUICK_START.md`

### 5. Arquivos na Raiz (não movidos)
- ✅ `main.py` - Script principal permanece na raiz
- ✅ `README.md` - Documentação principal
- ✅ `CLAUDE.md` - Regras de desenvolvimento
- ✅ `CHANGELOG.md` - Histórico de alterações
- ✅ `requirements.txt` - Dependências
- ✅ `.env` e `.env.example` - Configurações

## Atualizações de Imports

### Antes:
```python
from database import criar_conexao_do_env, PanfletoDatabase
from panfleto_processor import processar_panfleto
```

### Depois:
```python
from src.database import criar_conexao_do_env, PanfletoDatabase
from src.panfleto_processor import processar_panfleto
```

## Arquivos Atualizados

1. **main.py** - Imports atualizados para `src.database` e `src.panfleto_processor`
2. **scripts/test_connection.py** - Imports atualizados
3. **scripts/test_panfletos.py** - Imports atualizados
4. **scripts/exemplos.py** - Imports atualizados
5. **CLAUDE.md** - Estrutura do projeto e comandos atualizados
6. **README.md** - Estrutura do projeto e exemplo de uso atualizados

## Benefícios da Reorganização

### ✅ Organização Clara
- **src/** - Código principal separado de scripts auxiliares
- **database/** - Todos os scripts SQL em um único lugar
- **scripts/** - Scripts de teste e utilitários isolados
- **docs/** - Documentação adicional organizada

### ✅ Facilita Manutenção
- Mais fácil encontrar arquivos específicos
- Separação clara entre código principal e auxiliar
- Estrutura profissional e escalável

### ✅ Melhora Navegação
- Hierarquia de pastas intuitiva
- Arquivos agrupados por função
- Facilita onboarding de novos desenvolvedores

### ✅ Preparado para Crescimento
- Estrutura facilita adição de novos módulos
- Testes e scripts separados do código principal
- Migrations organizadas cronologicamente

## Como Usar Após a Reorganização

### Comandos Principais (não mudaram)
```bash
# Processar imagem
python main.py imagem.jpg

# Processar pasta
python main.py --folder panfletos/

# Ver estatísticas
python main.py --stats

# Inicializar banco
python main.py --init-schema
```

### Scripts de Teste (caminho atualizado)
```bash
# Testar conexão
python scripts/test_connection.py

# Testar processamento
python scripts/test_panfletos.py imagem.jpg

# Ver exemplos
python scripts/exemplos.py
```

### Uso Programático (imports atualizados)
```python
from dotenv import load_dotenv
from src.database import criar_conexao_do_env, PanfletoDatabase
from src.panfleto_processor import processar_panfleto

load_dotenv()
db_conn = criar_conexao_do_env()
db_conn.connect()
# ... resto do código
```

## Compatibilidade

- ✅ Todos os comandos principais (main.py) funcionam sem alterações
- ✅ Scripts de teste precisam ser executados com novo caminho
- ✅ Imports em código customizado precisam ser atualizados
- ✅ Ambiente virtual e dependências permanecem iguais

## Próximos Passos Recomendados

1. Testar todos os scripts após reorganização
2. Atualizar qualquer código customizado que importe os módulos
3. Considerar adicionar testes automatizados em `tests/`
4. Manter CHANGELOG.md atualizado com futuras mudanças

---

**Nota**: Esta reorganização mantém a simplicidade do projeto enquanto melhora a estrutura para facilitar manutenção e crescimento futuro.
