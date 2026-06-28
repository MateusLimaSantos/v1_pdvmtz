import re
from pydantic import ValidationError

from core.helpers import (
    get_config,
    set_config,
    get_dados_emitente,
    buscar_endereco_por_cep,
)
from core.models import EmitenteModel
from core.auditoria import registrar_auditoria

# ─────────────────────────────────────────
# PIX
# ─────────────────────────────────────────


def pix_esta_ativo() -> bool:
    return get_config("pix_ativo") == "True"


def dados_pix_atuais() -> dict:
    return {
        "chave": get_config("pix_chave", ""),
        "banco": get_config("pix_banco", ""),
        "nome": get_config("pix_nome", ""),
    }


def validar_chave_pix(tipo: str, chave: str) -> tuple[bool, str]:
    """
    tipo: '1'=CPF, '2'=Telefone, '3'=CNPJ, '4'=E-mail, '5'=Chave aleatória (UUID).
    Retorna (ok, mensagem).
    """
    limpo = re.sub(r"\D", "", chave)
    if tipo == "1":
        return (
            (True, "CPF válido.")
            if (len(limpo) == 11 and not re.search(r"[a-zA-Z]", chave))
            else (False, "CPF deve ter 11 dígitos.")
        )
    if tipo == "2":
        return (
            (True, "Telefone válido.")
            if (len(limpo) == 13 and re.match(r"^55[1-9]{2}9\d{8}$", limpo))
            else (False, "Formato: 55 + DDD + 9 + 8 dígitos.")
        )
    if tipo == "3":
        return (
            (True, "CNPJ válido.")
            if len(limpo) == 14
            else (False, "CNPJ deve ter 14 dígitos.")
        )
    if tipo == "4":
        return (
            (True, "E-mail válido.")
            if re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", chave)
            else (False, "E-mail inválido.")
        )
    if tipo == "5":
        return (
            (True, "Chave aleatória válida.")
            if re.match(
                r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
                r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
                chave,
            )
            else (
                False,
                "UUID inválido (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).",
            )
        )
    return False, "Tipo desconhecido."


def salvar_configuracao_pix(
    tipo: str, chave: str, banco: str, nome_titular: str
) -> tuple[bool, str]:
    ok, msg = validar_chave_pix(tipo, chave)
    if not ok:
        registrar_auditoria(
            "alterar_configuracao", "pix", "", f"Falha: {msg}", sucesso=False
        )
        return False, msg
    if len(banco.strip()) < 2:
        return False, "Banco / Instituição deve ter ao menos 2 caracteres."
    if not (2 <= len(nome_titular.strip()) <= 25):
        return False, "Nome do titular deve ter entre 2 e 25 caracteres."

    set_config("pix_chave", chave)
    set_config("pix_banco", banco)
    set_config("pix_nome", nome_titular)
    set_config("pix_ativo", "True")
    registrar_auditoria(
        "alterar_configuracao",
        "pix",
        "",
        f"PIX ativado. Banco='{banco.strip()}', titular='{nome_titular.strip()}'",
    )
    return True, "PIX configurado."


def desativar_pix():
    set_config("pix_ativo", "False")
    registrar_auditoria("alterar_configuracao", "pix", "", "PIX desativado")


# ─────────────────────────────────────────
# CARTÃO
# ─────────────────────────────────────────


def cartao_esta_ativo() -> bool:
    return get_config("cartao_ativo") == "True"


def alternar_cartao() -> bool:
    """Inverte o estado de ativação do cartão. Retorna o novo estado (True=ativo)."""
    atual = cartao_esta_ativo()
    novo = not atual
    set_config("cartao_ativo", "True" if novo else "False")
    return novo


# ─────────────────────────────────────────
# DADOS DO EMITENTE
# ─────────────────────────────────────────

_BASE_VALIDA = {
    "razao_social": "EMPRESA BASE LTDA",
    "cnpj": "11.222.333/0001-81",
    "ie": "ISENTO",
    "cep": "01310-100",
    "logradouro": "Avenida Paulista",
    "numero": "1000",
    "bairro": "Bela Vista",
    "municipio": "Sao Paulo",
    "uf": "SP",
    "telefone": "11987654321",
    "regime": "1",
    "crt": "1",
}


