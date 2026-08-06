import os
import json
import time
import logging
import urllib.parse
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ======================================================
# CONFIGURAÇÃO DE LOGS (Para monitorização no Render/Terminal)
# ======================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave_secreta_padrao_loja_roupas")

# ======================================================
# CLASSE DE CONFIGURAÇÃO DO SISTEMA
# ======================================================
class Config:
    NOME_LOJA = os.environ.get("NOME_LOJA", "Minha Loja de Roupas")
    WHATSAPP_NUMERO = os.environ.get("WHATSAPP_NUMERO", "258840000000")
    SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
    GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    ABA_PRODUTOS = os.environ.get("ABA_PRODUTOS", "Produtos")
    ABA_UTILIZADORES = os.environ.get("ABA_UTILIZADORES", "Utilizadores")
    ABA_ENCOMENDAS = os.environ.get("ABA_ENCOMENDAS", "Encomendas")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@loja.com")

# ======================================================
# CONEXÃO COM GOOGLE SHEETS
# ======================================================
def get_gspread_client():
    """Autentica na API do Google Sheets usando a variável de ambiente ou ficheiro local."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds_json = Config.GOOGLE_CREDENTIALS_JSON
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
        except Exception as e:
            logging.error(f"Erro ao carregar credenciais JSON da variável de ambiente: {e}")
            return None
    elif os.path.exists("credentials.json"):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            return gspread.authorize(creds)
        except Exception as e:
            logging.error(f"Erro ao carregar ficheiro credentials.json: {e}")
            return None
    else:
        logging.error("Nenhuma credencial do Google Sheets encontrada.")
        return None

def get_worksheet(sheet_name):
    """Obtém uma aba específica da planilha configurada."""
    client = get_gspread_client()
    if not client or not Config.SPREADSHEET_ID:
        logging.error("Cliente gspread não inicializado ou SPREADSHEET_ID ausente.")
        return None
    try:
        sheet = client.open_by_key(Config.SPREADSHEET_ID)
        return sheet.worksheet(sheet_name)
    except Exception as e:
        logging.error(f"Erro ao aceder à aba '{sheet_name}': {e}")
        return None

# ======================================================
# CARREGAMENTO DO CATÁLOGO DE PRODUTOS
# ======================================================
def load_catalog():
    """Carrega os produtos da folha de cálculo e higieniza os dados."""
    sheet = get_worksheet(Config.ABA_PRODUTOS)
    if not sheet:
        logging.warning("Não foi possível aceder à aba de produtos.")
        return []

    try:
        records = sheet.get_all_records()
        produtos = []
        
        for idx, r in enumerate(records):
            item = {str(k).strip().lower(): v for k, v in r.items()}
            
            nome = str(item.get("nome", "")).strip()
            if not nome:
                continue
            
            disp_raw = str(item.get("disponivel", "SIM")).strip().upper()
            disponivel = disp_raw in ["SIM", "YES", "1", "TRUE", "S"]

            preco_raw = str(item.get("preco", "0")).replace("MT", "").replace(",", ".").strip()
            try:
                preco = float(preco_raw)
            except ValueError:
                preco = 0.0

            produto = {
                "id": str(item.get("id", idx + 1)),
                "nome": nome,
                "categoria": str(item.get("categoria", "Geral")).strip(),
                "preco": preco,
                "descricao": str(item.get("descricao", "")).strip(),
                "tamanhos": str(item.get("tamanhos", "Único")).strip(),
                "cores": str(item.get("cores", "Padrão")).strip(),
                "fotos": str(item.get("fotos", "")).strip(),
                "disponivel": disponivel
            }
            produtos.append(produto)

        logging.info(f"Catálogo processado: {len(produtos)} produtos carregados com sucesso.")
        return produtos
    except Exception as e:
        logging.error(f"Erro ao processar dados da folha de produtos: {e}")
        return []

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
        logging.info(f"==> Cache do catálogo renovado: {len(CACHE_PRODUTOS)} itens armazenados.")

    return CACHE_PRODUTOS

def invalidate_catalog_cache():
    """Força a limpeza da memória cache para refletir atualizações imediatas."""
    global CACHE_PRODUTOS
    CACHE_PRODUTOS = None

# ======================================================
# ROTAS PRINCIPAIS DA LOJA
# ======================================================
@app.route("/")
def index():
    produtos = get_cached_catalog()
    
    print(f"\n--- [DEBUG ROTA INDEX] ---")
    print(f"Total de produtos na cache: {len(produtos)}")
    if produtos:
        print(f"Exemplo do 1º Produto: {produtos[0]}")
    else:
        print("[ALERTA] A lista de produtos retornou VAZIA do Google Sheets!")
    print("----------------------------\n")

    produtos_visiveis = [p for p in produtos if p.get("disponivel", True)]

    categorias = sorted(list(set(
        p.get("categoria", "Geral") for p in produtos_visiveis if p.get("categoria")
    )))

    return render_template(
        "loja.html",
        produtos=produtos_visiveis,
        categorias=categorias,
        config=Config
    )

@app.route("/produto/<id_produto>")
def detalhe_produto(id_produto):
    produtos = get_cached_catalog()
    produto = next((p for p in produtos if str(p["id"]) == str(id_produto)), None)
    
    if not produto:
        flash("Produto não encontrado.", "warning")
        return redirect(url_for("index"))
        
    return render_template("produto_detalhe.html", produto=produto, config=Config)

# ======================================================
# GESTÃO DA SACOLA DE COMPRAS (SESSÃO)
# ======================================================
@app.route("/sacola")
def ver_sacola():
    sacola = session.get("sacola", [])
    total = sum(item["preco"] * item["quantidade"] for item in sacola)
    return render_template("sacola.html", sacola=sacola, total=total, config=Config)

@app.route("/sacola/adicionar", methods=["POST"])
def adicionar_sacola():
    dados = request.form
    id_produto = str(dados.get("id"))
    tamanho = dados.get("tamanho", "Único")
    cor = dados.get("cor", "Padrão")
    quantidade = int(dados.get("quantidade", 1))

    produtos = get_cached_catalog()
    produto = next((p for p in produtos if str(p["id"]) == id_produto), None)

    if produto:
        sacola = session.get("sacola", [])
        
        item_existente = next((i for i in sacola if i["id"] == id_produto and i["tamanho"] == tamanho and i["cor"] == cor), None)
        
        if item_existente:
            item_existente["quantidade"] += quantidade
        else:
            sacola.append({
                "id": produto["id"],
                "nome": produto["nome"],
                "preco": produto["preco"],
                "tamanho": tamanho,
                "cor": cor,
                "quantidade": quantidade,
                "foto": produto["fotos"]
            })

        session["sacola"] = sacola
        flash(f"'{produto['nome']}' adicionado à sacola!", "success")

    return redirect(url_for("ver_sacola"))

@app.route("/sacola/remover/<int:index>")
def remover_sacola(index):
    sacola = session.get("sacola", [])
    if 0 <= index < len(sacola):
        item_removido = sacola.pop(index)
        session["sacola"] = sacola
        flash(f"'{item_removido['nome']}' removido da sacola.", "info")
    return redirect(url_for("ver_sacola"))

# ======================================================
# FINALIZAÇÃO DE ENCOMENDA (CHECKOUT)
# ======================================================
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    sacola = session.get("sacola", [])
    if not sacola:
        flash("A sua sacola está vazia.", "warning")
        return redirect(url_for("index"))

    total = sum(item["preco"] * item["quantidade"] for item in sacola)

    if request.method == "POST":
        cliente_nome = request.form.get("nome")
        cliente_telefone = request.form.get("telefone")
        cliente_endereco = request.form.get("endereco")
        metodo_pagamento = request.form.get("pagamento", "M-Pesa / Em numerário")

        sheet_encomendas = get_worksheet(Config.ABA_ENCOMENDAS)
        resumo_itens = "; ".join([f"{i['quantidade']}x {i['nome']} ({i['tamanho']}/{i['cor']})" for i in sacola])

        if sheet_encomendas:
            try:
                sheet_encomendas.append_row([
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    cliente_nome,
                    cliente_telefone,
                    cliente_endereco,
                    resumo_itens,
                    total,
                    metodo_pagamento,
                    "Pendente"
                ])
            except Exception as e:
                logging.error(f"Erro ao registar encomenda no Google Sheets: {e}")

        msg_wa = f"*NOVO PEDIDO - {Config.NOME_LOJA}*\n\n"
        msg_wa += f"*Cliente:* {cliente_nome}\n"
        msg_wa += f"*Contacto:* {cliente_telefone}\n"
        msg_wa += f"*Endereço:* {cliente_endereco}\n\n"
        msg_wa += "*ITENS:* \n"
        for i in sacola:
            msg_wa += f"• {i['quantidade']}x {i['nome']} ({i['tamanho']}, {i['cor']}) - {i['preco'] * i['quantidade']} MT\n"
        msg_wa += f"\n*TOTAL:* {total:.2f} MT\n"
        msg_wa += f"*Pagamento:* {metodo_pagamento}"

        session.pop("sacola", None)
        url_whatsapp = f"https://wa.me/{Config.WHATSAPP_NUMERO}?text={urllib.parse.quote(msg_wa)}"
        return redirect(url_whatsapp)

    return render_template("checkout.html", sacola=sacola, total=total, config=Config)

# ======================================================
# AUTENTICAÇÃO DE UTILIZADORES (LOGIN / REGISTO / LOGOUT)
# ======================================================
@app.route("/registo", methods=["GET", "POST"])
def registo():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha")

        sheet_users = get_worksheet(Config.ABA_UTILIZADORES)
        if not sheet_users:
            flash("Erro ao aceder à base de dados de utilizadores.", "danger")
            return redirect(url_for("registo"))

        try:
            records = sheet_users.get_all_records()
            for r in records:
                if str(r.get("email", "")).strip().lower() == email:
                    flash("Este email já está registado.", "warning")
                    return redirect(url_for("registo"))

            senha_hash = generate_password_hash(senha)
            novo_id = len(records) + 1
            sheet_users.append_row([novo_id, nome, email, senha_hash, "Cliente"])

            flash("Registo efetuado com sucesso! Faça login para continuar.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            logging.error(f"Erro ao registar utilizador: {e}")
            flash("Erro interno ao efetuar registo.", "danger")

    return render_template("registo.html", config=Config)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha")

        # Atalho para Administrador Master definido por variável de ambiente
        if email == Config.ADMIN_EMAIL.lower() and senha == os.environ.get("ADMIN_PASSWORD", "admin123"):
            session["user"] = {"nome": "Administrador", "email": email, "tipo": "Admin"}
            flash("Bem-vindo, Administrador!", "success")
            return redirect(url_for("admin_dashboard"))

        sheet_users = get_worksheet(Config.ABA_UTILIZADORES)
        if sheet_users:
            try:
                records = sheet_users.get_all_records()
                for r in records:
                    if str(r.get("email", "")).strip().lower() == email:
                        if check_password_hash(r.get("senha_hash", ""), senha):
                            session["user"] = {
                                "id": r.get("id"),
                                "nome": r.get("nome"),
                                "email": email,
                                "tipo": r.get("tipo", "Cliente")
                            }
                            flash(f"Bem-vindo de volta, {r.get('nome')}!", "success")
                            return redirect(url_for("index"))
                        else:
                            flash("Palavra-passe incorreta.", "danger")
                            return redirect(url_for("login"))
                flash("Utilizador não encontrado.", "warning")
            except Exception as e:
                logging.error(f"Erro na autenticação: {e}")
                flash("Erro ao processar login.", "danger")

    return render_template("login.html", config=Config)

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Sessão terminada.", "info")
    return redirect(url_for("index"))

# ======================================================
# PAINEL DE ADMINISTRAÇÃO DA LOJA (CRUD DE PRODUTOS)
# ======================================================
def is_admin():
    user = session.get("user")
    return user and user.get("tipo") == "Admin"

@app.route("/admin")
def admin_dashboard():
    if not is_admin():
        flash("Acesso negado. Inicie sessão como Administrador.", "danger")
        return redirect(url_for("login"))

    produtos = load_catalog()  # Carrega direto da planilha (sem cache)
    
    sheet_encomendas = get_worksheet(Config.ABA_ENCOMENDAS)
    encomendas = []
    if sheet_encomendas:
        try:
            encomendas = sheet_encomendas.get_all_records()
        except Exception as e:
            logging.error(f"Erro ao carregar encomendas: {e}")

    return render_template("admin.html", produtos=produtos, encomendas=encomendas, config=Config)

@app.route("/admin/produto/novo", methods=["POST"])
def admin_novo_produto():
    if not is_admin():
        return jsonify({"success": False, "message": "Não autorizado"}), 403

    sheet = get_worksheet(Config.ABA_PRODUTOS)
    if not sheet:
        flash("Não foi possível aceder à planilha.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        records = sheet.get_all_records()
        novo_id = len(records) + 1
        
        novo_row = [
            novo_id,
            request.form.get("nome"),
            request.form.get("categoria"),
            request.form.get("preco"),
            request.form.get("descricao"),
            request.form.get("tamanhos"),
            request.form.get("cores"),
            request.form.get("fotos"),
            "SIM" if request.form.get("disponivel") == "on" else "NÃO"
        ]
        
        sheet.append_row(novo_row)
        invalidate_catalog_cache()
        flash("Produto adicionado com sucesso!", "success")
    except Exception as e:
        logging.error(f"Erro ao adicionar produto: {e}")
        flash("Erro ao salvar produto.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/produto/apagar/<id_produto>")
def admin_apagar_produto(id_produto):
    if not is_admin():
        flash("Não autorizado.", "danger")
        return redirect(url_for("login"))

    sheet = get_worksheet(Config.ABA_PRODUTOS)
    if sheet:
        try:
            cell = sheet.find(str(id_produto))
            if cell:
                sheet.delete_rows(cell.row)
                invalidate_catalog_cache()
                flash("Produto removido!", "info")
            else:
                flash("Produto não encontrado.", "warning")
        except Exception as e:
            logging.error(f"Erro ao apagar produto: {e}")
            flash("Erro ao apagar produto.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/cache/limpar")
def admin_limpar_cache():
    if not is_admin():
        flash("Não autorizado.", "danger")
        return redirect(url_for("login"))
        
    invalidate_catalog_cache()
    flash("Memória cache atualizada!", "success")
    return redirect(url_for("admin_dashboard"))

# ======================================================
# ENDPOINTS API JSON
# ======================================================
@app.route("/api/produtos")
def api_produtos():
    produtos = get_cached_catalog()
    return jsonify({"total": len(produtos), "produtos": produtos})

# ======================================================
# INICIALIZAÇÃO DA APLICAÇÃO
# ======================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
