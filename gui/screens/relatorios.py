import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from core.relatorios import relatorio_vendas_periodo, relatorio_curva_abc


class TelaRelatorios(tk.Frame):
    """Tela de relatorios: vendas por periodo e curva ABC de produtos."""

    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.pack(fill="both", expand=True, padx=12, pady=12)

        self.configurar_layout()

    def configurar_layout(self):
        topo = tk.Frame(self)
        topo.pack(fill="x", pady=(0, 10))
        tk.Label(
            topo,
            text="Relatórios",
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

        aba_periodo = tk.Frame(notebook, padx=14, pady=14)
        notebook.add(aba_periodo, text="Vendas por período")
        self._montar_aba_periodo(aba_periodo)

        aba_abc = tk.Frame(notebook, padx=14, pady=14)
        notebook.add(aba_abc, text="Curva ABC de produtos")
        self._montar_aba_abc(aba_abc)

    @staticmethod
    def _data_valida(texto: str) -> bool:
        return bool(re.match(r"^\d{2}/\d{2}/\d{4}$", texto.strip())) and _eh_data_real(
            texto.strip()
        )

    # ── Aba: vendas por período ──────────────────────────────

    def _montar_aba_periodo(self, aba):
        filtros = tk.Frame(aba)
        filtros.pack(fill="x", pady=(0, 12))

        tk.Label(filtros, text="Data início (dd/mm/aaaa):").pack(
            side="left", padx=(0, 4)
        )
        self.entry_periodo_ini = tk.Entry(filtros, width=12)
        self.entry_periodo_ini.pack(side="left", padx=(0, 12))

        tk.Label(filtros, text="Data fim (dd/mm/aaaa):").pack(side="left", padx=(0, 4))
        self.entry_periodo_fim = tk.Entry(filtros, width=12)
        self.entry_periodo_fim.pack(side="left", padx=(0, 12))

        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1)
        self.entry_periodo_ini.insert(0, primeiro_dia_mes.strftime("%d/%m/%Y"))
        self.entry_periodo_fim.insert(0, hoje.strftime("%d/%m/%Y"))

        tk.Button(
            filtros,
            text="Gerar relatório",
            command=self._gerar_relatorio_periodo,
            bg="#1976D2",
            fg="white",
        ).pack(side="left", padx=(0, 8))
        tk.Button(filtros, text="Mês atual", command=self._preencher_mes_atual).pack(
            side="left"
        )

        self.frame_resultado_periodo = tk.Frame(aba)
        self.frame_resultado_periodo.pack(fill="both", expand=True, pady=(10, 0))

        self._exibir_placeholder_periodo()

    def _exibir_placeholder_periodo(self):
        for w in self.frame_resultado_periodo.winfo_children():
            w.destroy()
        tk.Label(
            self.frame_resultado_periodo,
            text='Escolha um período e clique em "Gerar relatório".',
            fg="#777",
        ).pack(pady=30)

    def _preencher_mes_atual(self):
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1)
        self.entry_periodo_ini.delete(0, "end")
        self.entry_periodo_ini.insert(0, primeiro_dia_mes.strftime("%d/%m/%Y"))
        self.entry_periodo_fim.delete(0, "end")
        self.entry_periodo_fim.insert(0, hoje.strftime("%d/%m/%Y"))

    def _gerar_relatorio_periodo(self):
        data_ini = self.entry_periodo_ini.get().strip()
        data_fim = self.entry_periodo_fim.get().strip()

        if not self._data_valida(data_ini) or not self._data_valida(data_fim):
            messagebox.showerror(
                "Relatórios", "Informe datas válidas no formato dd/mm/aaaa."
            )
            return

        dt_ini = datetime.strptime(data_ini, "%d/%m/%Y")
        dt_fim = datetime.strptime(data_fim, "%d/%m/%Y")
        if dt_ini > dt_fim:
            messagebox.showerror(
                "Relatórios", "A data início não pode ser depois da data fim."
            )
            return

        relatorio = relatorio_vendas_periodo(data_ini, data_fim)
        self._exibir_resultado_periodo(relatorio)

    def _exibir_resultado_periodo(self, relatorio: dict):
        for w in self.frame_resultado_periodo.winfo_children():
            w.destroy()

        tk.Label(
            self.frame_resultado_periodo,
            text=f"Período: {relatorio['data_ini']} a {relatorio['data_fim']}",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        if relatorio["qtd_vendas"] == 0:
            tk.Label(
                self.frame_resultado_periodo,
                text="Nenhuma venda concluída encontrada neste período.",
                fg="#777",
            ).pack(pady=20)
            return

        resumo = tk.Frame(self.frame_resultado_periodo)
        resumo.pack(fill="x", pady=(0, 12))
        self._linha_resumo(
            resumo, "Quantidade de vendas:", str(relatorio["qtd_vendas"])
        )
        self._linha_resumo(
            resumo, "Total descontos:", f"R$ {relatorio['descontos']:.2f}"
        )
        self._linha_resumo(
            resumo,
            "Total geral vendido:",
            f"R$ {relatorio['total_geral']:.2f}",
            destaque=True,
        )

        tk.Label(
            self.frame_resultado_periodo,
            text="Totais por forma de pagamento",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w", pady=(4, 4))

        colunas = ("forma", "total")
        tree = ttk.Treeview(
            self.frame_resultado_periodo, columns=colunas, show="headings", height=6
        )
        tree.heading("forma", text="Forma de pagamento")
        tree.heading("total", text="Total")
        tree.column("forma", width=220, anchor="w")
        tree.column("total", width=150, anchor="e")
        tree.pack(fill="x")

        for forma, valor in sorted(
            relatorio["totais_por_forma"].items(), key=lambda x: -x[1]
        ):
            tree.insert("", "end", values=(forma, f"R$ {valor:.2f}"))

    @staticmethod
    def _linha_resumo(parent, rotulo: str, valor: str, destaque: bool = False):
        linha = tk.Frame(parent)
        linha.pack(fill="x", pady=2)
        tk.Label(linha, text=rotulo, font=("Arial", 10)).pack(side="left")
        tk.Label(
            linha,
            text=valor,
            font=("Arial", 11, "bold") if destaque else ("Arial", 10, "bold"),
            fg="#2e7d32" if destaque else "#333",
        ).pack(side="right")

    # ── Aba: curva ABC ────────────────────────────────────────

    def _montar_aba_abc(self, aba):
        filtros = tk.Frame(aba)
        filtros.pack(fill="x", pady=(0, 12))

        tk.Label(filtros, text="Top N produtos:").pack(side="left", padx=(0, 4))
        self.entry_abc_limite = tk.Entry(filtros, width=6)
        self.entry_abc_limite.insert(0, "20")
        self.entry_abc_limite.pack(side="left", padx=(0, 12))

        tk.Button(
            filtros,
            text="Gerar curva ABC",
            command=self._gerar_curva_abc,
            bg="#1976D2",
            fg="white",
        ).pack(side="left")

        legenda = tk.Label(
            aba,
            text=(
                "Curva A: produtos que somam até 70% do valor vendido (mais importantes)   "
                "Curva B: até 90%   Curva C: os 10% finais"
            ),
            fg="#777",
            font=("Arial", 9),
            wraplength=760,
            justify="left",
        )
        legenda.pack(anchor="w", pady=(0, 8))

        colunas = ("pos", "produto", "qtd", "valor", "pct", "acumulado", "curva")
        self.tree_abc = ttk.Treeview(aba, columns=colunas, show="headings", height=18)
        titulos = {
            "pos": "#",
            "produto": "Produto",
            "qtd": "Qtd vendida",
            "valor": "Valor total",
            "pct": "% do total",
            "acumulado": "% acumulado",
            "curva": "Curva",
        }
        larguras = {
            "pos": 40,
            "produto": 260,
            "qtd": 100,
            "valor": 110,
            "pct": 90,
            "acumulado": 100,
            "curva": 70,
        }
        for col in colunas:
            self.tree_abc.heading(col, text=titulos[col])
            self.tree_abc.column(
                col, width=larguras[col], anchor="w" if col == "produto" else "center"
            )
        self.tree_abc.pack(fill="both", expand=True)

        self.tree_abc.tag_configure("curva_a", background="#e8f5e9")
        self.tree_abc.tag_configure("curva_b", background="#fff8e1")
        self.tree_abc.tag_configure("curva_c", background="#fbe9e7")

    def _gerar_curva_abc(self):
        try:
            limite = int(self.entry_abc_limite.get().strip())
            if limite <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Relatórios", "Informe um número inteiro maior que zero."
            )
            return

        for row in self.tree_abc.get_children():
            self.tree_abc.delete(row)

        dados = relatorio_curva_abc(limite=limite)
        if not dados:
            messagebox.showinfo(
                "Relatórios",
                "Nenhuma venda concluída encontrada para gerar a curva ABC.",
            )
            return

        for item in dados:
            tag = f"curva_{item['curva'].lower()}"
            self.tree_abc.insert(
                "",
                "end",
                values=(
                    item["posicao"],
                    item["nome_exibicao"],
                    f"{item['total_qtd']:.0f}",
                    f"R$ {item['total_valor']:.2f}",
                    f"{item['pct']:.1f}%",
                    f"{item['acumulado']:.1f}%",
                    item["curva"],
                ),
                tags=(tag,),
            )


def _eh_data_real(data_br: str) -> bool:
    try:
        datetime.strptime(data_br, "%d/%m/%Y")
        return True
    except ValueError:
        return False
