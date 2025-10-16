#!/usr/bin/env python3
"""
Script para popular tabela de aliases automaticamente.

Este script:
1. Identifica duplicatas potenciais no banco
2. Cria aliases automaticamente para produtos similares
3. Permite revisão manual dos aliases criados

Uso:
    python scripts/popular_aliases.py                    # Modo interativo
    python scripts/popular_aliases.py --auto             # Modo automático (alta confiança)
    python scripts/popular_aliases.py --relatorio        # Apenas gerar relatório
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


class GerenciadorAliases:
    """Gerenciador de aliases para produtos."""

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
                produto2_id,
                produto2_nome,
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

    def verificar_alias_existe(
        self,
        produto_id: int,
        alias: str
    ) -> bool:
        """
        Verifica se alias já existe para o produto.

        Args:
            produto_id: ID do produto
            alias: Nome do alias

        Returns:
            True se já existe
        """
        query = """
            SELECT COUNT(*) as total
            FROM produtos_aliases
            WHERE produto_id = %s
              AND alias_normalizado = normalizar_nome(%s)
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (produto_id, alias))
            result = cursor.fetchone()
            return result['total'] > 0

    def adicionar_alias(
        self,
        produto_id: int,
        alias: str,
        origem: str = 'auto',
        confianca: float = 0.9,
        created_by: str = 'script'
    ) -> bool:
        """
        Adiciona alias para um produto.

        Args:
            produto_id: ID do produto principal
            alias: Nome do alias
            origem: Origem do alias (auto, manual, llm)
            confianca: Nível de confiança (0-1)
            created_by: Quem criou o alias

        Returns:
            True se adicionado com sucesso
        """
        # Verificar se já existe
        if self.verificar_alias_existe(produto_id, alias):
            logger.debug(f"Alias '{alias}' já existe para produto {produto_id}")
            return False

        query = """
            INSERT INTO produtos_aliases (
                produto_id, alias, origem, confianca, created_by
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (alias_normalizado, produto_id) DO NOTHING
        """

        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (
                    produto_id, alias, origem, confianca, created_by
                ))

                if cursor.rowcount > 0:
                    logger.info(f"✓ Alias criado: '{alias}' → Produto ID {produto_id}")
                    return True
                else:
                    logger.debug(f"Alias '{alias}' não foi inserido (duplicata)")
                    return False

        except Exception as e:
            logger.error(f"Erro ao adicionar alias: {e}")
            return False

    def criar_aliases_bidirecionais(
        self,
        produto1_id: int,
        produto1_nome: str,
        produto2_id: int,
        produto2_nome: str,
        similaridade: float
    ) -> Tuple[bool, bool]:
        """
        Cria aliases bidirecionais entre dois produtos.

        Args:
            produto1_id: ID do primeiro produto
            produto1_nome: Nome do primeiro produto
            produto2_id: ID do segundo produto
            produto2_nome: Nome do segundo produto
            similaridade: Similaridade entre os produtos

        Returns:
            Tupla (alias1_criado, alias2_criado)
        """
        # Determinar confiança baseada na similaridade
        if similaridade >= 0.95:
            confianca = 1.0
            origem = 'auto'
        elif similaridade >= 0.90:
            confianca = 0.95
            origem = 'auto'
        elif similaridade >= 0.85:
            confianca = 0.90
            origem = 'auto'
        else:
            confianca = 0.80
            origem = 'semi-auto'

        # Produto1 → usar nome de Produto2 como alias
        alias1 = self.adicionar_alias(
            produto_id=produto1_id,
            alias=produto2_nome,
            origem=origem,
            confianca=confianca
        )

        # Produto2 → usar nome de Produto1 como alias
        alias2 = self.adicionar_alias(
            produto_id=produto2_id,
            alias=produto1_nome,
            origem=origem,
            confianca=confianca
        )

        return alias1, alias2

    def processar_duplicatas_automatico(
        self,
        limite: int = 100,
        similaridade_minima: float = 0.90
    ) -> Dict[str, int]:
        """
        Processa duplicatas automaticamente (alta confiança).

        Args:
            limite: Número máximo de duplicatas a processar
            similaridade_minima: Similaridade mínima para processar automaticamente

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
            'aliases_criados': 0,
            'aliases_existentes': 0,
            'erros': 0
        }

        for idx, dup in enumerate(duplicatas, 1):
            logger.info(f"\n[{idx}/{len(duplicatas)}] Processando:")
            logger.info(f"  Produto 1: {dup['produto1_nome']} (ID: {dup['produto1_id']})")
            logger.info(f"  Produto 2: {dup['produto2_nome']} (ID: {dup['produto2_id']})")
            logger.info(f"  Similaridade: {dup['similaridade']:.1%}")

            try:
                alias1, alias2 = self.criar_aliases_bidirecionais(
                    produto1_id=dup['produto1_id'],
                    produto1_nome=dup['produto1_nome'],
                    produto2_id=dup['produto2_id'],
                    produto2_nome=dup['produto2_nome'],
                    similaridade=dup['similaridade']
                )

                if alias1:
                    stats['aliases_criados'] += 1
                else:
                    stats['aliases_existentes'] += 1

                if alias2:
                    stats['aliases_criados'] += 1
                else:
                    stats['aliases_existentes'] += 1

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

        stats = {
            'total_duplicatas': len(duplicatas),
            'aliases_criados': 0,
            'aliases_ignorados': 0,
            'erros': 0
        }

        for idx, dup in enumerate(duplicatas, 1):
            print(f"\n{'='*70}")
            print(f"Duplicata {idx}/{len(duplicatas)}")
            print(f"{'='*70}")
            print(f"Produto 1: {dup['produto1_nome']} (ID: {dup['produto1_id']})")
            print(f"Produto 2: {dup['produto2_nome']} (ID: {dup['produto2_id']})")
            print(f"Similaridade: {dup['similaridade']:.1%} (distância: {dup['distancia']})")
            print()

            resposta = input("Criar aliases bidirecionais? [s/N/q(sair)]: ").lower().strip()

            if resposta == 'q':
                logger.info("Interrompido pelo usuário")
                break
            elif resposta == 's':
                try:
                    alias1, alias2 = self.criar_aliases_bidirecionais(
                        produto1_id=dup['produto1_id'],
                        produto1_nome=dup['produto1_nome'],
                        produto2_id=dup['produto2_id'],
                        produto2_nome=dup['produto2_nome'],
                        similaridade=dup['similaridade']
                    )

                    if alias1 or alias2:
                        stats['aliases_criados'] += (1 if alias1 else 0) + (1 if alias2 else 0)
                        print("✓ Aliases criados com sucesso!")
                    else:
                        print("ℹ Aliases já existiam")

                except Exception as e:
                    logger.error(f"Erro ao criar aliases: {e}")
                    stats['erros'] += 1
            else:
                stats['aliases_ignorados'] += 1
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

        print("\n" + "="*70)
        print("RELATÓRIO DE ALIASES E DUPLICATAS")
        print("="*70)
        print(f"Total de produtos: {stats['total_produtos']}")
        print(f"Total de aliases: {stats['total_aliases']}")
        print(f"Duplicatas potenciais (≥80%): {stats['duplicatas_potenciais']}")
        print()

        print("Aliases por origem:")
        for item in stats['aliases_por_origem']:
            print(f"  - {item['origem']}: {item['quantidade']}")
        print()

        if stats['produtos_mais_aliases']:
            print("Produtos com mais aliases:")
            for item in stats['produtos_mais_aliases'][:5]:
                print(f"  - {item['nome']}: {item['total_aliases']} aliases")
        print("="*70 + "\n")


def main():
    """Função principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Popular tabela de aliases automaticamente'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Modo automático (apenas alta confiança, ≥90%%)'
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
        default=0.80,
        help='Similaridade mínima (0-1, padrão: 0.80)'
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
    gerenciador = GerenciadorAliases(db)

    # Modo relatório
    if args.relatorio:
        gerenciador.imprimir_relatorio()
        return 0

    # Modo automático
    if args.auto:
        logger.info("Modo AUTOMÁTICO ativado")
        stats = gerenciador.processar_duplicatas_automatico(
            limite=args.limite,
            similaridade_minima=max(args.similaridade, 0.90)  # Mínimo 90% no automático
        )

        print("\n" + "="*70)
        print("RESULTADO DO PROCESSAMENTO AUTOMÁTICO")
        print("="*70)
        print(f"Duplicatas analisadas: {stats['total_duplicatas']}")
        print(f"Aliases criados: {stats['aliases_criados']}")
        print(f"Aliases já existentes: {stats['aliases_existentes']}")
        print(f"Erros: {stats['erros']}")
        print("="*70 + "\n")

    # Modo interativo
    else:
        logger.info("Modo INTERATIVO ativado")
        stats = gerenciador.processar_duplicatas_interativo(
            limite=args.limite,
            similaridade_minima=args.similaridade
        )

        print("\n" + "="*70)
        print("RESULTADO DO PROCESSAMENTO INTERATIVO")
        print("="*70)
        print(f"Duplicatas analisadas: {stats['total_duplicatas']}")
        print(f"Aliases criados: {stats['aliases_criados']}")
        print(f"Aliases ignorados: {stats['aliases_ignorados']}")
        print(f"Erros: {stats['erros']}")
        print("="*70 + "\n")

    # Relatório final
    gerenciador.imprimir_relatorio()

    # Fechar conexão
    db.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
