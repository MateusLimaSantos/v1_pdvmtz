import sqlite3
from config import TIPOS_PESO, UNIDADE_LABEL, DESCONTO_MAX_OPERADOR
from core.database import get_db_connection
from core.helpers import _iso_now, _fmt_data, get_config
from core.state import state
from core.fiscal.pix import gerar_pdf_pix
from core.fiscal.cupom import formatar_cupom, exportar_pdf_cupom


def buscar_produto_por_ean(ean: str) -> dict | None:
    """Retorna item padronizado para o carrinho, ou None se EAN não encontrado."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM produtos WHERE ean=?", (ean,)).fetchone()
        if row:
            p = dict(row)
            return {
                "ean_bipado": ean,
                "ean_base": ean,
                "nome_exibicao": p["nome"],
                "tipo_unidade": p["tipo_unidade"],
                "preco_unitario": p["preco_venda"],
                "preco_referencia": p["preco_referencia"] or p["preco_venda"],
                "qtd_desconto": 1.0,
                "preco_total": p["preco_venda"],
                "estoque_disponivel": p["estoque_atual"],
                "desconto_item": 0.0,
            }
        emb = conn.execute(
            "SELECT * FROM embalagens WHERE ean_embalagem=?", (ean,)
        ).fetchone()
        if emb:
            pr = conn.execute(
                "SELECT * FROM produtos WHERE ean=?", (emb["produto_base_ean"],)
            ).fetchone()
            if pr:
                p, e = dict(pr), dict(emb)
                fator = e["fator_conversao"]
                preco = (
                    e["preco_venda"] if e["preco_venda"] else p["preco_venda"] * fator
                )
                return {
                    "ean_bipado": ean,
                    "ean_base": e["produto_base_ean"],
                    "nome_exibicao": f"{p['nome']} ({e['tipo']} c/{int(fator)})",
                    "tipo_unidade": p["tipo_unidade"],
                    "preco_unitario": p["preco_venda"],
                    "preco_referencia": p["preco_referencia"] or p["preco_venda"],
                    "qtd_desconto": fator,
                    "preco_total": preco,
                    "estoque_disponivel": p["estoque_atual"],
                    "desconto_item": 0.0,
                }
    return None


def registrar_peso(item: dict, peso: float) -> tuple[bool, str]:
    """
    Valida e aplica o peso informado para um item vendido por peso/volume.
    Modifica `item` em memória (qtd_desconto e preco_total).
    Retorna (sucesso, mensagem_de_erro_se_houver).
    """
    un = item["tipo_unidade"]
    if peso <= 0:
        return False, "Peso inválido."
    if peso > item["estoque_disponivel"]:
        return (
            False,
            f"Estoque insuficiente. Disponível: {item['estoque_disponivel']:.3f} {un}",
        )
    item["qtd_desconto"] = peso
    item["preco_total"] = round(item["preco_referencia"] * peso, 2)
    item["desconto_item"] = 0.0
    return True, ""


def adicionar_item_ao_carrinho(
    itens_carrinho: list[dict], item_lido: dict
) -> tuple[bool, str]:
    """
    Adiciona (ou soma à quantidade de) um item unitário no carrinho.
    Não usar para itens por peso — aplique registrar_peso antes e faça o append manualmente.
    Retorna (sucesso, mensagem_de_erro_se_houver).
    """
    existente = next(
        (i for i in itens_carrinho if i["ean_bipado"] == item_lido["ean_bipado"]), None
    )
    if existente:
        nova_qtd = existente["qtd_desconto"] + item_lido["qtd_desconto"]
        if item_lido["estoque_disponivel"] < nova_qtd:
            return (
                False,
                f"Estoque insuficiente. Disponível: {item_lido['estoque_disponivel']:.2f}",
            )
        existente["qtd_desconto"] = nova_qtd
        existente["preco_total"] = round(
            existente["preco_unitario"] * nova_qtd - existente.get("desconto_item", 0),
            2,
        )
        return True, ""
    else:
        if item_lido["estoque_disponivel"] < item_lido["qtd_desconto"]:
            return False, "Estoque insuficiente."
        itens_carrinho.append(item_lido)
        return True, ""


def remover_item_indice(itens_carrinho: list[dict], indice: int) -> tuple[bool, str]:
    """Remove um item do carrinho pelo índice (0-based). Retorna (sucesso, nome_removido_ou_erro)."""
    if not (0 <= indice < len(itens_carrinho)):
        return False, "Número inválido."
    nome = itens_carrinho.pop(indice)["nome_exibicao"]
    return True, nome


def alterar_quantidade_indice(
    itens_carrinho: list[dict], indice: int, nova_qtd: float
) -> tuple[bool, str]:
    """Altera a quantidade de um item do carrinho pelo índice. Retorna (sucesso, mensagem)."""
    if not (0 <= indice < len(itens_carrinho)):
        return False, "Número inválido."
    if nova_qtd <= 0:
        return False, "Deve ser maior que zero."

    item = itens_carrinho[indice]
    info = buscar_produto_por_ean(item["ean_bipado"])
    estoque_disp = info["estoque_disponivel"] if info else 0
    if estoque_disp < nova_qtd:
        return False, f"Estoque insuficiente. Disponível: {estoque_disp:.3f}"

    item["qtd_desconto"] = nova_qtd
    item["preco_total"] = round(
        item["preco_referencia"] * nova_qtd - item.get("desconto_item", 0), 2
    )
    return True, f"Qtd atualizada: {item['nome_exibicao']} → {nova_qtd}"


def total_bruto_carrinho(itens_carrinho: list[dict]) -> float:
    return sum(i["preco_total"] for i in itens_carrinho)


def limite_desconto_operador() -> float:
    """Limite de desconto percentual: sem limite para admin, DESCONTO_MAX_OPERADOR para operador."""
    is_admin = state.operador and state.operador["perfil"] == "admin"
    return 100.0 if is_admin else DESCONTO_MAX_OPERADOR


def calcular_desconto_valor(
    total_bruto: float, valor_desconto: float
) -> tuple[bool, float, str]:
    """Valida e calcula desconto informado em R$. Retorna (ok, valor_aplicado, erro)."""
    lim = limite_desconto_operador()
    pct_equiv = valor_desconto / total_bruto * 100 if total_bruto else 0
    if pct_equiv > lim:
        return (
            False,
            0.0,
            f"Desconto excede o limite ({lim:.0f}%). Requer autorização de admin.",
        )
    if valor_desconto > total_bruto:
        return False, 0.0, "Desconto maior que o total."
    return True, round(valor_desconto, 2), ""


def calcular_desconto_percentual(
    total_bruto: float, pct: float
) -> tuple[bool, float, str]:
    """Valida e calcula desconto informado em %. Retorna (ok, valor_aplicado, erro)."""
    lim = limite_desconto_operador()
    if pct > lim:
        return False, 0.0, f"Excede o limite ({lim:.0f}%). Requer autorização de admin."
    return True, round(total_bruto * pct / 100, 2), ""


def produtos_estoque_baixo(itens_vendidos: list[dict]) -> list[dict]:
    """Verifica se algum item vendido ficou com estoque <= mínimo após a venda."""
    eans = {i["ean_base"] for i in itens_vendidos}
    alertas = []
    with get_db_connection() as conn:
        for ean in eans:
            row = conn.execute(
                "SELECT nome, estoque_atual, estoque_minimo FROM produtos WHERE ean=?",
                (ean,),
            ).fetchone()
            if row and row["estoque_atual"] <= row["estoque_minimo"]:
                alertas.append(dict(row))
    return alertas


def formas_pagamento_disponiveis() -> list[str]:
    formas = ["Dinheiro"]
    if get_config("pix_ativo") == "True":
        formas.append("PIX")
    if get_config("cartao_ativo") == "True":
        formas.append("Cartao")
    return formas


def calcular_troco(total: float, valor_recebido: float) -> tuple[bool, float, str]:
    """Calcula troco para pagamento em dinheiro. Retorna (ok, troco, erro)."""
    if valor_recebido < total:
        return False, 0.0, f"Faltam R$ {total - valor_recebido:.2f}."
    return True, round(valor_recebido - total, 2), ""


def gerar_qrcode_pix_para_venda(total: float) -> tuple[bool, str]:
    """Gera o PDF do QR Code PIX. Retorna (sucesso, caminho_ou_erro)."""
    return gerar_pdf_pix(total)


def produtos_cadastrados_existem() -> bool:
    with get_db_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0


def finalizar_venda(
    itens_carrinho: list[dict],
    desconto_venda: float,
    forma_pagamento: str,
    troco: float,
) -> tuple[bool, str, dict | None]:
    """
    Persiste a venda no banco: atualiza estoque, grava venda e itens.
    Retorna (sucesso, mensagem, dados_da_venda) onde dados_da_venda contém
    venda_id, cupom_texto e a lista de alertas de estoque baixo (se sucesso).
    """
    if not itens_carrinho:
        return False, "Carrinho vazio.", None

    if state._finalizando:
        return False, "Venda já está sendo processada.", None
    state._finalizando = True

    total_bruto = total_bruto_carrinho(itens_carrinho)
    total_final = max(0.0, round(total_bruto - desconto_venda, 2))

    itens_cupom = [
        {
            "nome": i["nome_exibicao"],
            "qtd": i["qtd_desconto"],
            "tipo_unidade": i.get("tipo_unidade", "unidade"),
            "preco_total": i["preco_total"],
            "desconto_item": i.get("desconto_item", 0),
        }
        for i in itens_carrinho
    ]

    cupom_texto, data_iso = formatar_cupom(
        itens_cupom, total_final, desconto_venda, forma_pagamento, troco
    )

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            for item in itens_carrinho:
                cur.execute(
                    "UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE ean=?",
                    (item["qtd_desconto"], item["ean_base"]),
                )
                cur.execute(
                    "INSERT INTO movimentacoes_estoque "
                    "(produto_ean, data_hora, tipo, qtd, motivo, operador_id) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        item["ean_base"],
                        data_iso,
                        "venda",
                        -item["qtd_desconto"],
                        "Venda PDV",
                        state.operador["id"],
                    ),
                )

            cur.execute(
                "INSERT INTO vendas "
                "(caixa_id, operador_id, data_hora, total, desconto, "
                "forma_pagamento, troco, cupom_texto) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    state.caixa_id,
                    state.operador["id"],
                    data_iso,
                    total_final,
                    desconto_venda,
                    forma_pagamento,
                    troco,
                    cupom_texto,
                ),
            )
            venda_id = cur.lastrowid

            for item in itens_carrinho:
                cur.execute(
                    "INSERT INTO itens_venda "
                    "(venda_id, produto_ean, nome_exibicao, tipo_unidade, "
                    "preco_unitario, qtd, desconto_item, preco_total) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        venda_id,
                        item["ean_base"],
                        item["nome_exibicao"],
                        item.get("tipo_unidade", "unidade"),
                        item["preco_unitario"],
                        item["qtd_desconto"],
                        item.get("desconto_item", 0),
                        item["preco_total"],
                    ),
                )

        alertas = produtos_estoque_baixo(itens_carrinho)
        return (
            True,
            f"Venda #{venda_id} registrada com sucesso!",
            {
                "venda_id": venda_id,
                "cupom_texto": cupom_texto,
                "alertas_estoque": alertas,
                "total_final": total_final,
            },
        )

    except sqlite3.IntegrityError as e:
        return False, f"ERRO DE INTEGRIDADE: {e} — transação desfeita.", None
    except sqlite3.OperationalError as e:
        return False, f"ERRO OPERACIONAL: {e} — transação desfeita.", None
    finally:
        state._finalizando = False


def exportar_cupom_pdf(cupom_texto: str, venda_id: int) -> str:
    return exportar_pdf_cupom(cupom_texto, numero_nota=venda_id)


# ─────────────────────────────────────────
# CANCELAMENTO DE VENDA
# ─────────────────────────────────────────


def buscar_venda(venda_id: int) -> tuple[dict | None, list[dict]]:
    """Retorna (venda, itens) ou (None, []) se não encontrada."""
    with get_db_connection() as conn:
        venda = conn.execute("SELECT * FROM vendas WHERE id=?", (venda_id,)).fetchone()
        if not venda:
            return None, []
        itens = [
            dict(i)
            for i in conn.execute(
                "SELECT * FROM itens_venda WHERE venda_id=?", (venda_id,)
            ).fetchall()
        ]
        return dict(venda), itens


def cancelar_venda(venda_id: int, motivo: str) -> tuple[bool, str]:
    """
    Cancela uma venda, restaura o estoque dos itens e registra o motivo.
    Apenas administradores podem cancelar (a checagem de perfil é responsabilidade da GUI,
    mas é reforçada aqui também).
    Retorna (sucesso, mensagem).
    """
    if not (state.operador and state.operador["perfil"] == "admin"):
        return False, "Acesso restrito a administradores."

    venda, itens = buscar_venda(venda_id)
    if not venda:
        return False, "Venda não encontrada."
    if venda["status"] == "cancelada":
        return False, "Já cancelada."
    if not motivo.strip():
        return False, "Informe o motivo."

    try:
        with get_db_connection() as conn:
            for item in itens:
                conn.execute(
                    "UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE ean=?",
                    (item["qtd"], item["produto_ean"]),
                )
                conn.execute(
                    "INSERT INTO movimentacoes_estoque "
                    "(produto_ean, data_hora, tipo, qtd, motivo, operador_id) VALUES (?,?,?,?,?,?)",
                    (
                        item["produto_ean"],
                        _iso_now(),
                        "estorno",
                        item["qtd"],
                        f"Cancelamento venda #{venda_id}",
                        state.operador["id"],
                    ),
                )
            conn.execute(
                "UPDATE vendas SET status='cancelada', motivo_cancelamento=? WHERE id=?",
                (motivo, venda_id),
            )
        return True, f"Venda #{venda_id} cancelada e estoque restaurado."
    except Exception as e:
        return False, f"Erro: {e}"
