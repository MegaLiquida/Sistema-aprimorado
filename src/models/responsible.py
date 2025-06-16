from src.models.database import db
from datetime import datetime

class Responsible(db.Model):
    __tablename__ = 'responsaveis'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    pin = db.Column(db.String(10), nullable=False)
    ativo = db.Column(db.Integer, default=1)
    ultimo_acesso = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Responsible {self.nome} ({"Ativo" if self.ativo else "Inativo"})>'
    
    def is_active(self):
        """Verifica se o responsável está ativo"""
        return self.ativo == 1
    
    def update_last_access(self):
        """Atualiza o último acesso"""
        self.ultimo_acesso = datetime.utcnow()
    
    def verify_pin(self, pin_input):
        """Verifica se o PIN está correto"""
        return self.pin == pin_input and self.is_active()

