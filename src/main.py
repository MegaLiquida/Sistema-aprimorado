import os
import sys
import sqlite3
from datetime import datetime
import requests
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from src.models.database import db, init_database
from src.models.user import User
from src.models.product import Product
from src.models.responsible import Responsible
from src.models.sent_list import SentList
from src.utils.permissions import update_session_user_data

# Importar blueprints
from src.routes.listas import listas_bp
from src.routes.admin import admin_bp
from src.routes.envio import envio_bp
from src.routes.api import api_bp

app = Flask(__name__, 
           static_folder=os.path.join(os.path.dirname(__file__), 'static'),
           template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

app.config['SECRET_KEY'] = 'ean_system_secret_key_windows11'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'ean_system.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Registrar blueprints
app.register_blueprint(listas_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(envio_bp)
app.register_blueprint(api_bp)

# Inicializar banco de dados
with app.app_context():
    init_database()

# Rotas principais
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Redirecionar baseado no tipo de usuário
    if user.is_admin():
        return redirect(url_for('admin_panel'))
    elif user.can_access_lists_panel():
        return redirect(url_for('listas.painel_listas'))
    elif user.can_access_ean_panel():
        return render_template('index.html', user=user)
    else:
        flash('Usuário sem permissões definidas. Contate o administrador.', 'warning')
        return redirect(url_for('logout'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(nome=username).first()
        
        if user and check_password_hash(user.senha_hash, password):
            session['user_id'] = user.id
            update_session_user_data(user)
            
            # Redirecionar baseado no tipo de usuário
            if user.is_admin():
                return redirect(url_for('admin_panel'))
            elif user.can_access_lists_panel():
                return redirect(url_for('listas.painel_listas'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verificar se usuário já existe
        existing_user = User.query.filter_by(nome=username).first()
        if existing_user:
            flash('Usuário já existe', 'error')
            return render_template('register.html')
        
        # Criar novo usuário
        password_hash = generate_password_hash(password)
        new_user = User(nome=username, senha_hash=password_hash, admin=0, tipo_usuario='ean')
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Usuário criado com sucesso', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/search_ean', methods=['POST'])
def search_ean():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    ean = request.json.get('ean')
    user_id = session['user_id']
    
    # Buscar primeiro no banco local (produtos do próprio usuário)
    product = Product.query.filter_by(ean=ean, usuario_id=user_id).first()
    
    if product:
        return jsonify({
            'found': True,
            'nome': product.nome,
            'cor': product.cor or '',
            'voltagem': product.voltagem or '',
            'modelo': product.modelo or '',
            'source': 'local'
        })
    
    # Se não encontrou localmente, buscar em API externa (simulado)
    # Aqui você pode integrar com APIs reais de produtos
    try:
        # Simulação de busca externa
        external_data = simulate_external_api(ean)
        if external_data:
            return jsonify({
                'found': True,
                'nome': external_data['nome'],
                'cor': external_data.get('cor', ''),
                'voltagem': external_data.get('voltagem', ''),
                'modelo': external_data.get('modelo', ''),
                'source': 'external'
            })
    except Exception as e:
        print(f"Erro na busca externa: {e}")
    
    return jsonify({'found': False})

def simulate_external_api(ean):
    """Simula busca em API externa - substitua por integração real"""
    # Dados simulados para demonstração
    simulated_products = {
        '7891234567890': {
            'nome': 'Produto Exemplo 1',
            'cor': 'Azul',
            'voltagem': '220V',
            'modelo': 'EX-001'
        },
        '7891234567891': {
            'nome': 'Produto Exemplo 2',
            'cor': 'Vermelho',
            'voltagem': '110V',
            'modelo': 'EX-002'
        }
    }
    
    return simulated_products.get(ean)

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    data = request.json
    ean = data.get('ean')
    nome = data.get('nome')
    cor = data.get('cor', '')
    voltagem = data.get('voltagem', '')
    modelo = data.get('modelo', '')
    quantidade = int(data.get('quantidade', 1))
    user_id = session['user_id']
    
    # Verificar se produto já existe para este usuário
    existing_product = Product.query.filter_by(ean=ean, usuario_id=user_id).first()
    
    if existing_product:
        # Somar quantidade
        existing_product.quantidade += quantidade
    else:
        # Criar novo produto para este usuário
        new_product = Product(
            ean=ean,
            nome=nome,
            cor=cor,
            voltagem=voltagem,
            modelo=modelo,
            quantidade=quantidade,
            usuario_id=user_id
        )
        db.session.add(new_product)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Produto adicionado com sucesso'})

@app.route('/get_user_products')
def get_user_products():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    user_id = session['user_id']
    products = Product.query.filter_by(usuario_id=user_id).all()
    products_list = []
    
    for product in products:
        products_list.append({
            'id': product.id,
            'ean': product.ean,
            'nome': product.nome,
            'cor': product.cor or '',
            'voltagem': product.voltagem or '',
            'modelo': product.modelo or '',
            'quantidade': product.quantidade
        })
    
    return jsonify(products_list)

@app.route('/admin_panel')
def admin_panel():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Acesso negado', 'error')
        return redirect(url_for('login'))
    
    # Buscar estatísticas
    total_users = User.query.count()
    total_products = Product.query.count()
    total_lists = SentList.query.count()
    
    # Buscar listas recentes
    recent_lists = SentList.query.order_by(SentList.timestamp.desc()).limit(10).all()
    
    return render_template('admin.html', 
                         total_users=total_users,
                         total_products=total_products,
                         total_lists=total_lists,
                         recent_lists=recent_lists)

@app.route('/get_responsaveis')
def get_responsaveis():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    responsaveis = Responsible.query.all()
    responsaveis_list = []
    
    for responsavel in responsaveis:
        responsaveis_list.append({
            'id': responsavel.id,
            'nome': responsavel.nome,
            'ativo': responsavel.ativo
        })
    
    return jsonify(responsaveis_list)

@app.route('/enviar_lista', methods=['POST'])
def enviar_lista():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    data = request.json
    responsavel_id = data.get('responsavel_id')
    pin = data.get('pin')
    
    # Verificar responsável e PIN
    responsavel = Responsible.query.get(responsavel_id)
    if not responsavel or not responsavel.ativo:
        return jsonify({'success': False, 'message': 'Responsável não encontrado ou inativo'}), 400
    
    if responsavel.pin != pin:
        return jsonify({'success': False, 'message': 'PIN incorreto'}), 400
    
    # Buscar produtos do usuário
    user_id = session['user_id']
    products = Product.query.filter_by(usuario_id=user_id).all()
    if not products:
        return jsonify({'success': False, 'message': 'Não há produtos para enviar'}), 400
    
    # Criar lista enviada
    sent_list = SentList(
        usuario_id=session['user_id'],
        responsavel_id=responsavel_id,
        status='pendente',
        timestamp=datetime.now()
    )
    db.session.add(sent_list)
    db.session.flush()  # Para obter o ID da lista
    
    # Adicionar produtos à lista
    from src.models.produto_lista import ProdutoLista
    for product in products:
        produto_lista = ProdutoLista(
            lista_id=sent_list.id,
            ean=product.ean,
            nome=product.nome,
            cor=product.cor,
            voltagem=product.voltagem,
            modelo=product.modelo,
            quantidade=product.quantidade
        )
        db.session.add(produto_lista)
    
    # Limpar produtos do usuário após envio
    Product.query.filter_by(usuario_id=user_id).delete()
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Lista enviada com sucesso! Aprovada por {responsavel.nome}. ID da lista: {sent_list.id}'
    })

@app.route('/export_excel')
def export_excel():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    # Buscar produtos do usuário atual
    user_id = session['user_id']
    products = Product.query.filter_by(usuario_id=user_id).all()
    
    # Criar DataFrame
    data = []
    for product in products:
        data.append({
            'EAN': product.ean,
            'DESCRIÇÃO': product.nome,
            'COR': product.cor or '',
            'VOLTAGEM': product.voltagem or '',
            'MODELO': product.modelo or '',
            'QUANTIDADE': product.quantidade
        })
    
    df = pd.DataFrame(data)
    
    # Salvar em arquivo Excel
    excel_path = os.path.join(os.path.dirname(__file__), 'exports', 'produtos.xlsx')
    os.makedirs(os.path.dirname(excel_path), exist_ok=True)
    
    df.to_excel(excel_path, index=False)
    
    return send_file(excel_path, as_attachment=True, download_name='produtos_ean.xlsx')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)

