from src.main import app, db
from src.models.user import User
from src.models.responsible import Responsible
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    # Verificar se admin já existe
    admin_user = User.query.filter_by(nome='admin').first()
    if not admin_user:
        # Criar usuário administrador padrão
        admin_hash = generate_password_hash('admin')
        admin = User(nome='admin', senha_hash=admin_hash, admin=1)
        db.session.add(admin)
    
    # Verificar se responsáveis padrão existem
    if Responsible.query.count() == 0:
        # Criar responsáveis padrão
        responsaveis = [
            Responsible(nome='Liliane', pin='5584'),
            Responsible(nome='Rogerio', pin='9841'),
            Responsible(nome='Celso', pin='2122'),
            Responsible(nome='Marcos', pin='6231')
        ]
        
        for resp in responsaveis:
            db.session.add(resp)
    
    db.session.commit()
    print("Banco de dados inicializado com sucesso!")

