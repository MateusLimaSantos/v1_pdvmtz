import re
from pydantic import BaseModel, Field, field_validator

UFS_VALIDAS = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}


def validar_cnpj(cnpj: str) -> bool:
    """Valida dígitos verificadores do CNPJ."""
    cnpj = re.sub(r"\D", "", cnpj)
    if len(cnpj) != 14:
        return False
    # Rejeita sequências de dígitos iguais (ex: 00000000000000)
    if cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    dv1 = 0 if resto < 2 else 11 - resto
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    dv2 = 0 if resto < 2 else 11 - resto
    return cnpj[-2:] == f"{dv1}{dv2}"


class EmitenteModel(BaseModel):
    razao_social: str
    nome_fantasia: str | None = None
    cnpj: str
    ie: str
    logradouro: str
    numero: str = Field(pattern=r"^\d+[A-Za-z]?$|^S/N$")
    bairro: str
    municipio: str
    uf: str
    cep: str
    telefone: str
    regime: str = Field(pattern=r"^[1-3]$")
    crt: str = Field(pattern=r"^[1-3]$")

    # ── telefone ──────────────────────────────────────────────────────────
    @field_validator("telefone", mode="before")
    @classmethod
    def validar_telefone(cls, v):
        tel = re.sub(r"\D", "", str(v))
        if len(tel) not in (10, 11):
            raise ValueError("Telefone deve ter 10 ou 11 dígitos (DDD + número).")
        if tel == tel[0] * len(tel):
            raise ValueError("Telefone inválido (sequência repetida).")
        return tel

    # ── Número ───────────────────────────────────────────────────────────
    @field_validator("numero")
    @classmethod
    def validar_numero(cls, v):
        v = v.strip().upper()
        if not re.match(r"^\d+[A-Za-z]?$|^S/N$", v):
            raise ValueError(
                "Número inválido. Use apenas dígitos (ex: 123, 42A) ou S/N para sem número."
            )
        return v

    # ── UF ───────────────────────────────────────────────────────────────
    @field_validator("uf")
    @classmethod
    def validar_uf(cls, v):
        uf = str(v).strip().upper()
        if uf not in UFS_VALIDAS:
            raise ValueError("UF inválida. Use a sigla do estado (ex: SP, RJ, MG).")
        return uf

    # ── CEP ──────────────────────────────────────────────────────────────
    @field_validator("cep")
    @classmethod
    def validar_cep(cls, v):
        cep = re.sub(r"\D", "", str(v))
        if len(cep) != 8:
            raise ValueError("CEP deve ter 8 dígitos.")
        if cep == cep[0] * 8:
            raise ValueError("CEP inválido (sequência repetida).")
        return f"{cep[:5]}-{cep[5:]}"  # padroniza para XXXXX-XXX

    # ── CNPJ ─────────────────────────────────────────────────────────────
    @field_validator("cnpj")
    @classmethod
    def validar_cnpj_field(cls, v):
        if not validar_cnpj(v):
            raise ValueError("CNPJ inválido. Verifique os dígitos verificadores.")
        digits = re.sub(r"\D", "", v)
        # Padroniza para XX.XXX.XXX/XXXX-XX
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"

    # ── Razão social ─────────────────────────────────────────────────────
    @field_validator("razao_social")
    @classmethod
    def validar_razao_social(cls, v):
        nome = re.sub(r"\s+", " ", str(v).strip())
        if len(nome) < 3:
            raise ValueError("Razão social deve ter ao menos 3 caracteres.")
        return nome.upper()

    # ── Nome fantasia caso tenha ─────────────────────────────────────────
    @field_validator("nome_fantasia")
    @classmethod
    def validar_nome_fantasia(cls, v):
        if not v:
            return None
        return re.sub(r"\s+", " ", str(v).strip()).upper()

    # ── IE ───────────────────────────────────────────────────────────────
    @field_validator("ie")
    @classmethod
    def validar_ie(cls, v):
        ie = str(v).strip().upper()
        if len(ie) < 2:
            raise ValueError("Inscrição Estadual inválida.")
        return ie

    # ── Logradouro ───────────────────────────────────────────────────────
    @field_validator("logradouro")
    @classmethod
    def validar_logradouro(cls, v):
        log = re.sub(r"\s+", " ", str(v).strip())
        if len(log) < 3:
            raise ValueError("Logradouro inválido.")
        return log.upper()

    # ── Bairro ───────────────────────────────────────────────────────────
    @field_validator("bairro")
    @classmethod
    def validar_bairro(cls, v):
        bairro = re.sub(r"\s+", " ", str(v).strip())
        if len(bairro) < 2:
            raise ValueError("Bairro inválido.")
        return bairro.upper()

    # ── Município ────────────────────────────────────────────────────────
    @field_validator("municipio")
    @classmethod
    def validar_municipio(cls, v):
        mun = re.sub(r"\s+", " ", str(v).strip())
        if len(mun) < 2:
            raise ValueError("Município inválido.")
        return mun.upper()
