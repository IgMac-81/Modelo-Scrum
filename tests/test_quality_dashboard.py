import csv
import shutil

import database
import dashboard_formulario
import data_transfer
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

    frame, average = form._calculate_quality_metrics([
        (1, "COBERTURA", 80, 22.222, "PENDENTE", 0, ""),
    ])
    assert abs(frame.loc[0, "Atingimento"] - 0.2775) < 1e-12
    assert abs(average - 0.2775) < 1e-12


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
        form._format_chart_axes(axis)
        figure.tight_layout(rect=(0.24, 0.24, 0.94, 0.9))
        figure.canvas.draw()
        labels = [label for label in axis.get_xticklabels() if label.get_visible()]
        assert all(label.get_rotation() == 45 for label in labels)
        assert all(label.get_ha() == "right" for label in labels)
        assert all(label.get_va() == "top" for label in labels)
        assert all("\n" in label.get_text() or len(label.get_text()) <= 10 for label in labels)
        bounds = figure.bbox
        for label in labels + [label for label in axis.get_yticklabels() if label.get_visible()]:
            extent = label.get_window_extent()
            assert bounds.contains(*extent.get_points()[0]) and bounds.contains(*extent.get_points()[1]), (
                title, label.get_text(), extent.bounds, bounds.bounds,
            )
