"""
Script para Aplicar Migrations SQL.

Executa arquivo SQL de migration no banco de dados.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Carregar variáveis de ambiente
load_dotenv()

from src.database import criar_conexao_do_env
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def aplicar_migration(db_conn, migration_path: str) -> bool:
    """
    Aplica migration SQL no banco de dados.

    Args:
        db_conn: Conexão com o banco
        migration_path: Caminho para o arquivo SQL

    Returns:
        True se aplicou com sucesso
    """
    try:
        # Ler arquivo SQL
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql = f.read()

        logger.info(f"Aplicando migration: {migration_path}")
        logger.info(f"Tamanho do arquivo: {len(sql)} bytes")

        # Executar SQL
        with db_conn.get_cursor(dict_cursor=False) as cursor:
            cursor.execute(sql)

        logger.info("✅ Migration aplicada com sucesso!")
        return True

    except FileNotFoundError:
        logger.error(f"❌ Arquivo não encontrado: {migration_path}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar migration: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal."""
    import argparse

    parser = argparse.ArgumentParser(description='Aplicar migration SQL')
    parser.add_argument(
        'migration_file',
        help='Caminho para o arquivo de migration SQL'
    )
    args = parser.parse_args()

    # Conectar ao banco
    logger.info("Conectando ao banco de dados...")
    try:
        db_conn = criar_conexao_do_env()
        db_conn.connect()
        logger.info("✓ Conectado ao banco")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
        sys.exit(1)

    # Aplicar migration
    sucesso = aplicar_migration(db_conn, args.migration_file)

    # Fechar conexão
    db_conn.close()

    if sucesso:
        logger.info("\n✅ Processo finalizado com sucesso!")
        sys.exit(0)
    else:
        logger.error("\n❌ Falha ao aplicar migration")
        sys.exit(1)


if __name__ == "__main__":
    main()
