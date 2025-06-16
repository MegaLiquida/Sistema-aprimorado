from src.models.database import db

class ProdutoLista(db.Model):
    """Modelo para produtos dentro de uma lista enviada"""
    __tablename__ = 'produtos_lista'
    
    id = db.Column(db.Integer, primary_key=True)
    lista_id = db.Column(db.Integer, db.ForeignKey('listas_enviadas.id'), nullable=False)
    ean = db.Column(db.String(20), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    cor = db.Column(db.String(50))
    voltagem = db.Column(db.String(20))
    modelo = db.Column(db.String(100))
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    
    # Relacionamento com lista enviada
    lista = db.relationship('SentList', backref='produtos')
    
    def __repr__(self):
        return f'<ProdutoLista {self.ean} - {self.nome} (Lista: {self.lista_id})>'
    
    def to_dict(self):
        """Converte o produto para dicionário"""
        return {
            'id': self.id,
            'lista_id': self.lista_id,
            'ean': self.ean,
            'nome': self.nome,
            'cor': self.cor or '',
            'voltagem': self.voltagem or '',
            'modelo': self.modelo or '',
            'quantidade': self.quantidade
        }

