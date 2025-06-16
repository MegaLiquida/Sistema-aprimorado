from src.models.database import db

class Product(db.Model):
    __tablename__ = 'produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    ean = db.Column(db.String(20), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    cor = db.Column(db.String(50))
    voltagem = db.Column(db.String(20))
    modelo = db.Column(db.String(100))
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # Relacionamento com usuário
    usuario = db.relationship('User', backref='produtos')
    
    def __repr__(self):
        return f'<Product {self.ean} - {self.nome} (User: {self.usuario_id})>'

