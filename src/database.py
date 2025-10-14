"""
Módulo de conexão e operações com PostgreSQL.
Gerencia todas as interações com o banco de dados.
"""

import os
import logging
from typing import Optional, Dict, List, Tuple, Any
from contextlib import contextmanager
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2 import sql

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Gerenciador de conexão com PostgreSQL."""

    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        port: int = 5432
    ):
        """
        Inicializa a conexão com o banco de dados.

        Args:
            host: Endereço do servidor PostgreSQL
            database: Nome do banco de dados
            user: Usuário do banco
            password: Senha do banco
            port: Porta do PostgreSQL (padrão: 5432)
        """
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.connection = None

    def connect(self) -> psycopg2.extensions.connection:
        """
        Estabelece conexão com o banco de dados.

        Returns:
            Objeto de conexão psycopg2

        Raises:
            psycopg2.Error: Se houver erro na conexão
        """
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            logger.info(f"Conectado ao banco: {self.database}@{self.host}")
            return self.connection
        except psycopg2.Error as e:
            logger.error(f"Erro ao conectar ao banco: {e}")
            raise

    def close(self):
        """Fecha a conexão com o banco de dados."""
        if self.connection:
            self.connection.close()
            logger.info("Conexão fechada")

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """
        Context manager para obter cursor do banco.

        Args:
            dict_cursor: Se True, retorna RealDictCursor (padrão: True)

        Yields:
            Cursor do banco de dados
        """
        if not self.connection or self.connection.closed:
            self.connect()

        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = self.connection.cursor(cursor_factory=cursor_factory)

        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Erro na transação: {e}")
            raise
        finally:
            cursor.close()


class PanfletoDatabase:
    """Operações de banco de dados para o sistema de panfletos."""

    def __init__(self, db_connection: DatabaseConnection):
        """
        Inicializa o gerenciador de operações.

        Args:
            db_connection: Instância de DatabaseConnection
        """
        self.db = db_connection

    def inicializar_schema(self, schema_path: str = "schema.sql"):
        """
        Executa o schema SQL para criar tabelas.

        Args:
            schema_path: Caminho para o arquivo schema.sql
        """
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()

            with self.db.get_cursor(dict_cursor=False) as cursor:
                cursor.execute(schema_sql)

            logger.info("Schema inicializado com sucesso")
        except FileNotFoundError:
            logger.warning(f"Arquivo {schema_path} não encontrado")
        except Exception as e:
            logger.error(f"Erro ao inicializar schema: {e}")
            raise

    def salvar_imagem_processada(
        self,
        nome_arquivo: str,
        caminho_arquivo: str,
        supermercado_nome: Optional[str] = None,
        data_panfleto: Optional[date] = None,
        status: str = "pendente",
        dados_json: Optional[Dict] = None,
        erro_mensagem: Optional[str] = None
    ) -> int:
        """
        Salva registro de imagem processada.

        Args:
            nome_arquivo: Nome do arquivo
            caminho_arquivo: Caminho completo do arquivo
            supermercado_nome: Nome do supermercado (opcional)
            data_panfleto: Data do panfleto (opcional)
            status: Status do processamento
            dados_json: JSON retornado pela LLM
            erro_mensagem: Mensagem de erro se houver

        Returns:
            ID da imagem salva
        """
        query = """
            INSERT INTO imagens_processadas (
                nome_arquivo, caminho_arquivo, supermercado_nome,
                data_panfleto, status, dados_json, erro_mensagem, processed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (
                nome_arquivo,
                caminho_arquivo,
                supermercado_nome,
                data_panfleto,
                status,
                Json(dados_json) if dados_json else None,
                erro_mensagem,
                datetime.now()
            ))
            result = cursor.fetchone()
            imagem_id = result['id']
            logger.info(f"Imagem salva com ID: {imagem_id}")
            return imagem_id

    def atualizar_imagem_processada(
        self,
        imagem_id: int,
        status: str,
        dados_json: Optional[Dict] = None,
        erro_mensagem: Optional[str] = None
    ):
        """
        Atualiza status de uma imagem processada.

        Args:
            imagem_id: ID da imagem
            status: Novo status
            dados_json: JSON atualizado
            erro_mensagem: Mensagem de erro
        """
        query = """
            UPDATE imagens_processadas
            SET status = %s, dados_json = %s, erro_mensagem = %s, processed_at = %s
            WHERE id = %s
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (
                status,
                Json(dados_json) if dados_json else None,
                erro_mensagem,
                datetime.now(),
                imagem_id
            ))
            logger.info(f"Imagem {imagem_id} atualizada: {status}")

    def buscar_categoria_por_nome(self, nome_categoria: str) -> Optional[Dict]:
        """
        Busca categoria por nome na tabela categorias.

        Args:
            nome_categoria: Nome da categoria

        Returns:
            Dict com dados da categoria ou None
        """
        if not nome_categoria or nome_categoria.strip() == '':
            return None

        query = """
            SELECT * FROM categorias
            WHERE LOWER(nome) = LOWER(%s)
            LIMIT 1
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (nome_categoria.strip(),))
            result = cursor.fetchone()
            return dict(result) if result else None

    def buscar_ou_criar_categoria(self, nome_categoria: str) -> Optional[int]:
        """
        Busca categoria existente ou retorna categoria 'Outros'.

        Args:
            nome_categoria: Nome da categoria vindo do LLM

        Returns:
            ID da categoria ou None
        """
        if not nome_categoria or nome_categoria.strip() == '':
            # Retorna categoria "Outros" como padrão
            categoria = self.buscar_categoria_por_nome('Outros')
            return categoria['id'] if categoria else None

        # Buscar categoria exata
        categoria = self.buscar_categoria_por_nome(nome_categoria)
        if categoria:
            return categoria['id']

        # Se não encontrar, retorna "Outros"
        categoria_outros = self.buscar_categoria_por_nome('Outros')
        if categoria_outros:
            logger.warning(f"Categoria '{nome_categoria}' não encontrada, usando 'Outros'")
            return categoria_outros['id']

        return None

    def buscar_produto_por_nome(self, nome: str, margem: float = 0.8) -> Optional[Dict]:
        """
        Busca produto por nome usando normalização.

        Args:
            nome: Nome do produto
            margem: Margem de similaridade (não usado)

        Returns:
            Dict com dados do produto ou None
        """
        query = """
            SELECT * FROM produtos_tabela
            WHERE nome_normalizado = normalizar_nome(%s)
            ORDER BY created_at DESC
            LIMIT 1
        """

        with self.db.get_cursor() as cursor:
            # Busca usando nome normalizado (previne duplicatas)
            cursor.execute(query, (nome,))
            result = cursor.fetchone()

            return dict(result) if result else None

    def criar_produto(
        self,
        nome: str,
        marca: Optional[str] = None,
        categoria: Optional[str] = None,
        categoria_id: Optional[int] = None,
        codigo_barras: Optional[str] = None,
        descricao: Optional[str] = None
    ) -> int:
        """
        Cria novo produto no banco.

        Args:
            nome: Nome do produto
            marca: Marca do produto
            categoria: Categoria (texto, mantido por compatibilidade)
            categoria_id: ID da categoria (foreign key para categorias)
            codigo_barras: Código de barras
            descricao: Descrição adicional

        Returns:
            ID do produto criado
        """
        query = """
            INSERT INTO produtos_tabela (nome, marca, categoria, categoria_id, codigo_barras, descricao)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (nome, marca, categoria, categoria_id, codigo_barras, descricao))
            result = cursor.fetchone()
            produto_id = result['id']
            logger.info(f"Produto criado: {nome} (ID: {produto_id}, Categoria ID: {categoria_id})")
            return produto_id

    def buscar_ou_criar_produto(
        self,
        nome: str,
        marca: Optional[str] = None,
        categoria: Optional[str] = None
    ) -> Tuple[int, bool]:
        """
        Busca produto existente ou cria novo com categoria_id.

        Args:
            nome: Nome do produto
            marca: Marca do produto
            categoria: Categoria (texto vindo do LLM)

        Returns:
            Tupla (produto_id, criado_novo)
        """
        produto = self.buscar_produto_por_nome(nome)

        if produto:
            return produto['id'], False

        # Resolver categoria_id a partir do nome da categoria
        categoria_id = None
        if categoria:
            categoria_id = self.buscar_ou_criar_categoria(categoria)

        produto_id = self.criar_produto(
            nome=nome,
            marca=marca,
            categoria=categoria,  # Mantém texto para compatibilidade
            categoria_id=categoria_id  # Adiciona foreign key
        )
        return produto_id, True

    def buscar_supermercado_por_nome(self, nome: str) -> Optional[Dict]:
        """
        Busca supermercado por nome.

        Args:
            nome: Nome do supermercado

        Returns:
            Dict com dados do supermercado ou None
        """
        query = """
            SELECT * FROM supermercados
            WHERE LOWER(nome) = LOWER(%s)
            LIMIT 1
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (nome,))
            result = cursor.fetchone()
            return dict(result) if result else None

    def criar_supermercado(
        self,
        nome: str,
        rede: Optional[str] = None,
        cidade: Optional[str] = None,
        estado: Optional[str] = None
    ) -> int:
        """
        Cria novo supermercado.

        Args:
            nome: Nome do supermercado
            rede: Rede do supermercado
            cidade: Cidade
            estado: Estado (sigla)

        Returns:
            ID do supermercado criado
        """
        query = """
            INSERT INTO supermercados (nome, rede, cidade, estado)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (nome, cidade, estado) DO UPDATE
            SET rede = EXCLUDED.rede
            RETURNING id
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (nome, rede, cidade, estado))
            result = cursor.fetchone()
            super_id = result['id']
            logger.info(f"Supermercado: {nome} (ID: {super_id})")
            return super_id

    def buscar_ou_criar_supermercado(self, nome: str) -> Tuple[int, bool]:
        """
        Busca supermercado existente ou cria novo.

        Args:
            nome: Nome do supermercado

        Returns:
            Tupla (supermercado_id, criado_novo)
        """
        supermercado = self.buscar_supermercado_por_nome(nome)

        if supermercado:
            return supermercado['id'], False

        super_id = self.criar_supermercado(nome)
        return super_id, True

    def salvar_preco(
        self,
        produto_id: int,
        supermercado_id: int,
        imagem_id: int,
        preco: float,
        preco_original: Optional[float] = None,
        em_promocao: bool = False,
        validade_inicio: Optional[date] = None,
        validade_fim: Optional[date] = None,
        unidade: Optional[str] = None,
        descricao_adicional: Optional[str] = None,
        confianca: Optional[float] = None
    ) -> int:
        """
        Salva preço de produto.

        Args:
            produto_id: ID do produto
            supermercado_id: ID do supermercado
            imagem_id: ID da imagem processada
            preco: Preço do produto
            preco_original: Preço original (antes da promoção)
            em_promocao: Se está em promoção
            validade_inicio: Data de início da validade
            validade_fim: Data de fim da validade
            unidade: Unidade de medida
            descricao_adicional: Descrição adicional
            confianca: Nível de confiança (0-1)

        Returns:
            ID do preço salvo
        """
        query = """
            INSERT INTO precos_panfleto (
                produto_id, supermercado_id, imagem_id, preco, preco_original,
                em_promocao, validade_inicio, validade_fim, unidade,
                descricao_adicional, confianca
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (
                produto_id, supermercado_id, imagem_id, preco, preco_original,
                em_promocao, validade_inicio, validade_fim, unidade,
                descricao_adicional, confianca
            ))
            result = cursor.fetchone()
            preco_id = result['id']
            return preco_id

    def salvar_panfleto_completo(
        self,
        nome_arquivo: str,
        caminho_arquivo: str,
        dados_json: Dict
    ) -> Dict[str, Any]:
        """
        Salva todos os dados de um panfleto processado.

        Args:
            nome_arquivo: Nome do arquivo da imagem
            caminho_arquivo: Caminho completo
            dados_json: JSON retornado pela LLM

        Returns:
            Dict com estatísticas do processamento
        """
        try:
            # Extrair dados do JSON
            supermercado_nome = dados_json.get('supermercado')
            data_inicio = dados_json.get('data_validade_inicio')
            data_fim = dados_json.get('data_validade_fim')
            produtos = dados_json.get('produtos', [])

            # Converter datas
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date() if data_inicio else None
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date() if data_fim else None

            # Salvar imagem processada
            imagem_id = self.salvar_imagem_processada(
                nome_arquivo=nome_arquivo,
                caminho_arquivo=caminho_arquivo,
                supermercado_nome=supermercado_nome,
                data_panfleto=data_inicio,
                status='processado',
                dados_json=dados_json
            )

            # Buscar ou criar supermercado
            if supermercado_nome:
                supermercado_id, super_novo = self.buscar_ou_criar_supermercado(supermercado_nome)
            else:
                supermercado_id, super_novo = self.buscar_ou_criar_supermercado("Desconhecido")

            # Estatísticas
            stats = {
                'imagem_id': imagem_id,
                'supermercado_id': supermercado_id,
                'total_produtos': len(produtos),
                'produtos_novos': 0,
                'produtos_existentes': 0,
                'precos_salvos': 0,
                'erros': []
            }

            # Processar cada produto
            for idx, produto_data in enumerate(produtos):
                try:
                    nome = produto_data.get('nome')
                    if not nome:
                        stats['erros'].append(f"Produto {idx+1}: nome vazio")
                        continue

                    marca = produto_data.get('marca')
                    categoria = produto_data.get('categoria')
                    preco = produto_data.get('preco')
                    preco_original = produto_data.get('preco_original')
                    em_promocao = produto_data.get('em_promocao', False)
                    unidade = produto_data.get('unidade')
                    descricao = produto_data.get('descricao_adicional')
                    confianca = produto_data.get('confianca')

                    # Validar preço
                    if preco is None or preco < 0:
                        stats['erros'].append(f"Produto {nome}: preço inválido")
                        continue

                    # Buscar ou criar produto
                    produto_id, produto_novo = self.buscar_ou_criar_produto(
                        nome=nome,
                        marca=marca,
                        categoria=categoria
                    )

                    if produto_novo:
                        stats['produtos_novos'] += 1
                    else:
                        stats['produtos_existentes'] += 1

                    # Salvar preço
                    preco_id = self.salvar_preco(
                        produto_id=produto_id,
                        supermercado_id=supermercado_id,
                        imagem_id=imagem_id,
                        preco=float(preco),
                        preco_original=float(preco_original) if preco_original else None,
                        em_promocao=em_promocao,
                        validade_inicio=data_inicio,
                        validade_fim=data_fim,
                        unidade=unidade,
                        descricao_adicional=descricao,
                        confianca=float(confianca) if confianca else None
                    )

                    stats['precos_salvos'] += 1

                except Exception as e:
                    erro_msg = f"Erro ao processar produto {idx+1}: {str(e)}"
                    stats['erros'].append(erro_msg)
                    logger.error(erro_msg)

            return stats

        except Exception as e:
            logger.error(f"Erro ao salvar panfleto completo: {e}")
            # Tentar atualizar status da imagem
            try:
                if 'imagem_id' in locals():
                    self.atualizar_imagem_processada(
                        imagem_id=imagem_id,
                        status='erro',
                        erro_mensagem=str(e)
                    )
            except:
                pass
            raise

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas gerais do banco.

        Returns:
            Dict com estatísticas
        """
        stats = {}

        with self.db.get_cursor() as cursor:
            # Total de produtos
            cursor.execute("SELECT COUNT(*) as total FROM produtos_tabela")
            stats['total_produtos'] = cursor.fetchone()['total']

            # Total de supermercados
            cursor.execute("SELECT COUNT(*) as total FROM supermercados")
            stats['total_supermercados'] = cursor.fetchone()['total']

            # Total de preços
            cursor.execute("SELECT COUNT(*) as total FROM precos_panfleto")
            stats['total_precos'] = cursor.fetchone()['total']

            # Total de imagens
            cursor.execute("SELECT COUNT(*) as total FROM imagens_processadas")
            stats['total_imagens'] = cursor.fetchone()['total']

            # Preço médio
            cursor.execute("SELECT AVG(preco) as media FROM precos_panfleto")
            result = cursor.fetchone()
            stats['preco_medio'] = float(result['media']) if result['media'] else 0

            # Produtos em promoção
            cursor.execute(
                "SELECT COUNT(*) as total FROM precos_panfleto WHERE em_promocao = TRUE"
            )
            stats['total_promocoes'] = cursor.fetchone()['total']

        return stats


def criar_conexao_do_env() -> DatabaseConnection:
    """
    Cria conexão a partir das variáveis de ambiente.

    Returns:
        Instância de DatabaseConnection

    Raises:
        ValueError: Se variáveis obrigatórias não estiverem definidas
    """
    host = os.getenv('DB_HOST')
    database = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASS')
    port = int(os.getenv('DB_PORT', '5432'))

    if not all([host, database, user, password]):
        raise ValueError(
            "Variáveis de ambiente obrigatórias não definidas: "
            "DB_HOST, DB_NAME, DB_USER, DB_PASS"
        )

    return DatabaseConnection(host, database, user, password, port)
