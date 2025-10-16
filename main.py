#!/usr/bin/env python3
"""
Script principal para processar panfletos de supermercado.

Uso:
    python main.py imagem.jpg
    python main.py --folder pasta_imagens/
    python main.py --image imagem.jpg --export saida.csv
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import csv

from dotenv import load_dotenv
from tqdm import tqdm

from src.database import (
    DatabaseConnection,
    PanfletoDatabase,
    criar_conexao_do_env
)
from src.panfleto_processor import processar_panfleto


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Extensões de imagem suportadas
EXTENSOES_SUPORTADAS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}


def formatar_preco(valor: float) -> str:
    """Formata valor como preço em reais."""
    return f"R$ {valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')


def imprimir_separador(char: str = "=", tamanho: int = 60):
    """Imprime linha separadora."""
    print(char * tamanho)


def imprimir_cabecalho(titulo: str):
    """Imprime cabeçalho formatado."""
    imprimir_separador()
    print(f"  {titulo}")
    imprimir_separador()


def processar_imagem_unica(
    caminho: str,
    db: PanfletoDatabase,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Processa uma única imagem.

    Args:
        caminho: Caminho da imagem
        db: Instância de PanfletoDatabase
        verbose: Se True, imprime detalhes

    Returns:
        Dict com estatísticas do processamento
    """
    nome_arquivo = os.path.basename(caminho)

    if verbose:
        print(f"\n🔄 Processando: {nome_arquivo}")

    try:
        # Processar imagem com LLM
        dados_json = processar_panfleto(caminho)

        if verbose:
            print(f"✅ JSON recebido com {len(dados_json.get('produtos', []))} produtos")
            print(f"\n💾 Salvando no banco de dados...")

        # Salvar no banco
        stats = db.salvar_panfleto_completo(
            nome_arquivo=nome_arquivo,
            caminho_arquivo=os.path.abspath(caminho),
            dados_json=dados_json
        )

        if verbose:
            # Mostrar resultados
            print(f"  ✓ Imagem salva (ID: {stats['imagem_id']})")
            if dados_json.get('supermercado'):
                print(f"  ✓ Supermercado: {dados_json['supermercado']} (ID: {stats['supermercado_id']})")

            print(f"\n📦 Processando produtos:")

            for idx in range(stats['precos_salvos']):
                if idx < len(dados_json['produtos']):
                    produto = dados_json['produtos'][idx]
                    nome = produto.get('nome', 'Desconhecido')
                    preco = produto.get('preco', 0)
                    print(f"  [{idx + 1}/{stats['total_produtos']}] {nome} ({formatar_preco(preco)}) ✓")

            # Resumo
            print(f"\n✅ Concluído!")
            print(f"   - {stats['total_produtos']} produtos encontrados")
            print(f"   - {stats['precos_salvos']} preços salvos")
            print(f"   - {stats['produtos_novos']} produtos novos criados")
            print(f"   - {stats['produtos_existentes']} produtos já existentes")

            if stats['erros']:
                print(f"\n⚠️  {len(stats['erros'])} avisos:")
                for erro in stats['erros'][:5]:  # Mostrar apenas os 5 primeiros
                    print(f"   - {erro}")

            # Produtos com menor preço
            if dados_json.get('produtos'):
                produtos_ordenados = sorted(
                    dados_json['produtos'],
                    key=lambda x: x.get('preco', float('inf'))
                )[:3]

                print(f"\n🎯 Produtos com menor preço:")
                for idx, produto in enumerate(produtos_ordenados, 1):
                    nome = produto.get('nome')
                    preco = produto.get('preco')
                    print(f"   {idx}. {nome} - {formatar_preco(preco)}")

        return stats

    except Exception as e:
        logger.error(f"Erro ao processar {nome_arquivo}: {e}")
        if verbose:
            print(f"❌ Erro: {str(e)}")

        # Tentar salvar erro no banco
        try:
            db.salvar_imagem_processada(
                nome_arquivo=nome_arquivo,
                caminho_arquivo=os.path.abspath(caminho),
                status='erro',
                erro_mensagem=str(e)
            )
        except:
            pass

        return {
            'erro': str(e),
            'arquivo': nome_arquivo
        }


