def _montar_pdf_backup(self, aba):
    aba.columnconfigure(1, weight=1)
    self._titulo(aba, "PDF", 0)
    self._campo_pasta(
        aba,
        "Pasta de PDFs/relatorios",
        "reports_dir",
        1,
        self._cfg("reports_dir", REPORTS_DIR),
    )
    self._check(
        aba,
        "Gerar PDF automaticamente",
        "impressao_gerar_pdf",
        2,
        self._cfg_bool("impressao_gerar_pdf", True),
    )
    self._check(
        aba,
        "Abrir PDF automaticamente",
        "impressao_abrir_pdf",
        3,
        self._cfg_bool("impressao_abrir_pdf", False),
    )
    self._check(
        aba,
        "Imprimir automaticamente (em desenvolvimento)",
        "impressao_auto_em_desenvolvimento",
        4,
        False,
        "disabled",
    )

    self._titulo(aba, "Backup", 5)
    self._campo_pasta(
        aba,
        "Pasta de backups",
        "backup_dir",
        6,
        self._cfg("backup_dir", os.path.join(BASE_DIR, "backups")),
    )
    self._combo(
        aba,
        "Periodicidade",
        "backup_periodicidade",
        7,
        ("manual", "diario", "semanal"),
        self._cfg("backup_periodicidade", "diario"),
    )
    self._campo(
        aba,
        "Manter backups por quantos dias",
        "backup_manter_dias",
        8,
        self._cfg("backup_manter_dias", "30"),
    )
    self._check(
        aba,
        "Backup ao fechar o sistema (futuro)",
        "backup_ao_fechar",
        9,
        self._cfg_bool("backup_ao_fechar", True),
    )
    tk.Button(
        aba,
        text="Salvar PDF/Backup",
        command=self._salvar_pdf_backup,
        bg="#2e7d32",
        fg="white",
    ).grid(row=10, column=1, sticky="e", pady=12)


def _salvar_pdf_backup(self):
    try:
        manter = int(self._valor("backup_manter_dias"))
    except ValueError:
        messagebox.showerror("Backup", "Dias de retencao deve ser numero inteiro.")
        return
    if not (1 <= manter <= 3650):
        messagebox.showerror("Backup", "Dias de retencao deve ficar entre 1 e 3650.")
        return
    for chave in (
        "reports_dir",
        "backup_dir",
        "backup_periodicidade",
        "backup_manter_dias",
    ):
        set_config(chave, self._valor(chave))
    for chave in ("impressao_gerar_pdf", "impressao_abrir_pdf", "backup_ao_fechar"):
        set_config(chave, "True" if self.bool_vars[chave].get() else "False")
    os.makedirs(self._valor("reports_dir"), exist_ok=True)
    os.makedirs(self._valor("backup_dir"), exist_ok=True)
    messagebox.showinfo("Configuracoes", "PDF/Backup salvo.")
