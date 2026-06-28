import sqlite3
from config import TIPOS_UNIDADE_VALIDOS, TIPOS_PESO, UNIDADE_LABEL
from core.database import get_db_connection
from core.helpers import _iso_now, _fmt_data
from core.state import state
from core.auditoria import registrar_auditoria

# ─────────────────────────────────────────
# PRODUTOS
# ─────────────────────────────────────────


def ean_existe(ean: str) -> bool:
    with get_db_connection() as conn:
        return bool(
            conn.execute("SELECT 1 FROM produtos WHERE ean=?", (ean,)).fetchone()
        )


def adicionar_produto(
    ean: str,
    nome: str,
    descricao: str,
    tipo_unidade: str,
    estoque_inicial: float,
    estoque_minimo: float,
    preco: float,
    embalagens: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Cadastra um novo produto e suas embalagens (opcionais).
    embalagens: lista de dicts {ean, tipo, fator, preco_venda(opcional)}
    Retorna (sucesso, mensagem).
    """
    embalagens = embalagens or []

    if ean_existe(ean):
        return False, f"EAN '{ean}' já cadastrado."
    if tipo_unidade not in TIPOS_UNIDADE_VALIDOS:
        return False, "Tipo de unidade inválido."
    if estoque_inicial < 0:
        return False, "Estoque inicial não pode ser negativo."
    if estoque_minimo < 0:
        return False, "Estoque mínimo não pode ser negativo."
    if preco <= 0:
        return False, "Preço deve ser maior que zero."

    preco_ref = preco if tipo_unidade in TIPOS_PESO else None

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO produtos "
                "(ean, nome, descricao, preco_venda, estoque_atual, "
                "estoque_minimo, tipo_unidade, preco_referencia) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    ean,
                    nome.upper(),
                    descricao,
                    preco,
                    estoque_inicial,
                    estoque_minimo,
                    tipo_unidade,
                    preco_ref,
                ),
            )
            for emb in embalagens:
                conn.execute(
                    "INSERT INTO embalagens "
                    "(ean_embalagem, produto_base_ean, tipo, fator_conversao, preco_venda) "
                    "VALUES (?,?,?,?,?)",
                    (
                        emb["ean"],
                        ean,
                        emb["tipo"].upper(),
                        emb["fator"],
                        emb.get("preco_venda"),
                    ),
                )
            if estoque_inicial > 0:
                conn.execute(
                    "INSERT INTO movimentacoes_estoque "
                    "(produto_ean, data_hora, tipo, qtd, motivo, operador_id) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        ean,
                        _iso_now(),
                        "entrada",
                        estoque_inicial,
                        "Estoque inicial",
                        state.operador["id"] if state.operador else None,
                    ),
                )
        registrar_auditoria(
            "cadastrar", "produto", ean,
            f"Nome='{nome.upper()}', preço=R$ {preco:.2f}, estoque inicial={estoque_inicial}",
        )
        return True, f"'{nome.upper()}' cadastrado como [{tipo_unidade}]."
    except sqlite3.IntegrityError as e:
        registrar_auditoria("cadastrar", "produto", ean, f"Falha: {e}", sucesso=False)
        return False, f"Erro: {e}"


def buscar_produto_para_edicao(ean: str) -> dict | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM produtos WHERE ean=?", (ean,)).fetchone()
        return dict(row) if row else None


def editar_produto(
    ean: str,
    nome: str,
    preco: float,
    estoque_minimo: float,
    descricao: str,
    preco_referencia: float | None,
) -> tuple[bool, str]:
    """Atualiza um produto existente. Retorna (sucesso, mensagem)."""
    if preco <= 0:
        return False, "Preço deve ser maior que zero."
    if estoque_minimo < 0:
        return False, "Estoque mínimo não pode ser negativo."

    with get_db_connection() as conn:
        row = conn.execute("SELECT 1 FROM produtos WHERE ean=?", (ean,)).fetchone()
        if not row:
            registrar_auditoria("editar", "produto", ean, "Falha: não encontrado", sucesso=False)
            return False, "Produto não encontrado."
        conn.execute(
            "UPDATE produtos SET nome=?, preco_venda=?, descricao=?, "
            "estoque_minimo=?, preco_referencia=? WHERE ean=?",
            (nome.upper(), preco, descricao, estoque_minimo, preco_referencia, ean),
        )
    registrar_auditoria(
        "editar", "produto", ean, f"Nome='{nome.upper()}', preço=R$ {preco:.2f}"
    )
    return True, "Produto atualizado."


def buscar_produtos(termo: str = "") -> list[dict]:
    """Busca produtos por nome ou EAN (termo vazio retorna todos)."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM produtos WHERE ean LIKE ? OR nome LIKE ? ORDER BY nome",
            (f"%{termo}%", f"%{termo}%"),
        ).fetchall()
    return [dict(r) for r in rows]


