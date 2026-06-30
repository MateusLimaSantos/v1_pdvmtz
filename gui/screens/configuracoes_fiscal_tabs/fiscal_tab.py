import tkinter as tk
from tkinter import filedialog, messagebox

from core.fiscal.fiscal_config import (
    obter_ambiente_ativo,
    remover_certificado_a1,
    salvar_ambiente_ativo,
    salvar_certificado_a1,
    salvar_csc,
    status_emissao_real,
)
from core.helpers import set_config


class FiscalTabMixin:
    def _montar_fiscal(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo(aba, "Documento fiscal", 0)
        self._combo(
            aba,
            "Modo de emissao",
            "modo_fiscal",
            1,
            ("simulado",),
            self._cfg("modo_fiscal", "simulado"),
        )
        self._check(
            aba,
            "Gerar cupom/PDF interno apos venda",
            "fiscal_gerar_cupom_pdf",
            2,
            self._cfg_bool("fiscal_gerar_cupom_pdf", True),
        )
        self._check(
            aba,
            "Exibir aviso de documento nao fiscal",
            "fiscal_aviso_simulado",
            3,
            self._cfg_bool("fiscal_aviso_simulado", True),
        )
        tk.Label(
            aba,
            text="NFC-e/SAT real ainda nao esta implementado. O modo atual gera cupom interno nao fiscal/simulado.",
            fg="#8a0000",
            wraplength=760,
            justify="left",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=8)
        tk.Button(
            aba,
            text="Salvar fiscal",
            command=self._salvar_fiscal,
            bg="#2e7d32",
            fg="white",
        ).grid(row=5, column=1, sticky="e", pady=12)

        self._titulo(aba, "Preparacao para emissao real de NFC-e", 6)
        tk.Label(
            aba,
            text=(
                "Esta secao guarda credenciais para futura emissao fiscal real. "
                "Preencher aqui nao ativa emissao fiscal agora.\n\n"
                "Antes de preencher, providencie fora do sistema: inscricao estadual ativa, "
                "certificado digital e-CNPJ A1 (.pfx), credenciamento NFC-e no portal da SEFAZ "
                "do seu estado e CSC gerado no mesmo portal."
            ),
            fg="#555",
            wraplength=760,
            justify="left",
        ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 10))

        self.lbl_status_certificado = tk.Label(
            aba, text=self._texto_status_certificado(), justify="left"
        )
        self.lbl_status_certificado.grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        tk.Label(aba, text="Arquivo do certificado (.pfx/.p12)").grid(
            row=9, column=0, sticky="w", padx=4, pady=4
        )
        self.entry_certificado_path = tk.Entry(aba, width=40)
        self.entry_certificado_path.grid(row=9, column=1, sticky="ew", padx=4, pady=4)
        tk.Button(aba, text="Procurar", command=self._procurar_certificado).grid(
            row=9, column=2, sticky="w", padx=4
        )

        tk.Label(aba, text="Senha do certificado").grid(
            row=10, column=0, sticky="w", padx=4, pady=4
        )
        self.entry_certificado_senha = tk.Entry(aba, width=40, show="*")
        self.entry_certificado_senha.grid(row=10, column=1, sticky="ew", padx=4, pady=4)

        frame_botoes_cert = tk.Frame(aba)
        frame_botoes_cert.grid(row=11, column=1, sticky="w", pady=(4, 14))
        tk.Button(
            frame_botoes_cert,
            text="Validar e salvar certificado",
            command=self._salvar_certificado_fiscal,
            bg="#1976D2",
            fg="white",
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            frame_botoes_cert,
            text="Remover certificado",
            command=self._remover_certificado_fiscal,
            bg="#b00020",
            fg="white",
        ).pack(side="left")

        self._titulo(aba, "CSC - Codigo de Seguranca do Contribuinte", 12)
        self._combo(
            aba,
            "Ambiente ativo",
            "fiscal_ambiente_ativo",
            13,
            ("homologacao", "producao"),
            obter_ambiente_ativo(),
        )
        self._campo(
            aba, "CSC (ambiente selecionado acima)", "fiscal_csc_valor", 14, show="*"
        )
        self._campo(aba, "ID do token do CSC", "fiscal_csc_id_valor", 15)
        tk.Button(
            aba,
            text="Validar e salvar CSC",
            command=self._salvar_csc_fiscal,
            bg="#1976D2",
            fg="white",
        ).grid(row=16, column=1, sticky="w", pady=(4, 14))

    def _texto_status_certificado(self) -> str:
        status = status_emissao_real()
        if status["info_certificado"] is None:
            return "Status: nenhum certificado configurado ainda."
        info = status["info_certificado"]
        if info["vencido"]:
            return f"Status: certificado VENCIDO em {info['validade']}. E necessario renovar."
        aviso = (
            f" (vence em {info['dias_restantes']} dia(s); considere renovar)"
            if info["vence_em_breve"]
            else ""
        )
        return f"Status: certificado valido ate {info['validade']}{aviso}. Titular: {info['titular']}"

    def _procurar_certificado(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o certificado digital",
            filetypes=[
                ("Certificado digital", "*.pfx *.p12"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if caminho:
            self.entry_certificado_path.delete(0, tk.END)
            self.entry_certificado_path.insert(0, caminho)

    def _salvar_certificado_fiscal(self):
        caminho = self.entry_certificado_path.get().strip()
        senha = self.entry_certificado_senha.get()
        if not caminho:
            messagebox.showwarning(
                "Certificado fiscal", "Selecione o arquivo do certificado."
            )
            return
        try:
            self.config(cursor="watch")
        except tk.TclError:
            pass
        self.update_idletasks()
        try:
            ok, msg = salvar_certificado_a1(caminho, senha)
        finally:
            try:
                self.config(cursor="")
            except tk.TclError:
                pass
        if not ok:
            messagebox.showerror("Certificado fiscal", msg)
            return
        messagebox.showinfo("Certificado fiscal", msg)
        self.entry_certificado_senha.delete(0, tk.END)
        self.lbl_status_certificado.config(text=self._texto_status_certificado())

    def _remover_certificado_fiscal(self):
        if not messagebox.askyesno(
            "Certificado fiscal", "Remover o certificado digital configurado?"
        ):
            return
        remover_certificado_a1()
        messagebox.showinfo("Certificado fiscal", "Certificado removido.")
        self.lbl_status_certificado.config(text=self._texto_status_certificado())

    def _salvar_csc_fiscal(self):
        ambiente = self._valor("fiscal_ambiente_ativo")
        csc = self.vars["fiscal_csc_valor"].get()
        id_token = self._valor("fiscal_csc_id_valor")

        ok, msg = salvar_ambiente_ativo(ambiente)
        if not ok:
            messagebox.showerror("CSC fiscal", msg)
            return

        ok, msg = salvar_csc(ambiente, csc, id_token)
        if not ok:
            messagebox.showerror("CSC fiscal", msg)
            return
        messagebox.showinfo("CSC fiscal", msg)
        self.vars["fiscal_csc_valor"].set("")

    def _salvar_fiscal(self):
        set_config("modo_fiscal", "simulado")
        for chave in ("fiscal_gerar_cupom_pdf", "fiscal_aviso_simulado"):
            set_config(chave, "True" if self.bool_vars[chave].get() else "False")
        messagebox.showinfo("Configuracoes", "Configuracao fiscal salva.")
