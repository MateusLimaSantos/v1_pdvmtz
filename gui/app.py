import tkinter as tk
from gui.login import TelaLogin
from gui.screens.pdv import TelaPDV
from gui.screens.estoque import TelaEstoque
from gui.screens.nfe import TelaNFe
from core.state import state


class AppPDV:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema Corporativo PDV - MTZ")
        self.root.geometry("1024x768")
        self.root.state("zoomed")

        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.mostrar_login()

    def limpar_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def mostrar_login(self):
        self.limpar_container()
        TelaLogin(self.container, self.ao_logar)

    def ao_logar(self):
        self.mostrar_pdv()

    def realizar_logoff(self):
        state.operador = None
        state.caixa_id = None
        self.mostrar_login()

    def mostrar_tela_principal(self):
        self.limpar_container()

        frame_menu = tk.Frame(self.container)
        frame_menu.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            frame_menu,
            text=f"Painel Principal — Operador: {state.operador['nome'].upper()}",
            font=("Arial", 20, "bold"),
            fg="#333",
        ).pack(pady=(0, 40))

        tk.Button(
            frame_menu,
            text="🛒 Abrir Frente de Caixa",
            font=("Arial", 14),
            width=25,
            height=2,
            bg="#2196F3",
            fg="white",
            bd=0,
            command=self.mostrar_pdv,
        ).pack(pady=8)
        tk.Button(
            frame_menu,
            text="📦 Controle de Estoque",
            font=("Arial", 14),
            width=25,
            height=2,
            bg="#FF9800",
            fg="white",
            bd=0,
            command=self.mostrar_estoque,
        ).pack(pady=8)

        # NOVO BOTÃO AQUI:
        tk.Button(
            frame_menu,
            text="📥 Importar XML (NF-e)",
            font=("Arial", 14),
            width=25,
            height=2,
            bg="#673AB7",
            fg="white",
            bd=0,
            command=self.mostrar_nfe,
        ).pack(pady=8)

        tk.Button(
            frame_menu,
            text="🚪 Realizar Logoff (Sair)",
            font=("Arial", 12),
            width=25,
            height=1,
            bg="#f44336",
            fg="white",
            bd=0,
            command=self.realizar_logoff,
        ).pack(pady=30)

    def mostrar_pdv(self):
        self.limpar_container()
        TelaPDV(self.container, self)

    def mostrar_estoque(self):
        self.limpar_container()
        TelaEstoque(self.container, self)

    def mostrar_nfe(self):
        self.limpar_container()
        TelaNFe(self.container, self)

    def run(self):
        self.root.mainloop()
