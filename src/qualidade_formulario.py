import csv
import json
import sqlite3
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import xml.etree.ElementTree as ET

import pandas as pd

from database import (
    delete_qualidade,
    get_governance_backlog_options,
    get_qualidade_backlog_ids,
    get_qualidade_statuses,
    get_status_sprint,
    list_sprint_backlog,
    list_qualidade,
    save_qualidade,
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
METRIC_LABEL = "Métrica"
KEY_RELEASE_EVENT = "<KeyRelease>"
GRID_COLUMNS = (
    ("id", "Id_Qualidade", 0, 110),
    ("metric", METRIC_LABEL, 1, 250),
    ("target", "Valor-alvo", 2, 110),
    ("actual", "Valor-real", 3, 110),
    ("achievement", "Atingimento", 4, 120),
    ("status", "Status", 5, 120),
    ("links", "Histórias vinculadas", 6, 220),
)
QUALITY_RECORD_COLUMNS = ("Id_Qualidade", "Metrica", "Valor_Alvo", "Valor_Real", "Status", "Qtd_Vinculos", "Historias")
TRANSFER_HEADERS = ("Id_Qualidade", "Metrica", "Valor_Alvo", "Valor_Real", "Status")


class QualidadeForm:
    def __init__(self, root, return_to_menu):
        self.root = root
        self.return_to_menu = return_to_menu
        self.records = []
        self.sprint_records = []
        self.external_actuals = {}
        self.external_sources = {}
        self.backlog_rows = get_governance_backlog_options()
        self.status_options = list(dict.fromkeys([
            *get_qualidade_statuses(), *get_status_sprint().keys(), "PENDENTE",
        ]))
        self.editing_id = None

        self.id_var = tk.StringVar()
        self.metric_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.actual_var = tk.StringVar()
        self.achievement_var = tk.StringVar(value="0,0%")
        self.quality_index_var = tk.StringVar(value="0,0%")
        self.status_var = tk.StringVar(value="PENDENTE")
        self.search_var = tk.StringVar()

        self._configure_style()
        self._build_layout()
        self.refresh_records()

    def _configure_style(self):
        style = ttk.Style(self.root)
        style.configure(PANEL_STYLE, background="#ffffff")
        style.configure(MUTED_STYLE, background="#ffffff", foreground="#718078", font=(FONT_NAME, 9))
        style.configure(SECTION_STYLE, background="#ffffff", foreground="#19392f", font=(FONT_NAME, 12, "bold"))
        style.configure("QualityScore.TLabel", background="#ffffff", foreground="#236b58", font=(FONT_NAME, 14, "bold"))
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
        tk.Label(title, text="SCRUM  /  QUALIDADE", bg="#19392f", fg="#a9c9bb", font=(FONT_NAME, 9, "bold")).pack(anchor="w")
        tk.Label(title, text="Indicadores de qualidade", bg="#19392f", fg="#ffffff", font=(FONT_NAME, 21, "bold")).pack(anchor="w", pady=(2, 0))
        self.count_label = tk.Label(self.header, text="0 MÉTRICAS", bg="#19392f", fg="#d7e8df", font=(FONT_NAME, 10, "bold"))
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
        self.list_panel.rowconfigure(5, weight=1)
        self._build_form()
        self._build_grid()

    def _build_form(self):
        ttk.Label(self.form_body, text="DADOS DA MÉTRICA", style=MUTED_STYLE).pack(anchor="w")
        ttk.Label(self.form_body, text="Cadastro", style=SECTION_STYLE).pack(anchor="w", pady=(3, 14))
        self.id_entry = self._add_entry("Id_Qualidade", self.id_var, search_command=self.search_quality)
        self.id_entry.configure(state="readonly")
        self.metric_entry = self._add_entry(f"{METRIC_LABEL} *", self.metric_var, "Ex.: COBERTURA DE TESTES (%)")
        self.target_entry = self._add_entry("Valor-alvo *", self.target_var, "Ex.: 80,0")
        self.actual_entry = self._add_entry("Valor-real *", self.actual_var, "Valor calculado ou medido", info_command=self.show_actual_help)
        self.metric_entry.bind(KEY_RELEASE_EVENT, self._on_metric_key)
        self.metric_entry.bind("<FocusOut>", self._refresh_metric_value, add="+")
        for entry in (self.target_entry, self.actual_entry):
            entry.bind(KEY_RELEASE_EVENT, self._normalize_decimal_entry)
        self.target_var.trace_add("write", lambda *_args: self._refresh_metric_value())
        self.actual_var.trace_add("write", lambda *_args: self._update_form_achievement())
        self.achievement_entry = self._add_entry("Atingimento (calculado)", self.achievement_var)
        self.achievement_entry.configure(state="readonly")
        self._update_form_achievement()
        ttk.Button(self.form_body, text="Importar fonte externa",
                   command=self.connect_external_source).pack(fill="x", pady=(6, 0))
        ttk.Button(self.form_body, text="Gerar modelo CSV de monitoramento",
               command=self.generate_monitoring_template).pack(fill="x", pady=(6, 0))

        ttk.Label(self.form_body, text="Status *").pack(anchor="w", pady=(10, 5))
        self.status_combo = ttk.Combobox(self.form_body, textvariable=self.status_var, values=self.status_options, state="readonly")
        self.status_combo.pack(fill="x")
        self.status_combo.bind(KEY_RELEASE_EVENT, self._uppercase_entry)

        ttk.Label(self.form_body, text="Histórias do Product_Backlog").pack(anchor="w", pady=(12, 5))
        links_frame = ttk.Frame(self.form_body, style=PANEL_STYLE)
        links_frame.pack(fill="both", expand=True)
        self.links_list = tk.Listbox(links_frame, selectmode=tk.MULTIPLE, exportselection=False, height=8,
                                     font=(FONT_NAME, 9), relief="flat", bg="#f7f9f7", fg="#23352f",
                                     selectbackground="#d9ebe3", selectforeground="#19392f",
                                     highlightthickness=1, highlightbackground="#dce5df")
        self.links_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(links_frame, orient="vertical", command=self.links_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.links_list.configure(yscrollcommand=scrollbar.set)
        links_frame.columnconfigure(0, weight=1)
        links_frame.rowconfigure(0, weight=1)
        self._populate_backlog_options()

        ttk.Separator(self.form_body).pack(fill="x", pady=16)
        ttk.Button(self.form_body, text="Nova métrica", style=NEW_STYLE, command=self.new_record).pack(fill="x", pady=(0, 8))
        self.save_button = ttk.Button(self.form_body, text="Salvar métrica", style=PRIMARY_STYLE, command=self.save_record)
        self.save_button.pack(fill="x")
        ttk.Button(self.form_body, text="Limpar formulário", command=self.clear_form).pack(fill="x", pady=(8, 0))

    def _add_entry(self, label, variable, placeholder=None, search_command=None, info_command=None):
        ttk.Label(self.form_body, text=label).pack(anchor="w", pady=(9, 5))
        row = ttk.Frame(self.form_body, style=PANEL_STYLE)
        row.pack(fill="x")
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True)
        if search_command:
            ttk.Button(row, text="🔍", style=ICON_STYLE, command=search_command).pack(side="left", padx=(6, 0))
        if placeholder:
            self._set_placeholder(entry, variable, placeholder)
        if info_command:
            ttk.Button(row, text="ⓘ", style=ICON_STYLE, command=info_command).pack(side="left", padx=(6, 0))
        return entry

    @staticmethod
    def _set_placeholder(entry, variable, placeholder):
        entry.placeholder = placeholder
        entry.configure(style=PLACEHOLDER_STYLE)
        variable.set(placeholder)
        entry.bind("<FocusIn>", lambda _event: QualidadeForm._clear_placeholder(entry, variable))
        entry.bind("<FocusOut>", lambda _event: QualidadeForm._restore_placeholder(entry, variable))

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

    @staticmethod
    def _normalize_decimal_entry(event):
        entry = event.widget
        value = entry.get().replace(".", ",")
        allowed = "0123456789,"
        normalized = "".join(character for character in value if character in allowed)
        if normalized.count(",") > 1:
            first_separator = normalized.find(",")
            normalized = normalized[:first_separator + 1] + normalized[first_separator + 1:].replace(",", "")
        if normalized != entry.get():
            cursor = entry.index(tk.INSERT)
            entry.delete(0, tk.END)
            entry.insert(0, normalized)
            entry.icursor(min(cursor, len(normalized)))

    def _populate_backlog_options(self, selected_ids=()):
        selected_ids = set(selected_ids)
        self.backlog_rows = get_governance_backlog_options()
        self.links_list.delete(0, tk.END)
        for index, (backlog_id, module) in enumerate(self.backlog_rows):
            self.links_list.insert(tk.END, f"{backlog_id}  |  {module}")
            if backlog_id in selected_ids:
                self.links_list.selection_set(index)

    def _selected_backlog_ids(self):
        return [self.backlog_rows[index][0] for index in self.links_list.curselection()]

    def _build_grid(self):
        ttk.Label(self.list_panel, text="VISÃO GERAL", style=MUTED_STYLE).grid(row=0, column=0, sticky="w")
        ttk.Label(self.list_panel, text="Indicadores de qualidade", style=SECTION_STYLE).grid(row=1, column=0, sticky="w", pady=(3, 12))
        score_row = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        score_row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(score_row, text="Índice de qualidade do projeto").pack(side="left")
        ttk.Label(score_row, textvariable=self.quality_index_var, style="QualityScore.TLabel").pack(side="right")
        filters = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        filters.grid(row=3, column=0, sticky="ew")
        filters.columnconfigure(0, weight=1)
        search = ttk.Entry(filters, textvariable=self.search_var)
        search.grid(row=0, column=0, sticky="ew")
        search.bind(KEY_RELEASE_EVENT, self._on_search)

        actions = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        actions.grid(row=4, column=0, sticky="ew", pady=(10, 10))
        ttk.Button(actions, text="Editar selecionada", command=self.edit_selected).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Excluir selecionada", command=self.delete_selected).pack(side="left", padx=(0, 6))
        transfer.add_transfer_buttons(actions, self)

        table_frame = ttk.Frame(self.list_panel, style=PANEL_STYLE)
        table_frame.grid(row=5, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, columns=("id", "metric", "target", "actual", "achievement", "status", "links"), show="headings", selectmode="browse")
        headings = (("id", "Id_Qualidade", 100), ("metric", METRIC_LABEL, 240), ("target", "Valor-alvo", 100),
                ("actual", "Valor-real", 100), ("achievement", "Atingimento", 120),
                ("status", "Status", 120), ("links", "Histórias vinculadas", 220))
        for column, label, width in headings:
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, minwidth=60, anchor="w", stretch=False)
        self.tree.tag_configure("even", background="#f7f9f7")
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.empty_label = ttk.Label(table_frame, text="Nenhuma métrica encontrada.", style=MUTED_STYLE)
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind("<Double-1>", self.load_selected)

    @staticmethod
    def _decimal_from_input(value):
        text = value.strip().replace(",", ".")
        if not text:
            raise ValueError("Informe um valor numérico.")
        try:
            return float(Decimal(text))
        except InvalidOperation as error:
            raise ValueError("Informe um valor numérico válido.") from error

    @staticmethod
    def _format_decimal(value):
        return (f"{float(value):g}").replace(".", ",")

    @staticmethod
    def _hours_to_decimal(value):
        parts = str(value or "").strip().split(":")
        if len(parts) < 2:
            return None
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2]) if len(parts) > 2 else 0
        except ValueError:
            return None
        return hours + minutes / 60 + seconds / 3600

    def _automatic_real(self, metric):
        metric_key = metric.strip().casefold()
        external_value = self.external_actuals.get(metric.strip().upper())
        if external_value is not None:
            return external_value
        completed = [
            row for row in self.sprint_records
            if str(row[9] or "").strip().upper() == "CONCLUÍDO"
        ]
        if "velocity" in metric_key:
            planned_points = sum(float(row[5] or 0) for row in self.sprint_records)
            delivered_points = sum(float(row[5] or 0) for row in completed)
            return delivered_points if planned_points > 0 else None
        if "tempo médio de resolução" in metric_key:
            resolution_hours = [self._hours_to_decimal(row[7]) for row in completed]
            resolution_hours = [value for value in resolution_hours if value is not None]
            if not resolution_hours:
                return None
            return sum(resolution_hours) / len(resolution_hours)
        return None

    def show_actual_help(self):
        messagebox.showinfo(
            "Arquivos para Valor_Real",
            "1. Cobertura: gere com Coverage.py em JSON/XML. O JSON deve conter totals.percent_covered; o XML deve conter lines-covered e lines-valid ou line-rate.\n\n"
            "2. Disponibilidade: CSV com cabeçalho online_hours,total_hours ou online_seconds,total_seconds; cada linha representa um período monitorado.\n\n"
            "Velocity e tempo médio vêm das tarefas concluídas em Sprints_Backlog. Sem arquivo externo, Valor_Real permanece editável. Depois de importar, clique em Salvar métrica para gravar o resultado.",
            parent=self.root,
        )

    def connect_external_source(self):
        metric_name = self.metric_var.get().strip().upper()
        if "COBERTURA" in metric_name:
            source_path = filedialog.askopenfilename(
                parent=self.root, title="Selecionar relatório Coverage.py",
                filetypes=[("Coverage JSON/XML", "*.json *.xml"), ("JSON", "*.json"), ("XML", "*.xml")],
            )
            if not source_path:
                return
            try:
                value = self._read_coverage_report(source_path)
            except (OSError, ValueError, ET.ParseError) as error:
                messagebox.showerror("Relatório de coverage inválido", str(error), parent=self.root)
                return
        elif "DISPONIBILIDADE" in metric_name:
            source_path = filedialog.askopenfilename(
                parent=self.root, title="Selecionar CSV de monitoramento",
                filetypes=[("CSV", "*.csv")],
            )
            if not source_path:
                return
            try:
                value = self._read_availability_report(source_path)
            except (OSError, ValueError, csv.Error) as error:
                messagebox.showerror("CSV de monitoramento inválido", str(error), parent=self.root)
                return
        else:
            messagebox.showinfo(
                "Fonte automática",
                "Velocity e tempo médio são calculados a partir de Sprints_Backlog; selecione Cobertura de Testes ou Disponibilidade para importar arquivo externo.",
                parent=self.root,
            )
            return

        self.external_actuals[metric_name] = value
        self.external_sources[metric_name] = source_path
        self._refresh_metric_value()
        messagebox.showinfo("Importação concluída", f"Valor_Real atualizado: {self._format_decimal(value)}. Clique em Salvar métrica para gravar no banco.", parent=self.root)

    def generate_monitoring_template(self):
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Salvar modelo de monitoramento", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")], initialfile="modelo_disponibilidade.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as template_file:
                csv.writer(template_file).writerow(("online_hours", "total_hours"))
        except OSError as error:
            messagebox.showerror("Erro ao criar modelo", str(error), parent=self.root)
            return
        messagebox.showinfo("Modelo criado", f"Cabeçalhos online_hours,total_hours salvos em:\n{path}", parent=self.root)

    @staticmethod
    def _read_coverage_report(source_path):
        if source_path.casefold().endswith(".json"):
            with open(source_path, encoding="utf-8") as report_file:
                report = json.load(report_file)
            totals = report.get("totals", {})
            if "percent_covered" not in totals:
                raise ValueError("O arquivo não contém totals.percent_covered.")
            return float(totals["percent_covered"])

        root = ET.parse(source_path).getroot()
        lines_valid = int(root.get("lines-valid", "0"))
        lines_covered = int(root.get("lines-covered", "0"))
        if lines_valid > 0:
            return lines_covered / lines_valid * 100
        line_rate = root.get("line-rate")
        if line_rate is None:
            raise ValueError("O XML não contém lines-covered/lines-valid nem line-rate.")
        return float(line_rate) * 100

    @staticmethod
    def _read_availability_report(source_path):
        with open(source_path, newline="", encoding="utf-8-sig") as report_file:
            rows = list(csv.DictReader(report_file))
        if not rows:
            raise ValueError("O CSV não contém registros de monitoramento.")
        normalized_rows = [
            {str(key).strip().casefold(): value for key, value in row.items() if key is not None}
            for row in rows
        ]
        headers = set(normalized_rows[0])
        if {"online_hours", "total_hours"} <= headers:
            online_key, total_key = "online_hours", "total_hours"
        elif {"online_seconds", "total_seconds"} <= headers:
            online_key, total_key = "online_seconds", "total_seconds"
        else:
            raise ValueError("Use as colunas online_hours,total_hours ou online_seconds,total_seconds.")
        online = sum(float(str(row.get(online_key) or "0").replace(",", ".")) for row in normalized_rows)
        total = sum(float(str(row.get(total_key) or "0").replace(",", ".")) for row in normalized_rows)
        if total <= 0:
            raise ValueError("O total de horas/segundos deve ser maior que zero.")
        return online / total * 100

    def _on_metric_key(self, event):
        self._uppercase_entry(event)
        self._refresh_metric_value()

    def _refresh_metric_value(self, _event=None):
        metric = self.metric_var.get().strip()
        if metric == getattr(self.metric_entry, "placeholder", None):
            metric = ""
        automatic_value = self._automatic_real(metric) if metric else None
        if automatic_value is None:
            if getattr(self, "_actual_is_automatic", False):
                self.actual_var.set("")
            self._actual_is_automatic = False
            self.actual_entry.configure(state="normal")
        else:
            self._actual_is_automatic = True
            self.actual_var.set(self._format_decimal(automatic_value))
            self.actual_entry.configure(state="readonly")
        self._update_form_achievement()

    def _effective_records(self):
        records = []
        for record in self.records:
            values = list(record)
            automatic_value = self._automatic_real(record[1])
            if automatic_value is not None:
                values[3] = automatic_value
            records.append(tuple(values))
        return records

    def _update_quality_index(self, draft_values=None):
        records = self._effective_records()
        if draft_values is not None and self.metric_var.get().strip() not in ("", self.metric_entry.placeholder):
            automatic_value = self._automatic_real(self.metric_var.get())
            metric_row = (
                self.editing_id if self.editing_id is not None else -1,
                self.metric_var.get().strip().upper(), draft_values[0],
                automatic_value if automatic_value is not None else draft_values[1],
                self.status_var.get().strip().upper(), 0, "",
            )
            metric_key = metric_row[1].casefold()
            existing_index = next(
                (index for index, row in enumerate(records) if str(row[1]).strip().casefold() == metric_key),
                None,
            )
            if existing_index is None:
                records.append(metric_row)
            else:
                metric_row = (records[existing_index][0], *metric_row[1:])
                records[existing_index] = metric_row
        _, overall_index = self._calculate_quality_metrics(records)
        self.quality_index_var.set(self._format_percentage(overall_index))

    def refresh_records(self):
        try:
            self.records = list_qualidade()
            self.sprint_records = list_sprint_backlog()
        except sqlite3.Error as error:
            messagebox.showerror("Erro ao carregar qualidade", str(error), parent=self.root)
            self.records = []
            self.sprint_records = []
        statuses = list(dict.fromkeys([
            *self.status_options, *(str(row[4]) for row in self.records if row[4]),
        ]))
        self.status_options = statuses
        self.status_combo.configure(values=statuses)
        self.apply_filters()
        if self.editing_id is None:
            self.id_var.set(str(self._next_id()))
            self.id_entry.configure(state="readonly")

    def _next_id(self):
        return max((int(row[0]) for row in self.records if row[0] is not None), default=0) + 1

    def export_csv(self):
        rows = [record[:5] for record in self.records]
        transfer.export_csv(self.root, "Exportar qualidade", "qualidade.csv", TRANSFER_HEADERS, rows)

    def export_excel(self):
        rows = [record[:5] for record in self.records]
        transfer.export_excel(self.root, "Exportar qualidade", "qualidade.xlsx", "Qualidade", TRANSFER_HEADERS, rows)

    def import_csv(self):
        rows = transfer.read_csv(self.root, "Importar métricas")
        if rows is not None:
            self._import_rows(rows)

    def import_excel(self):
        rows = transfer.read_excel(self.root, "Importar métricas")
        if rows is not None:
            self._import_rows(rows)

    def _import_rows(self, rows):
        existing = {str(record[1]).strip().casefold() for record in self.records}
        imported = skipped = 0
        for row in rows:
            data = transfer.normalized(row)
            metrica = transfer.field(data, "metrica", "métrica")
            if not metrica or metrica.casefold() in existing:
                skipped += 1
                continue
            try:
                target_text = transfer.field(data, "valor_alvo", "valor-alvo", "alvo").replace(",", ".")
                actual_text = transfer.field(data, "valor_real", "valor-real", "real").replace(",", ".")
                save_qualidade(None, metrica.upper(),
                               float(target_text) if target_text else 0.0,
                               float(actual_text) if actual_text else 0.0,
                               transfer.field(data, "status").upper(), [])
                existing.add(metrica.casefold())
                imported += 1
            except (ValueError, sqlite3.Error):
                skipped += 1
        self.refresh_records()
        transfer.report(self.root, imported, skipped)

    def _on_search(self, event=None):
        if event is not None:
            self.search_var.set(self.search_var.get().upper())
        self.apply_filters()

    def apply_filters(self):
        query = self.search_var.get().strip().casefold()
        effective_records = self._effective_records()
        dataframe, overall_index = self._calculate_quality_metrics(effective_records)
        self.quality_index_var.set(self._format_percentage(overall_index))
        scores_by_id = {
            int(dataframe.loc[index, "Id_Qualidade"]): dataframe.loc[index, "Atingimento"]
            for index in dataframe.index
        }
        filtered = [row for row in effective_records if not query or query in " ".join(str(value or "") for value in row).casefold()]
        self.tree.delete(*self.tree.get_children())
        if filtered:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        for index, row in enumerate(filtered):
            values = (*row[:4], self._format_percentage(scores_by_id[int(row[0])]), row[4], row[6] or "SEM HISTÓRIAS VINCULADAS")
            self.tree.insert("", "end", iid=str(index), values=values, tags=("even" if index % 2 == 0 else "odd",))
        self.count_label.configure(text=f"{len(filtered)} MÉTRICAS" if len(filtered) != 1 else "1 MÉTRICA")
        grid_rows = [
            (*row[:4], self._format_percentage(scores_by_id[int(row[0])]), row[4], row[6] or "SEM HISTÓRIAS VINCULADAS")
            for row in effective_records
        ]
        fit_tree_columns(self.tree, self.root, GRID_COLUMNS, grid_rows)

    @staticmethod
    def _calculate_quality_metrics(records):
        dataframe = pd.DataFrame(records, columns=QUALITY_RECORD_COLUMNS)
        if dataframe.empty:
            dataframe["Atingimento"] = pd.Series(dtype="float64")
            return dataframe, 0.0
        target_values = pd.to_numeric(dataframe["Valor_Alvo"], errors="coerce")
        actual_values = pd.to_numeric(dataframe["Valor_Real"], errors="coerce")
        attainment = actual_values.div(target_values)
        attainment = attainment.replace({float("inf"): 1.0, float("-inf"): 0.0}).clip(upper=1).fillna(0)
        dataframe["Atingimento"] = attainment
        return dataframe, float(attainment.mean())

    @staticmethod
    def _format_percentage(value):
        return f"{float(value) * 100:.1f}%".replace(".", ",")

    def _update_form_achievement(self, *_args):
        try:
            target_value = self._decimal_from_input(self.target_var.get())
            actual_value = self._decimal_from_input(self.actual_var.get())
        except ValueError:
            self.achievement_var.set("0,0%")
            self._update_quality_index()
            return
        dataframe, _overall = self._calculate_quality_metrics(
            [(None, None, target_value, actual_value, None, 0, "")]
        )
        self.achievement_var.set(self._format_percentage(dataframe.loc[0, "Atingimento"]))
        self._update_quality_index((target_value, actual_value))

    def search_quality(self):
        value = simpledialog.askinteger("Pesquisar métrica", "Informe o Id_Qualidade:", parent=self.root, minvalue=1)
        if value is None:
            return
        record = next((row for row in self.records if int(row[0]) == value), None)
        if record:
            self._load_record(record)
        else:
            messagebox.showinfo("Métrica não encontrada", f"Id_Qualidade {value} não existe.", parent=self.root)

    def save_record(self):
        self._refresh_metric_value()
        metric = self.metric_var.get().strip()
        target_text = self.target_var.get().strip()
        actual_text = self.actual_var.get().strip()
        for value_name, entry in (("metric", self.metric_entry), ("target", self.target_entry), ("actual", self.actual_entry)):
            if value_name == "metric" and metric == entry.placeholder:
                metric = ""
            elif value_name == "target" and target_text == entry.placeholder:
                target_text = ""
            elif value_name == "actual" and actual_text == entry.placeholder:
                actual_text = ""
        status = self.status_var.get().strip()
        missing = [name for name, value in ((METRIC_LABEL, metric), ("Valor-alvo", target_text), ("Valor-real", actual_text), ("Status", status)) if not value]
        if missing:
            messagebox.showwarning("Campos obrigatórios", f"Preencha: {', '.join(missing)}.", parent=self.root)
            return
        try:
            target = self._decimal_from_input(target_text)
            automatic_value = self._automatic_real(metric)
            actual = automatic_value if automatic_value is not None else self._decimal_from_input(actual_text)
            record_id = self.editing_id
            if record_id is None:
                existing = next(
                    (row for row in self.records if str(row[1]).strip().casefold() == metric.casefold()),
                    None,
                )
                if existing:
                    record_id = int(existing[0])
            record_id = save_qualidade(
                record_id, metric.upper(), target, actual, status.upper(),
                [self.backlog_rows[index][0] for index in self.links_list.curselection()],
            )
        except ValueError as error:
            messagebox.showwarning("Valor inválido", str(error), parent=self.root)
            return
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível salvar", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()
        messagebox.showinfo("Qualidade atualizada", f"Métrica {record_id} salva com seus vínculos.", parent=self.root)

    def _load_record(self, row):
        self.editing_id = int(row[0])
        self._actual_is_automatic = False
        self.actual_entry.configure(state="normal")
        self.id_var.set(str(row[0]))
        self.metric_var.set(row[1] or "")
        self.target_var.set(self._format_decimal(row[2]) if row[2] is not None else "")
        self.actual_var.set(self._format_decimal(row[3]) if row[3] is not None else "")
        self.status_var.set(row[4] or "")
        for entry in (self.metric_entry, self.target_entry, self.actual_entry):
            entry.configure(style="TEntry")
        self._refresh_metric_value()
        self._populate_backlog_options(get_qualidade_backlog_ids(self.editing_id))
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
            messagebox.showinfo("Selecione uma métrica", "Escolha uma linha para editar.", parent=self.root)
            return
        self.load_selected()

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Selecione uma métrica", "Escolha uma linha para excluir.", parent=self.root)
            return
        record_id = int(self.tree.item(selection[0], "values")[0])
        if not messagebox.askyesno("Confirmar exclusão", f"Excluir a métrica {record_id} e seus vínculos?", parent=self.root):
            return
        try:
            delete_qualidade(record_id)
        except sqlite3.Error as error:
            messagebox.showerror("Não foi possível excluir", str(error), parent=self.root)
            return
        self.refresh_records()
        self.clear_form()

    def new_record(self):
        self.clear_form(reset_filters=False)

    def clear_form(self, reset_filters=True):
        self.editing_id = None
        self._actual_is_automatic = False
        self.actual_entry.configure(state="normal")
        self.id_var.set(str(self._next_id()))
        self.metric_var.set(self.metric_entry.placeholder)
        self.target_var.set(self.target_entry.placeholder)
        self.actual_var.set(self.actual_entry.placeholder)
        self.status_var.set(self.status_options[0] if self.status_options else "PENDENTE")
        for entry in (self.metric_entry, self.target_entry, self.actual_entry):
            entry.configure(style=PLACEHOLDER_STYLE)
        self.links_list.selection_clear(0, tk.END)
        self.id_entry.configure(state="readonly")
        self.save_button.configure(text="Salvar métrica")
        self.tree.selection_remove(self.tree.selection())
        if reset_filters:
            self.search_var.set("")
            self.apply_filters()