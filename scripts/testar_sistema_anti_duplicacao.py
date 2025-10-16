#!/usr/bin/env python3
"""
Script para testar sistema anti-duplicação.
Verifica funções SQL e busca duplicatas.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.database import criar_conexao_do_env, PanfletoDatabase
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def testar_funcoes_sql(db_conn):
    """Testa funções SQL criadas pela migration."""
    print("\n" + "="*70)
    print("TESTE 1: Verificar Funções SQL")
    print("="*70)

    with db_conn.get_cursor() as cursor:
        # 1. Testar normalizar_nome()
        print("\n1. Testando normalizar_nome():")
        testes = [
            "Abóbora Kabotia",
            "Abobora Cabotia",
            "Kabotia",
            "Coca-Cola Lata!!!",
            "Óleo de Soja Liza"
        ]

        for teste in testes:
            cursor.execute("SELECT normalizar_nome(%s) as resultado", (teste,))
            resultado = cursor.fetchone()['resultado']
            print(f"  '{teste}' → '{resultado}'")

        # 2. Verificar extensões
        print("\n2. Verificando extensões instaladas:")
        cursor.execute("""
            SELECT extname FROM pg_extension
            WHERE extname IN ('fuzzystrmatch', 'pg_trgm', 'unaccent')
        """)
        extensoes = [row['extname'] for row in cursor.fetchall()]
        print(f"  Extensões: {', '.join(extensoes)}")

        # 3. Verificar tabela de aliases
        print("\n3. Verificando tabela produtos_aliases:")
        cursor.execute("SELECT COUNT(*) as total FROM produtos_aliases")
        total_aliases = cursor.fetchone()['total']
        print(f"  Total de aliases: {total_aliases}")


def buscar_duplicatas_potenciais(db_conn):
    """Busca duplicatas potenciais no banco."""
    print("\n" + "="*70)
    print("TESTE 2: Buscar Duplicatas Potenciais")
    print("="*70)

    with db_conn.get_cursor() as cursor:
        # Buscar duplicatas com similaridade >= 80%
        cursor.execute("""
            SELECT
                produto1_id,
                produto1_nome,
                produto2_id,
                produto2_nome,
                similaridade,
                distancia
            FROM vw_duplicatas_potenciais
            ORDER BY similaridade DESC
            LIMIT 20
        """)

        duplicatas = cursor.fetchall()

        if duplicatas:
            print(f"\nEncontradas {len(duplicatas)} duplicatas potenciais:\n")
            for idx, dup in enumerate(duplicatas, 1):
                print(f"{idx}. Similaridade: {dup['similaridade']:.1%} (dist: {dup['distancia']})")
                print(f"   Produto 1: {dup['produto1_nome']} (ID: {dup['produto1_id']})")
                print(f"   Produto 2: {dup['produto2_nome']} (ID: {dup['produto2_id']})")
                print()
        else:
            print("\n✓ Nenhuma duplicata potencial encontrada!")

        return duplicatas


def testar_busca_inteligente(db_conn):
    """Testa função buscar_produto_inteligente()."""
    print("\n" + "="*70)
    print("TESTE 3: Buscar Produto Inteligente")
    print("="*70)

    # Pegar alguns produtos do banco para testar
    with db_conn.get_cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT nome
            FROM produtos_tabela
            ORDER BY created_at DESC
            LIMIT 5
        """)
        produtos_teste = [row['nome'] for row in cursor.fetchall()]

    if not produtos_teste:
        print("\n⚠ Nenhum produto no banco para testar")
        return

    print(f"\nTestando busca com {len(produtos_teste)} produtos existentes:\n")

    for nome_original in produtos_teste:
        # Testar variações do nome
        variacoes = [
            nome_original,  # Nome original
            nome_original.lower(),  # Lowercase
            nome_original.upper(),  # Uppercase
        ]

        print(f"Produto: {nome_original}")
        print("-" * 50)

        with db_conn.get_cursor() as cursor:
            for variacao in variacoes:
                cursor.execute("""
                    SELECT
                        nome, similaridade, origem_match
                    FROM buscar_produto_inteligente(%s, 0.85)
                """, (variacao,))

                resultado = cursor.fetchone()

                if resultado:
                    print(f"  '{variacao}' → Encontrado!")
                    print(f"    Nome: {resultado['nome']}")
                    print(f"    Similaridade: {resultado['similaridade']:.1%}")
                    print(f"    Tipo match: {resultado['origem_match']}")
                else:
                    print(f"  '{variacao}' → Não encontrado ❌")

        print()


