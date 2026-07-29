import os
import json
import logging
from services.google_service import get_sheet, sheet_to_dict

def load_catalog():
    """Carrega todos os produtos da aba Produtos."""
    try:
        sheet = get_sheet("Produtos")
        data = sheet_to_dict(sheet)
        produtos = []
        for r in data:
            if not r.get("Nome"):
                continue
            produtos.append({
                "id": str(r.get("ID", "")),
                "nome": r.get("Nome", ""),
                "categoria": r.get("Categoria", "Geral"),
                "preco": r.get("Preco", "0"),
                "tamanhos": r.get("Tamanhos", ""),
                "cores": r.get("Cores", ""),
                "stock": r.get("Stock", 1),
                "fotos": r.get("Fotos", ""),
                "descricao": r.get("Descricao", "")
            })
        return produtos
    except Exception as e:
        logging.error(f"Erro ao carregar catálogo: {e}")
        return []

def get_orders(sheet_name="Pedidos"):
    """Carrega os pedidos salvos na planilha formatando as chaves para o template."""
    try:
        sheet = get_sheet(sheet_name)
        data = sheet_to_dict(sheet)
        pedidos_formatados = []

        for i, r in enumerate(data, start=2):  # Linhas da folha (cabeçalho é 1)
            raw_itens = r.get("Itens_JSON") or r.get("Itens_Texto") or "[]"
            
            # Tenta decodificar o JSON se possível
            itens_parsed = []
            if isinstance(raw_itens, str) and raw_itens.startswith(("[", "{")):
                try:
                    itens_parsed = json.loads(raw_itens)
                except Exception:
                    itens_parsed = []

            pedidos_formatados.append({
                "id": str(r.get("ID") or f"PED-{i}"),
                "row_index": i,
                "nome": r.get("Cliente", "Cliente"),
                "contacto": r.get("Contacto", "N/A"),
                "pedido": r.get("Itens_Texto") or r.get("Itens") or "Sem detalhes",
                "itens": raw_itens,
                "itens_parsed": itens_parsed,
                "total": r.get("Total", "0"),
                "hora": r.get("Data") or r.get("Hora") or "N/A",
                "data": r.get("Data") or r.get("Hora") or "N/A",
                "status": r.get("Status", "Pendente")
            })

        return pedidos_formatados
    except Exception as e:
        logging.error(f"Erro ao carregar pedidos: {e}")
        return []

def add_order(sheet_name, cliente_nome, contacto_completo, cart_items, hora_str, status="Pendente"):
    """Salva um novo pedido na planilha."""
    try:
        sheet = get_sheet(sheet_name)
        
        # Formata o resumo em texto simples
        resumo_texto = []
        total_calculado = 0.0

        for item in cart_items:
            nome = item.get("nome", "Produto")
            qtd = int(item.get("quantidade") or item.get("qtd") or 1)
            preco = float(str(item.get("preco", 0)).replace("MT", "").replace(",", ".").strip() or 0)
            tam = item.get("tamanho") or item.get("tam") or ""
            cor = item.get("cor") or ""

            detalhes = f"{qtd}x {nome}"
            if tam or cor:
                detalhes += f" ({tam}/{cor})"
            resumo_texto.append(detalhes)
            total_calculado += (preco * qtd)

        itens_str = ", ".join(resumo_texto)
        itens_json = json.dumps(cart_items, ensure_ascii=False)

        # Gerar ID único
        existentes = sheet.get_all_records()
        novo_id = f"PED-{(len(existentes) + 1):03d}"

        nova_linha = [
            novo_id,
            cliente_nome,
            contacto_completo,
            itens_str,
            f"{total_calculado:.2f} MT",
            hora_str,
            status,
            itens_json
        ]

        sheet.append_row(nova_linha)
        return True
    except Exception as e:
        logging.error(f"Erro ao adicionar pedido: {e}")
        return False

def update_order_status(sheet_name, pedido_id, novo_status):
    """Atualiza o estado de um pedido pelo ID ou pelo índice da linha."""
    try:
        sheet = get_sheet(sheet_name)
        records = sheet.get_all_records()

        row_to_update = None
        for index, row in enumerate(records, start=2):
            if str(row.get("ID")) == str(pedido_id):
                row_to_update = index
                break

        if not row_to_update:
            # Tenta tratar pedido_id diretamente como número da linha se for numérico
            try:
                row_to_update = int(pedido_id)
            except ValueError:
                return False

        # Na nossa estrutura: Coluna 7 (G) é o Status
        sheet.update_cell(row_to_update, 7, novo_status)
        return True
    except Exception as e:
        logging.error(f"Erro ao atualizar status do pedido: {e}")
        return False

def add_product(produto_dict):
    """Adiciona um novo produto ao catálogo."""
    try:
        sheet = get_sheet("Produtos")
        records = sheet.get_all_records()
        novo_id = str(len(records) + 1)

        linha = [
            novo_id,
            produto_dict.get("nome", ""),
            produto_dict.get("categoria", "Geral"),
            produto_dict.get("preco", "0"),
            produto_dict.get("tamanhos", ""),
            produto_dict.get("cores", ""),
            produto_dict.get("stock", 1),
            produto_dict.get("fotos", ""),
            produto_dict.get("descricao", "")
        ]

        sheet.append_row(linha)
        return True
    except Exception as e:
        logging.error(f"Erro ao adicionar produto: {e}")
        return False

def update_product(produto_id, produto_dict):
    """Atualiza os dados de um produto existente."""
    try:
        sheet = get_sheet("Produtos")
        records = sheet.get_all_records()

        row_to_update = None
        for index, row in enumerate(records, start=2):
            if str(row.get("ID")) == str(produto_id):
                row_to_update = index
                break

        if not row_to_update:
            return False

        novos_valores = [
            str(produto_id),
            produto_dict.get("nome", ""),
            produto_dict.get("categoria", "Geral"),
            produto_dict.get("preco", "0"),
            produto_dict.get("tamanhos", ""),
            produto_dict.get("cores", ""),
            produto_dict.get("stock", 1),
            produto_dict.get("fotos", ""),
            produto_dict.get("descricao", "")
        ]

        cell_range = f"A{row_to_update}:I{row_to_update}"
        sheet.update(cell_range, [novos_valores])
        return True
    except Exception as e:
        logging.error(f"Erro ao atualizar produto: {e}")
        return False

def delete_product(produto_id):
    """Remove um produto da planilha pelo ID."""
    try:
        sheet = get_sheet("Produtos")
        records = sheet.get_all_records()

        for index, row in enumerate(records, start=2):
            if str(row.get("ID")) == str(produto_id):
                sheet.delete_rows(index)
                return True
        return False
    except Exception as e:
        logging.error(f"Erro ao eliminar produto: {e}")
        return False
