from core.database import get_db_connection


def produtos_estoque_baixo(itens_vendidos: list[dict]) -> list[dict]:
    """Verifica se algum item vendido ficou com estoque <= minimo apos a venda."""
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
