import sqlite3
import tkinter as tk
from tkinter import ttk

from database import DB_NAME

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

FONT_NAME = "Segoe UI"
HEADER_BG = "#19392f"
PANEL_BG = "#ffffff"
MUTED_FG = "#718078"
TEXT_FG = "#23352f"
CHART_COLORS = ["#236b58", "#2878c7", "#d99a2b", "#c75050", "#7a5ea8", "#4d8f6f", "#b0653a", "#718078"]
PRIORITY_ORDER = ["ALTÍSSIMA", "ALTA", "MÉDIA", "BAIXA"]
MISSING_CHART_MESSAGE = "Gráficos indisponíveis.\nInstale as dependências com: pip install -r requirements.txt"


def _fetchall(sql):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    return rows


def _count(table):
    return _fetchall(f"SELECT COUNT(*) FROM {table}")[0][0]


def _to_hours(value):
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    if ":" in text:
        hours, _, minutes = text.partition(":")
        try:
            return int(hours) + int(minutes) / 60
        except ValueError:
            return 0.0
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return 0.0


def _to_number(value):
    if value is None:
        return None
    text = str(value).strip().replace("%", "").replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _counts_by(rows, index):
    counts = {}
    for row in rows:
        key = (row[index] or "NÃO INFORMADO").strip() or "NÃO INFORMADO"
        counts[key] = counts.get(key, 0) + 1
    return counts


