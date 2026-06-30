import re
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from config import BASE_DIR
from core.helpers import get_config


class ConfiguracoesBaseMixin:
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

    def _titulo(self, parent, texto: str, row: int):
        tk.Label(
            parent,
            text=texto,
            font=("Arial", 11, "bold"),
            fg="#333",
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(12, 6))

    def _campo(
        self,
        parent,
        label: str,
        chave: str,
        row: int,
        default: str = "",
        show: str | None = None,
    ):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
        var = tk.StringVar(value=default)
        ent = tk.Entry(parent, textvariable=var, width=48, show=show)
        ent.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        self.vars[chave] = var
        self._entries_por_chave[chave] = ent
        self._registrar_entry_na_aba(parent, ent)
        return ent

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
        if entry_cep is None:
            return

        def disparar_busca(_event=None):
            cep_limpo = re.sub(r"\D", "", entry_cep.get().strip())
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

    def _combo(
        self,
        parent,
        label: str,
        chave: str,
        row: int,
        values: tuple[str, ...],
        default: str,
    ):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(
            parent, textvariable=var, values=values, state="readonly", width=46
        )
        combo.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        self.vars[chave] = var
        return combo

    def _check(
        self,
        parent,
        label: str,
        chave: str,
        row: int,
        default: bool = False,
        state_opt: str = "normal",
    ):
        var = tk.BooleanVar(value=default)
        chk = tk.Checkbutton(parent, text=label, variable=var, state=state_opt)
        chk.grid(row=row, column=0, columnspan=3, sticky="w", padx=4, pady=4)
        self.bool_vars[chave] = var
        return chk

    def _campo_pasta(self, parent, label: str, chave: str, row: int, default: str):
        self._campo(parent, label, chave, row, default=default)
        tk.Button(
            parent, text="Procurar", command=lambda: self._browse_dir(chave)
        ).grid(row=row, column=2, sticky="w", padx=4)

    def _browse_dir(self, chave: str):
        atual = self.vars[chave].get().strip() or BASE_DIR
        caminho = filedialog.askdirectory(initialdir=atual, title="Selecione uma pasta")
        if caminho:
            self.vars[chave].set(caminho)

    def _encadear_enters_por_aba(self):
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

                    def focar_proximo(_event, prox=proximo):
                        prox.focus_set()
                        return "break"

                    entry.bind("<Return>", focar_proximo)
                    continue

                proxima_aba_com_campos = None
                for j in range(i + 1, len(listas_ordenadas)):
                    if listas_ordenadas[j]:
                        proxima_aba_com_campos = (j, listas_ordenadas[j][0])
                        break
                if proxima_aba_com_campos:
                    idx_aba, primeiro_campo = proxima_aba_com_campos
                    entry.bind(
                        "<Return>",
                        lambda _e, idx=idx_aba, campo=primeiro_campo: self._ir_para_aba_e_focar(
                            idx, campo
                        ),
                    )

    def _ir_para_aba_e_focar(self, indice_aba: int, campo: tk.Entry):
        self._notebook.select(indice_aba)
        campo.focus_set()
        return "break"

    def _cfg(self, chave: str, padrao: str = "") -> str:
        return get_config(chave, padrao) or ""

    def _cfg_bool(self, chave: str, padrao: bool = False) -> bool:
        valor = get_config(chave)
        if valor is None:
            return padrao
        return valor == "True"

    def _valor(self, chave: str) -> str:
        return self.vars[chave].get().strip()
