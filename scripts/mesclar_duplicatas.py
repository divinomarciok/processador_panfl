"""
Script para Mesclar Produtos Duplicados.

Este script identifica produtos duplicados (baseado em nome_normalizado)
e mescla seus registros, mantendo o mais antigo e transferindo todos os preços.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Carregar variáveis de ambiente
load_dotenv()

from src.database import criar_conexao_do_env, PanfletoDatabase
import psycopg2
from typing import List, Dict, Any
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MescladorDuplicatas:
    """Classe para mesclar produtos duplicados."""

    def __init__(self, db_connection):
        """
        Inicializa o mesclador.

        Args:
            db_connection: Conexão com o banco de dados
        """
        self.db = db_connection
        self.estatisticas = {
            'grupos_duplicados': 0,
            'produtos_mesclados': 0,
            'precos_transferidos': 0,
            'produtos_removidos': 0
        }

    def detectar_duplicatas(self) -> List[Dict[str, Any]]:
        """
        Detecta todos os grupos de produtos duplicados.

        Returns:
            Lista de dicts com informações sobre duplicatas
        """
        query = """
            SELECT * FROM vw_duplicatas_detalhadas
            ORDER BY quantidade_duplicatas DESC
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            return [dict(row) for row in results]

    def obter_produtos_duplicados(self, nome_normalizado: str) -> List[Dict[str, Any]]:
        """
        Obtém todos os produtos com o mesmo nome normalizado.

        Args:
            nome_normalizado: Nome normalizado do produto

        Returns:
            Lista de produtos duplicados
        """
        query = """
            SELECT
                id,
                nome,
                marca,
                categoria,
                categoria_id,
                categoria_sugerida,
                codigo_barras,
                descricao,
                created_at,
                (SELECT COUNT(*) FROM precos_panfleto WHERE produto_id = produtos_tabela.id) as total_precos
            FROM produtos_tabela
            WHERE nome_normalizado = %s
            ORDER BY created_at ASC
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (nome_normalizado,))
            results = cursor.fetchall()
            return [dict(row) for row in results]

    def escolher_produto_principal(self, produtos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Escolhe qual produto será mantido (o principal).

        Critérios:
        1. Produto mais antigo (primeiro criado)
        2. Produto com mais informações preenchidas
        3. Produto com mais preços associados

        Args:
            produtos: Lista de produtos duplicados

        Returns:
            Produto escolhido como principal
        """
        # Ordenar por: mais preços, mais campos preenchidos, mais antigo
        def score_produto(p):
            campos_preenchidos = sum([
                bool(p.get('marca')),
                bool(p.get('categoria_id')),
                bool(p.get('codigo_barras')),
                bool(p.get('descricao'))
            ])
            return (
                p.get('total_precos', 0),  # Mais preços primeiro
                campos_preenchidos,         # Mais campos preenchidos
                -p['created_at'].timestamp()  # Mais antigo (negativo para ordem crescente)
            )

        produtos_ordenados = sorted(produtos, key=score_produto, reverse=True)
        return produtos_ordenados[0]

    def mesclar_informacoes(self, produto_principal: Dict, produto_secundario: Dict) -> Dict:
        """
        Mescla informações de produto secundário no principal.

        Args:
            produto_principal: Produto que será mantido
            produto_secundario: Produto que será mesclado

        Returns:
            Dict com informações atualizadas do produto principal
        """
        atualizacoes = {}

        # Completar campos vazios do principal com dados do secundário
        campos = ['marca', 'categoria_id', 'codigo_barras', 'descricao']
        for campo in campos:
            if not produto_principal.get(campo) and produto_secundario.get(campo):
                atualizacoes[campo] = produto_secundario[campo]

        return atualizacoes

    def transferir_precos(self, produto_origem_id: int, produto_destino_id: int) -> int:
        """
        Transfere todos os preços de um produto para outro.

        Args:
            produto_origem_id: ID do produto de origem
            produto_destino_id: ID do produto de destino

        Returns:
            Número de preços transferidos
        """
        query = """
            UPDATE precos_panfleto
            SET produto_id = %s
            WHERE produto_id = %s
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (produto_destino_id, produto_origem_id))
            return cursor.rowcount

    def atualizar_produto(self, produto_id: int, atualizacoes: Dict) -> None:
        """
        Atualiza informações de um produto.

        Args:
            produto_id: ID do produto
            atualizacoes: Dict com campos a atualizar
        """
        if not atualizacoes:
            return

        campos = ', '.join([f"{k} = %s" for k in atualizacoes.keys()])
        valores = list(atualizacoes.values())
        valores.append(produto_id)

        query = f"""
            UPDATE produtos_tabela
            SET {campos}
            WHERE id = %s
        """

        with self.db.get_cursor(dict_cursor=False) as cursor:
            cursor.execute(query, valores)

    def remover_produto(self, produto_id: int) -> None:
        """
        Remove um produto (após transferir seus preços).

        Args:
            produto_id: ID do produto a remover
        """
        query = "DELETE FROM produtos_tabela WHERE id = %s"

        with self.db.get_cursor(dict_cursor=False) as cursor:
            cursor.execute(query, (produto_id,))

    def mesclar_grupo(self, nome_normalizado: str, modo_automatico: bool = False) -> bool:
        """
        Mescla um grupo de produtos duplicados.

        Args:
            nome_normalizado: Nome normalizado do grupo
            modo_automatico: Se True, não pede confirmação

        Returns:
            True se mesclou com sucesso
        """
        produtos = self.obter_produtos_duplicados(nome_normalizado)

        if len(produtos) < 2:
            logger.warning(f"Grupo {nome_normalizado} não tem duplicatas suficientes")
            return False

        # Escolher produto principal
        produto_principal = self.escolher_produto_principal(produtos)
        produtos_secundarios = [p for p in produtos if p['id'] != produto_principal['id']]

        logger.info(f"\n{'='*60}")
        logger.info(f"Grupo: {nome_normalizado}")
        logger.info(f"Total de duplicatas: {len(produtos)}")
        logger.info(f"\nProduto PRINCIPAL (será mantido):")
        logger.info(f"  ID: {produto_principal['id']}")
        logger.info(f"  Nome: {produto_principal['nome']}")
        logger.info(f"  Marca: {produto_principal.get('marca', 'N/A')}")
        logger.info(f"  Preços: {produto_principal.get('total_precos', 0)}")
        logger.info(f"  Criado: {produto_principal['created_at']}")

        logger.info(f"\nProdutos SECUNDÁRIOS (serão mesclados):")
        for p in produtos_secundarios:
            logger.info(f"  - ID: {p['id']}, Nome: {p['nome']}, Preços: {p.get('total_precos', 0)}")

        if not modo_automatico:
            resposta = input("\nConfirmar mesclagem? (s/N): ")
            if resposta.lower() != 's':
                logger.info("Mesclagem cancelada pelo usuário")
                return False

        # Processar mesclagem
        try:
            total_precos_transferidos = 0

            for produto_secundario in produtos_secundarios:
                # Mesclar informações
                atualizacoes = self.mesclar_informacoes(produto_principal, produto_secundario)
                if atualizacoes:
                    self.atualizar_produto(produto_principal['id'], atualizacoes)
                    logger.info(f"  ✓ Informações atualizadas: {list(atualizacoes.keys())}")

                # Transferir preços
                precos_transferidos = self.transferir_precos(
                    produto_secundario['id'],
                    produto_principal['id']
                )
                total_precos_transferidos += precos_transferidos
                logger.info(f"  ✓ Transferidos {precos_transferidos} preços")

                # Remover produto secundário
                self.remover_produto(produto_secundario['id'])
                logger.info(f"  ✓ Produto ID {produto_secundario['id']} removido")

            # Atualizar estatísticas
            self.estatisticas['grupos_duplicados'] += 1
            self.estatisticas['produtos_mesclados'] += 1
            self.estatisticas['produtos_removidos'] += len(produtos_secundarios)
            self.estatisticas['precos_transferidos'] += total_precos_transferidos

            logger.info(f"\n✅ Mesclagem concluída com sucesso!")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao mesclar grupo: {e}")
            return False

    def mesclar_todos(self, modo_automatico: bool = False) -> None:
        """
        Mescla todos os grupos de duplicatas.

        Args:
            modo_automatico: Se True, não pede confirmação para cada grupo
        """
        duplicatas = self.detectar_duplicatas()

        if not duplicatas:
            logger.info("✓ Nenhuma duplicata encontrada!")
            return

        logger.info(f"Encontrados {len(duplicatas)} grupos de duplicatas")

        for idx, dup in enumerate(duplicatas, 1):
            logger.info(f"\n[{idx}/{len(duplicatas)}] Processando grupo: {dup['nome_normalizado']}")
            self.mesclar_grupo(dup['nome_normalizado'], modo_automatico)

        # Relatório final
        logger.info(f"\n{'='*60}")
        logger.info("RELATÓRIO FINAL")
        logger.info(f"{'='*60}")
        logger.info(f"Grupos processados: {self.estatisticas['grupos_duplicados']}")
        logger.info(f"Produtos principais mesclados: {self.estatisticas['produtos_mesclados']}")
        logger.info(f"Produtos secundários removidos: {self.estatisticas['produtos_removidos']}")
        logger.info(f"Preços transferidos: {self.estatisticas['precos_transferidos']}")


def main():
    """Função principal."""
    import argparse

    parser = argparse.ArgumentParser(description='Mesclar produtos duplicados')
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Modo automático (sem confirmações)'
    )
    parser.add_argument(
        '--apenas-listar',
        action='store_true',
        help='Apenas listar duplicatas sem mesclar'
    )
    args = parser.parse_args()

    # Conectar ao banco
    logger.info("Conectando ao banco de dados...")
    try:
        db_conn = criar_conexao_do_env()
        db_conn.connect()
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco: {e}")
        sys.exit(1)

    mesclador = MescladorDuplicatas(db_conn)

    if args.apenas_listar:
        # Apenas listar
        duplicatas = mesclador.detectar_duplicatas()
        if not duplicatas:
            logger.info("✓ Nenhuma duplicata encontrada!")
        else:
            logger.info(f"\n{'='*60}")
            logger.info(f"DUPLICATAS ENCONTRADAS: {len(duplicatas)} grupos")
            logger.info(f"{'='*60}\n")
            for idx, dup in enumerate(duplicatas, 1):
                logger.info(f"{idx}. {dup['nome_normalizado']}")
                logger.info(f"   Quantidade: {dup['quantidade_duplicatas']}")
                logger.info(f"   Nomes originais: {dup['nomes_originais']}")
                logger.info(f"   IDs: {dup['ids']}\n")
    else:
        # Mesclar
        mesclador.mesclar_todos(modo_automatico=args.auto)

    db_conn.close()
    logger.info("\n✅ Processo finalizado!")


if __name__ == "__main__":
    main()
