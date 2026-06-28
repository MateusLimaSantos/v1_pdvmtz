"""
Tema claro/escuro para a aplicação inteira.

Estratégia (Tkinter não tem tema nativo — ver discussão no projeto):
1. `option_add` define as cores PADRÃO de cada classe de widget
   (Frame, Label, Button, Entry, etc). Isso cobre automaticamente
   qualquer widget que NÃO especifica bg/fg explicitamente.
2. Para widgets que já têm cor fixa no código (ex: botão verde de
   "salvar", vermelho de "excluir"), a paleta abaixo fornece
   `cor_semantica(papel)`, que essas telas devem usar no lugar do
   hex fixo. Botões de ação (salvar=verde, excluir=vermelho, etc)
   mantêm a MESMA cor nos dois temas — são cores de status, não de
   fundo, e mudar de tema não deve mudar o que elas significam.
3. Widgets Tk já criados quando o tema muda são re-coloridos por
   `repintar_widget` (chamado recursivamente a partir da raiz),
   para que alternar o tema em tempo real funcione sem reiniciar
   a tela atual.
"""
import tkinter as tk
from tkinter import ttk

from core.helpers import get_config, set_config

CLARO = {
    "fundo": "#f5f5f5",
    "fundo_alt": "#ffffff",
    "texto": "#212121",
    "texto_secundario": "#555555",
    "borda": "#cccccc",
    "entrada_fundo": "#ffffff",
    "entrada_texto": "#212121",
    "selecao_fundo": "#cce4ff",
    "botao_neutro_fundo": "#e0e0e0",
    "botao_neutro_texto": "#212121",
    "treeview_fundo": "#ffffff",
    "treeview_texto": "#212121",
    "treeview_cabecalho_fundo": "#e8e8e8",
    "treeview_linha_alt": "#f0f0f0",
}

ESCURO = {
    "fundo": "#1e1e1e",
    "fundo_alt": "#2a2a2a",
    "texto": "#e8e8e8",
    "texto_secundario": "#a0a0a0",
    "borda": "#444444",
    "entrada_fundo": "#2e2e2e",
    "entrada_texto": "#e8e8e8",
    "selecao_fundo": "#3a5a7a",
    "botao_neutro_fundo": "#3a3a3a",
    "botao_neutro_texto": "#e8e8e8",
    "treeview_fundo": "#252525",
    "treeview_texto": "#e8e8e8",
    "treeview_cabecalho_fundo": "#333333",
    "treeview_linha_alt": "#2c2c2c",
}

# Cores semânticas/de status: mantêm o mesmo significado visual em
# qualquer tema (verde = confirmar/salvar, vermelho = perigo/excluir,
# laranja = atenção/ajustar, azul = ação informativa). Texto sempre
# branco sobre essas, em ambos os temas, por contraste.
CORES_SEMANTICAS = {
    "sucesso": "#2e7d32",
    "perigo": "#b00020",
    "atencao": "#FF9800",
    "info": "#1976D2",
    "neutro_escuro": "#455A64",
}


def cor_semantica(papel: str) -> str:
    return CORES_SEMANTICAS.get(papel, "#757575")


def tema_atual_nome() -> str:
    return get_config("tema", "claro")


def tema_atual() -> dict:
    return ESCURO if tema_atual_nome() == "escuro" else CLARO


def alternar_tema() -> str:
    novo = "escuro" if tema_atual_nome() == "claro" else "claro"
    set_config("tema", novo)
    return novo


def aplicar_defaults_globais(root: tk.Tk):
    """
    Define as cores padrão de cada classe de widget via option_add.
    Chamar uma vez, logo após criar o root. Widgets criados depois
    disso, sem bg/fg explícito no código, usam essas cores
    automaticamente — inclusive popups (Toplevel) criados depois.
    """
    t = tema_atual()
    root.option_add("*Frame.background", t["fundo"])
    root.option_add("*Label.background", t["fundo"])
    root.option_add("*Label.foreground", t["texto"])
    root.option_add("*Button.background", t["botao_neutro_fundo"])
    root.option_add("*Button.foreground", t["botao_neutro_texto"])
    root.option_add("*Button.activeBackground", t["borda"])
    root.option_add("*Entry.background", t["entrada_fundo"])
    root.option_add("*Entry.foreground", t["entrada_texto"])
    root.option_add("*Entry.insertBackground", t["entrada_texto"])
    root.option_add("*Listbox.background", t["entrada_fundo"])
    root.option_add("*Listbox.foreground", t["entrada_texto"])
    root.option_add("*Toplevel.background", t["fundo"])
    root.option_add("*Canvas.background", t["fundo"])
    root.option_add("*Checkbutton.background", t["fundo"])
    root.option_add("*Checkbutton.foreground", t["texto"])
    root.option_add("*Checkbutton.selectColor", t["entrada_fundo"])
    root.configure(bg=t["fundo"])

    _configurar_estilo_ttk(root, t)


