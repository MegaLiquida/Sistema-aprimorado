from src.models.database import db

class User(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    admin = db.Column(db.Integer, default=0)
    tipo_usuario = db.Column(db.String(20), default='ean')  # 'ean', 'listas', 'admin'
    
    def __repr__(self):
        return f'<User {self.nome} ({self.tipo_usuario})>'
    
    def is_admin(self):
        """Verifica se o usuário é administrador"""
        return self.admin == 1 or self.tipo_usuario == 'admin'
    
    def can_access_ean_panel(self):
        """Verifica se pode acessar painel de consulta EAN"""
        return self.tipo_usuario in ['ean', 'admin'] or self.is_admin()
    
    def can_access_lists_panel(self):
        """Verifica se pode acessar painel de listas"""
        return self.tipo_usuario in ['listas', 'admin'] or self.is_admin()
    
    def get_tipo_display(self):
        """Retorna nome amigável do tipo de usuário"""
        tipos = {
            'ean': 'Consulta EAN',
            'listas': 'Painel de Listas',
            'admin': 'Administrador'
        }
        return tipos.get(self.tipo_usuario, 'Desconhecido')