def testar_busca_fuzzy_direta(db_conn):
    """Testa busca fuzzy com nomes conhecidos."""
    print("\n" + "="*70)
    print("TESTE 4: Busca Fuzzy com Erros Ortográficos")
    print("="*70)

    # Pegar um produto e testar variações
    with db_conn.get_cursor() as cursor:
        cursor.execute("""
            SELECT nome FROM produtos_tabela
            WHERE LENGTH(nome) > 10
            LIMIT 1
        """)
        produto = cursor.fetchone()

        if not produto:
            print("\n⚠ Nenhum produto adequado para teste")
            return

        nome_original = produto['nome']
        print(f"\nProduto original: {nome_original}")
        print("-" * 50)

        # Criar variações com erros
        import random
        nome_chars = list(nome_original)

        # Trocar 1-2 caracteres
        if len(nome_chars) > 5:
            idx1 = random.randint(0, len(nome_chars) - 1)
            nome_chars[idx1] = chr(ord(nome_chars[idx1]) + 1) if nome_chars[idx1].isalpha() else nome_chars[idx1]

        nome_com_erro = ''.join(nome_chars)

        print(f"Nome com erro: {nome_com_erro}\n")

        # Testar busca fuzzy
        cursor.execute("""
            SELECT
                nome, similaridade, distancia_levenshtein, origem_match
            FROM buscar_produto_fuzzy(%s, 0.80, 5)
        """, (nome_com_erro,))

        resultados = cursor.fetchall()

        if resultados:
            print(f"Encontrados {len(resultados)} produtos similares:")
            for r in resultados:
                print(f"  - {r['nome']}")
                print(f"    Similaridade: {r['similaridade']:.1%}")
                print(f"    Distância: {r['distancia_levenshtein']}")
        else:
            print("Nenhum produto similar encontrado")


def estatisticas_gerais(db_conn):
    """Mostra estatísticas gerais."""
    print("\n" + "="*70)
    print("ESTATÍSTICAS GERAIS")
    print("="*70)

    with db_conn.get_cursor() as cursor:
        # Total de produtos
        cursor.execute("SELECT COUNT(*) as total FROM produtos_tabela")
        total_produtos = cursor.fetchone()['total']

        # Total de produtos com nome_normalizado
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM produtos_tabela
            WHERE nome_normalizado IS NOT NULL
        """)
        produtos_normalizados = cursor.fetchone()['total']

        # Total de aliases
        cursor.execute("SELECT COUNT(*) as total FROM produtos_aliases")
        total_aliases = cursor.fetchone()['total']

        # Duplicatas potenciais
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM vw_duplicatas_potenciais
            WHERE similaridade >= 0.80
        """)
        duplicatas_80 = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(*) as total
            FROM vw_duplicatas_potenciais
            WHERE similaridade >= 0.90
        """)
        duplicatas_90 = cursor.fetchone()['total']

        print(f"\nTotal de produtos: {total_produtos}")
        print(f"Produtos normalizados: {produtos_normalizados} ({produtos_normalizados/total_produtos*100:.1f}%)")
        print(f"Total de aliases: {total_aliases}")
        print(f"Duplicatas potenciais (≥80%): {duplicatas_80}")
        print(f"Duplicatas potenciais (≥90%): {duplicatas_90}")


def main():
    """Função principal."""
    load_dotenv()

    # Conectar ao banco
    try:
        db = criar_conexao_do_env()
        db.connect()
        logger.info("✓ Conectado ao banco de dados\n")
    except Exception as e:
        logger.error(f"Erro ao conectar: {e}")
        return 1

    try:
        # Executar testes
        testar_funcoes_sql(db)
        duplicatas = buscar_duplicatas_potenciais(db)
        testar_busca_inteligente(db)
        testar_busca_fuzzy_direta(db)
        estatisticas_gerais(db)

        print("\n" + "="*70)
        print("✅ TESTES CONCLUÍDOS")
        print("="*70)

        if duplicatas:
            print(f"\n⚠ Foram encontradas {len(duplicatas)} duplicatas potenciais!")
            print("Execute: python scripts/popular_aliases.py")

    finally:
        db.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
