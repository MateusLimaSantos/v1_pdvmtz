"""
Orquestra os 3 modos de recebimento PIX (especificação do lojista):

1. Manual: QR estático local, sem API. Baixa exige clique humano de confirmação.
2. Automático: QR dinâmico via gateway. Baixa automática via polling de status.
3. Híbrido: tenta o gateway; se falhar (timeout, erro, sem resposta), aciona
   automaticamente a contingência manual NA MESMA VENDA, sem bloquear o caixa.

Este módulo é o único lugar que decide qual caminho seguir — gateway_pix.py
só faz a chamada HTTP crua, pix.py só gera o QR estático. Nem um nem o outro
sabe sobre os outros 2 modos.
"""
import uuid

from core.database import get_db_connection
from core.helpers import _iso_now, get_config, set_config
from core.seguranca import cifrar, decifrar, mascarar_token
from core.fiscal.pix import gerar_pdf_pix
from core.fiscal.gateway_pix import criar_cobranca_pix, consultar_status_pagamento, testar_credencial
from core.auditoria import registrar_auditoria

MODOS_VALIDOS = ("manual", "automatico", "hibrido")


# ───────────────────────────── Configuração ─────────────────────────────

def obter_modo_pagamento() -> str:
    return get_config("pix_modo_pagamento", "manual")


def salvar_modo_pagamento(modo: str) -> tuple[bool, str]:
    if modo not in MODOS_VALIDOS:
        return False, "Modo inválido."
    set_config("pix_modo_pagamento", modo)
    registrar_auditoria("alterar_configuracao", "pagamento", "", f"Modo definido como '{modo}'")
    return True, f"Modo de pagamento definido como '{modo}'."


def salvar_credencial_gateway(access_token: str, testar: bool = True) -> tuple[bool, str]:
    """Cifra e salva o access_token do gateway. Se testar=True, valida a
    credencial com o gateway antes de salvar definitivamente."""
    access_token = access_token.strip()
    if not access_token:
        return False, "Informe o access token."

    if testar:
        token_cifrado_temp = cifrar(access_token)
        ok, msg = testar_credencial(token_cifrado_temp)
        if not ok:
            registrar_auditoria(
                "alterar_configuracao", "gateway_pix", "",
                f"Falha ao validar nova credencial: {msg}", sucesso=False,
            )
            return False, f"Credencial não pôde ser validada: {msg}"

    cifrado = cifrar(access_token)
    set_config("pix_gateway_token", cifrado)
    registrar_auditoria(
        "alterar_configuracao", "gateway_pix", "",
        f"Credencial atualizada (token termina em ...{mascarar_token(access_token)[-4:]})",
    )
    return True, "Credencial do gateway salva e validada."


def remover_credencial_gateway():
    set_config("pix_gateway_token", "")
    registrar_auditoria("alterar_configuracao", "gateway_pix", "", "Credencial removida")


def gateway_configurado() -> bool:
    token_cifrado = get_config("pix_gateway_token", "")
    return bool(decifrar(token_cifrado))


def token_mascarado_atual() -> str:
    token_cifrado = get_config("pix_gateway_token", "")
    token = decifrar(token_cifrado)
    return mascarar_token(token) if token else ""


# ───────────────────────────── Iniciar cobrança ─────────────────────────────

def iniciar_cobranca(valor: float, descricao: str = "Venda PDV") -> dict:
    """
    Ponto de entrada único do PDV para iniciar um recebimento PIX,
    respeitando o modo configurado. Retorna um dict sempre com a
    chave 'modo_efetivo' (o modo que de fato foi usado nesta cobrança
    específica — pode diferir do modo configurado, no caso de
    contingência do híbrido) e demais campos conforme o caminho:

    Caminho manual / contingência:
      {'modo_efetivo': 'manual', 'sucesso': True, 'pdf_path': str,
       'referencia': str, 'contingencia': bool}

    Caminho automático bem-sucedido:
      {'modo_efetivo': 'automatico', 'sucesso': True, 'referencia': str,
       'payment_id': str, 'qr_code': str, 'qr_code_base64': str}

    Falha total (não deveria ocorrer no híbrido, que sempre cai para manual,
    mas pode ocorrer no modo 'automatico' puro sem fallback):
      {'modo_efetivo': 'automatico', 'sucesso': False, 'motivo': str}
    """
    modo = obter_modo_pagamento()
    referencia = f"PDV-{uuid.uuid4().hex[:12]}"

    if modo == "manual":
        return _cobranca_manual(valor, referencia)

    if modo == "automatico":
        resultado = _tentar_cobranca_automatica(valor, descricao, referencia)
        if resultado["sucesso"]:
            return resultado
        # Modo automático puro, sem rede de segurança: expõe a falha
        # ao caixa para decisão manual de como proceder (não inventa
        # contingência silenciosa quando o lojista optou só por automático).
        registrar_auditoria(
            "pix_automatico_falhou", "pagamento", referencia,
            f"Falha sem contingência configurada: {resultado['motivo']}", sucesso=False,
        )
        return resultado

    if modo == "hibrido":
        resultado = _tentar_cobranca_automatica(valor, descricao, referencia)
        if resultado["sucesso"]:
            return resultado
        # Contingência: cai para manual automaticamente, na mesma venda.
        registrar_auditoria(
            "contingencia_acionada", "pagamento", referencia,
            f"Gateway falhou ({resultado['motivo']}); usando Pix estático manual",
        )
        manual = _cobranca_manual(valor, referencia)
        manual["contingencia"] = True
        manual["motivo_contingencia"] = resultado["motivo"]
        return manual

    # Modo desconhecido (config corrompida) — cai em manual por segurança,
    # já que manual nunca depende de rede nem de credenciais.
    registrar_auditoria(
        "pagamento", "pagamento", referencia, f"Modo desconhecido '{modo}', usando manual", sucesso=False
    )
    return _cobranca_manual(valor, referencia)


