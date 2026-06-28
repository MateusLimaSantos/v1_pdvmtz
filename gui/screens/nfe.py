import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from backend.core.fiscal.sefaz import carregar_xml_de_arquivo, preparar_entrada_itens, dar_entrada_itens

class TelaNFe(tk.Frame):
    def __init__(self, parent, controlador_app):
        super().__init__(parent)
        self.controlador = controlador_app
        self.itens_carregados = []
        
        self.configurar_layout()

    def configurar_layout(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho
        tk.Label(self, text="📥 Importação de NF-e (XML)", font=("Arial", 18, "bold"), fg="#333").pack(anchor="w", pady=(0, 20))

        # Barra de Ações
        frame_acoes = tk.Frame(self)
        frame_acoes.pack(fill="x", pady=(0, 15))

        tk.Button(frame_acoes, text="📁 Buscar Arquivo XML", font=("Arial", 11, "bold"), bg="#2196F3", fg="white", command=self.selecionar_arquivo).pack(side="left", padx=(0, 10))
        self.lbl_arquivo = tk.Label(frame_acoes, text="Nenhum arquivo selecionado", font=("Arial", 10), fg="#666")
        self.lbl_arquivo.pack(side="left")

        # Tabela de Pré-visualização
        colunas = ("ean", "nome", "qtd", "preco", "status")
        self.tree = ttk.Treeview(self, columns=colunas, show="headings", height=15)
        self.tree.pack(fill="both", expand=True)

        self.tree.heading("ean", text="EAN")
        self.tree.heading("nome", text="Nome do Produto")
        self.tree.heading("qtd", text="Qtd")
        self.tree.heading("preco", text="Preço Un.")
        self.tree.heading("status", text="Status no Estoque")

        self.tree.column("ean", width=120, anchor="center")
        self.tree.column("nome", width=350, anchor="w")
        self.tree.column("qtd", width=80, anchor="center")
        self.tree.column("preco", width=100, anchor="e")
        self.tree.column("status", width=150, anchor="center")

        # Rodapé com Botões de Confirmação
        frame_rodape = tk.Frame(self)
        frame_rodape.pack(fill="x", pady=(20, 0))

        self.var_cadastrar_novos = tk.BooleanVar(value=False)
        tk.Checkbutton(frame_rodape, text="Cadastrar novos produtos automaticamente", variable=self.var_cadastrar_novos, font=("Arial", 11)).pack(side="left")

        tk.Button(frame_rodape, text="Cancelar / Voltar", font=("Arial", 11), bg="#f44336", fg="white", command=self.controlador.mostrar_tela_principal).pack(side="right", padx=(10, 0))
        self.btn_importar = tk.Button(frame_rodape, text="Gravar no Banco de Dados", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", state="disabled", command=self.efetivar_importacao)
        self.btn_importar.pack(side="right")

    def selecionar_arquivo(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo XML da NF-e",
            filetypes=[("Arquivos XML", "*.xml"), ("Todos os Arquivos", "*.*")]
        )
        if not caminho:
            return

        self.lbl_arquivo.config(text=caminho.split("/")[-1])
        
        # Usa a função do seu novo backend
        itens, erro = carregar_xml_de_arquivo(caminho)
        
        if erro:
            messagebox.showerror("Erro de Leitura", erro)
            return
            
        if not itens:
            messagebox.showwarning("Aviso", "Nenhum produto encontrado neste XML.")
            return

        self.itens_carregados = itens
        self.atualizar_tabela()
        self.btn_importar.config(state="normal")

    def atualizar_tabela(self):
        for r in self.tree.get_children():
            self.tree.delete(r)

        # Analisa o que já existe no banco e o que é novo
        existentes, novos = preparar_entrada_itens(self.itens_carregados)
        eans_existentes = {i["ean"] for i in existentes}

        for item in self.itens_carregados:
            status = "🔄 Atualizar Estoque" if item["ean"] in eans_existentes else "⚠️ Novo (Não Cadastrado)"
            self.tree.insert("", "end", values=(
                item["ean"],
                item["nome"],
                f"{item['qtd']:.3f}",
                f"R$ {item['preco']:.2f}",
                status
            ))

    def efetivar_importacao(self):
        if not self.itens_carregados:
            return

        # Chama a transação atômica do backend
        sucesso, msg, qtd_importada = dar_entrada_itens(
            self.itens_carregados, 
            cadastrar_novos_automaticamente=self.var_cadastrar_novos.get()
        )

        if sucesso:
            messagebox.showinfo("Importação Concluída", msg)
            self.controlador.mostrar_tela_principal()
        else:
            messagebox.showerror("Erro na Importação", msg)