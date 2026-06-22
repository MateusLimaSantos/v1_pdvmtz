from core.database import get_db_connection
from core.helpers import _iso_now, _fmt_data
from core.state import state


def caixa_aberto_no_banco() -> int | None:
    """Retorna o ID do caixa aberto no banco, ou None."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT id FROM abertura_caixa WHERE status='aberto' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row["id"] if row else None


def abrir_caixa(fundo: float) -> tuple[bool, str]:
    """
    Abre um novo caixa com o fundo de troco informado.
    Se já houver um caixa aberto no banco, apenas recupera o id.
    Retorna (sucesso, mensagem).
    """
    caixa_banco = caixa_aberto_no_banco()
    if caixa_banco:
        state.caixa_id = caixa_banco
        return True, f"Caixa #{caixa_banco} já estava aberto (recuperado)."

    if fundo < 0:
        return False, "Fundo não pode ser negativo."

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO abertura_caixa (operador_id, data_hora_abr, fundo_troco) VALUES (?,?,?)",
            (state.operador["id"], _iso_now(), fundo),
        )
        state.caixa_id = cur.lastrowid
    return True, f"Caixa #{state.caixa_id} aberto com fundo de R$ {fundo:.2f}."


def resumo_fechamento_caixa() -> dict | None:
    """Monta os dados de fechamento do caixa atual, sem fechar. None se não há caixa aberto."""
    if not state.caixa_id:
        return None

    with get_db_connection() as conn:
        caixa_row = conn.execute(
            "SELECT * FROM abertura_caixa WHERE id=?", (state.caixa_id,)
        ).fetchone()
        if not caixa_row:
            return None
        caixa = dict(caixa_row)
        vendas = [
            dict(v)
            for v in conn.execute(
                "SELECT * FROM vendas WHERE caixa_id=? AND status='concluida'",
                (state.caixa_id,),
            ).fetchall()
        ]

    totais: dict[str, float] = {}
    total_geral = 0.0
    total_troco = sum(v["troco"] for v in vendas)

    for v in vendas:
        totais[v["forma_pagamento"]] = (
            totais.get(v["forma_pagamento"], 0.0) + v["total"]
        )
        total_geral += v["total"]

    total_em_caixa = total_geral + caixa["fundo_troco"] - total_troco

    return {
        "caixa_id": state.caixa_id,
        "abertura_fmt": _fmt_data(caixa["data_hora_abr"]),
        "fundo_troco": caixa["fundo_troco"],
        "qtd_vendas": len(vendas),
        "totais_por_forma": totais,
        "total_geral": total_geral,
        "total_troco": total_troco,
        "total_em_caixa": total_em_caixa,
    }


def fechar_caixa() -> tuple[bool, str]:
    """Fecha o caixa atual. Retorna (sucesso, mensagem)."""
    if not state.caixa_id:
        return False, "Nenhum caixa aberto."

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE abertura_caixa SET data_hora_fec=?, status='fechado' WHERE id=?",
            (_iso_now(), state.caixa_id),
        )
    state.caixa_id = None
    return True, "Caixa fechado."
