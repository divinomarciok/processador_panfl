#!/usr/bin/env python3
"""
Script para testar busca de produtos usando aliases.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.database import criar_conexao_do_env, PanfletoDatabase
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def testar_busca_com_aliases():
    """Testa busca usando Python (buscar_produto_por_nome)."""
    load_dotenv()

    # Conectar ao banco
    db_conn = criar_conexao_do_env()
    db_conn.connect()
    panfleto_db = PanfletoDatabase(db_conn)

    print("\n" + "="*70)
    print("TESTE: Busca de Produtos com Aliases")
    print("="*70)

    # Casos de teste
    testes = [
        # Variações de Abóbora
        ("Abóbora Kabotiá", "Deve encontrar via alias"),
        ("Abóbora Cabotíá", "Deve encontrar via match exato"),
        ("Kabotiá", "Deve encontrar via fuzzy ou criar novo"),
        ("abobora kabotia", "Deve encontrar via normalização"),

        # Variações de Queijo Mussarela
        ("Queijo Mussarela Fatiado", "Deve encontrar via match exato"),
        ("Queijo Mussarela Fatiada", "Deve encontrar via alias"),

        # Variações de Contrafilé
        ("Contra Filé Bovino", "Deve encontrar via match exato"),
        ("Contrafilé Bovino", "Deve encontrar via alias"),

        # Produto não existente
        ("Produto Inventado XYZ", "Não deve encontrar nada"),
    ]

    print("\nTestando busca com diferentes variações:\n")

    for nome_busca, descricao in testes:
        print(f"{'='*70}")
        print(f"Buscando: '{nome_busca}'")
        print(f"Esperado: {descricao}")
        print("-" * 70)

        # Usar função Python
        produto = panfleto_db.buscar_produto_por_nome(nome_busca, margem=0.85)

        if produto:
            print(f"✓ ENCONTRADO!")
            print(f"  Nome no banco: {produto['nome']}")
            print(f"  ID: {produto['id']}")
            if 'origem_match' in produto:
                print(f"  Tipo de match: {produto['origem_match']}")
            if 'similaridade' in produto:
                print(f"  Similaridade: {produto['similaridade']:.1%}")
        else:
            print(f"✗ NÃO ENCONTRADO (será criado como produto novo)")

        print()

    db_conn.close()


if __name__ == '__main__':
    testar_busca_com_aliases()
