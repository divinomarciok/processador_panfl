"""
Módulo de processamento de imagens de panfletos usando LLM.
Suporta OpenAI GPT-4 Vision, Anthropic Claude e Google Gemini.
"""

import os
import json
import base64
import logging
import time
from typing import Dict, Optional, Tuple
from pathlib import Path
from io import BytesIO

from PIL import Image
import requests

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Prompt para extração de dados
PROMPT_EXTRACAO = """Você é um especialista em extrair informações de panfletos de supermercado.

Analise a imagem e extraia TODOS os produtos com preços.

REGRAS:
1. Extraia todos os produtos visíveis
2. Seja preciso com valores
3. Identifique promoções (preço normal vs promocional)
4. Capture datas de validade quando disponíveis
5. Identifique unidades de medida (kg, un, l, pct)
6. Identifique o supermercado se possível

FORMATO (JSON):
{
  "supermercado": "Nome do supermercado ou null",
  "data_validade_inicio": "YYYY-MM-DD ou null",
  "data_validade_fim": "YYYY-MM-DD ou null",
  "produtos": [
    {
      "nome": "Nome do produto",
      "marca": "Marca ou null",
      "categoria": "Categoria (Carnes, Bebidas, etc) ou null",
      "preco": 29.90,
      "preco_original": 35.90,
      "em_promocao": true,
      "unidade": "kg",
      "descricao_adicional": "Info extra ou null",
      "confianca": 0.95
    }
  ]
}

Retorne APENAS o JSON, sem texto antes ou depois."""


class ImageProcessor:
    """Processa imagens de panfletos."""

    def __init__(self, max_size: int = 2048):
        """
        Inicializa o processador de imagens.

        Args:
            max_size: Tamanho máximo da imagem (largura/altura)
        """
        self.max_size = max_size

    def carregar_imagem(self, caminho: str) -> Image.Image:
        """
        Carrega imagem do disco.

        Args:
            caminho: Caminho para a imagem

        Returns:
            Objeto PIL Image

        Raises:
            FileNotFoundError: Se arquivo não existir
            IOError: Se houver erro ao abrir imagem
        """
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"Imagem não encontrada: {caminho}")

        try:
            imagem = Image.open(caminho)
            logger.info(f"Imagem carregada: {imagem.size[0]}x{imagem.size[1]}px")
            return imagem
        except Exception as e:
            logger.error(f"Erro ao abrir imagem: {e}")
            raise IOError(f"Erro ao abrir imagem: {e}")

    def redimensionar_imagem(self, imagem: Image.Image) -> Image.Image:
        """
        Redimensiona imagem se necessário.

        Args:
            imagem: Objeto PIL Image

        Returns:
            Imagem redimensionada
        """
        width, height = imagem.size

        if width <= self.max_size and height <= self.max_size:
            return imagem

        # Calcular nova dimensão mantendo proporção
        if width > height:
            new_width = self.max_size
            new_height = int((height / width) * self.max_size)
        else:
            new_height = self.max_size
            new_width = int((width / height) * self.max_size)

        imagem_redimensionada = imagem.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

        logger.info(f"Imagem redimensionada: {new_width}x{new_height}px")
        return imagem_redimensionada

    def imagem_para_base64(self, imagem: Image.Image, formato: str = "JPEG") -> str:
        """
        Converte imagem para base64.

        Args:
            imagem: Objeto PIL Image
            formato: Formato de saída (JPEG, PNG, etc)

        Returns:
            String base64 da imagem
        """
        # Converter para RGB se necessário
        if imagem.mode not in ('RGB', 'L'):
            imagem = imagem.convert('RGB')

        buffer = BytesIO()
        imagem.save(buffer, format=formato, quality=85)
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        return img_base64

    def processar_imagem(self, caminho: str) -> Tuple[str, Image.Image]:
        """
        Processa imagem completa: carrega, redimensiona e converte para base64.

        Args:
            caminho: Caminho da imagem

        Returns:
            Tupla (base64_string, imagem_objeto)
        """
        imagem = self.carregar_imagem(caminho)
        imagem = self.redimensionar_imagem(imagem)
        base64_str = self.imagem_para_base64(imagem)

        return base64_str, imagem


