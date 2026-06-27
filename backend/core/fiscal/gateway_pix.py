"""
Integração com gateway de pagamento (Mercado Pago) para gerar PIX
dinâmico e consultar status via polling.

Importante: este módulo nunca decide por conta própria quando usar
contingência — quem decide é o módulo `pagamento.py`, que orquestra
os 3 modos. Aqui só ficam as chamadas HTTP cruas, com timeout curto
e tratamento de erro que NUNCA lança exceção para o chamador: toda
falha de rede, timeout, ou resposta inesperada vira (False, motivo).
"""

import uuid
import requests

from core.seguranca import decifrar

TIMEOUT_SEGUNDOS = (
    6  # curto de propósito: é o que viabiliza a contingência rápida do modo híbrido
)
BASE_URL = "https://api.mercadopago.com"


def criar_cobranca_pix(
    access_token_cifrado: str, valor: float, descricao: str, referencia_externa: str
) -> tuple[bool, dict | str]:
    """
    Cria uma cobrança PIX dinâmica no Mercado Pago.
    Retorna (True, dados) em sucesso, onde dados contém:
      - payment_id: identificador do pagamento no gateway
      - qr_code: texto copia-e-cola
      - qr_code_base64: imagem do QR em base64 (pode vir vazia, ver doc)
    Retorna (False, motivo_do_erro) em qualquer falha — rede, timeout,
    credencial inválida, resposta malformada. Nunca lança exceção.
    """
    token = decifrar(access_token_cifrado)
    if not token:
        return False, "Token de acesso do gateway não configurado."

    payload = {
        "transaction_amount": round(valor, 2),
        "description": descricao[:255],
        "payment_method_id": "pix",
        "external_reference": referencia_externa,
        "payer": {
            "email": "cliente-balcao@pdv.local",
            "first_name": "Cliente",
            "last_name": "Balcão",
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4()),
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/v1/payments",
            json=payload,
            headers=headers,
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.Timeout:
        return False, "Tempo de resposta do gateway excedido."
    except requests.exceptions.ConnectionError:
        return (
            False,
            "Não foi possível conectar ao gateway (sem internet ou serviço indisponível).",
        )
    except requests.exceptions.RequestException as e:
        return False, f"Erro de rede ao falar com o gateway: {e}"

    if resp.status_code == 401:
        return False, "Credencial do gateway inválida ou expirada."
    if resp.status_code >= 500:
        return False, f"Gateway indisponível (HTTP {resp.status_code})."
    if resp.status_code not in (200, 201):
        try:
            detalhe = resp.json().get("message", resp.text[:200])
        except Exception:
            detalhe = resp.text[:200]
        return False, f"Gateway rejeitou a cobrança: {detalhe}"

    try:
        dados = resp.json()
        transacao = dados.get("point_of_interaction", {}).get("transaction_data", {})
        qr_code = transacao.get("qr_code", "")
        if not qr_code:
            return False, "Gateway não retornou QR Code válido."
        return True, {
            "payment_id": str(dados.get("id", "")),
            "qr_code": qr_code,
            "qr_code_base64": transacao.get("qr_code_base64", ""),
            "status": dados.get("status", "pending"),
        }
    except (ValueError, KeyError, AttributeError) as e:
        return False, f"Resposta do gateway em formato inesperado: {e}"


def consultar_status_pagamento(
    access_token_cifrado: str, payment_id: str
) -> tuple[bool, str]:
    """
    Consulta o status atual de um pagamento no gateway (usado pelo polling).
    Retorna (True, status) em sucesso — status é 'pending', 'approved',
    'rejected', 'cancelled', etc. Retorna (False, motivo) em falha de rede.
    """
    token = decifrar(access_token_cifrado)
    if not token:
        return False, "Token de acesso do gateway não configurado."

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            f"{BASE_URL}/v1/payments/{payment_id}",
            headers=headers,
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.Timeout:
        return False, "Tempo de resposta do gateway excedido."
    except requests.exceptions.ConnectionError:
        return False, "Não foi possível conectar ao gateway."
    except requests.exceptions.RequestException as e:
        return False, f"Erro de rede: {e}"

    if resp.status_code != 200:
        return False, f"Gateway retornou erro HTTP {resp.status_code}."

    try:
        return True, resp.json().get("status", "pending")
    except ValueError:
        return False, "Resposta do gateway em formato inesperado."


def testar_credencial(access_token_cifrado: str) -> tuple[bool, str]:
    """
    Valida rapidamente se um access_token é aceito pelo gateway, sem criar
    cobrança real. Usado na tela de configuração ao salvar a credencial.
    """
    token = decifrar(access_token_cifrado)
    if not token:
        return False, "Token vazio."

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            f"{BASE_URL}/users/me", headers=headers, timeout=TIMEOUT_SEGUNDOS
        )
    except requests.exceptions.Timeout:
        return False, "Tempo de resposta excedido ao validar credencial."
    except requests.exceptions.ConnectionError:
        return False, "Sem conexão para validar a credencial agora."
    except requests.exceptions.RequestException as e:
        return False, f"Erro de rede: {e}"

    if resp.status_code == 401:
        return False, "Token inválido ou expirado."
    if resp.status_code != 200:
        return False, f"Resposta inesperada do gateway (HTTP {resp.status_code})."
    return True, "Credencial válida."
