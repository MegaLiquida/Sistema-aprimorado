# Rotas para gestão de usuários e administração

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from werkzeug.security import generate_password_hash
from datetime import datetime

from src.models.database import db
from src.models.user import User
from src.models.responsible import Responsible
from src.models.sent_list import SentList
from src.models.product import Product
from src.utils.permissions import login_required, admin_required
from src.utils.validators import validar_nome_usuario, validar_senha, validar_tipo_usuario

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_panel():
    """Painel administrativo principal"""
    
    # Estatísticas gerais
    total_users = User.query.count()
    total_products = Product.query.count()
    total_lists = SentList.query.count()
    total_responsaveis = Responsible.query.count()
    
    # Estatísticas por tipo de usuário
    usuarios_ean = User.query.filter_by(tipo_usuario='ean').count()
    usuarios_listas = User.query.filter_by(tipo_usuario='listas').count()
    usuarios_admin = User.query.filter_by(tipo_usuario='admin').count()
    
    # Listas pendentes
    listas_pendentes = SentList.query.filter_by(status='pendente').count()
    
    # Usuários recentes
    usuarios_recentes = User.query.order_by(User.id.desc()).limit(5).all()
    
    # Listas recentes
    listas_recentes = SentList.query.order_by(SentList.timestamp.desc()).limit(5).all()
    
    return render_template('admin.html',
                         total_users=total_users,
                         total_products=total_products,
                         total_lists=total_lists,
                         total_responsaveis=total_responsaveis,
                         usuarios_ean=usuarios_ean,
                         usuarios_listas=usuarios_listas,
                         usuarios_admin=usuarios_admin,
                         listas_pendentes=listas_pendentes,
                         usuarios_recentes=usuarios_recentes,
                         listas_recentes=listas_recentes)

