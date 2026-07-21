import os
import json
import uuid
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

# ======================================================
# LEITURA DO CATÁLOGO
# ======================================================
def load_catalog():
    """
    Carrega todos os produtos ativos da aba 'Produtos'.
    Caso a folha não esteja ligada, retorna dados de teste.
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
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
        
        produtos_ativos = []
        for r in records:
            disp = str(r.get("disponivel", "")).strip().upper()
            if disp in ["SIM", "TRUE", "1", "VERDADEIRO"]:
                produtos_ativos.append(r)
                
        return produtos_ativos
    except Exception as e:
        print(f"Erro ao carregar o catálogo de produtos: {e}")
        return []

# ======================================================
# GESTÃO DE PRODUTOS (ADMIN)
# ======================================================
def add_product(produto):
    """
    Adiciona um novo produto à aba 'Produtos' do Google Sheets.
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
        print("Aviso: Produto simulado com sucesso (Google Sheets não configurado).")
        return True

    try:
        sheet = spreadsheet.worksheet("Produtos")
        
        novo_id = str(uuid.uuid4())[:8]  # Gera um ID curto de 8 caracteres
        
        linha = [
            novo_id,
            produto.get("categoria", "Geral"),
            produto.get("nome", ""),
            produto.get("descricao", ""),
            produto.get("preco", "0"),
            produto.get("fotos", ""),
            produto.get("tamanhos", ""),
            produto.get("cores", ""),
            "SIM"  # Disponível por defeito
        ]
        
        sheet.append_row(linha)
        return True
    except Exception as e:
        print(f"Erro ao adicionar produto no Google Sheets: {e}")
        return False

def delete_product(produto_id):
    """
    Procura o produto pelo ID na aba 'Produtos' e elimina a linha.
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
        print("Aviso: Remoção simulada com sucesso.")
        return True

    try:
        sheet = spreadsheet.worksheet("Produtos")
        records = sheet.get_all_records()
        
        # Procura a linha correspondente (ajusta +2 para compensar o cabeçalho e índice 1)
        for index, row in enumerate(records):
            if str(row.get("id")) == str(produto_id):
                sheet.delete_rows(index + 2)
                return True
                
        return False
    except Exception as e:
        print(f"Erro ao eliminar produto no Google Sheets: {e}")
        return False

# ======================================================
# GESTÃO DE PEDIDOS
# ======================================================
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
        
        resumo_pedido = []
        total_geral = 0

        for item in cart_items:
            nome = item.get("nome", "Produto")
            # Suporta tanto 'qtd' (do carrinho frontend) como 'quantidade'
            qtd = item.get("qtd") or item.get("quantidade") or 1
            preco = float(item.get("preco", 0))
            tamanho = item.get("tamanho", "N/A")
            cor = item.get("cor", "N/A")
            
            subtotal = preco * int(qtd)
            total_geral += subtotal
            
            resumo_pedido.append(f"{qtd}x {nome} (Tam: {tamanho}, Cor: {cor}) - {subtotal:.2f} MT")

        pedido_texto = "\n".join(resumo_pedido)
        
        try:
            from utils.helpers import gerar_id
            novo_id = gerar_id()
        except ImportError:
            novo_id = str(uuid.uuid4())[:8]
        
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
    Lê a lista completa de pedidos da aba 'Pedidos' para o Painel Admin.
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
