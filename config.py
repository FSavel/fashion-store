import os

class Config:
    # Informações da Loja
    NOME_LOJA = os.getenv("NOME_LOJA", "Boutique Elegance")
    NUMERO_WHATSAPP = os.getenv("NUMERO_WHATSAPP", "258840000000")  # Coloca o número com indicativo sem +
    
    # Credenciais Admin
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "moda2026")

    # Identificadores das Abas do Google Sheets
    SHEET_PRODUCTS = "Produtos"
    SHEET_ORDERS = "Pedidos"

    # Estilo Visual (Dark Theme / Dourado Elegante)
    COR_PRIMARIA = "#111827"   # Fundo Escuro
    COR_SECUNDARIA = "#f59e0b" # Dourado/Âmbar
    COR_CARD = "#1f2937"       # Cartões dos Produtos