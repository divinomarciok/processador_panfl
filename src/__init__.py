"""
Sistema de Extração e Análise de Preços de Panfletos de Supermercado.

Módulos principais:
- database: Gerenciamento de conexão e operações com PostgreSQL
- panfleto_processor: Processamento de imagens com LLMs
"""

__version__ = "1.0.0"
__author__ = "Sistema de Análise de Preços"

from .database import DatabaseConnection, PanfletoDatabase, criar_conexao_do_env
from .panfleto_processor import processar_panfleto

__all__ = ["DatabaseConnection", "PanfletoDatabase", "criar_conexao_do_env", "processar_panfleto"]
