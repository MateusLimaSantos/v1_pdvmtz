import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from backend.core.caixa import (
    caixa_aberto_no_banco,
    abrir_caixa,
    fechar_caixa,
    resumo_fechamento_caixa,
    registrar_sangria,
    registrar_suprimento,
)
from backend.core.pdv import (
    buscar_produto_por_ean,
    adicionar_item_ao_carrinho,
    total_bruto_carrinho,
    formas_pagamento_disponiveis,
    calcular_troco,
    finalizar_venda,
    gerar_qrcode_pix_para_venda,
    produtos_cadastrados_existem,
    registrar_peso,
    remover_item_indice,
    alterar_quantidade_indice,
    calcular_desconto_valor,
)
from backend.core.fiscal.pagamento import (
    iniciar_cobranca,
    confirmar_recebimento_manual,
    consultar_status_cobranca,
    cancelar_cobranca,
)
from backend.core.state import state
from backend.core.helpers import parse_float
from backend.config import TIPOS_PESO


class TelaPDV(tk.Frame):
    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.carrinho = []
        self.desconto_venda_atual = 0.0

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
            if not entry_fundo.winfo_exists():
                return
            fundo = parse_float(entry_fundo.get())
            if fundo is None:
                messagebox.showerror("Erro", "Insira um valor numérico válido.")
                return
            sucesso, msg = abrir_caixa(fundo)
            if sucesso:
                messagebox.showinfo("Sucesso", msg)
                self.mostrar_painel_vendas()
            else:
                messagebox.showwarning("Aviso", msg)

        tk.Button(
            frame_abrir,
            text="Abrir Caixa (F2)",
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            command=executar_abertura,
        ).pack(pady=20, fill="x", padx=40)

        # Atalho F2 escopado a esta tela: usa bind (nao bind_all) e
        # remove o binding quando o frame e destruido, evitando que o
        # callback continue vivo apontando para um widget ja destruido.
        bind_id = self.winfo_toplevel().bind(
            "<F2>", lambda e: executar_abertura()
        )

        def _remover_atalho_f2(_event=None):
            try:
                self.winfo_toplevel().unbind("<F2>", bind_id)
            except tk.TclError:
                pass

        frame_abrir.bind("<Destroy>", _remover_atalho_f2)

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

        frame_caixa_extra = tk.Frame(frame_direito)
        frame_caixa_extra.pack(fill="x", padx=15, pady=5)
        tk.Button(
            frame_caixa_extra,
            text="Sangria (F9)",
            font=("Arial", 10),
            bg="#FFA000",
            fg="white",
            command=self.abrir_modal_sangria,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(
            frame_caixa_extra,
            text="Suprimento",
            font=("Arial", 10),
            bg="#7CB342",
            fg="white",
            command=self.abrir_modal_suprimento,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        tk.Button(
            frame_direito,
            text="Fechar Caixa",
            font=("Arial", 10),
            bg="#cfd8dc",
            command=self.executar_fechamento_caixa,
        ).pack(fill="x", padx=15, pady=5)
        if state.operador and state.operador.get("perfil") == "admin":
            tk.Button(
                frame_direito,
                text="Configurações",
                font=("Arial", 10),
                bg="#455A64",
                fg="white",
                command=self.controlador.mostrar_configuracoes,
            ).pack(fill="x", padx=15, pady=5)
        tk.Button(
            frame_direito,
            text="Voltar ao Menu",
            font=("Arial", 10),
            bg="#f44336",
            fg="white",
            command=self.controlador.mostrar_tela_principal,
        ).pack(fill="x", padx=15, pady=5)

        # Atalhos de teclado da tela de vendas, escopados a esta tela:
        # bind local (nao bind_all) com unbind automatico ao trocar de
        # tela, seguindo o mesmo padrao seguro usado no F2 da abertura
        # de caixa. F2 ja existe no botao "Finalizar Venda" acima.
        mapa_atalhos_pdv = [
            ("<F2>", self.executar_finalizacao),
            ("<F3>", self.cancelar_item_selecionado),
            ("<F4>", self.focar_busca_produto),
            ("<F5>", self.alterar_quantidade_selecionado),
            ("<F6>", self.aplicar_desconto_venda),
            ("<F8>", self._atalho_pix_rapido),
            ("<F9>", self.abrir_modal_sangria),
            ("<F10>", self.executar_fechamento_caixa),
        ]
        bind_ids_pdv = []
        for tecla, callback in mapa_atalhos_pdv:
            bind_id = self.winfo_toplevel().bind(tecla, lambda e, cb=callback: cb())
            bind_ids_pdv.append((tecla, bind_id))

        def _remover_atalhos_pdv(_event=None):
            for tecla, bind_id in bind_ids_pdv:
                try:
                    self.winfo_toplevel().unbind(tecla, bind_id)
                except tk.TclError:
                    pass

        frame_direito.bind("<Destroy>", _remover_atalhos_pdv)

    def cancelar_item_selecionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Cancelar item", "Selecione um item na lista para cancelar.")
            return
        indice = self.tree.index(sel[0])
        ok, resultado = remover_item_indice(self.carrinho, indice)
        if not ok:
            messagebox.showerror("Cancelar item", resultado)
            return
        self.atualizar_visual_carrinho()
        messagebox.showinfo("Item cancelado", f"'{resultado}' removido do carrinho.")

    def alterar_quantidade_selecionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Alterar quantidade", "Selecione um item na lista.")
            return
        indice = self.tree.index(sel[0])
        item = self.carrinho[indice]

        nova_qtd_texto = simpledialog.askstring(
            "Alterar quantidade",
            f"Nova quantidade para:\n{item['nome_exibicao']}",
            initialvalue=str(item["qtd_desconto"]),
            parent=self,
        )
        if not nova_qtd_texto:
            return
        nova_qtd = parse_float(nova_qtd_texto)
        if nova_qtd is None:
            messagebox.showerror("Alterar quantidade", "Quantidade inválida.")
            return

        ok, msg = alterar_quantidade_indice(self.carrinho, indice, nova_qtd)
        if not ok:
            messagebox.showerror("Alterar quantidade", msg)
            return
        self.atualizar_visual_carrinho()

    def aplicar_desconto_venda(self):
        if not self.carrinho:
            messagebox.showwarning("Desconto", "O carrinho está vazio.")
            return
        total_atual = total_bruto_carrinho(self.carrinho)
        valor_texto = simpledialog.askstring(
            "Aplicar desconto",
            f"Total atual: R$ {total_atual:.2f}\nValor do desconto (R$):",
            parent=self,
        )
        if not valor_texto:
            return
        valor_desconto = parse_float(valor_texto)
        if valor_desconto is None or valor_desconto <= 0:
            messagebox.showerror("Desconto", "Informe um valor de desconto válido.")
            return

        ok, valor_aplicado, erro = calcular_desconto_valor(total_atual, valor_desconto)
        if not ok:
            messagebox.showerror("Desconto", erro)
            return

        self.desconto_venda_atual = valor_aplicado
        self.atualizar_visual_carrinho()
        messagebox.showinfo("Desconto aplicado", f"Desconto de R$ {valor_aplicado:.2f} aplicado à venda.")

    def focar_busca_produto(self):
        if self.entry_ean.winfo_exists():
            self.entry_ean.focus_set()

    def _atalho_pix_rapido(self):
        """F8: atalho rápido para selecionar PIX como forma de pagamento
        e já finalizar a venda, espelhando o atalho F8 do plano original
        ('pagamento PIX')."""
        if not self.cb_pagamento.winfo_exists():
            return
        self.cb_pagamento.set("PIX")
        self.executar_finalizacao()

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
            peso = parse_float(peso_texto)
            if peso is None or peso <= 0:
                messagebox.showerror("Erro", "Quantidade/Peso inválido.")
                return
            sucesso, msg = registrar_peso(item_lido, peso)
            if not sucesso:
                messagebox.showwarning("Estoque insuficiente", msg)
                return
            self.carrinho.append(item_lido)
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

        total_bruto = total_bruto_carrinho(self.carrinho)
        total_liquido = round(total_bruto - self.desconto_venda_atual, 2)
        if self.desconto_venda_atual > 0:
            self.lbl_total.config(text=f"R$ {total_liquido:.2f}  (desconto: -R$ {self.desconto_venda_atual:.2f})")
        else:
            self.lbl_total.config(text=f"R$ {total_liquido:.2f}")
        self.entry_recebido.delete(0, tk.END)
        self.entry_recebido.insert(0, f"{total_liquido:.2f}")

    def _acompanhar_pix_automatico(self, resultado_pix: dict) -> bool:
        """
        Mostra o QR dinâmico do gateway e faz polling não-bloqueante
        (via widget.after, sem travar a interface) até o pagamento ser
        aprovado, rejeitado, ou o operador cancelar. Retorna True se
        aprovado (a venda deve seguir), False caso contrário.
        """
        referencia = resultado_pix["referencia"]
        janela = tk.Toplevel(self)
        janela.title("Pagamento PIX automático")
        janela.geometry("380x420")
        janela.transient(self.winfo_toplevel())
        janela.grab_set()
        janela.protocol("WM_DELETE_WINDOW", lambda: None)  # fecha só pelo botão Cancelar

        tk.Label(
            janela, text="Aguardando pagamento via PIX", font=("Arial", 13, "bold")
        ).pack(pady=(16, 8))

        if resultado_pix.get("qr_code_base64"):
            try:
                import base64
                from io import BytesIO
                from PIL import Image, ImageTk

                dados_img = base64.b64decode(resultado_pix["qr_code_base64"])
                img = Image.open(BytesIO(dados_img)).resize((220, 220))
                foto = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(janela, image=foto)
                lbl_img.image = foto  # mantém referência viva
                lbl_img.pack(pady=8)
            except Exception:
                tk.Label(janela, text="(QR Code indisponível para exibição)", fg="#777").pack(pady=8)

        tk.Label(janela, text="Ou copie o código Pix:", font=("Arial", 9)).pack(pady=(8, 2))
        entry_copia_cola = tk.Entry(janela, justify="center")
        entry_copia_cola.insert(0, resultado_pix.get("qr_code", ""))
        entry_copia_cola.config(state="readonly")
        entry_copia_cola.pack(fill="x", padx=20)

        lbl_status = tk.Label(janela, text="Aguardando confirmação...", fg="#1976D2")
        lbl_status.pack(pady=12)

        resultado_final = {"aprovado": False, "encerrado": False}

        def cancelar():
            resultado_final["encerrado"] = True
            cancelar_cobranca(referencia)
            janela.destroy()

        tk.Button(
            janela, text="Cancelar e usar outra forma de pagamento", command=cancelar, bg="#b00020", fg="white"
        ).pack(pady=(8, 16), fill="x", padx=20)

        def verificar():
            if resultado_final["encerrado"]:
                return
            ok, status = consultar_status_cobranca(referencia)
            if ok and status == "aprovado":
                resultado_final["aprovado"] = True
                resultado_final["encerrado"] = True
                lbl_status.config(text="Pagamento aprovado!", fg="#2e7d32")
                janela.after(600, janela.destroy)
                return
            if ok and status in ("erro", "cancelado"):
                resultado_final["encerrado"] = True
                lbl_status.config(text=f"Pagamento {status}.", fg="#b00020")
                janela.after(1500, janela.destroy)
                return
            if not ok:
                lbl_status.config(text=f"Verificando... ({status})", fg="#8a5a00")
            janela.after(3000, verificar)

        janela.after(1000, verificar)
        self.wait_window(janela)
        return resultado_final["aprovado"]

    def executar_finalizacao(self):
        if not self.carrinho:
            messagebox.showwarning("Aviso", "O carrinho está vazio.")
            return

        forma = self.cb_pagamento.get()
        total_bruto = total_bruto_carrinho(self.carrinho)
        total_venda = round(total_bruto - self.desconto_venda_atual, 2)

        recebido = parse_float(self.entry_recebido.get())
        if recebido is None:
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

        # Lógica para pagamento via PIX — usa o orquestrador, que decide
        # entre manual / automático / híbrido conforme configurado.
        elif forma == "PIX":
            resultado_pix = iniciar_cobranca(total_venda, f"Venda PDV - R$ {total_venda:.2f}")

            if resultado_pix["modo_efetivo"] == "automatico" and resultado_pix["sucesso"]:
                confirmado = self._acompanhar_pix_automatico(resultado_pix)
                if not confirmado:
                    return
            elif resultado_pix["modo_efetivo"] == "automatico" and not resultado_pix["sucesso"]:
                # Modo automático puro (sem híbrido) e o gateway falhou: não há
                # contingência configurada, então a falha é exposta ao caixa.
                messagebox.showerror(
                    "Erro PIX",
                    "Não foi possível gerar a cobrança automática:\n"
                    f"{resultado_pix.get('motivo', '')}\n\n"
                    "Configure o modo Híbrido para ter contingência automática, "
                    "ou escolha outra forma de pagamento.",
                )
                return
            else:
                # Manual nativo OU contingência do híbrido — mesma UX para o caixa.
                if not resultado_pix["sucesso"]:
                    messagebox.showerror(
                        "Erro PIX", f"Não foi possível gerar o QR Code:\n{resultado_pix.get('motivo', '')}"
                    )
                    return

                if resultado_pix.get("contingencia"):
                    messagebox.showwarning(
                        "Conexão automática indisponível",
                        "Não foi possível confirmar a cobrança automática agora "
                        f"({resultado_pix.get('motivo_contingencia', 'motivo não informado')}).\n\n"
                        "Gerando Pix manual para conferência do caixa.",
                    )

                pdf_path = resultado_pix["pdf_path"]
                try:
                    os.startfile(pdf_path)
                except Exception:
                    messagebox.showinfo("PIX Gerado", f"PDF do PIX gerado em:\n{pdf_path}")

                confirmacao = messagebox.askyesno(
                    "Aguardando Pagamento",
                    "O QR Code foi gerado e aberto.\n\nO pagamento foi confirmado no aplicativo do banco?",
                )
                if not confirmacao:
                    cancelar_cobranca(resultado_pix["referencia"])
                    messagebox.showinfo("Cancelado", "A finalização da venda foi suspensa.")
                    return
                confirmar_recebimento_manual(resultado_pix["referencia"])

        # Processamento e persistência fiscal/venda no banco de dados
        sucesso, msg, dados = finalizar_venda(
            self.carrinho, desconto_venda=self.desconto_venda_atual, forma_pagamento=forma, troco=troco
        )

        if sucesso:
            msg_sucesso = f"{msg}\n\nTroco: R$ {troco:.2f}"
            if dados and dados.get("alertas_estoque"):
                msg_sucesso += "\n\n⚠️ ALERTA: Alguns itens atingiram o estoque mínimo!"

            messagebox.showinfo("Venda Concluída", msg_sucesso)
            self.carrinho = []
            self.desconto_venda_atual = 0.0
            self.atualizar_visual_carrinho()
        else:
            messagebox.showerror("Erro de Processamento", msg)

    def abrir_modal_sangria(self):
        self._abrir_modal_movimentacao_caixa(
            titulo="Sangria de Caixa",
            cor="#FFA000",
            funcao_registro=registrar_sangria,
        )

    def abrir_modal_suprimento(self):
        self._abrir_modal_movimentacao_caixa(
            titulo="Suprimento de Caixa",
            cor="#7CB342",
            funcao_registro=registrar_suprimento,
        )

    def _abrir_modal_movimentacao_caixa(self, titulo: str, cor: str, funcao_registro):
        if not state.caixa_id:
            messagebox.showwarning("Aviso", "Nenhum caixa aberto.")
            return

        janela = tk.Toplevel(self)
        janela.title(titulo)
        janela.geometry("380x260")
        janela.transient(self.winfo_toplevel())
        janela.grab_set()

        tk.Label(janela, text=titulo, font=("Arial", 14, "bold"), fg=cor).pack(pady=(16, 10))

        tk.Label(janela, text="Valor (R$):", font=("Arial", 11)).pack(anchor="w", padx=20)
        entry_valor = tk.Entry(janela, font=("Arial", 13), justify="center")
        entry_valor.pack(fill="x", padx=20, pady=(2, 10))
        entry_valor.focus_set()

        tk.Label(janela, text="Motivo:", font=("Arial", 11)).pack(anchor="w", padx=20)
        entry_motivo = tk.Entry(janela, font=("Arial", 11))
        entry_motivo.pack(fill="x", padx=20, pady=(2, 16))

        def confirmar():
            valor = parse_float(entry_valor.get())
            if valor is None:
                messagebox.showerror("Erro", "Informe um valor numérico válido.")
                return
            motivo = entry_motivo.get().strip()
            sucesso, msg = funcao_registro(valor, motivo)
            if not sucesso:
                messagebox.showerror("Erro", msg)
                return
            messagebox.showinfo("Sucesso", msg)
            janela.destroy()

        tk.Button(
            janela,
            text="Confirmar",
            font=("Arial", 11, "bold"),
            bg=cor,
            fg="white",
            command=confirmar,
        ).pack(fill="x", padx=20, pady=(0, 6))
        tk.Button(janela, text="Cancelar", command=janela.destroy).pack(fill="x", padx=20)

        janela.bind("<Return>", lambda e: confirmar())

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
            f"Sangrias: R$ {resumo['total_sangrias']:.2f}\n"
            f"Suprimentos: R$ {resumo['total_suprimentos']:.2f}\n"
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
