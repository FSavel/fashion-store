import os
import json
import logging
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
# CONFIGURAÇÃO DA APP
# ======================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "boutique-elegance-secret-key-2026"
)

app.config.from_object(Config)


# ======================================================
# LOGGING
# ======================================================

logging.basicConfig(level=logging.INFO)


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
# PROTEÇÃO ADMIN
# ======================================================

def admin_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return func(*args, **kwargs)

    return wrapper


# ======================================================
# CACHE PRODUTOS
# ======================================================

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
# LOJA
# ======================================================

@app.route("/")
def index():

    produtos = get_products()

    categorias = sorted(
        list(
            set(
                p.get("categoria", "Geral")
                for p in produtos
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
# CHECKOUT
# ======================================================

@app.route("/checkout", methods=["POST"])
@app.route("/api/pedidos/novo", methods=["POST"])
def checkout():

    print("\n========== CHECKOUT ==========")

    data = request.get_json(
        silent=True
    ) or {}


    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        )
    )


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



    nome = (
        data.get("nome")
        or "Cliente"
    )


    telefone = (
        data.get("contacto")
        or data.get("telefone")
        or "N/A"
    )


    endereco = (
        data.get("endereco")
        or "N/A"
    )


    pagamento = (
        data.get("pagamento")
        or "Não especificado"
    )


    contacto_completo = (
        f"{telefone} | "
        f"End: {endereco} | "
        f"Pag: {pagamento}"
    )



    try:

        resultado = add_order(

            Config.SHEET_ORDERS,

            nome,

            contacto_completo,

            cart_items,

            hora_mocambique(),

            status="Pendente"

        )


        print(
            "Resultado add_order:",
            resultado
        )


        return jsonify({

            "success": resultado

        })


    except Exception as e:

        logging.exception(
            "Erro no checkout"
        )


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500
        # ==========================================================
# ROTAS DA LOJA
# ==========================================================

@app.route("/")
def index():
    produtos = get_all_products()
    return render_template(
        "index.html",
        produtos=produtos,
        config=Config
    )


@app.route("/cart")
@app.route("/carrinho")
def cart_page():
    return render_template(
        "cart.html",
        config=Config
    )


# ==========================================================
# CHECKOUT / RECEBER PEDIDOS
# ==========================================================

@app.route("/checkout", methods=["POST"])
@app.route("/api/pedidos/novo", methods=["POST"])
def checkout():

    print("\n====== NOVO PEDIDO ======")

    data = request.get_json(silent=True) or {}

    print(json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    ))

    cart = data.get("cart") or data.get("itens", [])

    if not cart:
        return jsonify({
            "success": False,
            "error": "Carrinho vazio"
        }),400


    nome = data.get("nome","Cliente")

    telefone = (
        data.get("contacto")
        or data.get("telefone")
        or "N/A"
    )

    endereco = (
        data.get("endereco")
        or "N/A"
    )

    pagamento = (
        data.get("pagamento")
        or "Não informado"
    )


    contacto_final = (
        f"{telefone} | "
        f"End: {endereco} | "
        f"Pag: {pagamento}"
    )


    sucesso = add_order(
        Config.SHEET_ORDERS,
        nome,
        contacto_final,
        cart,
        hora_mocambique(),
        "Pendente"
    )


    return jsonify({
        "success": sucesso
    })


# ==========================================================
# LOGIN ADMIN
# ==========================================================

@app.route("/login",methods=["GET","POST"])
def login():

    if request.method=="POST":

        user=request.form.get("username")
        pwd=request.form.get("password")


        if (
            user==Config.ADMIN_USERNAME
            and pwd==Config.ADMIN_PASSWORD
        ):

            session["admin"]=True

            return redirect(
                url_for("admin")
            )


        return render_template(
            "login.html",
            error="Login inválido"
        )


    return render_template(
        "login.html"
    )


@app.route("/logout")
def logout():

    session.pop(
        "admin",
        None
    )

    return redirect(
        url_for("login")
    )


# ==========================================================
# PAINEL ADMIN
# ==========================================================

@app.route("/admin")
def admin():

    if not session.get("admin"):

        return redirect(
            url_for("login")
        )


    try:

        ws=get_worksheet(
            Config.SHEET_ORDERS
        )

        pedidos=ws.get_all_records()

        pedidos.reverse()


    except Exception as e:

        print(
            "Erro Admin:",
            e
        )

        traceback.print_exc()

        pedidos=[]



    return render_template(
        "admin.html",
        pedidos=pedidos,
        config=Config
    )


# ==========================================================
# API PRODUTOS
# ==========================================================

@app.route("/api/produtos")
def api_produtos():

    return jsonify({
        "produtos":get_all_products()
    })


# ==========================================================
# HEALTH CHECK RENDER
# ==========================================================

@app.route("/health")
def health():

    return jsonify({
        "status":"online",
        "app":"Boutique Elegance"
    })


# ==========================================================
# START
# ==========================================================

if __name__=="__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )
