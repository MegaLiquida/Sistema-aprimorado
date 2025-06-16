# Rotas para API do Mercado Livre e consultas de EAN

from flask import Blueprint, request, jsonify, session
import logging

from src.models.database import db
from src.models.product import Product
from src.utils.permissions import login_required, ean_access_required
from src.utils.validators import validar_ean
from src.utils.mercado_livre import buscar_produto_mercado_livre, buscar_multiplos_produtos_mercado_livre

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/mercado-livre/<ean>')
@login_required
@ean_access_required
def consultar_ean_mercado_livre(ean):
    """API para consultar EAN no Mercado Livre"""
    
    try:
        # Validar EAN
        ean_valido, ean_msg = validar_ean(ean)
        if not ean_valido:
            return jsonify({
                'success': False,
                'message': ean_msg,
                'source': 'validation_error'
            }), 400
        
        # Buscar primeiro no banco local
        produto_local = Product.query.filter_by(ean=ean).first()
        
        if produto_local:
            logger.info(f"Produto EAN {ean} encontrado no banco local")
            return jsonify({
                'success': True,
                'data': {
                    'nome': produto_local.nome,
                    'cor': produto_local.cor or '',
                    'voltagem': produto_local.voltagem or '',
                    'modelo': produto_local.modelo or '',
                    'ean': produto_local.ean
                },
                'source': 'banco_local',
                'message': 'Produto encontrado no banco local'
            })
        
        # Buscar no Mercado Livre
        logger.info(f"Buscando EAN {ean} no Mercado Livre")
        resultado = buscar_produto_mercado_livre(ean)
        
        # Se encontrou no Mercado Livre, salvar no banco local
        if resultado['success'] and resultado.get('data'):
            try:
                produto_data = resultado['data']
                novo_produto = Product(
                    ean=produto_data['ean'],
                    nome=produto_data['nome'],
                    cor=produto_data.get('cor', ''),
                    voltagem=produto_data.get('voltagem', ''),
                    modelo=produto_data.get('modelo', '')
                )
                
                db.session.add(novo_produto)
                db.session.commit()
                
                logger.info(f"Produto EAN {ean} salvo no banco local")
                resultado['message'] += ' (Salvo no banco local)'
                
            except Exception as e:
                logger.error(f"Erro ao salvar produto no banco: {str(e)}")
                # Não falhar a requisição por erro de salvamento
                resultado['message'] += ' (Erro ao salvar no banco local)'
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro na consulta EAN {ean}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}',
            'source': 'api_error'
        }), 500

