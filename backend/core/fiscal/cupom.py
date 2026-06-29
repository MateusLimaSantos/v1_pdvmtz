import os
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from config import REPORTS_DIR, UNIDADE_LABEL
from core.helpers import get_dados_emitente
from core.fiscal.pix import _pdf_safe


def formatar_cupom(
    itens: list[dict],
    total: float,
    desconto_venda: float,
    forma_pagamento: str,
    troco: float = 0.0,
) -> tuple[str, str]:
    emit = get_dados_emitente()
    data_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_br = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    end_emit = (
        f"{emit['logradouro']}, {emit['numero']} - "
        f"{emit['bairro']} - {emit['municipio']}/{emit['uf']}"
    )

    linhas = [
        "=" * 44,
        emit["razao_social"].center(44),
        f"CNPJ: {emit['cnpj']}".center(44),
        end_emit[:44].center(44),
        "=" * 44,
        f" Data: {data_br}",
        "-" * 44,
    ]
    for item in itens:
        un = UNIDADE_LABEL.get(item.get("tipo_unidade", "unidade"), "un")
        qtd_s = (
            f"{item['qtd']:.3f}{un}"
            if item.get("tipo_unidade") in ("kg", "g", "litro", "ml")
            else f"{item['qtd']:.0f}x"
        )
        di = item.get("desconto_item", 0)
        desc_s = f" (-R${di:.2f})" if di > 0 else ""
        linha = f" {qtd_s} {item['nome']}{desc_s}"
        preco_s = f"R$ {item['preco_total']:.2f}"
        esp = 44 - len(linha) - len(preco_s)
        linhas.append(linha + ("." * max(1, esp)) + preco_s)

    linhas.append("-" * 44)
    if desconto_venda > 0:
        linhas.append(f" Desconto venda:         -R$ {desconto_venda:.2f}")
    linhas += [
        f" TOTAL:          R$ {total:.2f}",
        f" FORMA DE PAGTO: {forma_pagamento}",
    ]
    if troco > 0:
        linhas.append(f" TROCO:          R$ {troco:.2f}")
    linhas += [
        "=" * 44,
        "   Obrigado pela preferencia!",
        "=" * 44,
    ]
    return "\n".join(linhas), data_iso


def exportar_pdf_cupom(cupom_texto: str, numero_nota: int) -> str:
    """Gera o PDF do cupom interno (não fiscal) de venda e retorna o caminho do arquivo gerado."""
    emit = get_dados_emitente()
    end_emit = _pdf_safe(f"{emit['logradouro']}, {emit['numero']} - {emit['bairro']}")

    nome_arq = os.path.join(REPORTS_DIR, f"Cupom_Venda_{numero_nota:04d}.pdf")

    pdf = FPDF(format=(80, 270))
    pdf.add_page()
    pdf.set_margins(left=2, top=5, right=2)
    pdf.set_auto_page_break(auto=True, margin=5)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
        0,
        4,
        _pdf_safe(emit["razao_social"]),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        align="C",
    )
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(
        0,
        3,
        _pdf_safe(f"CNPJ: {emit['cnpj']} | IE: {emit['ie']}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        align="C",
    )
    pdf.cell(0, 3, end_emit, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(
        0,
        3,
        _pdf_safe(f"{emit['municipio']}/{emit['uf']} | CEP: {emit['cep']}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        align="C",
    )
    pdf.line(2, pdf.get_y() + 1, 78, pdf.get_y() + 1)
    pdf.ln(3)

    # Aviso bem visível: este é um comprovante interno, NÃO um documento
    # fiscal. O sistema ainda não emite NFC-e/SAT reais (ver core/configuracoes
    # e a aba Fiscal do painel admin). Nenhum QR code de consulta fiscal real
    # deve ser gerado aqui, para não sugerir validade fiscal que não existe.
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(180, 0, 0)
    pdf.multi_cell(
        0,
        3.5,
        "COMPROVANTE INTERNO\nNAO TEM VALOR FISCAL",
        align="C",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.line(2, pdf.get_y() + 1, 78, pdf.get_y() + 1)
    pdf.ln(3)

    pdf.set_font("Courier", "", 6)
    for linha in cupom_texto.split("\n"):
        pdf.cell(0, 3, _pdf_safe(linha), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.line(2, pdf.get_y() + 1, 78, pdf.get_y() + 1)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(180, 0, 0)
    pdf.multi_cell(
        0,
        3,
        "Este comprovante e gerado internamente pelo\n"
        "estabelecimento e nao substitui documento fiscal.",
        align="C",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.output(nome_arq)
    return nome_arq
