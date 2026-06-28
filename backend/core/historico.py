from backend.config import TIPOS_PESO, UNIDADE_LABEL
from backend.core.helpers import _fmt_data
from backend.core.database import get_db_connection


def listar_vendas(
    limite: int = 50,
    data_ini_br: str | None = None,
    data_fim_br: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Lista vendas mais recentes primeiro, com nome do operador.

    data_ini_br/data_fim_br: opcional, no formato dd/mm/aaaa, filtra pelo dia.
    status: opcional, filtra por 'concluida' ou 'cancelada'.
    """
    query = (
        "SELECT v.*, o.nome AS operador_nome "
        "FROM vendas v "
        "JOIN operadores o ON o.id = v.operador_id "
        "WHERE 1=1"
    )
    params: list = []

    if data_ini_br:
        partes = data_ini_br.split("/")
        if len(partes) == 3:
            iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
            query += " AND date(v.data_hora) >= date(?)"
            params.append(iso)
    if data_fim_br:
        partes = data_fim_br.split("/")
        if len(partes) == 3:
            iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
            query += " AND date(v.data_hora) <= date(?)"
            params.append(iso)
    if status:
        query += " AND v.status = ?"
        params.append(status)

    query += " ORDER BY v.id DESC LIMIT ?"
    params.append(limite)

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    resultado = []
    for v in rows:
        d = dict(v)
        d["data_hora_fmt"] = _fmt_data(d["data_hora"])
        resultado.append(d)
    return resultado


def detalhes_venda(venda_id: int) -> dict | None:

    with get_db_connection() as conn:

        venda = conn.execute(
            """
            SELECT v.*, o.nome AS operador_nome 
            FROM vendas v
            LEFT JOIN operadores o ON v.operador_id = o.id
            WHERE v.id = ?
            """,
            (venda_id,),
        ).fetchone()

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

    if "operador_nome" not in venda_dict or venda_dict["operador_nome"] is None:
        venda_dict["operador_nome"] = "Não Informado"

    for item in itens:
        un = UNIDADE_LABEL.get(item.get("tipo_unidade", "unidade"), "un")
        item["qtd_fmt"] = (
            f"{item['qtd']:.3f}{un}"
            if item.get("tipo_unidade") in TIPOS_PESO
            else f"{item['qtd']:.0f}x"
        )

    venda_dict["itens"] = itens
    return venda_dict
