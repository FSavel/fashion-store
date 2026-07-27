from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
from functools import wraps
import os
import time
import json
import logging
import cloudinary
import cloudinary.uploader

from config import Config
from utils.helpers import hora_mocambique
from services.catalog_service import (
    load_catalog, 
    add_order, 
    get_orders, 
    add_product, 
    delete_product, 
    update_product,
    update_order_status
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "loja_moda_secret_key_2026")

# ======================================================
# FILTRO JINJA2 PERSONALIZADO (PARSE DE JSON NO TEMPLATE)
# ======================================================
@app.template_filter('fromjson')
def fromjson_filter(value):
    """Converte strings JSON armazenadas na base de dados/planilha em listas/dicionários Python."""
    if not value:
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return []

# ======================================================
# CONFIGURAÇÃO DO CLOUDINARY (UPLOADS DE IMAGENS)
# ======================================================
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")
if CLOUDINARY_URL:
    os.environ["CLOUDINARY_URL"] = CLOUDINARY_URL
    cloudinary.config(secure=True)

# Decorator para Proteger Rotas Admin
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# Helper para upload de foto para o Cloudinary
def upload_foto(file_obj):
    if file_obj and file_obj.filename != '':
        try:
            upload_result = cloudinary.uploader.upload(file_obj)
            return upload_result.get("secure_url")
        except Exception as e:
            logging.error(f"Erro no upload do Cloudinary: {e}")
    return None

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

@app.route("/api/produtos")
def api_produtos():
    return jsonify({"produtos": get_cached_catalog()})

# ======================================================
# CHECKOUT / REGISTAR PEDIDO
# ======================================================
@app.route("/checkout", methods=["POST"])
def checkout():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Dados do pedido inválidos."}), 400

        novo_pedido = {
            "cliente": data.get("cliente"),
            "contacto": data.get("contacto"),
            "itens": json.dumps(data.get("itens", [])),
            "total": data.get("total", 0),
            "status": "Pendente",
            "data": hora_mocambique()
        }

        add_order(novo_pedido)
        return jsonify({"success": True, "message": "Pedido registado com sucesso!"})
    except Exception as e:
        logging.error(f"Erro ao processar checkout: {e}")
        return jsonify({"success": False, "message": "Erro ao gravar o pedido."}), 500

# ======================================================
# PAINEL ADMINISTRATIVO (ADMIN)
# ======================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        senha = request.form.get("senha")
        admin_pass = getattr(Config, 'ADMIN_PASSWORD', 'admin123')
        if senha == admin_pass:
            session["admin_logged_in"] = True
            flash("Sessão iniciada com sucesso!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Senha incorreta!", "danger")
    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Sessão encerrada.", "warning")
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    produtos = get_cached_catalog()
    pedidos = get_orders()
    return render_template("admin.html", produtos=produtos, pedidos=pedidos)

@app.route("/admin/add", methods=["POST"])
@admin_required
def admin_add_product():
    foto_file = request.files.get("foto_file")
    foto_url = request.form.get("fotos")

    # Se um arquivo de imagem foi enviado, realiza o upload no Cloudinary
    if foto_file and foto_file.filename != '':
        cloud_url = upload_foto(foto_file)
        if cloud_url:
            foto_url = cloud_url

    novo_produto = {
        "nome": request.form.get("nome"),
        "categoria": request.form.get("categoria"),
        "preco": float(request.form.get("preco", 0)),
        "tamanhos": request.form.get("tamanhos"),
        "cores": request.form.get("cores"),
        "fotos": foto_url,
        "descricao": request.form.get("descricao")
    }

    add_product(novo_produto)
    invalidate_catalog_cache()
    flash("Produto adicionado com sucesso!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit/<produto_id>", methods=["POST"])
@admin_required
def admin_edit_product(produto_id):
    foto_file = request.files.get("foto_file")
    foto_url = request.form.get("fotos") or request.form.get("foto_antiga")

    if foto_file and foto_file.filename != '':
        cloud_url = upload_foto(foto_file)
        if cloud_url:
            foto_url = cloud_url

    produto_atualizado = {
        "nome": request.form.get("nome"),
        "categoria": request.form.get("categoria"),
        "preco": float(request.form.get("preco", 0)),
        "tamanhos": request.form.get("tamanhos"),
        "cores": request.form.get("cores"),
        "fotos": foto_url,
        "descricao": request.form.get("descricao")
    }

    update_product(produto_id, produto_atualizado)
    invalidate_catalog_cache()
    flash("Produto atualizado com sucesso!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<produto_id>", methods=["POST"])
@admin_required
def admin_delete_product(produto_id):
    delete_product(produto_id)
    invalidate_catalog_cache()
    flash("Produto removido com sucesso!", "warning")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/pedido/status/<pedido_id>", methods=["POST"])
@admin_required
def admin_update_order_status(pedido_id):
    data = request.get_json()
    novo_status = data.get("status") if data else None
    
    if novo_status and update_order_status(pedido_id, novo_status):
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

if __name__ == "__main__":
    app.run(debug=True)
