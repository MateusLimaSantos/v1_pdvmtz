def _campo(
    self,
    parent,
    label: str,
    chave: str,
    row: int,
    default: str = "",
    show: str | None = None,
):
    tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
    var = tk.StringVar(value=default)
    ent = tk.Entry(parent, textvariable=var, width=48, show=show)
    ent.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
    self.vars[chave] = var
    self._entries_por_chave[chave] = ent
    self._registrar_entry_na_aba(parent, ent)
    return ent


def _combo(
    self,
    parent,
    label: str,
    chave: str,
    row: int,
    values: tuple[str, ...],
    default: str,
):
    tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
    var = tk.StringVar(value=default)
    combo = ttk.Combobox(
        parent, textvariable=var, values=values, state="readonly", width=46
    )
    combo.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
    self.vars[chave] = var
    return combo


def _check(
    self,
    parent,
    label: str,
    chave: str,
    row: int,
    default: bool = False,
    state_opt: str = "normal",
):
    var = tk.BooleanVar(value=default)
    chk = tk.Checkbutton(parent, text=label, variable=var, state=state_opt)
    chk.grid(row=row, column=0, columnspan=3, sticky="w", padx=4, pady=4)
    self.bool_vars[chave] = var
    return chk


def _titulo(self, parent, texto: str, row: int):
    tk.Label(
        parent,
        text=texto,
        font=("Arial", 11, "bold"),
        fg="#333",
    ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(12, 6))


def _campo_pasta(self, parent, label: str, chave: str, row: int, default: str):
    self._campo(parent, label, chave, row, default=default)
    tk.Button(parent, text="Procurar", command=lambda: self._browse_dir(chave)).grid(
        row=row, column=2, sticky="w", padx=4
    )


def _browse_dir(self, chave: str):
    atual = self.vars[chave].get().strip() or BASE_DIR
    caminho = filedialog.askdirectory(initialdir=atual, title="Selecione uma pasta")
    if caminho:
        self.vars[chave].set(caminho)


def _cfg(self, chave: str, padrao: str = "") -> str:
    return get_config(chave, padrao) or ""


def _cfg_bool(self, chave: str, padrao: bool = False) -> bool:
    valor = get_config(chave)
    if valor is None:
        return padrao
    return valor == "True"


def _valor(self, chave: str) -> str:
    return self.vars[chave].get().strip()
