import csv

from openpyxl import load_workbook

import data_transfer
import historico_formulario


def _form_with_history_records():
    form = object.__new__(historico_formulario.HistoricoSprintsForm)
    form.records = [
        (1, "SB-101", "SPRINT 1", "US-01", None, None, 8, 5, "62.567%", "12:00", "CONCLUÍDO"),
        (2, "SB-102", "SPRINT 1", "US-02", None, None, 3, 0, 0, "08:00", "PLANEJADO"),
    ]
    return form


def test_history_export_rows_share_treeview_velocity_format():
    form = _form_with_history_records()

    exported = form._export_rows()

    assert exported[0][8] == form._format_velocity(form.records[0][8]) == "62,6%"
    assert exported[1][8] == form._format_velocity(form.records[1][8]) == "0,0%"


def test_history_csv_excel_and_pdf_export_formatted_velocity(tmp_path):
    form = _form_with_history_records()
    headers = historico_formulario.TRANSFER_HEADERS
    rows = form._export_rows()

    csv_path = tmp_path / "history.csv"
    data_transfer.write_csv_file(csv_path, headers, rows)
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        csv_rows = list(csv.reader(source))
    assert csv_rows[1][8] == "62,6%"
    assert csv_rows[2][8] == "0,0%"

    excel_path = tmp_path / "history.xlsx"
    data_transfer.write_excel_file(excel_path, headers, rows, "Histórico")
    workbook = load_workbook(excel_path, data_only=True)
    sheet = workbook.active
    assert (sheet["I2"].value, sheet["I3"].value) == ("62,6%", "0,0%")
    workbook.close()

    table_rows = [("Historico_Sprints", headers, form.records)]
    pdf_lines = list(data_transfer._pdf_table_lines(*table_rows[0]))
    assert "ROW 1: 1 | SB-101 | SPRINT 1 | US-01 |  |  | 8 | 5 | 62,6% | 12:00 | CONCLUÍDO" in pdf_lines
    pdf_path = tmp_path / "history.pdf"
    data_transfer.write_tables_pdf_file(pdf_path, table_rows)
    assert pdf_path.read_bytes().startswith(b"%PDF")
