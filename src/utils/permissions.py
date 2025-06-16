# Utilitários para controle de permissões

from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    """Decorator para exigir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator para exigir privilégios de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        if not session.get('is_admin'):
            flash('Acesso negado. Privilégios de administrador necessários.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def ean_access_required(f):
    """Decorator para exigir acesso ao painel EAN"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        # Importar aqui para evitar import circular
        from src.models.user import User
        user = User.query.get(session['user_id'])
        
        if not user or not user.can_access_ean_panel():
            flash('Acesso negado. Você não tem permissão para acessar o painel EAN.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def lists_access_required(f):
    """Decorator para exigir acesso ao painel de listas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        # Importar aqui para evitar import circular
        from src.models.user import User
        user = User.query.get(session['user_id'])
        
        if not user or not user.can_access_lists_panel():
            flash('Acesso negado. Você não tem permissão para acessar o painel de listas.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Retorna o usuário atual da sessão"""
    if 'user_id' not in session:
        return None
    
    from src.models.user import User
    return User.query.get(session['user_id'])

def update_session_user_data(user):
    """Atualiza dados do usuário na sessão"""
    session['username'] = user.nome
    session['is_admin'] = user.is_admin()
    session['tipo_usuario'] = user.tipo_usuario
    session['can_access_ean'] = user.can_access_ean_panel()
    session['can_access_lists'] = user.can_access_lists_panel()

