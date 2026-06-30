def adicionar_item_ao_carrinho(
    itens_carrinho: list[dict], item_lido: dict
) -> tuple[bool, str]:
    """
    Adiciona (ou soma à quantidade de) um item unitário no carrinho.
    Não usar para itens por peso — aplique registrar_peso antes e faça o append manualmente.
    Retorna (sucesso, mensagem_de_erro_se_houver).
    """
    existente = next(
        (i for i in itens_carrinho if i["ean_bipado"] == item_lido["ean_bipado"]), None
    )
    if existente:
        nova_qtd = existente["qtd_desconto"] + item_lido["qtd_desconto"]
        if item_lido["estoque_disponivel"] < nova_qtd:
            return (
                False,
                f"Estoque insuficiente. Disponível: {item_lido['estoque_disponivel']:.2f}",
            )
        existente["qtd_desconto"] = nova_qtd
        existente["preco_total"] = round(
            existente["preco_unitario"] * nova_qtd - existente.get("desconto_item", 0),
            2,
        )
        return True, ""
    else:
        if item_lido["estoque_disponivel"] < item_lido["qtd_desconto"]:
            return False, "Estoque insuficiente."
        itens_carrinho.append(item_lido)
        return True, ""


def remover_item_indice(itens_carrinho: list[dict], indice: int) -> tuple[bool, str]:
    """Remove um item do carrinho pelo índice (0-based). Retorna (sucesso, nome_removido_ou_erro)."""
    if not (0 <= indice < len(itens_carrinho)):
        return False, "Número inválido."
    nome = itens_carrinho.pop(indice)["nome_exibicao"]
    return True, nome


def alterar_quantidade_indice(
    itens_carrinho: list[dict], indice: int, nova_qtd: float
) -> tuple[bool, str]:
    """Altera a quantidade de um item do carrinho pelo índice. Retorna (sucesso, mensagem)."""
    if not (0 <= indice < len(itens_carrinho)):
        return False, "Número inválido."
    if nova_qtd <= 0:
        return False, "Deve ser maior que zero."

    item = itens_carrinho[indice]
    info = buscar_produto_por_ean(item["ean_bipado"])
    estoque_disp = info["estoque_disponivel"] if info else 0
    if estoque_disp < nova_qtd:
        return False, f"Estoque insuficiente. Disponível: {estoque_disp:.3f}"

    item["qtd_desconto"] = nova_qtd
    item["preco_total"] = round(
        item["preco_referencia"] * nova_qtd - item.get("desconto_item", 0), 2
    )
    return True, f"Qtd atualizada: {item['nome_exibicao']} → {nova_qtd}"


def total_bruto_carrinho(itens_carrinho: list[dict]) -> float:
    return sum(i["preco_total"] for i in itens_carrinho)