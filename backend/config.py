import os

VERSION = "1.0"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "pdv_mtz.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
XML_DIR = os.path.join(DATA_DIR, "xmls_nfe")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(XML_DIR, exist_ok=True)

DESCONTO_MAX_OPERADOR = 10.0  # % máximo que operador pode dar

TIPOS_UNIDADE_VALIDOS = ("unidade", "kg", "g", "litro", "ml")
TIPOS_PESO = ("kg", "g", "litro", "ml")

UNIDADE_LABEL = {"unidade": "un", "kg": "kg", "g": "g", "litro": "L", "ml": "mL"}
