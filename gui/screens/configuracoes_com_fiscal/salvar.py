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


def _salvar_pagamentos(self):
    modo_escolhido = self._valor("pix_modo_pagamento")
    ok, msg = salvar_modo_pagamento(modo_escolhido)
    if not ok:
        messagebox.showerror("Modo de pagamento", msg)
        return

    if modo_escolhido in ("automatico", "hibrido") and not gateway_configurado():
        aviso = (
            "Gateway nao configurado ainda. "
            if modo_escolhido == "automatico"
            else "Gateway nao configurado: ate configurar, o sistema usara sempre o Pix manual. "
        )
        messagebox.showwarning(
            "Modo de pagamento", aviso + "Valide a credencial do gateway acima."
        )

    if self.bool_vars["pix_ativo"].get():
        ok, msg = salvar_configuracao_pix(
            self._valor("pix_tipo"),
            self._valor("pix_chave"),
            self._valor("pix_banco"),
            self._valor("pix_nome"),
        )
        if not ok:
            messagebox.showerror("PIX", msg)
            return
        set_config("pix_tipo", self._valor("pix_tipo"))
    else:
        desativar_pix()
    set_config("cartao_status", "em_desenvolvimento")
    set_config(
        "cartao_manual_futuro",
        "True" if self.bool_vars["cartao_manual_futuro"].get() else "False",
    )
    messagebox.showinfo("Configuracoes", "Pagamentos salvos.")


def _salvar_fiscal(self):
    set_config("modo_fiscal", "simulado")
    for chave in ("fiscal_gerar_cupom_pdf", "fiscal_aviso_simulado"):
        set_config(chave, "True" if self.bool_vars[chave].get() else "False")
    messagebox.showinfo("Configuracoes", "Configuracao fiscal salva.")


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


def _salvar_painel_admin(self):
    for chave, var in self.bool_vars.items():
        if chave.startswith("admin_mod_"):
            set_config(chave, "True" if var.get() else "False")
    messagebox.showinfo("Configuracoes", "Painel admin salvo.")
