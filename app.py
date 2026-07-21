from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
from functools import wraps
import os
import time

from config import Config
from utils.helpers import hora_mocambique
from services.catalog_service import load_catalog, add_order, get_orders

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
# ROTAS PWA (SERVICE WORKER E MANIFEST)
# ======================================================
@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js", mimetype="application/javascript")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/json")

# ======================================================
# CATÁLOGO PRINCIPAL (LEITURA DO QR CODE)
# ======================================================
@app.route("/")
def index():
    produtos = get_cached_catalog()
    
    # Extrai categorias únicas ativas para o menu superior
    categorias = sorted(list(set(p.get("categoria", "Geral") for p in produtos if p.get("categoria"))))
    
    return render_template(
        "loja.html",
        produtos=produtos,
        categorias=categorias,
        config=Config
    )

# ======================================================
# CACHE INTELIGENTE DE PRODUTOS (EVITA ERRO 429 DO GOOGLE)
# ======================================================
CACHE_PRODUTOS = None
ULTIMA_ATUALIZACAO = 0
TEMPO_CACHE = 20  # Mantém os dados na memória por 20 segundos

def get_cached_catalog():
    global CACHE_PRODUTOS, ULTIMA_ATUALIZACAO
    agora = time.time()

    if CACHE_PRODUTOS is None or (agora - ULTIMA_ATUALIZACAO) > TEMPO_CACHE:
        CACHE_PRODUTOS = load_catalog()
        ULTIMA_ATUALIZACAO = agora

    return CACHE_PRODUTOS

# API para o Frontend consultar produtos atualizados
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
# ADMIN ROUTES
# ======================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin/login.html")

    if request.form.get("username") == Config.ADMIN_USERNAME and request.form.get("password") == Config.ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return redirect(url_for("admin_pedidos"))

    flash("Credenciais inválidas!", "danger")
    return redirect(url_for("admin_login"))

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