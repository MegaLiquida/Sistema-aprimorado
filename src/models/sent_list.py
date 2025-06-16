from src.models.database import db
from datetime import datetime
import json

class SentList(db.Model):
    __tablename__ = 'listas_enviadas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    enviado = db.Column(db.Integer, default=0)
    data_envio = db.Column(db.DateTime)
    validado = db.Column(db.Integer, default=0)
    validador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    data_validacao = db.Column(db.DateTime)
    responsavel_id = db.Column(db.Integer, db.ForeignKey('responsaveis.id'))
    responsavel_pin = db.Column(db.String(10))
    produtos_json = db.Column(db.Text)  # JSON dos produtos para compatibilidade
    observacoes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pendente')  # 'pendente', 'validada', 'rejeitada'
    
    # Relacionamentos
    usuario = db.relationship('User', foreign_keys=[usuario_id], backref='listas_criadas')
    validador = db.relationship('User', foreign_keys=[validador_id], backref='listas_validadas')
    # responsavel = db.relationship('Responsible', backref='listas_responsavel')
    
    def __repr__(self):
        return f'<SentList {self.id} - User {self.usuario_id} ({self.status})>'
    
    def get_status_display(self):
        """Retorna nome amigável do status"""
        status_map = {
            'pendente': 'Pendente',
            'validada': 'Validada',
            'rejeitada': 'Rejeitada'
        }
        return status_map.get(self.status, 'Desconhecido')
    
    def get_status_class(self):
        """Retorna classe CSS para o status"""
        status_classes = {
            'pendente': 'warning',
            'validada': 'success',
            'rejeitada': 'danger'
        }
        return status_classes.get(self.status, 'secondary')
    
    def get_produtos_from_json(self):
        """Retorna produtos do JSON (para compatibilidade)"""
        if self.produtos_json:
            try:
                return json.loads(self.produtos_json)
            except:
                return []
        return []
    
    def set_produtos_json(self, produtos_list):
        """Define produtos no JSON"""
        self.produtos_json = json.dumps(produtos_list)
    
    def get_total_produtos(self):
        """Retorna total de produtos na lista"""
        if hasattr(self, 'produtos') and self.produtos:
            return len(self.produtos)
        produtos_json = self.get_produtos_from_json()
        return len(produtos_json)
    
    def get_total_quantidade(self):
        """Retorna quantidade total de itens"""
        total = 0
        if hasattr(self, 'produtos') and self.produtos:
            total = sum(p.quantidade for p in self.produtos)
        else:
            produtos_json = self.get_produtos_from_json()
            total = sum(p.get('quantidade', 0) for p in produtos_json)
        return total

