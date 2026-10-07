import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from database import (
    delete_transparencia,
    get_governance_backlog_options,
    get_transparencia_backlog_ids,
    list_transparencia,
    save_transparencia,
)
from grid_sizing import fit_tree_columns
import data_transfer as transfer


PANEL_STYLE = "Panel.TFrame"
MUTED_STYLE = "Muted.TLabel"
SECTION_STYLE = "Section.TLabel"
PRIMARY_STYLE = "Primary.TButton"
NEW_STYLE = "NewStory.TButton"
ICON_STYLE = "Icon.TButton"
PLACEHOLDER_STYLE = "Placeholder.TEntry"
BUTTON_WIDTH = 18
FONT_NAME = "Segoe UI"
GRID_COLUMNS = (
    ("id", "Id_Transp", 0, 95),
    ("report", "Relatório", 1, 260),
    ("frequency", "Frequência", 2, 200),
    ("owner", "Responsável", 3, 150),
    ("visibility", "Visibilidade", 4, 180),
    ("links", "Histórias vinculadas", 5, 220),
)
TRANSFER_HEADERS = ("Id_Transp", "Relatorio", "Frequencia_Publicacao", "Responsavel", "Visibilidade")


class TransparenciaForm:
    def __init__(self, root, return_to_menu):
        self.root = root
        self.return_to_menu = return_to_menu
        self.records = []
        self.backlog_rows = get_governance_backlog_options()
        self.editing_id = None

        self.id_var = tk.StringVar()
        self.report_var = tk.StringVar()
        self.frequency_var = tk.StringVar()
        self.owner_var = tk.StringVar()
        self.visibility_var = tk.StringVar()
        self.search_var = tk.StringVar()

        self._configure_style()
        self._build_layout()
        self.refresh_records()

    def _configure_style(self):
        style = ttk.Style(self.root)
        style.configure(PANEL_STYLE, background="#ffffff")
        style.configure(MUTED_STYLE, background="#ffffff", foreground="#718078", font=(FONT_NAME, 9))
        style.configure(SECTION_STYLE, background="#ffffff", foreground="#19392f", font=(FONT_NAME, 12, "bold"))
        style.configure("TEntry", padding=(9, 8), fieldbackground="#f7f9f7")
        style.configure(PLACEHOLDER_STYLE, padding=(9, 8), fieldbackground="#f7f9f7", foreground="#829088")
        style.configure("TCombobox", padding=(8, 7), fieldbackground="#f7f9f7")
        style.configure("TButton", width=BUTTON_WIDTH, padding=(10, 7), anchor="center", font=(FONT_NAME, 9))
        style.configure(PRIMARY_STYLE, width=BUTTON_WIDTH, padding=(10, 7), anchor="center", background="#236b58", foreground="#ffffff", font=(FONT_NAME, 9, "bold"))
        style.map(PRIMARY_STYLE, background=[("active", "#1b5747")])
        style.configure(NEW_STYLE, width=BUTTON_WIDTH, padding=(10, 7), anchor="center", background="#2878c7", foreground="#ffffff", font=(FONT_NAME, 9, "bold"))
        style.map(NEW_STYLE, background=[("active", "#1f609f")])
        style.configure("Header.TButton", width=BUTTON_WIDTH, padding=(10, 7), anchor="center", background="#315b4f", foreground="#ffffff", font=(FONT_NAME, 9, "bold"))
        style.configure(ICON_STYLE, width=4, padding=(8, 7), anchor="center", font=(FONT_NAME, 9))
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground="#23352f", rowheight=34, font=(FONT_NAME, 9))
        style.configure("Treeview.Heading", background="#e7eeea", foreground="#365046", font=(FONT_NAME, 9, "bold"), padding=(8, 9))
        style.map("Treeview", background=[("selected", "#d9ebe3")], foreground=[("selected", "#19392f")])

    def _build_layout(self):
        self.frame = ttk.Frame(self.root, style="TFrame")
        self.frame.pack(fill="both", expand=True)
        self.header = tk.Frame(self.frame, bg="#19392f", height=100)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        title = tk.Frame(self.header, bg="#19392f")
        title.pack(side="left", padx=28, pady=18)
        tk.Label(title, text="SCRUM  /  TRANSPARÊNCIA", bg="#19392f", fg="#a9c9bb", font=(FONT_NAME, 9, "bold")).pack(anchor="w")
        tk.Label(title, text="Relatórios e visibilidade", bg="#19392f", fg="#ffffff", font=(FONT_NAME, 21, "bold")).pack(anchor="w", pady=(2, 0))
        self.count_label = tk.Label(self.header, text="0 RELATÓRIOS", bg="#19392f", fg="#d7e8df", font=(FONT_NAME, 10, "bold"))
        self.count_label.pack(side="right", padx=20)
        ttk.Button(self.header, text="← Menu Principal", style="Header.TButton", command=self.return_to_menu).pack(side="right", padx=8)

        content = ttk.Frame(self.frame, padding=(20, 18, 20, 20))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=0, minsize=360)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        form_panel = ttk.Frame(content, style=PANEL_STYLE, padding=18)
        form_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        form_panel.columnconfigure(0, weight=1)
        form_panel.rowconfigure(0, weight=1)
        canvas = tk.Canvas(form_panel, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_panel, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.form_body = ttk.Frame(canvas, style=PANEL_STYLE)
        window = canvas.create_window((0, 0), window=self.form_body, anchor="nw")
        self.form_body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))

        self.list_panel = ttk.Frame(content, style=PANEL_STYLE, padding=18)
        self.list_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self.list_panel.columnconfigure(0, weight=1)
        self.list_panel.rowconfigure(4, weight=1)
        self._build_form()
        self._build_grid()

    def _build_form(self):
        ttk.Label(self.form_body, text="DADOS DO RELATÓRIO", style=MUTED_STYLE).pack(anchor="w")
        ttk.Label(self.form_body, text="Cadastro", style=SECTION_STYLE).pack(anchor="w", pady=(3, 14))
        self.id_entry = self._add_entry("Id_Transp", self.id_var, search_command=self.search_transparencia)
        self.id_entry.configure(state="readonly")
        self.report_entry = self._add_entry("Relatório *", self.report_var, "Ex.: RELATÓRIO DE PROGRESSO")
        self.frequency_entry = self._add_entry("Frequência de publicação *", self.frequency_var, "Ex.: SEMANAL")
        self.owner_entry = self._add_entry("Responsável *", self.owner_var, "Ex.: EQUIPE DE DESENVOLVIMENTO")
        for entry in (self.report_entry, self.frequency_entry, self.owner_entry):
            entry.bind("<KeyRelease>", self._uppercase_entry)

        ttk.Label(self.form_body, text="Visibilidade *").pack(anchor="w", pady=(10, 5))
        self.visibility_combo = ttk.Combobox(self.form_body, textvariable=self.visibility_var, state="readonly")
        self.visibility_combo.pack(fill="x")

        ttk.Label(self.form_body, text="Histórias do Product_Backlog").pack(anchor="w", pady=(12, 5))
        links_frame = ttk.Frame(self.form_body, style=PANEL_STYLE)
        links_frame.pack(fill="both", expand=True)
        self.links_list = tk.Listbox(links_frame, selectmode=tk.MULTIPLE, exportselection=False, height=8,
                                     font=(FONT_NAME, 9), relief="flat", bg="#f7f9f7", fg="#23352f",
                                     selectbackground="#d9ebe3", selectforeground="#19392f",
                                     highlightthickness=1, highlightbackground="#dce5df")
        self.links_list.grid(row=0, column=0, sticky="nsew")
        link_scrollbar = ttk.Scrollbar(links_frame, orient="vertical", command=self.links_list.yview)
        link_scrollbar.grid(row=0, column=1, sticky="ns")
        self.links_list.configure(yscrollcommand=link_scrollbar.set)
        links_frame.columnconfigure(0, weight=1)
        links_frame.rowconfigure(0, weight=1)
        self._populate_backlog_options()

        ttk.Separator(self.form_body).pack(fill="x", pady=16)
        ttk.Button(self.form_body, text="Novo relatório", style=NEW_STYLE, command=self.new_record).pack(fill="x", pady=(0, 8))
        self.save_button = ttk.Button(self.form_body, text="Salvar relatório", style=PRIMARY_STYLE, command=self.save_record)
        self.save_button.pack(fill="x")
        ttk.Button(self.form_body, text="Limpar formulário", command=self.clear_form).pack(fill="x", pady=(8, 0))

    def _add_entry(self, label, variable, placeholder=None, search_command=None):
        ttk.Label(self.form_body, text=label).pack(anchor="w", pady=(9, 5))
        row = ttk.Frame(self.form_body, style=PANEL_STYLE)
        row.pack(fill="x")
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True)
        if search_command:
            ttk.Button(row, text="🔍", style=ICON_STYLE, command=search_command).pack(side="left", padx=(6, 0))
        if placeholder:
            self._set_placeholder(entry, variable, placeholder)
        return entry

    @staticmethod
    def _set_placeholder(entry, variable, placeholder):
        entry.placeholder = placeholder
        entry.configure(style=PLACEHOLDER_STYLE)
        variable.set(placeholder)
        entry.bind("<FocusIn>", lambda _event: TransparenciaForm._clear_placeholder(entry, variable))
        entry.bind("<FocusOut>", lambda _event: TransparenciaForm._restore_placeholder(entry, variable))

    @staticmethod
    def _clear_placeholder(entry, variable):
        if variable.get() == entry.placeholder:
            variable.set("")
            entry.configure(style="TEntry")

    @staticmethod
    def _restore_placeholder(entry, variable):
        if not variable.get():
            variable.set(entry.placeholder)
            entry.configure(style=PLACEHOLDER_STYLE)

    @staticmethod
    def _uppercase_entry(event):
        entry = event.widget
        value = entry.get()
        if value == getattr(entry, "placeholder", None):
            return
        uppercase = value.upper()
        if uppercase != value:
            cursor = entry.index(tk.INSERT)
            entry.delete(0, tk.END)
            entry.insert(0, uppercase)
            entry.icursor(min(cursor, len(uppercase)))

    def _get_backlog_options(self):
        return get_governance_backlog_options()

    def _populate_backlog_options(self, selected_ids=()):
        selected_ids = set(selected_ids)
        self.backlog_rows = self._get_backlog_options()
        self.links_list.delete(0, tk.END)
        for index, (backlog_id, module) in enumerate(self.backlog_rows):
            self.links_list.insert(tk.END, f"{backlog_id}  |  {module}")
            if backlog_id in selected_ids:
                self.links_list.selection_set(index)

    def _selected_backlog_ids(self):
        return [self.backlog_rows[index][0] for index in self.links_list.curselection()]

    def _build_grid(self):
        ttk.Label(self.list_panel, text="VISÃO GERAL", style=MUTED_STYLE).grid(row=0, column=0, sticky="w")
        ttk.Label(self.list_panel, text="Relatórios de transparência", style=SECTION_STYLE).grid(row=1, column=0, sticky="w", pady=(3, 12))
        filters = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        filters.grid(row=2, column=0, sticky="ew")
        filters.columnconfigure(0, weight=1)
        search = ttk.Entry(filters, textvariable=self.search_var)
        search.grid(row=0, column=0, sticky="ew")
        search.bind("<KeyRelease>", self._on_search)

        actions = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 10))
        ttk.Button(actions, text="Editar selecionado", command=self.edit_selected).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Excluir selecionado", command=self.delete_selected).pack(side="left", padx=(0, 6))
        transfer.add_transfer_buttons(actions, self)

        table_frame = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        table_frame.grid(row=4, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, columns=("id", "report", "frequency", "owner", "visibility", "links"), show="headings", selectmode="browse")
        for column, heading, width in (("id", "Id_Transp", 95), ("report", "Relatório", 260),
                                       ("frequency", "Frequência", 200), ("owner", "Responsável", 150),
                                       ("visibility", "Visibilidade", 180), ("links", "Histórias vinculadas", 145)):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, minwidth=60, anchor="w", stretch=False)
        self.tree.tag_configure("even", background="#f7f9f7")
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.empty_label = ttk.Label(table_frame, text="Nenhum relatório encontrado.", style=MUTED_STYLE)
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind("<Double-1>", self.load_selected)

    def refresh_records(self):
        try:
            self.records = list_transparencia()
        except sqlite3.Error as error:
            messagebox.showerror("Erro ao carregar transparência", str(error), parent=self.root)
            self.records = []
        visibilities = sorted({row[4] for row in self.records if row[4]})
        self.visibility_combo.configure(values=visibilities)
        self.apply_filters()
        if self.editing_id is None:
            self.id_var.set(str(self._next_id()))
            self.id_entry.configure(state="readonly")

    def _next_id(self):
        return max((int(row[0]) for row in self.records if row[0] is not None), default=0) + 1

    def export_csv(self):
        rows = [record[:5] for record in self.records]
        transfer.export_csv(self.root, "Exportar transparência", "transparencia.csv", TRANSFER_HEADERS, rows)

    def export_excel(self):
        rows = [record[:5] for record in self.records]
        transfer.export_excel(self.root, "Exportar transparência", "transparencia.xlsx", "Transparência", TRANSFER_HEADERS, rows)

    def import_csv(self):
        rows = transfer.read_csv(self.root, "Importar transparência")
        if rows is not None:
            self._import_rows(rows)

    def import_excel(self):
        rows = transfer.read_excel(self.root, "Importar transparência")
        if rows is not None:
            self._import_rows(rows)

    def _import_rows(self, rows):
        existing = {str(record[1]).strip().casefold() for record in self.records}
        imported = skipped = 0
        for row in rows:
            data = transfer.normalized(row)
            relatorio = transfer.field(data, "relatorio", "relatório")
            if not relatorio or relatorio.casefold() in existing:
                skipped += 1
                continue
            try:
                save_transparencia(None, relatorio.upper(),
                                   transfer.field(data, "frequencia_publicacao", "frequência", "frequencia").upper(),
                                   transfer.field(data, "responsavel", "responsável").upper(),
                                   transfer.field(data, "visibilidade").upper(), [])
                existing.add(relatorio.casefold())
                imported += 1
            except sqlite3.Error:
                skipped += 1
        self.refresh_records()
        transfer.report(self.root, imported, skipped)

    def _on_search(self, event=None):
        if event is not None:
            self.search_var.set(self.search_var.get().upper())
        self.apply_filters()

    def apply_filters(self):
        query = self.search_var.get().strip().casefold()
        filtered = [row for row in self.records if not query or query in " ".join(str(value or "") for value in row).casefold()]
        self.tree.delete(*self.tree.get_children())
        if filtered:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        for index, row in enumerate(filtered):
            values = (*row[:5], row[6] or "SEM HISTÓRIAS VINCULADAS")
            self.tree.insert("", "end", iid=str(index), values=values, tags=("even" if index % 2 == 0 else "odd",))
        self.count_label.configure(text=f"{len(filtered)} RELATÓRIOS" if len(filtered) != 1 else "1 RELATÓRIO")
        grid_rows = [tuple(row[:5]) + (row[6] or "SEM HISTÓRIAS VINCULADAS",) for row in self.records]
        fit_tree_columns(self.tree, self.root, GRID_COLUMNS, grid_rows)

    def search_transparencia(self):
        value = simpledialog.askinteger("Pesquisar relatório", "Informe o Id_Transp:", parent=self.root, minvalue=1)
        if value is None:
            return
        row = next((record for record in self.records if int(record[0]) == value), None)
        if row:
            self._load_record(row)
        else:
            messagebox.showinfo("Relatório não encontrado", f"Id_Transp {value} não existe.", parent=self.root)

    def save_record(self):
        values = [self.report_var.get().strip(), self.frequency_var.get().strip(), self.owner_var.get().strip()]
        for index, entry in enumerate((self.report_entry, self.frequency_entry, self.owner_entry)):
            if values[index] == entry.placeholder:
                values[index] = ""
        visibility = self.visibility_var.get().strip()
        names = ("Relatório", "Frequência de publicação", "Responsável")
        missing = [name for name, value in zip(names, (*values,)) if not value]
        if not visibility:
            missing.append("Visibilidade")
        if missing:
            messagebox.showwarning("Campos obrigatórios", f"Preencha: {', '.join(missing)}.", parent=self.root)
            return
        try:
            record_id = save_transparencia(
                self.editing_id, values[0].upper(), values[1].upper(), values[2].upper(),
                visibility.upper(), self._selected_backlog_ids(),
            )
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível salvar", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()
        messagebox.showinfo("Transparência atualizada", f"Relatório {record_id} salvo com seus vínculos.", parent=self.root)

    def _load_record(self, row):
        self.editing_id = int(row[0])
        self.id_var.set(str(row[0]))
        self.report_var.set(row[1] or "")
        self.frequency_var.set(row[2] or "")
        self.owner_var.set(row[3] or "")
        self.visibility_var.set(row[4] or "")
        for entry in (self.report_entry, self.frequency_entry, self.owner_entry):
            entry.configure(style="TEntry")
        self._populate_backlog_options(get_transparencia_backlog_ids(self.editing_id))
        self.save_button.configure(text="Salvar alterações")

    def load_selected(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        selected_id = int(self.tree.item(selection[0], "values")[0])
        row = next((record for record in self.records if int(record[0]) == selected_id), None)
        if row:
            self._load_record(row)

    def edit_selected(self):
        if not self.tree.selection():
            messagebox.showinfo("Selecione um relatório", "Escolha uma linha para editar.", parent=self.root)
            return
        self.load_selected()

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Selecione um relatório", "Escolha uma linha para excluir.", parent=self.root)
            return
        record_id = int(self.tree.item(selection[0], "values")[0])
        if not messagebox.askyesno("Confirmar exclusão", f"Excluir o relatório {record_id} e seus vínculos?", parent=self.root):
            return
        try:
            delete_transparencia(record_id)
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível excluir", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()

    def new_record(self):
        self.clear_form(reset_filters=False)

    def clear_form(self, reset_filters=True):
        self.editing_id = None
        self.id_var.set(str(self._next_id()))
        self.report_var.set(self.report_entry.placeholder)
        self.frequency_var.set(self.frequency_entry.placeholder)
        self.owner_var.set(self.owner_entry.placeholder)
        self.visibility_var.set("")
        for entry in (self.report_entry, self.frequency_entry, self.owner_entry):
            entry.configure(style=PLACEHOLDER_STYLE)
        self.links_list.selection_clear(0, tk.END)
        self.id_entry.configure(state="readonly")
        self.save_button.configure(text="Salvar relatório")
        self.tree.selection_remove(self.tree.selection())
        if reset_filters:
            self.search_var.set("")
            self.apply_filters()