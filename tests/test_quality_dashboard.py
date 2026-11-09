import csv
import shutil
import builtins

import database
import dashboard_formulario
import data_transfer
import formulario
import qualidade_formulario


def _isolated_database(monkeypatch, tmp_path):
    db_path = tmp_path / "quality.db"
    shutil.copy2(database.DB_NAME, db_path)
    original_connect = database.connect_db
    monkeypatch.setattr(
        database, "connect_db",
        lambda path=None: original_connect(path or db_path),
    )
    connection = database.connect_db()
    connection.execute("DELETE FROM Backlog_Qualidade")
    connection.execute("DELETE FROM Qualidade")
    connection.commit()
    connection.close()
    return db_path


def test_quality_rounding_is_used_for_insert_and_update(monkeypatch, tmp_path):
    _isolated_database(monkeypatch, tmp_path)

    record_id = database.save_qualidade(None, "COBERTURA", 5.3333333333, 4.56, "PENDENTE", [])
    record = next(row for row in database.list_qualidade() if row[0] == record_id)
    assert record[:4] == (record_id, "COBERTURA", 5.3, 4.6)

    database.save_qualidade(record_id, "COBERTURA", 80, 22.222, "CONCLUÍDO", [])
    record = next(row for row in database.list_qualidade() if row[0] == record_id)
    assert record[2:4] == (80.0, 22.2)


def test_quality_form_formats_values_and_calculates_rounded_attainment():
    form = object.__new__(qualidade_formulario.QualidadeForm)
    assert form._decimal_from_input("5.3333333333") == 5.3
    assert form._format_decimal(80) == "80,0"
    assert form._format_percentage(22.222 / 100) == "22,2%"

    attainments, average = form._calculate_quality_metrics([
        (1, "COBERTURA", 80, 22.222, "PENDENTE", 0, ""),
    ])
    assert abs(attainments[0] - 0.2775) < 1e-12
    assert abs(average - 0.2775) < 1e-12


def test_quality_calculation_and_module_loading_fall_back_without_pandas():
    def blocked_pandas(_name):
        raise ImportError("DLL load failed while importing timezones")

    pandas_module, import_error = qualidade_formulario._load_optional_pandas(blocked_pandas)
    assert pandas_module is None
    assert "timezones" in str(import_error)

    attainments, average = qualidade_formulario.QualidadeForm._calculate_quality_metrics([
        (1, "COBERTURA", 80, 22.222, "PENDENTE", 0, ""),
        (2, "TESTE", 0, 3, "PENDENTE", 0, ""),
        (3, "VAZIA", 0, 0, "PENDENTE", 0, ""),
    ])
    assert abs(attainments[0] - 0.2775) < 1e-12
    assert attainments[1:] == [1.0, 0.0]
    assert abs(average - (0.2775 + 1.0) / 3) < 1e-12


def test_quality_navigation_reports_import_error_without_hiding_main_menu(monkeypatch):
    app = object.__new__(formulario.BacklogApp)
    app.root = object()
    errors = []
    monkeypatch.setattr(formulario.messagebox, "showerror", lambda *args, **kwargs: errors.append(args))
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "qualidade_formulario":
            raise ImportError("DLL load failed while importing timezones")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    app.show_quality()

    assert errors
    assert "timezones" in errors[0][1]
    assert not hasattr(app, "menu_frame")


def test_quality_navigation_warns_but_opens_when_pandas_uses_fallback(monkeypatch):
    class FakeFrame:
        def pack(self, *_args, **_kwargs):
            pass

        def pack_forget(self):
            pass

    class FakeQualityForm:
        def __init__(self, _root, _callback):
            self.frame = FakeFrame()

    app = object.__new__(formulario.BacklogApp)
    app.root = type("Root", (), {"title": lambda *_args: None})()
    app.menu_frame = FakeFrame()
    app.header = FakeFrame()
    app.content = FakeFrame()
    app.show_main_menu = lambda: None
    app._quality_fallback_warning_shown = False
    warnings = []
    monkeypatch.setattr(qualidade_formulario, "PANDAS_IMPORT_ERROR", ImportError("blocked timezones DLL"))
    monkeypatch.setattr(qualidade_formulario, "QualidadeForm", FakeQualityForm)
    monkeypatch.setattr(formulario.messagebox, "showwarning", lambda *args, **kwargs: warnings.append(args))

    app.show_quality()

    assert app.quality_form is not None
    assert app._quality_fallback_warning_shown
    assert warnings
    assert "cálculos alternativos sem pandas" in warnings[0][1]


