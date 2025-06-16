# Integração com API do Mercado Livre
# Adaptado do sistema original no GitHub

import requests
import json
import time
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MercadoLivreAPI:
    """Classe para integração com a API do Mercado Livre"""
    
    def __init__(self):
        self.base_url = "https://api.mercadolibre.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EAN-System/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Cache para evitar muitas requisições
        self.cache = {}
        self.cache_timeout = 3600  # 1 hora
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms entre requisições
    
    def _wait_rate_limit(self):
        """Implementa rate limiting para evitar sobrecarga da API"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica se o cache ainda é válido"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get('timestamp', 0)
        return (time.time() - cached_time) < self.cache_timeout
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Obtém dados do cache se válidos"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """Salva dados no cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def buscar_produto_por_ean(self, ean: str) -> Dict:
        """
        Busca produto no Mercado Livre por código EAN
        
        Args:
            ean (str): Código EAN do produto
            
        Returns:
            Dict: Dados do produto encontrado ou erro
        """
        try:
            # Limpar e validar EAN
            ean_clean = re.sub(r'[^0-9]', '', str(ean))
            
            if not ean_clean or len(ean_clean) not in [8, 12, 13]:
                return {
                    'success': False,
                    'message': 'EAN inválido. Deve ter 8, 12 ou 13 dígitos.',
                    'source': 'validation_error'
                }
            
            # Verificar cache
            cache_key = f"ean_{ean_clean}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.info(f"Produto EAN {ean_clean} encontrado no cache")
                return cached_result
            
            # Rate limiting
            self._wait_rate_limit()
            
            # Buscar no Mercado Livre
            logger.info(f"Buscando produto EAN {ean_clean} no Mercado Livre")
            
            # Primeira tentativa: busca direta por EAN
            resultado = self._buscar_por_ean_direto(ean_clean)
            
            if resultado['success']:
                self._save_to_cache(cache_key, resultado)
                return resultado
            
            # Segunda tentativa: busca por texto
            resultado = self._buscar_por_texto(ean_clean)
            
            if resultado['success']:
                self._save_to_cache(cache_key, resultado)
                return resultado
            
            # Terceira tentativa: produto simulado baseado no EAN
            resultado = self._gerar_produto_simulado(ean_clean)
            self._save_to_cache(cache_key, resultado)
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao buscar produto EAN {ean}: {str(e)}")
            return {
                'success': False,
                'message': f'Erro na busca: {str(e)}',
                'source': 'api_error'
            }
    
    def _buscar_por_ean_direto(self, ean: str) -> Dict:
        """Busca direta por EAN usando a API do Mercado Livre"""
        try:
            # Endpoint para busca por EAN
            url = f"{self.base_url}/sites/MLB/search"
            params = {
                'q': ean,
                'limit': 10
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('results'):
                # Pegar o primeiro resultado
                produto = data['results'][0]
                
                # Buscar detalhes do produto
                detalhes = self._obter_detalhes_produto(produto['id'])
                
                return {
                    'success': True,
                    'data': {
                        'nome': produto.get('title', f'Produto {ean}'),
                        'cor': detalhes.get('cor', ''),
                        'voltagem': detalhes.get('voltagem', ''),
                        'modelo': detalhes.get('modelo', ''),
                        'ean': ean,
                        'preco': produto.get('price', 0),
                        'moeda': produto.get('currency_id', 'BRL'),
                        'link': produto.get('permalink', ''),
                        'imagem': produto.get('thumbnail', ''),
                        'vendedor': produto.get('seller', {}).get('nickname', ''),
                        'condicao': produto.get('condition', ''),
                        'disponivel': produto.get('available_quantity', 0)
                    },
                    'source': 'mercado_livre_api',
                    'message': 'Produto encontrado no Mercado Livre'
                }
            
            return {
                'success': False,
                'message': 'Produto não encontrado na busca direta',
                'source': 'mercado_livre_api'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para Mercado Livre: {str(e)}")
            return {
                'success': False,
                'message': f'Erro na comunicação com Mercado Livre: {str(e)}',
                'source': 'api_error'
            }
        except Exception as e:
            logger.error(f"Erro inesperado na busca direta: {str(e)}")
            return {
                'success': False,
                'message': f'Erro inesperado: {str(e)}',
                'source': 'api_error'
            }
    
    def _buscar_por_texto(self, ean: str) -> Dict:
        """Busca por texto usando o EAN como termo de busca"""
        try:
            url = f"{self.base_url}/sites/MLB/search"
            params = {
                'q': f'EAN {ean}',
                'limit': 5
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('results'):
                # Procurar produto que contenha o EAN na descrição
                for produto in data['results']:
                    titulo = produto.get('title', '').lower()
                    if ean in titulo or ean in produto.get('id', ''):
                        detalhes = self._obter_detalhes_produto(produto['id'])
                        
                        return {
                            'success': True,
                            'data': {
                                'nome': produto.get('title', f'Produto {ean}'),
                                'cor': detalhes.get('cor', ''),
                                'voltagem': detalhes.get('voltagem', ''),
                                'modelo': detalhes.get('modelo', ''),
                                'ean': ean,
                                'preco': produto.get('price', 0),
                                'moeda': produto.get('currency_id', 'BRL'),
                                'link': produto.get('permalink', ''),
                                'imagem': produto.get('thumbnail', ''),
                                'vendedor': produto.get('seller', {}).get('nickname', ''),
                                'condicao': produto.get('condition', ''),
                                'disponivel': produto.get('available_quantity', 0)
                            },
                            'source': 'mercado_livre_text_search',
                            'message': 'Produto encontrado por busca textual'
                        }
            
            return {
                'success': False,
                'message': 'Produto não encontrado na busca por texto',
                'source': 'mercado_livre_text_search'
            }
            
        except Exception as e:
            logger.error(f"Erro na busca por texto: {str(e)}")
            return {
                'success': False,
                'message': f'Erro na busca por texto: {str(e)}',
                'source': 'api_error'
            }
    
    def _obter_detalhes_produto(self, produto_id: str) -> Dict:
        """Obtém detalhes adicionais do produto"""
        try:
            url = f"{self.base_url}/items/{produto_id}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extrair atributos relevantes
            atributos = data.get('attributes', [])
            detalhes = {}
            
            for attr in atributos:
                nome = attr.get('name', '').lower()
                valor = attr.get('value_name', '')
                
                if 'cor' in nome or 'color' in nome:
                    detalhes['cor'] = valor
                elif 'voltagem' in nome or 'voltage' in nome or 'tensão' in nome:
                    detalhes['voltagem'] = valor
                elif 'modelo' in nome or 'model' in nome:
                    detalhes['modelo'] = valor
            
            return detalhes
            
        except Exception as e:
            logger.error(f"Erro ao obter detalhes do produto {produto_id}: {str(e)}")
            return {}
    
    def _gerar_produto_simulado(self, ean: str) -> Dict:
        """Gera produto simulado baseado no EAN quando não encontrado"""
        try:
            # Extrair informações do EAN
            categoria_nome = self._extrair_categoria_do_ean(ean)
            
            # Gerar cor aleatória baseada no EAN
            cores = ["Preto", "Branco", "Azul", "Vermelho", "Verde", "Amarelo", "Cinza", "Prata"]
            cor = cores[sum(int(d) for d in ean) % len(cores)]
            
            # Gerar voltagem baseada no EAN
            voltagens = ["110V", "220V", "Bivolt", ""]
            voltagem = voltagens[sum(int(d) for d in ean if d.isdigit()) % len(voltagens)]
            
            # Gerar modelo baseado no EAN
            modelo = f"MOD-{ean[-6:-2]}"
            
            nome_produto = f"{categoria_nome} EAN {ean}"
            
            logger.info(f"Produto simulado gerado para o EAN {ean}: {nome_produto}")
            
            return {
                'success': True,
                'data': {
                    'nome': nome_produto,
                    'cor': cor,
                    'voltagem': voltagem,
                    'modelo': modelo,
                    'ean': ean
                },
                'source': 'fallback_simulado',
                'message': 'Produto não encontrado na base de dados. Por favor, preencha as informações manualmente.'
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar produto simulado: {str(e)}")
            return {
                'success': False,
                'message': f'Erro ao gerar produto simulado: {str(e)}',
                'source': 'fallback_error'
            }
    
    def _extrair_categoria_do_ean(self, ean: str) -> str:
        """Extrai categoria baseada no prefixo do EAN"""
        try:
            if len(ean) >= 3:
                prefixo = ean[:3]
                
                # Mapeamento básico de prefixos para categorias
                categorias = {
                    '789': 'Produto Nacional',
                    '780': 'Eletrônico',
                    '790': 'Eletrodoméstico',
                    '850': 'Livro',
                    '977': 'Revista',
                    '978': 'Livro',
                    '979': 'Música'
                }
                
                for pref, cat in categorias.items():
                    if ean.startswith(pref):
                        return cat
            
            return 'Produto'
            
        except Exception:
            return 'Produto'
    
    def buscar_multiplos_eans(self, eans: List[str]) -> Dict[str, Dict]:
        """
        Busca múltiplos produtos por EAN
        
        Args:
            eans (List[str]): Lista de códigos EAN
            
        Returns:
            Dict[str, Dict]: Dicionário com resultados para cada EAN
        """
        resultados = {}
        
        for ean in eans:
            try:
                resultado = self.buscar_produto_por_ean(ean)
                resultados[ean] = resultado
                
                # Pequena pausa entre requisições
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Erro ao buscar EAN {ean}: {str(e)}")
                resultados[ean] = {
                    'success': False,
                    'message': f'Erro na busca: {str(e)}',
                    'source': 'batch_error'
                }
        
        return resultados
    
    def obter_estatisticas_cache(self) -> Dict:
        """Retorna estatísticas do cache"""
        total_items = len(self.cache)
        items_validos = sum(1 for key in self.cache if self._is_cache_valid(key))
        
        return {
            'total_items': total_items,
            'items_validos': items_validos,
            'items_expirados': total_items - items_validos,
            'timeout_segundos': self.cache_timeout
        }
    
    def limpar_cache(self):
        """Limpa o cache"""
        self.cache.clear()
        logger.info("Cache limpo")

# Instância global da API
mercado_livre_api = MercadoLivreAPI()

def buscar_produto_mercado_livre(ean: str) -> Dict:
    """
    Função de conveniência para buscar produto no Mercado Livre
    
    Args:
        ean (str): Código EAN do produto
        
    Returns:
        Dict: Resultado da busca
    """
    return mercado_livre_api.buscar_produto_por_ean(ean)

def buscar_multiplos_produtos_mercado_livre(eans: List[str]) -> Dict[str, Dict]:
    """
    Função de conveniência para buscar múltiplos produtos
    
    Args:
        eans (List[str]): Lista de códigos EAN
        
    Returns:
        Dict[str, Dict]: Resultados para cada EAN
    """
    return mercado_livre_api.buscar_multiplos_eans(eans)

