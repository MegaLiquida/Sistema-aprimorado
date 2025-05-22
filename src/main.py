import sys
import os
import sqlite3
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from datetime import datetime
import io
import requests
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import pandas as pd
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ean_app_secret_key')  # Chave para sessões

# Configuração do banco de dados
if os.environ.get('RENDER') and os.environ.get('DATABASE_URL'):
    # Usar PostgreSQL no Render
    DB_TYPE = 'postgres'
    DATABASE_URL = os.environ.get('DATABASE_URL')
    print(f"Usando PostgreSQL no Render: {DATABASE_URL}")
else:
    # Usar SQLite localmente
    DB_TYPE = 'sqlite'
    DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'produtos.db')
    print(f"Usando SQLite localmente: {DB_FILE}")

# Configuração da API do Mercado Livre
ML_CLIENT_ID = os.environ.get('MERCADO_LIVRE_CLIENT_ID')
ML_CLIENT_SECRET = os.environ.get('ML_CLIENT_SECRET')

# Função para obter conexão com o banco de dados
def get_db_connection():
    if DB_TYPE == 'postgres':
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

# Inicializar o banco de dados
def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgres':
        # Tabela de usuários no PostgreSQL
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            admin INTEGER DEFAULT 0
        )
        ''')
        
        # Tabela de produtos no PostgreSQL
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            ean TEXT NOT NULL,
            nome TEXT NOT NULL,
            cor TEXT,
            voltagem TEXT,
            modelo TEXT,
            quantidade INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            timestamp TEXT,
            enviado INTEGER DEFAULT 0,
            data_envio TEXT,
            validado INTEGER DEFAULT 0,
            validador_id INTEGER,
            data_validacao TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (validador_id) REFERENCES usuarios (id)
        )
        ''')
        
        # Verificar se já existe um admin
        cursor.execute('SELECT * FROM usuarios WHERE admin = 1')
        admin = cursor.fetchone()
        
        if not admin:
            # Criar um usuário admin padrão
            admin_hash = generate_password_hash('admin')
            cursor.execute(
                'INSERT INTO usuarios (nome, senha_hash, admin) VALUES (%s, %s, %s)',
                ('admin', admin_hash, 1)
            )
            
            # Criar usuários solicitados
            celso_hash = generate_password_hash('cel*2025')
            cursor.execute(
                'INSERT INTO usuarios (nome, senha_hash, admin) VALUES (%s, %s, %s)',
                ('Celso', celso_hash, 0)
            )
            
            mega_hash = generate_password_hash('meg*2025')
            cursor.execute(
                'INSERT INTO usuarios (nome, senha_hash, admin) VALUES (%s, %s, %s)',
                ('Mega', mega_hash, 1)
            )
    else:
        # Tabela de usuários no SQLite
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            admin INTEGER DEFAULT 0
        )
        ''')
        
        # Tabela de produtos no SQLite
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ean TEXT NOT NULL,
            nome TEXT NOT NULL,
            cor TEXT,
            voltagem TEXT,
            modelo TEXT,
            quantidade INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            timestamp TEXT,
            enviado INTEGER DEFAULT 0,
            data_envio TEXT,
            validado INTEGER DEFAULT 0,
            validador_id INTEGER,
            data_validacao TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (validador_id) REFERENCES usuarios (id)
        )
        ''')
        
        # Verificar se já existe um admin
        cursor.execute('SELECT * FROM usuarios WHERE admin = 1')
        admin = cursor.fetchone()
        
        if not admin:
            # Criar um usuário admin padrão
            admin_hash = generate_password_hash('admin')
            cursor.execute('INSERT INTO usuarios (nome, senha_hash, admin) VALUES (?, ?, ?)', 
                          ('admin', admin_hash, 1))
            
            # Criar usuários solicitados
            celso_hash = generate_password_hash('cel*2025')
            cursor.execute('INSERT INTO usuarios (nome, senha_hash, admin) VALUES (?, ?, ?)', 
                          ('Celso', celso_hash, 0))
            
            mega_hash = generate_password_hash('meg*2025')
            cursor.execute('INSERT INTO usuarios (nome, senha_hash, admin) VALUES (?, ?, ?)', 
                          ('Mega', mega_hash, 1))
    
    conn.commit()
    conn.close()

