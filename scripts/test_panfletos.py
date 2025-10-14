#!/usr/bin/env python3
"""
Script de teste para processar panfletos usando Gemini API.
Testa apenas o processamento de imagem sem salvar no banco.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importar o processador
from src.panfleto_processor import processar_panfleto

def formatar_preco(valor: float) -> str:
    """Formata valor como preço em reais."""
    return f"R$ {valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')


def testar_imagem(caminho: str):
    """Testa processamento de uma única imagem."""
    print("=" * 60)
    print(f"  TESTE DE PROCESSAMENTO DE PANFLETO")
    print("=" * 60)
    print()

    nome_arquivo = os.path.basename(caminho)
    print(f"📁 Arquivo: {nome_arquivo}")
    print(f"🤖 Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
    print()

    try:
        print("🔄 Processando imagem com LLM...")
        dados_json = processar_panfleto(caminho)

        print("✅ Imagem processada com sucesso!")
        print()

        # Mostrar dados extraídos
        if dados_json.get('supermercado'):
            print(f"🏪 Supermercado: {dados_json['supermercado']}")

        if dados_json.get('validade'):
            validade = dados_json['validade']
            if validade.get('inicio'):
                print(f"📅 Validade início: {validade['inicio']}")
            if validade.get('fim'):
                print(f"📅 Validade fim: {validade['fim']}")

        produtos = dados_json.get('produtos', [])
        print(f"\n📦 Total de produtos encontrados: {len(produtos)}")

        if produtos:
            print("\n" + "-" * 60)
            print("  PRODUTOS EXTRAÍDOS:")
            print("-" * 60)

            for idx, produto in enumerate(produtos, 1):
                nome = produto.get('nome', 'Desconhecido')
                preco = produto.get('preco', 0)
                marca = produto.get('marca', '')
                categoria = produto.get('categoria', '')
                unidade = produto.get('unidade', '')
                promo = produto.get('em_promocao', False)

                print(f"\n[{idx}] {nome}")
                print(f"    💰 Preço: {formatar_preco(preco)}")
                if marca:
                    print(f"    🏷️  Marca: {marca}")
                if categoria:
                    print(f"    📂 Categoria: {categoria}")
                if unidade:
                    print(f"    📏 Unidade: {unidade}")
                if promo:
                    print(f"    🎯 EM PROMOÇÃO")

            # Top 3 mais baratos
            produtos_ordenados = sorted(produtos, key=lambda x: x.get('preco', float('inf')))[:3]
            print("\n" + "=" * 60)
            print("  🎯 TOP 3 PRODUTOS MAIS BARATOS:")
            print("=" * 60)
            for idx, produto in enumerate(produtos_ordenados, 1):
                nome = produto.get('nome')
                preco = produto.get('preco')
                print(f"  {idx}. {nome} - {formatar_preco(preco)}")

        # Salvar JSON para análise
        json_path = caminho.replace('.jpeg', '.json').replace('.jpg', '.json').replace('.png', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(dados_json, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Dados salvos em: {json_path}")

        return dados_json

    except Exception as e:
        print(f"❌ Erro ao processar: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print("Uso: python test_panfletos.py <caminho_imagem>")
        print("\nExemplos:")
        print('  python test_panfletos.py "panfletos/WhatsApp Image 2025-10-13 at 09.13.51.jpeg"')
        print('  python test_panfletos.py panfletos/*.jpeg')
        sys.exit(1)

    caminho = sys.argv[1]

    if not os.path.exists(caminho):
        print(f"❌ Arquivo não encontrado: {caminho}")
        sys.exit(1)

    testar_imagem(caminho)


if __name__ == "__main__":
    main()
