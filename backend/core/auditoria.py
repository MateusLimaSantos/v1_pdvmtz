"""
Auditoria: registra quem fez o que no sistema (cadastros, edições,
exclusões, cancelamentos, movimentações de caixa, alterações de
configuração). Cada chamada de escrita relevante no backend chama
registrar_auditoria() após a operação, com sucesso ou falha.
"""
from backend.core.database import get_db_connection
from backend.core.helpers import _iso_now, _fmt_data
from backend.core.state import state


def registrar_auditoria(
    acao: str,
    entidade: str,
    entidade_id: str = "",
    detalhes: str = "",
    sucesso: bool = True,
) -> None:
    """
    Grava um evento de auditoria. Nunca lança exceção para o chamador:
    uma falha ao registrar auditoria não deve impedir a operação de
    negócio que já ocorreu (ou foi corretamente rejeitada).

    acao: verbo da ação, ex: 'cadastrar', 'editar', 'excluir', 'cancelar',
          'desativar', 'reativar', 'sangria', 'suprimento', 'abrir_caixa',
          'fechar_caixa', 'redefinir_senha', 'alterar_configuracao'.
    entidade: nome da tabela/domínio afetado, ex: 'operador', 'fornecedor',
              'produto', 'venda', 'caixa', 'configuracao'.
    entidade_id: identificador do registro afetado (id, ean, chave...), se houver.
    detalhes: texto curto e legível do que mudou (sem dados sensíveis como senha).
    """
    try:
        operador_id = state.operador["id"] if state.operador else None
        operador_nome = state.operador["nome"] if state.operador else "Sistema"
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO auditoria "
                "(data_hora, operador_id, operador_nome, acao, entidade, entidade_id, detalhes, sucesso) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    _iso_now(),
                    operador_id,
                    operador_nome,
                    acao,
                    entidade,
                    str(entidade_id),
                    detalhes,
                    1 if sucesso else 0,
                ),
            )
    except Exception:
        # Auditoria é best-effort: nunca deve quebrar o fluxo principal.
        pass


def listar_auditoria(
    limite: int = 200,
    entidade: str | None = None,
    acao: str | None = None,
    operador_nome: str | None = None,
    data_ini_br: str | None = None,
    data_fim_br: str | None = None,
) -> list[dict]:
    """Lista eventos de auditoria, mais recentes primeiro, com filtros opcionais."""
    query = "SELECT * FROM auditoria WHERE 1=1"
    params: list = []

    if entidade:
        query += " AND entidade = ?"
        params.append(entidade)
    if acao:
        query += " AND acao = ?"
        params.append(acao)
    if operador_nome:
        query += " AND operador_nome LIKE ?"
        params.append(f"%{operador_nome}%")
    if data_ini_br:
        partes = data_ini_br.split("/")
        if len(partes) == 3:
            iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
            query += " AND date(data_hora) >= date(?)"
            params.append(iso)
    if data_fim_br:
        partes = data_fim_br.split("/")
        if len(partes) == 3:
            iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
            query += " AND date(data_hora) <= date(?)"
            params.append(iso)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limite)

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    resultado = []
    for r in rows:
        d = dict(r)
        d["data_hora_fmt"] = _fmt_data(d["data_hora"])
        resultado.append(d)
    return resultado


def listar_entidades_distintas() -> list[str]:
    """Lista os valores distintos de 'entidade' já registrados, para alimentar filtro na tela."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT entidade FROM auditoria ORDER BY entidade"
        ).fetchall()
    return [r["entidade"] for r in rows]


def listar_acoes_distintas() -> list[str]:
    """Lista os valores distintos de 'acao' já registrados, para alimentar filtro na tela."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT acao FROM auditoria ORDER BY acao"
        ).fetchall()
    return [r["acao"] for r in rows]
