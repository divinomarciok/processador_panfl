#!/usr/bin/env python3
"""
Script de teste para a expansão inteligente de produtos.
"""

import sys
import os
import logging

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(__file__))

from src.database import PanfletoDatabase, DatabaseConnection

# Configurar logging para ver os debugs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

# Casos de teste
CASOS_TESTE = [
    {
        "nome": "Coca-Cola Tradicional ou Zero",
        "esperado": ["Coca-Cola Tradicional", "Coca-Cola Zero"]
    },
    {
        "nome": "Leite Integral ou Desnatado",
        "esperado": ["Leite Integral", "Leite Desnatado"]
    },
    {
        "nome": "Picanha ou Alcatra",
        "esperado": ["Picanha", "Alcatra"]
    },
    {
        "nome": "Bombom Sonho de Valsa ou Ouro Branco",
        "esperado": ["Bombom Sonho de Valsa", "Bombom Ouro Branco"]
    },
    {
        "nome": "Refrigerante Guaraná ou Fanta ou Sprite",
        "esperado": ["Refrigerante Guaraná", "Refrigerante Fanta", "Refrigerante Sprite"]
    },
    {
        "nome": "Arroz Agulhinha ou Parboilizado",
        "esperado": ["Arroz Agulhinha", "Arroz Parboilizado"]
    },
]


def testar_expansao():
    """Testa a expansão de produtos sem conexão com banco."""

    # Criar instância mock (não vai usar banco)
    db_conn = DatabaseConnection("localhost", "test", "user", "pass")
    db = PanfletoDatabase(db_conn)

    print("=" * 70)
    print("TESTE DE EXPANSÃO INTELIGENTE DE PRODUTOS")
    print("=" * 70)
    print()

    total_testes = len(CASOS_TESTE)
    testes_ok = 0

    for i, caso in enumerate(CASOS_TESTE, 1):
        nome_original = caso["nome"]
        esperado = caso["esperado"]

        print(f"Teste {i}/{total_testes}: {nome_original}")
        print("-" * 70)

        # Simular produto_data
        produto_data = {
            "nome": nome_original,
            "preco": 10.50,
            "categoria": "Teste"
        }

        # Executar expansão
        resultado = db._expandir_produtos_multiplos(produto_data)

        # Extrair nomes resultantes
        nomes_resultantes = [p["nome"] for p in resultado]

        print(f"Esperado:   {esperado}")
        print(f"Resultado:  {nomes_resultantes}")

        # Verificar se está correto
        if nomes_resultantes == esperado:
            print("✅ PASSOU")
            testes_ok += 1
        else:
            print("❌ FALHOU")

        print()

    print("=" * 70)
    print(f"RESULTADO: {testes_ok}/{total_testes} testes passaram")
    print("=" * 70)

    return testes_ok == total_testes


if __name__ == "__main__":
    sucesso = testar_expansao()
    sys.exit(0 if sucesso else 1)
