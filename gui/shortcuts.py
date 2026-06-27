import tkinter as tk

def configurar_atalhos_globais(root: tk.Tk, app_instance):
    """
    Configura os atalhos de teclado globais da aplicação.
    """
    # Exemplo de atalhos comuns em PDV:
    # F12 para Sair / Logout
    root.bind("<F12>", lambda event: app_instance.mostrar_login())
    
    # F1 para Ajuda / Atalhos
    # root.bind("<F1>", lambda event: app_instance.mostrar_ajuda())

def configurar_atalhos_pdv(janela_pdv, funcoes_caixa: dict):
    """
    Configura os atalhos específicos da tela de Frente de Caixa (PDV).
    funcoes_caixa deve ser um dicionário com as funções de callback.
    """
    # F2 - Finalizar Venda
    if "finalizar" in funcoes_caixa:
        janela_pdv.bind("<F2>", lambda event: funcoes_caixa["finalizar"]())
        
    # F3 - Cancelar Venda
    if "cancelar" in funcoes_caixa:
        janela_pdv.bind("<F3>", lambda event: funcoes_caixa["cancelar"]())
        
    # F4 - Buscar Produto
    if "buscar" in funcoes_caixa:
        janela_pdv.bind("<F4>", lambda event: funcoes_caixa["buscar"]())