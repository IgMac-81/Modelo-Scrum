import sqlite3
import shutil

import database
import formulario
import governanca_formulario
import historico_formulario
import qualidade_formulario
import sprints_formulario
import transparencia_formulario


class FakeCombo:
    def __init__(self):
        self.values = ()

    def configure(self, **kwargs):
        self.values = kwargs["values"]


class FakeVariable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def test_story_id_resolution_supports_three_digit_ids():
    assert sprints_formulario.SprintBacklogForm._story_id_from_value(
        "US-100 MÓDULO"
    ) == "US-100"
    assert sprints_formulario.SprintBacklogForm._story_id_from_value(
        "US-100"
    ) == "US-100"

    form = object.__new__(sprints_formulario.SprintBacklogForm)
    form.story_map = {"US-100": ("US-100", "MÓDULO", 8)}
    assert form._matches_story("US-100 MÓDULO") == ("US-100", "MÓDULO", 8)


def test_database_connections_enable_foreign_keys_and_migrate_legacy_story_values(tmp_path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE Product_Backlog (Id TEXT PRIMARY KEY, Modulo TEXT);
        CREATE TABLE Sprints_Backlog (
            Id_Task TEXT PRIMARY KEY, Titulo_Sprint TEXT, User_Story TEXT,
            Story_Points INTEGER, Horas_Estimadas TEXT, Status TEXT,
            FOREIGN KEY(User_Story) REFERENCES Product_Backlog(Id)
        );
        CREATE TABLE Historico_Sprints (
            Id_Historico INTEGER PRIMARY KEY, Id_Task TEXT, User_Story TEXT,
            FOREIGN KEY(Id_Task) REFERENCES Sprints_Backlog(Id_Task),
            FOREIGN KEY(User_Story) REFERENCES Product_Backlog(Id)
        );
        INSERT INTO Product_Backlog VALUES ('US-100', 'MÓDULO');
        INSERT INTO Sprints_Backlog VALUES (
            'SB-101', 'SPRINT 1', 'US-100 MÓDULO', 8, '02:00', 'CONCLUÍDO'
        );
        INSERT INTO Historico_Sprints VALUES (1, 'SB-101', 'TAREFA ANTIGA');
    """)
    conn.commit()
    conn.close()

    conn = database.connect_db(db_path)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute(
        "SELECT User_Story FROM Sprints_Backlog WHERE Id_Task='SB-101'"
    ).fetchone()[0] == "US-100"
    assert conn.execute(
        "SELECT User_Story FROM Historico_Sprints WHERE Id_Historico=1"
    ).fetchone()[0] == "US-100"
    try:
        conn.execute(
            "INSERT INTO Sprints_Backlog (Id_Task, User_Story) VALUES (?, ?)",
            ("SB-102", "US-404"),
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Invalid story references must be rejected")
    conn.close()


def test_shipped_database_migration_leaves_no_foreign_key_violations(tmp_path):
    db_path = tmp_path / "seed-copy.db"
    shutil.copy2(database.DB_NAME, db_path)

    conn = database.connect_db(db_path)

    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    conn.close()


def test_backlog_refresh_updates_both_sprint_selectors(monkeypatch):
    monkeypatch.setattr(formulario, "get_sprints", lambda: ["SPRINT 4", "SPRINT 5"])
    form = object.__new__(formulario.BacklogApp)
    form.sprint_combo = FakeCombo()
    form.sprint_filter_combo = FakeCombo()
    form.sprint_filter_var = FakeVariable("SPRINT 3")

    form._refresh_sprint_options()

    assert form.sprint_combo.values == ["SPRINT 4", "SPRINT 5"]
    assert form.sprint_filter_combo.values == ["TODAS", "SPRINT 4", "SPRINT 5"]
    assert form.sprint_filter_var.get() == "TODAS"


def test_returning_to_backlog_refreshes_records_and_sprint_options():
    class FakeFrame:
        def pack(self, **_kwargs):
            pass

        def pack_forget(self):
            pass

    class FakeRoot:
        def title(self, _title):
            pass

    form = object.__new__(formulario.BacklogApp)
    form.root = FakeRoot()
    form.menu_frame = FakeFrame()
    form.header = FakeFrame()
    form.content = FakeFrame()
    form.refresh_records = lambda: setattr(form, "was_refreshed", True)

    form.show_backlog()

    assert form.was_refreshed


def test_history_refresh_updates_sprint_selector(monkeypatch):
    monkeypatch.setattr(
        historico_formulario, "get_history_sprint_titles",
        lambda: ["SPRINT 4", "SPRINT 5"],
    )
    form = object.__new__(historico_formulario.HistoricoSprintsForm)
    form.sprint_combo = FakeCombo()

    form._refresh_sprint_titles()

    assert form.sprint_titles == ["SPRINT 4", "SPRINT 5"]
    assert form.sprint_combo.values == ["SPRINT 4", "SPRINT 5"]


def test_import_handlers_skip_records_missing_required_fields(monkeypatch):
    cases = (
        (formulario.BacklogApp, formulario, "insert_product_backlog",
         {"records": [], "status_options": ["PRONTO"]},
         [{"Id": "US-101", "Módulo": "MÓDULO", "História": "HISTÓRIA"}]),
        (governanca_formulario.GovernancaForm, governanca_formulario, "save_governanca",
         {"records": [], "status_options": ["ATIVA"]},
         [{"Politica": "POLÍTICA", "Responsavel": "TIME", "Periodicidade": "MENSAL"}]),
        (transparencia_formulario.TransparenciaForm, transparencia_formulario, "save_transparencia",
         {"records": []},
         [{"Relatorio": "RELATÓRIO", "Frequencia_Publicacao": "SEMANAL",
           "Responsavel": "TIME"}]),
        (qualidade_formulario.QualidadeForm, qualidade_formulario, "save_qualidade",
         {"records": [], "status_options": ["PENDENTE"]},
         [{"Metrica": "COBERTURA", "Valor_Alvo": "80", "Status": "PENDENTE"}]),
    )
    for form_class, module, save_name, attributes, rows in cases:
        saved = []
        monkeypatch.setattr(module, save_name, lambda *args: saved.append(args))
        monkeypatch.setattr(module.transfer, "report", lambda *_args: None)
        monkeypatch.setattr(module.messagebox, "showinfo", lambda *_args, **_kwargs: None)
        form = object.__new__(form_class)
        form.root = None
        form.refresh_records = lambda: None
        for name, value in attributes.items():
            setattr(form, name, value)

        form._import_rows(rows)

        assert saved == [], f"{form_class.__name__} imported a record with missing fields"


def test_sprint_import_rejects_unresolved_story_and_stores_canonical_id(monkeypatch):
    saved = []
    monkeypatch.setattr(sprints_formulario, "insert_sprint_backlog",
                        lambda *args: saved.append(args))
    monkeypatch.setattr(sprints_formulario.transfer, "report", lambda *_args: None)
    form = object.__new__(sprints_formulario.SprintBacklogForm)
    form.records = []
    form.story_map = {"US-100": ("US-100", "MÓDULO", 8)}
    form.status_data = {"EM ANDAMENTO": {}}
    form.root = None
    form.refresh_records = lambda: None

    form._import_rows([
        {"Id_Task": "SB-101", "Titulo_Sprint": "SPRINT 1",
         "User_Story": "US-404 MÓDULO", "Subtarefa_Tecnica": "IMPLEMENTAR",
         "Status": "EM ANDAMENTO"},
        {"Id_Task": "SB-102", "Titulo_Sprint": "SPRINT 1",
         "User_Story": "US-100 MÓDULO", "Subtarefa_Tecnica": "IMPLEMENTAR",
         "Status": "EM ANDAMENTO"},
    ])

    assert len(saved) == 1
    assert saved[0][0] == "SB-102"
    assert saved[0][2] == "US-100"


def test_sprint_import_rejects_malformed_hours():
    assert sprints_formulario.SprintBacklogForm._import_time_to_minutes("12:30") == 750
    for value in ("invalid", "12:75", "1:2"):
        try:
            sprints_formulario.SprintBacklogForm._import_time_to_minutes(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{value!r} should be rejected")


def _sprint_form_for_save():
    form = object.__new__(sprints_formulario.SprintBacklogForm)
    form.id_var = FakeVariable("SB-101")
    form.sprint_var = FakeVariable("SPRINT 1")
    form.story_var = FakeVariable("US-01 MÓDULO")
    form.subtask_var = FakeVariable("IMPLEMENTAR")
    form.owner_var = FakeVariable("ANA")
    form.points_var = FakeVariable("")
    form.estimated_var = FakeVariable("01:00")
    form.spent_var = FakeVariable("00:30")
    form.remaining_var = FakeVariable("")
    form.status_var = FakeVariable("EM ANDAMENTO")
    form.completion_var = FakeVariable("")
    form.story_entry = type("Entry", (), {"placeholder": "Ex.: US-01 USUÁRIOS"})()
    form.sprint_entry = type("Entry", (), {"placeholder": "Ex.: SPRINT 4"})()
    form.subtask_entry = type("Entry", (), {"placeholder": "Ex.: CRIAR TELA DE CADASTRO"})()
    form.owner_entry = type("Entry", (), {"placeholder": "Ex.: ANA SILVA"})()
    form.date_entry = type("Entry", (), {"placeholder": "DD/MM/AAAA"})()
    form.story_map = {"US-01": ("US-01", "MÓDULO", 5)}
    form.records = []
    form.editing_id = None
    form.root = None
    form.refresh_records = lambda: None
    form.clear_form = lambda: None
    return form


def test_sprint_save_rejects_subtask_placeholder_as_missing(monkeypatch):
    saved = []
    warnings = []
    monkeypatch.setattr(sprints_formulario, "insert_sprint_backlog",
                        lambda *args: saved.append(args))
    monkeypatch.setattr(sprints_formulario.messagebox, "showwarning",
                        lambda title, text, **_kwargs: warnings.append((title, text)))
    form = _sprint_form_for_save()
    form.subtask_var.set(form.subtask_entry.placeholder)

    form.save_record()

    assert saved == []
    assert warnings and "Subtarefa técnica" in warnings[0][1]


def test_sprint_save_rejects_sprint_title_placeholder_as_missing(monkeypatch):
    saved = []
    warnings = []
    monkeypatch.setattr(sprints_formulario, "insert_sprint_backlog",
                        lambda *args: saved.append(args))
    monkeypatch.setattr(sprints_formulario.messagebox, "showwarning",
                        lambda title, text, **_kwargs: warnings.append((title, text)))
    form = _sprint_form_for_save()
    form.sprint_var.set(form.sprint_entry.placeholder)

    form.save_record()

    assert saved == []
    assert warnings and "Título da sprint" in warnings[0][1]


def test_sprint_save_stores_owner_placeholder_as_empty(monkeypatch):
    saved = []
    monkeypatch.setattr(sprints_formulario, "insert_sprint_backlog",
                        lambda *args: saved.append(args))
    monkeypatch.setattr(sprints_formulario.messagebox, "showinfo",
                        lambda *_args, **_kwargs: None)
    form = _sprint_form_for_save()
    form.owner_var.set(form.owner_entry.placeholder)

    form.save_record()

    assert len(saved) == 1
    assert saved[0][3] == "IMPLEMENTAR"
    assert saved[0][4] == ""


def test_sprint_save_normalizes_time_without_focus_out(monkeypatch):
    saved = []
    monkeypatch.setattr(sprints_formulario, "insert_sprint_backlog",
                        lambda *args: saved.append(args))
    monkeypatch.setattr(sprints_formulario.messagebox, "showinfo",
                        lambda *_args, **_kwargs: None)
    form = _sprint_form_for_save()
    form.estimated_var.set("123")

    form.save_record()

    assert len(saved) == 1
    assert saved[0][6:9] == ("12:30", "00:30", "12:00")


def test_history_import_rejects_unknown_tasks_and_uses_task_data(monkeypatch):
    saved = []
    monkeypatch.setattr(
        historico_formulario, "get_sprint_task_for_history",
        lambda task_id: (
            ("SB-102", "SPRINT 1", "US-100", 8, "02:00", "EM ANDAMENTO", "US-100 MÓDULO")
            if task_id == "SB-102" else None
        ),
    )
    monkeypatch.setattr(historico_formulario, "insert_history_sprint",
                        lambda *args: saved.append(args))
    monkeypatch.setattr(historico_formulario.transfer, "report", lambda *_args: None)
    form = object.__new__(historico_formulario.HistoricoSprintsForm)
    form.records = []
    form.status_data = {"EM ANDAMENTO": {}}
    form.root = None
    form.refresh_records = lambda: None

    form._import_rows([
        {"Id_Task": "SB-404", "Status_Sprint": "EM ANDAMENTO"},
        {"Id_Task": "SB-102", "Status_Sprint": "EM ANDAMENTO",
         "Data_Inicio": "31/02/2026"},
        {"Id_Task": "SB-102", "Status_Sprint": "EM ANDAMENTO"},
    ])

    assert len(saved) == 1
    assert saved[0][1:4] == ("SB-102", "SPRINT 1", "US-100")
