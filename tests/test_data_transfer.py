import csv

from openpyxl import load_workbook

import data_transfer


def _mock_export_dialogs(monkeypatch, path):
    monkeypatch.setattr(
        data_transfer.filedialog, "asksaveasfilename",
        lambda **_kwargs: str(path),
    )
    monkeypatch.setattr(data_transfer.messagebox, "showinfo", lambda *_args, **_kwargs: None)


def test_csv_export_escapes_formula_like_text(tmp_path, monkeypatch):
    path = tmp_path / "export.csv"
    _mock_export_dialogs(monkeypatch, path)

    data_transfer.export_csv(
        None, "Export", "export.csv", ("value",),
        (("=1+1",), ("+SUM(A1:A2)",), ("-1+1",),
         ("  @SUM(A1:A2)",), ("ordinary text",), (-1,)),
    )

    with path.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.reader(source))
    assert rows == [
        ["value"],
        ["'=1+1"],
        ["'+SUM(A1:A2)"],
        ["'-1+1"],
        ["'  @SUM(A1:A2)"],
        ["ordinary text"],
        ["-1"],
    ]


def test_excel_export_writes_formula_like_text_as_string(tmp_path, monkeypatch):
    path = tmp_path / "export.xlsx"
    _mock_export_dialogs(monkeypatch, path)

    data_transfer.export_excel(
        None, "Export", "export.xlsx", "Data", ("value",),
        (("=1+1",), ("+SUM(A1:A2)",), ("ordinary text",)),
    )

    workbook = load_workbook(path, data_only=False)
    sheet = workbook.active
    assert [sheet.cell(row=row, column=1).value for row in range(2, 5)] == [
        "=1+1", "+SUM(A1:A2)", "ordinary text",
    ]
    assert [sheet.cell(row=row, column=1).data_type for row in range(2, 5)] == [
        "s", "s", "s",
    ]
    workbook.close()


def test_import_field_validation_rejects_missing_values():
    assert not data_transfer.has_required_fields(
        {"politica": "POLÍTICA"}, ("politica",), ("responsavel",), ("status",),
    )
    assert data_transfer.has_required_fields(
        {"politica": "POLÍTICA", "responsavel": "TIME", "status": "ATIVA"},
        ("politica",), ("responsavel",), ("status",),
    )


def test_numeric_import_values_must_be_finite_and_integral():
    assert data_transfer.parse_integer("8.0") == 8
    assert data_transfer.parse_number("12,5") == 12.5
    for value in ("", "abc", "NaN", "Infinity"):
        try:
            data_transfer.parse_number(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{value!r} should be rejected")
    for value in ("abc", "1.5", "Infinity"):
        try:
            data_transfer.parse_integer(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{value!r} should be rejected")
