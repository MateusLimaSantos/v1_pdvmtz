"""
Configuração fiscal para emissão futura de NFC-e real.

IMPORTANTE — leia antes de usar este módulo:
Este módulo apenas ARMAZENA, de forma cifrada, as credenciais que o
lojista vai precisar quando decidir emitir NFC-e de verdade:
  - Certificado digital e-CNPJ A1 (.pfx/.p12) e sua senha
  - CSC (Código de Segurança do Contribuinte) e o ID do token
  - Ambiente (homologação ou produção)

Ele NÃO transmite nada para a SEFAZ. A transmissão real (assinatura
do XML, protocolo de autorização, tratamento de rejeição) ainda
precisa ser implementada quando o lojista tiver as credenciais reais
em mãos e for possível testar contra o ambiente de homologação da
SEFAZ-SP. Até lá, o sistema continua emitindo apenas o cupom interno
não fiscal (ver core/fiscal/cupom.py).

Pré-requisitos que o lojista precisa providenciar ANTES de preencher
esta tela, fora do sistema:
  1. Inscrição Estadual ativa
  2. Certificado digital e-CNPJ modelo A1, comprado em uma
     certificadora credenciada (ICP-Brasil)
  3. Credenciamento para NFC-e no portal da SEFAZ do seu estado
  4. Geração do CSC de produção (e, se quiser testar antes, o CSC
     de homologação também)
"""

import os
from datetime import datetime, timedelta

from cryptography.hazmat.primitives.serialization import pkcs12

from config import DATA_DIR
from core.helpers import get_config, set_config
from core.seguranca import (
    cifrar,
    decifrar,
    mascarar_token,
    cifrar_arquivo,
    decifrar_arquivo_para_bytes,
)
from core.auditoria import registrar_auditoria

_CERTIFICADO_CIFRADO_PATH = os.path.join(DATA_DIR, "certificado_fiscal.pfx.enc")

AMBIENTES_VALIDOS = ("homologacao", "producao")


# ───────────────────────────── Certificado digital A1 ─────────────────────────────


def validar_certificado_a1(caminho_pfx: str, senha: str) -> tuple[bool, str]:
    """
    Tenta abrir o arquivo .pfx/.p12 com a senha informada, só para
    confirmar que o arquivo e a senha são válidos antes de salvar.
    Não faz nenhuma chamada de rede. Retorna (sucesso, mensagem ou
    dados de validade do certificado).
    """
    if not os.path.isfile(caminho_pfx):
        return False, "Arquivo do certificado não encontrado."
    if not senha:
        return False, "Informe a senha do certificado."

    try:
        with open(caminho_pfx, "rb") as f:
            dados = f.read()
        _chave_priv, cert, _outros = pkcs12.load_key_and_certificates(
            dados, senha.encode("utf-8")
        )
    except ValueError:
        return False, "Senha incorreta ou arquivo de certificado inválido/corrompido."
    except OSError as e:
        return False, f"Erro ao ler o arquivo: {e}"

    if cert is None:
        return False, "Não foi possível extrair o certificado do arquivo."

    validade = (
        cert.not_valid_after_utc
        if hasattr(cert, "not_valid_after_utc")
        else cert.not_valid_after
    )
    titular = cert.subject.rfc4514_string()

    agora = datetime.now(validade.tzinfo) if validade.tzinfo else datetime.now()
    if validade < agora:
        return (
            False,
            f"Certificado vencido em {validade.strftime('%d/%m/%Y')}. Providencie a renovação.",
        )

    dias_restantes = (validade.replace(tzinfo=None) - datetime.now()).days
    aviso_validade = ""
    if dias_restantes <= 30:
        aviso_validade = (
            f" ATENÇÃO: vence em {dias_restantes} dia(s), considere renovar em breve."
        )

    return (
        True,
        f"Certificado válido até {validade.strftime('%d/%m/%Y')}.{aviso_validade} Titular: {titular}",
    )


def salvar_certificado_a1(caminho_pfx: str, senha: str) -> tuple[bool, str]:
    """
    Valida e, se válido, cifra e salva o certificado + senha. O
    arquivo original do .pfx não é movido nem apagado — uma cópia
    cifrada é criada em data/certificado_fiscal.pfx.enc.
    """
    ok, msg = validar_certificado_a1(caminho_pfx, senha)
    if not ok:
        registrar_auditoria(
            "alterar_configuracao",
            "certificado_fiscal",
            "",
            f"Falha: {msg}",
            sucesso=False,
        )
        return False, msg

    ok_cifra, msg_cifra = cifrar_arquivo(caminho_pfx, _CERTIFICADO_CIFRADO_PATH)
    if not ok_cifra:
        registrar_auditoria(
            "alterar_configuracao",
            "certificado_fiscal",
            "",
            f"Falha ao cifrar: {msg_cifra}",
            sucesso=False,
        )
        return False, msg_cifra

    set_config("fiscal_certificado_senha", cifrar(senha))
    registrar_auditoria(
        "alterar_configuracao", "certificado_fiscal", "", "Certificado A1 atualizado"
    )
    return True, msg


