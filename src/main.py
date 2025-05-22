import sys
import os
import sqlite3
from datetime import datetime
import io
import requests
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import pandas as pd
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'ean_app_secret_key'  # Chave para sessões

# Caminho para o banco de dados SQLite
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'produtos.db')

# Inicializar o banco de dados
def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        admin INTEGER DEFAULT 0
    )
    ''')
    
    # Tabela de produtos
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
    
    conn.commit()
    conn.close()

# Funções de autenticação
def registrar_usuario(nome, senha):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        senha_hash = generate_password_hash(senha)
        cursor.execute('INSERT INTO usuarios (nome, senha_hash) VALUES (?, ?)', (nome, senha_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Nome de usuário já existe
        return False
    finally:
        conn.close()

def verificar_usuario(nome, senha):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, senha_hash, admin FROM usuarios WHERE nome = ?', (nome,))
    usuario = cursor.fetchone()
    conn.close()
    
    if usuario and check_password_hash(usuario[1], senha):
        return {'id': usuario[0], 'admin': usuario[2]}
    return None

def obter_nome_usuario(usuario_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT nome FROM usuarios WHERE id = ?', (usuario_id,))
    usuario = cursor.fetchone()
    conn.close()
    
    return usuario[0] if usuario else None

# Funções de produtos
def carregar_produtos_usuario(usuario_id, apenas_nao_enviados=False):
    conn = sqlite3.connect(DB_FILE)
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
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Buscar produtos enviados junto com o nome do usuário e do validador (se houver)
    cursor.execute('''
    SELECT p.*, 
           u.nome as nome_usuario,
           v.nome as nome_validador
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
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Buscar produtos que correspondem ao termo de pesquisa (EAN ou palavra na descrição)
    cursor.execute('''
    SELECT p.*, 
           u.nome as nome_usuario,
           v.nome as nome_validador
    FROM produtos p 
    JOIN usuarios u ON p.usuario_id = u.id 
    LEFT JOIN usuarios v ON p.validador_id = v.id
    WHERE p.enviado = 1 
      AND (p.ean LIKE ? OR p.nome LIKE ? OR p.cor LIKE ? OR p.modelo LIKE ?)
    ORDER BY p.data_envio DESC
    ''', (f'%{termo_pesquisa}%', f'%{termo_pesquisa}%', f'%{termo_pesquisa}%', f'%{termo_pesquisa}%'))
    
    produtos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return produtos

