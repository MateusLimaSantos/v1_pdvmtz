import math
import sqlite3


from backend.core.database import get_db_connection
from backend.core.helpers import _iso_now, _fmt_data
from backend.core.state import state
from backend.core.auditoria import registrar_auditoria


def _e_numero_finito(valor: float) -> bool:
    """Rejeita inf, -inf e NaN, que passam despercebidos por checagens simples como 'valor < 0'."""
    return math.isfinite(valor)


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

    # --- PROTEÇÃO ADICIONADA AQUI ---
    if not state.operador:
        return False, "Erro: Nenhum operador logado no sistema. Faça login primeiro."
    # --------------------------------

    caixa_banco = caixa_aberto_no_banco()
    if caixa_banco:
        state.caixa_id = caixa_banco
        return True, f"Caixa #{caixa_banco} já estava aberto (recuperado)."

    if fundo < 0:
        return False, "Fundo não pode ser negativo."
    if not _e_numero_finito(fundo):
        return False, "Valor de fundo inválido."

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO abertura_caixa (operador_id, data_hora_abr, fundo_troco) VALUES (?,?,?)",
                (state.operador["id"], _iso_now(), fundo),
            )
            state.caixa_id = cur.lastrowid
        registrar_auditoria(
            "abrir_caixa", "caixa", state.caixa_id, f"Fundo inicial R$ {fundo:.2f}"
        )
        return True, f"Caixa #{state.caixa_id} aberto com fundo de R$ {fundo:.2f}."
    except sqlite3.IntegrityError:
        # Outro processo (outro PDV) abriu um caixa entre a verificação
        # acima e este INSERT. O índice único do banco bloqueou a
        # duplicidade; recuperamos o caixa que o outro processo abriu.
        caixa_concorrente = caixa_aberto_no_banco()
        if caixa_concorrente:
            state.caixa_id = caixa_concorrente
            return True, f"Caixa #{caixa_concorrente} já estava aberto (recuperado)."
        return False, "Não foi possível abrir o caixa. Tente novamente."


def registrar_sangria(valor: float, motivo: str) -> tuple[bool, str]:
    """Registra uma retirada de dinheiro do caixa (sangria). Retorna (sucesso, mensagem)."""
    return _registrar_movimentacao_caixa("sangria", valor, motivo)


def registrar_suprimento(valor: float, motivo: str) -> tuple[bool, str]:
    """Registra uma entrada extra de dinheiro no caixa (suprimento). Retorna (sucesso, mensagem)."""
    return _registrar_movimentacao_caixa("suprimento", valor, motivo)


def _registrar_movimentacao_caixa(
    tipo: str, valor: float, motivo: str
) -> tuple[bool, str]:
    if not state.caixa_id:
        return False, "Nenhum caixa aberto."
    if not _e_numero_finito(valor) or valor <= 0:
        return False, "Informe um valor maior que zero."
    if not motivo.strip():
        return False, "Informe o motivo."
    if not state.operador:
        return False, "Operador não identificado."

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO movimentacoes_caixa (caixa_id, operador_id, data_hora, tipo, valor, motivo) "
            "VALUES (?,?,?,?,?,?)",
            (
                state.caixa_id,
                state.operador["id"],
                _iso_now(),
                tipo,
                valor,
                motivo.strip(),
            ),
        )
    rotulo = "Sangria" if tipo == "sangria" else "Suprimento"
    registrar_auditoria(
        tipo, "caixa", state.caixa_id, f"R$ {valor:.2f} — {motivo.strip()}"
    )
    return True, f"{rotulo} de R$ {valor:.2f} registrada."


def listar_movimentacoes_caixa(caixa_id: int | None = None) -> list[dict]:
    """Lista sangrias e suprimentos do caixa indicado (ou do caixa atual, se None)."""
    cid = caixa_id if caixa_id is not None else state.caixa_id
    if not cid:
        return []
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT m.*, o.nome AS operador_nome FROM movimentacoes_caixa m "
            "JOIN operadores o ON o.id = m.operador_id "
            "WHERE m.caixa_id=? ORDER BY m.id DESC",
            (cid,),
        ).fetchall()
    resultado = []
    for r in rows:
        d = dict(r)
        d["data_hora_fmt"] = _fmt_data(d["data_hora"])
        resultado.append(d)
    return resultado


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

    movimentacoes = listar_movimentacoes_caixa(state.caixa_id)
    total_sangrias = sum(m["valor"] for m in movimentacoes if m["tipo"] == "sangria")
    total_suprimentos = sum(
        m["valor"] for m in movimentacoes if m["tipo"] == "suprimento"
    )

    total_em_caixa = (
        total_geral
        + caixa["fundo_troco"]
        - total_troco
        - total_sangrias
        + total_suprimentos
    )

    return {
        "caixa_id": state.caixa_id,
        "abertura_fmt": _fmt_data(caixa["data_hora_abr"]),
        "fundo_troco": caixa["fundo_troco"],
        "qtd_vendas": len(vendas),
        "totais_por_forma": totais,
        "total_geral": total_geral,
        "total_troco": total_troco,
        "total_sangrias": total_sangrias,
        "total_suprimentos": total_suprimentos,
        "total_em_caixa": total_em_caixa,
    }


def fechar_caixa() -> tuple[bool, str]:
    """Fecha o caixa atual. Retorna (sucesso, mensagem)."""
    if not state.caixa_id:
        return False, "Nenhum caixa aberto."

    caixa_id_fechado = state.caixa_id
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE abertura_caixa SET data_hora_fec=?, status='fechado' WHERE id=?",
            (_iso_now(), caixa_id_fechado),
        )
    state.caixa_id = None
    registrar_auditoria("fechar_caixa", "caixa", caixa_id_fechado, "")
    return True, "Caixa fechado."
