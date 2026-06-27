import sqlite3
from core.database import get_db_connection
from core.auth import _hash_senha
from core.state import state


def cadastrar_operador(nome: str, senha: str, perfil: str) -> tuple[bool, str]:
    """Cadastra um novo operador. perfil deve ser 'admin' ou 'operador'. Retorna (sucesso, mensagem)."""
    nome = nome.strip()
    if len(nome) < 2:
        return False, "Nome deve ter ao menos 2 caracteres."
    if len(senha) < 4:
        return False, "Senha deve ter ao menos 4 caracteres."
    if perfil not in ("admin", "operador"):
        return False, "Perfil inválido."

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO operadores (nome,senha,perfil) VALUES (?,?,?)",
                (nome, _hash_senha(senha), perfil),
            )
        return True, f"'{nome}' ({perfil}) cadastrado."
    except sqlite3.IntegrityError:
        return False, "Nome já existe."


def listar_operadores() -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT id,nome,perfil,ativo FROM operadores").fetchall()
    return [dict(r) for r in rows]


def redefinir_senha(operador_id: int, nova_senha: str) -> tuple[bool, str]:
    if len(nova_senha) < 4:
        return False, "Senha deve ter ao menos 4 caracteres."
    with get_db_connection() as conn:
        updated = conn.execute(
            "UPDATE operadores SET senha=? WHERE id=? AND ativo=1",
            (_hash_senha(nova_senha), operador_id),
        ).rowcount
    if updated:
        return True, "Senha atualizada."
    return False, f"Operador #{operador_id} não encontrado ou inativo."


def desativar_operador(operador_id: int) -> tuple[bool, str]:
    meu_id = state.operador["id"] if state.operador else -1
    if operador_id == meu_id:
        return False, "Não é possível desativar o próprio operador logado."
    with get_db_connection() as conn:
        updated = conn.execute(
            "UPDATE operadores SET ativo=0 WHERE id=?", (operador_id,)
        ).rowcount
    if updated:
        return True, "Operador desativado."
    return False, f"Operador #{operador_id} não encontrado."
