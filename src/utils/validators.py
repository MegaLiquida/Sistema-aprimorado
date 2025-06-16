# Utilitários para validação de dados

import re
from datetime import datetime

def validar_ean(ean):
    """Valida formato do código EAN"""
    if not ean:
        return False, "EAN não pode estar vazio"
    
    # Remover espaços e caracteres especiais
    ean_clean = re.sub(r'[^0-9]', '', str(ean))
    
    # Verificar comprimento (EAN-8, EAN-13, UPC-A)
    if len(ean_clean) not in [8, 12, 13]:
        return False, f"EAN deve ter 8, 12 ou 13 dígitos. Encontrado: {len(ean_clean)}"
    
    # Verificar se contém apenas números
    if not ean_clean.isdigit():
        return False, "EAN deve conter apenas números"
    
    # Validar dígito verificador para EAN-13
    if len(ean_clean) == 13:
        if not validar_digito_verificador_ean13(ean_clean):
            return False, "Dígito verificador do EAN-13 inválido"
    
    return True, ean_clean

def validar_digito_verificador_ean13(ean):
    """Valida dígito verificador do EAN-13"""
    if len(ean) != 13:
        return False
    
    # Calcular dígito verificador
    soma = 0
    for i, digito in enumerate(ean[:-1]):
        peso = 1 if i % 2 == 0 else 3
        soma += int(digito) * peso
    
    digito_calculado = (10 - (soma % 10)) % 10
    digito_informado = int(ean[-1])
    
    return digito_calculado == digito_informado

def validar_pin(pin):
    """Valida formato do PIN"""
    if not pin:
        return False, "PIN não pode estar vazio"
    
    pin_clean = str(pin).strip()
    
    if len(pin_clean) != 4:
        return False, "PIN deve ter exatamente 4 dígitos"
    
    if not pin_clean.isdigit():
        return False, "PIN deve conter apenas números"
    
    return True, pin_clean

def validar_nome_usuario(nome):
    """Valida nome de usuário"""
    if not nome:
        return False, "Nome de usuário não pode estar vazio"
    
    nome_clean = nome.strip()
    
    if len(nome_clean) < 3:
        return False, "Nome de usuário deve ter pelo menos 3 caracteres"
    
    if len(nome_clean) > 50:
        return False, "Nome de usuário deve ter no máximo 50 caracteres"
    
    # Verificar caracteres permitidos (letras, números, underscore, hífen)
    if not re.match(r'^[a-zA-Z0-9_-]+$', nome_clean):
        return False, "Nome de usuário pode conter apenas letras, números, _ e -"
    
    return True, nome_clean

def validar_senha(senha):
    """Valida senha"""
    if not senha:
        return False, "Senha não pode estar vazia"
    
    if len(senha) < 4:
        return False, "Senha deve ter pelo menos 4 caracteres"
    
    if len(senha) > 100:
        return False, "Senha deve ter no máximo 100 caracteres"
    
    return True, senha

def validar_tipo_usuario(tipo):
    """Valida tipo de usuário"""
    tipos_validos = ['ean', 'listas', 'admin']
    
    if tipo not in tipos_validos:
        return False, f"Tipo de usuário deve ser um de: {', '.join(tipos_validos)}"
    
    return True, tipo

def validar_produto_data(data):
    """Valida dados de produto"""
    erros = []
    
    # Validar EAN
    ean_valido, ean_msg = validar_ean(data.get('ean'))
    if not ean_valido:
        erros.append(f"EAN: {ean_msg}")
    
    # Validar nome
    nome = data.get('nome', '').strip()
    if not nome:
        erros.append("Nome do produto é obrigatório")
    elif len(nome) > 200:
        erros.append("Nome do produto deve ter no máximo 200 caracteres")
    
    # Validar quantidade
    try:
        quantidade = int(data.get('quantidade', 0))
        if quantidade <= 0:
            erros.append("Quantidade deve ser maior que zero")
    except (ValueError, TypeError):
        erros.append("Quantidade deve ser um número válido")
    
    # Validar campos opcionais
    for campo in ['cor', 'voltagem', 'modelo']:
        valor = data.get(campo, '')
        if valor and len(valor) > 100:
            erros.append(f"{campo.capitalize()} deve ter no máximo 100 caracteres")
    
    return len(erros) == 0, erros

def formatar_data_brasileira(data):
    """Formata data no padrão brasileiro"""
    if not data:
        return ""
    
    if isinstance(data, str):
        try:
            data = datetime.fromisoformat(data.replace('Z', '+00:00'))
        except:
            return data
    
    return data.strftime("%d/%m/%Y %H:%M")

def formatar_ean_display(ean):
    """Formata EAN para exibição"""
    if not ean:
        return ""
    
    ean_str = str(ean)
    
    # Adicionar espaços para melhor legibilidade
    if len(ean_str) == 13:
        return f"{ean_str[:1]} {ean_str[1:7]} {ean_str[7:12]} {ean_str[12:]}"
    elif len(ean_str) == 12:
        return f"{ean_str[:6]} {ean_str[6:]}"
    elif len(ean_str) == 8:
        return f"{ean_str[:4]} {ean_str[4:]}"
    
    return ean_str

