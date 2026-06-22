import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

for caminho in (BASE_DIR, BACKEND_DIR):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

from core.database import inicializar_banco
from core.configuracoes import setup_concluido
from gui.setup import SetupInicial
from gui.app import AppPDV


def main():
    inicializar_banco()

    if not setup_concluido():
        setup = SetupInicial()
        if not setup.run():
            return

    app = AppPDV()
    app.run()


if __name__ == "__main__":
    main()
