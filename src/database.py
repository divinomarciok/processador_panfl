"""
Módulo de conexão e operações com PostgreSQL.
Gerencia todas as interações com o banco de dados.
"""

import os
import re
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


# Mapeamento inteligente de categorias
# Mapeia categorias que o LLM pode retornar para as categorias do banco
MAPEAMENTO_CATEGORIAS = {
    # Bebidas
    'bebidas em pó': 'Bebidas',
    'bebidas em po': 'Bebidas',
    'refrigerantes': 'Bebidas',
    'sucos': 'Bebidas',
    'água': 'Bebidas',
    'agua': 'Bebidas',

    # Bebidas Alcoólicas
    'bebidas alcoolicas': 'Bebidas Alcoólicas',
    'bebidas alcoólicas': 'Bebidas Alcoólicas',
    'cervejas': 'Bebidas Alcoólicas',
    'vinhos': 'Bebidas Alcoólicas',
    'destilados': 'Bebidas Alcoólicas',

    # Carnes
    'carne bovina': 'Carnes',
    'carne suína': 'Carnes',
    'carne suina': 'Carnes',
    'aves': 'Carnes',
    'frango': 'Carnes',
    'peixes': 'Carnes',
    'pescados': 'Carnes',
    'açougue': 'Carnes',
    'acougue': 'Carnes',

    # Frios e Laticínios
    'laticinios': 'Frios e Laticínios',
    'laticínios': 'Frios e Laticínios',
    'queijos': 'Frios e Laticínios',
    'frios': 'Frios e Laticínios',
    'iogurtes': 'Frios e Laticínios',
    'leite': 'Frios e Laticínios',

    # Frutas
    'frutas frescas': 'Frutas',
    'hortifruti': 'Frutas',

    # Verduras e Legumes
    'verduras': 'Verduras e Legumes',
    'legumes': 'Verduras e Legumes',
    'hortaliças': 'Verduras e Legumes',
    'hortalicas': 'Verduras e Legumes',
    'temperos frescos': 'Verduras e Legumes',

    # Mercearia
    'mercearia seca': 'Mercearia',
    'grãos': 'Mercearia',
    'graos': 'Mercearia',
    'arroz': 'Mercearia',
    'feijão': 'Mercearia',
    'feijao': 'Mercearia',
    'macarrão': 'Mercearia',
    'macarrao': 'Mercearia',
    'massas': 'Mercearia',
    'óleos': 'Mercearia',
    'oleos': 'Mercearia',
    'ingredientes': 'Mercearia',
    'ingredientes para confeitaria': 'Mercearia',

    # Panificação
    'pães': 'Panificação',
    'paes': 'Panificação',
    'padaria': 'Panificação',
    'bolos': 'Panificação',

    # Doces e Sobremesas
    'doces': 'Doces e Sobremesas',
    'chocolates': 'Doces e Sobremesas',
    'balas': 'Doces e Sobremesas',
    'sobremesas': 'Doces e Sobremesas',
    'guloseimas': 'Doces e Sobremesas',

    # Molhos e Temperos
    'molhos': 'Molhos e Temperos',
    'condimentos': 'Molhos e Temperos',
    'temperos': 'Molhos e Temperos',
    'temperos secos': 'Molhos e Temperos',

    # Higiene Pessoal
    'higiene': 'Higiene Pessoal',
    'higiene pessoal': 'Higiene Pessoal',
    'cosméticos': 'Higiene Pessoal',
    'cosmeticos': 'Higiene Pessoal',
    'perfumaria': 'Higiene Pessoal',

    # Limpeza
    'produtos de limpeza': 'Limpeza',
    'limpeza doméstica': 'Limpeza',
    'limpeza domestica': 'Limpeza',

    # Congelados
    'produtos congelados': 'Congelados',
    'alimentos congelados': 'Congelados',
    'frozen': 'Congelados',
}


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

    def _mapear_categoria_inteligente(self, nome_categoria: str) -> str:
        """
        Mapeia categoria do LLM para categoria do banco usando mapeamento inteligente.

        Args:
            nome_categoria: Nome da categoria retornada pelo LLM

        Returns:
            Nome da categoria do banco (ou original se não mapear)
        """
        if not nome_categoria:
            return nome_categoria

        nome_lower = nome_categoria.lower().strip()

        # 1. Busca exata no mapeamento
        if nome_lower in MAPEAMENTO_CATEGORIAS:
            categoria_mapeada = MAPEAMENTO_CATEGORIAS[nome_lower]
            logger.info(f"Categoria mapeada: '{nome_categoria}' → '{categoria_mapeada}'")
            return categoria_mapeada

        # 2. Busca parcial (se contém palavra-chave)
        for chave, valor in MAPEAMENTO_CATEGORIAS.items():
            if chave in nome_lower or nome_lower in chave:
                logger.info(f"Categoria mapeada (parcial): '{nome_categoria}' → '{valor}'")
                return valor

        # 3. Não encontrou mapeamento, retorna original
        return nome_categoria

    def buscar_ou_criar_categoria(self, nome_categoria: str) -> Optional[int]:
        """
        Busca categoria existente usando mapeamento inteligente ou retorna categoria 'Outros'.

        Args:
            nome_categoria: Nome da categoria vindo do LLM

        Returns:
            ID da categoria ou None
        """
        if not nome_categoria or nome_categoria.strip() == '':
            # Retorna categoria "Outros" como padrão
            categoria = self.buscar_categoria_por_nome('Outros')
            return categoria['id'] if categoria else None

        # ✨ MAPEAMENTO INTELIGENTE
        categoria_mapeada = self._mapear_categoria_inteligente(nome_categoria)

        # Buscar categoria mapeada no banco
        categoria = self.buscar_categoria_por_nome(categoria_mapeada)
        if categoria:
            return categoria['id']

        # Se ainda não encontrar, retorna "Outros"
        categoria_outros = self.buscar_categoria_por_nome('Outros')
        if categoria_outros:
            logger.warning(f"Categoria '{categoria_mapeada}' não encontrada no banco, usando 'Outros'")
            return categoria_outros['id']

        return None

    def buscar_produto_por_nome(self, nome: str, margem: float = 0.85) -> Optional[Dict]:
        """
        Busca produto por nome usando estratégia inteligente:
        1. Busca exata (nome_normalizado)
        2. Busca por alias
        3. Busca fuzzy em aliases
        4. Busca fuzzy em produtos

        Args:
            nome: Nome do produto
            margem: Margem de similaridade para busca fuzzy (0-1, padrão: 0.85)

        Returns:
            Dict com dados do produto ou None
        """
        query = """
            SELECT
                p.id, p.nome, p.nome_normalizado, p.marca, p.categoria,
                p.categoria_id, p.categoria_sugerida, p.codigo_barras,
                p.descricao, p.created_at, p.updated_at,
                bi.similaridade, bi.origem_match
            FROM buscar_produto_inteligente(%s, %s) bi
            INNER JOIN produtos_tabela p ON bi.id = p.id
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (nome, margem))
            result = cursor.fetchone()

            if result:
                # Log do tipo de match encontrado
                origem = result.get('origem_match', 'desconhecido')
                similaridade = result.get('similaridade', 1.0)

                if origem == 'exato':
                    logger.info(f"✓ Produto encontrado (match exato): '{result['nome']}'")
                elif origem == 'alias':
                    logger.info(f"✓ Produto encontrado (via alias): '{nome}' → '{result['nome']}'")
                elif origem == 'alias_fuzzy':
                    logger.warning(f"⚠ Produto encontrado (fuzzy alias, {similaridade:.1%}): '{nome}' → '{result['nome']}'")
                elif origem == 'fuzzy':
                    logger.warning(f"⚠ Produto encontrado (fuzzy, {similaridade:.1%}): '{nome}' → '{result['nome']}'")

                return dict(result)

            return None

    def criar_produto(
        self,
        nome: str,
        marca: Optional[str] = None,
        categoria: Optional[str] = None,
        categoria_id: Optional[int] = None,
        categoria_sugerida: Optional[str] = None,
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
            categoria_sugerida: Categoria original sugerida pelo LLM antes do mapeamento
            codigo_barras: Código de barras
            descricao: Descrição adicional

        Returns:
            ID do produto criado
        """
        query = """
            INSERT INTO produtos_tabela (nome, marca, categoria, categoria_id, categoria_sugerida, codigo_barras, descricao)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (nome, marca, categoria, categoria_id, categoria_sugerida, codigo_barras, descricao))
            result = cursor.fetchone()
            produto_id = result['id']

            # Log diferente se categoria foi mapeada
            if categoria_sugerida and categoria and categoria_sugerida.lower().strip() != categoria.lower().strip():
                logger.info(f"Produto criado: {nome} (ID: {produto_id}, Categoria: '{categoria_sugerida}' → '{categoria}')")
            else:
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

        # Preservar categoria original do LLM
        categoria_sugerida = categoria

        # Resolver categoria_id a partir do nome da categoria (com mapeamento)
        categoria_id = None
        categoria_mapeada = None
        if categoria:
            categoria_id = self.buscar_ou_criar_categoria(categoria)
            # Buscar nome da categoria mapeada
            if categoria_id:
                cat_obj = self.db.get_cursor()
                with self.db.get_cursor() as cursor:
                    cursor.execute("SELECT nome FROM categorias WHERE id = %s", (categoria_id,))
                    result = cursor.fetchone()
                    if result:
                        categoria_mapeada = result['nome']

        produto_id = self.criar_produto(
            nome=nome,
            marca=marca,
            categoria=categoria_mapeada or categoria,  # Categoria mapeada ou original
            categoria_id=categoria_id,  # Foreign key
            categoria_sugerida=categoria_sugerida  # Categoria original do LLM
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

    def _expandir_produtos_multiplos(self, produto_data: Dict) -> List[Dict]:
        """
        Expande produtos que contêm "ou" no nome em múltiplos produtos.

        Exemplo: "Picanha OU Alcatra OU Contra Filé"
        -> ["Picanha", "Alcatra", "Contra Filé"]

        Args:
            produto_data: Dict com dados do produto do LLM

        Returns:
            Lista de produtos expandidos (ou lista com 1 produto se não houver "ou")
        """
        nome = produto_data.get('nome', '')

        # Detectar " ou " no nome (case insensitive)
        # Padrão: procura por "ou" cercado por espaços
        if re.search(r'\s+ou\s+', nome, re.IGNORECASE):
            # Dividir por "ou" e limpar espaços
            nomes = re.split(r'\s+ou\s+', nome, flags=re.IGNORECASE)
            nomes = [n.strip() for n in nomes if n.strip()]

            # Criar cópia do produto para cada nome
            produtos_expandidos = []
            for nome_individual in nomes:
                produto_copia = produto_data.copy()
                produto_copia['nome'] = nome_individual
                produtos_expandidos.append(produto_copia)

            logger.info(f"Produto expandido: '{nome}' → {len(produtos_expandidos)} produtos")
            return produtos_expandidos

        # Se não tem "ou", retorna lista com produto original
        return [produto_data]

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

                    # ✨ EXPANDIR PRODUTOS COM "OU"
                    produtos_expandidos = self._expandir_produtos_multiplos(produto_data)

                    # Processar cada produto expandido
                    for prod in produtos_expandidos:
                        nome = prod.get('nome')
                        marca = prod.get('marca')
                        categoria = prod.get('categoria')
                        preco = prod.get('preco')
                        preco_original = prod.get('preco_original')
                        em_promocao = prod.get('em_promocao', False)
                        unidade = prod.get('unidade')
                        descricao = prod.get('descricao_adicional')
                        confianca = prod.get('confianca')

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

    def obter_categorias_sugeridas_mais_frequentes(
        self,
        limite: int = 20,
        apenas_nao_mapeadas: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retorna categorias sugeridas mais frequentes para análise.

        Args:
            limite: Número máximo de categorias a retornar
            apenas_nao_mapeadas: Se True, mostra apenas categorias classificadas como 'Outros'

        Returns:
            Lista de dicts com: categoria_sugerida, quantidade, exemplos de produtos
        """
        if apenas_nao_mapeadas:
            query = """
                SELECT
                    categoria_sugerida,
                    COUNT(*) as quantidade,
                    STRING_AGG(DISTINCT nome, ' | ' ORDER BY nome) as exemplos_produtos
                FROM produtos_tabela
                WHERE categoria_sugerida IS NOT NULL
                  AND categoria = 'Outros'
                GROUP BY categoria_sugerida
                ORDER BY quantidade DESC
                LIMIT %s
            """
        else:
            query = """
                SELECT
                    categoria_sugerida,
                    categoria as categoria_mapeada,
                    COUNT(*) as quantidade,
                    STRING_AGG(DISTINCT nome, ' | ' ORDER BY nome) as exemplos_produtos
                FROM produtos_tabela
                WHERE categoria_sugerida IS NOT NULL
                  AND LOWER(TRIM(categoria_sugerida)) != LOWER(TRIM(COALESCE(categoria, '')))
                GROUP BY categoria_sugerida, categoria
                ORDER BY quantidade DESC
                LIMIT %s
            """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (limite,))
            results = cursor.fetchall()
            return [dict(row) for row in results]

    def obter_estatisticas_mapeamento_categorias(self) -> Dict[str, Any]:
        """
        Retorna estatísticas sobre o mapeamento de categorias.

        Returns:
            Dict com estatísticas de mapeamento
        """
        query = """
            SELECT
                CASE
                    WHEN categoria = 'Outros' THEN 'Não Mapeada'
                    WHEN categoria_sugerida IS NULL THEN 'Sem Sugestão'
                    WHEN LOWER(TRIM(categoria_sugerida)) = LOWER(TRIM(categoria)) THEN 'Exata'
                    ELSE 'Mapeada'
                END as tipo_mapeamento,
                COUNT(*) as quantidade,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM produtos_tabela), 2) as percentual
            FROM produtos_tabela
            GROUP BY tipo_mapeamento
            ORDER BY quantidade DESC
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            return {row['tipo_mapeamento']: dict(row) for row in results}


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