# Funções de autenticação
def registrar_usuario(nome, senha):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        senha_hash = generate_password_hash(senha)
        
        if DB_TYPE == 'postgres':
            cursor.execute('INSERT INTO usuarios (nome, senha_hash) VALUES (%s, %s)', (nome, senha_hash))
        else:
            cursor.execute('INSERT INTO usuarios (nome, senha_hash) VALUES (?, ?)', (nome, senha_hash))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao registrar usuário: {str(e)}")
        return False
    finally:
        conn.close()

def verificar_usuario(nome, senha):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgres':
        cursor.execute('SELECT id, senha_hash, admin FROM usuarios WHERE nome = %s', (nome,))
    else:
        cursor.execute('SELECT id, senha_hash, admin FROM usuarios WHERE nome = ?', (nome,))
    
    usuario = cursor.fetchone()
    conn.close()
    
    if DB_TYPE == 'postgres' and usuario:
        if check_password_hash(usuario[1], senha):
            return {'id': usuario[0], 'admin': usuario[2]}
    elif usuario and check_password_hash(usuario[1], senha):
        return {'id': usuario[0], 'admin': usuario[2]}
    
    return None

def obter_nome_usuario(usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgres':
        cursor.execute('SELECT nome FROM usuarios WHERE id = %s', (usuario_id,))
    else:
        cursor.execute('SELECT nome FROM usuarios WHERE id = ?', (usuario_id,))
    
    usuario = cursor.fetchone()
    conn.close()
    
    if DB_TYPE == 'postgres' and usuario:
        return usuario[0]
    elif usuario:
        return usuario[0]
    
    return None

# Funções de produtos
def carregar_produtos_usuario(usuario_id, apenas_nao_enviados=False):
    conn = get_db_connection()
    
    if DB_TYPE == 'postgres':
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if apenas_nao_enviados:
            cursor.execute('SELECT * FROM produtos WHERE usuario_id = %s AND enviado = 0', (usuario_id,))
        else:
            cursor.execute('SELECT * FROM produtos WHERE usuario_id = %s', (usuario_id,))
        
        produtos = list(cursor.fetchall())
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if apenas_nao_enviados:
            cursor.execute('SELECT * FROM produtos WHERE usuario_id = ? AND enviado = 0', (usuario_id,))
        else:
            cursor.execute('SELECT * FROM produtos WHERE usuario_id = ?', (usuario_id,))
        
        produtos = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return produtos

def carregar_todas_listas_enviadas():
    conn = get_db_connection()
    
    if DB_TYPE == 'postgres':
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar produtos enviados junto com o nome do usuário e do validador (se houver)
        cursor.execute('''
        SELECT p.*, u.nome as nome_usuario, v.nome as nome_validador 
        FROM produtos p 
        JOIN usuarios u ON p.usuario_id = u.id 
        LEFT JOIN usuarios v ON p.validador_id = v.id 
        WHERE p.enviado = 1 
        ORDER BY p.data_envio DESC
        ''')
        
        produtos = list(cursor.fetchall())
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar produtos enviados junto com o nome do usuário e do validador (se houver)
        cursor.execute('''
        SELECT p.*, u.nome as nome_usuario, v.nome as nome_validador 
        FROM produtos p 
        JOIN usuarios u ON p.usuario_id = u.id 
        LEFT JOIN usuarios v ON p.validador_id = v.id 
        WHERE p.enviado = 1 
        ORDER BY p.data_envio DESC
        ''')
        
        produtos = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return produtos

def pesquisar_produtos(termo_pesquisa):
    conn = get_db_connection()
    
    if DB_TYPE == 'postgres':
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar produtos que correspondem ao termo de pesquisa (EAN ou palavra na descrição)
        cursor.execute('''
        SELECT p.*, u.nome as nome_usuario, v.nome as nome_validador 
        FROM produtos p 
        JOIN usuarios u ON p.usuario_id = u.id 
        LEFT JOIN usuarios v ON p.validador_id = v.id 
        WHERE p.enviado = 1 AND (p.ean LIKE %s OR p.nome LIKE %s OR p.cor LIKE %s OR p.modelo LIKE %s) 
        ORDER BY p.data_envio DESC
        ''', (f'%{termo_pesquisa}%', f'%{termo_pesquisa}%', f'%{termo_pesquisa}%', f'%{termo_pesquisa}%'))
        
        produtos = list(cursor.fetchall())
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar produtos que correspondem ao termo de pesquisa (EAN ou palavra na descrição)
        cursor.execute('''
        SELECT p.*, u.nome as nome_usuario, v.nome as nome_validador 
        FROM produtos p 
        JOIN usuarios u ON p.usuario_id = u.id 
        LEFT JOIN usuarios v ON p.validador_id = v.id 
        WHERE p.enviado = 1 AND (p.ean LIKE ? OR p.nome LIKE ? OR p.cor LIKE ? OR p.modelo LIKE ?) 
        ORDER BY p.data_envio DESC
        ''', (f'%{termo_pesquisa}%', f'%{termo_pesquisa}%', f'%{termo_pesquisa}%', f'%{termo_pesquisa}%'))
        
        produtos = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return produtos

def buscar_produto_local(ean, usuario_id):
    conn = get_db_connection()
    
    if DB_TYPE == 'postgres':
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM produtos WHERE ean = %s AND usuario_id = %s AND enviado = 0', (ean, usuario_id))
        produto = cursor.fetchone()
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM produtos WHERE ean = ? AND usuario_id = ? AND enviado = 0', (ean, usuario_id))
        produto = cursor.fetchone()
    
    conn.close()
    
    if produto:
        if DB_TYPE == 'postgres':
            return dict(produto)
        else:
            return dict(produto)
    
    return None

def salvar_produto(produto, usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se o produto já existe para este usuário e não foi enviado
    if DB_TYPE == 'postgres':
        cursor.execute('SELECT * FROM produtos WHERE ean = %s AND usuario_id = %s AND enviado = 0', 
                      (produto['ean'], usuario_id))
        existing = cursor.fetchone()
        
        if existing:
            # Atualizar quantidade
            cursor.execute('''
            UPDATE produtos 
            SET quantidade = quantidade + %s, timestamp = %s 
            WHERE ean = %s AND usuario_id = %s AND enviado = 0
            ''', (produto['quantidade'], produto['timestamp'], produto['ean'], usuario_id))
        else:
            # Inserir novo produto
            cursor.execute('''
            INSERT INTO produtos (ean, nome, cor, voltagem, modelo, quantidade, usuario_id, timestamp, enviado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
            ''', (
                produto['ean'],
                produto['nome'],
                produto['cor'],
                produto['voltagem'],
                produto['modelo'],
                produto['quantidade'],
                usuario_id,
                produto['timestamp']
            ))
    else:
        cursor.execute('SELECT * FROM produtos WHERE ean = ? AND usuario_id = ? AND enviado = 0', 
                      (produto['ean'], usuario_id))
        existing = cursor.fetchone()
        
        if existing:
            # Atualizar quantidade
            cursor.execute('''
            UPDATE produtos 
            SET quantidade = quantidade + ?, timestamp = ? 
            WHERE ean = ? AND usuario_id = ? AND enviado = 0
            ''', (produto['quantidade'], produto['timestamp'], produto['ean'], usuario_id))
        else:
            # Inserir novo produto
            cursor.execute('''
            INSERT INTO produtos (ean, nome, cor, voltagem, modelo, quantidade, usuario_id, timestamp, enviado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                produto['ean'],
                produto['nome'],
                produto['cor'],
                produto['voltagem'],
                produto['modelo'],
                produto['quantidade'],
                usuario_id,
                produto['timestamp']
            ))
    
    conn.commit()
    conn.close()

def enviar_lista_produtos(usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    data_envio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Marcar todos os produtos não enviados como enviados
    if DB_TYPE == 'postgres':
        cursor.execute('''
        UPDATE produtos 
        SET enviado = 1, data_envio = %s 
        WHERE usuario_id = %s AND enviado = 0
        ''', (data_envio, usuario_id))
    else:
        cursor.execute('''
        UPDATE produtos 
        SET enviado = 1, data_envio = ? 
        WHERE usuario_id = ? AND enviado = 0
        ''', (data_envio, usuario_id))
    
    conn.commit()
    conn.close()
    
    return data_envio

def validar_lista(data_envio, nome_usuario, validador_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obter o ID do usuário pelo nome
    if DB_TYPE == 'postgres':
        cursor.execute('SELECT id FROM usuarios WHERE nome = %s', (nome_usuario,))
    else:
        cursor.execute('SELECT id FROM usuarios WHERE nome = ?', (nome_usuario,))
    
    usuario = cursor.fetchone()
    
    if not usuario:
        conn.close()
        return False
    
    usuario_id = usuario[0]
    data_validacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Marcar todos os produtos da lista como validados
    if DB_TYPE == 'postgres':
        cursor.execute('''
        UPDATE produtos 
        SET validado = 1, validador_id = %s, data_validacao = %s 
        WHERE usuario_id = %s AND data_envio = %s AND enviado = 1
        ''', (validador_id, data_validacao, usuario_id, data_envio))
    else:
        cursor.execute('''
        UPDATE produtos 
        SET validado = 1, validador_id = ?, data_validacao = ? 
        WHERE usuario_id = ? AND data_envio = ? AND enviado = 1
        ''', (validador_id, data_validacao, usuario_id, data_envio))
    
    conn.commit()
    conn.close()
    
    return True

def excluir_produto(produto_id, usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgres':
        cursor.execute('DELETE FROM produtos WHERE id = %s AND usuario_id = %s AND enviado = 0', 
                      (produto_id, usuario_id))
    else:
        cursor.execute('DELETE FROM produtos WHERE id = ? AND usuario_id = ? AND enviado = 0', 
                      (produto_id, usuario_id))
    
    conn.commit()
    conn.close()

# Função para obter token do Mercado Livre
def get_mercado_livre_token():
    if not ML_CLIENT_ID or not ML_CLIENT_SECRET:
        print("Credenciais do Mercado Livre não configuradas")
        return None
    
    try:
        url = "https://api.mercadolibre.com/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": ML_CLIENT_ID,
            "client_secret": ML_CLIENT_SECRET
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Erro ao obter token do Mercado Livre: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Erro ao obter token do Mercado Livre: {str(e)}")
        return None

# Função para buscar informações do produto por EAN no Mercado Livre
def buscar_produto_mercado_livre(ean):
    token = get_mercado_livre_token()
    if not token:
        return None
    
    try:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={ean}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            if results:
                produto = results[0]  # Pegar o primeiro resultado
                
                # Extrair informações relevantes
                return {
                    "success": True,
                    "data": {
                        "nome": produto.get("title", f"Produto {ean}"),
                        "marca": produto.get("attributes", [{}])[0].get("value_name", "") if produto.get("attributes") else "",
                        "categoria": produto.get("category_id", ""),
                        "preco": produto.get("price", 0),
                        "link": produto.get("permalink", ""),
                        "imagem": produto.get("thumbnail", "")
                    }
                }
            
        return None
    except Exception as e:
        print(f"Erro ao buscar produto no Mercado Livre: {str(e)}")
        return None

# Função para buscar informações do produto por EAN online
def buscar_produto_online(ean):
    # Primeiro, tentar buscar no Mercado Livre
    ml_result = buscar_produto_mercado_livre(ean)
    if ml_result:
        return ml_result
    
    # Se não encontrar no Mercado Livre, tentar na API alternativa
    try:
        # Primeiro, tentamos obter um token de acesso
        token_url = "https://gtin.rscsistemas.com.br/oauth/token"
        token_response = requests.post(token_url, json={
            "username": "demo",  # Usuário demo para testes
            "password": "demo"   # Senha demo para testes
        }, timeout=5)
        
        if token_response.status_code != 200:
            # Se não conseguir autenticar, retornamos dados básicos para edição manual
            return {
                "success": True,
                "data": {
                    "nome": f"Produto {ean}",
                    "marca": "",
                    "categoria": ""
                },
                "message": "Produto não encontrado na base de dados. Por favor, preencha as informações manualmente."
            }
        
        token_data = token_response.json()
        token = token_data.get("token")
        
        # Com o token, buscamos as informações do produto
        produto_url = f"https://gtin.rscsistemas.com.br/api/gtin/infor/{ean}"
        headers = {"Authorization": f"Bearer {token}"}
        produto_response = requests.get(produto_url, headers=headers, timeout=5)
        
        if produto_response.status_code == 200:
            produto_data = produto_response.json()
            # Verificar se o produto foi realmente encontrado ou se é uma resposta padrão de "não encontrado"
            if produto_data.get("nome") == "405" or produto_data.get("ean") == "405":
                return {
                    "success": True,
                    "data": {
                        "nome": f"Produto {ean}",
                        "marca": "",
                        "categoria": ""
                    },
                    "message": "Produto não encontrado na base de dados. Por favor, preencha as informações manualmente."
                }
            return {
                "success": True,
                "data": produto_data
            }
        else:
            # Se não encontrar na API, retornamos dados básicos para edição manual
            return {
                "success": True,
                "data": {
                    "nome": f"Produto {ean}",
                    "marca": "",
                    "categoria": ""
                },
                "message": "Produto não encontrado na base de dados. Por favor, preencha as informações manualmente."
            }
    except Exception as e:
        # Em caso de erro, retornamos dados básicos para edição manual
        return {
            "success": True,
            "data": {
                "nome": f"Produto {ean}",
                "marca": "",
                "categoria": ""
            },
            "message": f"Erro ao buscar produto: {str(e)}. Por favor, preencha as informações manualmente."
        }

# Manipulador de erros global
@app.errorhandler(Exception)
def handle_exception(e):
    print(f"Erro não tratado: {str(e)}")
    return jsonify({
        "error": "Ocorreu um erro interno no servidor",
        "details": str(e)
    }), 500

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        
        usuario = verificar_usuario(nome, senha)
        if usuario:
            session['usuario_id'] = usuario['id']
            session['admin'] = usuario['admin']
            session['nome'] = nome
            
            if usuario['admin']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Nome de usuário ou senha incorretos')
    
    return render_template('login.html')

# Rota de registro
@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        
        if registrar_usuario(nome, senha):
            return redirect(url_for('login'))
        else:
            return render_template('registrar.html', error='Nome de usuário já existe')
    
    return render_template('registrar.html')

# Rota de logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Middleware para verificar autenticação
def verificar_autenticacao():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

# Middleware para verificar permissão de admin
def verificar_admin():
    if 'usuario_id' not in session or not session.get('admin'):
        return redirect(url_for('login'))

# Rota principal
@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    produtos = carregar_produtos_usuario(session['usuario_id'], apenas_nao_enviados=True)
    return render_template('index.html', produtos=produtos)

# Rota para painel de administração
@app.route('/admin')
def admin_dashboard():
    if 'usuario_id' not in session or not session.get('admin'):
        return redirect(url_for('login'))
    
    listas = carregar_todas_listas_enviadas()
    return render_template('admin.html', listas=listas)

# Rota para pesquisar produtos
@app.route('/pesquisar', methods=['GET'])
def pesquisar():
    if 'usuario_id' not in session or not session.get('admin'):
        return redirect(url_for('login'))
    
    termo = request.args.get('termo', '')
    if termo:
        produtos = pesquisar_produtos(termo)
    else:
        produtos = []
    
    return render_template('pesquisa.html', produtos=produtos, termo=termo)

# Rota para validar lista
@app.route('/validar_lista', methods=['POST'])
def validar_lista_route():
    if 'usuario_id' not in session or not session.get('admin'):
        return redirect(url_for('login'))
    
    data_envio = request.form.get('data_envio')
    nome_usuario = request.form.get('nome_usuario')
    
    if validar_lista(data_envio, nome_usuario, session['usuario_id']):
        flash('Lista validada com sucesso!', 'success')
    else:
        flash('Erro ao validar lista', 'error')
    
    return redirect(url_for('admin_dashboard'))

# API para buscar produto por EAN
@app.route('/api/buscar-produto', methods=['GET'])
def api_buscar_produto():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autenticado"}), 401
    
    ean = request.args.get('ean')
    if not ean:
        return jsonify({"error": "EAN não fornecido"}), 400
    
    # Primeiro, verificar se o produto já existe no banco de dados local
    produto_local = buscar_produto_local(ean, session['usuario_id'])
    if produto_local:
        return jsonify({
            "success": True,
            "data": produto_local,
            "message": "Produto encontrado no banco de dados local."
        })
    
    # Se não existir localmente, buscar online
    resultado = buscar_produto_online(ean)
    
    # Registrar a consulta do usuário
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Registrar que o usuário consultou este produto
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Consulta registrada: Usuário ID {session['usuario_id']} consultou produto {ean}")
        
        conn.close()
    except Exception as e:
        print(f"Erro ao registrar consulta: {str(e)}")
    
    return jsonify(resultado)

# API para adicionar produto
@app.route('/api/produtos', methods=['POST'])
def api_adicionar_produto():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autenticado"}), 401
    
    data = request.json
    
    # Validar dados
    if not data.get('ean') or not data.get('nome') or not data.get('quantidade'):
        return jsonify({"error": "Dados incompletos"}), 400
    
    # Adicionar timestamp
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Salvar produto
    try:
        salvar_produto(data, session['usuario_id'])
        return jsonify({"success": True, "message": "Produto adicionado com sucesso"})
    except Exception as e:
        return jsonify({"error": f"Erro ao adicionar produto: {str(e)}"}), 500

# API para excluir produto
@app.route('/api/produtos/<int:produto_id>', methods=['DELETE'])
def api_excluir_produto(produto_id):
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        excluir_produto(produto_id, session['usuario_id'])
        return jsonify({"success": True, "message": "Produto excluído com sucesso"})
    except Exception as e:
        return jsonify({"error": f"Erro ao excluir produto: {str(e)}"}), 500

# API para enviar lista
@app.route('/api/enviar_lista', methods=['POST'])
def api_enviar_lista():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        data_envio = enviar_lista_produtos(session['usuario_id'])
        return jsonify({
            "success": True, 
            "message": "Lista enviada com sucesso", 
            "data_envio": data_envio
        })
    except Exception as e:
        return jsonify({"error": f"Erro ao enviar lista: {str(e)}"}), 500

# API para listar produtos
@app.route('/api/produtos', methods=['GET'])
def api_listar_produtos():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        produtos = carregar_produtos_usuario(session['usuario_id'], apenas_nao_enviados=True)
        return jsonify(produtos)
    except Exception as e:
        return jsonify({"error": f"Erro ao listar produtos: {str(e)}"}), 500

# Rota para exportar para Excel
@app.route('/api/export')
def exportar_excel():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obter produtos do usuário
        produtos = carregar_produtos_usuario(session['usuario_id'])
        
        if not produtos:
            flash('Não há produtos para exportar', 'error')
            return redirect(url_for('index'))
        
        # Criar DataFrame
        df = pd.DataFrame(produtos)
        
        # Selecionar colunas relevantes
        colunas = ['ean', 'nome', 'quantidade']
        df_export = df[colunas].copy()
        
        # Renomear colunas
        df_export.columns = ['EAN', 'DESCRIÇÃO', 'QUANTIDADE']
        
        # Criar buffer para o arquivo Excel
        output = io.BytesIO()
        
        # Criar arquivo Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Produtos')
        
        output.seek(0)
        
        # Gerar nome do arquivo com nome do usuário e timestamp no formato solicitado
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"produtos_{session['nome']}_{timestamp}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Erro ao exportar para Excel: {str(e)}', 'error')
        return redirect(url_for('index'))

# Inicializar o banco de dados na inicialização da aplicação
init_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