def processar_pasta(
    pasta: str,
    db: PanfletoDatabase,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Processa todas as imagens de uma pasta.

    Args:
        pasta: Caminho da pasta
        db: Instância de PanfletoDatabase
        verbose: Se True, mostra progresso

    Returns:
        Lista com estatísticas de cada imagem
    """
    path = Path(pasta)

    if not path.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {pasta}")

    if not path.is_dir():
        raise ValueError(f"Não é uma pasta: {pasta}")

    # Buscar todas as imagens
    imagens = []
    for ext in EXTENSOES_SUPORTADAS:
        imagens.extend(path.glob(f"*{ext}"))
        imagens.extend(path.glob(f"*{ext.upper()}"))

    if not imagens:
        print(f"⚠️  Nenhuma imagem encontrada em {pasta}")
        return []

    if verbose:
        print(f"\n📁 Encontradas {len(imagens)} imagens em {pasta}")

    resultados = []

    # Processar com barra de progresso
    for caminho_imagem in tqdm(imagens, desc="Processando imagens", disable=not verbose):
        stats = processar_imagem_unica(
            str(caminho_imagem),
            db,
            verbose=False  # Não mostrar detalhes individuais em modo pasta
        )
        resultados.append(stats)

    # Resumo geral
    if verbose:
        total_produtos = sum(s.get('total_produtos', 0) for s in resultados if 'erro' not in s)
        total_novos = sum(s.get('produtos_novos', 0) for s in resultados if 'erro' not in s)
        total_precos = sum(s.get('precos_salvos', 0) for s in resultados if 'erro' not in s)
        erros = sum(1 for s in resultados if 'erro' in s)

        print(f"\n📊 RESUMO GERAL:")
        print(f"   - {len(imagens)} imagens processadas")
        print(f"   - {total_produtos} produtos encontrados")
        print(f"   - {total_novos} produtos novos")
        print(f"   - {total_precos} preços salvos")
        if erros > 0:
            print(f"   - {erros} erros")

    return resultados


def exportar_para_csv(db: PanfletoDatabase, arquivo_saida: str):
    """
    Exporta dados para CSV.

    Args:
        db: Instância de PanfletoDatabase
        arquivo_saida: Caminho do arquivo de saída
    """
    print(f"\n📤 Exportando dados para {arquivo_saida}...")

    query = """
        SELECT
            p.nome as produto,
            p.marca,
            p.categoria,
            pp.preco,
            pp.preco_original,
            pp.em_promocao,
            s.nome as supermercado,
            pp.validade_inicio,
            pp.validade_fim,
            pp.unidade,
            pp.created_at
        FROM precos_panfleto pp
        INNER JOIN produtos_tabela p ON pp.produto_id = p.id
        INNER JOIN supermercados s ON pp.supermercado_id = s.id
        ORDER BY pp.created_at DESC
    """

    with db.db.get_cursor() as cursor:
        cursor.execute(query)
        resultados = cursor.fetchall()

    if not resultados:
        print("⚠️  Nenhum dado para exportar")
        return

    # Escrever CSV
    with open(arquivo_saida, 'w', newline='', encoding='utf-8') as f:
        campos = [
            'produto', 'marca', 'categoria', 'preco', 'preco_original',
            'em_promocao', 'supermercado', 'validade_inicio', 'validade_fim',
            'unidade', 'created_at'
        ]
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()

        for row in resultados:
            writer.writerow(dict(row))

    print(f"✅ {len(resultados)} registros exportados")


def mostrar_estatisticas(db: PanfletoDatabase):
    """
    Mostra estatísticas gerais do banco.

    Args:
        db: Instância de PanfletoDatabase
    """
    print("\n📊 ESTATÍSTICAS DO BANCO DE DADOS:")
    imprimir_separador("-")

    stats = db.obter_estatisticas()

    print(f"  Total de produtos: {stats['total_produtos']}")
    print(f"  Total de supermercados: {stats['total_supermercados']}")
    print(f"  Total de preços: {stats['total_precos']}")
    print(f"  Total de imagens: {stats['total_imagens']}")
    print(f"  Preço médio: {formatar_preco(stats['preco_medio'])}")
    print(f"  Promoções ativas: {stats['total_promocoes']}")

    imprimir_separador("-")


def mostrar_categorias_sugeridas(db: PanfletoDatabase, limite: int = 20):
    """
    Mostra análise de categorias sugeridas pelo LLM.

    Args:
        db: Instância de PanfletoDatabase
        limite: Número máximo de categorias a exibir
    """
    print("\n🏷️  ANÁLISE DE CATEGORIAS SUGERIDAS:")
    imprimir_separador("=")

    # Estatísticas de mapeamento
    print("\n📊 Estatísticas de Mapeamento:")
    imprimir_separador("-")

    stats_mapeamento = db.obter_estatisticas_mapeamento_categorias()

    for tipo, dados in stats_mapeamento.items():
        qtd = dados['quantidade']
        pct = dados['percentual']
        print(f"  {tipo:20s}: {qtd:5d} produtos ({pct:5.1f}%)")

    # Categorias não mapeadas (classificadas como "Outros")
    print(f"\n🔍 Top {limite} Categorias Não Mapeadas (classificadas como 'Outros'):")
    imprimir_separador("-")

    categorias_nao_mapeadas = db.obter_categorias_sugeridas_mais_frequentes(
        limite=limite,
        apenas_nao_mapeadas=True
    )

    if not categorias_nao_mapeadas:
        print("  ✅ Todas as categorias foram mapeadas com sucesso!")
    else:
        print(f"\n  {'Categoria Sugerida':<30} | {'Qtd':>5} | Exemplos de Produtos")
        print(f"  {'-' * 30}-+-{'-' * 5}-+-{'-' * 50}")

        for cat in categorias_nao_mapeadas:
            nome_cat = cat['categoria_sugerida']
            qtd = cat['quantidade']
            exemplos = cat.get('exemplos_produtos', '')

            # Limitar exemplos a 50 caracteres
            if exemplos and len(exemplos) > 50:
                exemplos = exemplos[:47] + "..."

            print(f"  {nome_cat:<30} | {qtd:>5} | {exemplos}")

        print(f"\n💡 Dica: Adicione estas categorias ao MAPEAMENTO_CATEGORIAS")
        print(f"   ou crie novas categorias no banco de dados.")

    # Categorias mapeadas (diferente da sugerida)
    print(f"\n✅ Top {limite} Categorias Mapeadas Automaticamente:")
    imprimir_separador("-")

    categorias_mapeadas = db.obter_categorias_sugeridas_mais_frequentes(
        limite=limite,
        apenas_nao_mapeadas=False
    )

    if not categorias_mapeadas:
        print("  Nenhuma categoria foi mapeada ainda.")
    else:
        print(f"\n  {'Sugerida':<25} | {'Mapeada Para':<25} | {'Qtd':>5}")
        print(f"  {'-' * 25}-+-{'-' * 25}-+-{'-' * 5}")

        for cat in categorias_mapeadas:
            sugerida = cat['categoria_sugerida']
            mapeada = cat.get('categoria_mapeada', 'N/A')
            qtd = cat['quantidade']

            # Truncar se necessário
            if len(sugerida) > 25:
                sugerida = sugerida[:22] + "..."
            if len(mapeada) > 25:
                mapeada = mapeada[:22] + "..."

            print(f"  {sugerida:<25} | {mapeada:<25} | {qtd:>5}")

    imprimir_separador("=")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Processador de panfletos de supermercado usando LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py imagem.jpg
  python main.py --image imagem.jpg
  python main.py --folder pasta_imagens/
  python main.py --image img.jpg --export dados.csv
  python main.py --stats
  python main.py --categorias-sugeridas
  python main.py --init-schema
        """
    )

    parser.add_argument(
        'imagem',
        nargs='?',
        help='Caminho para a imagem do panfleto'
    )

    parser.add_argument(
        '--image', '-i',
        dest='imagem_arg',
        help='Caminho para a imagem do panfleto'
    )

    parser.add_argument(
        '--folder', '-f',
        help='Pasta contendo múltiplas imagens'
    )

    parser.add_argument(
        '--export', '-e',
        help='Exportar dados para CSV'
    )

    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        help='Mostrar estatísticas do banco'
    )

    parser.add_argument(
        '--categorias-sugeridas', '--cat',
        action='store_true',
        help='Analisar categorias sugeridas pelo LLM'
    )

    parser.add_argument(
        '--init-schema',
        action='store_true',
        help='Inicializar schema do banco de dados'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Modo silencioso (menos output)'
    )

    args = parser.parse_args()

    # Carregar variáveis de ambiente
    load_dotenv()

    # Banner
    if not args.quiet:
        imprimir_cabecalho("PROCESSADOR DE PANFLETOS - LLM + PostgreSQL")

    try:
        # Conectar ao banco
        db_conn = criar_conexao_do_env()
        db_conn.connect()
        db = PanfletoDatabase(db_conn)

        # Inicializar schema se solicitado
        if args.init_schema:
            print("\n🔧 Inicializando schema do banco de dados...")
            db.inicializar_schema()
            print("✅ Schema inicializado com sucesso!")
            return

        # Mostrar estatísticas
        if args.stats:
            mostrar_estatisticas(db)
            return

        # Mostrar análise de categorias sugeridas
        if args.categorias_sugeridas:
            mostrar_categorias_sugeridas(db)
            return

        # Exportar para CSV
        if args.export and not (args.imagem or args.imagem_arg or args.folder):
            exportar_para_csv(db, args.export)
            return

        # Determinar caminho da imagem
        caminho_imagem = args.imagem or args.imagem_arg

        # Processar pasta
        if args.folder:
            resultados = processar_pasta(args.folder, db, verbose=not args.quiet)

            # Exportar se solicitado
            if args.export:
                exportar_para_csv(db, args.export)

        # Processar imagem única
        elif caminho_imagem:
            stats = processar_imagem_unica(caminho_imagem, db, verbose=not args.quiet)

            # Exportar se solicitado
            if args.export and 'erro' not in stats:
                exportar_para_csv(db, args.export)

        else:
            parser.print_help()
            return

        # Estatísticas finais
        if not args.quiet and not args.stats:
            mostrar_estatisticas(db)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo usuário")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        print(f"\n❌ Erro: {str(e)}")
        sys.exit(1)

    finally:
        try:
            db_conn.close()
        except:
            pass


if __name__ == "__main__":
    main()
