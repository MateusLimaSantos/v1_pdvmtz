import tkinter as tk
from tkinter import ttk, messagebox

class EmpresaTab(tk.Frame):
    def __int__(self, notebook, controlador):
        super().__init__(notebook)
        self.controlador = controlador
        
        notebook.add(self, text="Empresa")
        
        self._montar_empresa(self)
        

    def _montar_empresa(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo(aba, "Dados da empresa", 0)

        campos = [
            ("Razao social", "razao_social", "emit_razao_social"),
            ("Nome fantasia", "nome_fantasia", "emit_nome_fantasia"),
            ("CNPJ", "cnpj", "emit_cnpj"),
            ("Inscricao estadual", "ie", "emit_ie"),
            ("Telefone", "telefone", "emit_telefone"),
            ("CEP", "cep", "emit_cep"),
            ("Logradouro", "logradouro", "emit_logradouro"),
            ("Numero", "numero", "emit_numero"),
            ("Bairro", "bairro", "emit_bairro"),
            ("Municipio", "municipio", "emit_municipio"),
            ("UF", "uf", "emit_uf"),
            ("Regime/CRT", "regime", "emit_regime"),
        ]

        for i, (label, chave, cfg) in enumerate(campos, start=1):
            self._campo(aba, label, chave, i, self._cfg(cfg))

        tk.Button(
            aba,
            text="Salvar empresa",
            command=self._salvar_empresa,
            bg="#2e7d32",
            fg="white",
        ).grid(row=len(campos) + 1, column=1, sticky="e", pady=12)


    def _salvar_empresa(self):
        dados = {
            "razao_social": self._valor("razao_social"),
            "nome_fantasia": self._valor("nome_fantasia") or None,
            "cnpj": self._valor("cnpj"),
            "ie": self._valor("ie"),
            "telefone": self._valor("telefone"),
            "cep": self._valor("cep"),
            "logradouro": self._valor("logradouro"),
            "numero": self._valor("numero"),
            "bairro": self._valor("bairro"),
            "municipio": self._valor("municipio"),
            "uf": self._valor("uf"),
            "regime": self._valor("regime"),
        }

        ok, erros = salvar_dados_emitente(dados)

        if not ok:
            texto = "\n".join(f"- {e['campo']}: {e['mensagem']}" for e in erros)
            messagebox.showerror("Dados da empresa", texto)
            return

        messagebox.showinfo("Configuracoes", "Dados da empresa salvos.")
