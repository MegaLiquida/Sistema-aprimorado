# Script de Migração do Banco de Dados - Fase 1
# Adiciona novas funcionalidades ao sistema EAN

import sqlite3
import os
from datetime import datetime

def executar_migracao():
    """Executa as migrações necessárias no banco de dados"""
    
    # Caminho do banco de dados
    db_path = os.path.join(os.path.dirname(__file__), 'src', 'database', 'ean_system.db')
    
    print(f"Iniciando migração do banco de dados: {db_path}")
    
    try:
        # Conectar ao banco
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Conexão estabelecida com sucesso!")
        
        # 1. Adicionar campo tipo_usuario na tabela usuarios
        print("1. Adicionando campo tipo_usuario na tabela usuarios...")
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN tipo_usuario TEXT DEFAULT 'ean'")
            print("   ✅ Campo tipo_usuario adicionado com sucesso!")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⚠️  Campo tipo_usuario já existe, pulando...")
            else:
                raise e
        
        # 2. Expandir tabela listas_enviadas
        print("2. Expandindo tabela listas_enviadas...")
        
        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='listas_enviadas'")
        if not cursor.fetchone():
            print("   Criando tabela listas_enviadas...")
            cursor.execute("""
                CREATE TABLE listas_enviadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    enviado INTEGER DEFAULT 0,
                    data_envio TIMESTAMP,
                    validado INTEGER DEFAULT 0,
                    validador_id INTEGER,
                    data_validacao TIMESTAMP,
                    responsavel_id INTEGER,
                    responsavel_pin TEXT,
                    produtos_json TEXT,
                    observacoes TEXT,
                    status TEXT DEFAULT 'pendente',
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
                    FOREIGN KEY (validador_id) REFERENCES usuarios (id),
                    FOREIGN KEY (responsavel_id) REFERENCES responsaveis (id)
                )
            """)
            print("   ✅ Tabela listas_enviadas criada com sucesso!")
        else:
            # Adicionar novos campos se não existirem
            try:
                cursor.execute("ALTER TABLE listas_enviadas ADD COLUMN produtos_json TEXT")
                print("   ✅ Campo produtos_json adicionado!")
            except sqlite3.OperationalError:
                print("   ⚠️  Campo produtos_json já existe, pulando...")
            
            try:
                cursor.execute("ALTER TABLE listas_enviadas ADD COLUMN observacoes TEXT")
                print("   ✅ Campo observacoes adicionado!")
            except sqlite3.OperationalError:
                print("   ⚠️  Campo observacoes já existe, pulando...")
            
            try:
                cursor.execute("ALTER TABLE listas_enviadas ADD COLUMN status TEXT DEFAULT 'pendente'")
                print("   ✅ Campo status adicionado!")
            except sqlite3.OperationalError:
                print("   ⚠️  Campo status já existe, pulando...")
        
        # 3. Criar tabela produtos_lista
        print("3. Criando tabela produtos_lista...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='produtos_lista'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE produtos_lista (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lista_id INTEGER NOT NULL,
                    ean TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    cor TEXT,
                    voltagem TEXT,
                    modelo TEXT,
                    quantidade INTEGER NOT NULL,
                    FOREIGN KEY (lista_id) REFERENCES listas_enviadas (id)
                )
            """)
            print("   ✅ Tabela produtos_lista criada com sucesso!")
        else:
            print("   ⚠️  Tabela produtos_lista já existe, pulando...")
        
        # 4. Atualizar tabela responsaveis
        print("4. Atualizando tabela responsaveis...")
        try:
            cursor.execute("ALTER TABLE responsaveis ADD COLUMN ativo INTEGER DEFAULT 1")
            print("   ✅ Campo ativo adicionado!")
        except sqlite3.OperationalError:
            print("   ⚠️  Campo ativo já existe, pulando...")
        
        try:
            cursor.execute("ALTER TABLE responsaveis ADD COLUMN ultimo_acesso TIMESTAMP")
            print("   ✅ Campo ultimo_acesso adicionado!")
        except sqlite3.OperationalError:
            print("   ⚠️  Campo ultimo_acesso já existe, pulando...")
        
        # 5. Criar índices para melhor performance
        print("5. Criando índices para melhor performance...")
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo_usuario)",
            "CREATE INDEX IF NOT EXISTS idx_listas_usuario ON listas_enviadas(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_listas_status ON listas_enviadas(status)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_lista ON produtos_lista(lista_id)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_ean ON produtos_lista(ean)"
        ]
        
        for indice in indices:
            cursor.execute(indice)
            print(f"   ✅ Índice criado: {indice.split('idx_')[1].split(' ')[0]}")
        
        # 6. Atualizar usuários existentes para tipo 'ean' se não especificado
        print("6. Atualizando usuários existentes...")
        cursor.execute("UPDATE usuarios SET tipo_usuario = 'ean' WHERE tipo_usuario IS NULL OR tipo_usuario = ''")
        usuarios_atualizados = cursor.rowcount
        print(f"   ✅ {usuarios_atualizados} usuários atualizados para tipo 'ean'")
        
        # 7. Verificar estrutura final das tabelas
        print("7. Verificando estrutura final das tabelas...")
        
        tabelas = ['usuarios', 'listas_enviadas', 'produtos_lista', 'responsaveis']
        for tabela in tabelas:
            cursor.execute(f"PRAGMA table_info({tabela})")
            colunas = cursor.fetchall()
            print(f"   📋 Tabela {tabela}: {len(colunas)} colunas")
            for coluna in colunas:
                print(f"      - {coluna[1]} ({coluna[2]})")
        
        # Commit das mudanças
        conn.commit()
        print("\n✅ Migração concluída com sucesso!")
        
        # Estatísticas finais
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total_produtos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM responsaveis")
        total_responsaveis = cursor.fetchone()[0]
        
        print(f"\n📊 Estatísticas do banco:")
        print(f"   - Usuários: {total_usuarios}")
        print(f"   - Produtos: {total_produtos}")
        print(f"   - Responsáveis: {total_responsaveis}")
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {str(e)}")
        conn.rollback()
        raise e
    
    finally:
        conn.close()
        print("Conexão com banco de dados fechada.")

if __name__ == "__main__":
    print("=== MIGRAÇÃO DO BANCO DE DADOS - FASE 1 ===")
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)
    
    executar_migracao()
    
    print("=" * 50)
    print("Migração finalizada!")

