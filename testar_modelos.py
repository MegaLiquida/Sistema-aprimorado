# Teste das modificações no banco de dados

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.database import db
from src.models.user import User
from src.models.product import Product
from src.models.responsible import Responsible
from src.models.sent_list import SentList
from src.models.produto_lista import ProdutoLista

def testar_modelos():
    """Testa se todos os modelos estão funcionando corretamente"""
    
    print("=== TESTE DOS MODELOS ATUALIZADOS ===")
    
    # Testar modelo User
    print("\n1. Testando modelo User...")
    try:
        # Buscar usuário admin
        admin = User.query.filter_by(nome='admin').first()
        if admin:
            print(f"   ✅ Usuário admin encontrado: {admin}")
            print(f"   - Tipo: {admin.tipo_usuario}")
            print(f"   - É admin: {admin.is_admin()}")
            print(f"   - Pode acessar EAN: {admin.can_access_ean_panel()}")
            print(f"   - Pode acessar Listas: {admin.can_access_lists_panel()}")
            print(f"   - Tipo display: {admin.get_tipo_display()}")
        else:
            print("   ⚠️  Usuário admin não encontrado")
    except Exception as e:
        print(f"   ❌ Erro no modelo User: {e}")
    
    # Testar modelo Responsible
    print("\n2. Testando modelo Responsible...")
    try:
        responsaveis = Responsible.query.all()
        print(f"   ✅ {len(responsaveis)} responsáveis encontrados:")
        for resp in responsaveis:
            print(f"   - {resp}")
            print(f"     Ativo: {resp.is_active()}")
            print(f"     PIN válido (teste): {resp.verify_pin(resp.pin)}")
    except Exception as e:
        print(f"   ❌ Erro no modelo Responsible: {e}")
    
    # Testar modelo SentList
    print("\n3. Testando modelo SentList...")
    try:
        listas = SentList.query.all()
        print(f"   ✅ {len(listas)} listas encontradas:")
        for lista in listas:
            print(f"   - {lista}")
            print(f"     Status display: {lista.get_status_display()}")
            print(f"     Status class: {lista.get_status_class()}")
            print(f"     Total produtos: {lista.get_total_produtos()}")
    except Exception as e:
        print(f"   ❌ Erro no modelo SentList: {e}")
    
    # Testar modelo ProdutoLista
    print("\n4. Testando modelo ProdutoLista...")
    try:
        produtos_lista = ProdutoLista.query.all()
        print(f"   ✅ {len(produtos_lista)} produtos em listas encontrados:")
        for produto in produtos_lista:
            print(f"   - {produto}")
    except Exception as e:
        print(f"   ❌ Erro no modelo ProdutoLista: {e}")
    
    # Testar criação de dados de exemplo
    print("\n5. Testando criação de dados de exemplo...")
    try:
        # Criar usuário de teste para listas
        usuario_teste = User.query.filter_by(nome='teste_listas').first()
        if not usuario_teste:
            from werkzeug.security import generate_password_hash
            usuario_teste = User(
                nome='teste_listas',
                senha_hash=generate_password_hash('123456'),
                tipo_usuario='listas'
            )
            db.session.add(usuario_teste)
            db.session.commit()
            print("   ✅ Usuário de teste criado")
        else:
            print("   ⚠️  Usuário de teste já existe")
        
        # Criar lista de exemplo
        lista_exemplo = SentList.query.filter_by(usuario_id=usuario_teste.id).first()
        if not lista_exemplo:
            lista_exemplo = SentList(
                usuario_id=usuario_teste.id,
                status='pendente',
                observacoes='Lista de teste criada automaticamente'
            )
            db.session.add(lista_exemplo)
            db.session.commit()
            
            # Adicionar produtos à lista
            produtos_exemplo = [
                {
                    'ean': '7891234567890',
                    'nome': 'Produto Teste 1',
                    'cor': 'Azul',
                    'voltagem': '220V',
                    'modelo': 'TEST-001',
                    'quantidade': 5
                },
                {
                    'ean': '7891234567891',
                    'nome': 'Produto Teste 2',
                    'cor': 'Vermelho',
                    'voltagem': '110V',
                    'modelo': 'TEST-002',
                    'quantidade': 3
                }
            ]
            
            for produto_data in produtos_exemplo:
                produto = ProdutoLista(
                    lista_id=lista_exemplo.id,
                    **produto_data
                )
                db.session.add(produto)
            
            db.session.commit()
            print("   ✅ Lista de exemplo criada com produtos")
        else:
            print("   ⚠️  Lista de exemplo já existe")
            
    except Exception as e:
        print(f"   ❌ Erro ao criar dados de exemplo: {e}")
    
    print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    # Configurar Flask app para teste
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'ean_system.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        testar_modelos()