def _cobranca_manual(valor: float, referencia: str) -> dict:
    sucesso, resultado = gerar_pdf_pix(valor)
    _registrar_cobranca(referencia, payment_id="", valor=valor, modo="manual")
    if not sucesso:
        return {
            "modo_efetivo": "manual",
            "sucesso": False,
            "motivo": resultado,
            "referencia": referencia,
            "contingencia": False,
        }
    return {
        "modo_efetivo": "manual",
        "sucesso": True,
        "pdf_path": resultado,
        "referencia": referencia,
        "contingencia": False,
    }


def _tentar_cobranca_automatica(valor: float, descricao: str, referencia: str) -> dict:
    if not gateway_configurado():
        return {
            "modo_efetivo": "automatico", "sucesso": False,
            "motivo": "Gateway não configurado.", "referencia": referencia,
        }

    token_cifrado = get_config("pix_gateway_token", "")
    ok, resultado = criar_cobranca_pix(token_cifrado, valor, descricao, referencia)
    if not ok:
        return {
            "modo_efetivo": "automatico", "sucesso": False,
            "motivo": resultado, "referencia": referencia,
        }

    _registrar_cobranca(
        referencia, payment_id=resultado["payment_id"], valor=valor, modo="automatico"
    )
    return {
        "modo_efetivo": "automatico",
        "sucesso": True,
        "referencia": referencia,
        "payment_id": resultado["payment_id"],
        "qr_code": resultado["qr_code"],
        "qr_code_base64": resultado.get("qr_code_base64", ""),
    }


# ───────────────────────────── Acompanhar / baixar ─────────────────────────────

def _registrar_cobranca(referencia: str, payment_id: str, valor: float, modo: str):
    agora = _iso_now()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO cobrancas_pix (referencia, payment_id, valor, modo, status, "
            "data_criacao, data_atualizacao) VALUES (?,?,?,?,'pendente',?,?)",
            (referencia, payment_id, valor, modo, agora, agora),
        )


def confirmar_recebimento_manual(referencia: str) -> tuple[bool, str]:
    """Usado pelo caixa ao clicar 'Confirmar Recebimento' no modo manual/contingência."""
    with get_db_connection() as conn:
        updated = conn.execute(
            "UPDATE cobrancas_pix SET status='aprovado', data_atualizacao=? "
            "WHERE referencia=? AND status='pendente'",
            (_iso_now(), referencia),
        ).rowcount
    if updated:
        registrar_auditoria("confirmar_pagamento", "pagamento", referencia, "Confirmado manualmente pelo caixa")
        return True, "Recebimento confirmado."
    return False, "Cobrança não encontrada ou já processada."


def consultar_status_cobranca(referencia: str) -> tuple[bool, str]:
    """
    Usado pelo polling do modo automático. Consulta o gateway e atualiza
    o status local. Retorna (True, status_atual) ou (False, motivo_erro).
    status_atual pode ser: 'pendente', 'aprovado', 'rejeitado', etc.
    """
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM cobrancas_pix WHERE referencia=?", (referencia,)
        ).fetchone()
    if not row:
        return False, "Cobrança não encontrada."
    cobranca = dict(row)

    if cobranca["status"] != "pendente":
        return True, cobranca["status"]

    token_cifrado = get_config("pix_gateway_token", "")
    ok, status_gateway = consultar_status_pagamento(token_cifrado, cobranca["payment_id"])
    if not ok:
        # Falha de consulta não muda o status local — só reporta o erro,
        # o polling tenta de novo na próxima iteração.
        return False, status_gateway

    mapa_status = {
        "approved": "aprovado",
        "rejected": "erro",
        "cancelled": "cancelado",
        "pending": "pendente",
        "in_process": "pendente",
    }
    novo_status = mapa_status.get(status_gateway, "pendente")
    if novo_status != cobranca["status"]:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE cobrancas_pix SET status=?, data_atualizacao=? WHERE referencia=?",
                (novo_status, _iso_now(), cobranca["referencia"]),
            )
        if novo_status == "aprovado":
            registrar_auditoria("confirmar_pagamento", "pagamento", cobranca["referencia"], "Aprovado via gateway (polling)")
    return True, novo_status


def cancelar_cobranca(referencia: str) -> tuple[bool, str]:
    """Marca uma cobrança como cancelada (ex: cliente desistiu, operador trocou de forma de pagamento)."""
    with get_db_connection() as conn:
        updated = conn.execute(
            "UPDATE cobrancas_pix SET status='cancelado', data_atualizacao=? "
            "WHERE referencia=? AND status='pendente'",
            (_iso_now(), referencia),
        ).rowcount
    if updated:
        return True, "Cobrança cancelada."
    return False, "Cobrança não encontrada ou já processada."
