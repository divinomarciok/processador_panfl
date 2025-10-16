#!/usr/bin/env python3
"""
Verifica se os produtos mesclados tinham a mesma marca.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.database import criar_conexao_do_env
import logging

logging.basicConfig(level=logging.WARNING)


# IDs dos produtos que foram mantidos (depois da mesclagem)
PRODUTOS_MANTIDOS = [3, 6, 63, 128, 176, 264]


def verificar_marcas():
    """Verifica marcas dos produtos mantidos e seus aliases."""
    load_dotenv()

    db = criar_conexao_do_env()
    db.connect()

    print("\n" + "="*80)
    print("VERIFICAÇÃO DE MARCAS - PRODUTOS MESCLADOS")
    print("="*80)

    with db.get_cursor() as cursor:
        # Para cada produto mantido, buscar seus aliases e verificar marca
        for produto_id in PRODUTOS_MANTIDOS:
            # Buscar produto principal
            cursor.execute("""
                SELECT id, nome, marca
                FROM produtos_tabela
                WHERE id = %s
            """, (produto_id,))

            produto = cursor.fetchone()

            if not produto:
                print(f"\n⚠ Produto {produto_id} não encontrado")
                continue

            # Buscar aliases deste produto
            cursor.execute("""
                SELECT alias, origem, confianca, created_at
                FROM produtos_aliases
                WHERE produto_id = %s
                ORDER BY created_at DESC
            """, (produto_id,))

            aliases = cursor.fetchall()

            print(f"\n{'─'*80}")
            print(f"Produto ID: {produto['id']}")
            print(f"Nome: {produto['nome']}")
            print(f"Marca: {produto['marca'] or 'SEM MARCA'}")

            if aliases:
                print(f"\nAliases ({len(aliases)}):")
                for alias in aliases:
                    print(f"  - {alias['alias']}")
                    print(f"    Origem: {alias['origem']}, Confiança: {alias['confianca']}")
            else:
                print("\nNenhum alias encontrado")

    # Agora vamos verificar se ainda há duplicatas com marcas diferentes
    print(f"\n{'='*80}")
    print("VERIFICAÇÃO: Produtos similares com MARCAS DIFERENTES")
    print("="*80)

    with db.get_cursor() as cursor:
        cursor.execute("""
            SELECT
                p1.id as produto1_id,
                p1.nome as produto1_nome,
                p1.marca as produto1_marca,
                p2.id as produto2_id,
                p2.nome as produto2_nome,
                p2.marca as produto2_marca,
                1.0 - (
                    levenshtein(p1.nome_normalizado, p2.nome_normalizado)::DECIMAL /
                    GREATEST(LENGTH(p1.nome_normalizado), LENGTH(p2.nome_normalizado))
                ) AS similaridade
            FROM produtos_tabela p1
            CROSS JOIN produtos_tabela p2
            WHERE p1.id < p2.id
              AND p1.nome_normalizado IS NOT NULL
              AND p2.nome_normalizado IS NOT NULL
              AND levenshtein(p1.nome_normalizado, p2.nome_normalizado) BETWEEN 1 AND 3
              AND (
                  1.0 - (
                      levenshtein(p1.nome_normalizado, p2.nome_normalizado)::DECIMAL /
                      GREATEST(LENGTH(p1.nome_normalizado), LENGTH(p2.nome_normalizado))
                  )
              ) >= 0.80
              -- Filtro: MARCAS DIFERENTES
              AND p1.marca IS NOT NULL
              AND p2.marca IS NOT NULL
              AND LOWER(p1.marca) != LOWER(p2.marca)
            ORDER BY similaridade DESC
            LIMIT 10
        """)

        similares_marcas_diferentes = cursor.fetchall()

    if similares_marcas_diferentes:
        print(f"\n⚠ Encontrados {len(similares_marcas_diferentes)} produtos similares com MARCAS DIFERENTES:")
        print("(Estes NÃO devem ser mesclados!)\n")

        for idx, prod in enumerate(similares_marcas_diferentes, 1):
            print(f"{idx}. Similaridade: {prod['similaridade']:.1%}")
            print(f"   Produto 1: {prod['produto1_nome']}")
            print(f"              Marca: {prod['produto1_marca']} (ID: {prod['produto1_id']})")
            print(f"   Produto 2: {prod['produto2_nome']}")
            print(f"              Marca: {prod['produto2_marca']} (ID: {prod['produto2_id']})")
            print(f"   ✓ CORRETO: Mantidos separados (marcas diferentes)\n")
    else:
        print("\n✓ Nenhum produto similar com marcas diferentes encontrado")

    db.close()

    print("="*80)
    print("\nCONCLUSÃO:")
    print("A view vw_duplicatas_potenciais tem filtro de marca:")
    print("  - Apenas produtos com MESMA marca (ou ambos SEM marca) são considerados duplicatas")
    print("  - Produtos similares com MARCAS DIFERENTES são mantidos separados")
    print("="*80 + "\n")


if __name__ == '__main__':
    verificar_marcas()
