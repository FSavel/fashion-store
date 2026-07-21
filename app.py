from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
from functools import wraps
import os
import time
import cloudinary
import cloudinary.uploader

from config import Config
from utils.helpers import hora_mocambique
from services.catalog_service import load_catalog, add_order, get_orders, add_product, delete_product, update_product

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "loja_moda_secret_key_2026")

# ======================================================
# CONFIGURAÇÃO DO CLOUDINARY (UPLOADS DE IMAGENS)
# ======================================================
os.environ["CLOUDINARY_URL"] = os.environ.get(
    "CLOUDINARY_URL", 
    "cloudinary://336478923929577:fIoPC_rrW0nCqqH1nUX3lrYATkM@a0xqn8ql"
)
cloudinary.config(secure=True)

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
# ROTAS PWA (SERVICE WORKER, MANIFEST E ÍCONES)
# ======================================================
@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js", mimetype="application/javascript")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/json")

# Rota de fallback para evitar o erro 404 nos logs caso o ícone ainda não exista
@app.route("/static/icons/<path:filename>")
def serve_icons(filename):
    try:
        return send_from_directory("static/icons", filename)
    except Exception:
        return "", 204

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
@app.route("/api/pedidos/novo", methods=["POST"])
def checkout():
    """Regista um novo pedido vindo da Sacola de Compras antes de ir para o WhatsApp."""
    data = request.get_json(silent=True)

    if not data or (not data.get("cart") and not data.get("itens")):
        return jsonify({"success": False, "error": "Carrinho vazio"}), 400

    cart = data.get("cart") or data.get("itens", [])
    nome_cliente = data.get("nome") or data.get("cliente_nome", "Cliente")
    contacto = data.get("contacto") or data.get("cliente_endereco", "N/A")

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
    """Exibe o painel de gestão com a lista de produtos E pedidos."""
    produtos = load_catalog()
    pedidos = get_orders(Config.SHEET_ORDERS)  # <-- AGORA OS PEDIDOS SÃO CARREGADOS AQUI!
    
    return render_template(
        "admin.html", 
        produtos=produtos, 
        pedidos=pedidos, 
        config=Config
    )

def processar_imagem_produto(request_obj):
    """Auxiliar: Processa upload de ficheiro no Cloudinary ou retorna a URL enviada por texto."""
    if "foto_file" in request_obj.files and request_obj.files["foto_file"].filename != "":
        ficheiro = request_obj.files["foto_file"]
        resultado = cloudinary.uploader.upload(ficheiro, folder="boutique_elegance")
        return resultado.get("secure_url")
    
    return request_obj.form.get("fotos", "")

@app.route("/admin/add", methods=["POST"])
@admin_required
def admin_add_product():
    """Recebe o formulário de cadastro do produto (suporta upload ou URL)."""
    foto_url = processar_imagem_produto(request)

    novo_produto = {
        "nome": request.form.get("nome"),
        "categoria": request.form.get("categoria"),
        "preco": request.form.get("preco"),
        "tamanhos": request.form.get("tamanhos"),
        "cores": request.form.get("cores"),
        "fotos": foto_url,
        "descricao": request.form.get("descricao")
    }

    if add_product(novo_produto):
        invalidate_catalog_cache()
        flash("Produto adicionado com sucesso!", "success")
    else:
        flash("Erro ao adicionar produto.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit/<produto_id>", methods=["POST"])
@admin_required
def admin_edit_product(produto_id):
    """Edita um produto existente."""
    foto_url = processar_imagem_produto(request)
    
    if not foto_url:
        foto_url = request.form.get("foto_antiga", "")

    produto_atualizado = {
        "id": produto_id,
        "nome": request.form.get("nome"),
        "categoria": request.form.get("categoria"),
        "preco": request.form.get("preco"),
        "tamanhos": request.form.get("tamanhos"),
        "cores": request.form.get("cores"),
        "fotos": foto_url,
        "descricao": request.form.get("descricao")
    }

    if update_product(produto_id, produto_atualizado):
        invalidate_catalog_cache()
        flash("Produto atualizado com sucesso!", "success")
    else:
        invalidate_catalog_cache()
        flash("Erro ao atualizar produto.", "danger")

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
    """Exibe a lista e o estado dos pedidos efetuados."""
    pedidos = get_orders(Config.SHEET_ORDERS)
    return render_template("admin/pedidos.html", pedidos=pedidos, config=Config)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

# ======================================================
# SOBRE
# ======================================================
@app.route("/sobre")
def sobre():
    """Exibe a página de detalhes, localização e créditos da loja."""
    return render_template("sobre.html")
    
# ======================================================
# HEALTH CHECK
# ======================================================
@app.route("/health")
def health():
    return {"status": "ok", "system": "loja-moda-app"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