@api_bp.route('/api/mercado-livre/buscar-multiplos', methods=['POST'])
@login_required
@ean_access_required
def buscar_multiplos_eans():
    """API para buscar múltiplos EANs de uma vez"""
    
    try:
        dados = request.get_json()
        eans = dados.get('eans', [])
        
        if not eans or not isinstance(eans, list):
            return jsonify({
                'success': False,
                'message': 'Lista de EANs é obrigatória'
            }), 400
        
        if len(eans) > 50:
            return jsonify({
                'success': False,
                'message': 'Máximo de 50 EANs por requisição'
            }), 400
        
        # Validar todos os EANs
        eans_validos = []
        for ean in eans:
            ean_valido, _ = validar_ean(ean)
            if ean_valido:
                eans_validos.append(ean)
        
        if not eans_validos:
            return jsonify({
                'success': False,
                'message': 'Nenhum EAN válido fornecido'
            }), 400
        
        # Buscar no banco local primeiro
        produtos_locais = Product.query.filter(Product.ean.in_(eans_validos)).all()
        resultados = {}
        
        # Mapear produtos locais
        eans_encontrados_local = set()
        for produto in produtos_locais:
            eans_encontrados_local.add(produto.ean)
            resultados[produto.ean] = {
                'success': True,
                'data': {
                    'nome': produto.nome,
                    'cor': produto.cor or '',
                    'voltagem': produto.voltagem or '',
                    'modelo': produto.modelo or '',
                    'ean': produto.ean
                },
                'source': 'banco_local',
                'message': 'Produto encontrado no banco local'
            }
        
        # EANs que precisam ser buscados no Mercado Livre
        eans_para_buscar = [ean for ean in eans_validos if ean not in eans_encontrados_local]
        
        if eans_para_buscar:
            logger.info(f"Buscando {len(eans_para_buscar)} EANs no Mercado Livre")
            resultados_ml = buscar_multiplos_produtos_mercado_livre(eans_para_buscar)
            
            # Salvar produtos encontrados no banco local
            produtos_para_salvar = []
            for ean, resultado in resultados_ml.items():
                if resultado['success'] and resultado.get('data'):
                    produto_data = resultado['data']
                    produto = Product(
                        ean=produto_data['ean'],
                        nome=produto_data['nome'],
                        cor=produto_data.get('cor', ''),
                        voltagem=produto_data.get('voltagem', ''),
                        modelo=produto_data.get('modelo', '')
                    )
                    produtos_para_salvar.append(produto)
            
            # Salvar em lote
            if produtos_para_salvar:
                try:
                    db.session.add_all(produtos_para_salvar)
                    db.session.commit()
                    logger.info(f"{len(produtos_para_salvar)} produtos salvos no banco local")
                except Exception as e:
                    logger.error(f"Erro ao salvar produtos em lote: {str(e)}")
                    db.session.rollback()
            
            # Adicionar resultados do Mercado Livre
            resultados.update(resultados_ml)
        
        # Estatísticas
        total_buscados = len(eans_validos)
        encontrados_local = len(eans_encontrados_local)
        encontrados_ml = sum(1 for r in resultados.values() if r['success'] and r.get('source') != 'banco_local')
        nao_encontrados = total_buscados - encontrados_local - encontrados_ml
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'estatisticas': {
                'total_buscados': total_buscados,
                'encontrados_local': encontrados_local,
                'encontrados_mercado_livre': encontrados_ml,
                'nao_encontrados': nao_encontrados
            }
        })
        
    except Exception as e:
        logger.error(f"Erro na busca múltipla: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

@api_bp.route('/api/mercado-livre/cache/estatisticas')
@login_required
@ean_access_required
def estatisticas_cache():
    """API para obter estatísticas do cache do Mercado Livre"""
    
    try:
        from src.utils.mercado_livre import mercado_livre_api
        
        stats = mercado_livre_api.obter_estatisticas_cache()
        
        return jsonify({
            'success': True,
            'cache': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter estatísticas: {str(e)}'
        }), 500

@api_bp.route('/api/mercado-livre/cache/limpar', methods=['POST'])
@login_required
@ean_access_required
def limpar_cache():
    """API para limpar cache do Mercado Livre"""
    
    try:
        from src.utils.mercado_livre import mercado_livre_api
        
        mercado_livre_api.limpar_cache()
        
        return jsonify({
            'success': True,
            'message': 'Cache limpo com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao limpar cache: {str(e)}'
        }), 500

@api_bp.route('/api/produtos/buscar', methods=['POST'])
@login_required
@ean_access_required
def buscar_produtos():
    """API unificada para buscar produtos (local + Mercado Livre)"""
    
    try:
        dados = request.get_json()
        termo = dados.get('termo', '').strip()
        
        if not termo:
            return jsonify({
                'success': False,
                'message': 'Termo de busca é obrigatório'
            }), 400
        
        resultados = []
        
        # Se o termo parece ser um EAN, buscar por EAN
        if termo.isdigit() and len(termo) in [8, 12, 13]:
            ean_valido, _ = validar_ean(termo)
            if ean_valido:
                # Buscar no banco local
                produto_local = Product.query.filter_by(ean=termo).first()
                if produto_local:
                    resultados.append({
                        'ean': produto_local.ean,
                        'nome': produto_local.nome,
                        'cor': produto_local.cor or '',
                        'voltagem': produto_local.voltagem or '',
                        'modelo': produto_local.modelo or '',
                        'source': 'banco_local'
                    })
                else:
                    # Buscar no Mercado Livre
                    resultado_ml = buscar_produto_mercado_livre(termo)
                    if resultado_ml['success'] and resultado_ml.get('data'):
                        produto_data = resultado_ml['data']
                        resultados.append({
                            'ean': produto_data['ean'],
                            'nome': produto_data['nome'],
                            'cor': produto_data.get('cor', ''),
                            'voltagem': produto_data.get('voltagem', ''),
                            'modelo': produto_data.get('modelo', ''),
                            'source': 'mercado_livre'
                        })
        else:
            # Buscar por nome no banco local
            produtos_locais = Product.query.filter(
                Product.nome.contains(termo)
            ).limit(20).all()
            
            for produto in produtos_locais:
                resultados.append({
                    'ean': produto.ean,
                    'nome': produto.nome,
                    'cor': produto.cor or '',
                    'voltagem': produto.voltagem or '',
                    'modelo': produto.modelo or '',
                    'source': 'banco_local'
                })
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'total': len(resultados)
        })
        
    except Exception as e:
        logger.error(f"Erro na busca de produtos: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

