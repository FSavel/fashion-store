import os
import json
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, 
    url_for, flash, session, jsonify
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "boutique-elegance-secret-key-2026")

# Register Jinja2 filter for JSON parsing (safeguard for admin template)
@app.template_filter('fromjson')
def fromjson_filter(value):
    if not value:
        return []
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return []

# Config values
class Config:
    SHEET_ORDERS = "Pedidos"
    SHEET_PRODUCTS = "Produtos"

# Admin Authentication Decorator
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Acesso não autorizado. Por favor faça login.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# --- DATA HELPERS ---

def get_orders(sheet_name=Config.SHEET_ORDERS):
    """
    Retrieves order data. Defaults to 'Pedidos' if sheet_name is omitted.
    """
    # Replace or integrate this with your Google Sheets / Database integration logic
    orders_data = session.get("pedidos_db", [])
    return orders_data

def get_products(sheet_name=Config.SHEET_PRODUCTS):
    """
    Retrieves product catalog. Defaults to 'Produtos' if sheet_name is omitted.
    """
    products_data = session.get("produtos_db", [])
    return products_data

def save_order(order_data):
    orders = session.get("pedidos_db", [])
    order_data["id"] = len(orders) + 1
    orders.append(order_data)
    session["pedidos_db"] = orders

def update_order_status(order_id, new_status):
    orders = session.get("pedidos_db", [])
    updated = False
    for order in orders:
        if str(order.get("id")) == str(order_id):
            order["status"] = new_status
            updated = True
            break
    if updated:
        session["pedidos_db"] = orders
    return updated

# --- PUBLIC ROUTES ---

@app.route("/")
def index():
    produtos = get_products()
    return render_template("index.html", produtos=produtos)

@app.route("/api/pedido", methods=["POST"])
def criar_pedido():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Dados inválidos"}), 400
        
        save_order(data)
        return jsonify({"success": True, "message": "Pedido registado com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# --- ADMIN ROUTES ---

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Replace credentials check with your preferred security configuration
        admin_user = os.environ.get("ADMIN_USER", "admin")
        admin_pass = os.environ.get("ADMIN_PASS", "admin123")
        
        if username == admin_user and password == admin_pass:
            session["admin_logged_in"] = True
            flash("Sessão iniciada com sucesso!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Utilizador ou palavra-passe incorretos.", "danger")
            
    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Sessão encerrada.", "info")
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    # Pass sheet_name explicitly to satisfy requirement and prevent TypeError
    pedidos = get_orders(Config.SHEET_ORDERS)
    produtos = get_products(Config.SHEET_PRODUCTS)
    return render_template("admin.html", pedidos=pedidos, produtos=produtos)

@app.route("/admin/pedido/status/<int:pedido_id>", methods=["POST"])
@admin_required
def alterar_status_pedido(pedido_id):
    data = request.get_json() or {}
    novo_status = data.get("status")
    
    if not novo_status:
        return jsonify({"success": False, "message": "Estado não especificado."}), 400
        
    sucesso = update_order_status(pedido_id, novo_status)
    if sucesso:
        return jsonify({"success": True, "status": novo_status})
    return jsonify({"success": False, "message": "Pedido não encontrado."}), 404

@app.route("/admin/add", methods=["POST"])
@admin_required
def adicionar_produto():
    nome = request.form.get("nome")
    categoria = request.form.get("categoria")
    preco = request.form.get("preco")
    tamanhos = request.form.get("tamanhos")
    cores = request.form.get("cores")
    fotos = request.form.get("fotos")
    descricao = request.form.get("descricao")
    
    # Handle direct photo upload (Cloudinary integration point)
    file = request.files.get("foto_file")
    if file and file.filename != "":
        # Process upload via Cloudinary or local static folder
        pass

    produtos = session.get("produtos_db", [])
    novo_produto = {
        "id": len(produtos) + 1,
        "nome": nome,
        "categoria": categoria,
        "preco": float(preco) if preco else 0.0,
        "tamanhos": tamanhos,
        "cores": cores,
        "fotos": fotos,
        "descricao": descricao
    }
    produtos.append(novo_produto)
    session["produtos_db"] = produtos
    
    flash("Produto adicionado com sucesso!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit/<int:produto_id>", methods=["POST"])
@admin_required
def editar_produto(produto_id):
    produtos = session.get("produtos_db", [])
    for p in produtos:
        if p.get("id") == produto_id:
            p["nome"] = request.form.get("nome", p.get("nome"))
            p["categoria"] = request.form.get("categoria", p.get("categoria"))
            p["preco"] = float(request.form.get("preco", p.get("preco")))
            p["tamanhos"] = request.form.get("tamanhos", p.get("tamanhos"))
            p["cores"] = request.form.get("cores", p.get("cores"))
            p["fotos"] = request.form.get("fotos", p.get("fotos"))
            p["descricao"] = request.form.get("descricao", p.get("descricao"))
            break
            
    session["produtos_db"] = produtos
    flash("Produto atualizado com sucesso!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<int:produto_id>", methods=["POST"])
@admin_required
def remover_produto(produto_id):
    produtos = session.get("produtos_db", [])
    produtos = [p for p in produtos if p.get("id") != produto_id]
    session["produtos_db"] = produtos
    
    flash("Produto removido do catálogo.", "info")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