def _msg_amigavel(campo: str, msg_pydantic: str) -> str:
    m = msg_pydantic
    traduzidos = {
        "numero": "Use apenas dígitos (ex: 123, 42A) ou S/N para sem número.",
        "regime": "Digite 1, 2 ou 3.",
    }
    if campo in traduzidos and ("pattern" in m or "Value error" in m):
        return traduzidos[campo]
    if "Value error," in m:
        return m.split("Value error,")[-1].strip()
    m = m.replace("String should have at least", "Deve ter pelo menos")
    m = m.replace("String should have at most", "Deve ter no máximo")
    m = m.replace("characters", "caracteres")
    m = m.replace("String should match pattern", "Formato inválido")
    return m


def validar_campo_emitente(campo: str, valor: str) -> tuple[bool, str, str]:
    """Valida um campo isolado do emitente usando o EmitenteModel. Retorna (ok, valor_limpo, erro)."""
    dados_teste = _BASE_VALIDA.copy()
    dados_teste[campo] = valor
    try:
        modelo = EmitenteModel(**dados_teste)
        return True, getattr(modelo, campo), ""
    except ValidationError as e:
        erro = next((err for err in e.errors() if err["loc"][0] == campo), None)
        if erro:
            return False, "", _msg_amigavel(campo, erro["msg"])
        return True, valor, ""


def consultar_cep(cep: str) -> dict | None:
    """
    Consulta o CEP (ViaCEP com fallback BrasilAPI). Retorna dict com
    logradouro/bairro/municipio/uf (município/UF já validados pelo
    EmitenteModel quando possível) ou None se CEP não encontrado em
    nenhuma fonte.
    """
    end_api = buscar_endereco_por_cep(cep)
    if not end_api:
        return None

    log_api = end_api.get("logradouro", "").strip()
    bairro_api = end_api.get("bairro", "").strip()
    mun_api = end_api.get("cidade", "").strip()
    uf_api = end_api.get("uf", "").strip()

    _, municipio, _ = validar_campo_emitente("municipio", mun_api)
    _, uf, _ = validar_campo_emitente("uf", uf_api)

    return {
        "logradouro": log_api,
        "bairro": bairro_api,
        "municipio": municipio or mun_api,
        "uf": uf or uf_api,
    }


def salvar_dados_emitente(dados: dict) -> tuple[bool, list[dict]]:
    """
    Valida e salva o conjunto completo de dados do emitente.
    dados deve conter: razao_social, cnpj, ie, telefone, cep, logradouro,
    numero, bairro, municipio, uf, regime.
    Retorna (sucesso, lista_de_erros) — lista vazia se sucesso.
    """
    dados_completos = dict(dados)
    dados_completos["crt"] = dados_completos.get("regime", "")

    try:
        modelo = EmitenteModel(**dados_completos)
    except ValidationError as e:
        erros = [
            {
                "campo": err["loc"][0],
                "mensagem": _msg_amigavel(err["loc"][0], err["msg"]),
            }
            for err in e.errors()
        ]
        return False, erros

    validado = modelo.model_dump()
    for chave, valor in validado.items():
        if chave == "nome_fantasia" and valor is None:
            continue
        set_config(f"emit_{chave}", str(valor))
    registrar_auditoria(
        "alterar_configuracao",
        "emitente",
        "",
        f"Razão social='{validado.get('razao_social', '')}', CNPJ='{validado.get('cnpj', '')}'",
    )
    return True, []


# ─────────────────────────────────────────
# SETUP INICIAL
# ─────────────────────────────────────────


def setup_concluido() -> bool:
    return get_config("setup_concluido") == "True"


def marcar_setup_concluido():
    set_config("setup_concluido", "True")


def inicializar_flags_padrao():
    """Define PIX e Cartão como desativados por padrão (chamado uma única vez no 1º start)."""
    set_config("pix_ativo", "False")
    set_config("cartao_ativo", "False")
