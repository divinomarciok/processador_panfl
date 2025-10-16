#!/usr/bin/env python3
"""
Script CORRETO para lidar com duplicatas.

Este script MESCLA produtos duplicados (ao invés de criar aliases bidirecionais).

IMPORTANTE:
- Aliases bidirecionais mantêm produtos duplicados no banco (ERRADO)
- Mesclagem remove duplicatas e cria apenas 1 alias (CORRETO)

Uso:
    python scripts/popular_aliases_CORRETO.py                    # Modo interativo
    python scripts/popular_aliases_CORRETO.py --auto             # Modo automático
    python scripts/popular_aliases_CORRETO.py --relatorio        # Apenas relatório
"""

import os
import sys
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.database import DatabaseConnection, criar_conexao_do_env

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GerenciadorDuplicatas:
    """Gerenciador de duplicatas - MESCLA produtos ao invés de criar aliases bidirecionais."""

    def __init__(self, db_connection: DatabaseConnection):
        """
        Inicializa gerenciador.

        Args:
            db_connection: Conexão com banco de dados
        """
        self.db = db_connection

    def obter_duplicatas_potenciais(
        self,
        limite: int = 100,
        similaridade_minima: float = 0.80
    ) -> List[Dict]:
        """
        Obtém lista de duplicatas potenciais.

        Args:
            limite: Número máximo de duplicatas a retornar
            similaridade_minima: Similaridade mínima (0-1)

        Returns:
            Lista de dicts com duplicatas
        """
        query = """
            SELECT
                produto1_id,
                produto1_nome,
                produto1_marca,
                produto2_id,
                produto2_nome,
                produto2_marca,
                similaridade,
                distancia
            FROM vw_duplicatas_potenciais
            WHERE similaridade >= %s
            ORDER BY similaridade DESC
            LIMIT %s
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (similaridade_minima, limite))
            return [dict(row) for row in cursor.fetchall()]

    def mesclar_produtos(
        self,
        produto_manter: int,
        produto_deletar: int,
        nome_alias: str
    ) -> bool:
        """
        Mescla produto_deletar em produto_manter e cria 1 alias.

        Args:
            produto_manter: ID do produto que será mantido
            produto_deletar: ID do produto que será deletado
            nome_alias: Nome do produto deletado (será o alias)

        Returns:
            True se mesclado com sucesso
        """
        try:
            with self.db.get_cursor() as cursor:
                # 1. Atualizar preços
                cursor.execute("""
                    UPDATE precos_panfleto
                    SET produto_id = %s
                    WHERE produto_id = %s
                """, (produto_manter, produto_deletar))
                precos_atualizados = cursor.rowcount

                # 2. Deletar aliases do produto que será removido
                cursor.execute("""
                    DELETE FROM produtos_aliases
                    WHERE produto_id = %s
                """, (produto_deletar,))
                aliases_deletados = cursor.rowcount

                # 3. Criar alias no produto mantido (se não existir)
                cursor.execute("""
                    INSERT INTO produtos_aliases (
                        produto_id, alias, origem, confianca, created_by
                    )
                    VALUES (%s, %s, 'auto', 1.0, 'script')
                    ON CONFLICT (alias_normalizado, produto_id) DO NOTHING
                """, (produto_manter, nome_alias))
                alias_criado = cursor.rowcount > 0

                # 4. Deletar produto
                cursor.execute("""
                    DELETE FROM produtos_tabela
                    WHERE id = %s
                """, (produto_deletar,))

            logger.info(f"✓ Mesclado: Produto {produto_deletar} → Produto {produto_manter}")
            logger.info(f"  - {precos_atualizados} preços atualizados")
            logger.info(f"  - {aliases_deletados} aliases removidos do produto deletado")
            logger.info(f"  - Alias '{nome_alias}' {'criado' if alias_criado else 'já existia'}")
            logger.info(f"  - Produto {produto_deletar} removido")

            return True

        except Exception as e:
            logger.error(f"Erro ao mesclar produtos: {e}")
            return False

    def processar_duplicatas_automatico(
        self,
        limite: int = 100,
        similaridade_minima: float = 0.95
    ) -> Dict[str, int]:
        """
        Processa duplicatas automaticamente (altíssima confiança, ≥95%).

        Args:
            limite: Número máximo de duplicatas a processar
            similaridade_minima: Similaridade mínima (padrão: 0.95)

        Returns:
            Dict com estatísticas
        """
        logger.info(f"Iniciando processamento automático (similaridade >= {similaridade_minima:.0%})")

        duplicatas = self.obter_duplicatas_potenciais(
            limite=limite,
            similaridade_minima=similaridade_minima
        )

        stats = {
            'total_duplicatas': len(duplicatas),
            'produtos_mesclados': 0,
            'erros': 0
        }

        for idx, dup in enumerate(duplicatas, 1):
            logger.info(f"\n[{idx}/{len(duplicatas)}] Processando:")
            logger.info(f"  Produto 1: {dup['produto1_nome']} (ID: {dup['produto1_id']})")
            logger.info(f"  Produto 2: {dup['produto2_nome']} (ID: {dup['produto2_id']})")
            logger.info(f"  Similaridade: {dup['similaridade']:.1%}")

            try:
                # Mesclar produto2 em produto1, mantendo nome do produto2 como alias
                sucesso = self.mesclar_produtos(
                    produto_manter=dup['produto1_id'],
                    produto_deletar=dup['produto2_id'],
                    nome_alias=dup['produto2_nome']
                )

                if sucesso:
                    stats['produtos_mesclados'] += 1

            except Exception as e:
                logger.error(f"Erro ao processar duplicata: {e}")
                stats['erros'] += 1

        return stats

    def processar_duplicatas_interativo(
        self,
        limite: int = 50,
        similaridade_minima: float = 0.80
    ) -> Dict[str, int]:
        """
        Processa duplicatas em modo interativo (com confirmação manual).

        Args:
            limite: Número máximo de duplicatas a processar
            similaridade_minima: Similaridade mínima

        Returns:
            Dict com estatísticas
        """
        logger.info(f"Modo interativo (similaridade >= {similaridade_minima:.0%})")

        duplicatas = self.obter_duplicatas_potenciais(
            limite=limite,
            similaridade_minima=similaridade_minima
        )

        if not duplicatas:
            print("\n✓ Nenhuma duplicata encontrada!\n")
            return {
                'total_duplicatas': 0,
                'produtos_mesclados': 0,
                'ignorados': 0,
                'erros': 0
            }

        stats = {
            'total_duplicatas': len(duplicatas),
            'produtos_mesclados': 0,
            'ignorados': 0,
            'erros': 0
        }

        for idx, dup in enumerate(duplicatas, 1):
            print(f"\n{'='*80}")
            print(f"Duplicata {idx}/{len(duplicatas)}")
            print(f"{'='*80}")
            print(f"Produto 1: {dup['produto1_nome']}")
            print(f"           ID: {dup['produto1_id']}")
            print(f"           Marca: {dup['produto1_marca'] or 'N/A'}")
            print()
            print(f"Produto 2: {dup['produto2_nome']}")
            print(f"           ID: {dup['produto2_id']}")
            print(f"           Marca: {dup['produto2_marca'] or 'N/A'}")
            print()
            print(f"Similaridade: {dup['similaridade']:.1%} (distância Levenshtein: {dup['distancia']})")
            print()
            print("AÇÃO: Mesclar produto 2 em produto 1?")
            print("  - Produto 1 será mantido")
            print("  - Produto 2 será deletado")
            print(f"  - Alias '{dup['produto2_nome']}' será criado para produto 1")
            print()

            resposta = input("Mesclar? [s/N/q(sair)]: ").lower().strip()

            if resposta == 'q':
                logger.info("Interrompido pelo usuário")
                break
            elif resposta == 's':
                try:
                    sucesso = self.mesclar_produtos(
                        produto_manter=dup['produto1_id'],
                        produto_deletar=dup['produto2_id'],
                        nome_alias=dup['produto2_nome']
                    )

                    if sucesso:
                        stats['produtos_mesclados'] += 1
                        print("✅ Produtos mesclados com sucesso!")
                    else:
                        stats['erros'] += 1
                        print("❌ Erro ao mesclar produtos")

                except Exception as e:
                    logger.error(f"Erro ao mesclar produtos: {e}")
                    stats['erros'] += 1
                    print(f"❌ Erro: {e}")
            else:
                stats['ignorados'] += 1
                print("⊘ Ignorado")

        return stats

    def gerar_relatorio(self) -> Dict[str, any]:
        """
        Gera relatório completo sobre aliases e duplicatas.

        Returns:
            Dict com estatísticas
        """
        stats = {}

        with self.db.get_cursor() as cursor:
            # Total de produtos
            cursor.execute("SELECT COUNT(*) as total FROM produtos_tabela")
            stats['total_produtos'] = cursor.fetchone()['total']

            # Total de aliases
            cursor.execute("SELECT COUNT(*) as total FROM produtos_aliases")
            stats['total_aliases'] = cursor.fetchone()['total']

            # Aliases por origem
            cursor.execute("""
                SELECT origem, COUNT(*) as quantidade
                FROM produtos_aliases
                GROUP BY origem
                ORDER BY quantidade DESC
            """)
            stats['aliases_por_origem'] = [dict(row) for row in cursor.fetchall()]

            # Produtos com mais aliases
            cursor.execute("""
                SELECT
                    p.id,
                    p.nome,
                    COUNT(pa.id) as total_aliases
                FROM produtos_tabela p
                INNER JOIN produtos_aliases pa ON p.id = pa.produto_id
                GROUP BY p.id, p.nome
                ORDER BY total_aliases DESC
                LIMIT 10
            """)
            stats['produtos_mais_aliases'] = [dict(row) for row in cursor.fetchall()]

            # Duplicatas potenciais restantes
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM vw_duplicatas_potenciais
                WHERE similaridade >= 0.80
            """)
            stats['duplicatas_potenciais'] = cursor.fetchone()['total']

        return stats

    def imprimir_relatorio(self):
        """Imprime relatório formatado."""
        stats = self.gerar_relatorio()

        print("\n" + "="*80)
        print("RELATÓRIO DE ALIASES E DUPLICATAS")
        print("="*80)
        print(f"Total de produtos: {stats['total_produtos']}")
        print(f"Total de aliases: {stats['total_aliases']}")
        print(f"Duplicatas potenciais (≥80%): {stats['duplicatas_potenciais']}")
        print()

        if stats['aliases_por_origem']:
            print("Aliases por origem:")
            for item in stats['aliases_por_origem']:
                print(f"  - {item['origem']}: {item['quantidade']}")
            print()

        if stats['produtos_mais_aliases']:
            print("Produtos com mais aliases:")
            for item in stats['produtos_mais_aliases'][:5]:
                print(f"  - {item['nome']}: {item['total_aliases']} aliases")
        print("="*80 + "\n")


