import re
import sqlite3
from datetime import date
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from database import (
    delete_sprint_backlog,
    get_fibonacci,
    get_product_backlog_stories,
    get_status_sprint,
    insert_sprint_backlog,
    list_sprint_backlog,
    update_sprint_backlog,
)
from grid_sizing import fit_tree_columns
import data_transfer as transfer


PANEL_STYLE = "Panel.TFrame"
MUTED_STYLE = "Muted.TLabel"
SECTION_STYLE = "Section.TLabel"
PRIMARY_STYLE = "Primary.TButton"
NEW_STYLE = "NewStory.TButton"
ICON_STYLE = "Icon.TButton"
BUTTON_WIDTH = 18
FONT_NAME = "Segoe UI"
PLACEHOLDER_STYLE = "Placeholder.TEntry"
TRANSFER_HEADERS = (
    "Id_Task", "Titulo_Sprint", "User_Story", "Subtarefa_Tecnica", "Responsavel",
    "Story_Points", "Horas_Estimadas", "Horas_Gastas", "Horas_Restantes", "Status", "Data_Conclusao",
)


class SprintBacklogForm:
    def __init__(self, root, return_to_menu):
        self.root = root
        self.return_to_menu = return_to_menu
        self.status_data = get_status_sprint()
        self.story_options = get_product_backlog_stories()
        self.story_map = {str(row[0]).upper(): row for row in self.story_options}
        self.fibonacci_data = get_fibonacci()
        self.records = []
        self.editing_id = None
        self.search_mode = "all"

        self.id_var = tk.StringVar()
        self.sprint_var = tk.StringVar()
        self.story_var = tk.StringVar()
        self.subtask_var = tk.StringVar()
        self.owner_var = tk.StringVar()
        self.points_var = tk.StringVar()
        self.estimated_var = tk.StringVar()
        self.spent_var = tk.StringVar()
        self.remaining_var = tk.StringVar(value="00:00")
        self.status_var = tk.StringVar()
        self.completion_var = tk.StringVar()
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
        tk.Label(title, text="SCRUM  /  SPRINT BACKLOG", bg="#19392f", fg="#a9c9bb", font=(FONT_NAME, 9, "bold")).pack(anchor="w")
        tk.Label(title, text="Tarefas da sprint", bg="#19392f", fg="#ffffff", font=(FONT_NAME, 21, "bold")).pack(anchor="w", pady=(2, 0))
        self.count_label = tk.Label(self.header, text="0 TAREFAS", bg="#19392f", fg="#d7e8df", font=(FONT_NAME, 10, "bold"))
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
        canvas_window = canvas.create_window((0, 0), window=self.form_body, anchor="nw")
        self.form_body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_window, width=event.width))

        self.list_panel = ttk.Frame(content, style=PANEL_STYLE, padding=18)
        self.list_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self.list_panel.columnconfigure(0, weight=1)
        self.list_panel.rowconfigure(4, weight=1)
        self._build_form()
        self._build_grid()

    def _build_form(self):
        ttk.Label(self.form_body, text="DETALHES DA TAREFA", style=MUTED_STYLE).pack(anchor="w")
        ttk.Label(self.form_body, text="Cadastro", style=SECTION_STYLE).pack(anchor="w", pady=(3, 14))

        self.id_entry = self._add_entry("Id_Task *", self.id_var, search_command=self.search_task)
        self.id_entry.configure(state="readonly")
        self.sprint_entry = self._add_entry("Título da sprint *", self.sprint_var, "Ex.: SPRINT 4", self.search_sprint)
        self._uppercase_binding(self.sprint_entry)

        story_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        story_header.pack(fill="x", pady=(10, 5))
        ttk.Label(story_header, text="User_Story *").pack(side="left")
        ttk.Button(story_header, text="ⓘ", style=ICON_STYLE, command=self.show_story_help).pack(side="right")
        story_row = ttk.Frame(self.form_body, style=PANEL_STYLE)
        story_row.pack(fill="x")
        self.story_entry = ttk.Entry(story_row, textvariable=self.story_var)
        self.story_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(story_row, text="🔍", style=ICON_STYLE, command=self.choose_story).pack(side="left", padx=(6, 0))
        self.story_entry.placeholder = "Ex.: US-01 USUÁRIOS"
        self._set_placeholder(self.story_entry, self.story_var, self.story_entry.placeholder)
        self.story_entry.bind("<KeyRelease>", self._on_story_key)
        self.story_entry.bind("<FocusOut>", self._resolve_story, add="+")

        self.subtask_entry = self._add_entry("Subtarefa técnica *", self.subtask_var, "Ex.: CRIAR TELA DE CADASTRO")
        self._uppercase_binding(self.subtask_entry)
        ttk.Button(self.form_body, text="ⓘ Orientação da subtarefa", command=self.show_subtask_help).pack(anchor="e", pady=(3, 0))

        self.owner_entry = self._add_entry("Responsável", self.owner_var, "Ex.: ANA SILVA")
        self._uppercase_binding(self.owner_entry)
        points_row = ttk.Frame(self.form_body, style=PANEL_STYLE)
        points_row.pack(fill="x", pady=(10, 5))
        ttk.Label(points_row, text="Story_Points").pack(side="left")
        ttk.Button(points_row, text="ⓘ", style=ICON_STYLE, command=self.show_points_info).pack(side="right")
        self.points_entry = ttk.Entry(self.form_body, textvariable=self.points_var, state="readonly")
        self.points_entry.pack(fill="x")

        self.estimated_entry = self._add_entry("Horas estimadas (HH:MM)", self.estimated_var)
        self.spent_entry = self._add_entry("Horas gastas (HH:MM)", self.spent_var)
        for entry in (self.estimated_entry, self.spent_entry):
            entry.bind("<FocusIn>", self._prepare_time_entry)
            entry.bind("<KeyPress-BackSpace>", self._on_masked_delete)
            entry.bind("<KeyPress-Delete>", self._on_masked_delete)
            entry.bind("<KeyRelease>", self._on_time_key)
            entry.bind("<FocusOut>", self._normalize_time_entry)
        self.remaining_entry = self._add_entry("Horas restantes (automático)", self.remaining_var)
        self.remaining_entry.configure(state="readonly")

        status_header = ttk.Frame(self.form_body, style=PANEL_STYLE)
        status_header.pack(fill="x", pady=(10, 5))
        ttk.Label(status_header, text="Status *").pack(side="left")
        ttk.Button(status_header, text="ⓘ Orientação", command=self.show_status_info).pack(side="right")
        self.status_combo = ttk.Combobox(self.form_body, textvariable=self.status_var, values=list(self.status_data), state="readonly")
        self.status_combo.pack(fill="x")
        self.status_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_remaining())

        self.date_entry = self._add_entry("Data de conclusão (DD/MM/AAAA)", self.completion_var, "DD/MM/AAAA")
        self.date_entry.bind("<KeyPress-BackSpace>", self._on_masked_delete)
        self.date_entry.bind("<KeyPress-Delete>", self._on_masked_delete)
        self.date_entry.bind("<KeyRelease>", self._on_date_key)

        ttk.Separator(self.form_body).pack(fill="x", pady=16)
        ttk.Button(self.form_body, text="Nova tarefa", style=NEW_STYLE, command=self.new_record).pack(fill="x", pady=(0, 8))
        self.save_button = ttk.Button(self.form_body, text="Salvar tarefa", style=PRIMARY_STYLE, command=self.save_record)
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
        entry.bind("<FocusIn>", lambda _event: SprintBacklogForm._clear_placeholder(entry, variable))
        entry.bind("<FocusOut>", lambda _event: SprintBacklogForm._restore_placeholder(entry, variable))

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

    def _uppercase_binding(self, entry):
        entry.bind("<KeyRelease>", self._uppercase_key)

    @staticmethod
    def _uppercase_key(event):
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

    def _on_story_key(self, _event=None):
        value = self.story_var.get()
        if value != getattr(self.story_entry, "placeholder", None):
            uppercase = value.upper()
            if uppercase != value:
                self.story_var.set(uppercase)
            self._resolve_story()

    def _resolve_story(self, _event=None):
        value = self.story_var.get().strip().upper()
        story_id = value[:5]
        story = self.story_map.get(story_id)
        if story is None:
            self.points_var.set("")
            return
        self.story_var.set(f"{story[0]} {story[1]}".upper())
        self.points_var.set("" if story[2] is None else str(story[2]))

    def choose_story(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Selecionar User_Story")
        dialog.geometry("560x440")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        query_var = tk.StringVar()
        search = ttk.Entry(dialog, textvariable=query_var)
        search.grid(row=0, column=0, sticky="ew", padx=14, pady=14)
        tree = ttk.Treeview(dialog, columns=("id", "module", "points"), show="headings", selectmode="browse")
        for column, heading, width in (("id", "Id", 100), ("module", "Módulo", 300), ("points", "Story Points", 100)):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="w")
        tree.grid(row=1, column=0, sticky="nsew", padx=14)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 14))
        tree.configure(yscrollcommand=scrollbar.set)

        def populate(*_args):
            query = query_var.get().casefold()
            tree.delete(*tree.get_children())
            for index, story in enumerate(self.story_options):
                if query and query not in f"{story[0]} {story[1]}".casefold():
                    continue
                tree.insert("", "end", iid=str(index), values=(story[0], story[1], story[2]))

        def select_story(_event=None):
            selection = tree.selection()
            if not selection:
                return
            row = tree.item(selection[0], "values")
            self.story_var.set(f"{row[0]} {row[1]}".upper())
            self.points_var.set(str(row[2]) if row[2] is not None else "")
            self._update_remaining()
            dialog.destroy()

        query_var.trace_add("write", populate)
        tree.bind("<Double-1>", select_story)
        ttk.Button(dialog, text="Usar história selecionada", style=PRIMARY_STYLE, command=select_story).grid(row=2, column=0, sticky="e", padx=14, pady=14)
        populate()
        search.focus_set()

    def show_story_help(self):
        messagebox.showinfo(
            "Código da história",
            "User_Story é formado pelo Id do Product_Backlog, um espaço e o valor do campo Módulo.\n\nExemplo: US-01 USUÁRIOS. Story_Points é carregado automaticamente da história selecionada.",
            parent=self.root,
        )

    def show_subtask_help(self):
        messagebox.showinfo(
            "Subtarefa técnica",
            "Descreva uma atividade técnica necessária para entregar a história selecionada. Ela deve estar relacionada ao módulo indicado no Product_Backlog.",
            parent=self.root,
        )

    def show_points_info(self):
        if not self.fibonacci_data:
            messagebox.showinfo("Story_Points", "A tabela Fibonacci não possui descrições cadastradas.", parent=self.root)
            return
        explanations = []
        for points in sorted(self.fibonacci_data, key=lambda value: int(value)):
            details = self.fibonacci_data[points]
            explanations.append(
                f"{points} ponto(s)\nSignificado: {details.get('Significado', '')}\nExemplos: {details.get('Exemplos', '')}"
            )
        messagebox.showinfo("Escala Story_Points | Fibonacci", "\n\n".join(explanations), parent=self.root)

    def show_status_info(self):
        status = self.status_var.get().strip()
        details = self.status_data.get(status)
        if not details:
            messagebox.showinfo("Orientação de status", "Selecione um status para ver o significado e quando usá-lo.", parent=self.root)
            return
        messagebox.showinfo(
            f"Status: {status}",
            f"Significado: {details.get('Significado') or 'Não informado.'}\n\nQuando usar: {details.get('Quando_usar') or 'Não informado.'}",
            parent=self.root,
        )

    @staticmethod
    def _format_hour_text(digits):
        digits = re.sub(r"[^0-9]", "", digits)[:4]
        if len(digits) < 2:
            return digits
        return f"{digits[:2]}:{digits[2:]}"

    def _on_time_key(self, event):
        entry = event.widget
        current = entry.get()
        cursor = entry.index(tk.INSERT)
        digits_before = len(re.sub(r"[^0-9]", "", current[:cursor]))
        formatted = self._format_hour_text(current)
        if current != formatted:
            entry.delete(0, tk.END)
            entry.insert(0, formatted)
            new_cursor = digits_before + (1 if digits_before >= 2 else 0)
            entry.icursor(min(new_cursor, len(formatted)))
        self._update_remaining()

    def _on_masked_delete(self, event):
        entry = event.widget
        current = entry.get()
        cursor = entry.index(tk.INSERT)
        try:
            selection_start = entry.index("sel.first")
            selection_end = entry.index("sel.last")
        except tk.TclError:
            selection_start = selection_end = None

        if selection_start is not None:
            if selection_start == 0 and selection_end == len(current):
                updated = ""
            else:
                updated = list(current)
                for index in range(selection_start, selection_end):
                    if updated[index].isdigit():
                        updated[index] = "0"
                updated = "".join(updated)
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
        if entry in (self.estimated_entry, self.spent_entry):
            self._update_remaining()
        return "break"

    @staticmethod
    def _prepare_time_entry(event):
        if event.widget.get() == "00:00":
            event.widget.selection_range(0, tk.END)
            event.widget.icursor(tk.END)

    def _normalize_time_entry(self, event):
        entry = event.widget
        digits = re.sub(r"[^0-9]", "", entry.get())[:4]
        if not digits:
            entry.delete(0, tk.END)
            entry.insert(0, "00:00")
            self._update_remaining()
            return
        hours = int(digits[:2])
        minutes = int(digits[2:4].ljust(2, "0")) if len(digits) > 2 else 0
        if minutes < 60:
            entry.delete(0, tk.END)
            entry.insert(0, f"{hours:02d}:{minutes:02d}")
        self._update_remaining()

    @staticmethod
    def _time_to_minutes(value):
        if not value.strip():
            return 0
        if ":" not in value:
            digits = re.sub(r"[^0-9]", "", value)
            if not digits:
                return 0
            hours, minutes = int(digits[:2]), int(digits[2:4] or 0)
        else:
            hours_text, minutes_text = value.split(":", 1)
            hours = int(hours_text or 0)
            minutes = int(minutes_text or 0)
        if minutes > 59:
            raise ValueError("Minutos devem estar entre 00 e 59.")
        return hours * 60 + minutes

    @staticmethod
    def _minutes_to_time(total_minutes):
        hours, minutes = divmod(max(0, total_minutes), 60)
        return f"{hours:02d}:{minutes:02d}"

    def _update_remaining(self):
        if self.status_var.get().strip().upper() == "CONCLUÍDO":
            self.remaining_var.set("00:00")
            return
        try:
            estimate = self._time_to_minutes(self.estimated_var.get())
            spent = self._time_to_minutes(self.spent_var.get())
        except ValueError:
            return
        self.remaining_var.set(self._minutes_to_time(estimate - spent))

    def _on_date_key(self, event):
        entry = event.widget
        current = entry.get()
        cursor = entry.index(tk.INSERT)
        digits_before = len(re.sub(r"[^0-9]", "", current[:cursor]))
        digits = re.sub(r"[^0-9]", "", current)[:8]
        if len(digits) <= 2:
            formatted = digits
        elif len(digits) <= 4:
            formatted = f"{digits[:2]}/{digits[2:]}"
        else:
            formatted = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"
        if current != formatted:
            entry.delete(0, tk.END)
            entry.insert(0, formatted)
            slashes_before = int(digits_before > 2) + int(digits_before > 4)
            entry.icursor(min(digits_before + slashes_before, len(formatted)))

    def _build_grid(self):
        ttk.Label(self.list_panel, text="VISÃO GERAL", style=MUTED_STYLE).grid(row=0, column=0, sticky="w")
        ttk.Label(self.list_panel, text="Tarefas da sprint", style=SECTION_STYLE).grid(row=1, column=0, sticky="w", pady=(3, 12))
        filters = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        filters.grid(row=2, column=0, sticky="ew")
        filters.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(filters, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self._on_grid_search)
        ttk.Combobox(filters, textvariable=self.status_filter_var, values=["TODOS", *self.status_data], state="readonly", width=20).grid(row=0, column=1)
        self.status_filter_var.trace_add("write", lambda *_args: self.apply_filters())

        actions = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 10))
        ttk.Button(actions, text="Editar selecionada", command=self.edit_selected).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Excluir selecionada", command=self.delete_selected).pack(side="left", padx=(0, 6))
        transfer.add_transfer_buttons(actions, self)

        table_frame = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        table_frame.grid(row=4, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("id", "sprint", "story", "subtask", "owner", "points", "estimated", "spent", "remaining", "status", "date")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "id": ("Id_Task", 90), "sprint": ("Sprint", 110), "story": ("User_Story", 190),
            "subtask": ("Subtarefa técnica", 220), "owner": ("Responsável", 130),
            "points": ("Pontos", 65), "estimated": ("Estimadas", 90), "spent": ("Gastas", 90),
            "remaining": ("Restantes", 90), "status": ("Status", 130), "date": ("Conclusão", 110),
        }
        for key, (label, width) in headings.items():
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, minwidth=60, anchor="w", stretch=key in ("story", "subtask"))
        self.tree.tag_configure("even", background="#f7f9f7")
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.empty_label = ttk.Label(table_frame, text="Nenhuma tarefa encontrada para os filtros atuais.", style=MUTED_STYLE)
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind("<Double-1>", self.load_selected)
        ttk.Label(self.list_panel, text="Selecione uma tarefa ou dê dois cliques para editar.", style=MUTED_STYLE).grid(row=5, column=0, sticky="w", pady=(9, 0))

    def refresh_records(self):
        try:
            self.records = list_sprint_backlog()
        except sqlite3.Error as error:
            messagebox.showerror("Erro ao carregar sprints", str(error), parent=self.root)
            self.records = []
        if not self.editing_id:
            self.story_options = get_product_backlog_stories()
            self.story_map = {str(row[0]).upper(): row for row in self.story_options}
        self.apply_filters()
        if not self.editing_id:
            self.id_var.set(self._next_task_id())
            self.id_entry.configure(state="readonly")

    def _next_task_id(self):
        largest = 100
        for record in self.records:
            match = re.fullmatch(r"SB-(\d+)", str(record[0]).upper())
            if match:
                largest = max(largest, int(match.group(1)))
        return f"SB-{largest + 1:03d}"

    def export_csv(self):
        transfer.export_csv(self.root, "Exportar sprints", "sprints_backlog.csv", TRANSFER_HEADERS, self.records)

    def export_excel(self):
        transfer.export_excel(self.root, "Exportar sprints", "sprints_backlog.xlsx", "Sprints Backlog", TRANSFER_HEADERS, self.records)

    def import_csv(self):
        rows = transfer.read_csv(self.root, "Importar sprints")
        if rows is not None:
            self._import_rows(rows)

    def import_excel(self):
        rows = transfer.read_excel(self.root, "Importar sprints")
        if rows is not None:
            self._import_rows(rows)

    def _import_rows(self, rows):
        existing = {str(record[0]).upper() for record in self.records}
        imported = skipped = 0
        for row in rows:
            data = transfer.normalized(row)
            id_task = transfer.field(data, "id_task", "id")
            user_story = transfer.field(data, "user_story", "história", "historia")
            if not id_task or not user_story or id_task.upper() in existing:
                skipped += 1
                continue
            points_text = transfer.field(data, "story_points", "pontos").replace(",", ".")
            try:
                points = int(float(points_text)) if points_text else None
                insert_sprint_backlog(
                    id_task.upper(),
                    transfer.field(data, "titulo_sprint", "sprint").upper(),
                    user_story.upper(),
                    transfer.field(data, "subtarefa_tecnica", "subtarefa técnica", "subtarefa").upper(),
                    transfer.field(data, "responsavel", "responsável").upper(),
                    points,
                    transfer.field(data, "horas_estimadas", "estimadas"),
                    transfer.field(data, "horas_gastas", "gastas"),
                    transfer.field(data, "horas_restantes", "restantes"),
                    transfer.field(data, "status").upper(),
                    transfer.field(data, "data_conclusao", "conclusão", "conclusao"),
                )
                existing.add(id_task.upper())
                imported += 1
            except (ValueError, TypeError, sqlite3.Error):
                skipped += 1
        self.refresh_records()
        transfer.report(self.root, imported, skipped)

    def _on_grid_search(self, event=None):
        text = self.search_var.get()
        uppercase = text.upper()
        if text != uppercase:
            cursor = event.widget.index(tk.INSERT) if event else len(text)
            self.search_var.set(uppercase)
            if event:
                event.widget.icursor(min(cursor, len(uppercase)))
        self.apply_filters()

    def apply_filters(self):
        query = self.search_var.get().strip().casefold()
        status = self.status_filter_var.get()
        filtered = [row for row in self.records if
                    (not query or query in " ".join(str(value or "") for value in row).casefold()) and
                    (status == "TODOS" or row[9] == status)]
        self.tree.delete(*self.tree.get_children())
        if filtered:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        for index, row in enumerate(filtered):
            values = tuple(row[:10]) + (row[10] or "",)
            self.tree.insert("", "end", iid=str(index), values=values, tags=("even" if index % 2 == 0 else "odd",))
        sprint_columns = (
            ("id", "Id_Task", 0, 90), ("sprint", "Sprint", 1, 110),
            ("story", "User_Story", 2, 190), ("subtask", "Subtarefa técnica", 3, 200),
            ("owner", "Responsável", 4, 130), ("points", "Pontos", 5, 70),
            ("estimated", "Estimadas", 6, 90), ("spent", "Gastas", 7, 90),
            ("remaining", "Restantes", 8, 90), ("status", "Status", 9, 130),
            ("date", "Conclusão", 10, 110),
        )
        grid_rows = [tuple(row[:10]) + (row[10] or "",) for row in filtered]
        fit_tree_columns(self.tree, self.root, sprint_columns, grid_rows)
        self.count_label.configure(text=f"{len(filtered)} TAREFAS" if len(filtered) != 1 else "1 TAREFA")

    def search_task(self):
        task_id = simpledialog.askstring("Pesquisar tarefa", "Informe o Id_Task:", parent=self.root)
        if not task_id:
            return
        record = next((row for row in self.records if row[0].casefold() == task_id.strip().casefold()), None)
        if record is None:
            messagebox.showinfo("Tarefa não encontrada", f"Não existe tarefa com Id {task_id.strip().upper()}.", parent=self.root)
            return
        self._load_record(record)

    def search_sprint(self):
        title = simpledialog.askstring("Pesquisar sprint", "Informe o título da sprint:", parent=self.root)
        if title:
            self.search_var.set(title.strip().upper())
            self.status_filter_var.set("TODOS")
            self.apply_filters()

    def _matches_story(self, user_story):
        story_id = user_story.strip().upper()[:5]
        return self.story_map.get(story_id)

    def save_record(self):
        task_id = self.id_var.get().strip().upper()
        sprint_title = self.sprint_var.get().strip().upper()
        user_story = self.story_var.get().strip().upper()
        if user_story == getattr(self.story_entry, "placeholder", None):
            user_story = ""
        story = self._matches_story(user_story)
        subtask = self.subtask_var.get().strip().upper()
        status = self.status_var.get().strip().upper()
        missing = [label for label, value in (("Id_Task", task_id), ("Título da sprint", sprint_title), ("User_Story", story), ("Subtarefa técnica", subtask), ("Status", status)) if not value]
        if missing:
            messagebox.showwarning("Campos obrigatórios", f"Preencha ou selecione: {', '.join(missing)}.", parent=self.root)
            return
        self.story_var.set(f"{story[0]} {story[1]}".upper())
        self.points_var.set("" if story[2] is None else str(story[2]))
        try:
            estimated = self._time_to_minutes(self.estimated_var.get())
            spent = self._time_to_minutes(self.spent_var.get())
        except ValueError as error:
            messagebox.showwarning("Hora inválida", str(error), parent=self.root)
            return
        remaining = 0 if status == "CONCLUÍDO" else max(0, estimated - spent)
        remaining_text = self._minutes_to_time(remaining)
        self.remaining_var.set(remaining_text)
        date_text = self.completion_var.get().strip()
        if date_text == getattr(self.date_entry, "placeholder", None):
            date_text = ""
        if date_text:
            try:
                day, month, year = map(int, date_text.split("/"))
                date(year, month, day)
            except ValueError:
                messagebox.showwarning("Data inválida", "Informe uma data válida no formato DD/MM/AAAA.", parent=self.root)
                return
        points = int(story[2]) if story[2] is not None else None
        values = (sprint_title, self.story_var.get(), subtask, self.owner_var.get().strip().upper(),
                  points, self._minutes_to_time(estimated), self._minutes_to_time(spent), remaining_text,
                  status, date_text or None)
        try:
            if self.editing_id:
                update_sprint_backlog(self.editing_id, *values)
                success = f"Tarefa {self.editing_id} atualizada."
            else:
                if task_id in {str(row[0]).upper() for row in self.records}:
                    messagebox.showwarning("Id_Task já cadastrado", "O Id_Task gerado já existe. Atualize a lista e tente novamente.", parent=self.root)
                    return
                insert_sprint_backlog(task_id, *values)
                success = f"Tarefa {task_id} cadastrada."
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível salvar", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()
        messagebox.showinfo("Sprints_Backlog atualizado", success, parent=self.root)

    def load_selected(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        selected_id = self.tree.item(selection[0], "values")[0]
        row = next((record for record in self.records if str(record[0]) == str(selected_id)), None)
        if row:
            self._load_record(row)

    def _load_record(self, row):
        self.editing_id = row[0]
        self.id_var.set(row[0] or "")
        self.id_entry.configure(state="readonly")
        self.sprint_var.set(row[1] or "")
        self.story_var.set(row[2] or "")
        self.points_var.set("" if row[5] is None else str(row[5]))
        self.subtask_var.set(row[3] or "")
        self.owner_var.set(row[4] or "")
        self.estimated_var.set(row[6] or "00:00")
        self.spent_var.set(row[7] or "00:00")
        self.remaining_var.set(row[8] or "00:00")
        self.status_var.set(row[9] or "")
        self.completion_var.set(row[10] or "")
        self._restore_entry_style(self.sprint_entry)
        self._restore_entry_style(self.story_entry)
        self._restore_entry_style(self.subtask_entry)
        self._restore_entry_style(self.owner_entry)
        self._restore_entry_style(self.date_entry)
        self.save_button.configure(text="Salvar alterações")

    @staticmethod
    def _restore_entry_style(entry):
        entry.configure(style="TEntry")

    def edit_selected(self):
        if not self.tree.selection():
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma linha para editar.", parent=self.root)
            return
        self.load_selected()

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma linha para excluir.", parent=self.root)
            return
        task_id = self.tree.item(selection[0], "values")[0]
        if not messagebox.askyesno("Confirmar exclusão", f"Excluir a tarefa {task_id}?", parent=self.root):
            return
        try:
            delete_sprint_backlog(task_id)
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível excluir", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()

    def new_record(self):
        self.clear_form(reset_filters=False)

    def clear_form(self, reset_filters=True):
        self.editing_id = None
        self.sprint_var.set("Ex.: SPRINT 4")
        self.story_var.set("Ex.: US-01 USUÁRIOS")
        self.subtask_var.set("Ex.: CRIAR TELA DE CADASTRO")
        self.owner_var.set("Ex.: ANA SILVA")
        self.points_var.set("")
        self.estimated_var.set("")
        self.spent_var.set("")
        self.remaining_var.set("00:00")
        self.status_var.set("")
        self.completion_var.set("DD/MM/AAAA")
        for entry in (self.sprint_entry, self.story_entry, self.subtask_entry, self.owner_entry, self.date_entry):
            entry.configure(style=PLACEHOLDER_STYLE)
        self.save_button.configure(text="Salvar tarefa")
        self.id_var.set(self._next_task_id())
        self.id_entry.configure(state="readonly")
        self.tree.selection_remove(self.tree.selection())
        if reset_filters:
            self.search_var.set("")
            self.status_filter_var.set("TODOS")
            self.apply_filters()