class LLMClient:
    """Cliente para interação com LLMs."""

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        max_retries: int = 3
    ):
        """
        Inicializa cliente LLM.

        Args:
            provider: Provedor (openai, anthropic ou gemini)
            api_key: Chave da API
            max_retries: Número máximo de tentativas
        """
        self.provider = provider.lower()
        self.api_key = api_key or self._obter_api_key()
        self.max_retries = max_retries

        if self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Instale: pip install openai")

        elif self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Instale: pip install anthropic")

        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel('gemini-2.5-flash')
            except ImportError:
                raise ImportError("Instale: pip install google-generativeai")

        else:
            raise ValueError(f"Provider não suportado: {provider}")

    def _obter_api_key(self) -> str:
        """Obtém API key das variáveis de ambiente."""
        if self.provider == "openai":
            key = os.getenv('OPENAI_API_KEY')
            if not key:
                raise ValueError("OPENAI_API_KEY não definida")
            return key

        elif self.provider == "anthropic":
            key = os.getenv('ANTHROPIC_API_KEY')
            if not key:
                raise ValueError("ANTHROPIC_API_KEY não definida")
            return key

        elif self.provider == "gemini":
            key = os.getenv('GEMINI_API_KEY')
            if not key:
                raise ValueError("GEMINI_API_KEY não definida")
            return key

    def analisar_imagem_openai(
        self,
        base64_imagem: str,
        prompt: str
    ) -> str:
        """
        Analisa imagem usando OpenAI GPT-4 Vision.

        Args:
            base64_imagem: Imagem em base64
            prompt: Prompt para análise

        Returns:
            Resposta da LLM (JSON string)
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_imagem}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.2
            )

            resposta = response.choices[0].message.content
            logger.info("Resposta recebida da OpenAI")
            return resposta

        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI: {e}")
            raise

    def analisar_imagem_anthropic(
        self,
        base64_imagem: str,
        prompt: str
    ) -> str:
        """
        Analisa imagem usando Anthropic Claude.

        Args:
            base64_imagem: Imagem em base64
            prompt: Prompt para análise

        Returns:
            Resposta da LLM (JSON string)
        """
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_imagem
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                temperature=0.2
            )

            resposta = message.content[0].text
            logger.info("Resposta recebida da Anthropic")
            return resposta

        except Exception as e:
            logger.error(f"Erro ao chamar Anthropic: {e}")
            raise

    def analisar_imagem_gemini(
        self,
        base64_imagem: str,
        prompt: str
    ) -> str:
        """
        Analisa imagem usando Google Gemini.

        Args:
            base64_imagem: Imagem em base64
            prompt: Prompt para análise

        Returns:
            Resposta da LLM (JSON string)
        """
        try:
            import google.generativeai as genai
            from PIL import Image
            import io

            # Decodificar base64 para bytes
            img_bytes = base64.b64decode(base64_imagem)
            img = Image.open(io.BytesIO(img_bytes))

            # Criar conteúdo com imagem e texto
            response = self.client.generate_content(
                [prompt, img],
                generation_config={
                    'temperature': 0.2,
                    'max_output_tokens': 8192,
                }
            )

            resposta = response.text
            logger.info("Resposta recebida do Gemini")
            logger.info(f"RESPOSTA COMPLETA DO GEMINI:\n{resposta}")
            return resposta

        except Exception as e:
            logger.error(f"Erro ao chamar Gemini: {e}")
            raise

    def analisar_imagem(
        self,
        base64_imagem: str,
        prompt: str = PROMPT_EXTRACAO
    ) -> str:
        """
        Analisa imagem usando o provider configurado.

        Args:
            base64_imagem: Imagem em base64
            prompt: Prompt para análise

        Returns:
            Resposta da LLM

        Raises:
            Exception: Se todas as tentativas falharem
        """
        for tentativa in range(1, self.max_retries + 1):
            try:
                logger.info(f"Tentativa {tentativa}/{self.max_retries}")

                if self.provider == "openai":
                    return self.analisar_imagem_openai(base64_imagem, prompt)
                elif self.provider == "anthropic":
                    return self.analisar_imagem_anthropic(base64_imagem, prompt)
                elif self.provider == "gemini":
                    return self.analisar_imagem_gemini(base64_imagem, prompt)

            except Exception as e:
                logger.warning(f"Tentativa {tentativa} falhou: {e}")

                if tentativa < self.max_retries:
                    tempo_espera = tentativa * 2
                    logger.info(f"Aguardando {tempo_espera}s antes de tentar novamente...")
                    time.sleep(tempo_espera)
                else:
                    logger.error("Todas as tentativas falharam")
                    raise


class JSONParser:
    """Parser para extrair e validar JSON da resposta da LLM."""

    @staticmethod
    def extrair_json(texto: str) -> Dict:
        """
        Extrai JSON do texto da resposta.

        Args:
            texto: Texto contendo JSON

        Returns:
            Dict com dados parseados

        Raises:
            ValueError: Se não conseguir extrair JSON válido
        """
        # Remover blocos de código markdown (```json ... ```)
        import re
        texto_limpo = re.sub(r'```json\s*', '', texto)
        texto_limpo = re.sub(r'```\s*$', '', texto_limpo)
        texto_limpo = texto_limpo.strip()

        # Tentar parsear diretamente
        try:
            return json.loads(texto_limpo)
        except json.JSONDecodeError:
            pass

        # Tentar encontrar JSON no texto
        inicio = texto_limpo.find('{')
        fim = texto_limpo.rfind('}')

        if inicio == -1 or fim == -1:
            raise ValueError("Nenhum JSON encontrado na resposta")

        try:
            json_str = texto_limpo[inicio:fim + 1]
            logger.info(f"Tentando parsear JSON extraído (tamanho: {len(json_str)} chars)")
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {e}")
            logger.error(f"JSON problemático (últimos 200 chars): ...{json_str[-200:]}")
            raise ValueError(f"JSON inválido: {e}")

    @staticmethod
    def validar_dados(dados: Dict) -> Tuple[bool, Optional[str]]:
        """
        Valida estrutura dos dados extraídos.

        Args:
            dados: Dict com dados parseados

        Returns:
            Tupla (valido, mensagem_erro)
        """
        # Verificar chave produtos
        if 'produtos' not in dados:
            return False, "Campo 'produtos' não encontrado"

        produtos = dados['produtos']

        if not isinstance(produtos, list):
            return False, "Campo 'produtos' deve ser uma lista"

        if len(produtos) == 0:
            return False, "Nenhum produto encontrado"

        # Validar cada produto
        for idx, produto in enumerate(produtos):
            if not isinstance(produto, dict):
                return False, f"Produto {idx + 1} não é um objeto"

            # Validar campos obrigatórios
            if 'nome' not in produto or not produto['nome']:
                return False, f"Produto {idx + 1}: campo 'nome' obrigatório"

            if 'preco' not in produto:
                return False, f"Produto {idx + 1}: campo 'preco' obrigatório"

            # Validar tipo de preço
            try:
                preco = float(produto['preco'])
                if preco < 0:
                    return False, f"Produto {idx + 1}: preço negativo"
            except (ValueError, TypeError):
                return False, f"Produto {idx + 1}: preço inválido"

        return True, None


class PanfletoProcessor:
    """Processador completo de panfletos."""

    def __init__(
        self,
        llm_provider: str = "openai",
        api_key: Optional[str] = None,
        max_image_size: int = 2048,
        max_retries: int = 3
    ):
        """
        Inicializa o processador de panfletos.

        Args:
            llm_provider: Provedor LLM (openai, anthropic ou gemini)
            api_key: Chave da API
            max_image_size: Tamanho máximo da imagem
            max_retries: Número máximo de tentativas
        """
        self.image_processor = ImageProcessor(max_size=max_image_size)
        self.llm_client = LLMClient(
            provider=llm_provider,
            api_key=api_key,
            max_retries=max_retries
        )
        self.json_parser = JSONParser()

    def processar_panfleto(self, caminho_imagem: str) -> Dict:
        """
        Processa panfleto completo.

        Args:
            caminho_imagem: Caminho para a imagem do panfleto

        Returns:
            Dict com dados extraídos

        Raises:
            Exception: Se houver erro no processamento
        """
        logger.info(f"Processando: {caminho_imagem}")

        # Processar imagem
        base64_imagem, imagem_obj = self.image_processor.processar_imagem(caminho_imagem)

        # Analisar com LLM
        logger.info(f"Enviando para {self.llm_client.provider.upper()}...")
        resposta = self.llm_client.analisar_imagem(base64_imagem)

        # Parsear JSON
        logger.info("Parseando resposta...")
        logger.info(f"RESPOSTA A SER PARSEADA (primeiros 500 chars):\n{resposta[:500]}")
        dados = self.json_parser.extrair_json(resposta)

        # Validar dados
        valido, erro = self.json_parser.validar_dados(dados)
        if not valido:
            raise ValueError(f"Dados inválidos: {erro}")

        logger.info(f"JSON válido com {len(dados['produtos'])} produtos")

        return dados


def processar_panfleto(
    caminho_imagem: str,
    llm_provider: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    Função de conveniência para processar um panfleto.

    Args:
        caminho_imagem: Caminho da imagem
        llm_provider: Provedor LLM (padrão: da variável de ambiente)
        api_key: Chave da API (padrão: da variável de ambiente)

    Returns:
        Dict com dados extraídos
    """
    provider = llm_provider or os.getenv('LLM_PROVIDER', 'openai')
    max_size = int(os.getenv('MAX_IMAGE_SIZE', '2048'))
    max_retries = int(os.getenv('RETRY_ATTEMPTS', '3'))

    processor = PanfletoProcessor(
        llm_provider=provider,
        api_key=api_key,
        max_image_size=max_size,
        max_retries=max_retries
    )

    return processor.processar_panfleto(caminho_imagem)
