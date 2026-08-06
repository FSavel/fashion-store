import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials
from config import Config

logger = logging.getLogger(__name__)

# Arquivos JSON locais de backup/fallback
LOCAL_CATALOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'catalog.json')
LOCAL_ORDERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'orders.json')

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ======================================================
# CONEXÃO GOOGLE SHEETS
# ======================================================
def get_gsheet_client():
    """Inicializa e retorna a conexão com o Google Sheets usando google-auth."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON") or getattr(Config, 'GOOGLE_CREDENTIALS_JSON', None)
    
    if creds_json:
        try:
            creds_dict = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Erro ao autenticar com GOOGLE_CREDENTIALS_JSON: {e}")

    # Tenta carregar do arquivo local se existir
    creds_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
    if os.path.exists(creds_file):
        try:
            creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Erro ao carregar credentials.json: {e}")

    return None


def get_worksheet(sheet_name):
    """Acessa uma aba específica da planilha Google Sheets."""
    client = get_gsheet_client()
    spreadsheet_id = os.environ.get("SPREADSHEET_ID") or getattr(Config, 'SPREADSHEET_ID', None)
    
    if client and spreadsheet_id:
        try:
            return client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        except Exception as e:
            logger.error(f"Erro ao abrir a aba {sheet_name}: {e}")
            return None
    return None


# ======================================================
# OPERAÇÕES DE PRODUTOS / CATÁLOGO
# ======================================================
def load_catalog():
    """Carrega todos os produtos da aba 'Produtos' ou do arquivo JSON local."""
    ws = get_worksheet(getattr(Config, 'SHEET_CATALOG', 'Produtos'))
    
    if ws:
        try:
            records = ws.get_all_records()
            produtos = []
            for idx, r in enumerate(records, start=1):
                p = {
                    "id": str(r.get("ID") or r.get("id") or idx),
                    "nome": str(r.get("Nome") or r.get("nome") or ""),
                    "categoria": str(r.get("Categoria") or r.get("categoria") or "Geral"),
                    "preco": str(r.get("Preco") or r.get("preco") or "0"),
                    "tamanhos": str(r.get("Tamanhos") or r.get("tamanhos") or ""),
                    "cores": str(r.get("Cores") or r.get("cores") or ""),
                    "stock": int(r.get("Stock") or r.get("stock") or 1),
                    "fotos": str(r.get("Fotos") or r.get("fotos") or ""),
                    "descricao": str(r.get("Descricao") or r.get("descricao") or "")
                }
                produtos.append(p)
            return produtos
        except Exception as e:
            logger.error(f"Erro ao ler catálogo do Google Sheets: {e}")

    # Fallback local em JSON
    if os.path.exists(LOCAL_CATALOG_FILE):
        try:
            with open(LOCAL_CATALOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler catalog.json local: {e}")
            
    return []


def save_local_catalog(produtos):
    """Auxiliar: Salva a lista de produtos no arquivo local JSON."""
    try:
        with open(LOCAL_CATALOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(produtos, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar catalog.json: {e}")
        return False


def add_product(novo_produto):
    """Adiciona um novo produto ao catálogo."""
    ws = get_worksheet(getattr(Config, 'SHEET_CATALOG', 'Produtos'))
    
    if ws:
        try:
            records = ws.get_all_records()
            next_id = len(records) + 1
            
            linha = [
                next_id,
                novo_produto.get("nome", ""),
                novo_produto.get("categoria", ""),
                novo_produto.get("preco", ""),
                novo_produto.get("tamanhos", ""),
                novo_produto.get("cores", ""),
                novo_produto.get("stock", 1),
                novo_produto.get("fotos", ""),
                novo_produto.get("descricao", "")
            ]
            ws.append_row(linha)
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar produto no Google Sheets: {e}")

    # Fallback JSON
    produtos = load_catalog()
    novo_produto["id"] = str(len(produtos) + 1)
    produtos.append(novo_produto)
    return save_local_catalog(produtos)


def update_product(produto_id, produto_atualizado):
    """Atualiza as informações de um produto existente."""
    ws = get_worksheet(getattr(Config, 'SHEET_CATALOG', 'Produtos'))
    
    if ws:
        try:
            cell = ws.find(str(produto_id))
            if cell:
                row = cell.row
                ws.update(f"A{row}:I{row}", [[
                    produto_id,
                    produto_atualizado.get("nome", ""),
                    produto_atualizado.get("categoria", ""),
                    produto_atualizado.get("preco", ""),
                    produto_atualizado.get("tamanhos", ""),
                    produto_atualizado.get("cores", ""),
                    produto_atualizado.get("stock", 1),
                    produto_atualizado.get("fotos", ""),
                    produto_atualizado.get("descricao", "")
                ]])
                return True
        except Exception as e:
            logger.error(f"Erro ao atualizar produto no Google Sheets: {e}")

    # Fallback JSON
    produtos = load_catalog()
    updated = False
    for i, p in enumerate(produtos):
        if str(p.get("id")) == str(produto_id):
            produtos[i].update(produto_atualizado)
            updated = True
            break
    
    if updated:
        save_local_catalog(produtos)
    return updated


def delete_product(produto_id):
    """Remove um produto do catálogo."""
    ws = get_worksheet(getattr(Config, 'SHEET_CATALOG', 'Produtos'))
    
    if ws:
        try:
            cell = ws.find(str(produto_id))
            if cell:
                ws.delete_rows(cell.row)
                return True
        except Exception as e:
            logger.error(f"Erro ao eliminar produto no Google Sheets: {e}")

    # Fallback JSON
    produtos = load_catalog()
    novos_produtos = [p for p in produtos if str(p.get("id")) != str(produto_id)]
    return save_local_catalog(novos_produtos)


# ======================================================
# OPERAÇÕES DE PEDIDOS
# ======================================================
def get_orders(sheet_name="Pedidos"):
    """Retorna todos os pedidos registados."""
    ws = get_worksheet(sheet_name)
    
    if ws:
        try:
            records = ws.get_all_records()
            pedidos = []
            for idx, r in enumerate(records, start=1):
                p_id = str(r.get("ID") or r.get("id") or idx)
                cliente = str(r.get("Cliente") or r.get("nome") or "Cliente")
                contacto = str(r.get("Contacto") or r.get("contacto") or "")
                data_hora = str(r.get("Data/Hora") or r.get("hora") or r.get("data") or "")
                status = str(r.get("Status") or r.get("status") or "Pendente")
                
                raw_itens = r.get("Itens") or r.get("itens") or r.get("pedido") or "[]"
                
                # Parsing dos itens JSON
                itens_parsed = []
                if isinstance(raw_itens, list):
                    itens_parsed = raw_itens
                elif isinstance(raw_itens, str):
                    try:
                        itens_parsed = json.loads(raw_itens)
                    except Exception:
                        itens_parsed = []

                # Cálculo ou obtenção do total
                total = str(r.get("Total") or r.get("total") or "0")
                if total == "0" and itens_parsed:
                    t_val = 0.0
                    for item in itens_parsed:
                        preco_num = float(str(item.get("preco", 0)).replace("MT", "").replace(",", ".").strip() or 0)
                        qtd = int(item.get("quantidade", 1))
                        t_val += preco_num * qtd
                    total = f"{t_val:.2f}"

                pedidos.append({
                    "id": p_id,
                    "nome": cliente,
                    "cliente": cliente,
                    "contacto": contacto,
                    "data": data_hora,
                    "hora": data_hora,
                    "pedido": raw_itens if isinstance(raw_itens, str) else json.dumps(raw_itens),
                    "itens": raw_itens,
                    "itens_parsed": itens_parsed,
                    "total": total,
                    "status": status
                })
            return pedidos
        except Exception as e:
            logger.error(f"Erro ao buscar pedidos no Google Sheets: {e}")

    # Fallback JSON
    if os.path.exists(LOCAL_ORDERS_FILE):
        try:
            with open(LOCAL_ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler orders.json local: {e}")

    return []


def add_order(sheet_name, cliente, contacto, cart_itens, data_hora, status="Pendente"):
    """Regista um novo pedido no Google Sheets ou no JSON local."""
    ws = get_worksheet(sheet_name)
    
    # Calcular total
    total_val = 0.0
    for item in cart_itens:
        preco_num = float(str(item.get("preco", 0)).replace("MT", "").replace(",", ".").strip() or 0)
        qtd = int(item.get("quantidade", item.get("qtd", 1)))
        total_val += preco_num * qtd

    total_str = f"{total_val:.2f} MT"
    itens_json_str = json.dumps(cart_itens, ensure_ascii=False)

    if ws:
        try:
            records = ws.get_all_records()
            next_id = len(records) + 1
            linha = [
                next_id,
                cliente,
                contacto,
                itens_json_str,
                total_str,
                status,
                data_hora
            ]
            ws.append_row(linha)
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar pedido no Google Sheets: {e}")

    # Fallback JSON local
    pedidos = get_orders(sheet_name)
    novo_pedido = {
        "id": str(len(pedidos) + 1),
        "nome": cliente,
        "cliente": cliente,
        "contacto": contacto,
        "data": data_hora,
        "hora": data_hora,
        "pedido": itens_json_str,
        "itens": cart_itens,
        "itens_parsed": cart_itens,
        "total": total_str,
        "status": status
    }
    pedidos.append(novo_pedido)
    try:
        with open(LOCAL_ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(pedidos, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erro ao guardar orders.json local: {e}")
        return False


def update_order_status(sheet_name, order_id, new_status):
    """
    Atualiza o estado (Pendente, A Caminho, Entregue, Cancelado) de um pedido específico.
    """
    ws = get_worksheet(sheet_name)
    
    if ws:
        try:
            cell = ws.find(str(order_id))
            if cell:
                headers = ws.row_values(1)
                col_status = 6  # Padrão: Coluna F
                
                for idx, h in enumerate(headers, start=1):
                    if str(h).strip().lower() in ["status", "estado"]:
                        col_status = idx
                        break

                ws.update_cell(cell.row, col_status, new_status)
                return True
        except Exception as e:
            logger.error(f"Erro ao atualizar status do pedido no Google Sheets: {e}")

    # Fallback JSON local
    pedidos = get_orders(sheet_name)
    updated = False
    for order in pedidos:
        if str(order.get('id')) == str(order_id):
            order['status'] = new_status
            updated = True
            break
            
    if updated:
        try:
            with open(LOCAL_ORDERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(pedidos, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar atualização no orders.json: {e}")
            
    return updated
