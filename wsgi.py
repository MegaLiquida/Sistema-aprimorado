import os
import sys

# Adiciona o diretório atual ao caminho Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa a aplicação Flask do módulo main.py dentro da pasta src
from src.main import app

# Necessário para o Gunicorn
application = app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