def main():
    """Função principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Gerenciar duplicatas (MESCLA produtos ao invés de criar aliases bidirecionais)'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Modo automático (apenas altíssima confiança, ≥95%%)'
    )
    parser.add_argument(
        '--relatorio',
        action='store_true',
        help='Apenas gerar relatório'
    )
    parser.add_argument(
        '--limite',
        type=int,
        default=100,
        help='Número máximo de duplicatas a processar (padrão: 100)'
    )
    parser.add_argument(
        '--similaridade',
        type=float,
        default=0.85,
        help='Similaridade mínima (0-1, padrão: 0.85)'
    )

    args = parser.parse_args()

    # Carregar variáveis de ambiente
    load_dotenv()

    # Conectar ao banco
    try:
        db = criar_conexao_do_env()
        db.connect()
        logger.info("Conectado ao banco de dados")
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco: {e}")
        return 1

    # Criar gerenciador
    gerenciador = GerenciadorDuplicatas(db)

    # Modo relatório
    if args.relatorio:
        gerenciador.imprimir_relatorio()
        return 0

    # Modo automático
    if args.auto:
        print("\n" + "="*80)
        print("⚠ MODO AUTOMÁTICO")
        print("="*80)
        print("Isso vai MESCLAR produtos com similaridade ≥95%")
        print("Produtos duplicados serão DELETADOS permanentemente")
        print("="*80 + "\n")

        resposta = input("Continuar? (s/n): ").lower().strip()
        if resposta != 's':
            print("Cancelado.")
            return 0

        logger.info("Modo AUTOMÁTICO ativado")
        stats = gerenciador.processar_duplicatas_automatico(
            limite=args.limite,
            similaridade_minima=max(args.similaridade, 0.95)  # Mínimo 95% no automático
        )

        print("\n" + "="*80)
        print("RESULTADO DO PROCESSAMENTO AUTOMÁTICO")
        print("="*80)
        print(f"Duplicatas analisadas: {stats['total_duplicatas']}")
        print(f"Produtos mesclados: {stats['produtos_mesclados']}")
        print(f"Erros: {stats['erros']}")
        print("="*80 + "\n")

    # Modo interativo
    else:
        logger.info("Modo INTERATIVO ativado")
        stats = gerenciador.processar_duplicatas_interativo(
            limite=args.limite,
            similaridade_minima=args.similaridade
        )

        print("\n" + "="*80)
        print("RESULTADO DO PROCESSAMENTO INTERATIVO")
        print("="*80)
        print(f"Duplicatas analisadas: {stats['total_duplicatas']}")
        print(f"Produtos mesclados: {stats['produtos_mesclados']}")
        print(f"Ignorados: {stats['ignorados']}")
        print(f"Erros: {stats['erros']}")
        print("="*80 + "\n")

    # Relatório final
    if not args.relatorio:
        gerenciador.imprimir_relatorio()

    # Fechar conexão
    db.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
