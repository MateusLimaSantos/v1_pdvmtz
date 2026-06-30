import tkinter as tk
from tkinter import messagebox

from core.configuracoes import desativar_pix, salvar_configuracao_pix
from core.fiscal.pagamento import (
    gateway_configurado,
    obter_modo_pagamento as get_modo_pagamento,
    remover_credencial_gateway,
    salvar_credencial_gateway,
    salvar_modo_pagamento,
    token_mascarado_atual,
)
from core.helpers import set_config


class PagamentosTabMixin:
    def _montar_pagamentos(self, aba):
        aba.columnconfigure(1, weight=1)

        self._titulo(aba, "Modo de recebimento PIX", 0)
        tk.Label(
            aba,
            text=(
                "Manual: gera um QR Code fixo na tela; o caixa confere o recebimento no app do banco "
                "e confirma manualmente. Funciona sempre, sem custo, sem internet.\n\n"
                "Automatico: usa um gateway de pagamento para gerar um QR Code exclusivo por venda, "
                "com baixa automatica quando o cliente paga. Sujeito a taxas e depende de internet.\n\n"
                "Hibrido: tenta o modo automatico primeiro; se o gateway falhar, usa Pix manual "
                "na mesma venda automaticamente, sem travar o caixa."
            ),
            fg="#555",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        self._combo(
            aba,
            "Modo de recebimento",
            "pix_modo_pagamento",
            2,
            ("manual", "automatico", "hibrido"),
            get_modo_pagamento(),
        )

        self._titulo(aba, "Pix estatico (manual / contingencia do hibrido)", 3)
        self._check(
            aba, "Ativar PIX manual", "pix_ativo", 4, self._cfg_bool("pix_ativo")
        )
        self._combo(
            aba,
            "Tipo da chave PIX",
            "pix_tipo",
            5,
            ("1", "2", "3", "4", "5"),
            self._cfg("pix_tipo", "4"),
        )
        self._campo(aba, "Chave PIX", "pix_chave", 6, self._cfg("pix_chave"))
        self._campo(aba, "Banco/instituicao", "pix_banco", 7, self._cfg("pix_banco"))
        self._campo(aba, "Nome do titular", "pix_nome", 8, self._cfg("pix_nome"))

        self._titulo(aba, "Gateway de pagamento (modo automatico / hibrido)", 9)
        status_gateway = "Configurado" if gateway_configurado() else "Nao configurado"
        cor_status = "#2e7d32" if gateway_configurado() else "#b00020"
        self.lbl_status_gateway = tk.Label(
            aba,
            text=f"Status: {status_gateway}",
            fg=cor_status,
            font=("Arial", 10, "bold"),
        )
        self.lbl_status_gateway.grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        if gateway_configurado():
            tk.Label(
                aba, text=f"Token atual: {token_mascarado_atual()}", fg="#555"
            ).grid(row=11, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self._campo(
            aba, "Access Token do gateway", "pix_gateway_access_token", 12, show="*"
        )
        frame_botoes_gateway = tk.Frame(aba)
        frame_botoes_gateway.grid(row=13, column=1, sticky="w", pady=(0, 10))
        tk.Button(
            frame_botoes_gateway,
            text="Validar e salvar credencial",
            command=self._salvar_credencial_gateway,
            bg="#1976D2",
            fg="white",
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            frame_botoes_gateway,
            text="Remover credencial",
            command=self._remover_credencial_gateway,
            bg="#b00020",
            fg="white",
        ).pack(side="left")

        self._titulo(aba, "Cartao / maquininha", 14)
        self._check(
            aba,
            "Cartao integrado ao sistema (em desenvolvimento)",
            "cartao_integrado_em_desenvolvimento",
            15,
            False,
            "disabled",
        )
        self._check(
            aba,
            "Permitir registro manual de cartao no futuro",
            "cartao_manual_futuro",
            16,
            self._cfg_bool("cartao_manual_futuro", True),
        )
        tk.Label(
            aba,
            text="Por enquanto a maquininha fica fora do sistema; a confirmacao sera manual quando liberarmos essa tela.",
            fg="#8a5a00",
            wraplength=760,
            justify="left",
        ).grid(row=17, column=0, columnspan=3, sticky="w", pady=8)
        tk.Button(
            aba,
            text="Salvar pagamentos",
            command=self._salvar_pagamentos,
            bg="#2e7d32",
            fg="white",
        ).grid(row=18, column=1, sticky="e", pady=12)

    def _salvar_credencial_gateway(self):
        token = self.vars["pix_gateway_access_token"].get().strip()
        if not token:
            messagebox.showwarning(
                "Gateway PIX", "Informe o Access Token antes de validar."
            )
            return
        try:
            self.config(cursor="watch")
        except tk.TclError:
            pass
        self.update_idletasks()
        try:
            ok, msg = salvar_credencial_gateway(token, testar=True)
        finally:
            try:
                self.config(cursor="")
            except tk.TclError:
                pass
        if not ok:
            messagebox.showerror("Gateway PIX", msg)
            return
        messagebox.showinfo("Gateway PIX", msg)
        self.vars["pix_gateway_access_token"].set("")
        self.lbl_status_gateway.config(text="Status: Configurado", fg="#2e7d32")

    def _remover_credencial_gateway(self):
        if not messagebox.askyesno(
            "Gateway PIX", "Remover a credencial do gateway configurada?"
        ):
            return
        remover_credencial_gateway()
        messagebox.showinfo("Gateway PIX", "Credencial removida.")
        self.lbl_status_gateway.config(text="Status: Nao configurado", fg="#b00020")

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