class DashboardForm:
    def __init__(self, root, back_callback):
        self.root = root
        self.back_callback = back_callback
        self.frame = ttk.Frame(root)
        self.frame.pack(fill="both", expand=True)
        self._build_header()

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(16, 20))
        self.builders = {
            "Product Backlog": self._build_product_tab,
            "Sprints Backlog": self._build_sprints_tab,
            "Histórico": self._build_history_tab,
            "Governança": self._build_governance_tab,
            "Transparência": self._build_transparency_tab,
            "Qualidade": self._build_quality_tab,
        }
        self.tabs = {}
        for title in self.builders:
            tab = ttk.Frame(self.notebook, padding=16)
            self.notebook.add(tab, text=f"  {title}  ")
            self.tabs[title] = tab
        self.refresh_records()

    def _build_header(self):
        header = tk.Frame(self.frame, bg=HEADER_BG, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        title = tk.Frame(header, bg=HEADER_BG)
        title.pack(side="left", padx=28, pady=14)
        tk.Label(title, text="SCRUM  /  DASHBOARDS", bg=HEADER_BG, fg="#a9c9bb",
                 font=(FONT_NAME, 9, "bold")).pack(anchor="w")
        tk.Label(title, text="Visão executiva para decisões", bg=HEADER_BG, fg="#ffffff",
                 font=(FONT_NAME, 18, "bold")).pack(anchor="w", pady=(2, 0))
        ttk.Button(header, text="← Menu Principal", style="Header.TButton",
                   command=self.back_callback).pack(side="right", padx=(8, 28))
        ttk.Button(header, text="⟳ Atualizar", style="Header.TButton",
                   command=self.refresh_records).pack(side="right")

    def refresh_records(self):
        for title, tab in self.tabs.items():
            for child in tab.winfo_children():
                child.destroy()
            self.builders[title](tab)

    # ----------------------------- Cards -----------------------------
    def _card(self, parent, column, title, value, detail, color):
        card = tk.Frame(parent, bg=PANEL_BG, highlightbackground="#d9e2dd", highlightthickness=1)
        card.grid(row=0, column=column, sticky="nsew", padx=6)
        tk.Frame(card, bg=color, height=4).pack(fill="x")
        body = tk.Frame(card, bg=PANEL_BG)
        body.pack(fill="both", expand=True, padx=14, pady=(10, 12))
        tk.Label(body, text=title.upper(), bg=PANEL_BG, fg=MUTED_FG,
                 font=(FONT_NAME, 8, "bold")).pack(anchor="w")
        tk.Label(body, text=value, bg=PANEL_BG, fg=color,
                 font=(FONT_NAME, 20, "bold")).pack(anchor="w", pady=(2, 0))
        tk.Label(body, text=detail, bg=PANEL_BG, fg=MUTED_FG,
                 font=(FONT_NAME, 8)).pack(anchor="w")

    def _build_cards(self, tab, cards):
        frame = ttk.Frame(tab)
        frame.pack(fill="x", pady=(0, 12))
        for index in range(len(cards)):
            frame.columnconfigure(index, weight=1)
        for index, (title, value, detail) in enumerate(cards):
            self._card(frame, index, title, value, detail, CHART_COLORS[index % len(CHART_COLORS)])

    # ----------------------------- Charts -----------------------------
    def _chart(self, parent, column, title, draw):
        holder = tk.Frame(parent, bg=PANEL_BG, highlightbackground="#d9e2dd", highlightthickness=1)
        holder.grid(row=0, column=column, sticky="nsew", padx=6)
        parent.columnconfigure(column, weight=1)
        if not MATPLOTLIB_OK:
            tk.Label(holder, text=MISSING_CHART_MESSAGE, bg=PANEL_BG, fg=MUTED_FG,
                     font=(FONT_NAME, 9), justify="center").pack(expand=True, pady=40)
            return
        figure = Figure(figsize=(5.4, 3.1), dpi=100, facecolor=PANEL_BG)
        ax = figure.add_subplot(111)
        draw(ax)
        ax.set_title(title, fontsize=10, fontweight="bold", color=TEXT_FG, pad=10)
        ax.tick_params(labelsize=8, colors=MUTED_FG)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        figure.tight_layout()
        canvas = FigureCanvasTkAgg(figure, master=holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    def _build_charts(self, tab, charts):
        frame = ttk.Frame(tab)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        for column, (title, draw) in enumerate(charts):
            self._chart(frame, column, title, draw)

    def _empty(self, ax):
        ax.text(0.5, 0.5, "Sem dados", transform=ax.transAxes, ha="center", va="center",
                fontsize=10, color=MUTED_FG)
        ax.set_xticks([])
        ax.set_yticks([])

    def _bar_counts(self, ax, counts, order=None, horizontal=False):
        if not counts:
            self._empty(ax)
            return
        keys = [key for key in (order or []) if key in counts]
        keys += sorted(key for key in counts if key not in keys)
        values = [counts[key] for key in keys]
        colors = CHART_COLORS[:len(keys)]
        if horizontal:
            ax.barh(keys, values, color=colors)
            ax.invert_yaxis()
        else:
            bars = ax.bar(keys, values, color=colors)
            ax.bar_label(bars, fontsize=8, color=TEXT_FG)
            ax.tick_params(axis="x", rotation=20)
        ax.margins(y=0.15)

    def _donut(self, ax, counts):
        if not counts:
            self._empty(ax)
            return
        keys = sorted(counts)
        values = [counts[key] for key in keys]
        ax.pie(values, labels=keys, autopct="%1.0f%%", startangle=90,
               colors=CHART_COLORS[:len(keys)], textprops={"fontsize": 8, "color": TEXT_FG},
               wedgeprops={"width": 0.55, "edgecolor": PANEL_BG})

    # ----------------------------- Abas -----------------------------
    def _build_product_tab(self, tab):
        rows = _fetchall("SELECT Status, Prioridade, Story_Points, Sprint_Alocada FROM Product_Backlog")
        total = len(rows)
        points = sum(int(row[2] or 0) for row in rows)
        done = sum(1 for row in rows if (row[0] or "").upper().startswith("CONCLU"))
        no_sprint = sum(1 for row in rows if not (row[3] or "").strip())
        self._build_cards(tab, (
            ("Histórias", str(total), "itens no Product Backlog"),
            ("Story Points", str(points), "esforço total estimado"),
            ("Concluídas", f"{(done / total * 100) if total else 0:.0f}%", f"{done} de {total} histórias"),
            ("Sem sprint", str(no_sprint), "histórias aguardando alocação"),
        ))

        def draw_status(ax):
            self._donut(ax, _counts_by(rows, 0))

        def draw_priority(ax):
            points_by_priority = {}
            for row in rows:
                key = (row[1] or "NÃO INFORMADA").strip() or "NÃO INFORMADA"
                points_by_priority[key] = points_by_priority.get(key, 0) + int(row[2] or 0)
            self._bar_counts(ax, points_by_priority, order=PRIORITY_ORDER)

        self._build_charts(tab, (
            ("Histórias por status", draw_status),
            ("Story Points por prioridade", draw_priority),
        ))

    def _build_sprints_tab(self, tab):
        rows = _fetchall("SELECT Status, Horas_Estimadas, Horas_Gastas, Horas_Restantes, Titulo_Sprint FROM Sprints_Backlog")
        total = len(rows)
        done = sum(1 for row in rows if "CONCLU" in (row[0] or "").upper())
        spent = sum(_to_hours(row[2]) for row in rows)
        remaining = sum(_to_hours(row[3]) for row in rows)
        self._build_cards(tab, (
            ("Tarefas", str(total), "itens no Sprints Backlog"),
            ("Concluídas", f"{(done / total * 100) if total else 0:.0f}%", f"{done} de {total} tarefas"),
            ("Horas gastas", f"{spent:.1f} h", "esforço realizado"),
            ("Horas restantes", f"{remaining:.1f} h", "trabalho pendente"),
        ))

        def draw_status(ax):
            self._bar_counts(ax, _counts_by(rows, 0))

        def draw_hours(ax):
            estimated = {}
            used = {}
            for row in rows:
                sprint = (row[4] or "SEM SPRINT").strip() or "SEM SPRINT"
                estimated[sprint] = estimated.get(sprint, 0.0) + _to_hours(row[1])
                used[sprint] = used.get(sprint, 0.0) + _to_hours(row[2])
            if not estimated:
                self._empty(ax)
                return
            sprints = sorted(estimated)
            positions = range(len(sprints))
            ax.bar([p - 0.2 for p in positions], [estimated[s] for s in sprints],
                   width=0.4, color=CHART_COLORS[1], label="Estimadas")
            ax.bar([p + 0.2 for p in positions], [used[s] for s in sprints],
                   width=0.4, color=CHART_COLORS[0], label="Gastas")
            ax.set_xticks(list(positions))
            ax.set_xticklabels(sprints, rotation=20)
            ax.legend(fontsize=8)

        self._build_charts(tab, (
            ("Tarefas por status", draw_status),
            ("Horas estimadas x gastas por sprint", draw_hours),
        ))

    def _build_history_tab(self, tab):
        rows = _fetchall("SELECT Titulo_Sprint, Pontos_Planejados, Pontos_Entregues, Velocity FROM Historico_Sprints")
        total = len(rows)
        velocities = [value for value in (_to_number(row[3]) for row in rows) if value is not None]
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0.0
        planned = sum(int(row[1] or 0) for row in rows)
        delivered = sum(int(row[2] or 0) for row in rows)
        self._build_cards(tab, (
            ("Registros", str(total), "históricos de sprint"),
            ("Velocity média", f"{avg_velocity:.1f}%", "entrega sobre o planejado"),
            ("Pontos planejados", str(planned), "total comprometido"),
            ("Pontos entregues", f"{(delivered / planned * 100) if planned else 0:.0f}%", f"{delivered} de {planned} pontos"),
        ))

        def _sprint_groups():
            groups = {}
            for row in rows:
                sprint = (row[0] or "SEM SPRINT").strip() or "SEM SPRINT"
                entry = groups.setdefault(sprint, {"planned": 0, "delivered": 0, "velocity": []})
                entry["planned"] += int(row[1] or 0)
                entry["delivered"] += int(row[2] or 0)
                velocity = _to_number(row[3])
                if velocity is not None:
                    entry["velocity"].append(velocity)
            return groups

        def draw_velocity(ax):
            groups = _sprint_groups()
            if not groups:
                self._empty(ax)
                return
            sprints = sorted(groups)
            averages = [sum(groups[s]["velocity"]) / len(groups[s]["velocity"]) if groups[s]["velocity"] else 0.0 for s in sprints]
            ax.plot(sprints, averages, marker="o", color=CHART_COLORS[0], linewidth=2)
            for x_pos, value in enumerate(averages):
                ax.annotate(f"{value:.0f}%", (x_pos, value), textcoords="offset points",
                            xytext=(0, 6), ha="center", fontsize=8, color=TEXT_FG)
            ax.set_ylim(bottom=0)
            ax.tick_params(axis="x", rotation=20)

        def draw_points(ax):
            groups = _sprint_groups()
            if not groups:
                self._empty(ax)
                return
            sprints = sorted(groups)
            positions = range(len(sprints))
            ax.bar([p - 0.2 for p in positions], [groups[s]["planned"] for s in sprints],
                   width=0.4, color=CHART_COLORS[1], label="Planejados")
            ax.bar([p + 0.2 for p in positions], [groups[s]["delivered"] for s in sprints],
                   width=0.4, color=CHART_COLORS[0], label="Entregues")
            ax.set_xticks(list(positions))
            ax.set_xticklabels(sprints, rotation=20)
            ax.legend(fontsize=8)

        self._build_charts(tab, (
            ("Velocity média por sprint", draw_velocity),
            ("Pontos planejados x entregues", draw_points),
        ))

    def _build_governance_tab(self, tab):
        rows = _fetchall("SELECT Status, Periodicidade FROM Governanca")
        total = len(rows)
        active = sum(1 for row in rows if "ATIV" in (row[0] or "").upper())
        linked = _count("Backlog_Governanca")
        self._build_cards(tab, (
            ("Políticas", str(total), "registros de governança"),
            ("Ativas", f"{(active / total * 100) if total else 0:.0f}%", f"{active} de {total} políticas"),
            ("Periodicidades", str(len({(row[1] or '').strip() for row in rows if (row[1] or '').strip()})), "ciclos distintos"),
            ("Histórias vinculadas", str(linked), "associações com o backlog"),
        ))

        def draw_status(ax):
            self._bar_counts(ax, _counts_by(rows, 0))

        def draw_periodicity(ax):
            self._bar_counts(ax, _counts_by(rows, 1))

        self._build_charts(tab, (
            ("Políticas por status", draw_status),
            ("Políticas por periodicidade", draw_periodicity),
        ))

    def _build_transparency_tab(self, tab):
        rows = _fetchall("SELECT Visibilidade, Frequencia_Publicacao, Responsavel FROM Transparencia")
        total = len(rows)
        linked = _count("Backlog_Transparencia")
        visibilities = len({(row[0] or "").strip() for row in rows if (row[0] or "").strip()})
        owners = len({(row[2] or "").strip() for row in rows if (row[2] or "").strip()})
        self._build_cards(tab, (
            ("Relatórios", str(total), "registros de transparência"),
            ("Visibilidades", str(visibilities), "públicos distintos"),
            ("Responsáveis", str(owners), "pessoas publicando"),
            ("Histórias vinculadas", str(linked), "associações com o backlog"),
        ))

        def draw_visibility(ax):
            self._bar_counts(ax, _counts_by(rows, 0))

        def draw_frequency(ax):
            self._bar_counts(ax, _counts_by(rows, 1))

        self._build_charts(tab, (
            ("Relatórios por visibilidade", draw_visibility),
            ("Relatórios por frequência", draw_frequency),
        ))

    def _build_quality_tab(self, tab):
        rows = _fetchall("SELECT Metrica, Valor_Alvo, Valor_Real, Status FROM Qualidade")
        total = len(rows)
        achievements = []
        for row in rows:
            target = float(row[1] or 0)
            real = float(row[2] or 0)
            achievements.append(min(real / target, 1.0) if target > 0 else 0.0)
        index = sum(achievements) / len(achievements) * 100 if achievements else 0.0
        reached = sum(1 for value in achievements if value >= 1.0)
        linked = _count("Backlog_Qualidade")
        self._build_cards(tab, (
            ("Métricas", str(total), "indicadores de qualidade"),
            ("Índice do projeto", f"{index:.1f}%", "média dos atingimentos"),
            ("Metas atingidas", f"{reached} de {total}", "atingimento em 100%"),
            ("Histórias vinculadas", str(linked), "associações com o backlog"),
        ))

        def draw_achievement(ax):
            if not rows:
                self._empty(ax)
                return
            names = [(row[0] or f"Métrica {i + 1}") for i, row in enumerate(rows)]
            values = [value * 100 for value in achievements]
            colors = [CHART_COLORS[0] if value >= 100 else CHART_COLORS[2] for value in values]
            bars = ax.barh(names, values, color=colors)
            ax.bar_label(bars, fontsize=8, color=TEXT_FG, fmt="%.0f%%")
            ax.axvline(100, color=CHART_COLORS[3], linestyle="--", linewidth=1)
            ax.invert_yaxis()
            ax.set_xlim(0, max(110, max(values, default=0) * 1.15))

        def draw_status(ax):
            self._donut(ax, _counts_by(rows, 3))

        self._build_charts(tab, (
            ("Atingimento por métrica (meta = 100%)", draw_achievement),
            ("Métricas por status", draw_status),
        ))
