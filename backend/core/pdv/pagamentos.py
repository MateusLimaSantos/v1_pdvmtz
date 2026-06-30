def formas_pagamento_disponiveis() -> list[str]:
    formas = ["Dinheiro"]
    if get_config("pix_ativo") == "True":
        formas.append("PIX")
    if get_config("cartao_ativo") == "True":
        formas.append("Cartao")
    return formas


def calcular_troco(total: float, valor_recebido: float) -> tuple[bool, float, str]:
    """Calcula troco para pagamento em dinheiro. Retorna (ok, troco, erro)."""
    if valor_recebido < total:
        return False, 0.0, f"Faltam R$ {total - valor_recebido:.2f}."
    return True, round(valor_recebido - total, 2), ""


def gerar_qrcode_pix_para_venda(total: float) -> tuple[bool, str]:
    """Gera o PDF do QR Code PIX. Retorna (sucesso, caminho_ou_erro)."""
    return gerar_pdf_pix(total)
