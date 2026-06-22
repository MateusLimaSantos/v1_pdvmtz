import hashlib
import sqlite3
import re
from config import DB_PATH


def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def autenticar(nome: str, senha: str) -> dict | None:
    """Retorna dict do operador se credenciais válidas, None caso contrário."""
    h = _hash_senha(senha)
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM operadores WHERE nome=? AND senha=? AND ativo=1", (nome, h)
        ).fetchone()
        if row:
            return dict(row)

    # Compatibilidade: banco antigo com senha em texto puro
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM operadores WHERE nome=? AND senha=? AND ativo=1",
            (nome, senha),
        ).fetchone()
        if row:
            conn.execute("UPDATE operadores SET senha=? WHERE id=?", (h, row["id"]))
            return dict(row)
    return None


def existe_algum_operador() -> bool:
    """True se já existe pelo menos um operador cadastrado no banco."""
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM operadores").fetchone()
        return row[0] > 0


def validar_nome_admin(nome: str) -> tuple[bool, str]:
    """Valida nome do primeiro administrador (1 a 15 letras, sem espaços/acentos/números)."""
    if re.match(r"^[A-Za-z]{1,15}$", nome):
        return True, ""
    return (
        False,
        "Use APENAS LETRAS (sem espaços, acentos ou números) e no máximo 15 caracteres.",
    )


def validar_senha_admin(senha: str) -> tuple[bool, str]:
    """Valida senha do primeiro administrador (1 a 10 caracteres)."""
    if 1 <= len(senha) <= 10:
        return True, ""
    return False, "A senha deve ter entre 1 e 10 caracteres."


def criar_primeiro_admin(nome: str, senha: str) -> tuple[bool, str]:
    """
    Cria o primeiro administrador do sistema.
    Retorna (sucesso, mensagem_de_erro).
    """
    ok, erro = validar_nome_admin(nome)
    if not ok:
        return False, erro
    ok, erro = validar_senha_admin(senha)
    if not ok:
        return False, erro

    with _get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO operadores (nome, senha, perfil) VALUES (?,?,?)",
                (nome, _hash_senha(senha), "admin"),
            )
        except sqlite3.IntegrityError:
            return False, f"Usuário '{nome}' já existe."
    return True, ""
