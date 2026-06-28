import re
import sqlite3
from backend.core.database import get_db_connection
from backend.core.helpers import validar_cnpj_input, validar_telefone_simples, validar_email
from backend.core.auditoria import registrar_auditoria


def cadastrar_fornecedor(
    cnpj_raw: str, nome: str, email: str, telefone_raw: str
) -> tuple[bool, str]:
    """Valida e cadastra um fornecedor. Retorna (sucesso, mensagem)."""
    ok, resultado = validar_cnpj_input(cnpj_raw)
    if not ok:
        return False, resultado
    cnpj_fmt = resultado
    cnpj = re.sub(r"\D", "", cnpj_fmt)

    nome = nome.strip()
    if len(nome) < 3:
        return False, "Nome / Razão Social deve ter ao menos 3 caracteres."
    nome = nome.upper()

    ok, msg = validar_email(email)
    if not ok:
        return False, msg
    email_validado = msg

    ok, msg = validar_telefone_simples(telefone_raw)
    if not ok:
        return False, msg
    telefone = msg

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO fornecedores (cnpj,nome,email,telefone) VALUES (?,?,?,?)",
                (cnpj, nome, email_validado, telefone),
            )
            novo_id = cur.lastrowid
        registrar_auditoria("cadastrar", "fornecedor", novo_id, f"Nome='{nome}', CNPJ='{cnpj_fmt}'")
        return True, f"'{nome}' cadastrado com sucesso."
    except sqlite3.IntegrityError:
        registrar_auditoria(
            "cadastrar", "fornecedor", "", f"Falha: CNPJ='{cnpj_fmt}' já cadastrado", sucesso=False
        )
        return False, "CNPJ já cadastrado."


def listar_fornecedores() -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM fornecedores ORDER BY nome").fetchall()
    return [dict(r) for r in rows]


def atualizar_fornecedor(
    fornecedor_id: int, nome: str, email: str, telefone_raw: str
) -> tuple[bool, str]:
    """Atualiza nome/email/telefone de um fornecedor existente. CNPJ nao e alterado."""
    nome = nome.strip()
    if len(nome) < 3:
        return False, "Nome / Razão Social deve ter ao menos 3 caracteres."
    nome = nome.upper()

    ok, msg = validar_email(email)
    if not ok:
        return False, msg
    email_validado = msg

    ok, msg = validar_telefone_simples(telefone_raw)
    if not ok:
        return False, msg
    telefone = msg

    with get_db_connection() as conn:
        updated = conn.execute(
            "UPDATE fornecedores SET nome=?, email=?, telefone=? WHERE id=?",
            (nome, email_validado, telefone, fornecedor_id),
        ).rowcount
    if updated:
        registrar_auditoria(
            "editar", "fornecedor", fornecedor_id,
            f"Nome='{nome}', email='{email_validado}', telefone='{telefone}'",
        )
        return True, f"'{nome}' atualizado."
    registrar_auditoria("editar", "fornecedor", fornecedor_id, "Falha: não encontrado", sucesso=False)
    return False, f"Fornecedor #{fornecedor_id} não encontrado."


def excluir_fornecedor(fornecedor_id: int) -> tuple[bool, str]:
    with get_db_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM fornecedores WHERE id=?", (fornecedor_id,)
        ).rowcount
    if deleted:
        registrar_auditoria("excluir", "fornecedor", fornecedor_id, "")
        return True, "Fornecedor excluído."
    registrar_auditoria("excluir", "fornecedor", fornecedor_id, "Falha: não encontrado", sucesso=False)
    return False, f"Fornecedor #{fornecedor_id} não encontrado."
