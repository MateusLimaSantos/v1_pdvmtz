import tkinter as tk
from tkinter import messagebox
from core.auth import autenticar
from core.state import state


class TelaLogin:
    def __init__(self, parent, on_success):
        self.parent = parent
        self.on_success = on_success

        frame = tk.Frame(self.parent)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="Acesso ao Sistema", font=("Arial", 18, "bold")).pack(
            pady=20
        )

        tk.Label(frame, text="Usuário:", font=("Arial", 12)).pack(anchor="w")
        self.entry_nome = tk.Entry(frame, font=("Arial", 12), width=30)
        self.entry_nome.pack(pady=5)

        tk.Label(frame, text="Senha:", font=("Arial", 12)).pack(anchor="w")
        self.entry_senha = tk.Entry(frame, show="*", font=("Arial", 12), width=30)
        self.entry_senha.pack(pady=5)

        tk.Button(
            frame,
            text="Entrar",
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            command=self.tentar_login,
        ).pack(pady=20, fill="x")

    def tentar_login(self):
        nome = self.entry_nome.get()
        senha = self.entry_senha.get()

        if not nome or not senha:
            messagebox.showwarning("Atenção", "Preencha usuário e senha.")
            return

        operador = autenticar(nome, senha)

        if operador:
            state.operador = operador
            self.on_success()
        else:
            messagebox.showerror(
                "Erro", "Usuário ou senha incorretos, ou operador inativo."
            )
