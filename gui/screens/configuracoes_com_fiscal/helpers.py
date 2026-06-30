def _aba_scroll(self, notebook: ttk.Notebook, titulo: str) -> tk.Frame:
    outer = tk.Frame(notebook)
    canvas = tk.Canvas(outer, highlightthickness=0)
    scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    frame = tk.Frame(canvas, padx=14, pady=14)

    frame.bind(
        "<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=frame, anchor="nw")
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    notebook.add(outer, text=titulo)
    self._entries_por_aba[id(frame)] = []
    self._frame_aba_atual = frame
    return frame


def _encadear_enters_por_aba(self):
    """
    Enter avança para o próximo campo de texto dentro da mesma
    aba (ordenado pela linha do grid). No último campo de uma
    aba, Enter pula para a primeira aba seguinte que tiver algum
    campo navegável. Na última aba, Enter não tem mais para onde
    ir — fica com o comportamento padrão (sem ação especial),
    já que aqui cada aba tem seu próprio botão "Salvar", não um
    botão único de salvar geral como no assistente inicial.
    Campos desabilitados são pulados.
    """
    abas_ids_em_ordem = list(self._entries_por_aba.keys())

    listas_ordenadas: list[list[tk.Entry]] = []
    for chave_aba in abas_ids_em_ordem:
        entries = self._entries_por_aba[chave_aba]
        entries_validos = [e for e in entries if str(e.cget("state")) != "disabled"]
        entries_ordenados = sorted(
            entries_validos, key=lambda e: e.grid_info().get("row", 0)
        )
        listas_ordenadas.append(entries_ordenados)

    for i, entries_aba in enumerate(listas_ordenadas):
        for pos, entry in enumerate(entries_aba):
            if pos + 1 < len(entries_aba):
                proximo = entries_aba[pos + 1]
                entry.bind(
                    "<Return>", lambda e, prox=proximo: (prox.focus_set(), "break")
                )
            else:
                proxima_aba_com_campos = None
                for j in range(i + 1, len(listas_ordenadas)):
                    if listas_ordenadas[j]:
                        proxima_aba_com_campos = (j, listas_ordenadas[j][0])
                        break
                if proxima_aba_com_campos:
                    idx_aba, primeiro_campo = proxima_aba_com_campos
                    entry.bind(
                        "<Return>",
                        lambda e, idx=idx_aba, campo=primeiro_campo: self._ir_para_aba_e_focar(
                            idx, campo
                        ),
                    )
                # última aba, último campo: sem bind especial — comportamento padrão do Tk


def _ir_para_aba_e_focar(self, indice_aba: int, campo: tk.Entry):
    self._notebook.select(indice_aba)
    campo.focus_set()
    return "break"


def _registrar_entry_na_aba(self, parent, entry: tk.Entry):
    chave_aba = id(parent)
    if chave_aba not in self._entries_por_aba:
        chave_aba = id(self._frame_aba_atual)
    self._entries_por_aba.setdefault(chave_aba, []).append(entry)


def _entry_por_chave(self, chave: str) -> tk.Entry | None:
    return self._entries_por_chave.get(chave)


def _configurar_autocomplete_cep(
    self, entry_cep: tk.Entry | None, campos_destino: dict[str, tk.Entry | None]
):
    """
    Ao sair do campo CEP (perder o foco) ou apertar Enter nele,
    consulta o endereço numa thread separada (para não congelar a
    janela enquanto espera a rede) e preenche automaticamente
    logradouro/bairro/município/UF. Nunca sobrescreve o que o
    usuário já tiver digitado manualmente — só preenche campos
    vazios. O número nunca é preenchido automaticamente.
    """
    import re
    import threading

    if entry_cep is None:
        return

    def disparar_busca(_event=None):
        cep_texto = entry_cep.get().strip()
        cep_limpo = re.sub(r"\D", "", cep_texto)
        if len(cep_limpo) != 8:
            return

        def buscar_em_thread():
            from core.helpers import buscar_endereco_por_cep

            resultado = buscar_endereco_por_cep(cep_limpo)
            self.winfo_toplevel().after(0, lambda: aplicar_resultado(resultado))

        def aplicar_resultado(resultado: dict | None):
            if not resultado:
                return
            mapa = {
                "logradouro": resultado.get("logradouro", ""),
                "bairro": resultado.get("bairro", ""),
                "municipio": resultado.get("cidade", ""),
                "uf": resultado.get("uf", ""),
            }
            for chave, valor in mapa.items():
                campo = campos_destino.get(chave)
                if campo is None or not valor:
                    continue
                if not campo.get().strip():
                    campo.delete(0, tk.END)
                    campo.insert(0, valor)

        threading.Thread(target=buscar_em_thread, daemon=True).start()

    entry_cep.bind("<FocusOut>", disparar_busca)
    entry_cep.bind("<Return>", lambda e: disparar_busca(), add="+")
