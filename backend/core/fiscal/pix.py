import os
import qrcode
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from config import BASE_DIR, REPORTS_DIR
from core.helpers import get_config, get_dados_emitente


def calcular_crc16(payload: str) -> str:
    crc = 0xFFFF
    for char in payload:
        crc ^= ord(char) << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def gerar_payload_pix(
    chave: str, valor: float, nome: str = "LOJA MTZ", cidade: str = "ITAPEVI"
) -> str:
    if len(chave) == 13 and chave.startswith("55") and chave.isdigit():
        chave = f"+{chave}"
    nome = nome[:25].upper()
    cidade = cidade[:15].upper()
    vs = f"{valor:.2f}"

    def f(id_: str, v: str) -> str:
        return f"{id_}{len(v):02d}{v}"

    payload = (
        "000201"
        + f("26", f("00", "br.gov.bcb.pix") + f("01", chave))
        + "52040000"
        + "5303986"
        + f("54", vs)
        + "5802BR"
        + f("59", nome)
        + f("60", cidade)
        + f("62", f("05", "***"))
        + "6304"
    )
    return payload + calcular_crc16(payload)


def _pdf_safe(texto: str) -> str:
    """Substitui caracteres fora do Latin-1 para compatibilidade com fpdf2 core fonts."""
    sub = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u00b7": ".",
        "\u2026": "...",
        "\u20ac": "EUR",
        "\u00a0": " ",
    }
    for orig, rep in sub.items():
        texto = texto.replace(orig, rep)
    return texto.encode("latin-1", errors="replace").decode("latin-1")


def gerar_pdf_pix(total: float) -> tuple[bool, str]:
    """
    Gera o PDF do QR Code PIX para o valor informado.
    Retorna (sucesso, caminho_do_arquivo_ou_mensagem_de_erro).
    """
    chave_loja = get_config("pix_chave")
    if not chave_loja:
        return False, "Chave PIX não configurada."

    nome_loja = get_config("pix_nome", "LOJA MTZ")
    cidade = get_config("emit_municipio", "ITAPEVI")
    payload = gerar_payload_pix(chave_loja, total, nome=nome_loja, cidade=cidade)
    emit = get_dados_emitente()

    tmp_qr = os.path.join(BASE_DIR, "_temp_qr_pix.png")
    qrcode.make(payload).save(tmp_qr)

    nome_arq = os.path.join(
        REPORTS_DIR, f"PIX_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    pdf = FPDF(format=(80, 110))
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "PAGAMENTO PIX", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        0,
        5,
        _pdf_safe(emit["razao_social"]),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        align="C",
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 6, f"Valor: R$ {total:.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C"
    )
    pdf.cell(
        0,
        5,
        _pdf_safe(f"Chave: {chave_loja}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        align="C",
    )
    pdf.ln(2)
    pdf.image(tmp_qr, x=15, y=pdf.get_y(), w=50)
    pdf.ln(55)
    pdf.set_font("Helvetica", "", 7)
    pdf.multi_cell(
        0,
        3,
        "Escaneie o QR Code no seu banco.\nApos confirmar, informe ao caixa.",
        align="C",
    )
    pdf.output(nome_arq)

    if os.path.exists(tmp_qr):
        os.remove(tmp_qr)
    return True, nome_arq