def test_quality_decimal_input_validation_rejects_more_than_one_fractional_digit():
    validator = qualidade_formulario.QualidadeForm._is_valid_decimal_entry

    for value in ("", "8", "80", "80.", "80,", "80.0", "80,0", "4.5", "4,5", ".5"):
        assert validator(value), value
    for value in ("4.56", "5.333333", "80.12", "1,23", "abc", "-2.0", "1..0"):
        assert not validator(value), value

    achievement_validator = qualidade_formulario.QualidadeForm._is_valid_achievement_entry
    assert achievement_validator("80,0%")
    assert achievement_validator("22.2%")
    assert not achievement_validator("22,22%")


def test_quality_import_normalizes_values_before_persisting(monkeypatch, tmp_path):
    _isolated_database(monkeypatch, tmp_path)
    monkeypatch.setattr(qualidade_formulario.transfer, "report", lambda *_args: None)
    form = object.__new__(qualidade_formulario.QualidadeForm)
    form.records = []
    form.status_options = ["PENDENTE"]
    form.root = None
    form.refresh_records = lambda: None

    form._import_rows([{
        "Metrica": "COBERTURA",
        "Valor_Alvo": "5.3333333333",
        "Valor_Real": "4.56",
        "Status": "PENDENTE",
    }])

    record = next(row for row in database.list_qualidade() if row[1] == "COBERTURA")
    assert record[2:4] == (5.3, 4.6)


