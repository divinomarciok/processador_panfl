#!/usr/bin/env python3
"""
Exemplos de uso programático do sistema.
"""

from dotenv import load_dotenv
from src.database import criar_conexao_do_env, PanfletoDatabase
from src.panfleto_processor import processar_panfleto

# Carregar variáveis de ambiente
load_dotenv()


# ==============================================================================
# EXEMPLO 1: Processar uma imagem simples
# ==============================================================================
def exemplo_processar_imagem():
    """Exemplo básico: processar uma imagem."""
    print("\n" + "=" * 60)
    print("EXEMPLO 1: Processar uma imagem")
    print("=" * 60 + "\n")

    # Conectar ao banco
    db_conn = criar_conexao_do_env()
    db_conn.connect()
    db = PanfletoDatabase(db_conn)

    # Processar panfleto
    caminho = "panfleto.jpg"  # Substitua pelo caminho real
    dados = processar_panfleto(caminho)

    # Salvar no banco
    stats = db.salvar_panfleto_completo(
        nome_arquivo="panfleto.jpg",
        caminho_arquivo=caminho,
        dados_json=dados
    )

    print(f"✓ {stats['precos_salvos']} preços salvos")
    print(f"✓ {stats['produtos_novos']} produtos novos")

    # Fechar conexão
    db_conn.close()


# ==============================================================================
# EXEMPLO 2: Processar múltiplas imagens
# ==============================================================================
def exemplo_processar_multiplas():
    """Processa múltiplas imagens de uma lista."""
    print("\n" + "=" * 60)
    print("EXEMPLO 2: Processar múltiplas imagens")
    print("=" * 60 + "\n")

    imagens = [
        "panfleto1.jpg",
        "panfleto2.jpg",
        "panfleto3.jpg"
    ]

    db_conn = criar_conexao_do_env()
    db_conn.connect()
    db = PanfletoDatabase(db_conn)

    for caminho in imagens:
        try:
            print(f"Processando: {caminho}")
            dados = processar_panfleto(caminho)
            stats = db.salvar_panfleto_completo(
                nome_arquivo=caminho,
                caminho_arquivo=caminho,
                dados_json=dados
            )
            print(f"  ✓ {stats['precos_salvos']} preços salvos\n")
        except Exception as e:
            print(f"  ❌ Erro: {e}\n")

    db_conn.close()


# ==============================================================================
# EXEMPLO 3: Consultar produtos mais baratos
# ==============================================================================
def exemplo_produtos_mais_baratos():
    """Busca os produtos mais baratos no banco."""
    print("\n" + "=" * 60)
    print("EXEMPLO 3: Produtos mais baratos")
    print("=" * 60 + "\n")

    db_conn = criar_conexao_do_env()
    db_conn.connect()

    query = """
        SELECT
            p.nome,
            p.marca,
            pp.preco,
            s.nome as supermercado,
            pp.validade_fim
        FROM precos_panfleto pp
        INNER JOIN produtos_tabela p ON pp.produto_id = p.id
        INNER JOIN supermercados s ON pp.supermercado_id = s.id
        WHERE pp.validade_fim >= CURRENT_DATE
        ORDER BY pp.preco ASC
        LIMIT 10
    """

    with db_conn.get_cursor() as cursor:
        cursor.execute(query)
        resultados = cursor.fetchall()

        for idx, row in enumerate(resultados, 1):
            print(f"{idx}. {row['nome']} - R$ {row['preco']:.2f}")
            print(f"   {row['supermercado']} (válido até {row['validade_fim']})\n")

    db_conn.close()


