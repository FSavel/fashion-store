import os
import json
import logging
import traceback
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    flash
)

from config import Config

from services.catalog_service import (
    load_catalog,
    add_order,
    get_orders,
    add_product,
    update_product,
    delete_product,
    update_order_status
)

from utils.helpers import hora_mocambique


# ======================================================
# CONFIGURAÇÃO DA APP (Com busca de templates na raiz e em templates/)
# ======================================================

app = Flask(__name__, template_folder=".")

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "boutique-elegance-secret-key-2026"
)

app.config.from_object(Config)

logging.basicConfig(level=logging.INFO)


# Configura o Jinja2 para procurar ficheiros tanto na raiz como na pasta templates/
app.jinja_loader.searchpath.append(os.path.join(app.root_path, "templates"))


# ======================================================
# FILTRO JSON PARA TEMPLATES
# ======================================================

@app.template_filter("fromjson")
def fromjson_filter(value):
    if not value:
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return []


# ======================================================
# PROTEÇÃO ADMIN & CACHE
# ======================================================

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


CACHE_PRODUTOS = None

def get_products():
    global CACHE_PRODUTOS
    if CACHE_PRODUTOS is None:
        CACHE_PRODUTOS = load_catalog()
    return CACHE_PRODUTOS

def clear_product_cache():
    global CACHE_PRODUTOS
    CACHE_PRODUTOS = None


# ======================================================
# ROTAS DA LOJA
# ======================================================

@app.route("/")
def index():
    produtos = get_products()
    
    # Extrai categorias dinamicamente
    categorias = sorted(
        list(
            set(
                p.get("categoria", "Geral")
                for p in produtos if isinstance(p, dict)
            )
        )
    )

    return render_template(
        "loja.html",
        produtos=produtos,
        categorias=categorias,
        config=Config
    )


@app.route("/cart")
@app.route("/carrinho")
def cart():
    return render_template(
        "cart.html",
        config=Config
    )


@app.route("/api/produtos")
def api_produtos():
    return jsonify({
        "produtos": get_products()
    })


# ======================================================
# CHECKOUT / PROCESSAMENTO DE PEDIDOS
# ======================================================

@app.route("/checkout", methods=["POST"])
@app.route("/api/pedidos/novo", methods=["POST"])
def checkout():
    print("\n========== NOVO CHECKOUT ==========")

    data = request.get_json(silent=True) or {}
    print(json.dumps(data, indent=2, ensure_ascii=False))

    cart_items = (
        data.get("cart")
        or data.get("itens")
        or []
    )

    if not cart_items:
        return jsonify({
            "success": False,
            "error": "Carrinho vazio"
        }), 400

    nome = data.get("nome") or "Cliente"
    telefone = data.get("contacto") or data.get("telefone") or "N/A"
    endereco = data.get("endereco") or "N/A"
    pagamento = data.get("pagamento") or "Não especificado"

    contacto_completo = f"{telefone} | End: {endereco} | Pag: {pagamento}"

    try:
        resultado = add_order(
            getattr(Config, "SHEET_ORDERS", "Pedidos"),
            nome,
            contacto_completo,
            cart_items,
            hora_mocambique(),
            status="Pendente"
        )

        print("Resultado add_order:", resultado)

        return jsonify({
            "success": resultado
        })

    except Exception as e:
        logging.exception("Erro ao processar checkout")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ======================================================
# AUTENTICAÇÃO E PAINEL ADMIN
# ======================================================

@app.route("/login", methods=["GET", "POST"])
@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")

        admin_user = getattr(Config, "ADMIN_USERNAME", "admin")
        admin_pass = getattr(Config, "ADMIN_PASSWORD", "admin123")

        if user == admin_user and pwd == admin_pass:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))

        return render_template("login.html", error="Credenciais inválidas")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("login"))


@app.route("/admin")
@admin_required
def admin():
    try:
        pedidos = get_orders(getattr(Config, "SHEET_ORDERS", "Pedidos"))
        if isinstance(pedidos, list):
            pedidos.reverse()
    except Exception as e:
        logging.error(f"Erro ao carregar painel Admin: {e}")
        pedidos = []

    return render_template(
        "admin.html",
        pedidos=pedidos,
        config=Config
    )


# ======================================================
# HEALTH CHECK
# ======================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "app": "Boutique Elegance"
    })


# ======================================================
# INICIALIZAÇÃO
# ======================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
