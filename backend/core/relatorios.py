from backend.core.database import get_db_connection
from backend.core.helpers import _iso_de_br


def relatorio_vendas_periodo(data_ini_br: str, data_fim_br: str) -> dict:
    """
    Monta o relatório de vendas por período.
    Datas no formato DD/MM/YYYY.
    """
    ini_iso = _iso_de_br(data_ini_br) + " 00:00:00"
    fim_iso = _iso_de_br(data_fim_br) + " 23:59:59"

    with get_db_connection() as conn:
        vendas = conn.execute(
            "SELECT * FROM vendas WHERE data_hora BETWEEN ? AND ? "
            "AND status='concluida' ORDER BY id",
            (ini_iso, fim_iso),
        ).fetchall()

    totais: dict[str, float] = {}
    total_geral = descontos = 0.0
    for v in vendas:
        totais[v["forma_pagamento"]] = (
            totais.get(v["forma_pagamento"], 0.0) + v["total"]
        )
        total_geral += v["total"]
        descontos += v["desconto"]

    return {
        "data_ini": data_ini_br,
        "data_fim": data_fim_br,
        "qtd_vendas": len(vendas),
        "descontos": descontos,
        "totais_por_forma": totais,
        "total_geral": total_geral,
    }


def relatorio_vendas_mensal(meses: int = 12) -> list[dict]:
    """
    Agrega vendas concluídas por mês (AAAA-MM), nos últimos `meses` meses
    a partir do mês atual, incluindo meses sem nenhuma venda (com total=0).
    Retorna lista ordenada do mês mais antigo para o mais recente —
    ordem natural para um gráfico de linha/barras.
    """
    from datetime import datetime

    hoje = datetime.now()
    ano_base, mes_base = hoje.year, hoje.month

    meses_alvo = []
    for i in range(meses - 1, -1, -1):
        # Subtrai i meses de (ano_base, mes_base) usando aritmética inteira
        # em base-0, sem depender de bibliotecas externas de data.
        indice_total = (mes_base - 1) - i
        ano = ano_base + indice_total // 12
        mes_num = indice_total % 12 + 1
        meses_alvo.append(f"{ano:04d}-{mes_num:02d}")

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m', data_hora) AS mes,
                   SUM(total) AS total_vendido,
                   COUNT(*) AS qtd_vendas
            FROM vendas
            WHERE status='concluida'
            GROUP BY mes
            """
        ).fetchall()

    por_mes = {r["mes"]: {"total_vendido": r["total_vendido"], "qtd_vendas": r["qtd_vendas"]} for r in rows}

    nomes_meses_pt = [
        "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez",
    ]
    resultado = []
    for mes_str in meses_alvo:
        ano, mes_num = mes_str.split("-")
        dados = por_mes.get(mes_str, {"total_vendido": 0.0, "qtd_vendas": 0})
        resultado.append(
            {
                "mes": mes_str,
                "rotulo": f"{nomes_meses_pt[int(mes_num) - 1]}/{ano[2:]}",
                "total_vendido": dados["total_vendido"] or 0.0,
                "qtd_vendas": dados["qtd_vendas"] or 0,
            }
        )
    return resultado


def relatorio_curva_abc(limite: int = 20) -> list[dict]:
    """Monta a curva ABC dos produtos mais vendidos."""
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT iv.produto_ean, iv.nome_exibicao,
                   SUM(iv.qtd) AS total_qtd,
                   SUM(iv.preco_total) AS total_valor
            FROM itens_venda iv
            JOIN vendas v ON v.id=iv.venda_id
            WHERE v.status='concluida'
            GROUP BY iv.produto_ean
            ORDER BY total_valor DESC LIMIT ?
            """,
            (limite,),
        ).fetchall()

    total_geral = sum(r["total_valor"] for r in rows)
    acumulado = 0.0
    resultado = []
    for i, r in enumerate(rows, 1):
        pct = r["total_valor"] / total_geral * 100 if total_geral else 0
        acumulado += pct
        curva = "A" if acumulado <= 70 else "B" if acumulado <= 90 else "C"
        resultado.append(
            {
                "posicao": i,
                "nome_exibicao": r["nome_exibicao"],
                "total_qtd": r["total_qtd"],
                "total_valor": r["total_valor"],
                "pct": pct,
                "acumulado": acumulado,
                "curva": curva,
            }
        )
    return resultado
