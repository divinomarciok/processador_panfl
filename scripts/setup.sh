#!/bin/bash

# Script de setup rápido para o sistema de extração de panfletos

echo "=================================================="
echo "  SETUP - Sistema de Extração de Panfletos"
echo "=================================================="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.8+"
    exit 1
fi

echo "✓ Python encontrado: $(python3 --version)"

# Verificar PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL não encontrado. Certifique-se de instalá-lo."
else
    echo "✓ PostgreSQL encontrado"
fi

echo ""
echo "1. Criando ambiente virtual..."
python3 -m venv venv

echo "2. Ativando ambiente virtual..."
source venv/bin/activate

echo "3. Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "4. Configurando variáveis de ambiente..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Arquivo .env criado"
    echo "⚠️  IMPORTANTE: Edite o arquivo .env com suas credenciais!"
    echo ""
    echo "   - Configure DB_HOST, DB_NAME, DB_USER, DB_PASS"
    echo "   - Configure OPENAI_API_KEY ou ANTHROPIC_API_KEY"
    echo "   - Configure LLM_PROVIDER (openai ou anthropic)"
else
    echo "✓ Arquivo .env já existe"
fi

echo ""
echo "5. Para inicializar o banco de dados, execute:"
echo "   python main.py --init-schema"

echo ""
echo "=================================================="
echo "  SETUP CONCLUÍDO!"
echo "=================================================="
echo ""
echo "Próximos passos:"
echo "1. Edite o arquivo .env com suas credenciais"
echo "2. Execute: python main.py --init-schema"
echo "3. Processe uma imagem: python main.py imagem.jpg"
echo ""
echo "Para ajuda: python main.py --help"
echo ""
