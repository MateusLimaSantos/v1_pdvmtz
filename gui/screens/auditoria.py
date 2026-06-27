import tkinter as tk
from tkinter import ttk

from core.auditoria import (
    listar_auditoria,
    listar_entidades_distintas,
    listar_acoes_distintas,
)


class TelaAuditoria(tk.Frame):
    """Tela de auditoria: lista quem fez o que no sistema, com filtros."""

    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.pack(fill="both", expand=True, padx=12, pady=12)

        self.configurar_layout()
        self.carregar_dados()

    def configurar_layout(self):
        topo = tk.Frame(self)
        topo.pack(fill="x", pady=(0, 10))
        tk.Label(
            topo,
            text="Auditoria",
            font=("Arial", 18, "bold"),
        ).pack(side="left")
        tk.Button(
            topo,
            text="Voltar ao menu",
            command=self.controlador.mostrar_tela_principal,
            bg="#e0e0e0",
        ).pack(side="right")

        filtros = tk.Frame(self)
        filtros.pack(fill="x", pady=(0, 10))

        tk.Label(filtros, text="Data início:").pack(side="left", padx=(0, 4))
        self.entry_data_ini = tk.Entry(filtros, width=11)
        self.entry_data_ini.pack(side="left", padx=(0, 10))

        tk.Label(filtros, text="Data fim:").pack(side="left", padx=(0, 4))
        self.entry_data_fim = tk.Entry(filtros, width=11)
        self.entry_data_fim.pack(side="left", padx=(0, 10))

        tk.Label(filtros, text="Entidade:").pack(side="left", padx=(0, 4))
        self.var_entidade = tk.StringVar(value="todas")
        self.combo_entidade = ttk.Combobox(
            filtros, textvariable=self.var_entidade, state="readonly", width=13
        )
        self.combo_entidade.pack(side="left", padx=(0, 10))

        tk.Label(filtros, text="Ação:").pack(side="left", padx=(0, 4))
        self.var_acao = tk.StringVar(value="todas")
        self.combo_acao = ttk.Combobox(
            filtros, textvariable=self.var_acao, state="readonly", width=15
        )
        self.combo_acao.pack(side="left", padx=(0, 10))

        tk.Label(filtros, text="Operador:").pack(side="left", padx=(0, 4))
        self.entry_operador = tk.Entry(filtros, width=14)
        self.entry_operador.pack(side="left", padx=(0, 10))

        tk.Button(
            filtros,
            text="Filtrar",
            command=self.carregar_dados,
            bg="#1976D2",
            fg="white",
        ).pack(side="left", padx=(0, 6))
        tk.Button(filtros, text="Limpar", command=self._limpar_filtros).pack(
            side="left"
        )

        colunas = (
            "data",
            "operador",
            "acao",
            "entidade",
            "id_entidade",
            "status",
            "detalhes",
        )
        self.tree = ttk.Treeview(self, columns=colunas, show="headings", height=20)
        titulos = {
            "data": "Data/Hora",
            "operador": "Operador",
            "acao": "Ação",
            "entidade": "Entidade",
            "id_entidade": "ID",
            "status": "Status",
            "detalhes": "Detalhes",
        }
        larguras = {
            "data": 130,
            "operador": 130,
            "acao": 130,
            "entidade": 100,
            "id_entidade": 70,
            "status": 80,
            "detalhes": 320,
        }
        for col in colunas:
            self.tree.heading(col, text=titulos[col])
            anchor = "w" if col in ("operador", "detalhes") else "center"
            self.tree.column(col, width=larguras[col], anchor=anchor)
        self.tree.pack(fill="both", expand=True, pady=(0, 6))

        self.tree.tag_configure("falha", background="#fdecea")

        self.lbl_contagem = tk.Label(self, text="", fg="#777", font=("Arial", 9))
        self.lbl_contagem.pack(anchor="w")

        self._popular_combos()

    def _popular_combos(self):
        entidades = ["todas"] + listar_entidades_distintas()
        self.combo_entidade["values"] = entidades
        acoes = ["todas"] + listar_acoes_distintas()
        self.combo_acao["values"] = acoes

    def _limpar_filtros(self):
        self.entry_data_ini.delete(0, "end")
        self.entry_data_fim.delete(0, "end")
        self.entry_operador.delete(0, "end")
        self.var_entidade.set("todas")
        self.var_acao.set("todas")
        self.carregar_dados()

    def carregar_dados(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        entidade = self.var_entidade.get()
        acao = self.var_acao.get()

        eventos = listar_auditoria(
            limite=300,
            entidade=None if entidade == "todas" else entidade,
            acao=None if acao == "todas" else acao,
            operador_nome=self.entry_operador.get().strip() or None,
            data_ini_br=self.entry_data_ini.get().strip() or None,
            data_fim_br=self.entry_data_fim.get().strip() or None,
        )

        for e in eventos:
            status = "OK" if e["sucesso"] else "FALHA"
            tag = "falha" if not e["sucesso"] else ""
            self.tree.insert(
                "",
                "end",
                values=(
                    e["data_hora_fmt"],
                    e["operador_nome"],
                    e["acao"],
                    e["entidade"],
                    e["entidade_id"],
                    status,
                    e["detalhes"],
                ),
                tags=(tag,) if tag else (),
            )

        self.lbl_contagem.config(text=f"{len(eventos)} evento(s) encontrado(s).")
        self._popular_combos()
