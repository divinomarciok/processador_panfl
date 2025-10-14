# Suporte ao Google Gemini

O sistema agora suporta o Google Gemini como provider de LLM, além do OpenAI GPT-4 Vision e Anthropic Claude.

## O que mudou?

### Arquivos Atualizados

1. **requirements.txt**
   - Adicionado: `google-generativeai==0.3.2`

2. **panfleto_processor.py**
   - Adicionado método `analisar_imagem_gemini()`
   - Atualizado `LLMClient.__init__()` para suportar Gemini
   - Atualizado `_obter_api_key()` para buscar GEMINI_API_KEY
   - Atualizado `analisar_imagem()` para incluir Gemini no switch

3. **.env.example**
   - Adicionado: `GEMINI_API_KEY=...`
   - Atualizado: `LLM_PROVIDER` agora aceita `gemini`

4. **Documentação**
   - README.md: Atualizado com informações sobre Gemini
   - QUICK_START.md: Adicionado instruções de configuração
   - PROJECT_SUMMARY.md: Incluído Gemini nas features

5. **test_connection.py**
   - Adicionado teste para GEMINI_API_KEY

## Como usar o Gemini?

### 1. Obter API Key

Acesse o [Google AI Studio](https://makersuite.google.com/app/apikey) e gere uma API key gratuita.

### 2. Configurar .env

```env
# Adicione a API key do Gemini
GEMINI_API_KEY=sua_api_key_aqui

# Configure o provider
LLM_PROVIDER=gemini
```

### 3. Usar normalmente

```bash
# Processar uma imagem
python main.py panfleto.jpg

# O sistema usará automaticamente o Gemini
```

### 4. Uso programático

```python
from panfleto_processor import processar_panfleto

# Processar com Gemini (configurado no .env)
dados = processar_panfleto("panfleto.jpg")

# Ou especificar diretamente
dados = processar_panfleto("panfleto.jpg", llm_provider="gemini")
```

## Vantagens do Gemini

### Custo
- **Gratuito** até 60 requisições/minuto
- ~$0.002-0.005 por imagem no plano pago
- **Mais barato** que OpenAI e Anthropic

### Performance
- Modelo `gemini-1.5-pro` com boa qualidade
- Suporte nativo a imagens
- Processamento rápido

### Limites
- Gratuito: 60 requisições/minuto
- Imagens até 2048x2048px (já redimensionadas automaticamente)

## Comparação de Custos

| Provider | Custo por Imagem | 100 Imagens | Plano Grátis |
|----------|------------------|-------------|--------------|
| **Gemini** | $0.002-0.005 | $0.20-0.50 | Sim (60 req/min) |
| OpenAI | $0.01 | $1.00 | Não |
| Anthropic | $0.008 | $0.80 | Não |

## Detalhes Técnicos

### Modelo Usado
- `gemini-1.5-pro` - Modelo multimodal com visão

### Parâmetros
```python
generation_config={
    'temperature': 0.2,      # Respostas mais consistentes
    'max_output_tokens': 4096  # Limite de tokens
}
```

### Formato de Entrada
O Gemini aceita diretamente objetos PIL Image, então o código:
1. Decodifica a imagem base64 para bytes
2. Converte para PIL Image
3. Envia junto com o prompt

### Tratamento de Erros
- Sistema de retry (3 tentativas por padrão)
- Logs detalhados de erros
- Fallback automático se falhar

## Instalação do Pacote

```bash
# Atualizar dependências
pip install -r requirements.txt

# Ou instalar apenas o Gemini
pip install google-generativeai==0.3.2
```

## Exemplo Completo

```python
from dotenv import load_dotenv
from database import criar_conexao_do_env, PanfletoDatabase
from panfleto_processor import processar_panfleto

# Carregar .env com GEMINI_API_KEY
load_dotenv()

# Conectar ao banco
db_conn = criar_conexao_do_env()
db_conn.connect()
db = PanfletoDatabase(db_conn)

# Processar com Gemini (configurado no .env como LLM_PROVIDER=gemini)
dados = processar_panfleto("panfleto_atacadao.jpg")

print(f"Encontrados {len(dados['produtos'])} produtos")

# Salvar no banco
stats = db.salvar_panfleto_completo(
    nome_arquivo="panfleto_atacadao.jpg",
    caminho_arquivo="panfleto_atacadao.jpg",
    dados_json=dados
)

print(f"Salvos {stats['precos_salvos']} preços")

db_conn.close()
```

## Troubleshooting

### Erro: "GEMINI_API_KEY não definida"
```bash
# Verifique se a key está no .env
cat .env | grep GEMINI_API_KEY

# Configure a key
echo "GEMINI_API_KEY=sua_key" >> .env
```

### Erro: "Instale: pip install google-generativeai"
```bash
pip install google-generativeai==0.3.2
```

### Erro de quota (rate limit)
```bash
# O plano gratuito tem limite de 60 req/min
# Aguarde 1 minuto ou use outro provider
# O sistema faz retry automático

# Ou configure delay entre requests no código
```

## Quando usar cada provider?

### Use Gemini quando:
- ✅ Quer testar sem custos (plano gratuito)
- ✅ Processar poucas imagens por minuto (< 60)
- ✅ Busca o menor custo possível
- ✅ Qualidade boa é suficiente

### Use OpenAI quando:
- ✅ Precisa da melhor qualidade possível
- ✅ Volume alto sem preocupação com custo
- ✅ Já tem créditos da OpenAI

### Use Anthropic quando:
- ✅ Quer equilíbrio custo/qualidade
- ✅ Prefere o Claude por outros motivos
- ✅ Precisa de contextos muito longos

## Documentação Oficial

- [Google AI Studio](https://makersuite.google.com/)
- [Gemini API Docs](https://ai.google.dev/docs)
- [Python SDK](https://github.com/google/generative-ai-python)

## Conclusão

O suporte ao Gemini adiciona uma opção gratuita e econômica ao sistema, tornando-o acessível para testes e uso em pequena escala sem custos iniciais.

---

**Data da atualização:** 2025-01-14
**Versão:** 1.1.0