@admin_bp.route('/admin/criar-usuario', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_usuario():
    """Criar novo usuário com tipo específico"""
    
    if request.method == 'GET':
        return render_template('criar_usuario.html')
    
    try:
        # Obter dados do formulário
        nome = request.form.get('nome', '').strip()
        senha = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        tipo_usuario = request.form.get('tipo_usuario', '')
        admin_completo = request.form.get('admin_completo') == 'on'
        
        # Validações
        nome_valido, nome_msg = validar_nome_usuario(nome)
        if not nome_valido:
            return jsonify({'success': False, 'message': nome_msg}), 400
        
        senha_valida, senha_msg = validar_senha(senha)
        if not senha_valida:
            return jsonify({'success': False, 'message': senha_msg}), 400
        
        if senha != confirmar_senha:
            return jsonify({'success': False, 'message': 'Senhas não coincidem'}), 400
        
        tipo_valido, tipo_msg = validar_tipo_usuario(tipo_usuario)
        if not tipo_valido:
            return jsonify({'success': False, 'message': tipo_msg}), 400
        
        # Verificar se usuário já existe
        usuario_existente = User.query.filter_by(nome=nome).first()
        if usuario_existente:
            return jsonify({'success': False, 'message': 'Usuário já existe'}), 400
        
        # Criar novo usuário
        senha_hash = generate_password_hash(senha)
        
        novo_usuario = User(
            nome=nome,
            senha_hash=senha_hash,
            tipo_usuario=tipo_usuario,
            admin=1 if tipo_usuario == 'admin' and admin_completo else 0
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuário {nome} criado com sucesso como {novo_usuario.get_tipo_display()}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/usuarios')
@login_required
@admin_required
def listar_usuarios():
    """Listar todos os usuários"""
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtros
    tipo_filtro = request.args.get('tipo', '')
    busca = request.args.get('busca', '')
    
    # Query base
    query = User.query
    
    # Aplicar filtros
    if tipo_filtro:
        query = query.filter(User.tipo_usuario == tipo_filtro)
    
    if busca:
        query = query.filter(User.nome.contains(busca))
    
    # Paginação
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    usuarios = pagination.items
    
    return render_template('listar_usuarios.html',
                         usuarios=usuarios,
                         pagination=pagination)

@admin_bp.route('/admin/usuarios/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(user_id):
    """Editar usuário existente"""
    
    usuario = User.query.get_or_404(user_id)
    
    if request.method == 'GET':
        return render_template('editar_usuario.html', usuario=usuario)
    
    try:
        # Obter dados do formulário
        nome = request.form.get('nome', '').strip()
        tipo_usuario = request.form.get('tipo_usuario', '')
        nova_senha = request.form.get('nova_senha', '')
        ativo = request.form.get('ativo') == 'on'
        
        # Validações
        if nome != usuario.nome:
            nome_valido, nome_msg = validar_nome_usuario(nome)
            if not nome_valido:
                return jsonify({'success': False, 'message': nome_msg}), 400
            
            # Verificar se novo nome já existe
            usuario_existente = User.query.filter_by(nome=nome).first()
            if usuario_existente and usuario_existente.id != user_id:
                return jsonify({'success': False, 'message': 'Nome de usuário já existe'}), 400
        
        tipo_valido, tipo_msg = validar_tipo_usuario(tipo_usuario)
        if not tipo_valido:
            return jsonify({'success': False, 'message': tipo_msg}), 400
        
        if nova_senha:
            senha_valida, senha_msg = validar_senha(nova_senha)
            if not senha_valida:
                return jsonify({'success': False, 'message': senha_msg}), 400
        
        # Atualizar usuário
        usuario.nome = nome
        usuario.tipo_usuario = tipo_usuario
        usuario.admin = 1 if tipo_usuario == 'admin' else 0
        
        if nova_senha:
            usuario.senha_hash = generate_password_hash(nova_senha)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuário {nome} atualizado com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/usuarios/<int:user_id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(user_id):
    """Excluir usuário"""
    
    try:
        usuario = User.query.get_or_404(user_id)
        
        # Não permitir excluir o próprio usuário
        if user_id == session['user_id']:
            return jsonify({'success': False, 'message': 'Não é possível excluir seu próprio usuário'}), 400
        
        # Verificar se usuário tem listas associadas
        listas_usuario = SentList.query.filter_by(usuario_id=user_id).count()
        if listas_usuario > 0:
            return jsonify({
                'success': False, 
                'message': f'Usuário possui {listas_usuario} listas associadas. Não é possível excluir.'
            }), 400
        
        nome_usuario = usuario.nome
        db.session.delete(usuario)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuário {nome_usuario} excluído com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/responsaveis')
@login_required
@admin_required
def listar_responsaveis():
    """Listar responsáveis"""
    
    responsaveis = Responsible.query.all()
    return render_template('listar_responsaveis.html', responsaveis=responsaveis)

@admin_bp.route('/admin/responsaveis/criar', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_responsavel():
    """Criar novo responsável"""
    
    if request.method == 'GET':
        return render_template('criar_responsavel.html')
    
    try:
        nome = request.form.get('nome', '').strip()
        pin = request.form.get('pin', '').strip()
        
        # Validações
        if not nome or len(nome) < 3:
            return jsonify({'success': False, 'message': 'Nome deve ter pelo menos 3 caracteres'}), 400
        
        if not pin or len(pin) != 4 or not pin.isdigit():
            return jsonify({'success': False, 'message': 'PIN deve ter exatamente 4 dígitos'}), 400
        
        # Verificar se já existe
        responsavel_existente = Responsible.query.filter_by(nome=nome).first()
        if responsavel_existente:
            return jsonify({'success': False, 'message': 'Responsável já existe'}), 400
        
        # Verificar se PIN já está em uso
        pin_existente = Responsible.query.filter_by(pin=pin).first()
        if pin_existente:
            return jsonify({'success': False, 'message': 'PIN já está em uso'}), 400
        
        # Criar responsável
        novo_responsavel = Responsible(
            nome=nome,
            pin=pin,
            ativo=1
        )
        
        db.session.add(novo_responsavel)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Responsável {nome} criado com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/responsaveis/<int:resp_id>/toggle-ativo', methods=['POST'])
@login_required
@admin_required
def toggle_responsavel_ativo(resp_id):
    """Ativar/desativar responsável"""
    
    try:
        responsavel = Responsible.query.get_or_404(resp_id)
        responsavel.ativo = 1 - responsavel.ativo  # Toggle
        
        db.session.commit()
        
        status = "ativado" if responsavel.ativo else "desativado"
        return jsonify({
            'success': True,
            'message': f'Responsável {responsavel.nome} {status} com sucesso',
            'ativo': responsavel.ativo
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/estatisticas')
@login_required
@admin_required
def estatisticas_admin():
    """Estatísticas detalhadas para administradores"""
    
    try:
        # Estatísticas de usuários
        stats_usuarios = {
            'total': User.query.count(),
            'ean': User.query.filter_by(tipo_usuario='ean').count(),
            'listas': User.query.filter_by(tipo_usuario='listas').count(),
            'admin': User.query.filter_by(tipo_usuario='admin').count()
        }
        
        # Estatísticas de listas
        stats_listas = {
            'total': SentList.query.count(),
            'pendentes': SentList.query.filter_by(status='pendente').count(),
            'validadas': SentList.query.filter_by(status='validada').count(),
            'rejeitadas': SentList.query.filter_by(status='rejeitada').count()
        }
        
        # Estatísticas de produtos
        stats_produtos = {
            'total': Product.query.count(),
            'cadastrados_hoje': Product.query.filter(
                Product.id > 0  # Placeholder - adicionar campo de data se necessário
            ).count()
        }
        
        # Responsáveis ativos
        responsaveis_ativos = Responsible.query.filter_by(ativo=1).count()
        
        return jsonify({
            'success': True,
            'usuarios': stats_usuarios,
            'listas': stats_listas,
            'produtos': stats_produtos,
            'responsaveis_ativos': responsaveis_ativos
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

