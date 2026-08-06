import os

class Config:
    # ------------------------------------------------------
    # Informações da Loja
    # ------------------------------------------------------
    NOME_LOJA = os.getenv("NOME_LOJA", "Boutique Elegance")
    NUMERO_WHATSAPP = os.getenv("NUMERO_WHATSAPP", "258879131089")
    # Alias para compatibilidade caso algum template/serviço chame WHATSAPP_NUMBER
    WHATSAPP_NUMBER = NUMERO_WHATSAPP

    # ------------------------------------------------------
    # Credenciais Admin & Sessão
    # ------------------------------------------------------
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "loja_moda_secret_key_2026")

    # ------------------------------------------------------
    # Integração Google Sheets
    # ------------------------------------------------------
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
    GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
    
    # Nomes das Abas na Planilha
    SHEET_PRODUCTS = "Produtos"
    SHEET_ORDERS = "Pedidos"
    # Alias caso o catalog_service.py procure por SHEET_CATALOG
    SHEET_CATALOG = SHEET_PRODUCTS

    # ------------------------------------------------------
    # Estilo Visual (Dark Theme / Dourado Elegante)
    # ------------------------------------------------------
    COR_PRIMARIA = "#111827"   # Fundo Escuro
    COR_SECUNDARIA = "#f59e0b" # Dourado/Âmbar
    COR_CARD = "#1f2937"       # Cartões dos Produtos
