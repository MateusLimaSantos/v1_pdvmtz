import os
import re
import socket
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

from config import XML_DIR, TIPOS_PESO
from core.database import get_db_connection
from core.helpers import _iso_now, get_config, set_config
from core.fiscal.nfe_parser import parsear_xml_nfe
from core.state import state


def tem_internet(host="nfe.fazenda.gov.br", porta=443, timeout=4) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, porta))
        s.close()
        return True
    except (socket.error, OSError):
        return False


def salvar_chave_pendente(chave: str, motivo: str = "") -> tuple[bool, str]:
    with get_db_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO nfe_pendentes (chave,motivo,criado_em) VALUES (?,?,?)",
                (chave, motivo, _iso_now()),
            )
            return True, "Chave salva na fila offline."
        except sqlite3.IntegrityError:
            return False, "Chave já está na fila."


def listar_pendentes() -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM nfe_pendentes WHERE status='pendente'"
        ).fetchall()
    return [dict(r) for r in rows]


def consultar_nfe_por_chave_online(chave: str) -> tuple[str | None, str]:
    """Retorna (xml_str_ou_None, mensagem_de_status)."""
    try:
        import requests
    except ImportError:
        return None, "'requests' não instalado."

    uf = chave[:2]
    url = {"35": "https://nfe.fazenda.sp.gov.br/ws/nfeconsulta2.asmx"}.get(
        uf, "https://nfe.fazenda.gov.br/NfeConsulta2/NfeConsulta2.asmx"
    )
    env = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4">
      <consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
        <tpAmb>1</tpAmb><xServ>CONSULTAR</xServ><chNFe>{chave}</chNFe>
      </consSitNFe>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""

    try:
        import requests as req

        r = req.post(
            url,
            data=env.encode("utf-8"),
            headers={"Content-Type": "application/soap+xml; charset=utf-8"},
            timeout=15,
            verify=True,
        )
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
            proc = root.find(".//nfe:procNFe", ns)
            if proc is not None:
                return ET.tostring(proc, encoding="unicode"), "OK"
            cstat = root.findtext(".//nfe:cStat", namespaces=ns) or "?"
            xmot = root.findtext(".//nfe:xMotivo", namespaces=ns) or ""
            return None, f"SEFAZ cStat={cstat}: {xmot}"
        return None, f"HTTP {r.status_code}"
    except Exception as e:
        return None, f"Falha SEFAZ: {e}"


def consultar_nfes_por_cnpj_online(
    cnpj: str, pfx_path: str, pfx_senha: str
) -> tuple[list[str], str]:
    """Retorna (lista_de_xmls, mensagem_de_status)."""
    try:
        import requests, gzip, base64, tempfile
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PrivateFormat,
            NoEncryption,
        )
    except ImportError as e:
        return (
            [],
            f"Dependência faltando: {e}. Execute: pip install requests cryptography",
        )

    try:
        with open(pfx_path, "rb") as f:
            pfx_data = f.read()
        chave_priv, cert, _ = pkcs12.load_key_and_certificates(
            pfx_data, pfx_senha.encode()
        )
        chave_pem = chave_priv.private_bytes(
            Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
        )
        cert_pem = cert.public_bytes(Encoding.PEM)
    except Exception as e:
        return [], f"Certificado: {e}"

    tmp_cert = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    tmp_key = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    status_final = "OK"
    try:
        tmp_cert.write(cert_pem)
        tmp_cert.close()
        tmp_key.write(chave_pem)
        tmp_key.close()

        url = (
            "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
        )
        xmls = []
        ult_nsu = get_config("sefaz_ult_nsu", "0")

        while True:
            env = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
        <tpAmb>1</tpAmb><cUFAutor>35</cUFAutor><CNPJ>{cnpj}</CNPJ>
        <distNSU><ultNSU>{ult_nsu.zfill(15)}</ultNSU></distNSU>
      </distDFeInt>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""
            import requests as req

            r = req.post(
                url,
                data=env.encode("utf-8"),
                headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                cert=(tmp_cert.name, tmp_key.name),
                timeout=30,
                verify=True,
            )
            if r.status_code != 200:
                status_final = f"HTTP {r.status_code}"
                break

            root_r = ET.fromstring(r.text)
            ns_d = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
            cstat = root_r.findtext(".//nfe:cStat", namespaces=ns_d)
            max_nsu = root_r.findtext(".//nfe:maxNSU", namespaces=ns_d)
            ult_ret = root_r.findtext(".//nfe:ultNSU", namespaces=ns_d)

            if cstat == "137":
                status_final = "Sem documentos novos."
                break
            if cstat != "138":
                status_final = f"cStat={cstat}"
                break

            for doc in root_r.findall(".//nfe:docZip", namespaces=ns_d):
                schema = doc.get("schema", "")
                if "procNFe" in schema or "NFe" in schema:
                    xmls.append(
                        gzip.decompress(base64.b64decode(doc.text)).decode("utf-8")
                    )

            if max_nsu and ult_ret:
                set_config("sefaz_ult_nsu", max_nsu)
                if ult_ret >= max_nsu:
                    break
                ult_nsu = max_nsu
            else:
                break

        return xmls, status_final
    finally:
        for f in [tmp_cert.name, tmp_key.name]:
            try:
                os.remove(f)
            except OSError:
                pass


