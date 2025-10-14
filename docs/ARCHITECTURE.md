# Arquitetura do Sistema

## Visão Geral

Sistema modular para extração de dados de panfletos de supermercado usando LLM e armazenamento em PostgreSQL.

```
┌─────────────────────────────────────────────────────────────┐
│                        CAMADA DE INTERFACE                   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   main.py    │  │ exemplos.py  │  │  API (futuro)│     │
│  │   (CLI)      │  │ (Programático)│  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE PROCESSAMENTO                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         panfleto_processor.py                         │  │
│  │                                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │ImageProcessor│  │  LLMClient  │  │ JSONParser  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  │                                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE PERSISTÊNCIA                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              database.py                              │  │
│  │                                                        │  │
│  │  ┌───────────────┐  ┌───────────────────────────┐   │  │
│  │  │ DBConnection  │  │  PanfletoDatabase         │   │  │
│  │  └───────────────┘  └───────────────────────────┘   │  │
│  │                                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    BANCO DE DADOS                            │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │produtos_ │  │supermerca│  │ precos_  │  │ imagens_ │   │
│  │tabela    │  │dos       │  │ panfleto │  │processad.│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                    PostgreSQL                                │
└─────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados

### 1. Processamento de Imagem

```
Imagem → ImageProcessor
   │
   ├─→ Validação (existe?)
   ├─→ Carregamento (PIL)
   ├─→ Redimensionamento (se > 2048px)
   └─→ Conversão Base64
```

### 2. Análise com LLM

```
Base64 → LLMClient
   │
   ├─→ Seleção do Provider (OpenAI/Anthropic)
   ├─→ Montagem do Request
   ├─→ Envio para API
   ├─→ Retry Logic (até 3 tentativas)
   └─→ Resposta JSON
```

### 3. Validação e Parsing

```
Resposta → JSONParser
   │
   ├─→ Extração do JSON
   ├─→ Validação de Estrutura
   ├─→ Validação de Campos
   ├─→ Validação de Tipos
   └─→ Dados Validados
```

### 4. Persistência no Banco

```
Dados → PanfletoDatabase
   │
   ├─→ Salvar Imagem Processada
   ├─→ Buscar/Criar Supermercado
   ├─→ Para cada produto:
   │   ├─→ Buscar Produto Similar
   │   ├─→ Criar se não existir
   │   └─→ Salvar Preço
   └─→ Retornar Estatísticas
```

## Módulos Principais

### database.py (20KB)

**Classes:**
- `DatabaseConnection`: Gerencia conexão com PostgreSQL
- `PanfletoDatabase`: Operações de alto nível

**Responsabilidades:**
- Conexão e desconexão do banco
- Transações (commit/rollback)
- CRUD de produtos, supermercados, preços
- Consultas e estatísticas
- Sistema de busca por similaridade

**Principais Métodos:**
- `salvar_panfleto_completo()`: Salva todos os dados de um panfleto
- `buscar_ou_criar_produto()`: Normalização de produtos
- `obter_estatisticas()`: Agregações e métricas

### panfleto_processor.py (16KB)

**Classes:**
- `ImageProcessor`: Processamento de imagens
- `LLMClient`: Interface com APIs de LLM
- `JSONParser`: Parsing e validação
- `PanfletoProcessor`: Orquestrador principal

**Responsabilidades:**
- Manipulação de imagens (PIL)
- Comunicação com OpenAI/Anthropic
- Retry logic e error handling
- Validação de dados extraídos
- Conversão de formatos

**Principais Métodos:**
- `processar_panfleto()`: Fluxo completo de processamento
- `analisar_imagem()`: Interação com LLM
- `extrair_json()`: Parsing inteligente

### main.py (13KB)

**Funções:**
- Interface CLI com argparse
- Processamento único e em lote
- Exportação para CSV
- Estatísticas e relatórios
- Pretty printing e formatação

**Responsabilidades:**
- Validação de argumentos
- Orquestração do fluxo
- Feedback ao usuário
- Tratamento de erros de alto nível

## Modelo de Dados

### Relacionamentos

```
produtos_tabela (1) ────┬──── (N) precos_panfleto
                        │
supermercados (1) ──────┤
                        │
imagens_processadas (1)─┘
```

### Campos Principais

**produtos_tabela:**
- id, nome, marca, categoria
- codigo_barras, descricao
- created_at, updated_at

**supermercados:**
- id, nome, rede
- cidade, estado
- created_at

**precos_panfleto:**
- id, produto_id, supermercado_id, imagem_id
- preco, preco_original, em_promocao
- validade_inicio, validade_fim
- unidade, descricao_adicional, confianca
- created_at

**imagens_processadas:**
- id, nome_arquivo, caminho_arquivo
- supermercado_nome, data_panfleto
- status, dados_json, erro_mensagem
- created_at, processed_at

## Decisões de Design

### 1. Modularidade
- Separação clara de responsabilidades
- Módulos independentes e testáveis
- Interfaces bem definidas

### 2. Robustez
- Try/catch em operações críticas
- Retry logic automático
- Validação em múltiplas camadas
- Logging extensivo

### 3. Flexibilidade
- Suporte a múltiplos providers LLM
- Configuração via variáveis de ambiente
- Uso programático ou CLI
- Schema extensível

### 4. Performance
- Context managers para conexões
- Transações eficientes
- Índices no banco
- Cache de resultados (futuro)

### 5. Simplicidade
- SQL direto (sem ORM)
- Dependências mínimas
- Código autodocumentado
- Exemplos práticos

## Padrões Utilizados

### Context Manager
```python
with db.get_cursor() as cursor:
    cursor.execute(query)
    # Auto-commit ou rollback
