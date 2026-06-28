import sqlite3
from core.database import get_db_connection
from core.auth import _hash_senha
from core.state import state
from core.auditoria import registrar_auditoria


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
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO operadores (nome,senha,perfil) VALUES (?,?,?)",
                (nome, _hash_senha(senha), perfil),
            )
            novo_id = cur.lastrowid
        registrar_auditoria(
            "cadastrar", "operador", novo_id, f"Nome='{nome}', perfil='{perfil}'"
        )
        return True, f"'{nome}' ({perfil}) cadastrado."
    except sqlite3.IntegrityError:
        registrar_auditoria(
            "cadastrar", "operador", "", f"Falha: nome='{nome}' já existe", sucesso=False
        )
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
        registrar_auditoria("redefinir_senha", "operador", operador_id, "Senha redefinida")
        return True, "Senha atualizada."
    registrar_auditoria(
        "redefinir_senha", "operador", operador_id, "Falha: não encontrado ou inativo", sucesso=False
    )
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
        registrar_auditoria("desativar", "operador", operador_id, "")
        return True, "Operador desativado."
    registrar_auditoria("desativar", "operador", operador_id, "Falha: não encontrado", sucesso=False)
    return False, f"Operador #{operador_id} não encontrado."


def reativar_operador(operador_id: int) -> tuple[bool, str]:
    with get_db_connection() as conn:
        updated = conn.execute(
            "UPDATE operadores SET ativo=1 WHERE id=?", (operador_id,)
        ).rowcount
    if updated:
        registrar_auditoria("reativar", "operador", operador_id, "")
        return True, "Operador reativado."
    registrar_auditoria("reativar", "operador", operador_id, "Falha: não encontrado", sucesso=False)
    return False, f"Operador #{operador_id} não encontrado."
