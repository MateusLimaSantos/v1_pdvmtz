import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.relatorios import relatorio_vendas_mensal


class TelaGraficos(tk.Frame):
    """Tela de gráficos: evolução de vendas mês a mês."""

    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.pack(fill="both", expand=True, padx=12, pady=12)

        self.canvas = None
        self.configurar_layout()
        self.atualizar_grafico()

    def configurar_layout(self):
        topo = tk.Frame(self)
        topo.pack(fill="x", pady=(0, 10))
        tk.Label(
            topo,
            text="Gráficos de Vendas",
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

        tk.Label(filtros, text="Período:").pack(side="left", padx=(0, 6))
        self.var_periodo = tk.StringVar(value="12 meses")
        combo = ttk.Combobox(
            filtros,
            textvariable=self.var_periodo,
            values=("3 meses", "6 meses", "12 meses", "24 meses"),
            state="readonly",
            width=12,
        )
        combo.pack(side="left", padx=(0, 10))
        combo.bind("<<ComboboxSelected>>", lambda e: self.atualizar_grafico())

        tk.Label(filtros, text="Tipo:").pack(side="left", padx=(0, 6))
        self.var_tipo = tk.StringVar(value="Valor vendido (R$)")
        combo_tipo = ttk.Combobox(
            filtros,
            textvariable=self.var_tipo,
            values=("Valor vendido (R$)", "Quantidade de vendas"),
            state="readonly",
            width=20,
        )
        combo_tipo.pack(side="left", padx=(0, 10))
        combo_tipo.bind("<<ComboboxSelected>>", lambda e: self.atualizar_grafico())

        tk.Button(
            filtros, text="Atualizar", command=self.atualizar_grafico, bg="#1976D2", fg="white"
        ).pack(side="left")

        self.frame_grafico = tk.Frame(self)
        self.frame_grafico.pack(fill="both", expand=True)

        self.lbl_resumo = tk.Label(self, text="", font=("Arial", 10, "bold"), fg="#333")
        self.lbl_resumo.pack(anchor="w", pady=(6, 0))

    def _qtd_meses(self) -> int:
        texto = self.var_periodo.get()
        return int(texto.split()[0])

    def atualizar_grafico(self):
        dados = relatorio_vendas_mensal(meses=self._qtd_meses())

        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        for w in self.frame_grafico.winfo_children():
            w.destroy()

        rotulos = [d["rotulo"] for d in dados]
        usar_valor = self.var_tipo.get() == "Valor vendido (R$)"
        valores = [d["total_vendido"] if usar_valor else d["qtd_vendas"] for d in dados]

        fig = Figure(figsize=(8, 4.2), dpi=100)
        ax = fig.add_subplot(111)

        cores = ["#1976D2" if v > 0 else "#cfd8dc" for v in valores]
        ax.bar(rotulos, valores, color=cores)

        ax.set_title(
            "Vendas por mês — " + ("Valor (R$)" if usar_valor else "Quantidade de vendas"),
            fontsize=12,
        )
        ax.set_ylabel("R$" if usar_valor else "Qtd. vendas")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(fig, master=self.frame_grafico)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        total_periodo = sum(d["total_vendido"] for d in dados)
        qtd_total = sum(d["qtd_vendas"] for d in dados)
        media_mensal = total_periodo / len(dados) if dados else 0.0
        self.lbl_resumo.config(
            text=(
                f"Total no período: R$ {total_periodo:.2f}  |  "
                f"Vendas: {qtd_total}  |  "
                f"Média mensal: R$ {media_mensal:.2f}"
            )
        )
