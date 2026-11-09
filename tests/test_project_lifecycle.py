import sqlite3

from openpyxl import load_workbook

import data_transfer
import database
import formulario


PROJECT_TABLES = (
    "Backlog_Governanca", "Backlog_Transparencia", "Backlog_Qualidade",
    "Historico_Sprints", "Sprints_Backlog", "Product_Backlog",
    "Governanca", "Transparencia", "Qualidade", "Roadmap",
)
REFERENCE_TABLES = ("Fibonacci", "Status_ProductBacklog", "Status_Sprint")


class FakeForm:
    def __init__(self, events, name):
        self.events = events
        self.name = name

    def refresh_records(self):
        self.events.append(f"refresh:{self.name}")

    def clear_form(self):
        self.events.append(f"clear:{self.name}")


def _build_database(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE Product_Backlog (Id TEXT PRIMARY KEY, Modulo TEXT, record TEXT);
        CREATE TABLE Sprints_Backlog (
            Id_Task TEXT PRIMARY KEY, User_Story TEXT, record TEXT
        );
        CREATE TABLE Historico_Sprints (
            Id_Historico INTEGER PRIMARY KEY, Id_Task TEXT, User_Story TEXT
        );
        CREATE TABLE Backlog_Governanca (record TEXT);
        CREATE TABLE Backlog_Transparencia (record TEXT);
        CREATE TABLE Backlog_Qualidade (record TEXT);
        CREATE TABLE Governanca (record TEXT);
        CREATE TABLE Transparencia (record TEXT);
        CREATE TABLE Qualidade (record TEXT);
        CREATE TABLE Roadmap (record TEXT);
        CREATE TABLE Fibonacci (record TEXT);
        CREATE TABLE Status_ProductBacklog (record TEXT);
        CREATE TABLE Status_Sprint (record TEXT);
        CREATE TABLE System_Settings (record TEXT);

        INSERT INTO Product_Backlog VALUES ('US-01', 'MÓDULO', 'história');
        INSERT INTO Sprints_Backlog VALUES ('SB-101', 'US-01', 'tarefa');
        INSERT INTO Historico_Sprints VALUES (1, 'SB-101', 'US-01');
        INSERT INTO Backlog_Governanca VALUES ('vínculo gov');
        INSERT INTO Backlog_Transparencia VALUES ('vínculo transp');
        INSERT INTO Backlog_Qualidade VALUES ('vínculo qualidade');
        INSERT INTO Governanca VALUES ('política');
        INSERT INTO Transparencia VALUES ('relatório');
        INSERT INTO Qualidade VALUES ('métrica');
        INSERT INTO Roadmap VALUES ('fase');
        INSERT INTO Fibonacci VALUES ('8');
        INSERT INTO Status_ProductBacklog VALUES ('PRONTO');
        INSERT INTO Status_Sprint VALUES ('CONCLUÍDO');
        INSERT INTO System_Settings VALUES ('configuração');
    """)
    conn.commit()
    conn.close()


def test_reset_clears_project_records_but_preserves_schema_and_references(tmp_path):
    db_path = tmp_path / "project.db"
    _build_database(db_path)
    conn = sqlite3.connect(db_path)
    original_tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    conn.close()

    database.reset_project_data(db_path)

    conn = sqlite3.connect(db_path)
    remaining_tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    assert remaining_tables == original_tables
    for table in PROJECT_TABLES:
        assert conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 0
    for table in (*REFERENCE_TABLES, "System_Settings"):
        assert conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 1
    conn.close()


def test_database_export_includes_every_table_in_csv_excel_and_pdf(tmp_path):
    db_path = tmp_path / "project.db"
    _build_database(db_path)
    tables = database.get_database_tables(db_path)
    table_names = {table[0] for table in tables}
    assert table_names == set(PROJECT_TABLES) | set(REFERENCE_TABLES) | {"System_Settings"}

    csv_path = tmp_path / "project.csv"
    data_transfer.write_database_export(csv_path, "csv", tables)
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        csv_text = source.read()
    for table_name in table_names:
        assert f"TABLE: {table_name}" in csv_text
    assert "história" in csv_text
    assert "configuração" in csv_text

    excel_path = tmp_path / "project.xlsx"
    data_transfer.write_database_export(excel_path, "xlsx", tables)
    workbook = load_workbook(excel_path, read_only=True, data_only=False)
    assert set(workbook.sheetnames) == table_names
    assert workbook["Fibonacci"]["A2"].value == "8"
    assert workbook["Product_Backlog"]["C2"].value == "história"
    workbook.close()

    pdf_path = tmp_path / "project.pdf"
    data_transfer.write_database_export(pdf_path, "pdf", tables)
    assert pdf_path.read_bytes().startswith(b"%PDF-")


def _new_project_test_app(events):
    app = object.__new__(formulario.BacklogApp)
    app.root = None
    app.refresh_records = lambda: events.append("refresh:product")
    app.clear_form = lambda: events.append("clear:product")
    for name in ("sprint_form", "history_form", "governance_form",
                 "transparency_form", "quality_form", "dashboard_form"):
        setattr(app, name, FakeForm(events, name))
    app._choose_project_export_format = lambda: "csv"
    app._confirm_project_reset = lambda: events.append("confirm:reset") or True
    return app


def test_new_project_exports_before_reset_and_refreshes_open_forms(monkeypatch, tmp_path):
    events = []
    app = _new_project_test_app(events)
    db_path = tmp_path / "project.db"
    _build_database(db_path)
    monkeypatch.setattr(formulario.messagebox, "askyesnocancel",
                        lambda *_args, **_kwargs: events.append("ask:export") or True)
    app._choose_project_export_format = lambda: "csv"
    monkeypatch.setattr(formulario.filedialog, "asksaveasfilename",
                        lambda **_kwargs: str(tmp_path / "project.csv"))
    monkeypatch.setattr(formulario, "get_database_tables",
                        lambda: events.append("snapshot") or database.get_database_tables(db_path))
    write_export = data_transfer.write_database_export
    def write_export_and_record(path, file_format, rows):
        events.append(("export", path, file_format, rows))
        write_export(path, file_format, rows)
    monkeypatch.setattr(data_transfer, "write_database_export", write_export_and_record)
    yes_no_responses = iter((True,))
    monkeypatch.setattr(formulario.messagebox, "askyesno",
                        lambda *_args, **_kwargs: next(yes_no_responses))
    monkeypatch.setattr(formulario, "reset_project_data",
                        lambda: events.append("reset") or database.reset_project_data(db_path))
    monkeypatch.setattr(formulario.messagebox, "showinfo",
                        lambda *_args, **_kwargs: None)

    app.start_new_project()

    export_index = next(
        index for index, event in enumerate(events)
        if isinstance(event, tuple) and event[0] == "export"
    )
    assert export_index < events.index("reset")
    exported_tables = events[export_index][3]
    assert events[export_index][1:3] == (str(tmp_path / "project.csv"), "csv")
    assert any(table[0] == "Product_Backlog" and table[2] for table in exported_tables)
    with (tmp_path / "project.csv").open(newline="", encoding="utf-8-sig") as source:
        exported = source.read()
    assert "TABLE: Product_Backlog" in exported and "história" in exported
    assert "TABLE: Fibonacci" in exported and "TABLE: System_Settings" in exported
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM Product_Backlog").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM Fibonacci").fetchone()[0] == 1
    conn.close()
    assert "refresh:product" in events and "clear:product" in events
    for form_name in ("sprint_form", "history_form", "governance_form",
                      "transparency_form", "quality_form", "dashboard_form"):
        assert f"refresh:{form_name}" in events
    assert events.index("reset") < events.index("refresh:product")


def test_declining_export_and_confirming_creates_empty_project(monkeypatch, tmp_path):
    events = []
    app = _new_project_test_app(events)
    db_path = tmp_path / "project.db"
    _build_database(db_path)
    monkeypatch.setattr(formulario.messagebox, "askyesnocancel",
                        lambda *_args, **_kwargs: False)
    app._confirm_project_reset = lambda: True
    monkeypatch.setattr(formulario, "reset_project_data",
                        lambda: database.reset_project_data(db_path))
    monkeypatch.setattr(formulario.messagebox, "showinfo",
                        lambda *_args, **_kwargs: None)

    app.start_new_project()

    conn = sqlite3.connect(db_path)
    for table in PROJECT_TABLES:
        assert conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 0
    for table in (*REFERENCE_TABLES, "System_Settings"):
        assert conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 1
    conn.close()
    assert "refresh:product" in events


def test_new_project_cancellation_never_resets_data(monkeypatch):
    events = []
    app = _new_project_test_app(events)
    monkeypatch.setattr(formulario.messagebox, "askyesnocancel",
                        lambda *_args, **_kwargs: None)
    monkeypatch.setattr(formulario, "reset_project_data",
                        lambda: events.append("reset"))

    app.start_new_project()

    assert "reset" not in events
    assert events == []


def test_cancel_after_export_keeps_current_project(monkeypatch, tmp_path):
    events = []
    app = _new_project_test_app(events)
    monkeypatch.setattr(formulario.messagebox, "askyesnocancel",
                        lambda *_args, **_kwargs: True)
    monkeypatch.setattr(formulario.filedialog, "asksaveasfilename",
                        lambda **_kwargs: str(tmp_path / "project.csv"))
    monkeypatch.setattr(formulario, "get_database_tables", lambda: [])
    monkeypatch.setattr(data_transfer, "write_database_export",
                        lambda *_args: events.append("export"))
    monkeypatch.setattr(formulario.messagebox, "askyesno",
                        lambda *_args, **_kwargs: False)
    monkeypatch.setattr(formulario, "reset_project_data",
                        lambda: events.append("reset"))

    app.start_new_project()

    assert events == ["export"]


def test_cancel_save_dialog_keeps_current_project(monkeypatch):
    events = []
    app = _new_project_test_app(events)
    monkeypatch.setattr(formulario.messagebox, "askyesnocancel",
                        lambda *_args, **_kwargs: True)
    monkeypatch.setattr(formulario.filedialog, "asksaveasfilename",
                        lambda **_kwargs: "")
    monkeypatch.setattr(formulario, "reset_project_data",
                        lambda: events.append("reset"))

    app.start_new_project()

    assert events == []
