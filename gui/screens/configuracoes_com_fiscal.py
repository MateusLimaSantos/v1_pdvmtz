import tkinter as tk
from tkinter import ttk

from core.state import state
from gui.screens.configuracoes_fiscal_tabs import (
    ConfiguracoesBaseMixin,
    EmpresaTabMixin,
    FiscalTabMixin,
    OperadoresTabMixin,
    PagamentosTabMixin,
    PainelAdminTabMixin,
    PDFBackupTabMixin,
    PDVEstoqueTabMixin,
)


class TelaConfiguracoes(
    tk.Frame,
    ConfiguracoesBaseMixin,
    EmpresaTabMixin,
    PagamentosTabMixin,
    FiscalTabMixin,
    PDVEstoqueTabMixin,
    PDFBackupTabMixin,
    PainelAdminTabMixin,
    OperadoresTabMixin,
):
    """Painel interno de configuracoes, visivel apenas para administradores."""

    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.vars: dict[str, tk.StringVar] = {}
        self.bool_vars: dict[str, tk.BooleanVar] = {}
        self._entries_por_aba: dict[int, list[tk.Entry]] = {}
        self._entries_por_chave: dict[str, tk.Entry] = {}
        self._frame_aba_atual = None
        self.pack(fill="both", expand=True, padx=12, pady=12)

        if not (state.operador and state.operador.get("perfil") == "admin"):
            self._sem_acesso()
            return

        self._montar()

    def _sem_acesso(self):
        frame = tk.Frame(self, bd=2, relief="groove")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=460, height=180)
        tk.Label(
            frame,
            text="Acesso restrito",
            font=("Arial", 16, "bold"),
            fg="#b00020",
        ).pack(pady=(28, 8))
        tk.Label(
            frame, text="Somente administradores podem acessar configuracoes."
        ).pack(pady=8)
        tk.Button(
            frame, text="Voltar", command=self.controlador.mostrar_tela_principal
        ).pack(pady=12)

    def _montar(self):
        topo = tk.Frame(self)
        topo.pack(fill="x", pady=(0, 10))
        tk.Label(
            topo,
            text="Configuracoes do sistema",
            font=("Arial", 18, "bold"),
        ).pack(side="left")
        tk.Button(
            topo,
            text="Voltar ao menu",
            command=self.controlador.mostrar_tela_principal,
            bg="#e0e0e0",
        ).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self._montar_empresa(self._aba_scroll(notebook, "Empresa"))
        self._montar_pagamentos(self._aba_scroll(notebook, "Pagamentos"))
        self._montar_fiscal(self._aba_scroll(notebook, "Fiscal"))
        self._montar_pdv_estoque(self._aba_scroll(notebook, "PDV/Estoque"))
        self._montar_pdf_backup(self._aba_scroll(notebook, "PDF/Backup"))
        self._montar_painel_admin(self._aba_scroll(notebook, "Painel Admin"))
        self._montar_operadores(self._aba_scroll(notebook, "Operadores"))

        self._notebook = notebook
        self._encadear_enters_por_aba()

        self._configurar_autocomplete_cep(
            entry_cep=self._entry_por_chave("cep"),
            campos_destino={
                "logradouro": self._entry_por_chave("logradouro"),
                "bairro": self._entry_por_chave("bairro"),
                "municipio": self._entry_por_chave("municipio"),
                "uf": self._entry_por_chave("uf"),
            },
        )
