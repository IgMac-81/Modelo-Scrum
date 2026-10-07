import re
import sqlite3
from datetime import date
import tkinter as tk
 
from tkinter import messagebox, simpledialog, ttk

from database import (
    delete_history_sprint,
    get_history_sprint_titles,
    get_sprint_task_for_history,
    get_status_sprint,
    insert_history_sprint,
    list_history_sprints,
    update_history_sprint,
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
TRANSFER_HEADERS = (
    "Id_Historico", "Id_Task", "Titulo_Sprint", "User_Story", "Data_Inicio", "Data_Fim",
    "Pontos_Planejados", "Pontos_Entregues", "Velocity", "Capacidade_Horas", "Status_Sprint",
)


class HistoricoSprintsForm:
    def __init__(self, root, return_to_menu):
        self.root = root
        self.return_to_menu = return_to_menu
        self.status_data = get_status_sprint()
        self.sprint_titles = get_history_sprint_titles()
        self.records = []
        self.editing_id = None

        self.history_id_var = tk.StringVar()
        self.task_id_var = tk.StringVar()
        self.sprint_title_var = tk.StringVar()
        self.user_story_var = tk.StringVar()
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.planned_points_var = tk.StringVar()
        self.delivered_points_var = tk.StringVar(value="0")
        self.velocity_var = tk.StringVar(value="0,0%")
        self.capacity_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="TODOS")

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
        tk.Label(title, text="SCRUM  /  HISTÓRICO DE SPRINTS", bg="#19392f", fg="#a9c9bb", font=(FONT_NAME, 9, "bold")).pack(anchor="w")
        tk.Label(title, text="Histórico de execução", bg="#19392f", fg="#ffffff", font=(FONT_NAME, 21, "bold")).pack(anchor="w", pady=(2, 0))
        self.count_label = tk.Label(self.header, text="0 REGISTROS", bg="#19392f", fg="#d7e8df", font=(FONT_NAME, 10, "bold"))
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
        ttk.Label(self.form_body, text="DADOS DO HISTÓRICO", style=MUTED_STYLE).pack(anchor="w")
        ttk.Label(self.form_body, text="Registro de sprint", style=SECTION_STYLE).pack(anchor="w", pady=(3, 14))

        self.history_id_entry = self._add_entry("Id_Historico", self.history_id_var, search_command=self.search_history)
        self.history_id_entry.configure(state="readonly")
        self.task_id_entry = self._add_entry("Id_Task *", self.task_id_var, "Ex.: SB-101", self.search_task)
        self.task_id_entry.bind("<KeyRelease>", self._uppercase_key)

        sprint_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        sprint_header.pack(fill="x", pady=(10, 5))
        ttk.Label(sprint_header, text="Titulo_Sprint *").pack(side="left")
        ttk.Button(sprint_header, text="ⓘ", style=ICON_STYLE, command=self.show_sprint_source).pack(side="right")
        self.sprint_combo = ttk.Combobox(self.form_body, textvariable=self.sprint_title_var, values=self.sprint_titles, state="readonly")
        self.sprint_combo.pack(fill="x")

        story_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        story_header.pack(fill="x", pady=(10, 5))
        ttk.Label(story_header, text="User_Story").pack(side="left")
        ttk.Button(story_header, text="ⓘ", style=ICON_STYLE, command=self.show_task_source).pack(side="right")
        self.user_story_entry = self._add_entry("", self.user_story_var)
        self.user_story_entry.configure(state="readonly")

        self.start_date_entry = self._add_entry("Data_Inicio (DD/MM/AAAA)", self.start_date_var, "Digite somente números")
        self.end_date_entry = self._add_entry("Data_Fim (DD/MM/AAAA)", self.end_date_var, "Digite somente números")
        for entry in (self.start_date_entry, self.end_date_entry):
            entry.bind("<KeyRelease>", self._format_date)
            entry.bind("<KeyPress-BackSpace>", self._delete_date_digits)
            entry.bind("<KeyPress-Delete>", self._delete_date_digits)

        planned_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        planned_header.pack(fill="x", pady=(10, 5))
        ttk.Label(planned_header, text="Pontos_Planejados").pack(side="left")
        ttk.Button(planned_header, text="ⓘ", style=ICON_STYLE, command=self.show_task_source).pack(side="right")
        self.planned_entry = self._add_entry("", self.planned_points_var)
        self.planned_entry.configure(state="readonly")

        delivered_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        delivered_header.pack(fill="x", pady=(10, 5))
        ttk.Label(delivered_header, text="Pontos_Entregues").pack(side="left")
        ttk.Button(delivered_header, text="ⓘ", style=ICON_STYLE, command=self.show_delivered_help).pack(side="right")
        self.delivered_entry = self._add_entry("", self.delivered_points_var)
        self.delivered_entry.configure(state="readonly")

        velocity_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        velocity_header.pack(fill="x", pady=(10, 5))
        ttk.Label(velocity_header, text="Velocity_%").pack(side="left")
        ttk.Button(velocity_header, text="ⓘ", style=ICON_STYLE, command=self.show_velocity_help).pack(side="right")
        self.velocity_entry = self._add_entry("", self.velocity_var)
        self.velocity_entry.configure(state="readonly")

        capacity_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        capacity_header.pack(fill="x", pady=(10, 5))
        ttk.Label(capacity_header, text="Capacidade_Horas").pack(side="left")
        ttk.Button(capacity_header, text="ⓘ", style=ICON_STYLE, command=self.show_task_source).pack(side="right")
        self.capacity_entry = self._add_entry("", self.capacity_var)
        self.capacity_entry.configure(state="readonly")

        status_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        status_header.pack(fill="x", pady=(10, 5))
        ttk.Label(status_header, text="Status_Sprint *").pack(side="left")
        ttk.Button(status_header, text="ⓘ Orientação", command=self.show_status_help).pack(side="right")
        self.status_combo = ttk.Combobox(self.form_body, textvariable=self.status_var, values=list(self.status_data), state="readonly")
        self.status_combo.pack(fill="x", pady=(5, 0))
        self.status_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_delivery())

        ttk.Separator(self.form_body).pack(fill="x", pady=16)
        ttk.Button(self.form_body, text="Novo histórico", style=NEW_STYLE, command=self.new_record).pack(fill="x", pady=(0, 8))
        self.save_button = ttk.Button(self.form_body, text="Salvar histórico", style=PRIMARY_STYLE, command=self.save_record)
        self.save_button.pack(fill="x")
        ttk.Button(self.form_body, text="Limpar formulário", command=self.clear_form).pack(fill="x", pady=(8, 0))

    def _add_entry(self, label, variable, placeholder=None, search_command=None):
        if label:
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
    def _uppercase_key(event):
        entry = event.widget
        value = entry.get()
        uppercase = value.upper()
        if uppercase != value:
            cursor = entry.index(tk.INSERT)
            entry.delete(0, tk.END)
            entry.insert(0, uppercase)
            entry.icursor(min(cursor, len(uppercase)))

    @staticmethod
    def _set_placeholder(entry, variable, placeholder):
        entry.placeholder = placeholder
        entry.configure(style=PLACEHOLDER_STYLE)
        variable.set(placeholder)
        entry.bind("<FocusIn>", lambda _event: HistoricoSprintsForm._clear_placeholder(entry, variable))
        entry.bind("<FocusOut>", lambda _event: HistoricoSprintsForm._restore_placeholder(entry, variable))

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

    def _build_grid(self):
        ttk.Label(self.list_panel, text="VISÃO GERAL", style=MUTED_STYLE).grid(row=0, column=0, sticky="w")
        ttk.Label(self.list_panel, text="Histórico de sprints", style=SECTION_STYLE).grid(row=1, column=0, sticky="w", pady=(3, 12))
        filters = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        filters.grid(row=2, column=0, sticky="ew")
        filters.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(filters, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self._on_search)
        ttk.Combobox(filters, textvariable=self.status_filter_var, values=["TODOS", *self.status_data], state="readonly", width=20).grid(row=0, column=1)
        self.status_filter_var.trace_add("write", lambda *_args: self.apply_filters())

        actions = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 10))
        ttk.Button(actions, text="Editar selecionado", command=self.edit_selected).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Excluir selecionado", command=self.delete_selected).pack(side="left", padx=(0, 6))
        transfer.add_transfer_buttons(actions, self)

        table_frame = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        table_frame.grid(row=4, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("id", "task", "sprint", "story", "start", "end", "planned", "delivered", "velocity", "capacity", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "id": ("Id_Historico", 90), "task": ("Id_Task", 90), "sprint": ("Sprint", 110),
            "story": ("User_Story", 220), "start": ("Início", 100), "end": ("Fim", 100),
            "planned": ("Planejados", 90), "delivered": ("Entregues", 90), "velocity": ("Velocity_%", 90),
            "capacity": ("Capacidade", 100), "status": ("Status", 130),
        }
        for key, (heading, width) in headings.items():
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, minwidth=60, anchor="w", stretch=False)
        self.tree.tag_configure("even", background="#f7f9f7")
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.empty_label = ttk.Label(table_frame, text="Nenhum histórico encontrado para os filtros atuais.", style=MUTED_STYLE)
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind("<Double-1>", self.load_selected)
        ttk.Label(self.list_panel, text="Selecione um histórico ou dê dois cliques para editar.", style=MUTED_STYLE).grid(row=5, column=0, sticky="w", pady=(9, 0))

    def refresh_records(self):
        try:
            self.records = list_history_sprints()
        except sqlite3.Error as error:
            messagebox.showerror("Erro ao carregar histórico", str(error), parent=self.root)
            self.records = []
        self.apply_filters()
        if not self.editing_id:
            self.history_id_var.set(self._next_history_id())
            self.history_id_entry.configure(state="readonly")

    def _next_history_id(self):
        return max((int(row[0]) for row in self.records if row[0] is not None), default=0) + 1

    def export_csv(self):
        transfer.export_csv(self.root, "Exportar histórico", "historico_sprints.csv", TRANSFER_HEADERS, self.records)

    def export_excel(self):
        transfer.export_excel(self.root, "Exportar histórico", "historico_sprints.xlsx", "Histórico", TRANSFER_HEADERS, self.records)

    def import_csv(self):
        rows = transfer.read_csv(self.root, "Importar histórico")
        if rows is not None:
            self._import_rows(rows)

    def import_excel(self):
        rows = transfer.read_excel(self.root, "Importar histórico")
        if rows is not None:
            self._import_rows(rows)

    def _import_rows(self, rows):
        next_id = self._next_history_id()
        imported = skipped = 0
        for row in rows:
            data = transfer.normalized(row)
            id_task = transfer.field(data, "id_task", "tarefa")
            if not id_task:
                skipped += 1
                continue
            try:
                planned_text = transfer.field(data, "pontos_planejados", "planejados").replace(",", ".")
                delivered_text = transfer.field(data, "pontos_entregues", "entregues").replace(",", ".")
                velocity_text = transfer.field(data, "velocity_%", "velocity").replace("%", "").replace(",", ".")
                insert_history_sprint(
                    next_id, id_task.upper(),
                    transfer.field(data, "titulo_sprint", "sprint").upper(),
                    transfer.field(data, "user_story", "história", "historia").upper(),
                    transfer.field(data, "data_inicio", "início", "inicio"),
                    transfer.field(data, "data_fim", "fim"),
                    int(float(planned_text)) if planned_text else 0,
                    int(float(delivered_text)) if delivered_text else 0,
                    float(velocity_text) if velocity_text else None,
                    transfer.field(data, "capacidade_horas", "capacidade"),
                    transfer.field(data, "status_sprint", "status").upper(),
                )
                next_id += 1
                imported += 1
            except (ValueError, TypeError, sqlite3.Error):
                skipped += 1
        self.refresh_records()
        transfer.report(self.root, imported, skipped)

    def _on_search(self, event=None):
        if event is not None:
            value = self.search_var.get().upper()
            if value != self.search_var.get():
                self.search_var.set(value)
        self.apply_filters()

    def apply_filters(self):
        query = self.search_var.get().strip().casefold()
        status = self.status_filter_var.get()
        filtered = [row for row in self.records if
                    (not query or query in " ".join(str(value or "") for value in row).casefold()) and
                    (status == "TODOS" or row[10] == status)]
        self.tree.delete(*self.tree.get_children())
        if filtered:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

        for index, row in enumerate(filtered):
            velocity = self._format_velocity(row[8])
            values = tuple(row[:8]) + (velocity, row[9], row[10])
            self.tree.insert("", "end", iid=str(index), values=values, tags=("even" if index % 2 == 0 else "odd",))
        self._fit_columns(filtered)
        self.count_label.configure(text=f"{len(filtered)} REGISTROS" if len(filtered) != 1 else "1 REGISTRO")


    def _fit_columns(self, rows):
        columns = (
            ("id", "Id_Historico", 0, 110), ("task", "Id_Task", 1, 90), ("sprint", "Sprint", 2, 110),
            ("story", "User_Story", 3, 220), ("start", "Início", 4, 110), ("end", "Fim", 5, 110),
            ("planned", "Planejados", 6, 100), ("delivered", "Entregues", 7, 100),
            ("velocity", "Velocity_%", 8, 100), ("capacity", "Capacidade", 9, 115), ("status", "Status", 10, 130),
        )
        rows = [tuple(row[:8]) + (self._format_velocity(row[8]), row[9], row[10]) for row in rows]
        fit_tree_columns(self.tree, self.root, columns, rows)

    @staticmethod
    def _format_velocity(value):
        if value is None or value == "":
            return "0,0%"
        if isinstance(value, str):
            text = value.strip().replace("%", "").replace(",", ".")
            try:
                number = float(text)
            except ValueError:
                return value
        else:
            number = float(value)
        return f"{number:.1f}%".replace(".", ",")

    def search_task(self):
        task_id = simpledialog.askstring("Pesquisar Id_Task", "Informe o Id_Task (ex.: SB-101):", parent=self.root)
        if task_id:
            task_id = task_id.strip().upper()
            self.task_id_var.set(task_id)
            self._load_task_details()
            record = next((row for row in self.records if str(row[1]).upper() == task_id), None)
            if record:
                self._load_record(record)
            elif not get_sprint_task_for_history(task_id):
                messagebox.showinfo("Tarefa não encontrada", f"Id_Task {task_id} não existe em Sprints_Backlog.", parent=self.root)

    def search_history(self):
        value = simpledialog.askinteger("Pesquisar histórico", "Informe Id_Historico:", parent=self.root, minvalue=1)
        if value is None:
            return
        record = next((row for row in self.records if int(row[0]) == value), None)
        if record is None:
            messagebox.showinfo("Histórico não encontrado", f"Id_Historico {value} não existe.", parent=self.root)
            return
        self._load_record(record)

    def _load_task_details(self, _event=None):
        task = get_sprint_task_for_history(self.task_id_var.get().strip().upper())
        if task is None:
            self.sprint_title_var.set("")
            self.user_story_var.set("")
            self.planned_points_var.set("")
            self.capacity_var.set("")
            self._update_delivery()
            return
        self.task_id_var.set(task[0])
        self.sprint_title_var.set(task[1] or "")
        self.user_story_var.set(task[2] or "")
        self.planned_points_var.set("" if task[3] is None else str(task[3]))
        self.capacity_var.set(task[4] or "")
        self._update_delivery()

    def show_sprint_source(self):
        messagebox.showinfo("Origem da sprint", "As opções vêm dos títulos sem duplicidade em Sprints_Backlog.", parent=self.root)

    def show_task_source(self):
        messagebox.showinfo("Origem da tarefa", "User_Story, Pontos_Planejados e Capacidade_Horas são carregados de Sprints_Backlog após informar Id_Task.", parent=self.root)

    def show_delivered_help(self):
        messagebox.showinfo("Pontos entregues", "CONCLUÍDO retorna Pontos_Planejados. Nos outros status, Pontos_Entregues é zero.", parent=self.root)

    def show_velocity_help(self):
        messagebox.showinfo("Cálculo de velocity", "Velocity_% = (Pontos_Entregues ÷ Pontos_Planejados) × 100. Se os pontos planejados forem zero, o resultado é 0,0%.", parent=self.root)

    def show_status_help(self):
        status = self.status_var.get().strip()
        details = self.status_data.get(status)
        if not details:
            messagebox.showinfo("Orientação de status", "Selecione um Status_Sprint para consultar as orientações.", parent=self.root)
            return
        messagebox.showinfo(f"Status: {status}", f"Significado: {details.get('Significado', '')}\n\nQuando usar: {details.get('Quando_usar', '')}", parent=self.root)

    def _update_delivery(self):
        try:
            planned = int(self.planned_points_var.get() or 0)
        except ValueError:
            planned = 0
        delivered = planned if self.status_var.get().strip().upper() == "CONCLUÍDO" else 0
        velocity = delivered / planned * 100 if planned > 0 else 0
        self.delivered_points_var.set(str(delivered))
        self.velocity_var.set(f"{velocity:.1f}%".replace(".", ","))

    @staticmethod
    def _format_date(event):
        entry = event.widget
        current = entry.get()
        cursor = entry.index(tk.INSERT)
        digits_before = len(re.sub(r"\D", "", current[:cursor]))
        digits = re.sub(r"\D", "", current)[:8]
        if len(digits) <= 2:
            formatted = digits
        elif len(digits) <= 4:
            formatted = f"{digits[:2]}/{digits[2:]}"
        else:
            formatted = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"
        if current != formatted:
            entry.delete(0, tk.END)
            entry.insert(0, formatted)
            separators = int(digits_before > 2) + int(digits_before > 4)
            entry.icursor(min(digits_before + separators, len(formatted)))

    @staticmethod
    def _delete_date_digits(event):
        entry = event.widget
        current = entry.get()
        cursor = entry.index(tk.INSERT)
        try:
            selection_start, selection_end = entry.index("sel.first"), entry.index("sel.last")
        except tk.TclError:
            selection_start = selection_end = None
        if selection_start is not None:
            if selection_start == 0 and selection_end == len(current):
                updated = ""
            else:
                characters = list(current)
                for index in range(selection_start, selection_end):
                    if characters[index].isdigit():
                        characters[index] = "0"
                updated = "".join(characters)
            cursor = selection_start
        else:
            backwards = event.keysym == "BackSpace"
            target = cursor - 1 if backwards else cursor
            step = -1 if backwards else 1
            while 0 <= target < len(current) and not current[target].isdigit():
                target += step
            if not 0 <= target < len(current):
                return "break"
            updated = f"{current[:target]}0{current[target + 1:]}"
            cursor = target
        entry.delete(0, tk.END)
        entry.insert(0, updated)
        entry.icursor(min(cursor, len(updated)))
        return "break"

    def save_record(self):
        try:
            history_id = int(self.history_id_var.get())
            task_id = self.task_id_var.get().strip().upper()
            task = get_sprint_task_for_history(task_id)
            if task is None:
                messagebox.showwarning("Id_Task inválido", "Informe um Id_Task existente em Sprints_Backlog.", parent=self.root)
                return
            status = self.status_var.get().strip().upper()
            if not status:
                messagebox.showwarning("Status obrigatório", "Selecione um Status_Sprint.", parent=self.root)
                return
            start_text = self.start_date_var.get().strip()
            end_text = self.end_date_var.get().strip()
            for label, value, entry in (("Data_Inicio", start_text, self.start_date_entry), ("Data_Fim", end_text, self.end_date_entry)):
                if value == getattr(entry, "placeholder", None):
                    continue
                if value:
                    day, month, year = map(int, value.split("/"))
                    date(year, month, day)
            planned = int(task[3] or 0)
            delivered = planned if status == "CONCLUÍDO" else 0
            velocity = delivered / planned * 100 if planned > 0 else 0.0
            velocity_text = f"{velocity:.1f}%".replace(".", ",")
            start_text = None if start_text == getattr(self.start_date_entry, "placeholder", None) or not start_text else start_text
            end_text = None if end_text == getattr(self.end_date_entry, "placeholder", None) or not end_text else end_text
        except (ValueError, TypeError) as error:
            messagebox.showwarning("Dados inválidos", f"Verifique Id_Historico, os pontos e as datas DD/MM/AAAA.\n{error}", parent=self.root)
            return

        values = (task_id, task[1], task[2], start_text, end_text, planned, delivered,
                  velocity_text, task[4], status)
        try:
            if self.editing_id is None:
                insert_history_sprint(history_id, *values)
                result_message = f"Histórico {history_id} criado."
            else:
                update_history_sprint(self.editing_id, *values)
                result_message = f"Histórico {self.editing_id} atualizado."
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível salvar", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()
        messagebox.showinfo("Histórico atualizado", result_message, parent=self.root)

    def _load_record(self, row):
        self.editing_id = int(row[0])
        self.history_id_var.set(str(row[0]))
        self.task_id_var.set(row[1] or "")
        self.sprint_title_var.set(row[2] or "")
        self.user_story_var.set(row[3] or "")
        self.start_date_var.set(row[4] or "")
        self.end_date_var.set(row[5] or "")
        self.planned_points_var.set("" if row[6] is None else str(row[6]))
        self.delivered_points_var.set("" if row[7] is None else str(row[7]))
        self.velocity_var.set(self._format_velocity(row[8]))
        self.capacity_var.set(row[9] or "")
        self.status_var.set(row[10] or "")
        for entry in (self.task_id_entry, self.start_date_entry, self.end_date_entry):
            entry.configure(style="TEntry")
        self.save_button.configure(text="Salvar alterações")

    def load_selected(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        selected_id = self.tree.item(selection[0], "values")[0]
        row = next((record for record in self.records if str(record[0]) == str(selected_id)), None)
        if row:
            self._load_record(row)

    def edit_selected(self):
        if not self.tree.selection():
            messagebox.showinfo("Selecione um histórico", "Escolha uma linha para editar.", parent=self.root)
            return
        self.load_selected()

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Selecione um histórico", "Escolha uma linha para excluir.", parent=self.root)
            return
        history_id = int(self.tree.item(selection[0], "values")[0])
        if not messagebox.askyesno("Confirmar exclusão", f"Excluir o histórico {history_id}?", parent=self.root):
            return
        try:
            delete_history_sprint(history_id)
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível excluir", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()

    def new_record(self):
        self.clear_form(reset_filters=False)

    def clear_form(self, reset_filters=True):
        self.editing_id = None
        self.history_id_var.set(str(self._next_history_id()))
        self.task_id_var.set("Ex.: SB-101")
        self.sprint_title_var.set("")
        self.user_story_var.set("")
        self.start_date_var.set("Digite somente números")
        self.end_date_var.set("Digite somente números")
        self.planned_points_var.set("")
        self.delivered_points_var.set("0")
        self.velocity_var.set("0,0%")
        self.capacity_var.set("")
        self.status_var.set("")
        for entry in (self.task_id_entry, self.start_date_entry, self.end_date_entry):
            entry.configure(style=PLACEHOLDER_STYLE)
        self.history_id_entry.configure(state="readonly")
        self.save_button.configure(text="Salvar histórico")
        self.tree.selection_remove(self.tree.selection())
        if reset_filters:
            self.search_var.set("")
            self.status_filter_var.set("TODOS")