def ajustar_estoque(ean: str, qtd: float, motivo: str) -> tuple[bool, str]:
    """
    Ajusta manualmente o estoque de um produto (qtd positiva=entrada, negativa=saída).
    Retorna (sucesso, mensagem).
    """
    if qtd == 0:
        return False, "Quantidade não pode ser zero."
    if len(motivo.strip()) < 3:
        return False, "Motivo deve ter ao menos 3 caracteres."

    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM produtos WHERE ean=?", (ean,)).fetchone()
        if not row:
            registrar_auditoria("ajustar_estoque", "produto", ean, "Falha: não encontrado", sucesso=False)
            return False, "Produto não encontrado."
        prod = dict(row)

    nova = round(prod["estoque_atual"] + qtd, 4)
    if nova < 0:
        registrar_auditoria(
            "ajustar_estoque", "produto", ean,
            f"Falha: resultaria em estoque negativo ({nova:.4f})", sucesso=False,
        )
        return (
            False,
            f"Resultaria em estoque negativo ({nova:.4f}). Operação cancelada.",
        )

    with get_db_connection() as conn:
        conn.execute("UPDATE produtos SET estoque_atual=? WHERE ean=?", (nova, ean))
        conn.execute(
            "INSERT INTO movimentacoes_estoque "
            "(produto_ean, data_hora, tipo, qtd, motivo, operador_id) VALUES (?,?,?,?,?,?)",
            (
                ean,
                _iso_now(),
                "ajuste",
                qtd,
                motivo,
                state.operador["id"] if state.operador else None,
            ),
        )
    un = UNIDADE_LABEL.get(prod["tipo_unidade"], "un")
    registrar_auditoria(
        "ajustar_estoque", "produto", ean,
        f"{prod['estoque_atual']:.3f} → {nova:.3f} {un} | Motivo: {motivo}",
    )
    return True, f"{prod['estoque_atual']:.3f} → {nova:.3f} {un} | Motivo: {motivo}"


def listar_estoque_minimo() -> list[dict]:
    """Lista produtos com estoque atual <= estoque mínimo."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM produtos WHERE estoque_atual <= estoque_minimo ORDER BY nome"
        ).fetchall()
    return [dict(r) for r in rows]


def listar_movimentacoes(ean: str = "", limite: int = 30) -> list[dict]:
    """Lista movimentações de estoque (ean vazio = todas)."""
    with get_db_connection() as conn:
        if ean:
            rows = conn.execute(
                "SELECT m.*, p.nome FROM movimentacoes_estoque m "
                "JOIN produtos p ON p.ean=m.produto_ean "
                "WHERE m.produto_ean=? ORDER BY m.id DESC LIMIT ?",
                (ean, limite),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT m.*, p.nome FROM movimentacoes_estoque m "
                "JOIN produtos p ON p.ean=m.produto_ean "
                "ORDER BY m.id DESC LIMIT ?",
                (limite,),
            ).fetchall()
    resultado = []
    for r in rows:
        d = dict(r)
        d["data_hora_fmt"] = _fmt_data(d["data_hora"])
        resultado.append(d)
    return resultado
