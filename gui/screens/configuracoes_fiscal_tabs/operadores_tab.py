import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from core.operadores import (
    cadastrar_operador,
    desativar_operador,
    listar_operadores,
    reativar_operador,
    redefinir_senha,
)


class OperadoresTabMixin:
    def _montar_operadores(self, aba):
        aba.columnconfigure(0, weight=1)

        tk.Label(
            aba,
            text="Operadores cadastrados",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(10, 6))

        colunas = ("id", "nome", "perfil", "status")
        self.tree_operadores = ttk.Treeview(
            aba, columns=colunas, show="headings", height=8
        )
        self.tree_operadores.heading("id", text="ID")
        self.tree_operadores.heading("nome", text="Nome")
        self.tree_operadores.heading("perfil", text="Perfil")
        self.tree_operadores.heading("status", text="Status")
        self.tree_operadores.column("id", width=50, anchor="center")
        self.tree_operadores.column("nome", width=260, anchor="w")
        self.tree_operadores.column("perfil", width=120, anchor="center")
        self.tree_operadores.column("status", width=120, anchor="center")
        self.tree_operadores.grid(row=1, column=0, columnspan=3, sticky="ew", pady=6)

        frame_acoes = tk.Frame(aba)
        frame_acoes.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 16))
        tk.Button(
            frame_acoes,
            text="Atualizar lista",
            command=self._carregar_operadores,
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            frame_acoes,
            text="Redefinir senha do selecionado",
            command=self._redefinir_senha_operador_selecionado,
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            frame_acoes,
            text="Ativar/Desativar selecionado",
            command=self._alternar_status_operador_selecionado,
        ).pack(side="left")

        self._titulo(aba, "Cadastrar novo operador", 3)
        self._campo(aba, "Nome", "novo_op_nome", 4)
        self._campo(aba, "Senha (min. 4 caracteres)", "novo_op_senha", 5, show="*")
        self._combo(
            aba, "Perfil", "novo_op_perfil", 6, ("operador", "admin"), "operador"
        )
        tk.Button(
            aba,
            text="Cadastrar operador",
            command=self._cadastrar_operador,
            bg="#2e7d32",
            fg="white",
        ).grid(row=7, column=1, sticky="e", pady=12)

        self._carregar_operadores()

    def _carregar_operadores(self):
        for row in self.tree_operadores.get_children():
            self.tree_operadores.delete(row)
        for op in listar_operadores():
            status = "Ativo" if op["ativo"] else "Inativo"
            self.tree_operadores.insert(
                "",
                "end",
                iid=str(op["id"]),
                values=(op["id"], op["nome"], op["perfil"], status),
            )

    def _operador_selecionado_id(self) -> int | None:
        sel = self.tree_operadores.selection()
        if not sel:
            messagebox.showwarning("Operadores", "Selecione um operador na lista.")
            return None
        return int(sel[0])

    def _cadastrar_operador(self):
        nome = self._valor("novo_op_nome")
        senha = self._valor("novo_op_senha")
        perfil = self._valor("novo_op_perfil")
        ok, msg = cadastrar_operador(nome, senha, perfil)
        if not ok:
            messagebox.showerror("Operadores", msg)
            return
        self.vars["novo_op_nome"].set("")
        self.vars["novo_op_senha"].set("")
        messagebox.showinfo("Operadores", msg)
        self._carregar_operadores()

    def _redefinir_senha_operador_selecionado(self):
        op_id = self._operador_selecionado_id()
        if op_id is None:
            return
        nova_senha = simpledialog.askstring(
            "Redefinir senha", "Nova senha (min. 4 caracteres):", show="*", parent=self
        )
        if not nova_senha:
            return
        ok, msg = redefinir_senha(op_id, nova_senha)
        if not ok:
            messagebox.showerror("Operadores", msg)
            return
        messagebox.showinfo("Operadores", msg)

    def _alternar_status_operador_selecionado(self):
        op_id = self._operador_selecionado_id()
        if op_id is None:
            return
        valores = self.tree_operadores.item(str(op_id), "values")
        status_atual = valores[3]
        if status_atual == "Ativo":
            ok, msg = desativar_operador(op_id)
        else:
            ok, msg = reativar_operador(op_id)
        if not ok:
            messagebox.showerror("Operadores", msg)
            return
        messagebox.showinfo("Operadores", msg)
        self._carregar_operadores()
