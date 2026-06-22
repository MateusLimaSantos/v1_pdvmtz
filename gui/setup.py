import os
import re
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

from config import BASE_DIR, REPORTS_DIR, TIPOS_UNIDADE_VALIDOS
from core.auth import _hash_senha
from core.database import get_db_connection
from core.configuracoes import (
    salvar_dados_emitente,
    salvar_configuracao_pix,
    desativar_pix,
    alternar_cartao,
    cartao_esta_ativo,
    marcar_setup_concluido,
)
from core.helpers import set_config


class SetupInicial:
    """Assistente obrigatorio da primeira execucao."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Configuracao inicial - PDV MTZ")
        self.root.geometry("980x720")
        self.root.minsize(900, 650)
        self.concluido = False

        self.vars: dict[str, tk.StringVar] = {}
        self.bool_vars: dict[str, tk.BooleanVar] = {}

        self._montar()

    def run(self) -> bool:
        self.root.mainloop()
        return self.concluido

    def _aba_scroll(self, notebook: ttk.Notebook, titulo: str) -> tk.Frame:
        outer = tk.Frame(notebook)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, padx=14, pady=14)

        frame.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        notebook.add(outer, text=titulo)
        return frame

    def _titulo_secao(self, parent, texto: str, row: int):
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
        *,
        default: str = "",
        show: str | None = None,
        width: int = 42,
    ):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=4)
        var = tk.StringVar(value=default)
        ent = tk.Entry(parent, textvariable=var, width=width, show=show)
        ent.grid(row=row, column=1, sticky="ew", pady=4, padx=4)
        self.vars[chave] = var
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
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=4)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=40)
        combo.grid(row=row, column=1, sticky="ew", pady=4, padx=4)
        self.vars[chave] = var
        return combo

    def _check(self, parent, label: str, chave: str, row: int, *, default: bool = False, state: str = "normal"):
        var = tk.BooleanVar(value=default)
        chk = tk.Checkbutton(parent, text=label, variable=var, state=state)
        chk.grid(row=row, column=0, columnspan=3, sticky="w", pady=4, padx=4)
        self.bool_vars[chave] = var
        return chk

    def _browse_dir(self, chave: str):
        atual = self.vars[chave].get().strip() or BASE_DIR
        caminho = filedialog.askdirectory(initialdir=atual, title="Selecione uma pasta")
        if caminho:
            self.vars[chave].set(caminho)

    def _browse_file(self, chave: str):
        caminho = filedialog.askopenfilename(title="Selecione um arquivo")
        if caminho:
            self.vars[chave].set(caminho)

    def _campo_pasta(self, parent, label: str, chave: str, row: int, default: str):
        self._campo(parent, label, chave, row, default=default, width=54)
        tk.Button(parent, text="Procurar", command=lambda: self._browse_dir(chave)).grid(
            row=row, column=2, sticky="w", padx=4
        )

    def _campo_arquivo(self, parent, label: str, chave: str, row: int):
        self._campo(parent, label, chave, row, width=54)
        tk.Button(parent, text="Procurar", command=lambda: self._browse_file(chave)).grid(
            row=row, column=2, sticky="w", padx=4
        )

    def _montar(self):
        tk.Label(
            self.root,
            text="Primeira configuracao do sistema",
            font=("Arial", 18, "bold"),
        ).pack(pady=(16, 4))
        tk.Label(
            self.root,
            text="Configure a base minima para operar o PDV com seguranca.",
            font=("Arial", 10),
            fg="#555",
        ).pack(pady=(0, 10))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=16, pady=8)

        self._montar_empresa(self._aba_scroll(notebook, "Empresa"))
        self._montar_admin(self._aba_scroll(notebook, "Admin"))
        self._montar_pagamentos(self._aba_scroll(notebook, "Pagamentos"))
        self._montar_fiscal(self._aba_scroll(notebook, "Fiscal"))
        self._montar_pdv_estoque(self._aba_scroll(notebook, "PDV/Estoque"))
        self._montar_impressao_backup(self._aba_scroll(notebook, "PDF/Backup"))
        self._montar_painel_admin(self._aba_scroll(notebook, "Painel Admin"))

        rodape = tk.Frame(self.root)
        rodape.pack(fill="x", padx=18, pady=(4, 16))
        tk.Button(rodape, text="Cancelar", command=self.root.destroy, width=16).pack(side="right", padx=6)
        tk.Button(
            rodape,
            text="Salvar configuracao",
            command=self._salvar,
            width=22,
            bg="#2e7d32",
            fg="white",
        ).pack(side="right", padx=6)

    def _montar_empresa(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo_secao(aba, "Dados do emitente", 0)
        campos = [
            ("Razao social", "razao_social", ""),
            ("Nome fantasia", "nome_fantasia", ""),
            ("CNPJ", "cnpj", ""),
            ("Inscricao estadual", "ie", "ISENTO"),
            ("Telefone", "telefone", ""),
            ("CEP", "cep", ""),
            ("Logradouro", "logradouro", ""),
            ("Numero", "numero", ""),
            ("Bairro", "bairro", ""),
            ("Municipio", "municipio", ""),
            ("UF", "uf", ""),
            ("Regime/CRT (1 Simples, 2 SN excesso, 3 Regime normal)", "regime", "1"),
        ]
        for i, (label, chave, default) in enumerate(campos, start=1):
            self._campo(aba, label, chave, i, default=default)

    def _montar_admin(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo_secao(aba, "Administrador principal", 0)
        self._campo(aba, "Login do administrador", "admin_nome", 1)
        self._campo(aba, "Senha", "admin_senha", 2, show="*")
        self._campo(aba, "Confirmar senha", "admin_senha2", 3, show="*")
        tk.Label(
            aba,
            text=(
                "Este usuario tera acesso ao painel interno, operadores, configuracoes, "
                "cancelamentos e relatorios."
            ),
            fg="#555",
            wraplength=760,
            justify="left",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=10)

        self._titulo_secao(aba, "Permissoes iniciais", 5)
        self._check(aba, "Operadores comuns podem vender", "perm_operador_vender", 6, default=True)
        self._check(aba, "Cancelamento de venda apenas para administrador", "perm_cancelamento_admin", 7, default=True)
        self._check(aba, "Ajuste de estoque apenas para administrador", "perm_estoque_admin", 8, default=True)
        self._campo(aba, "Desconto maximo do operador comum (%)", "desconto_operador_max", 9, default="10")

    def _montar_pagamentos(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo_secao(aba, "PIX", 0)
        self._check(aba, "Ativar PIX manual nesta versao", "pix_ativo", 1, default=False)
        self._combo(aba, "Tipo da chave PIX", "pix_tipo", 2, ("1", "2", "3", "4", "5"), "4")
        self._campo(aba, "Chave PIX", "pix_chave", 3)
        self._campo(aba, "Banco/instituicao", "pix_banco", 4)
        self._campo(aba, "Nome do titular", "pix_nome", 5)
        self._check(
            aba,
            "PIX automatico via API do banco (em desenvolvimento)",
            "pix_api_em_desenvolvimento",
            6,
            default=False,
            state="disabled",
        )

        self._titulo_secao(aba, "Cartao/maquininha", 7)
        self._check(
            aba,
            "Cartao integrado ao sistema (em desenvolvimento)",
            "cartao_integrado_em_desenvolvimento",
            8,
            default=False,
            state="disabled",
        )
        self._check(aba, "Permitir registro manual de venda em cartao no futuro", "cartao_manual_futuro", 9, default=True)
        tk.Label(
            aba,
            text="Nesta etapa, a maquininha fica externa e a confirmacao sera manual quando o recurso for liberado.",
            fg="#8a5a00",
            wraplength=760,
            justify="left",
        ).grid(row=10, column=0, columnspan=3, sticky="w", pady=10)

    def _montar_fiscal(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo_secao(aba, "Modo fiscal", 0)
        self._combo(
            aba,
            "Modo de emissao",
            "modo_fiscal",
            1,
            ("simulado", "nfce_homologacao_em_desenvolvimento", "nfce_producao_em_desenvolvimento"),
            "simulado",
        )
        self._campo_arquivo(aba, "Certificado digital A1/PFX (futuro)", "certificado_pfx", 2)
        self._campo(aba, "Senha do certificado (futuro)", "certificado_senha", 3, show="*")
        self._check(aba, "Gerar cupom/PDF interno apos venda", "fiscal_gerar_cupom_pdf", 4, default=True)
        self._check(aba, "Exibir aviso de documento nao fiscal no modo simulado", "fiscal_aviso_simulado", 5, default=True)
        tk.Label(
            aba,
            text=(
                "Apenas o modo simulado esta operacional agora. NFC-e real exige certificado, "
                "tributacao, homologacao e autorizacao da SEFAZ."
            ),
            fg="#8a0000",
            wraplength=760,
            justify="left",
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=10)

    def _montar_pdv_estoque(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo_secao(aba, "Comportamento do PDV", 0)
        self._check(aba, "Abrir o PDV logo apos o login", "pdv_abrir_apos_login", 1, default=True)
        self._check(aba, "Bloquear venda quando nao houver produto cadastrado", "pdv_bloquear_sem_produtos", 2, default=True)
        self._check(aba, "Perguntar se o pagamento foi confirmado antes de finalizar", "pdv_confirmar_pagamento", 3, default=True)
        self._check(aba, "Perguntar se o cliente quer impressao/PDF do cupom", "pdv_perguntar_impressao", 4, default=True)
        self._check(aba, "Ativar atalhos F1-F12 e teclado numerico", "pdv_atalhos_ativos", 5, default=True)

        self._titulo_secao(aba, "Estoque e unidades", 6)
        self._check(aba, "Bloquear estoque negativo", "estoque_bloquear_negativo", 7, default=True)
        self._check(aba, "Permitir embalagens/fardos vinculados ao produto base", "estoque_embalagens_ativas", 8, default=True)
        self._check(aba, "Permitir entrada manual de estoque", "estoque_entrada_manual", 9, default=True)
        self._check(aba, "Permitir importacao de XML de compra", "estoque_importar_xml", 10, default=True)
        self._campo(
            aba,
            "Unidades ativas",
            "estoque_unidades_ativas",
            11,
            default=",".join(TIPOS_UNIDADE_VALIDOS),
        )
        tk.Label(
            aba,
            text="Use produto base + embalagens para vender avulso, fardo, caixa, pacote ou engradado.",
            fg="#555",
            wraplength=760,
            justify="left",
        ).grid(row=12, column=0, columnspan=3, sticky="w", pady=10)

    def _montar_impressao_backup(self, aba):
        aba.columnconfigure(1, weight=1)
        self._titulo_secao(aba, "PDF e impressao", 0)
        self._campo_pasta(aba, "Pasta de PDFs/relatorios", "reports_dir", 1, REPORTS_DIR)
        self._check(aba, "Gerar PDF automaticamente apos finalizar venda", "impressao_gerar_pdf", 2, default=True)
        self._check(aba, "Abrir PDF automaticamente apos gerar", "impressao_abrir_pdf", 3, default=False)
        self._check(aba, "Imprimir automaticamente (futuro)", "impressao_auto_em_desenvolvimento", 4, default=False, state="disabled")

        self._titulo_secao(aba, "Backup", 5)
        self._campo_pasta(aba, "Pasta de backups", "backup_dir", 6, os.path.join(BASE_DIR, "backups"))
        self._combo(aba, "Periodicidade", "backup_periodicidade", 7, ("manual", "diario", "semanal"), "diario")
        self._campo(aba, "Manter backups por quantos dias", "backup_manter_dias", 8, default="30")
        self._check(aba, "Fazer backup ao fechar o sistema (futuro)", "backup_ao_fechar", 9, default=True)

    def _montar_painel_admin(self, aba):
        self._titulo_secao(aba, "Modulos visiveis para administrador", 0)
        self._check(aba, "Fornecedores", "admin_mod_fornecedores", 1, default=True)
        self._check(aba, "Operadores e permissoes", "admin_mod_operadores", 2, default=True)
        self._check(aba, "Historico de vendas e cupons/PDFs", "admin_mod_historico", 3, default=True)
        self._check(aba, "Graficos de vendas mensal", "admin_mod_graficos", 4, default=True)
        self._check(aba, "Caixa: abertura, fechamento, sangria e suprimento", "admin_mod_caixa", 5, default=True)
        self._check(aba, "Auditoria de alteracoes", "admin_mod_auditoria", 6, default=True)
        tk.Label(
            aba,
            text="Essas opcoes ficam salvas para orientar a proxima etapa: construir o painel interno do administrador.",
            fg="#555",
            wraplength=760,
            justify="left",
        ).grid(row=7, column=0, columnspan=3, sticky="w", pady=10)

    def _valor(self, chave: str) -> str:
        return self.vars[chave].get().strip()

    def _bool(self, chave: str) -> bool:
        return bool(self.bool_vars[chave].get())

    def _validar_admin(self) -> tuple[bool, str, str, str]:
        nome = self._valor("admin_nome")
        senha = self._valor("admin_senha")
        senha2 = self._valor("admin_senha2")

        if not re.match(r"^[A-Za-z0-9_.-]{3,30}$", nome):
            return False, "", "", "Login admin deve ter 3 a 30 caracteres, sem espacos."
        if len(senha) < 6:
            return False, "", "", "Senha admin deve ter ao menos 6 caracteres."
        if senha != senha2:
            return False, "", "", "Confirmacao de senha nao confere."
        return True, nome, _hash_senha(senha), ""

    def _salvar_admin(self, nome: str, senha_hash: str) -> tuple[bool, str]:
        hash_padrao = _hash_senha("admin")

        with get_db_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM operadores").fetchone()[0]
            padrao = conn.execute(
                "SELECT id FROM operadores WHERE nome='admin' AND senha=?",
                (hash_padrao,),
            ).fetchone()

            try:
                if padrao and total == 1:
                    conn.execute(
                        "UPDATE operadores SET nome=?, senha=?, perfil='admin', ativo=1 WHERE id=?",
                        (nome, senha_hash, padrao["id"]),
                    )
                elif total == 0:
                    conn.execute(
                        "INSERT INTO operadores (nome, senha, perfil, ativo) VALUES (?,?,?,1)",
                        (nome, senha_hash, "admin"),
                    )
                else:
                    existente = conn.execute(
                        "SELECT id FROM operadores WHERE nome=?",
                        (nome,),
                    ).fetchone()
                    if existente:
                        conn.execute(
                            "UPDATE operadores SET senha=?, perfil='admin', ativo=1 WHERE id=?",
                            (senha_hash, existente["id"]),
                        )
                    else:
                        conn.execute(
                            "INSERT INTO operadores (nome, senha, perfil, ativo) VALUES (?,?,?,1)",
                            (nome, senha_hash, "admin"),
                        )
            except sqlite3.IntegrityError:
                return False, "Ja existe operador com este login."

        return True, ""

    def _validar_configs_operacionais(self) -> tuple[bool, str]:
        try:
            desconto = float(self._valor("desconto_operador_max").replace(",", "."))
        except ValueError:
            return False, "Desconto maximo do operador deve ser numerico."
        if not (0 <= desconto <= 100):
            return False, "Desconto maximo do operador deve estar entre 0 e 100."

        try:
            manter_dias = int(self._valor("backup_manter_dias"))
        except ValueError:
            return False, "Dias de retencao de backup deve ser numero inteiro."
        if not (1 <= manter_dias <= 3650):
            return False, "Dias de retencao de backup deve ficar entre 1 e 3650."

        unidades = [u.strip() for u in self._valor("estoque_unidades_ativas").split(",") if u.strip()]
        invalidas = [u for u in unidades if u not in TIPOS_UNIDADE_VALIDOS]
        if invalidas:
            return False, f"Unidades invalidas: {', '.join(invalidas)}."
        if "unidade" not in unidades:
            return False, "Unidades ativas deve incluir 'unidade'."

        modo_fiscal = self._valor("modo_fiscal")
        if modo_fiscal != "simulado":
            return False, "Apenas o modo fiscal 'simulado' esta operacional nesta versao."

        return True, ""

    def _salvar_configs_operacionais(self):
        configs_texto = {
            "desconto_operador_max": self._valor("desconto_operador_max").replace(",", "."),
            "modo_fiscal": self._valor("modo_fiscal"),
            "certificado_pfx": self._valor("certificado_pfx"),
            "reports_dir": self._valor("reports_dir"),
            "backup_dir": self._valor("backup_dir"),
            "backup_periodicidade": self._valor("backup_periodicidade"),
            "backup_manter_dias": self._valor("backup_manter_dias"),
            "estoque_unidades_ativas": self._valor("estoque_unidades_ativas"),
            "cartao_status": "em_desenvolvimento",
            "pix_api_status": "em_desenvolvimento",
        }
        for chave, valor in configs_texto.items():
            set_config(chave, valor)

        for chave, var in self.bool_vars.items():
            set_config(chave, "True" if var.get() else "False")

        os.makedirs(self._valor("reports_dir"), exist_ok=True)
        os.makedirs(self._valor("backup_dir"), exist_ok=True)

    def _salvar(self):
        ok_admin, admin_nome, admin_hash, erro_admin = self._validar_admin()
        if not ok_admin:
            messagebox.showerror("Administrador", erro_admin)
            return

        ok_operacao, erro_operacao = self._validar_configs_operacionais()
        if not ok_operacao:
            messagebox.showerror("Configuracao", erro_operacao)
            return

        dados_empresa = {
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

        ok_empresa, erros = salvar_dados_emitente(dados_empresa)
        if not ok_empresa:
            texto = "\n".join(f"- {e['campo']}: {e['mensagem']}" for e in erros)
            messagebox.showerror("Dados da empresa", texto)
            return

        ok_admin_save, erro_admin_save = self._salvar_admin(admin_nome, admin_hash)
        if not ok_admin_save:
            messagebox.showerror("Administrador", erro_admin_save)
            return

        if self._bool("pix_ativo"):
            ok_pix, msg_pix = salvar_configuracao_pix(
                self._valor("pix_tipo"),
                self._valor("pix_chave"),
                self._valor("pix_banco"),
                self._valor("pix_nome"),
            )
            if not ok_pix:
                messagebox.showerror("PIX", msg_pix)
                return
        else:
            desativar_pix()

        if cartao_esta_ativo():
            alternar_cartao()

        self._salvar_configs_operacionais()
        marcar_setup_concluido()

        self.concluido = True
        messagebox.showinfo(
            "Configuracao concluida",
            "Setup salvo. O sistema sera iniciado na tela de login.",
        )
        self.root.destroy()