def processar_fila_pendentes() -> list[str]:
    """Tenta resolver as chaves pendentes online. Retorna lista de mensagens de log."""
    log = []
    pendentes = listar_pendentes()
    if not pendentes:
        return log
    log.append(f"Fila offline: {len(pendentes)} chave(s). Processando...")
    for row in pendentes:
        chave = row["chave"]
        xml_str, msg = consultar_nfe_por_chave_online(chave)
        if xml_str:
            cam = os.path.join(XML_DIR, f"NFe_{chave}.xml")
            with open(cam, "w", encoding="utf-8") as f:
                f.write(xml_str)
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE nfe_pendentes SET status='resolvido', xml_path=? WHERE chave=?",
                    (cam, chave),
                )
            log.append(f"Salvo: {cam}")
        else:
            log.append(f"Chave {chave[:10]}...: {msg}")
    return log


def preparar_entrada_itens(itens: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Separa os itens de uma NF-e entre os que já existem no estoque
    (existentes) e os que precisarão ser cadastrados (novos).
    Não altera o banco — apenas classifica para a tela confirmar.
    """
    existentes, novos = [], []
    with get_db_connection() as conn:
        for item in itens:
            row = conn.execute(
                "SELECT ean FROM produtos WHERE ean=?", (item["ean"],)
            ).fetchone()
            (existentes if row else novos).append(item)
    return existentes, novos


def dar_entrada_itens(
    itens: list[dict], cadastrar_novos_automaticamente: bool = False
) -> tuple[bool, str, int]:
    """
    Executa a entrada de estoque para os itens de uma NF-e em uma única transação.
    Itens já cadastrados têm o estoque incrementado; itens novos são cadastrados
    automaticamente apenas se cadastrar_novos_automaticamente=True.
    Retorna (sucesso, mensagem, quantidade_importada).
    """
    if not itens:
        return False, "Nenhum item.", 0

    importados = 0
    novos_pulados = []

    try:
        with get_db_connection() as conn:
            for item in itens:
                row = conn.execute(
                    "SELECT ean FROM produtos WHERE ean=?", (item["ean"],)
                ).fetchone()
                if row:
                    conn.execute(
                        "UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE ean=?",
                        (item["qtd"], item["ean"]),
                    )
                    conn.execute(
                        "INSERT INTO movimentacoes_estoque "
                        "(produto_ean, data_hora, tipo, qtd, motivo, operador_id) VALUES (?,?,?,?,?,?)",
                        (
                            item["ean"],
                            _iso_now(),
                            "entrada",
                            item["qtd"],
                            "Importação XML NF-e",
                            state.operador["id"] if state.operador else None,
                        ),
                    )
                    importados += 1
                elif cadastrar_novos_automaticamente:
                    try:
                        tipo_un = item.get("tipo_unidade", "unidade")
                        preco_r = item["preco"] if tipo_un in TIPOS_PESO else None
                        conn.execute(
                            "INSERT INTO produtos "
                            "(ean,nome,descricao,preco_venda,estoque_atual,"
                            "tipo_unidade,preco_referencia) VALUES (?,?,?,?,?,?,?)",
                            (
                                item["ean"],
                                item["nome"],
                                f"NCM:{item.get('ncm','')} | XML NF-e",
                                item["preco"],
                                item["qtd"],
                                tipo_un,
                                preco_r,
                            ),
                        )
                        conn.execute(
                            "INSERT INTO movimentacoes_estoque "
                            "(produto_ean,data_hora,tipo,qtd,motivo,operador_id) VALUES (?,?,?,?,?,?)",
                            (
                                item["ean"],
                                _iso_now(),
                                "entrada",
                                item["qtd"],
                                "Cadastro via XML NF-e",
                                state.operador["id"] if state.operador else None,
                            ),
                        )
                        importados += 1
                    except sqlite3.IntegrityError:
                        novos_pulados.append(item["ean"])
                else:
                    novos_pulados.append(item["ean"])
    except Exception as e:
        return False, f"Erro na transação: {e} — nenhuma alteração foi salva.", 0

    msg = f"{importados} produto(s) atualizados no estoque."
    if novos_pulados:
        msg += f" {len(novos_pulados)} item(ns) não cadastrado(s) foram ignorados."
    return True, msg, importados


def carregar_xml_de_arquivo(caminho: str) -> tuple[list[dict] | None, str]:
    """Lê e parseia um arquivo XML local. Retorna (itens_ou_None, mensagem_de_erro)."""
    caminho = caminho.strip().strip('"')
    if not os.path.exists(caminho):
        return None, "Arquivo não encontrado."
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            xml_str = f.read()
        return parsear_xml_nfe(xml_str), ""
    except ValueError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Erro: {e}"


def consultar_por_chave(chave_raw: str) -> tuple[str, str]:
    """Valida o formato da chave de acesso. Retorna (chave_limpa, erro) — erro vazio se ok."""
    chave = re.sub(r"\D", "", chave_raw)
    if len(chave) != 44:
        return "", f"Chave inválida ({len(chave)} dígitos, esperado 44)."
    return chave, ""
