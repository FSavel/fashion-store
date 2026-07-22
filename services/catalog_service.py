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
                "stock": 5,
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
                "stock": 3,
                "disponivel": "SIM"
            }
        ]

    try:
        sheet = spreadsheet.worksheet("Produtos")
        records = sheet.get_all_records()
        
        produtos_ativos = []
        for r in records:
            disp = str(r.get("disponivel", "")).strip().upper()
            if disp in ["SIM", "TRUE", "1", "VERDADEIRO", ""]:
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
            produto.get("stock", 1),
            "SIM"  # Disponível por defeito
        ]
        
        sheet.append_row(linha)
        return True
    except Exception as e:
        print(f"Erro ao adicionar produto no Google Sheets: {e}")
        return False

def update_product(produto_id, produto):
    """
    Procura o produto pelo ID na aba 'Produtos' e atualiza os seus campos.
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
        print("Aviso: Edição simulada com sucesso (Google Sheets não configurado).")
        return True

    try:
        sheet = spreadsheet.worksheet("Produtos")
        records = sheet.get_all_records()
        
        # Procura a linha correspondente (+2 compensa cabeçalho + índice 1 do Sheets)
        for index, row in enumerate(records):
            if str(row.get("id")) == str(produto_id):
                row_idx = index + 2
                
                sheet.update_cell(row_idx, 2, produto.get("categoria", row.get("categoria", "")))
                sheet.update_cell(row_idx, 3, produto.get("nome", row.get("nome", "")))
                sheet.update_cell(row_idx, 4, produto.get("descricao", row.get("descricao", "")))
                sheet.update_cell(row_idx, 5, produto.get("preco", row.get("preco", "")))
                sheet.update_cell(row_idx, 6, produto.get("fotos", row.get("fotos", "")))
                sheet.update_cell(row_idx, 7, produto.get("tamanhos", row.get("tamanhos", "")))
                sheet.update_cell(row_idx, 8, produto.get("cores", row.get("cores", "")))
                sheet.update_cell(row_idx, 9, produto.get("stock", row.get("stock", 1)))
                return True
                
        print(f"Produto {produto_id} não encontrado para atualização.")
        return False
    except Exception as e:
        print(f"Erro ao atualizar produto no Google Sheets: {e}")
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
def add_order(sheet_name, nome_cliente, contacto, cart_items, data_hora, status="Pendente"):
    """
    Regista um novo pedido efetuado pelo cliente na aba 'Pedidos'.
    Guarda tanto o resumo em texto como os dados estruturados em JSON.
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
        print("Aviso: Pedido simulado com sucesso (Folha Google não ligada).")
        return True

    try:
        sheet = spreadsheet.worksheet(sheet_name)
        
        # Garante que temos uma lista de itens tratada
        if isinstance(cart_items, str):
            try:
                items_list = json.loads(cart_items)
            except Exception:
                items_list = []
        else:
            items_list = cart_items or []

        resumo_pedido = []
        total_geral = 0.0

        for item in items_list:
            nome = item.get("nome") or item.get("title") or "Produto"
            qtd = int(item.get("qtd") or item.get("quantidade") or 1)
            
            try:
                preco = float(str(item.get("preco", 0)).replace(",", ".").replace("MT", "").strip())
            except ValueError:
                preco = 0.0

            tamanho = item.get("tamanho", "N/A")
            cor = item.get("cor", "N/A")
            
            subtotal = preco * qtd
            total_geral += subtotal
            
            resumo_pedido.append(f"{qtd}x {nome} (Tam: {tamanho}, Cor: {cor}) - {subtotal:.2f} MT")

        pedido_texto = "\n".join(resumo_pedido) if resumo_pedido else "Detalhes no JSON"
        json_itens = json.dumps(items_list, ensure_ascii=False)
        
        try:
            from utils.helpers import gerar_id
            novo_id = gerar_id()
        except ImportError:
            novo_id = str(uuid.uuid4())[:8]
        
        # Estrutura das colunas no Google Sheets:
        # [ID, Cliente, Contacto, Itens_Texto, Total, Data, Status, Itens_JSON]
        sheet.append_row([
            novo_id,
            nome_cliente,
            contacto,
            pedido_texto,
            f"{total_geral:.2f} MT",
            data_hora,
            status,
            json_itens
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
        records = sheet.get_all_records()
        
        # Garante padronização das chaves para o frontend
        pedidos_formatados = []
        for r in records:
            # Tenta obter o JSON dos itens se existir, senão usa o campo de texto
            itens_raw = r.get("Itens_JSON") or r.get("itens_json") or r.get("pedido_texto") or r.get("itens")
            
            pedidos_formatados.append({
                "id": r.get("id") or r.get("ID"),
                "nome": r.get("nome") or r.get("cliente_nome") or r.get("Cliente") or "Cliente",
                "contacto": r.get("contacto") or r.get("Contacto") or "N/A",
                "total": r.get("total") or r.get("Total") or "0.00 MT",
                "data": r.get("data") or r.get("Data") or "Hoje",
                "status": r.get("status") or r.get("Status") or "Pendente",
                "itens": itens_raw
            })
            
        return pedidos_formatados
    except Exception as e:
        print(f"Erro ao procurar lista de pedidos: {e}")
        return []

def update_order_status(sheet_name, order_id, new_status):
    """
    Procura um pedido pelo ID na aba 'Pedidos' e atualiza a sua coluna de Status.
    """
    spreadsheet = get_spreadsheet()
    
    if not spreadsheet:
        print(f"Aviso: Estado do pedido #{order_id} alterado simuladamente para '{new_status}'.")
        return True

    try:
        sheet = spreadsheet.worksheet(sheet_name)
        records = sheet.get_all_records()
        
        for index, row in enumerate(records):
            current_id = str(row.get("id") or row.get("ID") or "")
            if current_id == str(order_id):
                row_idx = index + 2
                
                # Procura o índice da coluna 'Status' no cabeçalho
                headers = sheet.row_values(1)
                col_idx = 7  # Padrão: coluna 7
                for h_idx, h_name in enumerate(headers, 1):
                    if h_name.lower() in ["status", "estado"]:
                        col_idx = h_idx
                        break
                        
                sheet.update_cell(row_idx, col_idx, new_status)
                return True
                
        print(f"Pedido #{order_id} não encontrado para atualizar status.")
        return False
    except Exception as e:
        print(f"Erro ao atualizar estado do pedido no Google Sheets: {e}")
        return False
