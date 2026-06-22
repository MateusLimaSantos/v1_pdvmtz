from __future__ import annotations

from datetime import datetime
from pathlib import Path

CONFIG_SCREEN = r'''import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import BASE_DIR, REPORTS_DIR, TIPOS_UNIDADE_VALIDOS
from core.configuracoes import (
    salvar_dados_emitente,
    salvar_configuracao_pix,
    desativar_pix,
)
from core.helpers import get_config, set_config
from core.state import state


class TelaConfiguracoes(tk.Frame):
    """Painel interno de configuracoes, visivel apenas para administradores."""

    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.vars: dict[str, tk.StringVar] = {}
        self.bool_vars: dict[str, tk.BooleanVar] = {}
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
        tk.Label(frame, text="Somente administradores podem acessar configuracoes.").pack(pady=8)
        tk.Button(frame, text="Voltar", command=self.controlador.mostrar_tela_principal).pack(pady=12)

    def _aba_scroll(self, notebook: ttk.Notebook, titulo: str) -> tk.Frame:
        outer = tk.Frame(notebook)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, padx=14, pady=14)

        frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        notebook.add(outer, text=titulo)
        return frame

    def _titulo(self, parent, texto: str, row: int):
        tk.Label(
            parent,
            text=texto,
            font=("Arial", 11, "bold"),
            fg="#333",
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(12, 6))

    def _campo(self, parent, label: str, chave: str, row: int, default: str = "", show: str | None = None):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
        var = tk.StringVar(value=default)
        ent = tk.Entry(parent, textvariable=var, width=48, show=show)
        ent.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        self.vars[chave] = var
        return ent

    def _combo(self, parent, label: str, chave: str, row: int, values: tuple[str, ...], default: str):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=46)
        combo.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        self.vars[chave] = var
        return combo

    def _check(self, parent, label: str, chave: str, row: int, default: bool = False, state_opt: str = "normal"):
        var = tk.BooleanVar(value=default)
        chk = tk.Checkbutton(parent, text=label, variable=var, state=state_opt)
        chk.grid(row=row, column=0, columnspan=3, sticky="w", padx=4, pady=4)
        self.bool_vars[chave] = var
        return chk

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
        self._titulo(aba, "PIX", 0)
        self._check(aba, "Ativar PIX manual", "pix_ativo", 1, self._cfg_bool("pix_ativo"))
        self._combo(aba, "Tipo da chave PIX", "pix_tipo", 2, ("1", "2", "3", "4", "5"), self._cfg("pix_tipo", "4"))
        self._campo(aba, "Chave PIX", "pix_chave", 3, self._cfg("pix_chave"))
        self._campo(aba, "Banco/instituicao", "pix_banco", 4, self._cfg("pix_banco"))
        self._campo(aba, "Nome do titular", "pix_nome", 5, self._cfg("pix_nome"))
        self._check(aba, "PIX automatico via API do banco (em desenvolvimento)", "pix_api_em_desenvolvimento", 6, False, "disabled")

        self._titulo(aba, "Cartao / maquininha", 7)
        self._check(aba, "Cartao integrado ao sistema (em desenvolvimento)", "cartao_integrado_em_desenvolvimento", 8, False, "disabled")
        self._check(aba, "Permitir registro manual de cartao no futuro", "cartao_manual_futuro", 9, self._cfg_bool("cartao_manual_futuro", True))
        tk.Label(
            aba,
            text="Por enquanto a maquininha fica fora do sistema; a confirmacao sera manual quando liberarmos essa tela.",
            fg="#8a5a00",
            wraplength=760,
            justify="left",
        ).grid(row=10, column=0, columnspan=3, sticky="w", pady=8)
        tk.Button(aba, text="Salvar pagamentos", command=self._salvar_pagamentos, bg="#2e7d32", fg="white").grid(
            row=11, column=1, sticky="e", pady=12
        )

    def _montar_fiscal(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo(aba, "Documento fiscal", 0)
        self._combo(aba, "Modo de emissao", "modo_fiscal", 1, ("simulado",), self._cfg("modo_fiscal", "simulado"))
        self._check(aba, "Gerar cupom/PDF interno apos venda", "fiscal_gerar_cupom_pdf", 2, self._cfg_bool("fiscal_gerar_cupom_pdf", True))
        self._check(aba, "Exibir aviso de documento nao fiscal", "fiscal_aviso_simulado", 3, self._cfg_bool("fiscal_aviso_simulado", True))
        tk.Label(
            aba,
            text="NFC-e/SAT real ainda nao esta implementado. O modo atual gera cupom interno nao fiscal/simulado.",
            fg="#8a0000",
            wraplength=760,
            justify="left",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=8)
        tk.Button(aba, text="Salvar fiscal", command=self._salvar_fiscal, bg="#2e7d32", fg="white").grid(
            row=5, column=1, sticky="e", pady=12
        )

    def _montar_pdv_estoque(self, aba):
        self._titulo(aba, "Comportamento do PDV", 0)
        self._check(aba, "Abrir o PDV logo apos login", "pdv_abrir_apos_login", 1, self._cfg_bool("pdv_abrir_apos_login", True))
        self._check(aba, "Bloquear venda sem produtos cadastrados", "pdv_bloquear_sem_produtos", 2, self._cfg_bool("pdv_bloquear_sem_produtos", True))
        self._check(aba, "Confirmar pagamento antes de finalizar", "pdv_confirmar_pagamento", 3, self._cfg_bool("pdv_confirmar_pagamento", True))
        self._check(aba, "Perguntar se cliente quer impressao/PDF", "pdv_perguntar_impressao", 4, self._cfg_bool("pdv_perguntar_impressao", True))
        self._check(aba, "Ativar atalhos F1-F12 e teclado numerico", "pdv_atalhos_ativos", 5, self._cfg_bool("pdv_atalhos_ativos", True))

        self._titulo(aba, "Estoque e unidades", 6)
        self._check(aba, "Bloquear estoque negativo", "estoque_bloquear_negativo", 7, self._cfg_bool("estoque_bloquear_negativo", True))
        self._check(aba, "Permitir embalagens/fardos por produto base", "estoque_embalagens_ativas", 8, self._cfg_bool("estoque_embalagens_ativas", True))
        self._check(aba, "Permitir entrada manual", "estoque_entrada_manual", 9, self._cfg_bool("estoque_entrada_manual", True))
        self._check(aba, "Permitir importacao XML de compra", "estoque_importar_xml", 10, self._cfg_bool("estoque_importar_xml", True))
        self._campo(aba, "Unidades ativas", "estoque_unidades_ativas", 11, self._cfg("estoque_unidades_ativas", ",".join(TIPOS_UNIDADE_VALIDOS)))
        tk.Button(aba, text="Salvar PDV/Estoque", command=self._salvar_pdv_estoque, bg="#2e7d32", fg="white").grid(
            row=12, column=1, sticky="e", pady=12
        )

    def _montar_pdf_backup(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo(aba, "PDF", 0)
        self._campo_pasta(aba, "Pasta de PDFs/relatorios", "reports_dir", 1, self._cfg("reports_dir", REPORTS_DIR))
        self._check(aba, "Gerar PDF automaticamente", "impressao_gerar_pdf", 2, self._cfg_bool("impressao_gerar_pdf", True))
        self._check(aba, "Abrir PDF automaticamente", "impressao_abrir_pdf", 3, self._cfg_bool("impressao_abrir_pdf", False))
        self._check(aba, "Imprimir automaticamente (em desenvolvimento)", "impressao_auto_em_desenvolvimento", 4, False, "disabled")

        self._titulo(aba, "Backup", 5)
        self._campo_pasta(aba, "Pasta de backups", "backup_dir", 6, self._cfg("backup_dir", os.path.join(BASE_DIR, "backups")))
        self._combo(aba, "Periodicidade", "backup_periodicidade", 7, ("manual", "diario", "semanal"), self._cfg("backup_periodicidade", "diario"))
        self._campo(aba, "Manter backups por quantos dias", "backup_manter_dias", 8, self._cfg("backup_manter_dias", "30"))
        self._check(aba, "Backup ao fechar o sistema (futuro)", "backup_ao_fechar", 9, self._cfg_bool("backup_ao_fechar", True))
        tk.Button(aba, text="Salvar PDF/Backup", command=self._salvar_pdf_backup, bg="#2e7d32", fg="white").grid(
            row=10, column=1, sticky="e", pady=12
        )

    def _montar_painel_admin(self, aba):
        self._titulo(aba, "Modulos do painel interno", 0)
        checks = [
            ("Fornecedores", "admin_mod_fornecedores"),
            ("Operadores e permissoes", "admin_mod_operadores"),
            ("Historico de vendas e cupons/PDFs", "admin_mod_historico"),
            ("Graficos de vendas mensal", "admin_mod_graficos"),
            ("Caixa: sangria, suprimento e fechamento", "admin_mod_caixa"),
            ("Auditoria de alteracoes", "admin_mod_auditoria"),
        ]
        for i, (label, chave) in enumerate(checks, start=1):
            self._check(aba, label, chave, i, self._cfg_bool(chave, True))
        tk.Button(aba, text="Salvar painel admin", command=self._salvar_painel_admin, bg="#2e7d32", fg="white").grid(
            row=len(checks) + 1, column=1, sticky="e", pady=12
        )

    def _montar_operadores(self, aba):
        tk.Label(
            aba,
            text="Gestao de operadores",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(10, 6))
        tk.Label(
            aba,
            text=(
                "A criacao completa de operadores vai entrar na proxima tela. "
                "Por enquanto este painel confirma que apenas administradores acessam configuracoes."
            ),
            wraplength=760,
            justify="left",
            fg="#555",
        ).grid(row=1, column=0, sticky="w", pady=8)

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
        set_config("cartao_manual_futuro", "True" if self.bool_vars["cartao_manual_futuro"].get() else "False")
        set_config("pix_api_status", "em_desenvolvimento")
        messagebox.showinfo("Configuracoes", "Pagamentos salvos.")

    def _salvar_fiscal(self):
        set_config("modo_fiscal", "simulado")
        for chave in ("fiscal_gerar_cupom_pdf", "fiscal_aviso_simulado"):
            set_config(chave, "True" if self.bool_vars[chave].get() else "False")
        messagebox.showinfo("Configuracoes", "Configuracao fiscal salva.")

    def _salvar_pdv_estoque(self):
        unidades = [u.strip() for u in self._valor("estoque_unidades_ativas").split(",") if u.strip()]
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
        for chave in ("reports_dir", "backup_dir", "backup_periodicidade", "backup_manter_dias"):
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
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Trecho nao encontrado: {label}")
    return text.replace(old, new, 1)


def patch_app(app_path: Path) -> None:
    text = app_path.read_text(encoding="utf-8")
    if "from gui.screens.configuracoes import TelaConfiguracoes" not in text:
        text = text.replace(
            "from gui.screens.nfe import TelaNFe\n",
            "from gui.screens.nfe import TelaNFe\nfrom gui.screens.configuracoes import TelaConfiguracoes\n",
            1,
        )
    if "def mostrar_configuracoes(self):" not in text:
        text = text.replace(
            "    def mostrar_nfe(self):\n        self.limpar_container()\n        TelaNFe(self.container, self)\n\n",
            "    def mostrar_nfe(self):\n        self.limpar_container()\n        TelaNFe(self.container, self)\n\n"
            "    def mostrar_configuracoes(self):\n"
            "        self.limpar_container()\n"
            "        TelaConfiguracoes(self.container, self)\n\n",
            1,
        )
    if 'text="Configuracoes"' not in text:
        logout_cmd = "            command=self.realizar_logoff,"
        logout_pos = text.find(logout_cmd)
        if logout_pos == -1:
            raise RuntimeError("Trecho nao encontrado: botao logoff")
        button_start = text.rfind("        tk.Button(", 0, logout_pos)
        if button_start == -1:
            raise RuntimeError("Trecho nao encontrado: inicio botao logoff")
        insert = (
            '        if state.operador and state.operador.get("perfil") == "admin":\n'
            "            tk.Button(\n"
            "                frame_menu,\n"
            '                text="Configuracoes",\n'
            '                font=("Arial", 14),\n'
            "                width=25,\n"
            "                height=2,\n"
            '                bg="#455A64",\n'
            '                fg="white",\n'
            "                bd=0,\n"
            "                command=self.mostrar_configuracoes,\n"
            "            ).pack(pady=8)\n\n"
        )
        text = text[:button_start] + insert + text[button_start:]
    app_path.write_text(text, encoding="utf-8", newline="\n")


def patch_pdv(pdv_path: Path) -> None:
    text = pdv_path.read_text(encoding="utf-8")
    if 'text="Configuracoes"' in text:
        return
    marker = (
        "        tk.Button(\n"
        "            frame_direito,\n"
        '            text="Fechar Caixa",\n'
        '            font=("Arial", 10),\n'
        '            bg="#cfd8dc",\n'
        "            command=self.executar_fechamento_caixa,\n"
        '        ).pack(fill="x", padx=15, pady=5)\n'
    )
    insert = marker + (
        '        if state.operador and state.operador.get("perfil") == "admin":\n'
        "            tk.Button(\n"
        "                frame_direito,\n"
        '                text="Configuracoes",\n'
        '                font=("Arial", 10),\n'
        '                bg="#455A64",\n'
        '                fg="white",\n'
        "                command=self.controlador.mostrar_configuracoes,\n"
        '            ).pack(fill="x", padx=15, pady=5)\n'
    )
    text = replace_once(text, marker, insert, "botao configuracoes pdv")
    pdv_path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    root = Path(r"K:\pdvmtz_v2")
    backup_dir = root / ".codex_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        root / "gui" / "app.py",
        root / "gui" / "screens" / "pdv.py",
        root / "gui" / "screens" / "configuracoes.py",
    ]
    for path in targets:
        if path.exists():
            (backup_dir / path.name).write_text(
                path.read_text(encoding="utf-8"), encoding="utf-8"
            )

    config_path = root / "gui" / "screens" / "configuracoes.py"
    config_path.write_text(CONFIG_SCREEN, encoding="utf-8", newline="\n")
    patch_app(root / "gui" / "app.py")
    patch_pdv(root / "gui" / "screens" / "pdv.py")

    print("Tela interna de configuracoes adicionada.")
    print(f"Backup: {backup_dir}")


if __name__ == "__main__":
    main()
