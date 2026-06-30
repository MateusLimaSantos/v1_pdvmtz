from core.database import get_db_connection


def buscar_produto_por_ean(ean: str) -> dict | None:
    """Retorna item padronizado para o carrinho, ou None se EAN nao encontrado."""
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
    Modifica `item` em memoria (qtd_desconto e preco_total).
    """
    un = item["tipo_unidade"]
    if peso <= 0:
        return False, "Peso invalido."
    if peso > item["estoque_disponivel"]:
        return (
            False,
            f"Estoque insuficiente. Disponivel: {item['estoque_disponivel']:.3f} {un}",
        )
    item["qtd_desconto"] = peso
    item["preco_total"] = round(item["preco_referencia"] * peso, 2)
    item["desconto_item"] = 0.0
    return True, ""


def produtos_cadastrados_existem() -> bool:
    with get_db_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0
