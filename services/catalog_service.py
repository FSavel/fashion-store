import os
import json
import uuid
import logging
import gspread
from datetime import datetime
from typing import List, Dict, Optional
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
logging.basicConfig(level=logging.INFO)

def get_google_client():
    creds = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds: return None
    try:
        cred = Credentials.from_service_account_info(json.loads(creds), scopes=SCOPES)
        return gspread.authorize(cred)
    except Exception as e:
        logging.exception(f"Erro Google Client: {e}")
        return None

def get_spreadsheet():
    client = get_google_client()
    sheet_id = os.environ.get("GOOGLE_SHEETS_ID")
    if not client or not sheet_id: return None
    try:
        return client.open_by_key(sheet_id)
    except Exception as e:
        logging.exception(f"Erro Spreadsheet: {e}")
        return None

def get_sheet(sheet_name):
    book = get_spreadsheet()
    if not book: return None
    try:
        return book.worksheet(sheet_name)
    except Exception as e:
        logging.exception(f"Erro folha {sheet_name}: {e}")
        return None

def sheet_to_dict(sheet):
    if sheet is None: return []
    try:
        return sheet.get_all_records()
    except Exception as e:
        logging.exception(f"Erro leitura: {e}")
        return []

# ==========================================================
# CATÁLOGO
# ==========================================================

def load_catalog() -> List[Dict]:
    sheet = get_sheet("Produtos")
    if not sheet: return []
    produtos = []
    try:
        for r in sheet_to_dict(sheet):
            disp = str(r.get("Disponivel") or r.get("disponivel") or "SIM").strip().upper()
            if disp not in ["SIM", "TRUE", "1", "VERDADEIRO", "YES"]: continue
            produtos.append({
                "id": str(r.get("ID") or r.get("id") or uuid.uuid4()),
                "categoria": r.get("Categoria") or r.get("categoria") or "Geral",
                "nome": r.get("Nome") or r.get("nome") or "",
                "descricao": r.get("Descricao") or r.get("descricao") or "",
                "preco": str(r.get("Preco") or r.get("preco") or "0"),
                "fotos": r.get("Fotos") or r.get("fotos") or "",
                "tamanhos": r.get("Tamanhos") or r.get("tamanhos") or "",
                "cores": r.get("Cores") or r.get("cores") or "",
                "stock": int(r.get("Stock") or r.get("stock") or 0),
                "disponivel": disp
            })
        produtos.sort(key=lambda x: x["nome"])
        return produtos
    except Exception as e:
        logging.exception(f"Erro catálogo: {e}")
        return []

def get_product_by_id(produto_id) -> Optional[Dict]:
    for p in load_catalog():
        if str(p["id"]) == str(produto_id): return p
    return None

def search_products(texto) -> List[Dict]:
    texto = texto.lower().strip()
    return [p for p in load_catalog() if texto in p["nome"].lower() or texto in p["categoria"].lower() or texto in p["descricao"].lower()]

def get_products_by_category(categoria) -> List[Dict]:
    categoria = categoria.lower()
    return [p for p in load_catalog() if p["categoria"].lower() == categoria]

# ==========================================================
# PRODUTOS (CRUD)
# ==========================================================

def add_product(produto):
    sheet = get_sheet("Produtos")
    if not sheet: return False
    try:
        novo_id = str(uuid.uuid4())[:8]
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
            produto.get("disponivel", "SIM")
        ]
        sheet.append_row(linha)
        return True
    except Exception as e:
        logging.exception(f"Erro add_product: {e}")
        return False

def update_product(produto_id, produto):
    sheet = get_sheet("Produtos")
    if not sheet: return False
    try:
        records = sheet.get_all_records()
        for i, row in enumerate(records, start=2):
            if str(row.get("ID") or row.get("id")) == str(produto_id):
                valores = [
                    str(produto_id),
                    produto.get("categoria", row.get("Categoria") or row.get("categoria", "Geral")),
                    produto.get("nome", row.get("Nome") or row.get("nome", "")),
                    produto.get("descricao", row.get("Descricao") or row.get("descricao", "")),
                    produto.get("preco", row.get("Preco") or row.get("preco", "0")),
                    produto.get("fotos", row.get("Fotos") or row.get("fotos", "")),
                    produto.get("tamanhos", row.get("Tamanhos") or row.get("tamanhos", "")),
                    produto.get("cores", row.get("Cores") or row.get("cores", "")),
                    produto.get("stock", row.get("Stock") or row.get("stock", 1)),
                    produto.get("disponivel", row.get("Disponivel") or row.get("disponivel", "SIM"))
                ]
                sheet.update(f"A{i}:J{i}", [valores])
                return True
        return False
    except Exception as e:
        logging.exception(f"Erro update_product: {e}")
        return False

def delete_product(produto_id):
    sheet = get_sheet("Produtos")
    if not sheet: return False
    try:
        records = sheet.get_all_records()
        for i, row in enumerate(records, start=2):
            if str(row.get("ID") or row.get("id")) == str(produto_id):
                sheet.delete_rows(i)
                return True
        return False
    except Exception as e:
        logging.exception(f"Erro delete_product: {e}")
        return False

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def product_exists(produto_id):
    return get_product_by_id(produto_id) is not None

def total_products():
    return len(load_catalog())

def categories():
    return sorted(list(set(p["categoria"] for p in load_catalog())))

