# Rotas para o painel de listas enviadas

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from sqlalchemy import or_, and_
from datetime import datetime
import json

from src.models.database import db
from src.models.sent_list import SentList
from src.models.produto_lista import ProdutoLista
from src.models.user import User
from src.models.responsible import Responsible
from src.utils.permissions import login_required, lists_access_required, admin_required

listas_bp = Blueprint('listas', __name__)

@listas_bp.route('/painel-listas')
@login_required
@lists_access_required
def painel_listas():
    """Página principal do painel de listas"""
    
    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtros
    busca = request.args.get('busca', '')
    status_filtro = request.args.get('status', '')
    usuario_filtro = request.args.get('usuario', '', type=int)
    responsavel_filtro = request.args.get('responsavel', '', type=int)
    
    # Query base
    query = SentList.query
    
    # Aplicar filtros
    if busca:
        # Buscar em produtos relacionados ou observações
        query = query.join(ProdutoLista, SentList.id == ProdutoLista.lista_id, isouter=True)
        query = query.filter(
            or_(
                ProdutoLista.ean.contains(busca),
                ProdutoLista.nome.contains(busca),
                SentList.observacoes.contains(busca)
            )
        )
    
    if status_filtro:
        query = query.filter(SentList.status == status_filtro)
    
    if usuario_filtro:
        query = query.filter(SentList.usuario_id == usuario_filtro)
    
    if responsavel_filtro:
        query = query.filter(SentList.responsavel_id == responsavel_filtro)
    
    # Ordenar por data mais recente
    query = query.order_by(SentList.timestamp.desc())
    
    # Paginação
    pagination = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    listas = pagination.items
    
    # Carregar produtos para cada lista
    for lista in listas:
        lista.produtos = ProdutoLista.query.filter_by(lista_id=lista.id).all()
    
    # Estatísticas
    stats = {
        'total': SentList.query.count(),
        'pendentes': SentList.query.filter_by(status='pendente').count(),
        'validadas': SentList.query.filter_by(status='validada').count(),
        'rejeitadas': SentList.query.filter_by(status='rejeitada').count()
    }
    
    # Dados para filtros
    usuarios = User.query.filter(User.tipo_usuario.in_(['listas', 'admin'])).all()
    responsaveis = Responsible.query.filter_by(ativo=1).all()
    
    return render_template('painel_listas.html',
                         listas=listas,
                         pagination=pagination,
                         stats=stats,
                         usuarios=usuarios,
                         responsaveis=responsaveis)

