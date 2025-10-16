#!/usr/bin/env python3
"""
Script para corrigir todos os casos de aliases bidirecionais.

Divide os casos em:
1. Duplicatas reais → Mesclar produtos
2. Produtos diferentes → Remover aliases incorretos
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.database import criar_conexao_do_env
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Casos para MESCLAR (duplicatas reais)
CASOS_MESCLAR = [
    {
        'produto_manter': 3,
        'produto_deletar': 13,
        'descricao': 'Queijo Mussarela vs Queijo Mussarela KG',
        'motivo': 'Mesmo produto, variação com/sem "KG"'
    },
    {
        'produto_manter': 6,
        'produto_deletar': 15,
        'descricao': 'Catchup vs Ketchup',
        'motivo': 'Mesmo produto, erro ortográfico'
    },
    {
        'produto_manter': 63,
        'produto_deletar': 383,
        'descricao': 'Kit Shampoo + vs e',
        'motivo': 'Mesmo produto, variação de símbolo'
    },
    {
        'produto_manter': 128,
        'produto_deletar': 270,
        'descricao': 'Contra Filé vs Contrafilé',
        'motivo': 'Mesmo produto, variação de espaçamento'
    },
    {
        'produto_manter': 176,
        'produto_deletar': 196,
        'descricao': 'Biscoito Laminados vs Laminado',
        'motivo': 'Mesmo produto, plural/singular'
    },
    {
        'produto_manter': 264,
        'produto_deletar': 370,
        'descricao': 'Queijo Mussarela Fatiado vs Fatiada',
        'motivo': 'Mesmo produto, variação de gênero'
    },
]

# Casos para REMOVER aliases (produtos diferentes)
CASOS_REMOVER_ALIAS = [
    {
        'produto1_id': 98,
        'produto2_id': 163,
        'descricao': 'Papel Higiênico Folha Dupla vs Tripla',
        'motivo': 'Produtos DIFERENTES (dupla ≠ tripla)'
    },
    {
        'produto1_id': 359,
        'produto2_id': 360,
        'descricao': 'Pernil Suíno Sem Osso vs Com Osso',
        'motivo': 'Produtos DIFERENTES (com osso ≠ sem osso)'
    },
]


def mesclar_produto(db, produto_manter: int, produto_deletar: int, descricao: str, motivo: str):
    """Mescla produto_deletar em produto_manter."""
    logger.info(f"\n{'─'*80}")
    logger.info(f"MESCLANDO: {descricao}")
    logger.info(f"Motivo: {motivo}")
    logger.info(f"Mantendo produto {produto_manter}, deletando produto {produto_deletar}")

    with db.get_cursor() as cursor:
        # 1. Verificar se produtos existem
        cursor.execute("SELECT id, nome FROM produtos_tabela WHERE id IN (%s, %s)",
                      (produto_manter, produto_deletar))
        produtos = cursor.fetchall()

        if len(produtos) != 2:
            logger.warning(f"⚠ Um dos produtos não existe mais. Pulando...")
            return False

        # 2. Atualizar preços
        cursor.execute("""
            UPDATE precos_panfleto
            SET produto_id = %s
            WHERE produto_id = %s
        """, (produto_manter, produto_deletar))
        precos_atualizados = cursor.rowcount
        logger.info(f"  ✓ {precos_atualizados} preços atualizados")

        # 3. Deletar aliases do produto que será removido
        cursor.execute("DELETE FROM produtos_aliases WHERE produto_id = %s", (produto_deletar,))
        aliases_deletados = cursor.rowcount
        logger.info(f"  ✓ {aliases_deletados} aliases removidos")

        # 4. Deletar produto
        cursor.execute("DELETE FROM produtos_tabela WHERE id = %s", (produto_deletar,))
        logger.info(f"  ✓ Produto {produto_deletar} removido")

    # Commit automático ao sair do context manager
    logger.info(f"✅ Mesclagem concluída!")
    return True


def remover_aliases_incorretos(db, produto1_id: int, produto2_id: int, descricao: str, motivo: str):
    """Remove aliases bidirecionais entre dois produtos que SÃO diferentes."""
    logger.info(f"\n{'─'*80}")
    logger.info(f"REMOVENDO ALIASES INCORRETOS: {descricao}")
    logger.info(f"Motivo: {motivo}")
    logger.info(f"Produtos {produto1_id} e {produto2_id} são DIFERENTES e devem permanecer separados")

    with db.get_cursor() as cursor:
        # Buscar os aliases bidirecionais
        cursor.execute("""
            SELECT id, produto_id, alias
            FROM produtos_aliases
            WHERE (produto_id = %s OR produto_id = %s)
        """, (produto1_id, produto2_id))
        aliases = cursor.fetchall()

        if not aliases:
            logger.warning(f"⚠ Nenhum alias encontrado. Pulando...")
            return False

        # Mostrar aliases que serão removidos
        for alias in aliases:
            logger.info(f"  Removendo: produto_id={alias['produto_id']} → alias='{alias['alias']}'")

        # Deletar todos os aliases entre esses produtos
        cursor.execute("""
            DELETE FROM produtos_aliases
            WHERE produto_id IN (%s, %s)
        """, (produto1_id, produto2_id))
        total_removido = cursor.rowcount

    # Commit automático ao sair do context manager
    logger.info(f"✅ {total_removido} aliases incorretos removidos!")
    return True


def corrigir_todos_casos():
    """Corrige todos os casos de aliases bidirecionais."""
    load_dotenv()

    db = criar_conexao_do_env()
    db.connect()

    print("\n" + "="*80)
    print("CORREÇÃO DE ALIASES BIDIRECIONAIS")
    print("="*80)

    # Parte 1: Mesclar duplicatas reais
    print(f"\n{'='*80}")
    print(f"PARTE 1: MESCLAR DUPLICATAS REAIS ({len(CASOS_MESCLAR)} casos)")
    print(f"{'='*80}")

    mesclados = 0
    for caso in CASOS_MESCLAR:
        if mesclar_produto(
            db,
            caso['produto_manter'],
            caso['produto_deletar'],
            caso['descricao'],
            caso['motivo']
        ):
            mesclados += 1

    # Parte 2: Remover aliases incorretos
    print(f"\n{'='*80}")
    print(f"PARTE 2: REMOVER ALIASES INCORRETOS ({len(CASOS_REMOVER_ALIAS)} casos)")
    print(f"{'='*80}")

    removidos = 0
    for caso in CASOS_REMOVER_ALIAS:
        if remover_aliases_incorretos(
            db,
            caso['produto1_id'],
            caso['produto2_id'],
            caso['descricao'],
            caso['motivo']
        ):
            removidos += 1

    db.close()

    # Relatório final
    print("\n" + "="*80)
    print("RELATÓRIO FINAL")
    print("="*80)
    print(f"✅ Produtos mesclados: {mesclados}/{len(CASOS_MESCLAR)}")
    print(f"✅ Aliases incorretos removidos: {removidos}/{len(CASOS_REMOVER_ALIAS)}")
    print("\n" + "="*80)
    print("PRÓXIMOS PASSOS")
    print("="*80)
    print("1. Verificar se ainda há casos:")
    print("   python scripts/verificar_aliases_bidirecionais.py")
    print("\n2. Ver duplicatas restantes:")
    print("   python scripts/listar_duplicatas.py")
    print("="*80 + "\n")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Corrigir aliases bidirecionais')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Apenas mostrar o que seria feito, sem executar'
    )

    args = parser.parse_args()

    if args.dry_run:
        print("\n⚠ MODO DRY-RUN: Nenhuma alteração será feita no banco\n")
        # TODO: Implementar modo dry-run se necessário
    else:
        resposta = input("\n⚠ Isso vai MESCLAR produtos e REMOVER aliases. Continuar? (s/n): ")
        if resposta.lower() == 's':
            corrigir_todos_casos()
        else:
            print("Operação cancelada.")