def buscar_produto_local(ean, usuario_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM produtos WHERE ean = ? AND usuario_id = ? AND enviado = 0', (ean, usuario_id))
    produto = cursor.fetchone()
    conn.close()
    
    if produto:
        return dict(produto)
    return None

def salvar_produto(produto, usuario_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Verificar se o produto já existe para este usuário e não foi enviado
    cursor.execute('SELECT * FROM produtos WHERE ean = ? AND usuario_id = ? AND enviado = 0', 
                  (produto['ean'], usuario_id))
    existing = cursor.fetchone()
    
    if existing:
        # Atualizar quantidade
        cursor.execute('''
        UPDATE produtos 
        SET quantidade = quantidade + ?, 
            timestamp = ? 
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
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    data_envio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Marcar todos os produtos não enviados como enviados
    cursor.execute('''
    UPDATE produtos 
    SET enviado = 1, 
        data_envio = ? 
    WHERE usuario_id = ? AND enviado = 0
    ''', (data_envio, usuario_id))
    
    conn.commit()
    conn.close()
    
    return data_envio

def validar_lista(data_envio, nome_usuario, validador_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Obter o ID do usuário pelo nome
    cursor.execute('SELECT id FROM usuarios WHERE nome = ?', (nome_usuario,))
    usuario = cursor.fetchone()
    
    if not usuario:
        conn.close()
        return False
    
    usuario_id = usuario[0]
    data_validacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Marcar todos os produtos da lista como validados
    cursor.execute('''
    UPDATE produtos 
    SET validado = 1, 
        validador_id = ?,
        data_validacao = ? 
    WHERE usuario_id = ? AND data_envio = ? AND enviado = 1
    ''', (validador_id, data_validacao, usuario_id, data_envio))
    
    conn.commit()
    conn.close()
    
    return True

def excluir_produto(produto_id, usuario_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM produtos WHERE id = ? AND usuario_id = ? AND enviado = 0', 
                  (produto_id, usuario_id))
    
    conn.commit()
    conn.close()

# Função para buscar informações do produto por EAN online
def buscar_produto_online(ean):
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

# Rotas de autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        
        usuario = verificar_usuario(nome, senha)
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = nome
            session['admin'] = usuario['admin']
            
            if usuario['admin']:
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Nome de usuário ou senha incorretos')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        
        if registrar_usuario(nome, senha):
            flash('Usuário registrado com sucesso! Faça login para continuar.')
            return redirect(url_for('login'))
        else:
            flash('Nome de usuário já existe')
    
    return render_template('registro.html')

# Rotas da aplicação
@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    produtos = carregar_produtos_usuario(session['usuario_id'], apenas_nao_enviados=True)
    return render_template('index.html', produtos=produtos)

@app.route('/admin')
def admin_panel():
    if 'usuario_id' not in session or not session.get('admin'):
        return redirect(url_for('login'))
    
    termo_pesquisa = request.args.get('pesquisa', '')
    
    if termo_pesquisa:
        # Se houver termo de pesquisa, buscar produtos correspondentes
        produtos_encontrados = pesquisar_produtos(termo_pesquisa)
        
        # Agrupar produtos por data de envio e usuário
        listas_agrupadas = {}
        for produto in produtos_encontrados:
            chave = (produto['data_envio'], produto['nome_usuario'])
            if chave not in listas_agrupadas:
                listas_agrupadas[chave] = {
                    'produtos': [],
                    'validado': produto.get('validado', 0),
                    'nome_validador': produto.get('nome_validador', None),
                    'data_validacao': produto.get('data_validacao', None)
                }
            listas_agrupadas[chave]['produtos'].append(produto)
        
        return render_template('admin.html', listas_agrupadas=listas_agrupadas, termo_pesquisa=termo_pesquisa)
    else:
        # Se não houver pesquisa, mostrar todas as listas
        listas_enviadas = carregar_todas_listas_enviadas()
        
        # Agrupar produtos por data de envio e usuário
        listas_agrupadas = {}
        for produto in listas_enviadas:
            chave = (produto['data_envio'], produto['nome_usuario'])
            if chave not in listas_agrupadas:
                listas_agrupadas[chave] = {
                    'produtos': [],
                    'validado': produto.get('validado', 0),
                    'nome_validador': produto.get('nome_validador', None),
                    'data_validacao': produto.get('data_validacao', None)
                }
            listas_agrupadas[chave]['produtos'].append(produto)
        
        return render_template('admin.html', listas_agrupadas=listas_agrupadas, termo_pesquisa='')

@app.route('/api/buscar-produto', methods=['GET'])
def buscar_produto():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    ean = request.args.get('ean')
    if not ean:
        return jsonify({"error": "EAN não fornecido"}), 400
    
    # Primeiro, verificar se o produto já existe no banco de dados local
    produto_local = buscar_produto_local(ean, session['usuario_id'])
    if produto_local:
        return jsonify({
            "ean": produto_local['ean'],
            "nome": produto_local['nome'],
            "cor": produto_local['cor'],
            "voltagem": produto_local['voltagem'],
            "modelo": produto_local['modelo'],
            "quantidade": produto_local['quantidade'],
            "message": "Produto encontrado no banco de dados local."
        }), 200
    
    # Se não existir localmente, buscar online
    resultado = buscar_produto_online(ean)
    
    if resultado["success"]:
        produto_data = resultado["data"]
        
        # Extrair informações relevantes
        nome = produto_data.get("nome", f"Produto {ean}")
        marca = produto_data.get("marca", "")
        categoria = produto_data.get("categoria", "")
        
        # Retornar as informações obtidas
        return jsonify({
            "ean": ean,
            "nome": nome,
            "cor": "",
            "voltagem": "",
            "modelo": marca,
            "quantidade": 1,
            "message": resultado.get("message", "")
        }), 200
    else:
        return jsonify({
            "error": "Produto não encontrado",
            "ean": ean,
            "nome": f"Produto {ean}",
            "cor": "",
            "voltagem": "",
            "modelo": "",
            "quantidade": 1,
            "message": "Produto não encontrado. Por favor, preencha as informações manualmente."
        }), 200

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    produtos = carregar_produtos_usuario(session['usuario_id'], apenas_nao_enviados=True)
    return jsonify(produtos)

@app.route('/api/produtos', methods=['POST'])
def add_produto():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    data = request.json
    
    # Adicionar timestamp
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Salvar no banco de dados
    salvar_produto(data, session['usuario_id'])
    
    # Retornar os produtos atualizados
    produtos = carregar_produtos_usuario(session['usuario_id'], apenas_nao_enviados=True)
    return jsonify(produtos), 200

@app.route('/api/produtos/<int:produto_id>', methods=['DELETE'])
def delete_produto_route(produto_id):
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    excluir_produto(produto_id, session['usuario_id'])
    return jsonify({"message": "Produto removido com sucesso"}), 200

@app.route('/api/enviar-lista', methods=['POST'])
def enviar_lista():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    data_envio = enviar_lista_produtos(session['usuario_id'])
    return jsonify({"message": "Lista enviada com sucesso", "data_envio": data_envio}), 200

@app.route('/api/validar-lista', methods=['POST'])
def validar_lista_route():
    if 'usuario_id' not in session or not session.get('admin'):
        return jsonify({"error": "Não autorizado"}), 401
    
    data = request.json
    data_envio = data.get('data_envio')
    nome_usuario = data.get('nome_usuario')
    
    if not data_envio or not nome_usuario:
        return jsonify({"error": "Dados incompletos"}), 400
    
    if validar_lista(data_envio, nome_usuario, session['usuario_id']):
        return jsonify({"message": "Lista validada com sucesso", "validador": session['usuario_nome']}), 200
    else:
        return jsonify({"error": "Erro ao validar lista"}), 500

@app.route('/api/export', methods=['GET'])
def export_excel():
    if 'usuario_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    produtos = carregar_produtos_usuario(session['usuario_id'], apenas_nao_enviados=True)
    
    if not produtos:
        return jsonify({"error": "Não há produtos para exportar"}), 400
    
    # Criar DataFrame com os dados
    df = pd.DataFrame(produtos)
    
    # Selecionar e renomear colunas conforme solicitado pelo usuário
    df_export = df[['ean', 'nome', 'quantidade']].copy()
    df_export.columns = ['EAN', 'DESCRIÇÃO', 'QUANTIDADE']
    
    # Criar buffer para o arquivo Excel
    output = io.BytesIO()
    
    # Criar arquivo Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Produtos')
    
    output.seek(0)
    
    # Gerar nome do arquivo com timestamp
    filename = f"produtos_ean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        output, 
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5010, debug=True)
