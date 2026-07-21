from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
from functools import wraps
import os
import time

from config import Config
from utils.helpers import hora_mocambique
# Certifica-te de que o catalog_service tem as funções de adicionar e eliminar (add_product, delete_product)
from services.catalog_service import load_catalog, add_order, get_orders, add_product, delete_product

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "loja_moda_secret_key_2026")

# Decorator para Proteger Rotas Admin
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# ======================================================
# CACHE INTELIGENTE DE PRODUTOS
# ======================================================
CACHE_PRODUTOS = None
ULTIMA_ATUALIZACAO = 0
TEMPO_CACHE = 20  # Segundos

def get_cached_catalog():
    global CACHE_PRODUTOS, ULTIMA_ATUALIZACAO
    agora = time.time()

    if CACHE_PRODUTOS is None or (agora - ULTIMA_ATUALIZACAO) > TEMPO_CACHE:
        CACHE_PRODUTOS = load_catalog()
        ULTIMA_ATUALIZACAO = agora

    return CACHE_PRODUTOS

def invalidate_catalog_cache():
    """Força a limpeza da memória cache ao modificar o catálogo."""
    global CACHE_PRODUTOS
    CACHE_PRODUTOS = None

# ======================================================
# ROTAS PWA (SERVICE WORKER E MANIFEST)
# ======================================================
@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js", mimetype="application/javascript")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/json")

# ======================================================
# ROTAS DA LOJA (CATÁLOGO E SACOLA)
# ======================================================
@app.route("/")
def index():
    produtos = get_cached_catalog()
    categorias = sorted(list(set(p.get("categoria", "Geral") for p in produtos if p.get("categoria"))))
    
    return render_template(
        "loja.html",
        produtos=produtos,
        categorias=categorias,
        config=Config
    )

@app.route("/cart")
def cart():
    """Rota para visualizar a Sacola de Compras."""
    return render_template("cart.html", config=Config)

# API para o Frontend consultar produtos atualizados via JS
@app.route("/api/produtos")
def api_produtos():
    return jsonify({"produtos": get_cached_catalog()})

# ======================================================
# CHECKOUT / REGISTAR PEDIDO
# ======================================================
@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.get_json(silent=True)

    if not data or not data.get("cart"):
        return jsonify({"success": False, "error": "Carrinho vazio"}), 400

    cart = data.get("cart", [])
    nome_cliente = data.get("nome", "Cliente")
    contacto = data.get("contacto", "N/A")

    sucesso = add_order(
        Config.SHEET_ORDERS,
        nome_cliente,
        contacto,
        cart,
        hora_mocambique()
    )

    return jsonify({"success": sucesso})

# ======================================================
# ROTAS DE ADMINISTRAÇÃO (GESTÃO DA BOUTIQUE)
# ======================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin/login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return redirect(url_for("admin_dashboard"))

    flash("Credenciais inválidas!", "danger")
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    """Exibe o painel de gestão com a lista de produtos (usando admin.html)."""
    produtos = load_catalog()
    return render_template("admin.html", produtos=produtos, config=Config)

@app.route("/admin/add", methods=["POST"])
@admin_required
def admin_add_product():
    """Recebe o formulário de cadastro do produto no admin.html."""
    novo_produto = {
        "nome": request.form.get("nome"),
        "categoria": request.form.get("categoria"),
        "preco": request.form.get("preco"),
        "tamanhos": request.form.get("tamanhos"),
        "cores": request.form.get("cores"),
        "fotos": request.form.get("fotos"),
        "descricao": request.form.get("descricao")
    }

    if add_product(novo_produto):
        invalidate_catalog_cache()  # Limpa o cache para mostrar na loja imediatamente
        flash("Produto adicionado com sucesso!", "success")
    else:
        flash("Erro ao adicionar produto.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<produto_id>", methods=["POST"])
@admin_required
def admin_delete_product(produto_id):
    """Elimina um produto do catálogo."""
    if delete_product(produto_id):
        invalidate_catalog_cache()
        flash("Produto removido com sucesso!", "warning")
    else:
        flash("Erro ao remover produto.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/pedidos")
@admin_required
def admin_pedidos():
    pedidos = get_orders(Config.SHEET_ORDERS)
    return render_template("admin/pedidos.html", pedidos=pedidos, config=Config)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

# ======================================================
# HEALTH CHECK
# ======================================================
@app.route("/health")
def health():
    return {"status": "ok", "system": "loja-moda-app"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
