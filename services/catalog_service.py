import os
import json
import gspread
from google.oauth2.service_account import Credentials

# Âmbitos de permissão para aceder à API do Google Sheets e Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_google_client():
    """
    Autentica com a API do Google Sheets utilizando as credenciais JSON 
    passadas nas Variáveis de Ambiente.
    """
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    if not creds_json:
        # Se as credenciais ainda não estiverem configuradas, retorna None
        return None

    try:
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as e:
        print(f"Erro na autenticação do Google Sheets: {e}")
        return None

def get_spreadsheet():
    """
    Acede e abre a Folha de Cálculo principal usando o GOOGLE_SHEETS_ID.
    """
    client = get_google_client()
    sheet_id = os.environ.get("GOOGLE_SHEETS_ID")
    
    if not client or not sheet_id:
        return None

    try:
        return client.open_by_key(sheet_id)
    except Exception as e:
        print(f"Erro ao abrir a folha de cálculo: {e}")
        return None

def load_catalog():
    """
    Carrega todos os produtos ativos da aba 'Produtos'.
    Caso a folha não esteja ligada (ex: em desenvolvimento local), 
    retorna um catálogo de exemplo (Mock Data).
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
        # Dados de teste para poderes navegar no site mesmo antes das 12h
        return [
            {
                "id": "1",
                "categoria": "Vestidos",
                "nome": "Vestido Floral de Verão",
                "descricao": "Vestido leve e elegante para eventos casuais.",
                "preco": "2500",
                "fotos": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=500",
                "tamanhos": "S, M, L",
                "cores": "Preto, Vermelho",
                "disponivel": "SIM"
            },
            {
                "id": "2",
                "categoria": "Calças",
                "nome": "Calça Jeans High Waist",
                "descricao": "Corte moderno com excelente caimento.",
                "preco": "1800",
                "fotos": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500",
                "tamanhos": "38, 40, 42",
                "cores": "Azul Claro, Azul Escuro",
                "disponivel": "SIM"
            }
        ]

    try:
        sheet = spreadsheet.worksheet("Produtos")
        records = sheet.get_all_records()
        
        # Filtra apenas os produtos marcados como disponíveis
        produtos_ativos = []
        for r in records:
            disp = str(r.get("disponivel", "")).strip().upper()
            if disp in ["SIM", "TRUE", "1", "VERDADEIRO"]:
                produtos_ativos.append(r)
                
        return produtos_ativos
    except Exception as e:
        print(f"Erro ao carregar o catálogo de produtos: {e}")
        return []

def add_order(sheet_name, nome_cliente, contacto, cart_items, data_hora):
    """
    Regista um novo pedido efetuado pelo cliente na aba 'Pedidos'.
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
        print("Aviso: Pedido simulado com sucesso (Folha Google não ligada).")
        return True

    try:
        sheet = spreadsheet.worksheet(sheet_name)
        
        # Formatação do resumo das peças escolhidas
        resumo_pedido = []
        total_geral = 0

        for item in cart_items:
            nome = item.get("nome", "Produto")
            qtd = item.get("quantidade", 1)
            preco = float(item.get("preco", 0))
            tamanho = item.get("tamanho", "N/A")
            cor = item.get("cor", "N/A")
            
            subtotal = preco * qtd
            total_geral += subtotal
            
            resumo_pedido.append(f"{qtd}x {nome} (Tam: {tamanho}, Cor: {cor}) - {subtotal:.2f} MT")

        pedido_texto = "\n".join(resumo_pedido)
        
        # Importação do gerador de ID único curto
        from utils.helpers import gerar_id
        novo_id = gerar_id()
        
        # Adiciona uma nova linha no Google Sheets
        sheet.append_row([
            novo_id,
            nome_cliente,
            contacto,
            pedido_texto,
            f"{total_geral:.2f} MT",
            data_hora,
            "Pendente"
        ])
        return True
    except Exception as e:
        print(f"Erro ao registar pedido no Google Sheets: {e}")
        return False

def get_orders(sheet_name):
    """
    Lê a lista completa de pedidos da aba 'Pedidos' para ser exibida no Painel Admin.
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
        return []

    try:
        sheet = spreadsheet.worksheet(sheet_name)
        return sheet.get_all_records()
    except Exception as e:
        print(f"Erro ao procurar lista de pedidos: {e}")
        return []