#!/usr/bin/env python3
"""
Script para listar duplicatas potenciais em detalhes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.database import criar_conexao_do_env
import logging

logging.basicConfig(level=logging.WARNING)


def listar_duplicatas(limite=50, similaridade_minima=0.80):
    """Lista duplicatas potenciais."""
    load_dotenv()

    db = criar_conexao_do_env()
    db.connect()

    with db.get_cursor() as cursor:
        cursor.execute("""
            SELECT
                produto1_id,
                produto1_nome,
                produto2_id,
                produto2_nome,
                similaridade,
                distancia
            FROM vw_duplicatas_potenciais
            WHERE similaridade >= %s
            ORDER BY similaridade DESC
            LIMIT %s
        """, (similaridade_minima, limite))

        duplicatas = cursor.fetchall()

    db.close()

    print("\n" + "="*80)
    print("DUPLICATAS POTENCIAIS NO BANCO DE DADOS")
    print("="*80)
    print(f"Critério: Similaridade ≥ {similaridade_minima:.0%}")
    print(f"Total encontrado: {len(duplicatas)}")
    print("="*80)

    if not duplicatas:
        print("\n✓ Nenhuma duplicata encontrada!")
        return

    # Agrupar por faixa de similaridade
    faixas = {
        'Alta (≥95%)': [],
        'Muito Alta (90-94%)': [],
        'Alta (85-89%)': [],
        'Média (80-84%)': []
    }

    for dup in duplicatas:
        sim = dup['similaridade']
        if sim >= 0.95:
            faixas['Alta (≥95%)'].append(dup)
        elif sim >= 0.90:
            faixas['Muito Alta (90-94%)'].append(dup)
        elif sim >= 0.85:
            faixas['Alta (85-89%)'].append(dup)
        else:
            faixas['Média (80-84%)'].append(dup)

    # Imprimir por faixa
    for faixa, items in faixas.items():
        if not items:
            continue

        print(f"\n{'='*80}")
        print(f"{faixa} - {len(items)} duplicatas")
        print('='*80)

        for idx, dup in enumerate(items, 1):
            print(f"\n{idx}. Similaridade: {dup['similaridade']:.1%} (Distância Levenshtein: {dup['distancia']})")
            print(f"   Produto 1: {dup['produto1_nome']}")
            print(f"              ID: {dup['produto1_id']}")
            print(f"   Produto 2: {dup['produto2_nome']}")
            print(f"              ID: {dup['produto2_id']}")

    print("\n" + "="*80)
    print("RESUMO")
    print("="*80)
    print(f"Total de duplicatas: {len(duplicatas)}")
    for faixa, items in faixas.items():
        if items:
            print(f"  {faixa}: {len(items)}")

    print("\n" + "="*80)
    print("PRÓXIMOS PASSOS")
    print("="*80)
    print("Para resolver duplicatas:")
    print("  1. Modo interativo: python scripts/popular_aliases.py")
    print("  2. Modo automático: python scripts/popular_aliases.py --auto")
    print("  3. Mesclar produtos: python scripts/mesclar_duplicatas.py")
    print("="*80 + "\n")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Listar duplicatas potenciais')
    parser.add_argument(
        '--similaridade',
        type=float,
        default=0.80,
        help='Similaridade mínima (0-1, padrão: 0.80)'
    )
    parser.add_argument(
        '--limite',
        type=int,
        default=50,
        help='Número máximo de duplicatas (padrão: 50)'
    )

    args = parser.parse_args()
    listar_duplicatas(limite=args.limite, similaridade_minima=args.similaridade)
