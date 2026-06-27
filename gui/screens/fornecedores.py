import tkinter as tk
from tkinter import ttk, messagebox

from core.fornecedores import (
    cadastrar_fornecedor,
    listar_fornecedores,
    atualizar_fornecedor,
    excluir_fornecedor,
)


class TelaFornecedores(tk.Frame):
    """Tela de cadastro e gestao de fornecedores."""

    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.pack(fill="both", expand=True, padx=12, pady=12)

        self.fornecedor_em_edicao_id: int | None = None

        self.configurar_layout()
        self.carregar_dados()

    def configurar_layout(self):
        topo = tk.Frame(self)
        topo.pack(fill="x", pady=(0, 10))
        tk.Label(
            topo,
            text="Fornecedores",
            font=("Arial", 18, "bold"),
        ).pack(side="left")
        tk.Button(
            topo,
            text="Voltar ao menu",
            command=self.controlador.mostrar_tela_principal,
            bg="#e0e0e0",
        ).pack(side="right")

        colunas = ("id", "cnpj", "nome", "email", "telefone")
        self.tree = ttk.Treeview(self, columns=colunas, show="headings", height=12)
        titulos = {
            "id": "ID",
            "cnpj": "CNPJ",
            "nome": "Razão Social",
            "email": "E-mail",
            "telefone": "Telefone",
        }
        larguras = {"id": 50, "cnpj": 150, "nome": 280, "email": 200, "telefone": 130}
        for col in colunas:
            self.tree.heading(col, text=titulos[col])
            self.tree.column(
                col,
                width=larguras[col],
                anchor="w" if col in ("nome", "email") else "center",
            )
        self.tree.pack(fill="both", expand=True, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar)

        acoes = tk.Frame(self)
        acoes.pack(fill="x", pady=(0, 16))
        tk.Button(acoes, text="Atualizar lista", command=self.carregar_dados).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(
            acoes,
            text="Excluir selecionado",
            command=self._excluir_selecionado,
            bg="#b00020",
            fg="white",
        ).pack(side="left")

        form = tk.LabelFrame(
            self, text="Cadastrar / Editar fornecedor", padx=12, pady=12
        )
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        tk.Label(form, text="CNPJ").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.entry_cnpj = tk.Entry(form, width=40)
        self.entry_cnpj.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        tk.Label(form, text="Razão Social").grid(
            row=1, column=0, sticky="w", padx=4, pady=4
        )
        self.entry_nome = tk.Entry(form, width=50)
        self.entry_nome.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        tk.Label(form, text="E-mail").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.entry_email = tk.Entry(form, width=50)
        self.entry_email.grid(row=2, column=1, sticky="ew", padx=4, pady=4)

        tk.Label(form, text="Telefone").grid(
            row=3, column=0, sticky="w", padx=4, pady=4
        )
        self.entry_telefone = tk.Entry(form, width=30)
        self.entry_telefone.grid(row=3, column=1, sticky="w", padx=4, pady=4)

        botoes_form = tk.Frame(form)
        botoes_form.grid(row=4, column=1, sticky="e", pady=(10, 0))
        self.btn_salvar = tk.Button(
            botoes_form,
            text="Cadastrar fornecedor",
            command=self._salvar,
            bg="#2e7d32",
            fg="white",
        )
        self.btn_salvar.pack(side="left", padx=(0, 8))
        tk.Button(
            botoes_form, text="Limpar formulário", command=self._limpar_form
        ).pack(side="left")

    def carregar_dados(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for f in listar_fornecedores():
            cnpj_fmt = self._formatar_cnpj_exibicao(f["cnpj"])
            self.tree.insert(
                "",
                "end",
                iid=str(f["id"]),
                values=(f["id"], cnpj_fmt, f["nome"], f["email"], f["telefone"]),
            )

    @staticmethod
    def _formatar_cnpj_exibicao(cnpj_digits: str) -> str:
        d = cnpj_digits
        if len(d) == 14:
            return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
        return cnpj_digits

    def _ao_selecionar(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        valores = self.tree.item(sel[0], "values")
        self.fornecedor_em_edicao_id = int(valores[0])
        self.entry_cnpj.delete(0, "end")
        self.entry_cnpj.insert(0, valores[1])
        self.entry_cnpj.config(state="disabled")  # CNPJ não é editável após cadastro
        self.entry_nome.delete(0, "end")
        self.entry_nome.insert(0, valores[2])
        self.entry_email.delete(0, "end")
        self.entry_email.insert(0, valores[3])
        self.entry_telefone.delete(0, "end")
        self.entry_telefone.insert(0, valores[4])
        self.btn_salvar.config(text="Salvar alterações")

    def _limpar_form(self):
        self.fornecedor_em_edicao_id = None
        self.entry_cnpj.config(state="normal")
        for entry in (
            self.entry_cnpj,
            self.entry_nome,
            self.entry_email,
            self.entry_telefone,
        ):
            entry.delete(0, "end")
        self.btn_salvar.config(text="Cadastrar fornecedor")
        self.tree.selection_remove(self.tree.selection())

    def _salvar(self):
        nome = self.entry_nome.get().strip()
        email = self.entry_email.get().strip()
        telefone = self.entry_telefone.get().strip()

        if self.fornecedor_em_edicao_id is None:
            cnpj = self.entry_cnpj.get().strip()
            ok, msg = cadastrar_fornecedor(cnpj, nome, email, telefone)
        else:
            ok, msg = atualizar_fornecedor(
                self.fornecedor_em_edicao_id, nome, email, telefone
            )

        if not ok:
            messagebox.showerror("Fornecedores", msg)
            return
        messagebox.showinfo("Fornecedores", msg)
        self._limpar_form()
        self.carregar_dados()

    def _excluir_selecionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Fornecedores", "Selecione um fornecedor na lista.")
            return
        fornecedor_id = int(sel[0])
        nome = self.tree.item(sel[0], "values")[2]
        if not messagebox.askyesno(
            "Confirmar exclusão",
            f"Excluir o fornecedor '{nome}'? Esta ação não pode ser desfeita.",
        ):
            return
        ok, msg = excluir_fornecedor(fornecedor_id)
        if not ok:
            messagebox.showerror("Fornecedores", msg)
            return
        messagebox.showinfo("Fornecedores", msg)
        self._limpar_form()
        self.carregar_dados()
