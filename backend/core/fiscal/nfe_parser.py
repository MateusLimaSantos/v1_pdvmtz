import xml.etree.ElementTree as ET


def parsear_xml_nfe(xml_str: str) -> list[dict]:
    NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

    try:
        root = (
            ET.fromstring(xml_str)
            if isinstance(xml_str, str)
            else ET.parse(xml_str).getroot()
        )
    except ET.ParseError as e:
        raise ValueError(f"XML inválido: {e}")

    itens_det = root.findall(".//nfe:det", NS) or root.findall(".//det")
    if not itens_det:
        raise ValueError("Nenhum <det>. Verifique se é uma NF-e válida.")

    def _txt(pai, tag: str) -> str:
        el = pai.find(f"nfe:{tag}", NS)
        if el is None:
            el = pai.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    MAPA_UNIDADE = {
        "KG": "kg",
        "G": "g",
        "GR": "g",
        "L": "litro",
        "LT": "litro",
        "ML": "ml",
        "UN": "unidade",
        "PC": "unidade",
        "CX": "unidade",
    }

    itens = []
    for det in itens_det:
        prod = det.find("nfe:prod", NS) or det.find("prod")
        if prod is None:
            continue
        ean = _txt(prod, "cEAN") or _txt(prod, "cEANTrib") or ""
        if ean.upper() in ("", "SEM GTIN", "SEMGTIN"):
            ean = f"NCMEAN_{_txt(prod, 'cProd')}"
        un_nfe = _txt(prod, "uCom").upper()
        tipo_un = MAPA_UNIDADE.get(un_nfe, "unidade")
        qtd = float(_txt(prod, "qCom") or 0)
        preco_unit = float(_txt(prod, "vUnCom") or 0)

        itens.append(
            {
                "ean": ean,
                "nome": _txt(prod, "xProd"),
                "qtd": qtd,
                "preco": preco_unit,
                "ncm": _txt(prod, "NCM"),
                "unidade": un_nfe,
                "tipo_unidade": tipo_un,
            }
        )
    return itens