def products_available():
    return [p for p in load_catalog() if int(p.get("stock", 0)) > 0]

def products_out_stock():
    return [p for p in load_catalog() if int(p.get("stock", 0)) <= 0]

# ==========================================================
# PEDIDOS
# ==========================================================

def add_order(cliente_ou_sheet, contacto_ou_cliente=None, itens_ou_contacto=None, cart_items=None, data_hora=None, status="Pendente"):
    """
    Adiciona um novo pedido. Aceita tanto a assinatura curta:
      add_order(cliente, contacto, itens)
    como a assinatura vinda do app.py:
      add_order(sheet_name, cliente, contacto, cart_items, data_hora, status="Pendente")
    """
    sheet = get_sheet("Pedidos")
    if not sheet: return False
    
    try:
        if cart_items is not None:
            cliente = contacto_ou_cliente
            contacto = itens_ou_contacto
            itens = cart_items
        else:
            cliente = cliente_ou_sheet
            contacto = contacto_ou_cliente
            itens = itens_ou_contacto

        if isinstance(itens, str):
            try:
                itens = json.loads(itens)
            except Exception:
                itens = []

        total = 0.0
        resumo = []

        for item in (itens or []):
            qtd = safe_float(item.get("quantidade") or item.get("qtd") or 1)
            raw_preco = str(item.get("preco", 0)).replace("MT", "").replace(",", ".").strip()
            preco = safe_float(raw_preco)
            
            subtotal = qtd * preco
            total += subtotal

            resumo.append({
                "produto": item.get("nome") or item.get("title") or "Produto",
                "cor": item.get("cor", "N/A"),
                "tamanho": item.get("tamanho") or item.get("tam") or "N/A",
                "quantidade": qtd,
                "preco": preco,
                "subtotal": subtotal
            })

        pedido_texto = "\n".join(
            f'{int(i["quantidade"])}x {i["produto"]} (Tam: {i["tamanho"]}, Cor: {i["cor"]}) - {i["subtotal"]:.2f} MT'
            for i in resumo
        ) if resumo else "Detalhes no JSON"

        data_final = data_hora or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            str(uuid.uuid4())[:8],
            cliente or "Cliente",
            contacto or "N/A",
            pedido_texto,
            f"{round(total, 2)} MT",
            data_final,
            status or "Pendente",
            json.dumps(resumo, ensure_ascii=False)
        ]

        sheet.append_row(row)
        return True

    except Exception as e:
        logging.exception(f"Erro add_order: {e}")
        return False

def get_orders(sheet_name="Pedidos"):
    """Retorna a lista de pedidos da planilha."""
    sheet = get_sheet(sheet_name if isinstance(sheet_name, str) else "Pedidos")
    if not sheet: return []

    try:
        pedidos = []

        for i, row in enumerate(sheet.get_all_records(), start=2):
            itens_json = row.get("Itens_JSON") or row.get("itens_json") or "[]"

            try:
                itens_parsed = json.loads(itens_json)
            except Exception:
                itens_parsed = []

            pedidos.append({
                "row_index": i,
                "id": str(row.get("ID") or row.get("id") or ""),
                "nome": row.get("Cliente") or row.get("cliente") or "",
                "contacto": row.get("Contacto") or row.get("contacto") or "",
                "pedido": row.get("Itens_Texto") or row.get("Pedido") or row.get("pedido") or "",
                "total": str(row.get("Total") or "0 MT"),
                "hora": row.get("Data") or row.get("Hora") or "",
                "data": row.get("Data") or "",
                "status": row.get("Status") or "Pendente",
                "itens": itens_json,
                "itens_parsed": itens_parsed
            })

        pedidos.sort(key=lambda x: x["hora"], reverse=True)
        return pedidos

    except Exception as e:
        logging.exception(f"Erro get_orders: {e}")
        return []

def dashboard_stats(sheet_name="Pedidos"):
    """Calcula estatísticas do painel admin."""
    pedidos = get_orders(sheet_name)
    return {
        "total_pedidos": len(pedidos),
        "pendentes": len([p for p in pedidos if str(p["status"]).lower() == "pendente"]),
        "concluidos": len([p for p in pedidos if str(p["status"]).lower() in ["concluido", "entregue"]]),
        "cancelados": len([p for p in pedidos if str(p["status"]).lower() == "cancelado"]),
        "vendas": round(sum(safe_float(str(p["total"]).replace("MT", "").replace(",", ".").strip()) for p in pedidos), 2)
    }

# ==========================================================
# UTILITÁRIOS
# ==========================================================

def generate_id():
    return str(uuid.uuid4())[:8]

def format_price(valor):
    try:
        return round(float(valor), 2)
    except:
        return 0

def safe_float(valor):
    try:
        return float(valor)
    except:
        return 0.0

def safe_int(valor):
    try:
        return int(valor)
    except:
        return 0

def validate_product(produto):
    obrigatorios = ["nome", "categoria", "preco"]
    for campo in obrigatorios:
        if not produto.get(campo):
            return False, f"Campo obrigatório: {campo}"
    return True, "OK"

# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [
    "load_catalog",
    "get_product_by_id",
    "search_products",
    "get_products_by_category",
    "add_product",
    "update_product",
    "delete_product",
    "add_order",
    "get_orders",
    "update_order_status",
    "dashboard_stats",
    "total_products",
    "products_available",
    "products_out_stock",
    "categories"
]
