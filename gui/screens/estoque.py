import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from backend.core.estoque import buscar_produtos, adicionar_produto, ajustar_estoque
from backend.config import TIPOS_UNIDADE_VALIDOS


class TelaEstoque(tk.Frame):
    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app

        self.configurar_layout()
        self.carregar_dados()

    def configurar_layout(self):
        self.pack(fill="both", expand=True, padx=10, pady=10)

        # --- BARRA SUPERIOR: Pesquisa e Filtros ---
        frame_topo = tk.Frame(self)
        frame_topo.pack(fill="x", pady=(0, 10))

        tk.Label(
            frame_topo, text="Pesquisar Produto (Nome/EAN):", font=("Arial", 11)
        ).pack(side="left", padx=5)
        self.entry_busca = tk.Entry(frame_topo, font=("Arial", 11), width=35)
        self.entry_busca.pack(side="left", padx=5)
        self.entry_busca.bind("<KeyRelease>", lambda e: self.carregar_dados())

        tk.Button(
            frame_topo, text="🔄 Atualizar", bg="#e0e0e0", command=self.carregar_dados
        ).pack(side="left", padx=10)
        tk.Button(
            frame_topo,
            text="➕ Novo Produto",
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.abrir_popup_cadastro,
        ).pack(side="right", padx=5)
        tk.Button(
            frame_topo,
            text="🔧 Ajustar Estoque",
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.abrir_popup_ajuste,
        ).pack(side="right", padx=5)

        # --- GRID DE EXIBIÇÃO: Tabela de Itens ---
        colunas = ("ean", "nome", "unidade", "preco", "estoque", "minimo")
        self.tree = ttk.Treeview(
            self, columns=colunas, show="headings", selectmode="browse"
        )
        self.tree.pack(fill="both", expand=True)

        self.tree.heading("ean", text="Código EAN")
        self.tree.heading("nome", text="Nome do Produto")
        self.tree.heading("unidade", text="Unidade")
        self.tree.heading("preco", text="Preço Venda")
        self.tree.heading("estoque", text="Qtd Estoque")
        self.tree.heading("minimo", text="Estoque Mín.")

        self.tree.column("ean", width=130, anchor="center")
        self.tree.column("nome", width=300, anchor="w")
        self.tree.column("unidade", width=90, anchor="center")
        self.tree.column("preco", width=100, anchor="e")
        self.tree.column("estoque", width=100, anchor="center")
        self.tree.column("minimo", width=100, anchor="center")

        # Botão de saída na parte inferior
        tk.Button(
            self,
            text="Voltar ao Menu Principal",
            font=("Arial", 11),
            bg="#f44336",
            fg="white",
            command=self.controlador.mostrar_tela_principal,
        ).pack(fill="x", pady=(10, 0))

    def carregar_dados(self):
        # Limpa linhas antigas
        for r in self.tree.get_children():
            self.tree.delete(r)

        termo = self.entry_busca.get()
        produtos = buscar_produtos(termo)

        for p in produtos:
            self.tree.insert(
                "",
                "end",
                values=(
                    p["ean"],
                    p["nome"],
                    p["tipo_unidade"],
                    f"R$ {p['preco_venda']:.2f}",
                    f"{p['estoque_atual']:.3f}",
                    f"{p['estoque_minimo']:.3f}",
                ),
            )

    def abrir_popup_ajuste(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning(
                "Aviso", "Selecione um produto na tabela para ajustar."
            )
            return

        item = self.tree.item(selecionado)["values"]
        ean = item[0]
        nome = item[1]

        qtd_texto = simpledialog.askstring(
            "Ajuste de Estoque",
            f"Produto: {nome}\nDigite a quantidade a alterar:\n(Use valores positivos para ENTRADAS e negativos para SAÍDAS):",
        )
        if not qtd_texto:
            return

        motivo = simpledialog.askstring(
            "Ajuste de Estoque", "Informe o motivo/justificativa do ajuste:"
        )
        if not motivo:
            return

        try:
            qtd = float(qtd_texto.replace(",", "."))
            sucesso, msg = ajustar_estoque(ean, qtd, motivo)
            if sucesso:
                messagebox.showinfo("Sucesso", msg)
                self.carregar_dados()
            else:
                messagebox.showerror("Erro", msg)
        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida.")

    def abrir_popup_cadastro(self):
        # Criação de uma subjanela modal para preenchimento dos campos do novo produto
        top = tk.Toplevel(self)
        top.title("Cadastrar Novo Produto")
        top.geometry("450x450")
        top.resizable(False, False)
        top.grab_set()  # Bloqueia interação com a tela de fundo

        frame = tk.Frame(top, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        campos = [
            ("Código EAN:", "ean"),
            ("Nome do Produto:", "nome"),
            ("Descrição Opcional:", "desc"),
            ("Preço de Venda (R$):", "preco"),
            ("Estoque Inicial:", "estoque"),
            ("Estoque Mínimo:", "minimo"),
        ]

        entries = {}
        for row, (label_text, key) in enumerate(campos):
            tk.Label(frame, text=label_text, font=("Arial", 10)).grid(
                row=row, column=0, sticky="w", pady=5
            )
            entries[key] = tk.Entry(frame, font=("Arial", 10), width=30)
            entries[key].grid(row=row, column=1, pady=5, padx=5)

        # Tipo de unidade combobox
        tk.Label(frame, text="Tipo de Unidade:", font=("Arial", 10)).grid(
            row=len(campos), column=0, sticky="w", pady=5
        )
        cb_unidade = ttk.Combobox(
            frame,
            values=TIPOS_UNIDADE_VALIDOS,
            font=("Arial", 10),
            state="readonly",
            width=28,
        )
        cb_unidade.grid(row=len(campos), column=1, pady=5, padx=5)
        cb_unidade.current(0)

        def salvar_novo_produto():
            try:
                ean = entries["ean"].get().strip()
                nome = entries["nome"].get().strip()
                desc = entries["desc"].get().strip()
                preco = float(entries["preco"].get().replace(",", "."))
                est_ini = float(entries["estoque"].get().replace(",", "."))
                est_min = float(entries["minimo"].get().replace(",", "."))
                unidade = cb_unidade.get()

                if not ean or not nome:
                    messagebox.showwarning(
                        "Aviso", "Campos EAN e Nome são obrigatórios."
                    )
                    return

                sucesso, msg = adicionar_produto(
                    ean, nome, desc, unidade, est_ini, est_min, preco
                )
                if sucesso:
                    messagebox.showinfo("Sucesso", msg)
                    top.destroy()
                    self.carregar_dados()
                else:
                    messagebox.showerror("Erro", msg)

            except ValueError:
                messagebox.showerror(
                    "Erro",
                    "Verifique se os campos de Preço e Estoque possuem formatos numéricos válidos.",
                )

        tk.Button(
            frame,
            text="Gravar Produto",
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            command=salvar_novo_produto,
        ).grid(row=len(campos) + 1, column=0, columnspan=2, pady=25, sticky="ew")
