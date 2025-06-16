# Script para migrar banco de dados - Adicionar campo usuario_id

import os
import sys
import sqlite3

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.database import db
from src.models.user import User
from src.models.product import Product

def migrar_banco():
    """Migra o banco de dados para adicionar o campo usuario_id na tabela produtos"""
    
    # Caminho do banco de dados
    db_path = os.path.join(os.path.dirname(__file__), 'src', 'database', 'ean_system.db')
    
    try:
        # Conectar ao banco SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a coluna usuario_id já existe
        cursor.execute("PRAGMA table_info(produtos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'usuario_id' not in columns:
            print("Adicionando coluna usuario_id à tabela produtos...")
            
            # Buscar o primeiro usuário admin para usar como padrão
            cursor.execute("SELECT id FROM usuarios WHERE admin = 1 LIMIT 1")
            admin_user = cursor.fetchone()
            
            if admin_user:
                admin_id = admin_user[0]
                
                # Adicionar a coluna usuario_id com valor padrão
                cursor.execute(f"ALTER TABLE produtos ADD COLUMN usuario_id INTEGER DEFAULT {admin_id}")
                
                # Atualizar todos os produtos existentes para pertencer ao admin
                cursor.execute(f"UPDATE produtos SET usuario_id = {admin_id} WHERE usuario_id IS NULL")
                
                print(f"Coluna usuario_id adicionada com sucesso! Produtos existentes atribuídos ao usuário admin (ID: {admin_id})")
            else:
                print("Erro: Nenhum usuário admin encontrado. Criando usuário admin padrão...")
                
                # Criar usuário admin padrão se não existir
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash('admin')
                
                cursor.execute("""
                    INSERT INTO usuarios (nome, senha_hash, admin, tipo_usuario) 
                    VALUES ('admin', ?, 1, 'admin')
                """, (password_hash,))
                
                admin_id = cursor.lastrowid
                
                # Adicionar a coluna usuario_id
                cursor.execute(f"ALTER TABLE produtos ADD COLUMN usuario_id INTEGER DEFAULT {admin_id}")
                cursor.execute(f"UPDATE produtos SET usuario_id = {admin_id} WHERE usuario_id IS NULL")
                
                print(f"Usuário admin criado e coluna usuario_id adicionada com sucesso!")
        else:
            print("Coluna usuario_id já existe na tabela produtos.")
        
        # Confirmar as alterações
        conn.commit()
        print("Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro durante a migração: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrar_banco()

