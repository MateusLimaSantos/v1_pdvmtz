def _montar_pdv_estoque(self, aba):
    self._titulo(aba, "Comportamento do PDV", 0)
    self._check(
        aba,
        "Abrir o PDV logo apos login",
        "pdv_abrir_apos_login",
        1,
        self._cfg_bool("pdv_abrir_apos_login", True),
    )
    self._check(
        aba,
        "Bloquear venda sem produtos cadastrados",
        "pdv_bloquear_sem_produtos",
        2,
        self._cfg_bool("pdv_bloquear_sem_produtos", True),
    )
    self._check(
        aba,
        "Confirmar pagamento antes de finalizar",
        "pdv_confirmar_pagamento",
        3,
        self._cfg_bool("pdv_confirmar_pagamento", True),
    )
    self._check(
        aba,
        "Perguntar se cliente quer impressao/PDF",
        "pdv_perguntar_impressao",
        4,
        self._cfg_bool("pdv_perguntar_impressao", True),
    )
    self._check(
        aba,
        "Ativar atalhos F1-F12 e teclado numerico",
        "pdv_atalhos_ativos",
        5,
        self._cfg_bool("pdv_atalhos_ativos", True),
    )

    self._titulo(aba, "Estoque e unidades", 6)
    self._check(
        aba,
        "Bloquear estoque negativo",
        "estoque_bloquear_negativo",
        7,
        self._cfg_bool("estoque_bloquear_negativo", True),
    )
    self._check(
        aba,
        "Permitir embalagens/fardos por produto base",
        "estoque_embalagens_ativas",
        8,
        self._cfg_bool("estoque_embalagens_ativas", True),
    )
    self._check(
        aba,
        "Permitir entrada manual",
        "estoque_entrada_manual",
        9,
        self._cfg_bool("estoque_entrada_manual", True),
    )
    self._check(
        aba,
        "Permitir importacao XML de compra",
        "estoque_importar_xml",
        10,
        self._cfg_bool("estoque_importar_xml", True),
    )
    self._campo(
        aba,
        "Unidades ativas",
        "estoque_unidades_ativas",
        11,
        self._cfg("estoque_unidades_ativas", ",".join(TIPOS_UNIDADE_VALIDOS)),
    )
    tk.Button(
        aba,
        text="Salvar PDV/Estoque",
        command=self._salvar_pdv_estoque,
        bg="#2e7d32",
        fg="white",
    ).grid(row=12, column=1, sticky="e", pady=12)


def _salvar_pdv_estoque(self):
    unidades = [
        u.strip()
        for u in self._valor("estoque_unidades_ativas").split(",")
        if u.strip()
    ]
    invalidas = [u for u in unidades if u not in TIPOS_UNIDADE_VALIDOS]
    if invalidas or "unidade" not in unidades:
        messagebox.showerror(
            "Unidades",
            "Use apenas unidades validas e inclua 'unidade'.\nValidas: "
            + ", ".join(TIPOS_UNIDADE_VALIDOS),
        )
        return
    set_config("estoque_unidades_ativas", ",".join(unidades))
    for chave in (
        "pdv_abrir_apos_login",
        "pdv_bloquear_sem_produtos",
        "pdv_confirmar_pagamento",
        "pdv_perguntar_impressao",
        "pdv_atalhos_ativos",
        "estoque_bloquear_negativo",
        "estoque_embalagens_ativas",
        "estoque_entrada_manual",
        "estoque_importar_xml",
    ):
        set_config(chave, "True" if self.bool_vars[chave].get() else "False")
    messagebox.showinfo("Configuracoes", "PDV/Estoque salvo.")
