import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from config import BASE_DIR, REPORTS_DIR, TIPOS_UNIDADE_VALIDOS
from core.configuracoes import (
    salvar_dados_emitente,
    salvar_configuracao_pix,
    desativar_pix,
)
from core.helpers import get_config, set_config
from core.state import state
from core.operadores import (
    cadastrar_operador,
    listar_operadores,
    redefinir_senha,
    desativar_operador,
    reativar_operador,
)
from core.fiscal.pagamento import (
    obter_modo_pagamento as get_modo_pagamento,
    salvar_modo_pagamento,
    salvar_credencial_gateway,
    remover_credencial_gateway,
    gateway_configurado,
    token_mascarado_atual,
)
from core.fiscal.fiscal_config import (
    salvar_certificado_a1,
    remover_certificado_a1,
    salvar_csc,
    obter_ambiente_ativo,
    salvar_ambiente_ativo,
    status_emissao_real,
)


class TelaConfiguracoes(tk.Frame):
    """Painel interno de configuracoes, visivel apenas para administradores."""

    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.vars: dict[str, tk.StringVar] = {}
        self.bool_vars: dict[str, tk.BooleanVar] = {}
        self._entries_por_aba: dict[int, list[tk.Entry]] = {}
        self._entries_por_chave: dict[str, tk.Entry] = {}
        self._frame_aba_atual = None
        self.pack(fill="both", expand=True, padx=12, pady=12)

        if not (state.operador and state.operador.get("perfil") == "admin"):
            self._sem_acesso()
            return

        self._montar()

    def _sem_acesso(self):
        frame = tk.Frame(self, bd=2, relief="groove")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=460, height=180)
        tk.Label(
            frame,
            text="Acesso restrito",
            font=("Arial", 16, "bold"),
            fg="#b00020",
        ).pack(pady=(28, 8))
        tk.Label(
            frame, text="Somente administradores podem acessar configuracoes."
        ).pack(pady=8)
        tk.Button(
            frame, text="Voltar", command=self.controlador.mostrar_tela_principal
        ).pack(pady=12)

    def _aba_scroll(self, notebook: ttk.Notebook, titulo: str) -> tk.Frame:
        outer = tk.Frame(notebook)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, padx=14, pady=14)

        frame.bind(
            "<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        notebook.add(outer, text=titulo)
        self._entries_por_aba[id(frame)] = []
        self._frame_aba_atual = frame
        return frame

    def _titulo(self, parent, texto: str, row: int):
        tk.Label(
            parent,
            text=texto,
            font=("Arial", 11, "bold"),
            fg="#333",
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(12, 6))

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

    def _registrar_entry_na_aba(self, parent, entry: tk.Entry):
        chave_aba = id(parent)
        if chave_aba not in self._entries_por_aba:
            chave_aba = id(self._frame_aba_atual)
        self._entries_por_aba.setdefault(chave_aba, []).append(entry)

    def _entry_por_chave(self, chave: str) -> tk.Entry | None:
        return self._entries_por_chave.get(chave)

    def _configurar_autocomplete_cep(
        self, entry_cep: tk.Entry | None, campos_destino: dict[str, tk.Entry | None]
    ):
        """
        Ao sair do campo CEP (perder o foco) ou apertar Enter nele,
        consulta o endereço numa thread separada (para não congelar a
        janela enquanto espera a rede) e preenche automaticamente
        logradouro/bairro/município/UF. Nunca sobrescreve o que o
        usuário já tiver digitado manualmente — só preenche campos
        vazios. O número nunca é preenchido automaticamente.
        """
        import re
        import threading

        if entry_cep is None:
            return

        def disparar_busca(_event=None):
            cep_texto = entry_cep.get().strip()
            cep_limpo = re.sub(r"\D", "", cep_texto)
            if len(cep_limpo) != 8:
                return

            def buscar_em_thread():
                from core.helpers import buscar_endereco_por_cep

                resultado = buscar_endereco_por_cep(cep_limpo)
                self.winfo_toplevel().after(0, lambda: aplicar_resultado(resultado))

            def aplicar_resultado(resultado: dict | None):
                if not resultado:
                    return
                mapa = {
                    "logradouro": resultado.get("logradouro", ""),
                    "bairro": resultado.get("bairro", ""),
                    "municipio": resultado.get("cidade", ""),
                    "uf": resultado.get("uf", ""),
                }
                for chave, valor in mapa.items():
                    campo = campos_destino.get(chave)
                    if campo is None or not valor:
                        continue
                    if not campo.get().strip():
                        campo.delete(0, tk.END)
                        campo.insert(0, valor)

            threading.Thread(target=buscar_em_thread, daemon=True).start()

        entry_cep.bind("<FocusOut>", disparar_busca)
        entry_cep.bind("<Return>", lambda e: disparar_busca(), add="+")

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

    def _campo_pasta(self, parent, label: str, chave: str, row: int, default: str):
        self._campo(parent, label, chave, row, default=default)
        tk.Button(
            parent, text="Procurar", command=lambda: self._browse_dir(chave)
        ).grid(row=row, column=2, sticky="w", padx=4)

    def _browse_dir(self, chave: str):
        atual = self.vars[chave].get().strip() or BASE_DIR
        caminho = filedialog.askdirectory(initialdir=atual, title="Selecione uma pasta")
        if caminho:
            self.vars[chave].set(caminho)

    def _encadear_enters_por_aba(self):
        """
        Enter avança para o próximo campo de texto dentro da mesma
        aba (ordenado pela linha do grid). No último campo de uma
        aba, Enter pula para a primeira aba seguinte que tiver algum
        campo navegável. Na última aba, Enter não tem mais para onde
        ir — fica com o comportamento padrão (sem ação especial),
        já que aqui cada aba tem seu próprio botão "Salvar", não um
        botão único de salvar geral como no assistente inicial.
        Campos desabilitados são pulados.
        """
        abas_ids_em_ordem = list(self._entries_por_aba.keys())

        listas_ordenadas: list[list[tk.Entry]] = []
        for chave_aba in abas_ids_em_ordem:
            entries = self._entries_por_aba[chave_aba]
            entries_validos = [e for e in entries if str(e.cget("state")) != "disabled"]
            entries_ordenados = sorted(
                entries_validos, key=lambda e: e.grid_info().get("row", 0)
            )
            listas_ordenadas.append(entries_ordenados)

        for i, entries_aba in enumerate(listas_ordenadas):
            for pos, entry in enumerate(entries_aba):
                if pos + 1 < len(entries_aba):
                    proximo = entries_aba[pos + 1]
                    entry.bind(
                        "<Return>", lambda e, prox=proximo: (prox.focus_set(), "break")
                    )
                else:
                    proxima_aba_com_campos = None
                    for j in range(i + 1, len(listas_ordenadas)):
                        if listas_ordenadas[j]:
                            proxima_aba_com_campos = (j, listas_ordenadas[j][0])
                            break
                    if proxima_aba_com_campos:
                        idx_aba, primeiro_campo = proxima_aba_com_campos
                        entry.bind(
                            "<Return>",
                            lambda e, idx=idx_aba, campo=primeiro_campo: self._ir_para_aba_e_focar(
                                idx, campo
                            ),
                        )
                    # última aba, último campo: sem bind especial — comportamento padrão do Tk

    def _ir_para_aba_e_focar(self, indice_aba: int, campo: tk.Entry):
        self._notebook.select(indice_aba)
        campo.focus_set()
        return "break"

    def _cfg(self, chave: str, padrao: str = "") -> str:
        return get_config(chave, padrao) or ""

    def _cfg_bool(self, chave: str, padrao: bool = False) -> bool:
        valor = get_config(chave)
        if valor is None:
            return padrao
        return valor == "True"

    def _montar(self):
        topo = tk.Frame(self)
        topo.pack(fill="x", pady=(0, 10))
        tk.Label(
            topo,
            text="Configuracoes do sistema",
            font=("Arial", 18, "bold"),
        ).pack(side="left")
        tk.Button(
            topo,
            text="Voltar ao menu",
            command=self.controlador.mostrar_tela_principal,
            bg="#e0e0e0",
        ).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self._montar_empresa(self._aba_scroll(notebook, "Empresa"))
        self._montar_pagamentos(self._aba_scroll(notebook, "Pagamentos"))
        self._montar_fiscal(self._aba_scroll(notebook, "Fiscal"))
        self._montar_pdv_estoque(self._aba_scroll(notebook, "PDV/Estoque"))
        self._montar_pdf_backup(self._aba_scroll(notebook, "PDF/Backup"))
        self._montar_painel_admin(self._aba_scroll(notebook, "Painel Admin"))
        self._montar_operadores(self._aba_scroll(notebook, "Operadores"))

        self._notebook = notebook
        self._encadear_enters_por_aba()

        self._configurar_autocomplete_cep(
            entry_cep=self._entry_por_chave("cep"),
            campos_destino={
                "logradouro": self._entry_por_chave("logradouro"),
                "bairro": self._entry_por_chave("bairro"),
                "municipio": self._entry_por_chave("municipio"),
                "uf": self._entry_por_chave("uf"),
            },
        )

    def _montar_empresa(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo(aba, "Dados da empresa", 0)
        campos = [
            ("Razao social", "razao_social", "emit_razao_social"),
            ("Nome fantasia", "nome_fantasia", "emit_nome_fantasia"),
            ("CNPJ", "cnpj", "emit_cnpj"),
            ("Inscricao estadual", "ie", "emit_ie"),
            ("Telefone", "telefone", "emit_telefone"),
            ("CEP", "cep", "emit_cep"),
            ("Logradouro", "logradouro", "emit_logradouro"),
            ("Numero", "numero", "emit_numero"),
            ("Bairro", "bairro", "emit_bairro"),
            ("Municipio", "municipio", "emit_municipio"),
            ("UF", "uf", "emit_uf"),
            ("Regime/CRT", "regime", "emit_regime"),
        ]
        for i, (label, chave, cfg) in enumerate(campos, start=1):
            self._campo(aba, label, chave, i, self._cfg(cfg))
        tk.Button(
            aba,
            text="Salvar empresa",
            command=self._salvar_empresa,
            bg="#2e7d32",
            fg="white",
        ).grid(row=len(campos) + 1, column=1, sticky="e", pady=12)

    def _montar_pagamentos(self, aba):
        aba.columnconfigure(1, weight=1)

        self._titulo(aba, "Modo de recebimento PIX", 0)
        tk.Label(
            aba,
            text=(
                "Manual: gera um QR Code fixo na tela; o caixa confere o recebimento no app do banco "
                "e confirma manualmente. Funciona sempre, sem custo, sem internet.\n\n"
                "Automático: usa um gateway de pagamento (ex: Mercado Pago) para gerar um QR Code "
                "exclusivo por venda, com baixa automática quando o cliente paga. Sujeito às taxas "
                "do gateway e depende de internet.\n\n"
                "Híbrido (recomendado): tenta o modo automático primeiro; se o gateway falhar ou "
                "não responder a tempo, usa o Pix manual na mesma venda automaticamente, sem travar o caixa."
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

        self._titulo(aba, "Pix estático (manual / contingência do híbrido)", 3)
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

        self._titulo(aba, "Gateway de pagamento (modo automático / híbrido)", 9)
        status_gateway = "Configurado ✓" if gateway_configurado() else "Não configurado"
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
            pass  # alguns SOs/temas não suportam esse nome de cursor; segue sem feedback visual de espera
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
        self.lbl_status_gateway.config(text="Status: Configurado ✓", fg="#2e7d32")

    def _remover_credencial_gateway(self):
        if not messagebox.askyesno(
            "Gateway PIX", "Remover a credencial do gateway configurada?"
        ):
            return
        remover_credencial_gateway()
        messagebox.showinfo("Gateway PIX", "Credencial removida.")
        self.lbl_status_gateway.config(text="Status: Não configurado", fg="#b00020")

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

        self._titulo(aba, "Preparação para emissão real de NFC-e (avançado)", 6)
        tk.Label(
            aba,
            text=(
                "Esta seção guarda, de forma cifrada, as credenciais que serão necessárias quando a "
                "emissão fiscal real for implementada. Preencher aqui NÃO ativa emissão fiscal agora.\n\n"
                "Antes de preencher, você precisa ter providenciado, fora do sistema:\n"
                "1) Inscrição Estadual ativa  2) Certificado digital e-CNPJ modelo A1 (.pfx)  "
                "3) Credenciamento para NFC-e no portal da SEFAZ do seu estado  4) CSC (Código de "
                "Segurança do Contribuinte) gerado no mesmo portal."
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

        self._titulo(aba, "CSC — Código de Segurança do Contribuinte", 12)
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
            return f"Status: certificado VENCIDO em {info['validade']}. É necessário renovar."
        aviso = (
            f" (vence em {info['dias_restantes']} dia(s) — considere renovar)"
            if info["vence_em_breve"]
            else ""
        )
        return f"Status: certificado válido até {info['validade']}{aviso}. Titular: {info['titular']}"

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

    def _valor(self, chave: str) -> str:
        return self.vars[chave].get().strip()

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
            messagebox.showerror(
                "Backup", "Dias de retencao deve ficar entre 1 e 3650."
            )
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
