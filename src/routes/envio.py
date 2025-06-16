# Rotas para envio de listas e funcionalidades relacionadas

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from datetime import datetime
import json

from src.models.database import db
from src.models.sent_list import SentList
from src.models.produto_lista import ProdutoLista
from src.models.user import User
from src.models.responsible import Responsible
from src.utils.permissions import login_required, lists_access_required
from src.utils.validators import validar_ean, validar_pin, validar_produto_data

envio_bp = Blueprint('envio', __name__)

@envio_bp.route('/enviar-lista')
@login_required
@lists_access_required
def formulario_envio():
    """Formulário para envio de nova lista"""
    
    responsaveis = Responsible.query.filter_by(ativo=1).all()
    return render_template('enviar_lista.html', responsaveis=responsaveis)

@envio_bp.route('/api/enviar-lista', methods=['POST'])
@login_required
@lists_access_required
def enviar_lista():
    """API para enviar nova lista de produtos"""
    
    try:
        dados = request.get_json()
        
        # Validar dados básicos
        produtos = dados.get('produtos', [])
        observacoes = dados.get('observacoes', '')
        responsavel_id = dados.get('responsavel_id')
        pin_responsavel = dados.get('pin_responsavel', '')
        
        if not produtos:
            return jsonify({'success': False, 'message': 'Lista deve conter pelo menos um produto'}), 400
        
        # Validar responsável e PIN se fornecidos
        responsavel = None
        if responsavel_id and pin_responsavel:
            responsavel = Responsible.query.get(responsavel_id)
            if not responsavel:
                return jsonify({'success': False, 'message': 'Responsável não encontrado'}), 400
            
            if not responsavel.verify_pin(pin_responsavel):
                return jsonify({'success': False, 'message': 'PIN do responsável incorreto ou responsável inativo'}), 400
        
        # Validar produtos
        produtos_validados = []
        for i, produto in enumerate(produtos):
            produto_valido, erros = validar_produto_data(produto)
            if not produto_valido:
                return jsonify({
                    'success': False, 
                    'message': f'Produto {i+1}: {"; ".join(erros)}'
                }), 400
            
            produtos_validados.append({
                'ean': produto['ean'],
                'nome': produto['nome'],
                'cor': produto.get('cor', ''),
                'voltagem': produto.get('voltagem', ''),
                'modelo': produto.get('modelo', ''),
                'quantidade': int(produto['quantidade'])
            })
        
        # Criar lista
        nova_lista = SentList(
            usuario_id=session['user_id'],
            observacoes=observacoes,
            status='pendente'
        )
        
        # Se responsável foi validado, marcar como enviada
        if responsavel:
            nova_lista.enviado = 1
            nova_lista.data_envio = datetime.utcnow()
            nova_lista.responsavel_id = responsavel.id
            nova_lista.responsavel_pin = pin_responsavel
            responsavel.update_last_access()
        
        db.session.add(nova_lista)
        db.session.flush()  # Para obter o ID da lista
        
        # Adicionar produtos
        for produto_data in produtos_validados:
            produto = ProdutoLista(
                lista_id=nova_lista.id,
                **produto_data
            )
            db.session.add(produto)
        
        # Salvar JSON dos produtos para compatibilidade
        nova_lista.set_produtos_json(produtos_validados)
        
        db.session.commit()
        
        mensagem = 'Lista enviada com sucesso!'
        if responsavel:
            mensagem += f' Validada pelo responsável {responsavel.nome}.'
        else:
            mensagem += ' Aguardando validação.'
        
        return jsonify({
            'success': True,
            'message': mensagem,
            'lista_id': nova_lista.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@envio_bp.route('/api/validar-pin-responsavel', methods=['POST'])
@login_required
@lists_access_required
def validar_pin_responsavel():
    """API para validar PIN do responsável"""
    
    try:
        dados = request.get_json()
        responsavel_id = dados.get('responsavel_id')
        pin = dados.get('pin', '')
        
        if not responsavel_id or not pin:
            return jsonify({'success': False, 'message': 'Responsável e PIN são obrigatórios'}), 400
        
        responsavel = Responsible.query.get(responsavel_id)
        if not responsavel:
            return jsonify({'success': False, 'message': 'Responsável não encontrado'}), 400
        
        if responsavel.verify_pin(pin):
            return jsonify({
                'success': True,
                'message': f'PIN validado para {responsavel.nome}',
                'responsavel_nome': responsavel.nome
            })
        else:
            return jsonify({'success': False, 'message': 'PIN incorreto ou responsável inativo'}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@envio_bp.route('/api/buscar-produto-ean', methods=['POST'])
@login_required
@lists_access_required
def buscar_produto_ean():
    """API para buscar produto por EAN (integração futura com Mercado Livre)"""
    
    try:
        dados = request.get_json()
        ean = dados.get('ean', '')
        
        # Validar EAN
        ean_valido, ean_msg = validar_ean(ean)
        if not ean_valido:
            return jsonify({'success': False, 'message': ean_msg}), 400
        
        # Buscar primeiro no banco local
        from src.models.product import Product
        produto_local = Product.query.filter_by(ean=ean).first()
        
        if produto_local:
            return jsonify({
                'success': True,
                'source': 'local',
                'produto': {
                    'ean': produto_local.ean,
                    'nome': produto_local.nome,
                    'cor': produto_local.cor or '',
                    'voltagem': produto_local.voltagem or '',
                    'modelo': produto_local.modelo or ''
                }
            })
        
        # TODO: Integrar com API do Mercado Livre
        # Por enquanto, retornar produto genérico
        return jsonify({
            'success': True,
            'source': 'fallback',
            'produto': {
                'ean': ean,
                'nome': f'Produto {ean}',
                'cor': '',
                'voltagem': '',
                'modelo': ''
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@envio_bp.route('/minhas-listas')
@login_required
@lists_access_required
def minhas_listas():
    """Visualizar listas do usuário atual"""
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Buscar listas do usuário
    pagination = SentList.query.filter_by(usuario_id=session['user_id'])\
                              .order_by(SentList.timestamp.desc())\
                              .paginate(page=page, per_page=per_page, error_out=False)
    
    listas = pagination.items
    
    # Carregar produtos para cada lista
    for lista in listas:
        lista.produtos = ProdutoLista.query.filter_by(lista_id=lista.id).all()
    
    return render_template('minhas_listas.html', listas=listas, pagination=pagination)

@envio_bp.route('/api/lista/<int:lista_id>/reenviar', methods=['POST'])
@login_required
@lists_access_required
def reenviar_lista(lista_id):
    """Reenviar lista com validação por PIN"""
    
    try:
        lista = SentList.query.get_or_404(lista_id)
        
        # Verificar se é o dono da lista ou admin
        if lista.usuario_id != session['user_id'] and not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        
        # Verificar se lista não foi enviada ainda
        if lista.enviado:
            return jsonify({'success': False, 'message': 'Lista já foi enviada'}), 400
        
        dados = request.get_json()
        responsavel_id = dados.get('responsavel_id')
        pin = dados.get('pin', '')
        
        if not responsavel_id or not pin:
            return jsonify({'success': False, 'message': 'Responsável e PIN são obrigatórios'}), 400
        
        # Validar responsável
        responsavel = Responsible.query.get(responsavel_id)
        if not responsavel or not responsavel.verify_pin(pin):
            return jsonify({'success': False, 'message': 'PIN incorreto ou responsável inativo'}), 400
        
        # Atualizar lista
        lista.enviado = 1
        lista.data_envio = datetime.utcnow()
        lista.responsavel_id = responsavel.id
        lista.responsavel_pin = pin
        
        responsavel.update_last_access()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Lista reenviada com sucesso! Validada por {responsavel.nome}.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@envio_bp.route('/api/lista/<int:lista_id>/editar', methods=['GET', 'POST'])
@login_required
@lists_access_required
def editar_lista(lista_id):
    """Editar lista existente"""
    
    try:
        lista = SentList.query.get_or_404(lista_id)
        
        # Verificar permissões
        if lista.usuario_id != session['user_id'] and not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        
        if request.method == 'GET':
            # Retornar dados da lista para edição
            produtos = ProdutoLista.query.filter_by(lista_id=lista_id).all()
            
            return jsonify({
                'success': True,
                'lista': {
                    'id': lista.id,
                    'observacoes': lista.observacoes,
                    'status': lista.status,
                    'enviado': lista.enviado
                },
                'produtos': [p.to_dict() for p in produtos]
            })
        
        # POST - Atualizar lista
        if lista.status == 'validada':
            return jsonify({'success': False, 'message': 'Lista já validada não pode ser editada'}), 400
        
        dados = request.get_json()
        produtos = dados.get('produtos', [])
        observacoes = dados.get('observacoes', '')
        
        if not produtos:
            return jsonify({'success': False, 'message': 'Lista deve conter pelo menos um produto'}), 400
        
        # Validar produtos
        produtos_validados = []
        for i, produto in enumerate(produtos):
            produto_valido, erros = validar_produto_data(produto)
            if not produto_valido:
                return jsonify({
                    'success': False, 
                    'message': f'Produto {i+1}: {"; ".join(erros)}'
                }), 400
            
            produtos_validados.append({
                'ean': produto['ean'],
                'nome': produto['nome'],
                'cor': produto.get('cor', ''),
                'voltagem': produto.get('voltagem', ''),
                'modelo': produto.get('modelo', ''),
                'quantidade': int(produto['quantidade'])
            })
        
        # Atualizar lista
        lista.observacoes = observacoes
        lista.set_produtos_json(produtos_validados)
        
        # Remover produtos antigos
        ProdutoLista.query.filter_by(lista_id=lista_id).delete()
        
        # Adicionar produtos novos
        for produto_data in produtos_validados:
            produto = ProdutoLista(
                lista_id=lista.id,
                **produto_data
            )
            db.session.add(produto)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lista atualizada com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

