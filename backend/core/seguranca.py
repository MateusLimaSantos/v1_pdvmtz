"""
Cifra/decifra credenciais sensíveis (ex: access_token de gateway de
pagamento) antes de guardar no banco. A tabela `configuracoes` é
texto plano por natureza — qualquer um com acesso ao arquivo .db lê
tudo. Para segredos reais (tokens de API), ciframos com Fernet antes
de gravar, e a chave de cifragem fica em um arquivo separado do
banco, fora do .db, para que copiar só o banco não exponha o token.
"""

import os
from cryptography.fernet import Fernet, InvalidToken
from config import DATA_DIR

_CHAVE_PATH = os.path.join(DATA_DIR, ".chave_local")


def _obter_ou_criar_chave() -> bytes:
    if os.path.exists(_CHAVE_PATH):
        with open(_CHAVE_PATH, "rb") as f:
            return f.read()
    chave = Fernet.generate_key()
    with open(_CHAVE_PATH, "wb") as f:
        f.write(chave)
    try:
        os.chmod(_CHAVE_PATH, 0o600)
    except OSError:
        pass  # Windows não suporta chmod POSIX; segue sem essa proteção extra
    return chave


def cifrar(texto_claro: str) -> str:
    """Cifra uma string. Retorna string vazia se a entrada for vazia (não cifra nada à toa)."""
    if not texto_claro:
        return ""
    f = Fernet(_obter_ou_criar_chave())
    return f.encrypt(texto_claro.encode("utf-8")).decode("utf-8")


def decifrar(texto_cifrado: str) -> str:
    """Decifra uma string. Retorna string vazia se vazia, None, ou se a cifra for inválida/corrompida."""
    if not texto_cifrado:
        return ""
    f = Fernet(_obter_ou_criar_chave())
    try:
        return f.decrypt(texto_cifrado.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mascarar_token(texto_claro: str, visiveis: int = 4) -> str:
    """Para exibição na UI/logs: mostra só os últimos N caracteres do token."""
    if not texto_claro:
        return ""
    if len(texto_claro) <= visiveis:
        return "*" * len(texto_claro)
    return "*" * (len(texto_claro) - visiveis) + texto_claro[-visiveis:]