# ==============================================================================
# EXEMPLO 4: Buscar promoções ativas
# ==============================================================================
def exemplo_promocoes_ativas():
    """Lista todas as promoções ativas."""
    print("\n" + "=" * 60)
    print("EXEMPLO 4: Promoções ativas")
    print("=" * 60 + "\n")

    db_conn = criar_conexao_do_env()
    db_conn.connect()

    query = """
        SELECT
            p.nome,
            s.nome as supermercado,
            pp.preco_original,
            pp.preco,
            ROUND(((pp.preco_original - pp.preco) / pp.preco_original * 100)::numeric, 2) as desconto
        FROM precos_panfleto pp
        INNER JOIN produtos_tabela p ON pp.produto_id = p.id
        INNER JOIN supermercados s ON pp.supermercado_id = s.id
        WHERE pp.em_promocao = TRUE
            AND pp.validade_fim >= CURRENT_DATE
        ORDER BY desconto DESC
        LIMIT 10
    """

    with db_conn.get_cursor() as cursor:
        cursor.execute(query)
        resultados = cursor.fetchall()

        for row in resultados:
            print(f"🏷️  {row['nome']} - {row['supermercado']}")
            print(f"   De R$ {row['preco_original']:.2f} por R$ {row['preco']:.2f}")
            print(f"   Desconto: {row['desconto']}%\n")

    db_conn.close()


# ==============================================================================
# EXEMPLO 5: Criar produto manualmente
# ==============================================================================
def exemplo_criar_produto():
    """Cria um produto manualmente no banco."""
    print("\n" + "=" * 60)
    print("EXEMPLO 5: Criar produto manualmente")
    print("=" * 60 + "\n")

    db_conn = criar_conexao_do_env()
    db_conn.connect()
    db = PanfletoDatabase(db_conn)

    # Criar produto
    produto_id = db.criar_produto(
        nome="Arroz Tio João 5kg",
        marca="Tio João",
        categoria="Alimentos",
        codigo_barras="7891234567890"
    )

    print(f"✓ Produto criado com ID: {produto_id}")

    # Criar supermercado
    super_id = db.criar_supermercado(
        nome="Carrefour",
        rede="Carrefour",
        cidade="São Paulo",
        estado="SP"
    )

    print(f"✓ Supermercado criado com ID: {super_id}")

    # Criar preço
    preco_id = db.salvar_preco(
        produto_id=produto_id,
        supermercado_id=super_id,
        imagem_id=1,  # Assumindo que existe
        preco=23.90,
        preco_original=29.90,
        em_promocao=True,
        unidade="pct"
    )

    print(f"✓ Preço salvo com ID: {preco_id}")

    db_conn.close()


# ==============================================================================
# EXEMPLO 6: Buscar histórico de preços
# ==============================================================================
def exemplo_historico_precos(nome_produto: str):
    """Busca histórico de preços de um produto."""
    print("\n" + "=" * 60)
    print(f"EXEMPLO 6: Histórico de preços - {nome_produto}")
    print("=" * 60 + "\n")

    db_conn = criar_conexao_do_env()
    db_conn.connect()

    query = """
        SELECT
            s.nome as supermercado,
            pp.preco,
            pp.em_promocao,
            pp.validade_inicio,
            pp.created_at
        FROM precos_panfleto pp
        INNER JOIN produtos_tabela p ON pp.produto_id = p.id
        INNER JOIN supermercados s ON pp.supermercado_id = s.id
        WHERE LOWER(p.nome) LIKE LOWER(%s)
        ORDER BY pp.created_at DESC
        LIMIT 20
    """

    with db_conn.get_cursor() as cursor:
        cursor.execute(query, (f"%{nome_produto}%",))
        resultados = cursor.fetchall()

        if not resultados:
            print(f"Nenhum registro encontrado para '{nome_produto}'")
        else:
            for row in resultados:
                promo = "🏷️ " if row['em_promocao'] else ""
                print(f"{promo}{row['supermercado']}: R$ {row['preco']:.2f}")
                print(f"   Data: {row['created_at'].strftime('%d/%m/%Y')}\n")

    db_conn.close()