def certificado_configurado() -> bool:
    return os.path.isfile(_CERTIFICADO_CIFRADO_PATH) and bool(
        get_config("fiscal_certificado_senha", "")
    )


def remover_certificado_a1():
    if os.path.isfile(_CERTIFICADO_CIFRADO_PATH):
        os.remove(_CERTIFICADO_CIFRADO_PATH)
    set_config("fiscal_certificado_senha", "")
    registrar_auditoria(
        "alterar_configuracao", "certificado_fiscal", "", "Certificado removido"
    )


def info_certificado_atual() -> dict | None:
    """
    Decifra o certificado já salvo só para extrair informações de
    validade/titular para exibição — não retorna a senha nem os bytes
    do certificado. Retorna None se não houver certificado salvo ou
    se a decifragem falhar.
    """
    if not certificado_configurado():
        return None
    dados = decifrar_arquivo_para_bytes(_CERTIFICADO_CIFRADO_PATH)
    if dados is None:
        return None
    senha = decifrar(get_config("fiscal_certificado_senha", ""))
    try:
        _chave_priv, cert, _outros = pkcs12.load_key_and_certificates(
            dados, senha.encode("utf-8")
        )
    except (ValueError, AttributeError):
        return None
    if cert is None:
        return None
    validade = (
        cert.not_valid_after_utc
        if hasattr(cert, "not_valid_after_utc")
        else cert.not_valid_after
    )
    dias_restantes = (validade.replace(tzinfo=None) - datetime.now()).days
    return {
        "titular": cert.subject.rfc4514_string(),
        "validade": validade.strftime("%d/%m/%Y"),
        "dias_restantes": dias_restantes,
        "vencido": dias_restantes < 0,
        "vence_em_breve": 0 <= dias_restantes <= 30,
    }


# ───────────────────────────── CSC e ambiente ─────────────────────────────


def salvar_csc(ambiente: str, csc: str, id_token: str) -> tuple[bool, str]:
    if ambiente not in AMBIENTES_VALIDOS:
        return False, "Ambiente inválido. Use 'homologacao' ou 'producao'."
    csc = csc.strip()
    id_token = id_token.strip()
    if not csc or not id_token:
        return False, "Informe o CSC e o ID do token."

    set_config(f"fiscal_csc_{ambiente}", cifrar(csc))
    set_config(f"fiscal_csc_id_{ambiente}", cifrar(id_token))
    registrar_auditoria(
        "alterar_configuracao", "csc_fiscal", ambiente, f"CSC de {ambiente} atualizado"
    )
    return True, f"CSC de {ambiente} salvo."


def csc_configurado(ambiente: str) -> bool:
    if ambiente not in AMBIENTES_VALIDOS:
        return False
    return bool(decifrar(get_config(f"fiscal_csc_{ambiente}", "")))


def csc_id_mascarado(ambiente: str) -> str:
    if ambiente not in AMBIENTES_VALIDOS:
        return ""
    id_token = decifrar(get_config(f"fiscal_csc_id_{ambiente}", ""))
    return mascarar_token(id_token) if id_token else ""


def remover_csc(ambiente: str):
    if ambiente not in AMBIENTES_VALIDOS:
        return
    set_config(f"fiscal_csc_{ambiente}", "")
    set_config(f"fiscal_csc_id_{ambiente}", "")
    registrar_auditoria(
        "alterar_configuracao", "csc_fiscal", ambiente, f"CSC de {ambiente} removido"
    )


def obter_ambiente_ativo() -> str:
    return get_config("fiscal_ambiente_ativo", "homologacao")


def salvar_ambiente_ativo(ambiente: str) -> tuple[bool, str]:
    if ambiente not in AMBIENTES_VALIDOS:
        return False, "Ambiente inválido."
    set_config("fiscal_ambiente_ativo", ambiente)
    registrar_auditoria(
        "alterar_configuracao",
        "csc_fiscal",
        "",
        f"Ambiente ativo definido como '{ambiente}'",
    )
    return True, f"Ambiente ativo: {ambiente}."


# ───────────────────────────── Status geral ─────────────────────────────


def status_emissao_real() -> dict:
    """
    Resumo do que falta configurar antes de a emissão real de NFC-e
    poder ser tentada. Usado pela tela de Configurações para orientar
    o lojista sobre o que falta.
    """
    ambiente = obter_ambiente_ativo()
    info_cert = info_certificado_atual()
    return {
        "certificado_ok": certificado_configurado()
        and info_cert is not None
        and not info_cert.get("vencido", True),
        "info_certificado": info_cert,
        "csc_ok": csc_configurado(ambiente),
        "ambiente_ativo": ambiente,
        "pronto_para_emissao_real": (
            certificado_configurado()
            and info_cert is not None
            and not info_cert.get("vencido", True)
            and csc_configurado(ambiente)
        ),
    }
