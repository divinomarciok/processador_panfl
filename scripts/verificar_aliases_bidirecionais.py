#!/usr/bin/env python3
"""
Script para detectar aliases bidirecionais (erro de design).

Aliases bidirecionais indicam que dois produtos duplicados não foram mesclados,
apenas receberam aliases apontando um para o outro.

Exemplo do problema:
  Produto 222: "Abóbora Cabotiá" → alias "Abóbora Kabotiá"
  Produto 435: "Abóbora Kabotiá" → alias "Abóbora Cabotiá"

Correto seria:
  Mesclar produto 435 em produto 222
  Manter apenas: Produto 222 com alias "Abóbora Kabotiá"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.database import criar_conexao_do_env
import logging

logging.basicConfig(level=logging.WARNING)


def verificar_aliases_bidirecionais():
    """Detecta aliases bidirecionais no banco."""
    load_dotenv()

    db = criar_conexao_do_env()
    db.connect()

    # Query para encontrar aliases bidirecionais
    query = """
        WITH aliases_normalized AS (
            SELECT
                pa.id as alias_id,
                pa.produto_id,
                p.nome as produto_nome,
                pa.alias,
                pa.alias_normalizado,
                pa.origem,
                pa.confianca,
                pa.created_at
            FROM produtos_aliases pa
            INNER JOIN produtos_tabela p ON pa.produto_id = p.id
        )
        SELECT
            a1.produto_id as produto1_id,
            a1.produto_nome as produto1_nome,
            a1.alias as produto1_alias,
            a1.alias_normalizado as produto1_alias_norm,
            a1.origem as produto1_origem,
            a1.confianca as produto1_confianca,

            a2.produto_id as produto2_id,
            a2.produto_nome as produto2_nome,
            a2.alias as produto2_alias,
            a2.alias_normalizado as produto2_alias_norm,
            a2.origem as produto2_origem,
            a2.confianca as produto2_confianca
        FROM aliases_normalized a1
        INNER JOIN aliases_normalized a2
            ON a1.produto_id < a2.produto_id  -- Evitar duplicar comparações
            AND normalizar_nome(a1.alias) = normalizar_nome(a2.produto_nome)
            AND normalizar_nome(a2.alias) = normalizar_nome(a1.produto_nome)
        ORDER BY a1.produto_id, a2.produto_id;
    """

    with db.get_cursor() as cursor:
        cursor.execute(query)
        casos = cursor.fetchall()

    db.close()

    print("\n" + "="*80)
    print("VERIFICAÇÃO DE ALIASES BIDIRECIONAIS")
    print("="*80)
    print(f"Total de casos encontrados: {len(casos)}")
    print("="*80)

    if not casos:
        print("\n✓ Nenhum alias bidirecional encontrado!")
        print("  Todos os aliases estão corretos (unidirecionais).")
        return

    print("\n⚠ PROBLEMA: Aliases bidirecionais detectados!")
    print("Esses produtos devem ser MESCLADOS, não apenas ter aliases cruzados.\n")

    for idx, caso in enumerate(casos, 1):
        print(f"\n{'─'*80}")
        print(f"CASO {idx}:")
        print(f"{'─'*80}")

        print(f"\n  Produto 1:")
        print(f"    ID: {caso['produto1_id']}")
        print(f"    Nome: {caso['produto1_nome']}")
        print(f"    Alias: {caso['produto1_alias']}")
        print(f"    Origem: {caso['produto1_origem']}")
        print(f"    Confiança: {caso['produto1_confianca']}")

        print(f"\n  Produto 2:")
        print(f"    ID: {caso['produto2_id']}")
        print(f"    Nome: {caso['produto2_nome']}")
        print(f"    Alias: {caso['produto2_alias']}")
        print(f"    Origem: {caso['produto2_origem']}")
        print(f"    Confiança: {caso['produto2_confianca']}")

        print(f"\n  ❌ PROBLEMA:")
        print(f"     Produto {caso['produto1_id']} tem alias '{caso['produto1_alias']}'")
        print(f"     Produto {caso['produto2_id']} tem alias '{caso['produto2_alias']}'")
        print(f"     → Ambos continuam como produtos SEPARADOS no banco!")

        print(f"\n  ✅ SOLUÇÃO:")
        print(f"     Mesclar produto {caso['produto2_id']} em produto {caso['produto1_id']}")
        print(f"     Manter apenas 1 alias: '{caso['produto1_alias']}'")

    print("\n" + "="*80)
    print("COMO CORRIGIR")
    print("="*80)
    print("\nPara cada caso acima, execute:")
    print("  python scripts/mesclar_duplicatas.py <produto1_id> <produto2_id>")
    print("\nOu corrija manualmente com SQL:")
    print("  UPDATE precos_panfleto SET produto_id = <produto1_id> WHERE produto_id = <produto2_id>;")
    print("  DELETE FROM produtos_aliases WHERE produto_id = <produto2_id>;")
    print("  DELETE FROM produtos_tabela WHERE id = <produto2_id>;")
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    verificar_aliases_bidirecionais()