@listas_bp.route('/api/listas/filtrar', methods=['POST'])
@login_required
@lists_access_required
def filtrar_listas():
    """API para filtrar listas via AJAX"""
    
    try:
        filtros = request.get_json()
        
        # Query base
        query = SentList.query
        
        # Aplicar filtros
        if filtros.get('busca'):
            busca = filtros['busca']
            query = query.join(ProdutoLista, SentList.id == ProdutoLista.lista_id, isouter=True)
            query = query.filter(
                or_(
                    ProdutoLista.ean.contains(busca),
                    ProdutoLista.nome.contains(busca),
                    SentList.observacoes.contains(busca)
                )
            )
        
        if filtros.get('status'):
            query = query.filter(SentList.status == filtros['status'])
        
        if filtros.get('usuario'):
            query = query.filter(SentList.usuario_id == int(filtros['usuario']))
        
        if filtros.get('responsavel'):
            query = query.filter(SentList.responsavel_id == int(filtros['responsavel']))
        
        # Ordenar e limitar
        listas = query.order_by(SentList.timestamp.desc()).limit(50).all()
        
        # Converter para JSON
        listas_json = []
        for lista in listas:
            lista.produtos = ProdutoLista.query.filter_by(lista_id=lista.id).all()
            listas_json.append({
                'id': lista.id,
                'usuario': lista.usuario.nome,
                'status': lista.status,
                'status_display': lista.get_status_display(),
                'status_class': lista.get_status_class(),
                'timestamp': lista.timestamp.strftime('%d/%m/%Y %H:%M'),
                'responsavel': lista.responsavel.nome if lista.responsavel else None,
                'total_produtos': lista.get_total_produtos(),
                'total_quantidade': lista.get_total_quantidade(),
                'observacoes': lista.observacoes
            })
        
        # Estatísticas atualizadas
        stats = {
            'total': SentList.query.count(),
            'pendentes': SentList.query.filter_by(status='pendente').count(),
            'validadas': SentList.query.filter_by(status='validada').count(),
            'rejeitadas': SentList.query.filter_by(status='rejeitada').count()
        }
        
        return jsonify({
            'success': True,
            'listas': listas_json,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@listas_bp.route('/api/listas/<int:lista_id>/validar', methods=['POST'])
@login_required
@admin_required
def validar_lista(lista_id):
    """API para validar uma lista"""
    
    try:
        dados = request.get_json()
        
        # Buscar lista
        lista = SentList.query.get_or_404(lista_id)
        
        # Verificar se já foi validada
        if lista.status != 'pendente':
            return jsonify({
                'success': False,
                'message': 'Esta lista já foi processada'
            }), 400
        
        # Buscar responsável
        responsavel = Responsible.query.get(dados['responsavel_id'])
        if not responsavel:
            return jsonify({
                'success': False,
                'message': 'Responsável não encontrado'
            }), 400
        
        # Verificar PIN
        if not responsavel.verify_pin(dados['pin']):
            return jsonify({
                'success': False,
                'message': 'PIN incorreto ou responsável inativo'
            }), 400
        
        # Atualizar lista
        lista.status = dados['status']
        lista.validado = 1 if dados['status'] == 'validada' else 0
        lista.validador_id = session['user_id']
        lista.data_validacao = datetime.utcnow()
        lista.responsavel_id = responsavel.id
        lista.responsavel_pin = dados['pin']
        
        if dados.get('observacoes'):
            lista.observacoes = dados['observacoes']
        
        # Atualizar último acesso do responsável
        responsavel.update_last_access()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Lista {lista.get_status_display().lower()} com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@listas_bp.route('/api/listas/<int:lista_id>/detalhes')
@login_required
@lists_access_required
def detalhes_lista(lista_id):
    """API para obter detalhes de uma lista"""
    
    try:
        lista = SentList.query.get_or_404(lista_id)
        produtos = ProdutoLista.query.filter_by(lista_id=lista_id).all()
        
        return jsonify({
            'success': True,
            'lista': {
                'id': lista.id,
                'usuario': lista.usuario.nome,
                'status': lista.status,
                'status_display': lista.get_status_display(),
                'timestamp': lista.timestamp.strftime('%d/%m/%Y %H:%M'),
                'data_envio': lista.data_envio.strftime('%d/%m/%Y %H:%M') if lista.data_envio else None,
                'data_validacao': lista.data_validacao.strftime('%d/%m/%Y %H:%M') if lista.data_validacao else None,
                'responsavel': lista.responsavel.nome if lista.responsavel else None,
                'validador': lista.validador.nome if lista.validador else None,
                'observacoes': lista.observacoes,
                'total_produtos': len(produtos),
                'total_quantidade': sum(p.quantidade for p in produtos)
            },
            'produtos': [p.to_dict() for p in produtos]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@listas_bp.route('/api/listas/exportar')
@login_required
@admin_required
def exportar_listas():
    """Exportar listas para Excel"""
    
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        # Buscar todas as listas
        listas = SentList.query.order_by(SentList.timestamp.desc()).all()
        
        # Preparar dados
        dados = []
        for lista in listas:
            produtos = ProdutoLista.query.filter_by(lista_id=lista.id).all()
            
            for produto in produtos:
                dados.append({
                    'Lista ID': lista.id,
                    'Usuário': lista.usuario.nome,
                    'Status': lista.get_status_display(),
                    'Data Criação': lista.timestamp.strftime('%d/%m/%Y %H:%M'),
                    'Data Validação': lista.data_validacao.strftime('%d/%m/%Y %H:%M') if lista.data_validacao else '',
                    'Responsável': lista.responsavel.nome if lista.responsavel else '',
                    'Validador': lista.validador.nome if lista.validador else '',
                    'EAN': produto.ean,
                    'Produto': produto.nome,
                    'Cor': produto.cor or '',
                    'Voltagem': produto.voltagem or '',
                    'Modelo': produto.modelo or '',
                    'Quantidade': produto.quantidade,
                    'Observações': lista.observacoes or ''
                })
        
        # Criar DataFrame
        df = pd.DataFrame(dados)
        
        # Criar arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Listas Enviadas', index=False)
        
        output.seek(0)
        
        # Nome do arquivo com timestamp
        filename = f'listas_enviadas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Erro ao exportar listas: {str(e)}', 'error')
        return redirect(url_for('listas.painel_listas'))

@listas_bp.route('/api/listas/estatisticas')
@login_required
@lists_access_required
def estatisticas_listas():
    """API para obter estatísticas das listas"""
    
    try:
        # Estatísticas básicas
        stats = {
            'total': SentList.query.count(),
            'pendentes': SentList.query.filter_by(status='pendente').count(),
            'validadas': SentList.query.filter_by(status='validada').count(),
            'rejeitadas': SentList.query.filter_by(status='rejeitada').count()
        }
        
        # Estatísticas por usuário
        usuarios_stats = db.session.query(
            User.nome,
            db.func.count(SentList.id).label('total_listas')
        ).join(SentList).group_by(User.id, User.nome).all()
        
        # Estatísticas por responsável
        responsaveis_stats = db.session.query(
            Responsible.nome,
            db.func.count(SentList.id).label('total_validacoes')
        ).join(SentList).group_by(Responsible.id, Responsible.nome).all()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'usuarios': [{'nome': u.nome, 'total': u.total_listas} for u in usuarios_stats],
            'responsaveis': [{'nome': r.nome, 'total': r.total_validacoes} for r in responsaveis_stats]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

