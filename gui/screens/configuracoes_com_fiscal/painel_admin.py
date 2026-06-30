def _montar_painel_admin(self, aba):
    self._titulo(aba, "Modulos do painel interno", 0)
    checks = [
        ("Fornecedores", "admin_mod_fornecedores"),
        ("Operadores e permissoes", "admin_mod_operadores"),
        ("Historico de vendas e cupons/PDFs", "admin_mod_historico"),
        ("Relatorios: vendas por periodo e curva ABC", "admin_mod_relatorios"),
        ("Graficos de vendas mensal", "admin_mod_graficos"),
        ("Caixa: sangria, suprimento e fechamento", "admin_mod_caixa"),
        ("Auditoria de alteracoes", "admin_mod_auditoria"),
    ]
    for i, (label, chave) in enumerate(checks, start=1):
        self._check(aba, label, chave, i, self._cfg_bool(chave, True))
    tk.Button(
        aba,
        text="Salvar painel admin",
        command=self._salvar_painel_admin,
        bg="#2e7d32",
        fg="white",
    ).grid(row=len(checks) + 1, column=1, sticky="e", pady=12)


def _salvar_painel_admin(self):
    for chave, var in self.bool_vars.items():
        if chave.startswith("admin_mod_"):
            set_config(chave, "True" if var.get() else "False")
    messagebox.showinfo("Configuracoes", "Painel admin salvo.")
