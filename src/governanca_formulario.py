import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from database import (
    delete_governanca,
    get_governance_backlog_options,
    get_governance_statuses,
    get_governanca_backlog_ids,
    list_governanca,
    save_governanca,
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
    ("id", "Id_Gov", 0, 90),
    ("policy", "Política", 1, 260),
    ("owner", "Responsável", 2, 140),
    ("period", "Periodicidade", 3, 150),
    ("status", "Status", 4, 120),
    ("links", "Histórias vinculadas", 5, 145),
)
TRANSFER_HEADERS = ("Id_Gov", "Politica", "Responsavel", "Periodicidade", "Status")


class GovernancaForm:
    def __init__(self, root, return_to_menu):
        self.root = root
        self.return_to_menu = return_to_menu
        self.status_options = get_governance_statuses() or ["ATIVA", "EM REVISÃO", "PLANEJADA"]
        self.backlog_options = get_governance_backlog_options()
        self.records = []
        self.editing_id = None

        self.id_var = tk.StringVar()
        self.policy_var = tk.StringVar()
        self.owner_var = tk.StringVar()
        self.period_var = tk.StringVar()
        self.status_var = tk.StringVar()
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
        tk.Label(title, text="SCRUM  /  GOVERNANÇA", bg="#19392f", fg="#a9c9bb", font=(FONT_NAME, 9, "bold")).pack(anchor="w")
        tk.Label(title, text="Políticas de governança", bg="#19392f", fg="#ffffff", font=(FONT_NAME, 21, "bold")).pack(anchor="w", pady=(2, 0))
        self.count_label = tk.Label(self.header, text="0 POLÍTICAS", bg="#19392f", fg="#d7e8df", font=(FONT_NAME, 10, "bold"))
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
        ttk.Label(self.form_body, text="DADOS DA POLÍTICA", style=MUTED_STYLE).pack(anchor="w")
        ttk.Label(self.form_body, text="Governança", style=SECTION_STYLE).pack(anchor="w", pady=(3, 14))
        self.id_entry = self._add_entry("Id_Gov", self.id_var, search_command=self.search_governance)
        self.id_entry.configure(state="readonly")
        self.policy_entry = self._add_entry("Política *", self.policy_var, "Ex.: POLÍTICA DE SEGURANÇA")
        self.owner_entry = self._add_entry("Responsável *", self.owner_var, "Ex.: EQUIPE DE DESENVOLVIMENTO")
        self.period_entry = self._add_entry("Periodicidade *", self.period_var, "Ex.: REVISÃO SEMESTRAL")
        for entry in (self.policy_entry, self.owner_entry, self.period_entry):
            entry.bind("<KeyRelease>", self._uppercase_entry)

        ttk.Label(self.form_body, text="Status *").pack(anchor="w", pady=(10, 5))
        self.status_combo = ttk.Combobox(self.form_body, textvariable=self.status_var, values=self.status_options, state="readonly")
        self.status_combo.pack(fill="x")

        ttk.Label(self.form_body, text="Histórias do Product_Backlog").pack(anchor="w", pady=(12, 5))
        link_frame = ttk.Frame(self.form_body, style=PANEL_STYLE)
        link_frame.pack(fill="both", expand=True)
        self.links_list = tk.Listbox(link_frame, selectmode=tk.MULTIPLE, exportselection=False, height=8,
                                     font=(FONT_NAME, 9), relief="flat", bg="#f7f9f7", fg="#23352f",
                                     selectbackground="#d9ebe3", selectforeground="#19392f",
                                     highlightthickness=1, highlightbackground="#dce5df")
        self.links_list.grid(row=0, column=0, sticky="nsew")
        link_scrollbar = ttk.Scrollbar(link_frame, orient="vertical", command=self.links_list.yview)
        link_scrollbar.grid(row=0, column=1, sticky="ns")
        self.links_list.configure(yscrollcommand=link_scrollbar.set)
        link_frame.columnconfigure(0, weight=1)
        link_frame.rowconfigure(0, weight=1)
        self._populate_backlog_options()

        ttk.Separator(self.form_body).pack(fill="x", pady=16)
        ttk.Button(self.form_body, text="Nova política", style=NEW_STYLE, command=self.new_record).pack(fill="x", pady=(0, 8))
        self.save_button = ttk.Button(self.form_body, text="Salvar política", style=PRIMARY_STYLE, command=self.save_record)
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
        entry.bind("<FocusIn>", lambda _event: GovernancaForm._clear_placeholder(entry, variable))
        entry.bind("<FocusOut>", lambda _event: GovernancaForm._restore_placeholder(entry, variable))

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

    def _populate_backlog_options(self, selected_ids=()):
        selected_ids = set(selected_ids)
        self.links_list.delete(0, tk.END)
        self.backlog_rows = self._get_backlog_options()
        for index, (backlog_id, module) in enumerate(self.backlog_rows):
            self.links_list.insert(tk.END, f"{backlog_id}  |  {module}")
            if backlog_id in selected_ids:
                self.links_list.selection_set(index)

    def _get_backlog_options(self):
        return get_governance_backlog_options()

    def _build_grid(self):
        ttk.Label(self.list_panel, text="VISÃO GERAL", style=MUTED_STYLE).grid(row=0, column=0, sticky="w")
        ttk.Label(self.list_panel, text="Políticas", style=SECTION_STYLE).grid(row=1, column=0, sticky="w", pady=(3, 12))
        filters = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        filters.grid(row=2, column=0, sticky="ew")
        filters.columnconfigure(0, weight=1)
        search = ttk.Entry(filters, textvariable=self.search_var)
        search.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        search.bind("<KeyRelease>", self._on_search)
        actions = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 10))
        ttk.Button(actions, text="Editar selecionada", command=self.edit_selected).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Excluir selecionada", command=self.delete_selected).pack(side="left", padx=(0, 6))
        transfer.add_transfer_buttons(actions, self)

        table_frame = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        table_frame.grid(row=4, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("id", "policy", "owner", "period", "status", "links")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "id": ("Id_Gov", 90), "policy": ("Política", 260), "owner": ("Responsável", 140),
            "period": ("Periodicidade", 150), "status": ("Status", 120), "links": ("Histórias vinculadas", 145),
        }
        for column, (heading, width) in headings.items():
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, minwidth=60, anchor="w", stretch=False)
        self.tree.tag_configure("even", background="#f7f9f7")
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.empty_label = ttk.Label(table_frame, text="Nenhuma política encontrada.", style=MUTED_STYLE)
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind("<Double-1>", self.load_selected)

    def refresh_records(self):
        try:
            self.records = list_governanca()
        except sqlite3.Error as error:
            messagebox.showerror("Erro ao carregar governança", str(error), parent=self.root)
            self.records = []
        self.apply_filters()
        if not self.editing_id:
            self.id_var.set(self._next_id())
            self.id_entry.configure(state="readonly")

    def _next_id(self):
        return max((int(row[0]) for row in self.records if row[0] is not None), default=0) + 1

    def export_csv(self):
        rows = [record[:5] for record in self.records]
        transfer.export_csv(self.root, "Exportar governança", "governanca.csv", TRANSFER_HEADERS, rows)

    def export_excel(self):
        rows = [record[:5] for record in self.records]
        transfer.export_excel(self.root, "Exportar governança", "governanca.xlsx", "Governança", TRANSFER_HEADERS, rows)

    def import_csv(self):
        rows = transfer.read_csv(self.root, "Importar governança")
        if rows is not None:
            self._import_rows(rows)

    def import_excel(self):
        rows = transfer.read_excel(self.root, "Importar governança")
        if rows is not None:
            self._import_rows(rows)

    def _import_rows(self, rows):
        existing = {str(record[1]).strip().casefold() for record in self.records}
        imported = skipped = 0
        for row in rows:
            data = transfer.normalized(row)
            politica = transfer.field(data, "politica", "política")
            if not politica or politica.casefold() in existing:
                skipped += 1
                continue
            try:
                save_governanca(None, politica.upper(),
                                transfer.field(data, "responsavel", "responsável").upper(),
                                transfer.field(data, "periodicidade").upper(),
                                transfer.field(data, "status").upper(), [])
                existing.add(politica.casefold())
                imported += 1
            except sqlite3.Error:
                skipped += 1
        self.refresh_records()
        transfer.report(self.root, imported, skipped)

    def _selected_backlog_ids(self):
        return [self.backlog_rows[index][0] for index in self.links_list.curselection()]

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
            values = (*row[:5], f"{row[5]} histórias")
            self.tree.insert("", "end", iid=str(index), values=values, tags=("even" if index % 2 == 0 else "odd",))
        self.count_label.configure(text=f"{len(filtered)} POLÍTICAS" if len(filtered) != 1 else "1 POLÍTICA")
        visible_rows = [tuple(row[:5]) + (f"{row[5]} histórias",) for row in self.records]
        fit_tree_columns(self.tree, self.root, GRID_COLUMNS, visible_rows)

    def search_governance(self):
        value = simpledialog.askinteger("Pesquisar política", "Informe o Id_Gov:", parent=self.root, minvalue=1)
        if value is None:
            return
        record = next((row for row in self.records if int(row[0]) == value), None)
        if record is None:
            messagebox.showinfo("Política não encontrada", f"Id_Gov {value} não existe.", parent=self.root)
            return
        self._load_record(record)

    def save_record(self):
        policy = self.policy_var.get().strip()
        owner = self.owner_var.get().strip()
        period = self.period_var.get().strip()
        status = self.status_var.get().strip()
        for entry, value in ((self.policy_entry, policy), (self.owner_entry, owner), (self.period_entry, period)):
            if value == getattr(entry, "placeholder", None):
                if entry is self.policy_entry:
                    policy = ""
                elif entry is self.owner_entry:
                    owner = ""
                else:
                    period = ""
        missing = [name for name, value in (("Política", policy), ("Responsável", owner), ("Periodicidade", period), ("Status", status)) if not value]
        if missing:
            messagebox.showwarning("Campos obrigatórios", f"Preencha: {', '.join(missing)}.", parent=self.root)
            return
        try:
            record_id = save_governanca(
                self.editing_id,
                policy.upper(), owner.upper(), period.upper(), status.upper(),
                self._selected_backlog_ids(),
            )
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível salvar", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()
        messagebox.showinfo("Governança atualizada", f"Política {record_id} salva com seus vínculos.", parent=self.root)

    def _load_record(self, row):
        self.editing_id = int(row[0])
        self.id_var.set(str(row[0]))
        self.policy_var.set(row[1] or "")
        self.owner_var.set(row[2] or "")
        self.period_var.set(row[3] or "")
        self.status_var.set(row[4] or "")
        for entry in (self.policy_entry, self.owner_entry, self.period_entry):
            entry.configure(style="TEntry")
        self._populate_backlog_options(get_governanca_backlog_ids(self.editing_id))
        self.save_button.configure(text="Salvar alterações")

    def load_selected(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        selected_id = int(self.tree.item(selection[0], "values")[0])
        record = next((row for row in self.records if int(row[0]) == selected_id), None)
        if record:
            self._load_record(record)

    def edit_selected(self):
        if not self.tree.selection():
            messagebox.showinfo("Selecione uma política", "Escolha uma linha para editar.", parent=self.root)
            return
        self.load_selected()

    def search_policy(self):
        value = simpledialog.askinteger("Pesquisar política", "Informe o Id_Gov:", parent=self.root, minvalue=1)
        if value is None:
            return
        record = next((row for row in self.records if int(row[0]) == value), None)
        if record:
            self._load_record(record)
        else:
            messagebox.showinfo("Política não encontrada", f"Id_Gov {value} não existe.", parent=self.root)

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Selecione uma política", "Escolha uma linha para excluir.", parent=self.root)
            return
        policy_id = int(self.tree.item(selection[0], "values")[0])
        if not messagebox.askyesno("Confirmar exclusão", f"Excluir a política {policy_id} e seus vínculos?", parent=self.root):
            return
        try:
            delete_governanca(policy_id)
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
        self.policy_var.set(self.policy_entry.placeholder)
        self.owner_var.set(self.owner_entry.placeholder)
        self.period_var.set(self.period_entry.placeholder)
        self.status_var.set("")
        for entry in (self.policy_entry, self.owner_entry, self.period_entry):
            entry.configure(style=PLACEHOLDER_STYLE)
        self.links_list.selection_clear(0, tk.END)
        self.id_entry.configure(state="readonly")
        self.save_button.configure(text="Salvar política")
        self.tree.selection_remove(self.tree.selection())
        if reset_filters:
            self.search_var.set("")
            self.apply_filters()