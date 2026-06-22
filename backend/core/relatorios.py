from core.database import get_db_connection
from core.helpers import _iso_de_br


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