```

### Factory Pattern
```python
def criar_conexao_do_env():
    # Cria conexão a partir de variáveis de ambiente
    return DatabaseConnection(...)
```

### Strategy Pattern
```python
class LLMClient:
    # Estratégia selecionada via provider
    if self.provider == "openai":
        return self.analisar_imagem_openai(...)
    elif self.provider == "anthropic":
        return self.analisar_imagem_anthropic(...)
```

### Template Method
```python
def processar_panfleto(caminho):
    # 1. Processar imagem
    # 2. Analisar com LLM
    # 3. Parsear JSON
    # 4. Validar dados
    # 5. Retornar resultado
```

## Extensibilidade

### Adicionar Novo Provider LLM

1. Criar método em `LLMClient`:
```python
def analisar_imagem_novo_provider(self, base64_imagem, prompt):
    # Implementação
    pass
```

2. Adicionar no switch:
```python
elif self.provider == "novo_provider":
    return self.analisar_imagem_novo_provider(...)
```

3. Atualizar `.env.example`:
```env
LLM_PROVIDER=novo_provider
NOVO_PROVIDER_API_KEY=...
```

### Adicionar Nova Funcionalidade

1. Adicionar método em `PanfletoDatabase`
2. Criar query SQL necessária
3. Adicionar comando CLI em `main.py`
4. Atualizar documentação

### Adicionar Nova Tabela

1. Atualizar `schema.sql`
2. Criar métodos CRUD em `database.py`
3. Atualizar views se necessário
4. Migrar banco existente

## Segurança

### Proteções Implementadas

- ✅ SQL injection (parameterized queries)
- ✅ API keys em variáveis de ambiente
- ✅ .gitignore para .env
- ✅ Validação de entrada
- ✅ Tratamento de exceções

### Melhorias Futuras

- [ ] Autenticação/autorização
- [ ] Rate limiting
- [ ] Sanitização adicional
- [ ] Audit logs
- [ ] Criptografia de dados sensíveis

## Performance

### Otimizações Atuais

- Índices no banco de dados
- Transações agrupadas
- Context managers
- Redimensionamento de imagens

### Melhorias Futuras

- [ ] Cache de consultas frequentes
- [ ] Processamento paralelo de imagens
- [ ] Connection pooling
- [ ] Lazy loading
- [ ] Batch inserts

## Testes

### Estratégia de Testes (Sugerida)

```
tests/
├── test_database.py          # Testes de DB
├── test_processor.py         # Testes de processamento
├── test_integration.py       # Testes integrados
└── fixtures/
    ├── sample_images/        # Imagens de teste
    └── sample_responses.json # Respostas mockadas
```

### Cobertura Desejada

- Unit tests: 80%+
- Integration tests: 60%+
- E2E tests: Casos principais

## Monitoramento

### Logs

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Métricas Importantes

- Tempo de processamento por imagem
- Taxa de sucesso/erro
- Produtos extraídos por imagem
- Custos de API por dia
- Taxa de duplicatas

## Deployment

### Ambientes Sugeridos

**Desenvolvimento:**
- PostgreSQL local
- API keys de teste
- Logs verbose

**Produção:**
- PostgreSQL em servidor dedicado
- API keys de produção
- Logs estruturados
- Backup automático
- Monitoramento

### Checklist de Deploy

- [ ] Variáveis de ambiente configuradas
- [ ] Banco inicializado
- [ ] Backup configurado
- [ ] Monitoramento ativo
- [ ] Rate limits configurados
- [ ] Documentação atualizada

## Manutenção

### Tarefas Regulares

- Backup do banco (diário)
- Limpeza de imagens antigas (mensal)
- Atualização de dependências (mensal)
- Revisão de logs (semanal)
- Análise de custos (mensal)

### Troubleshooting

Ver seção de Troubleshooting no README.md

## Roadmap

### v1.1
- [ ] API REST
- [ ] Dashboard web
- [ ] Testes automatizados

### v2.0
- [ ] Cache inteligente
- [ ] Matching ML-based
- [ ] Multi-tenancy

### v3.0
- [ ] App mobile
- [ ] Notificações push
- [ ] Análise preditiva

---

**Última atualização:** 2025-01-13
**Versão:** 1.0.0
