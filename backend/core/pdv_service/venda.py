import sqlite3

from core.database import get_db_connection
from core.fiscal.cupom import formatar_cupom
from core.state import state

from .carrinho import total_bruto_carrinho
from .estoque_pdv import produtos_estoque_baixo


def finalizar_venda(
    itens_carrinho: list[dict],
    desconto_venda: float,
    forma_pagamento: str,
    troco: float,
) -> tuple[bool, str, dict | None]:
    """
    Persiste a venda no banco: atualiza estoque, grava venda e itens.
    Retorna (sucesso, mensagem, dados_da_venda).
    """
    if not itens_carrinho:
        return False, "Carrinho vazio.", None

    if state._finalizando:
        return False, "Venda ja esta sendo processada.", None
    state._finalizando = True

    total_bruto = total_bruto_carrinho(itens_carrinho)
    total_final = max(0.0, round(total_bruto - desconto_venda, 2))

    itens_cupom = [
        {
            "nome": i["nome_exibicao"],
            "qtd": i["qtd_desconto"],
            "tipo_unidade": i.get("tipo_unidade", "unidade"),
            "preco_total": i["preco_total"],
            "desconto_item": i.get("desconto_item", 0),
        }
        for i in itens_carrinho
    ]

    cupom_texto, data_iso = formatar_cupom(
        itens_cupom, total_final, desconto_venda, forma_pagamento, troco
    )

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            for item in itens_carrinho:
                cur.execute(
                    "UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE ean=?",
                    (item["qtd_desconto"], item["ean_base"]),
                )
                cur.execute(
                    "INSERT INTO movimentacoes_estoque "
                    "(produto_ean, data_hora, tipo, qtd, motivo, operador_id) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        item["ean_base"],
                        data_iso,
                        "venda",
                        -item["qtd_desconto"],
                        "Venda PDV",
                        state.operador["id"],
                    ),
                )

            cur.execute(
                "INSERT INTO vendas "
                "(caixa_id, operador_id, data_hora, total, desconto, "
                "forma_pagamento, troco, cupom_texto) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    state.caixa_id,
                    state.operador["id"],
                    data_iso,
                    total_final,
                    desconto_venda,
                    forma_pagamento,
                    troco,
                    cupom_texto,
                ),
            )
            venda_id = cur.lastrowid

            for item in itens_carrinho:
                cur.execute(
                    "INSERT INTO itens_venda "
                    "(venda_id, produto_ean, nome_exibicao, tipo_unidade, "
                    "preco_unitario, qtd, desconto_item, preco_total) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        venda_id,
                        item["ean_base"],
                        item["nome_exibicao"],
                        item.get("tipo_unidade", "unidade"),
                        item["preco_unitario"],
                        item["qtd_desconto"],
                        item.get("desconto_item", 0),
                        item["preco_total"],
                    ),
                )

        alertas = produtos_estoque_baixo(itens_carrinho)
        return (
            True,
            f"Venda #{venda_id} registrada com sucesso!",
            {
                "venda_id": venda_id,
                "cupom_texto": cupom_texto,
                "alertas_estoque": alertas,
                "total_final": total_final,
            },
        )

    except sqlite3.IntegrityError as e:
        return False, f"ERRO DE INTEGRIDADE: {e} - transacao desfeita.", None
    except sqlite3.OperationalError as e:
        return False, f"ERRO OPERACIONAL: {e} - transacao desfeita.", None
    finally:
        state._finalizando = False