def test_quality_exports_keep_one_decimal_in_csv_excel_and_pdf(tmp_path):
    headers = qualidade_formulario.TRANSFER_HEADERS
    form = object.__new__(qualidade_formulario.QualidadeForm)
    form.records = [(1, "COBERTURA", 80, 22.222, "PENDENTE", 0, "")]
    csv_rows = form._export_rows(as_text=True)
    excel_rows = form._export_rows()

    csv_path = tmp_path / "quality.csv"
    data_transfer.write_csv_file(csv_path, headers, csv_rows)
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        assert list(csv.reader(source))[1] == [
            "1", "COBERTURA", "80.0", "22.2", "27.8%", "PENDENTE",
        ]

    excel_path = tmp_path / "quality.xlsx"
    data_transfer.write_excel_file(excel_path, headers, excel_rows, "Qualidade")
    from openpyxl import load_workbook
    workbook = load_workbook(excel_path, data_only=True)
    sheet = workbook.active
    assert (sheet["C2"].value, sheet["D2"].value) == (80.0, 22.2)
    assert (sheet["C2"].number_format, sheet["D2"].number_format) == ("0.0", "0.0")
    assert (sheet["E2"].value, sheet["E2"].number_format) == (0.2775, "0.0%")
    workbook.close()

    pdf_lines = list(data_transfer._pdf_table_lines("Qualidade", headers, excel_rows))
    assert "ROW 1: 1 | COBERTURA | 80.0 | 22.2 | 27.8% | PENDENTE" in pdf_lines
    pdf_path = tmp_path / "quality.pdf"
    data_transfer.write_tables_pdf_file(pdf_path, [("Qualidade", headers, excel_rows)])
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_dashboard_chart_builders_use_consistent_wrapped_x_labels(monkeypatch):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    samples = {
        "Product_Backlog": [("CONCLUÍDO", "PRIORIDADE MUITO ALTA", 8, "SPRINT COM NOME EXTREMAMENTE LONGO")],
        "Sprints_Backlog": [("EM ANDAMENTO", "12:00", "08:00", "04:00", "SPRINT COM NOME EXTREMAMENTE LONGO")],
        "Historico_Sprints": [("SPRINT COM NOME EXTREMAMENTE LONGO", 8, 5, "62.5%")],
        "Governanca": [("ATIVA", "A CADA DUAS SEMANAS")],
        "Transparencia": [("PÚBLICO INTERNO", "A CADA DUAS SEMANAS", "TIME SCRUM")],
        "Qualidade": [("COBERTURA COM NOME MUITO LONGO", 80, 22.222, "PENDENTE")],
    }

    def fetch(sql):
        table = next(name for name in samples if f"FROM {name}" in sql)
        return samples[table]

    monkeypatch.setattr(dashboard_formulario, "_fetchall", fetch)
    monkeypatch.setattr(dashboard_formulario, "_count", lambda _table: 0)
    form = object.__new__(dashboard_formulario.DashboardForm)
    form._build_cards = lambda *_args: None
    charts = []
    form._build_charts = lambda _tab, entries: charts.extend(entries)

    for builder in (
        form._build_product_tab, form._build_sprints_tab, form._build_history_tab,
        form._build_governance_tab, form._build_transparency_tab, form._build_quality_tab,
    ):
        builder(None)
    assert len(charts) == 12

    for title, draw in charts:
        figure = Figure(figsize=(5.4, 3.1), dpi=100)
        axis = figure.add_subplot(111)
        draw(axis)
        form._fit_chart_layout(figure, axis, title)
        labels = [label for label in axis.get_xticklabels() if label.get_visible()]
        assert all(label.get_rotation() == 0 for label in labels)
        assert all(label.get_ha() == "center" for label in labels)
        assert all("\n" in label.get_text() or len(label.get_text()) <= 14 for label in labels)
        bounds = figure.bbox
        for label in labels + [label for label in axis.get_yticklabels() if label.get_visible()]:
            extent = label.get_window_extent()
            assert bounds.contains(*extent.get_points()[0]) and bounds.contains(*extent.get_points()[1]), (
                title, label.get_text(), extent.bounds, bounds.bounds,
            )
        assert not dashboard_formulario._labels_overlap(labels, figure), title
        assert not dashboard_formulario._labels_overlap(
            [label for label in axis.get_yticklabels() if label.get_visible()], figure,
        ), title


def test_dashboard_chart_layout_expands_dense_categorical_axes_without_overlap():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    form = object.__new__(dashboard_formulario.DashboardForm)
    categories = [f"Categoria {index} com descrição extensa" for index in range(12)]
    figure = Figure(figsize=(5.4, 3.1), dpi=100)
    axis = figure.add_subplot(111)
    axis.bar(categories, range(1, len(categories) + 1))
    form._fit_chart_layout(figure, axis, "Categorias")

    labels = [label for label in axis.get_xticklabels() if label.get_visible()]
    assert figure.get_size_inches()[0] > 5.4
    assert figure.get_size_inches()[0] <= 8.0
    assert all("\n" in label.get_text() for label in labels)
    assert all(label.get_rotation() == 0 and label.get_ha() == "center" for label in labels)
    assert not dashboard_formulario._labels_overlap(labels, figure)
    for label in labels:
        extent = label.get_window_extent()
        assert figure.bbox.contains(*extent.get_points()[0])
        assert figure.bbox.contains(*extent.get_points()[1])

    horizontal_figure = Figure(figsize=(5.4, 3.1), dpi=100)
    horizontal_axis = horizontal_figure.add_subplot(111)
    form._bar_counts(horizontal_axis, {name: index for index, name in enumerate(categories, 1)})
    form._fit_chart_layout(horizontal_figure, horizontal_axis, "Categorias horizontais")
    y_labels = [label for label in horizontal_axis.get_yticklabels() if label.get_visible()]
    assert horizontal_figure.get_size_inches()[1] > 3.1
    assert not dashboard_formulario._labels_overlap(y_labels, horizontal_figure)
    for label in y_labels:
        extent = label.get_window_extent()
        assert horizontal_figure.bbox.contains(*extent.get_points()[0])
        assert horizontal_figure.bbox.contains(*extent.get_points()[1])