# ==============================================================================
# EXEMPLO 7: Estatísticas gerais
# ==============================================================================
def exemplo_estatisticas():
    """Mostra estatísticas gerais do banco."""
    print("\n" + "=" * 60)
    print("EXEMPLO 7: Estatísticas gerais")
    print("=" * 60 + "\n")

    db_conn = criar_conexao_do_env()
    db_conn.connect()
    db = PanfletoDatabase(db_conn)

    stats = db.obter_estatisticas()

    print(f"📊 Total de produtos: {stats['total_produtos']}")
    print(f"📊 Total de supermercados: {stats['total_supermercados']}")
    print(f"📊 Total de preços: {stats['total_precos']}")
    print(f"📊 Total de imagens: {stats['total_imagens']}")
    print(f"📊 Preço médio: R$ {stats['preco_medio']:.2f}")
    print(f"📊 Promoções ativas: {stats['total_promocoes']}")

    db_conn.close()


# ==============================================================================
# EXEMPLO 8: Comparar preços entre supermercados
# ==============================================================================
def exemplo_comparar_precos(nome_produto: str):
    """Compara preços de um produto entre supermercados."""
    print("\n" + "=" * 60)
    print(f"EXEMPLO 8: Comparar preços - {nome_produto}")
    print("=" * 60 + "\n")

    db_conn = criar_conexao_do_env()
    db_conn.connect()

    query = """
        SELECT DISTINCT ON (s.id)
            s.nome as supermercado,
            pp.preco,
            pp.em_promocao,
            pp.validade_fim
        FROM precos_panfleto pp
        INNER JOIN produtos_tabela p ON pp.produto_id = p.id
        INNER JOIN supermercados s ON pp.supermercado_id = s.id
        WHERE LOWER(p.nome) LIKE LOWER(%s)
            AND (pp.validade_fim >= CURRENT_DATE OR pp.validade_fim IS NULL)
        ORDER BY s.id, pp.created_at DESC
    """

    with db_conn.get_cursor() as cursor:
        cursor.execute(query, (f"%{nome_produto}%",))
        resultados = cursor.fetchall()

        if not resultados:
            print(f"Nenhum preço encontrado para '{nome_produto}'")
        else:
            # Ordenar por preço
            resultados = sorted(resultados, key=lambda x: x['preco'])

            print(f"Encontrados {len(resultados)} preços:\n")

            for idx, row in enumerate(resultados, 1):
                promo = "🏷️  EM PROMOÇÃO" if row['em_promocao'] else ""
                melhor = "⭐ MELHOR PREÇO" if idx == 1 else ""

                print(f"{idx}. {row['supermercado']}: R$ {row['preco']:.2f} {promo} {melhor}")
                if row['validade_fim']:
                    print(f"   Válido até: {row['validade_fim']}")
                print()

    db_conn.close()


# ==============================================================================
# MENU PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  EXEMPLOS DE USO - Sistema de Extração de Panfletos")
    print("=" * 60)

    print("\nEscolha um exemplo para executar:\n")
    print("1. Processar uma imagem")
    print("2. Processar múltiplas imagens")
    print("3. Produtos mais baratos")
    print("4. Promoções ativas")
    print("5. Criar produto manualmente")
    print("6. Histórico de preços")
    print("7. Estatísticas gerais")
    print("8. Comparar preços entre supermercados")
    print("0. Sair")

    escolha = input("\nDigite o número do exemplo: ")

    try:
        if escolha == "1":
            exemplo_processar_imagem()
        elif escolha == "2":
            exemplo_processar_multiplas()
        elif escolha == "3":
            exemplo_produtos_mais_baratos()
        elif escolha == "4":
            exemplo_promocoes_ativas()
        elif escolha == "5":
            exemplo_criar_produto()
        elif escolha == "6":
            produto = input("Digite o nome do produto: ")
            exemplo_historico_precos(produto)
        elif escolha == "7":
            exemplo_estatisticas()
        elif escolha == "8":
            produto = input("Digite o nome do produto: ")
            exemplo_comparar_precos(produto)
        elif escolha == "0":
            print("\nAté logo!")
        else:
            print("\nOpção inválida!")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
