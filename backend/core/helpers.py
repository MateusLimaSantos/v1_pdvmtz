import re
import math
import requests
from datetime import datetime
from pydantic import ValidationError

from core.database import get_db_connection
from core.models import EmitenteModel, validar_cnpj

# ─────────────────────────────────────────
# HELPERS DE DATA / HORA
# ─────────────────────────────────────────


def _iso_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fmt_data(iso: str) -> str:
    """Converte ISO-8601 para DD/MM/YYYY HH:MM."""
    try:
        dt = datetime.strptime(iso[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso[:16]


def _iso_de_br(data_br: str) -> str:
    """DD/MM/YYYY → YYYY-MM-DD para queries SQL."""
    try:
        return datetime.strptime(data_br.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return data_br


# ─────────────────────────────────────────
# PARSE / VALIDAÇÃO DE NÚMEROS (sem input de terminal)
# ─────────────────────────────────────────


def parse_float(raw: str) -> float | None:
    """Converte texto de campo da GUI em float aceitando vírgula. None se inválido,
    incluindo infinito (ex: '1e10000') e NaN, que float() aceita silenciosamente
    mas corrompem cálculos financeiros (somas com inf nunca mais voltam a um número)."""
    if raw is None:
        return None
    raw = str(raw).strip().replace(",", ".")
    if not raw:
        return None
    try:
        valor = float(raw)
    except ValueError:
        return None
    if not math.isfinite(valor):
        return None
    return valor


# ─────────────────────────────────────────
# VALIDADORES DE NEGÓCIO REUTILIZÁVEIS
# ─────────────────────────────────────────


def validar_ean(ean: str) -> tuple[bool, str]:
    """
    EAN deve ter entre 8 e 14 dígitos numéricos, sem sequências repetidas.
    Aceita também códigos internos alfanuméricos com pelo menos 3 caracteres.
    """
    ean = ean.strip()
    if len(ean) < 3:
        return False, "EAN deve ter pelo menos 3 caracteres."
    if re.match(r"^\d+$", ean):
        if not (8 <= len(ean) <= 14):
            return False, "EAN numérico deve ter entre 8 e 14 dígitos."
        if ean == ean[0] * len(ean):
            return False, "EAN inválido (sequência repetida)."
    return True, ean


def validar_telefone_simples(tel: str) -> tuple[bool, str]:
    """Valida e limpa telefone: retorna (ok, digitos_limpos_ou_mensagem_erro)."""
    digitos = re.sub(r"\D", "", tel)
    if len(digitos) not in (10, 11):
        return False, "Telefone deve ter 10 ou 11 dígitos (com DDD)."
    if digitos == digitos[0] * len(digitos):
        return False, "Telefone inválido (sequência repetida)."
    return True, digitos


def validar_email(email: str) -> tuple[bool, str]:
    """Validação básica de e-mail."""
    if not email:
        return True, ""  # e-mail é opcional na maioria dos cadastros
    if re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return True, email.lower()
    return False, "E-mail inválido (ex: nome@dominio.com)."


def validar_cnpj_input(cnpj: str) -> tuple[bool, str]:
    """Valida e formata CNPJ. Retorna (ok, cnpj_formatado_ou_mensagem_erro)."""
    digitos = re.sub(r"\D", "", cnpj)
    if not validar_cnpj(digitos):
        return (
            False,
            "CNPJ inválido. Verifique os 14 dígitos e os dígitos verificadores.",
        )
    fmt = f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    return True, fmt


# ─────────────────────────────────────────
# CONFIGURAÇÕES (chave/valor no banco)
# ─────────────────────────────────────────


def get_config(chave: str, padrao=None):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT valor FROM configuracoes WHERE chave=?", (chave,)
        ).fetchone()
        return row["valor"] if row else padrao


def set_config(chave: str, valor):
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO configuracoes (chave, valor) VALUES (?,?)
            ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor
            """,
            (chave, str(valor)),
        )


# ─────────────────────────────────────────
# DADOS DO EMITENTE
# ─────────────────────────────────────────


def buscar_endereco_por_cep(cep: str) -> dict | None:
    """
    Consulta o CEP em ViaCEP (primária) com fallback em BrasilAPI,
    seguindo o padrão recomendado de não depender de uma única fonte.
    Retorna um dict normalizado com as chaves:
        logradouro, bairro, cidade, uf
    ou None se o CEP for inválido, não encontrado em nenhuma fonte,
    ou se não houver rede disponível — nunca lança exceção: o
    autocompletar é um auxílio opcional, preenchimento manual sempre
    continua possível.
    """
    cep_limpo = re.sub(r"\D", "", cep)
    if len(cep_limpo) != 8:
        return None

    resultado = _buscar_cep_viacep(cep_limpo)
    if resultado:
        return resultado
    return _buscar_cep_brasilapi(cep_limpo)


def _buscar_cep_viacep(cep_limpo: str) -> dict | None:
    try:
        r = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=5)
    except requests.exceptions.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        dados = r.json()
    except ValueError:
        return None
    if dados.get("erro"):
        return None
    if not dados.get("logradouro") and not dados.get("bairro"):
        return None
    return {
        "logradouro": dados.get("logradouro", ""),
        "bairro": dados.get("bairro", ""),
        "cidade": dados.get("localidade", ""),
        "uf": dados.get("uf", ""),
    }


def _buscar_cep_brasilapi(cep_limpo: str) -> dict | None:
    try:
        r = requests.get(f"https://brasilapi.com.br/api/cep/v2/{cep_limpo}", timeout=5)
    except requests.exceptions.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        dados = r.json()
    except ValueError:
        return None
    if not dados.get("street") and not dados.get("neighborhood"):
        return None
    return {
        "logradouro": dados.get("street", ""),
        "bairro": dados.get("neighborhood", ""),
        "cidade": dados.get("city", ""),
        "uf": dados.get("state", ""),
    }


def get_dados_emitente(validar: bool = True) -> dict:
    """
    Retorna os dados do emitente salvos. Se validar=True, tenta validar
    via EmitenteModel e retorna também a lista de erros encontrados
    (chave 'erros', lista vazia se tudo certo) — a GUI decide o que exibir.
    """
    dados_brutos = {
        "razao_social": get_config("emit_razao_social", ""),
        "cnpj": get_config("emit_cnpj", ""),
        "ie": get_config("emit_ie", ""),
        "logradouro": get_config("emit_logradouro", ""),
        "numero": get_config("emit_numero", ""),
        "bairro": get_config("emit_bairro", ""),
        "municipio": get_config("emit_municipio", ""),
        "uf": get_config("emit_uf", ""),
        "cep": get_config("emit_cep", ""),
        "telefone": get_config("emit_telefone", ""),
        "regime": get_config("emit_regime", ""),
        "crt": get_config("emit_crt", ""),
    }

    if not validar:
        return dados_brutos

    try:
        emitente_validado = EmitenteModel(**dados_brutos)
        resultado = emitente_validado.model_dump()
        resultado["erros"] = []
        return resultado
    except ValidationError as e:
        dados_brutos["erros"] = [
            {"campo": erro["loc"][0], "mensagem": erro["msg"]} for erro in e.errors()
        ]
        return dados_brutos
