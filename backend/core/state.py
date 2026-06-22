class AppState:
    operador: dict | None = None
    caixa_id: int | None = None
    _finalizando: bool = False


state = AppState()