def _configurar_estilo_ttk(root: tk.Tk, t: dict):
    """ttk usa um sistema de estilos próprio — option_add não alcança
    widgets ttk (Treeview, Combobox, Notebook, Scrollbar). Configuramos
    via ttk.Style, que é o mecanismo correto para esses widgets."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")  # tema base que aceita customização de cores em todas plataformas
    except tk.TclError:
        pass

    style.configure("Treeview", background=t["treeview_fundo"], foreground=t["treeview_texto"],
                     fieldbackground=t["treeview_fundo"], bordercolor=t["borda"])
    style.configure("Treeview.Heading", background=t["treeview_cabecalho_fundo"], foreground=t["texto"])
    style.map("Treeview", background=[("selected", t["selecao_fundo"])])

    style.configure("TCombobox", fieldbackground=t["entrada_fundo"], background=t["entrada_fundo"],
                     foreground=t["entrada_texto"])
    style.map("TCombobox", fieldbackground=[("readonly", t["entrada_fundo"])])

    style.configure("TNotebook", background=t["fundo"], bordercolor=t["borda"])
    style.configure("TNotebook.Tab", background=t["botao_neutro_fundo"], foreground=t["texto"])
    style.map("TNotebook.Tab", background=[("selected", t["fundo_alt"])])

    style.configure("TFrame", background=t["fundo"])
    style.configure("TLabel", background=t["fundo"], foreground=t["texto"])
    style.configure("TScrollbar", background=t["botao_neutro_fundo"], troughcolor=t["fundo"])


def repintar_widget(widget, t: dict | None = None):
    """
    Percorre recursivamente a árvore de widgets a partir de `widget` e
    reaplica as cores do tema atual, preservando cores semânticas
    (botões verdes/vermelhos continuam verdes/vermelhos). Usado para
    alternar o tema em tempo real sem reconstruir a tela.

    Heurística para distinguir "cor de fundo neutra" de "cor semântica
    proposital": comparamos a cor atual do widget contra as cores
    neutras conhecidas de AMBOS os temas. Se a cor atual bate com uma
    cor neutra conhecida (de qualquer um dos dois temas — o widget
    pode já estar no tema antigo), trocamos pela cor neutra do tema
    novo. Caso contrário (é uma cor de status como verde/vermelho),
    deixamos como está — é proposital.
    """
    if t is None:
        t = tema_atual()

    cores_neutras_fundo = {
        CLARO["fundo"], CLARO["fundo_alt"], CLARO["botao_neutro_fundo"],
        ESCURO["fundo"], ESCURO["fundo_alt"], ESCURO["botao_neutro_fundo"],
        "#e0e0e0", "#cfd8dc",  # cores de botão neutro usadas no código legado das telas
    }
    cores_neutras_texto = {
        CLARO["texto"], CLARO["botao_neutro_texto"], ESCURO["texto"], ESCURO["botao_neutro_texto"],
        "black", "#000000", "#212121", "#333", "#333333", "#555", "#555555",  # textos/títulos neutros do código legado
    }
    cores_neutras_entrada = {CLARO["entrada_fundo"], ESCURO["entrada_fundo"], "white", "#ffffff"}

    classe = widget.winfo_class()

    try:
        if classe in ("Frame", "Toplevel", "Canvas", "Labelframe"):
            atual = str(widget.cget("background"))
            if atual.lower() in {c.lower() for c in cores_neutras_fundo} or atual == "":
                widget.configure(background=t["fundo"])
        elif classe == "Label":
            atual_bg = str(widget.cget("background"))
            atual_fg = str(widget.cget("foreground"))
            if atual_bg.lower() in {c.lower() for c in cores_neutras_fundo} or atual_bg == "":
                widget.configure(background=t["fundo"])
            if atual_fg.lower() in {c.lower() for c in cores_neutras_texto} or atual_fg == "":
                widget.configure(foreground=t["texto"])
        elif classe == "Button":
            atual_bg = str(widget.cget("background"))
            if atual_bg.lower() in {c.lower() for c in cores_neutras_fundo} or atual_bg == "":
                widget.configure(background=t["botao_neutro_fundo"], foreground=t["botao_neutro_texto"])
            # Botões com cor semântica (verde/vermelho/laranja/azul) mantêm
            # o fundo, mas o texto branco continua correto nos dois temas.
        elif classe == "Entry":
            atual_bg = str(widget.cget("background"))
            if atual_bg.lower() in {c.lower() for c in cores_neutras_entrada} or atual_bg == "":
                widget.configure(background=t["entrada_fundo"], foreground=t["entrada_texto"],
                                  insertbackground=t["entrada_texto"])
        elif classe == "Checkbutton":
            widget.configure(background=t["fundo"], foreground=t["texto"],
                              selectcolor=t["entrada_fundo"], activebackground=t["fundo"])
        elif classe == "Listbox":
            widget.configure(background=t["entrada_fundo"], foreground=t["entrada_texto"])
    except tk.TclError:
        pass  # widget pode não suportar a opção (ex: separador) — ignora

    for filho in widget.winfo_children():
        repintar_widget(filho, t)


def aplicar_tema_em_toda_aplicacao(root: tk.Tk):
    """Reaplica defaults globais + repinta toda a árvore de widgets a
    partir da janela raiz. Chamar depois de alternar_tema()."""
    aplicar_defaults_globais(root)
    repintar_widget(root, tema_atual())
