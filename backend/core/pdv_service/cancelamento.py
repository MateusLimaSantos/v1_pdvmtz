from core.auditoria import registrar_auditoria
from core.database import get_db_connection
from core.helpers import _iso_now
from core.state import state


def buscar_venda(venda_id: int) -> tuple[dict | None, list[dict]]:
    """Retorna (venda, itens) ou (None, []) se nao encontrada."""
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
    Apenas administradores podem cancelar.
    """
    if not (state.operador and state.operador["perfil"] == "admin"):
        registrar_auditoria(
            "cancelar",
            "venda",
            venda_id,
            "Falha: acesso restrito a administradores",
            sucesso=False,
        )
        return False, "Acesso restrito a administradores."

    venda, itens = buscar_venda(venda_id)
    if not venda:
        registrar_auditoria(
            "cancelar", "venda", venda_id, "Falha: nao encontrada", sucesso=False
        )
        return False, "Venda nao encontrada."
    if venda["status"] == "cancelada":
        registrar_auditoria(
            "cancelar", "venda", venda_id, "Falha: ja estava cancelada", sucesso=False
        )
        return False, "Ja cancelada."
    if not motivo.strip():
        registrar_auditoria(
            "cancelar", "venda", venda_id, "Falha: motivo nao informado", sucesso=False
        )
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
                    "(produto_ean, data_hora, tipo, qtd, motivo, operador_id) "
                    "VALUES (?,?,?,?,?,?)",
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
        registrar_auditoria(
            "cancelar",
            "venda",
            venda_id,
            f"Motivo: {motivo.strip()} | Total: R$ {venda['total']:.2f}",
        )
        return True, f"Venda #{venda_id} cancelada e estoque restaurado."
    except Exception as e:
        registrar_auditoria("cancelar", "venda", venda_id, f"Falha: {e}", sucesso=False)
        return False, f"Erro: {e}"
