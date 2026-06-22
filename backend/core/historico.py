from config import TIPOS_PESO, UNIDADE_LABEL
from core.helpers import _fmt_data
from core.database import get_db_connection


def listar_vendas(limite: int = 50) -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM vendas ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    resultado = []
    for v in rows:
        d = dict(v)
        d["data_hora_fmt"] = _fmt_data(d["data_hora"])
        resultado.append(d)
    return resultado


def detalhes_venda(venda_id: int) -> dict | None:
    """Retorna a venda com seus itens formatados, ou None se não encontrada."""
    with get_db_connection() as conn:
        venda = conn.execute("SELECT * FROM vendas WHERE id=?", (venda_id,)).fetchone()
        if not venda:
            return None
        itens = [
            dict(i)
            for i in conn.execute(
                "SELECT * FROM itens_venda WHERE venda_id=?", (venda_id,)
            ).fetchall()
        ]

    venda_dict = dict(venda)
    venda_dict["data_hora_fmt"] = _fmt_data(venda_dict["data_hora"])

    for item in itens:
        un = UNIDADE_LABEL.get(item.get("tipo_unidade", "unidade"), "un")
        item["qtd_fmt"] = (
            f"{item['qtd']:.3f}{un}"
            if item.get("tipo_unidade") in TIPOS_PESO
            else f"{item['qtd']:.0f}x"
        )

    venda_dict["itens"] = itens
    return venda_dict