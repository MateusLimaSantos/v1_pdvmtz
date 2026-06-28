import os
import platform
import subprocess
import tkinter as tk
from tkinter import (
    ttk,
    messagebox,
    simpledialog,
    scrolledtext,
)  # <-- Adicione o scrolledtext

from backend.core.historico import listar_vendas, detalhes_venda
from backend.core.pdv import cancelar_venda
from backend.core.state import state

# IMPORTANTE: Ajuste o caminho de importação abaixo conforme a estrutura de pastas do seu projeto
from backend.core.fiscal.cupom import formatar_cupom, exportar_pdf_cupom


class TelaHistorico(tk.Frame):
    """Tela de historico de vendas, com filtro por data/status e detalhe por item."""

    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.pack(fill="both", expand=True, padx=12, pady=12)

        self.configurar_layout()
        self.carregar_dados()

    def _mostrar_cupom(self, venda: dict):
        # 1. Adaptar as chaves do dicionário para a função formatar_cupom
        # O banco de dados traz "nome_exibicao", mas o cupom espera "nome"
        itens_cupom = []
        for item in venda["itens"]:
            itens_cupom.append(
                {
                    "nome": item.get("nome_exibicao", "Produto"),
                    "qtd": item["qtd"],
                    "preco_total": item["preco_total"],
                    "tipo_unidade": item.get("tipo_unidade", "unidade"),
                    "desconto_item": item.get("desconto_item", 0.0),
                }
            )

        # 2. Gerar o texto do cupom usando sua função existente
        texto_cupom, _ = formatar_cupom(
            itens=itens_cupom,
            total=venda["total"],
            desconto_venda=venda.get("desconto", 0.0),
            forma_pagamento=venda.get("forma_pagamento", "N/A"),
            troco=venda.get("troco", 0.0),
        )

        # 3. Criar uma nova janela para exibir o texto do cupom
        janela_cupom = tk.Toplevel(self)
        janela_cupom.title(f"Nota Fiscal - Venda #{venda['id']}")
        janela_cupom.geometry("350x550")

        # Área de texto com barra de rolagem (somente leitura)
        txt = scrolledtext.ScrolledText(janela_cupom, font=("Courier", 9))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", texto_cupom)
        txt.config(state="disabled")

        # 4. Função interna para exportar e abrir o PDF automaticamente
        def abrir_pdf():
            try:
                caminho_arq = exportar_pdf_cupom(texto_cupom, venda["id"])

                # Descobre o Sistema Operacional e abre o arquivo no leitor padrão
                if platform.system() == "Windows":
                    os.startfile(caminho_arq)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.call(["open", caminho_arq])
                else:  # Linux
                    subprocess.call(["xdg-open", caminho_arq])

            except Exception as e:
                messagebox.showerror(
                    "Erro ao abrir PDF",
                    f"O PDF foi gerado, mas não pôde ser aberto automaticamente.\nErro: {e}",
                    parent=janela_cupom,
                )

        tk.Button(
            janela_cupom,
            text="Gerar e Abrir PDF",
            command=abrir_pdf,
            bg="#388E3C",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(pady=(0, 10))

    def configurar_layout(self):
        topo = tk.Frame(self)
        topo.pack(fill="x", pady=(0, 10))
        tk.Label(
            topo,
            text="Histórico de Vendas",
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

        tk.Label(filtros, text="Data início (dd/mm/aaaa):").pack(
            side="left", padx=(0, 4)
        )
        self.entry_data_ini = tk.Entry(filtros, width=12)
        self.entry_data_ini.pack(side="left", padx=(0, 12))

        tk.Label(filtros, text="Data fim (dd/mm/aaaa):").pack(side="left", padx=(0, 4))
        self.entry_data_fim = tk.Entry(filtros, width=12)
        self.entry_data_fim.pack(side="left", padx=(0, 12))

        tk.Label(filtros, text="Status:").pack(side="left", padx=(0, 4))
        self.var_status = tk.StringVar(value="todos")
        combo_status = ttk.Combobox(
            filtros,
            textvariable=self.var_status,
            values=("todos", "concluida", "cancelada"),
            state="readonly",
            width=12,
        )
        combo_status.pack(side="left", padx=(0, 12))

        tk.Button(
            filtros,
            text="Filtrar",
            command=self.carregar_dados,
            bg="#1976D2",
            fg="white",
        ).pack(side="left", padx=(0, 8))
        tk.Button(filtros, text="Limpar filtros", command=self._limpar_filtros).pack(
            side="left"
        )

        colunas = ("id", "data", "operador", "total", "pagamento", "status")
        self.tree = ttk.Treeview(self, columns=colunas, show="headings", height=16)
        titulos = {
            "id": "Venda",
            "data": "Data/Hora",
            "operador": "Operador",
            "total": "Total",
            "pagamento": "Pagamento",
            "status": "Status",
        }
        larguras = {
            "id": 70,
            "data": 150,
            "operador": 160,
            "total": 100,
            "pagamento": 120,
            "status": 110,
        }
        for col in colunas:
            self.tree.heading(col, text=titulos[col])
            self.tree.column(
                col, width=larguras[col], anchor="center" if col != "operador" else "w"
            )
        self.tree.pack(fill="both", expand=True, pady=(0, 10))
        self.tree.bind("<Double-1>", lambda e: self._abrir_detalhes())

        frame_botoes_lista = tk.Frame(self)
        frame_botoes_lista.pack(fill="x")
        tk.Button(
            frame_botoes_lista,
            text="Ver detalhes da venda selecionada",
            command=self._abrir_detalhes,
            bg="#455A64",
            fg="white",
        ).pack(side="right")
        if state.operador and state.operador.get("perfil") == "admin":
            tk.Button(
                frame_botoes_lista,
                text="Cancelar venda selecionada",
                command=self._cancelar_venda_selecionada,
                bg="#b00020",
                fg="white",
            ).pack(side="right", padx=(0, 8))

    def _limpar_filtros(self):
        self.entry_data_ini.delete(0, "end")
        self.entry_data_fim.delete(0, "end")
        self.var_status.set("todos")
        self.carregar_dados()

    def carregar_dados(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        status = self.var_status.get()
        status_filtro = None if status == "todos" else status

        vendas = listar_vendas(
            limite=200,
            data_ini_br=self.entry_data_ini.get().strip() or None,
            data_fim_br=self.entry_data_fim.get().strip() or None,
            status=status_filtro,
        )
        for v in vendas:
            self.tree.insert(
                "",
                "end",
                iid=str(v["id"]),
                values=(
                    v["id"],
                    v["data_hora_fmt"],
                    v["operador_nome"],
                    f"R$ {v['total']:.2f}",
                    v["forma_pagamento"],
                    "Cancelada" if v["status"] == "cancelada" else "Concluída",
                ),
            )

    def _cancelar_venda_selecionada(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Histórico", "Selecione uma venda na lista.")
            return
        venda_id = int(sel[0])
        valores = self.tree.item(sel[0], "values")
        status_atual = valores[5]
        if status_atual == "Cancelada":
            messagebox.showinfo("Histórico", "Esta venda já está cancelada.")
            return

        if not messagebox.askyesno(
            "Confirmar cancelamento",
            f"Cancelar a venda #{venda_id}?\n\n"
            "O estoque dos itens será restaurado automaticamente. "
            "Esta ação não pode ser desfeita.",
        ):
            return

        motivo = simpledialog.askstring(
            "Motivo do cancelamento",
            "Informe o motivo do cancelamento:",
            parent=self,
        )
        if not motivo or not motivo.strip():
            messagebox.showwarning(
                "Histórico", "O cancelamento requer um motivo. Operação não realizada."
            )
            return

        sucesso, msg = cancelar_venda(venda_id, motivo)
        if not sucesso:
            messagebox.showerror("Histórico", msg)
            return
        messagebox.showinfo("Histórico", msg)
        self.carregar_dados()

    def _abrir_detalhes(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Histórico", "Selecione uma venda na lista.")
            return
        venda_id = int(sel[0])
        venda = detalhes_venda(venda_id)
        if not venda:
            messagebox.showerror("Histórico", f"Venda #{venda_id} não encontrada.")
            return
        self._mostrar_janela_detalhes(venda)

    def _mostrar_janela_detalhes(self, venda: dict):
        janela = tk.Toplevel(self)
        janela.title(f"Venda #{venda['id']}")
        janela.geometry("520x480")

        tk.Label(
            janela,
            text=f"Venda #{venda['id']} — {venda['data_hora_fmt']}",
            font=("Arial", 14, "bold"),
        ).pack(pady=(12, 4))
        tk.Label(janela, text=f"Operador: {venda['operador_nome']}").pack()
        tk.Label(janela, text=f"Forma de pagamento: {venda['forma_pagamento']}").pack()
        if venda["status"] == "cancelada":
            tk.Label(
                janela,
                text=f"CANCELADA — Motivo: {venda.get('motivo_cancelamento') or 'não informado'}",
                fg="#b00020",
                font=("Arial", 10, "bold"),
            ).pack(pady=4)

        colunas = ("produto", "qtd", "unitario", "total")
        tree_itens = ttk.Treeview(janela, columns=colunas, show="headings", height=12)
        titulos = {
            "produto": "Produto",
            "qtd": "Qtd",
            "unitario": "Unit.",
            "total": "Total",
        }
        larguras = {"produto": 220, "qtd": 80, "unitario": 90, "total": 90}
        for col in colunas:
            tree_itens.heading(col, text=titulos[col])
            tree_itens.column(
                col, width=larguras[col], anchor="center" if col != "produto" else "w"
            )
        tree_itens.pack(fill="both", expand=True, padx=12, pady=10)

        for item in venda["itens"]:
            tree_itens.insert(
                "",
                "end",
                values=(
                    item["nome_exibicao"],
                    item["qtd_fmt"],
                    f"R$ {item['preco_unitario']:.2f}",
                    f"R$ {item['preco_total']:.2f}",
                ),
            )

        tk.Label(
            janela,
            text=f"Total da venda: R$ {venda['total']:.2f}    Desconto: R$ {venda['desconto']:.2f}",
            font=("Arial", 11, "bold"),
        ).pack(pady=(0, 12))

        frame_rodape = tk.Frame(janela)
        frame_rodape.pack(pady=(0, 12))

        tk.Button(
            frame_rodape,
            text="Ver Nota Fiscal",
            command=lambda: self._mostrar_cupom(venda),
            bg="#1976D2",
            fg="white",
        ).pack(side="left", padx=(0, 8))

        if (
            venda["status"] != "cancelada"
            and state.operador
            and state.operador.get("perfil") == "admin"
        ):

            def cancelar_e_fechar():
                janela.destroy()
                self.tree.selection_set(str(venda["id"]))
                self._cancelar_venda_selecionada()

            tk.Button(
                frame_rodape,
                text="Cancelar esta venda",
                command=cancelar_e_fechar,
                bg="#b00020",
                fg="white",
            ).pack(side="left", padx=(0, 8))

        tk.Button(frame_rodape, text="Fechar", command=janela.destroy).pack(side="left")
