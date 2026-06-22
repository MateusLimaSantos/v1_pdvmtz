import re
import sqlite3
from core.database import get_db_connection
from core.helpers import validar_cnpj_input, validar_telefone_simples, validar_email


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
            conn.execute(
                "INSERT INTO fornecedores (cnpj,nome,email,telefone) VALUES (?,?,?,?)",
                (cnpj, nome, email_validado, telefone),
            )
        return True, f"'{nome}' cadastrado com sucesso."
    except sqlite3.IntegrityError:
        return False, "CNPJ já cadastrado."


def listar_fornecedores() -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM fornecedores ORDER BY nome").fetchall()
    return [dict(r) for r in rows]
