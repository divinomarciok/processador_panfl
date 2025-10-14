#!/usr/bin/env python3
"""
Script de teste para validar conexões e configuração.
"""

import sys
from dotenv import load_dotenv

print("=" * 60)
print("  TESTE DE CONFIGURAÇÃO")
print("=" * 60)
print()

# 1. Testar carregamento de variáveis de ambiente
print("1. Testando arquivo .env...")
try:
    load_dotenv()
    print("   ✓ Arquivo .env carregado")
except Exception as e:
    print(f"   ❌ Erro ao carregar .env: {e}")
    sys.exit(1)

# 2. Testar importação dos módulos
print("\n2. Testando importação dos módulos...")
try:
    from src.database import DatabaseConnection, PanfletoDatabase, criar_conexao_do_env
    print("   ✓ Módulo database.py OK")
except Exception as e:
    print(f"   ❌ Erro ao importar database: {e}")
    sys.exit(1)

try:
    from src.panfleto_processor import (
        ImageProcessor,
        LLMClient,
        JSONParser,
        PanfletoProcessor
    )
    print("   ✓ Módulo panfleto_processor.py OK")
except Exception as e:
    print(f"   ❌ Erro ao importar panfleto_processor: {e}")
    sys.exit(1)

# 3. Testar conexão com o banco
print("\n3. Testando conexão com PostgreSQL...")
try:
    db_conn = criar_conexao_do_env()
    db_conn.connect()
    print("   ✓ Conexão com PostgreSQL OK")

    # Testar query simples
    with db_conn.get_cursor() as cursor:
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"   ✓ PostgreSQL: {version['version'][:50]}...")

    db_conn.close()
except ValueError as e:
    print(f"   ❌ Erro de configuração: {e}")
    print("   → Verifique as variáveis DB_HOST, DB_NAME, DB_USER, DB_PASS no .env")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Erro de conexão: {e}")
    print("   → Verifique se o PostgreSQL está rodando")
    print("   → Verifique as credenciais no arquivo .env")
    sys.exit(1)

# 4. Testar configuração da LLM
print("\n4. Testando configuração da LLM...")
import os

llm_provider = os.getenv('LLM_PROVIDER', 'openai')
print(f"   Provider configurado: {llm_provider}")

if llm_provider == 'openai':
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key and api_key.startswith('sk-'):
        print(f"   ✓ OPENAI_API_KEY configurada (sk-...{api_key[-4:]})")
    else:
        print("   ⚠️  OPENAI_API_KEY não configurada ou inválida")
        print("   → Configure no arquivo .env")

elif llm_provider == 'anthropic':
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key and api_key.startswith('sk-ant-'):
        print(f"   ✓ ANTHROPIC_API_KEY configurada (sk-ant-...{api_key[-4:]})")
    else:
        print("   ⚠️  ANTHROPIC_API_KEY não configurada ou inválida")
        print("   → Configure no arquivo .env")

elif llm_provider == 'gemini':
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"   ✓ GEMINI_API_KEY configurada (...{api_key[-4:]})")
    else:
        print("   ⚠️  GEMINI_API_KEY não configurada ou inválida")
        print("   → Configure no arquivo .env")

# 5. Verificar tabelas do banco
print("\n5. Verificando tabelas do banco de dados...")
try:
    db_conn = criar_conexao_do_env()
    db_conn.connect()

    with db_conn.get_cursor() as cursor:
        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        tabelas = cursor.fetchall()

        if tabelas:
            print(f"   ✓ {len(tabelas)} tabelas encontradas:")
            for tabela in tabelas:
                print(f"      - {tabela['tablename']}")
        else:
            print("   ⚠️  Nenhuma tabela encontrada")
            print("   → Execute: python main.py --init-schema")

    db_conn.close()
except Exception as e:
    print(f"   ⚠️  Erro ao verificar tabelas: {e}")

# 6. Resumo
print("\n" + "=" * 60)
print("  RESUMO")
print("=" * 60)
print()
print("✓ Módulos Python OK")
print("✓ Conexão PostgreSQL OK")
print()

if api_key:
    print("✓ Sistema pronto para uso!")
    print()
    print("Próximos passos:")
    if not tabelas:
        print("1. Inicialize o schema: python main.py --init-schema")
        print("2. Processe uma imagem: python main.py imagem.jpg")
    else:
        print("1. Processe uma imagem: python main.py imagem.jpg")
        print("2. Veja as estatísticas: python main.py --stats")
else:
    print("⚠️  Configure a API key da LLM no arquivo .env")
    print()

print()
