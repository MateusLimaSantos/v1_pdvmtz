import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from core.caixa import (
    caixa_aberto_no_banco,
    abrir_caixa,
    fechar_caixa,
    resumo_fechamento_caixa,
)
from core.pdv import (
    buscar_produto_por_ean,
    adicionar_item_ao_carrinho,
    total_bruto_carrinho,
    formas_pagamento_disponiveis,
    calcular_troco,
    finalizar_venda,
    gerar_qrcode_pix_para_venda,
    produtos_cadastrados_existem,
    registrar_peso,
)
from core.state import state
from config import TIPOS_PESO


class TelaPDV(tk.Frame):
    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.carrinho = []

        self.configurar_layout()
        self.verificar_status_caixa()

    def verificar_status_caixa(self):
        if not produtos_cadastrados_existem():
            self.mostrar_painel_sem_estoque()
            return

        # Verifica se existe algum caixa ativo no estado ou no banco
        caixa_id = caixa_aberto_no_banco()
        if caixa_id:
            state.caixa_id = caixa_id
            self.mostrar_painel_vendas()
        else:
            self.mostrar_painel_abertura()

    def mostrar_painel_sem_estoque(self):
        self.limpar_tela()
        frame = tk.Frame(self, bd=2, relief="groove")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=520, height=300)

        tk.Label(
            frame,
            text="PDV bloqueado: nenhum produto cadastrado",
            font=("Arial", 16, "bold"),
            fg="#b00020",
        ).pack(pady=(28, 12))
        tk.Label(
            frame,
            text=(
                "Cadastre produtos manualmente ou importe um XML de compra "
                "antes de iniciar as vendas."
            ),
            font=("Arial", 11),
            wraplength=430,
            justify="center",
        ).pack(pady=8)
        tk.Button(
            frame,
            text="Cadastrar / ajustar estoque",
            font=("Arial", 11, "bold"),
            bg="#FF9800",
            fg="white",
            command=self.controlador.mostrar_estoque,
        ).pack(fill="x", padx=70, pady=(24, 8))
        tk.Button(
            frame,
            text="Importar XML de compra",
            font=("Arial", 11, "bold"),
            bg="#673AB7",
            fg="white",
            command=self.controlador.mostrar_nfe,
        ).pack(fill="x", padx=70, pady=8)

    def mostrar_painel_abertura(self):
        self.limpar_tela()
        frame_abrir = tk.Frame(self, bd=2, relief="groove")
        frame_abrir.place(relx=0.5, rely=0.5, anchor="center", width=400, height=300)

        tk.Label(
            frame_abrir, text="Caixa Fechado", font=("Arial", 18, "bold"), fg="#f44336"
        ).pack(pady=20)
        tk.Label(
            frame_abrir,
            text="Informe o valor do Fundo de Troco (R$):",
            font=("Arial", 12),
        ).pack(pady=5)

        entry_fundo = tk.Entry(frame_abrir, font=("Arial", 14), justify="center")
        entry_fundo.pack(pady=10)
        entry_fundo.insert(0, "0.00")
        entry_fundo.focus_set()

        def executar_abertura():
            try:
                fundo = float(entry_fundo.get().replace(",", "."))
                sucesso, msg = abrir_caixa(fundo)
                if sucesso:
                    messagebox.showinfo("Sucesso", msg)
                    self.mostrar_painel_vendas()
                else:
                    messagebox.showwarning("Aviso", msg)
            except ValueError:
                messagebox.showerror("Erro", "Insira um valor numérico válido.")

        tk.Button(
            frame_abrir,
            text="Abrir Caixa (F2)",
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            command=executar_abertura,
        ).pack(pady=20, fill="x", padx=40)
        self.bind_all("<F2>", lambda e: executar_abertura())

    def mostrar_painel_vendas(self):
        self.limpar_tela()

        # --- PAINEL ESQUERDO: Carrinho de Compras ---
        frame_esquerdo = tk.Frame(self, bg="#f5f5f5")
        frame_esquerdo.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            frame_esquerdo,
            text="🛒 ITENS NO CARRINHO",
            font=("Arial", 14, "bold"),
            bg="#f5f5f5",
        ).pack(anchor="w", pady=5)

        # Tabela Treeview para listagem do carrinho
        colunas = ("item", "ean", "descricao", "qtd", "preco_un", "total")
        self.tree = ttk.Treeview(
            frame_esquerdo, columns=colunas, show="headings", selectmode="browse"
        )
        self.tree.pack(fill="both", expand=True)

        self.tree.heading("item", text="Item")
        self.tree.heading("ean", text="Código EAN")
        self.tree.heading("descricao", text="Descrição do Produto")
        self.tree.heading("qtd", text="Qtd")
        self.tree.heading("preco_un", text="Preço Un.")
        self.tree.heading("total", text="Total")

        self.tree.column("item", width=50, anchor="center")
        self.tree.column("ean", width=120, anchor="center")
        self.tree.column("descricao", width=250, anchor="w")
        self.tree.column("qtd", width=70, anchor="center")
        self.tree.column("preco_un", width=90, anchor="e")
        self.tree.column("total", width=100, anchor="e")

        # --- PAINEL DIREITO: Entrada de dados e Totais ---
        frame_direito = tk.Frame(self, width=350, bd=1, relief="solid")
        frame_direito.pack(side="right", fill="both", padx=10, pady=10)
        frame_direito.pack_propagate(False)

        # Campo de Entrada EAN
        tk.Label(
            frame_direito, text="Código de Barras (EAN):", font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 2))
        self.entry_ean = tk.Entry(frame_direito, font=("Arial", 16), justify="center")
        self.entry_ean.pack(fill="x", padx=15, pady=5)
        self.entry_ean.bind("<Return>", self.bipar_produto)
        self.entry_ean.focus_set()

        # Display do Total Geral
        tk.Label(
            frame_direito, text="TOTAL GERAL:", font=("Arial", 12, "bold"), fg="#555"
        ).pack(anchor="w", padx=15, pady=(20, 0))
        self.lbl_total = tk.Label(
            frame_direito, text="R$ 0,00", font=("Arial", 28, "bold"), fg="#2e7d32"
        )
        self.lbl_total.pack(anchor="w", padx=15)

        # Seção de Pagamento
        tk.Label(
            frame_direito, text="Forma de Pagamento:", font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=15, pady=(20, 2))
        self.cb_pagamento = ttk.Combobox(
            frame_direito,
            values=formas_pagamento_disponiveis(),
            font=("Arial", 12),
            state="readonly",
        )
        self.cb_pagamento.pack(fill="x", padx=15, pady=5)
        if self.cb_pagamento.cget("values"):
            self.cb_pagamento.current(0)

        tk.Label(
            frame_direito, text="Valor Recebido (R$):", font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 2))
        self.entry_recebido = tk.Entry(
            frame_direito, font=("Arial", 14), justify="right"
        )
        self.entry_recebido.pack(fill="x", padx=15, pady=5)
        self.entry_recebido.insert(0, "0,00")

        # Botões de Ação Básica
        tk.Button(
            frame_direito,
            text="Finalizar Venda (F2)",
            font=("Arial", 12, "bold"),
            bg="#2e7d32",
            fg="white",
            command=self.executar_finalizacao,
        ).pack(fill="x", padx=15, pady=(30, 5))
        tk.Button(
            frame_direito,
            text="Fechar Caixa",
            font=("Arial", 10),
            bg="#cfd8dc",
            command=self.executar_fechamento_caixa,
        ).pack(fill="x", padx=15, pady=5)
        tk.Button(
            frame_direito,
            text="Voltar ao Menu",
            font=("Arial", 10),
            bg="#f44336",
            fg="white",
            command=self.controlador.mostrar_tela_principal,
        ).pack(fill="x", padx=15, pady=5)

    def bipar_produto(self, event=None):
        ean = self.entry_ean.get().strip()
        self.entry_ean.delete(0, tk.END)
        if not ean:
            return

        item_lido = buscar_produto_por_ean(ean)
        if not item_lido:
            messagebox.showerror("Erro", "Produto não encontrado ou Código inválido.")
            return

        # Tratamento de produtos vendidos por Peso/Frações
        if item_lido["tipo_unidade"] in TIPOS_PESO:
            peso_texto = simpledialog.askstring(
                "Produto por Peso",
                f"Informe a quantidade/peso para:\n{item_lido['nome_exibicao']}:",
                parent=self,
            )
            if not peso_texto:
                return
            try:
                peso = float(peso_texto.replace(",", "."))
                sucesso, msg = registrar_peso(item_lido, peso)
                if not sucesso:
                    messagebox.showwarning("Estoque insuficiente", msg)
                    return
                self.carrinho.append(item_lido)
            except ValueError:
                messagebox.showerror("Erro", "Quantidade/Peso inválido.")
                return
        else:
            # Produtos unitários normais
            sucesso, msg = adicionar_item_ao_carrinho(self.carrinho, item_lido)
            if not sucesso:
                messagebox.showwarning("Estoque Insuficiente", msg)
                return

        self.atualizar_visual_carrinho()

    def atualizar_visual_carrinho(self):
        # Limpa as linhas atuais da tabela gráfica
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Remonta a tabela baseando-se no estado atual da lista em memória
        for i, item in enumerate(self.carrinho, 1):
            self.tree.insert(
                "",
                "end",
                values=(
                    i,
                    item["ean_bipado"],
                    item["nome_exibicao"],
                    (
                        f"{item['qtd_desconto']:.3f}"
                        if item["tipo_unidade"] in TIPOS_PESO
                        else f"{int(item['qtd_desconto'])}"
                    ),
                    f"R$ {item['preco_unitario']:.2f}",
                    f"R$ {item['preco_total']:.2f}",
                ),
            )

        total = total_bruto_carrinho(self.carrinho)
        self.lbl_total.config(text=f"R$ {total:.2f}")
        self.entry_recebido.delete(0, tk.END)
        self.entry_recebido.insert(0, f"{total:.2f}")

    def executar_finalizacao(self):
        if not self.carrinho:
            messagebox.showwarning("Aviso", "O carrinho está vazio.")
            return

        forma = self.cb_pagamento.get()
        total_venda = total_bruto_carrinho(self.carrinho)

        try:
            recebido = float(self.entry_recebido.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Informe um valor recebido válido.")
            return

        troco = 0.0

        # Lógica para pagamento em Dinheiro
        if forma == "Dinheiro":
            ok, valor_troco, erro = calcular_troco(total_venda, recebido)
            if not ok:
                messagebox.showerror("Erro", erro)
                return
            troco = valor_troco

        # Lógica para pagamento via PIX
        elif forma == "PIX":
            sucesso_pix, retorno_pix = gerar_qrcode_pix_para_venda(total_venda)
            if not sucesso_pix:
                messagebox.showerror(
                    "Erro PIX", f"Não foi possível gerar o QR Code:\n{retorno_pix}"
                )
                return

            # Abre o PDF automaticamente no leitor padrão do Windows
            try:
                os.startfile(retorno_pix)
            except Exception:
                messagebox.showinfo(
                    "PIX Gerado", f"PDF do PIX gerado em:\n{retorno_pix}"
                )

            # Trava a tela aguardando a confirmação do operador
            confirmacao = messagebox.askyesno(
                "Aguardando Pagamento",
                "O QR Code foi gerado e aberto.\n\nO pagamento foi confirmado no aplicativo do banco?",
            )

            if not confirmacao:
                messagebox.showinfo("Cancelado", "A finalização da venda foi suspensa.")
                return

        # Processamento e persistência fiscal/venda no banco de dados
        sucesso, msg, dados = finalizar_venda(
            self.carrinho, desconto_venda=0.0, forma_pagamento=forma, troco=troco
        )

        if sucesso:
            msg_sucesso = f"{msg}\n\nTroco: R$ {troco:.2f}"
            if dados and dados.get("alertas_estoque"):
                msg_sucesso += "\n\n⚠️ ALERTA: Alguns itens atingiram o estoque mínimo!"

            messagebox.showinfo("Venda Concluída", msg_sucesso)
            self.carrinho = []
            self.atualizar_visual_carrinho()
        else:
            messagebox.showerror("Erro de Processamento", msg)

    def executar_fechamento_caixa(self):
        resumo = resumo_fechamento_caixa()
        if not resumo:
            return

        texto_resumo = (
            f"Resumo Caixa #{resumo['caixa_id']}\n"
            f"Abertura: {resumo['abertura_fmt']}\n"
            f"Fundo Inicial: R$ {resumo['fundo_troco']:.2f}\n"
            f"Qtd Vendas: {resumo['qtd_vendas']}\n"
            f"Total Geral Vendido: R$ {resumo['total_geral']:.2f}\n"
            f"Total Líquido Esperado em Caixa: R$ {resumo['total_em_caixa']:.2f}"
        )

        if messagebox.askyesno(
            "Confirmar Fechamento",
            f"{texto_resumo}\n\nDeseja realmente fechar o caixa corrente?",
        ):
            sucesso, msg = fechar_caixa()
            if sucesso:
                messagebox.showinfo("Caixa Fechado", msg)
                self.verificar_status_caixa()

    def configurar_layout(self):
        self.pack(fill="both", expand=True)

    def limpar_tela(self):
        for widget in self.winfo_children():
            widget.destroy()
