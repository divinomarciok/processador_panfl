# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

## [1.1.0] - 2025-01-14

### Adicionado
- ✨ **Suporte ao Google Gemini** como provider de LLM
- 📦 Dependência `google-generativeai==0.3.2`
- 📝 Arquivo `GEMINI_SUPPORT.md` com documentação completa
- 🔧 Variável de ambiente `GEMINI_API_KEY`
- 🧪 Testes para validação da API key do Gemini

### Modificado
- 🔄 `panfleto_processor.py` - Adicionado método `analisar_imagem_gemini()`
- 🔄 `panfleto_processor.py` - Atualizado `LLMClient` para suportar Gemini
- 📄 `.env.example` - Adicionado exemplo de configuração Gemini
- 📚 `README.md` - Atualizado com instruções Gemini
- 📚 `QUICK_START.md` - Adicionado guia rápido Gemini
- 📚 `PROJECT_SUMMARY.md` - Incluído Gemini nas features
- 🧪 `test_connection.py` - Adicionado validação Gemini

### Benefícios
- 💰 Opção gratuita (até 60 req/min)
- 💵 Menor custo no plano pago (~$0.002-0.005/imagem)
- 🚀 Mais acessível para testes e pequena escala
- ⚡ Performance similar aos outros providers

## [1.0.0] - 2025-01-13

### Adicionado
- 🎉 Release inicial do sistema
- 📦 Suporte OpenAI GPT-4 Vision
- 📦 Suporte Anthropic Claude
- 🗄️ Schema PostgreSQL completo
- 📊 4 tabelas (produtos, supermercados, preços, imagens)
- 🔍 Sistema de busca e normalização
- 📤 Exportação para CSV
- 📈 Estatísticas e relatórios
- 🔄 Sistema de retry automático
- ✅ Validação completa de dados
- 📝 Documentação abrangente
- 🧪 Script de teste de conexão
- 📚 8 exemplos de uso
- 🛠️ CLI completa com argparse
- 🎨 Pretty printing com emojis
- 📊 Barra de progresso (tqdm)

### Características Técnicas
- Type hints completos
- Docstrings detalhadas
- Context managers
- Logging extensivo
- Tratamento robusto de erros
- PEP 8 compliant
- ~2.500 linhas de código

---

## Formato

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## Tipos de Mudanças

- `Adicionado` para novas funcionalidades
- `Modificado` para mudanças em funcionalidades existentes
- `Depreciado` para funcionalidades que serão removidas
- `Removido` para funcionalidades removidas
- `Corrigido` para correções de bugs
- `Segurança` para vulnerabilidades

## Links de Versão

- [1.1.0] - 2025-01-14 - Suporte Google Gemini
- [1.0.0] - 2025-01-13 - Release inicial
