from datetime import datetime
import random
import string

def hora_mocambique():
    # Retorna hora no formato HH:MM - DD/MM/AAAA
    return datetime.now().strftime("%H:%M - %d/%m/%Y")

def gerar_id(tamanho=6):
    # Gera um ID único curto para o pedido (ex: R8X2A1)
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(tamanho))