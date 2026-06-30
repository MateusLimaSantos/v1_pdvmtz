import tkinter as tk
from tkinter import ttk

from empresa import EmpresaTab
from fiscal import FiscalTab
from salvar import SalvarTab
from operadores import OperadoresTab

class TelaConfiguracoes(tk.Frame):

    def __init__(self, parent, controlador):
        super().__init__(parent)

        self.controlador = controlador

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        EmpresaTab(notebook, controlador)
        PagamentosTab(notebook, controlador)
        FiscalTab(notebook, controlador)
        PDVEstoqueTab(notebook, controlador)
        PDFBackupTab(notebook, controlador)
        PainelAdminTab(notebook, controlador)
        OperadoresTab(notebook, controlador)
