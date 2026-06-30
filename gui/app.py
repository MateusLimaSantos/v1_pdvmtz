import tkinter as tk
from gui.login import TelaLogin
from gui.screens.pdv import TelaPDV
from gui.screens.estoque import TelaEstoque
from gui.screens.nfe import TelaNFe
from gui.screens.configuracoes_com_fiscal import TelaConfiguracoes
from gui.screens.historico import TelaHistorico
from gui.screens.fornecedores import TelaFornecedores
from gui.screens.relatorios import TelaRelatorios
from gui.screens.auditoria import TelaAuditoria
from gui.screens.graficos import TelaGraficos
from core.state import state
from core.helpers import get_config
from gui.tema import (
    aplicar_defaults_globais,
    aplicar_tema_em_toda_aplicacao,
    alternar_tema,
    tema_atual_nome,
)


class AppPDV:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema Corporativo PDV - MTZ")
        self.root.geometry("1024x768")
        try:
            self.root.state("zoomed")  # maximiza no Windows
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)  # equivalente no Linux/X11
            except tk.TclError:
                pass  # mantém o geometry definido acima como fallback final

        aplicar_defaults_globais(self.root)

        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.tela_atual_nome = "login"
        self.mostrar_login()

    def limpar_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()
        # Agenda o repaint do tema para depois que a tela nova (chamada
        # logo após limpar_container, em cada mostrar_*) terminar de
        # construir seus widgets. Isso garante que toda tela, ao nascer,
        # já reflita o tema salvo — mesmo widgets com fg/bg explícito no
        # código legado (que option_add não alcança), sem precisar
        # chamar repintar_widget manualmente em cada método mostrar_*.
        self.container.after_idle(self._repintar_container_atual)

    def _repintar_container_atual(self):
        from gui.tema import repintar_widget, tema_atual

        repintar_widget(self.container, tema_atual())

    def mostrar_login(self):
        self.tela_atual_nome = "login"
        self.limpar_container()
        TelaLogin(self.container, self.ao_logar)

    def ao_logar(self):
        self.mostrar_tela_principal()

    def realizar_logoff(self):
        state.operador = None
        state.caixa_id = None
        self.mostrar_login()

    def alternar_tema_app(self):
        alternar_tema()
        aplicar_tema_em_toda_aplicacao(self.root)
        # Recria a tela atual do zero, garantindo que widgets criados
        # antes desta troca (inclusive os que option_add não alcança,
        # como ttk já instanciado com cache de estilo antigo) saiam
        # consistentes com o novo tema.
        self.mostrar_tela_atual()

    def mostrar_tela_atual(self):
        destino = getattr(self, f"mostrar_{self.tela_atual_nome}", None)
        if destino:
            destino()
        else:
            self.mostrar_tela_principal()

    def mostrar_tela_principal(self):
        self.tela_atual_nome = "tela_principal"
        self.limpar_container()

        frame_menu = tk.Frame(self.container)
        frame_menu.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            frame_menu,
            text=f"Painel Principal — Operador: {state.operador['nome'].upper()}",
            font=("Arial", 20, "bold"),
            fg="#333",
        ).pack(pady=(0, 40))

        tk.Button(
            frame_menu,
            text="🛒 Abrir Frente de Caixa (F1)",
            font=("Arial", 14),
            width=28,
            height=2,
            bg="#2196F3",
            fg="white",
            bd=0,
            command=self.mostrar_pdv,
        ).pack(pady=8)
        tk.Button(
            frame_menu,
            text="📦 Controle de Estoque (F2)",
            font=("Arial", 14),
            width=28,
            height=2,
            bg="#FF9800",
            fg="white",
            bd=0,
            command=self.mostrar_estoque,
        ).pack(pady=8)
        tk.Button(
            frame_menu,
            text="📥 Importar XML (NF-e) (F3)",
            font=("Arial", 14),
            width=28,
            height=2,
            bg="#673AB7",
            fg="white",
            bd=0,
            command=self.mostrar_nfe,
        ).pack(pady=8)

        if state.operador and state.operador.get("perfil") == "admin":
            if get_config("admin_mod_historico", "True") == "True":
                tk.Button(
                    frame_menu,
                    text="🧾 Histórico de Vendas (F4)",
                    font=("Arial", 14),
                    width=28,
                    height=2,
                    bg="#00897B",
                    fg="white",
                    bd=0,
                    command=self.mostrar_historico,
                ).pack(pady=8)
            if get_config("admin_mod_fornecedores", "True") == "True":
                tk.Button(
                    frame_menu,
                    text="🚚 Fornecedores (F5)",
                    font=("Arial", 14),
                    width=28,
                    height=2,
                    bg="#5D4037",
                    fg="white",
                    bd=0,
                    command=self.mostrar_fornecedores,
                ).pack(pady=8)
            if get_config("admin_mod_relatorios", "True") == "True":
                tk.Button(
                    frame_menu,
                    text="📊 Relatórios (F6)",
                    font=("Arial", 14),
                    width=28,
                    height=2,
                    bg="#283593",
                    fg="white",
                    bd=0,
                    command=self.mostrar_relatorios,
                ).pack(pady=8)
            if get_config("admin_mod_graficos", "True") == "True":
                tk.Button(
                    frame_menu,
                    text="📈 Gráficos (F7)",
                    font=("Arial", 14),
                    width=28,
                    height=2,
                    bg="#00838F",
                    fg="white",
                    bd=0,
                    command=self.mostrar_graficos,
                ).pack(pady=8)
            if get_config("admin_mod_auditoria", "True") == "True":
                tk.Button(
                    frame_menu,
                    text="🔍 Auditoria (F8)",
                    font=("Arial", 14),
                    width=28,
                    height=2,
                    bg="#37474F",
                    fg="white",
                    bd=0,
                    command=self.mostrar_auditoria,
                ).pack(pady=8)
            tk.Button(
                frame_menu,
                text="⚙️ Configurações (F9)",
                font=("Arial", 14),
                width=28,
                height=2,
                bg="#455A64",
                fg="white",
                bd=0,
                command=self.mostrar_configuracoes,
            ).pack(pady=8)

        tk.Button(
            frame_menu,
            text=(
                "🌙 Alternar Modo Claro/Escuro (F11)"
                if tema_atual_nome() == "claro"
                else "☀️ Alternar Modo Claro/Escuro (F11)"
            ),
            font=("Arial", 11),
            width=31,
            height=1,
            bg="#616161",
            fg="white",
            bd=0,
            command=self.alternar_tema_app,
        ).pack(pady=(0, 16))

        tk.Button(
            frame_menu,
            text="🚪 Realizar Logoff (Sair) (F12)",
            font=("Arial", 12),
            width=28,
            height=1,
            bg="#f44336",
            fg="white",
            bd=0,
            command=self.realizar_logoff,
        ).pack(pady=30)

        # =========================================================================
        # NOVO CÓDIGO: Efeito visual dinâmico (aumenta o botão ao focar/passar o mouse)
        # =========================================================================
        botoes = [w for w in frame_menu.winfo_children() if isinstance(w, tk.Button)]

        for btn in botoes:
            # Salva o tamanho original no próprio botão
            btn._font_padrao = btn.cget("font")
            btn._width_padrao = btn.cget("width")
            texto = btn.cget("text")

            # Define o tamanho de destaque proporcional a cada botão
            if "Alternar Modo" in texto:
                font_destaque = ("Arial", 13, "bold")
                width_destaque = 34
            elif "Logoff" in texto:
                font_destaque = ("Arial", 14, "bold")
                width_destaque = 30
            else:
                font_destaque = ("Arial", 16, "bold")
                width_destaque = 31

            def on_focus(e, b=btn, f=font_destaque, w=width_destaque):
                b.config(font=f, width=w)

            def off_focus(e, b=btn):
                b.config(font=b._font_padrao, width=b._width_padrao)

            # Aplica os eventos do teclado (setas) e mouse (hover)
            btn.bind("<FocusIn>", on_focus)
            btn.bind("<FocusOut>", off_focus)
            btn.bind("<Enter>", on_focus)
            btn.bind("<Leave>", off_focus)

        if botoes:
            botoes[0].focus_set()  # Já começa com o primeiro botão destacado
        # =========================================================================

        self._registrar_atalhos_menu_principal()

    def _registrar_atalhos_menu_principal(self):
        """
        Atalhos F1-F9, F11 e F12 do menu principal, mais navegação por setas,
        Enter e números (1 a 9). Escopados a esta tela via <Destroy>.
        """
        # Mapeia tanto o F-key quanto o número correspondente
        mapa: list[tuple[str, callable]] = [
            ("<F1>", self.mostrar_pdv),
            ("1", self.mostrar_pdv),
            ("<F2>", self.mostrar_estoque),
            ("2", self.mostrar_estoque),
            ("<F3>", self.mostrar_nfe),
            ("3", self.mostrar_nfe),
        ]

        if state.operador and state.operador.get("perfil") == "admin":
            if get_config("admin_mod_historico", "True") == "True":
                mapa.extend(
                    [("<F4>", self.mostrar_historico), ("4", self.mostrar_historico)]
                )

            if get_config("admin_mod_fornecedores", "True") == "True":
                mapa.extend(
                    [
                        ("<F5>", self.mostrar_fornecedores),
                        ("5", self.mostrar_fornecedores),
                    ]
                )

            if get_config("admin_mod_relatorios", "True") == "True":
                mapa.extend(
                    [("<F6>", self.mostrar_relatorios), ("6", self.mostrar_relatorios)]
                )

            if get_config("admin_mod_graficos", "True") == "True":
                mapa.extend(
                    [("<F7>", self.mostrar_graficos), ("7", self.mostrar_graficos)]
                )

            if get_config("admin_mod_auditoria", "True") == "True":
                mapa.extend(
                    [("<F8>", self.mostrar_auditoria), ("8", self.mostrar_auditoria)]
                )

            mapa.extend(
                [
                    ("<F9>", self.mostrar_configuracoes),
                    ("9", self.mostrar_configuracoes),
                ]
            )

        mapa.append(("<F11>", self.alternar_tema_app))
        mapa.append(("<F12>", self.realizar_logoff))

        # --- Funções para Navegação por Setas e Enter ---
        def _invocar_foco():
            focado = self.root.focus_get()
            if isinstance(focado, tk.Button):
                focado.invoke()

        def _focar_proximo():
            focado = self.root.focus_get()
            if isinstance(focado, tk.Widget):
                focado.tk_focusNext().focus_set()

        def _focar_anterior():
            focado = self.root.focus_get()
            if isinstance(focado, tk.Widget):
                focado.tk_focusPrev().focus_set()

        # Vincula Enter e Setas
        mapa.extend(
            [
                ("<Return>", _invocar_foco),
                ("<Down>", _focar_proximo),
                ("<Up>", _focar_anterior),
            ]
        )
        # ------------------------------------------------

        bind_ids = []
        for tecla, callback in mapa:
            bind_id = self.root.bind(tecla, lambda e, cb=callback: cb())
            bind_ids.append((tecla, bind_id))

        def _remover_atalhos(_event=None):
            for tecla, bind_id in bind_ids:
                try:
                    self.root.unbind(tecla, bind_id)
                except tk.TclError:
                    pass

        # frame_menu é o último frame criado em mostrar_tela_principal;
        # buscamos ele nos filhos do container para anexar o cleanup.
        for widget in self.container.winfo_children():
            widget.bind("<Destroy>", _remover_atalhos)

    def mostrar_pdv(self):
        self.tela_atual_nome = "pdv"
        self.limpar_container()
        TelaPDV(self.container, self)

    def mostrar_estoque(self):
        self.tela_atual_nome = "estoque"
        self.limpar_container()
        TelaEstoque(self.container, self)

    def mostrar_nfe(self):
        self.tela_atual_nome = "nfe"
        self.limpar_container()
        TelaNFe(self.container, self)

    def mostrar_configuracoes(self):
        self.tela_atual_nome = "configuracoes"
        self.limpar_container()
        TelaConfiguracoes(self.container, self)

    def mostrar_historico(self):
        self.tela_atual_nome = "historico"
        self.limpar_container()
        TelaHistorico(self.container, self)

    def mostrar_fornecedores(self):
        self.tela_atual_nome = "fornecedores"
        self.limpar_container()
        TelaFornecedores(self.container, self)

    def mostrar_relatorios(self):
        self.tela_atual_nome = "relatorios"
        self.limpar_container()
        TelaRelatorios(self.container, self)

    def mostrar_auditoria(self):
        self.tela_atual_nome = "auditoria"
        self.limpar_container()
        TelaAuditoria(self.container, self)

    def mostrar_graficos(self):
        self.tela_atual_nome = "graficos"
        self.limpar_container()
        TelaGraficos(self.container, self)

    def run(self):
        self.root.mainloop()
