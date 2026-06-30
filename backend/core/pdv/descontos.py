def limite_desconto_operador() -> float:
    """Limite de desconto percentual: sem limite para admin, DESCONTO_MAX_OPERADOR para operador."""
    is_admin = state.operador and state.operador["perfil"] == "admin"
    return 100.0 if is_admin else DESCONTO_MAX_OPERADOR


def calcular_desconto_valor(
    total_bruto: float, valor_desconto: float
) -> tuple[bool, float, str]:
    """Valida e calcula desconto informado em R$. Retorna (ok, valor_aplicado, erro)."""
    lim = limite_desconto_operador()
    pct_equiv = valor_desconto / total_bruto * 100 if total_bruto else 0
    if pct_equiv > lim:
        return (
            False,
            0.0,
            f"Desconto excede o limite ({lim:.0f}%). Requer autorização de admin.",
        )
    if valor_desconto > total_bruto:
        return False, 0.0, "Desconto maior que o total."
    return True, round(valor_desconto, 2), ""


def calcular_desconto_percentual(
    total_bruto: float, pct: float
) -> tuple[bool, float, str]:
    """Valida e calcula desconto informado em %. Retorna (ok, valor_aplicado, erro)."""
    lim = limite_desconto_operador()
    if pct > lim:
        return False, 0.0, f"Excede o limite ({lim:.0f}%). Requer autorização de admin."
    return True, round(total_bruto * pct / 100, 2), ""
