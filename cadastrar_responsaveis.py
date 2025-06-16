# Script para cadastrar responsáveis padrão

from src.models.database import db
from src.models.responsible import Responsible

def cadastrar_responsaveis_padrao():
    """Cadastra os responsáveis padrão no sistema"""
    
    responsaveis_padrao = [
        {'nome': 'Liliane', 'pin': '1234'},
        {'nome': 'Rogerio', 'pin': '5678'},
        {'nome': 'Celso', 'pin': '9012'},
        {'nome': 'Marcos', 'pin': '3456'}
    ]
    
    for resp_data in responsaveis_padrao:
        # Verificar se já existe
        existing = Responsible.query.filter_by(nome=resp_data['nome']).first()
        if not existing:
            responsavel = Responsible(
                nome=resp_data['nome'],
                pin=resp_data['pin'],
                ativo=1
            )
            db.session.add(responsavel)
            print(f"Responsável {resp_data['nome']} cadastrado com PIN {resp_data['pin']}")
        else:
            print(f"Responsável {resp_data['nome']} já existe")
    
    db.session.commit()
    print("Cadastro de responsáveis concluído!")

if __name__ == '__main__':
    from src.main import app
    with app.app_context():
        cadastrar_responsaveis_padrao()

