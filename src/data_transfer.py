import csv
import textwrap
import zipfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from tkinter import filedialog, messagebox, ttk

DEPENDENCY_ERROR_TITLE = "Dependência ausente"
DEPENDENCY_ERROR_MESSAGE = "Instale as dependências com: pip install -r requirements.txt"


def add_transfer_buttons(parent, handler):
    for label, command in (
        ("Importar CSV", handler.import_csv),
        ("Importar Excel", handler.import_excel),
        ("Exportar CSV", handler.export_csv),
        ("Exportar Excel", handler.export_excel),
    ):
        ttk.Button(parent, text=label, command=command).pack(side="left", padx=(0, 6))


def csv_safe_value(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def normalize_one_decimal(value):
    try:
        number = Decimal(str(value).strip().replace(",", "."))
        if not number.is_finite():
            raise ValueError("O valor numérico deve ser finito.")
        return number.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    except InvalidOperation as error:
        raise ValueError("Informe um valor numérico válido.") from error


def format_one_decimal(value, decimal_separator="."):
    return f"{normalize_one_decimal(value):.1f}".replace(".", decimal_separator)


def quality_attainment(target, actual):
    normalized_target = normalize_one_decimal(target)
    normalized_actual = normalize_one_decimal(actual)
    if normalized_target <= 0:
        return 0.0
    return min(float(normalized_actual / normalized_target), 1.0)


def format_velocity(value):
    if value is None or value == "":
        return "0,0%"
    text = str(value).strip().replace("%", "").replace(",", ".")
    try:
        return f"{format_one_decimal(text, decimal_separator=',')}%"
    except ValueError:
        return str(value)


def _history_table_rows(headers, rows):
    velocity_columns = {
        index for index, name in enumerate(headers)
        if str(name).strip().casefold() in {"velocity", "velocity_%"}
    }
    if not velocity_columns:
        return rows
    formatted_rows = []
    for row in rows:
        values = list(row)
        for index in velocity_columns:
            if index < len(values):
                values[index] = format_velocity(values[index])
        formatted_rows.append(tuple(values))
    return formatted_rows


def _quality_table_rows(headers, rows, as_text=False, include_attainment=False):
    output_headers = list(headers)
    decimal_columns = {
        index for index, name in enumerate(headers)
        if str(name).strip().casefold() in {"valor_alvo", "valor_real"}
    }
    attainment_index = next(
        (index for index, name in enumerate(output_headers)
         if str(name).strip().casefold() == "atingimento"),
        None,
    )
    append_attainment = include_attainment and attainment_index is None
    if append_attainment:
        attainment_index = next(
            (index for index, name in enumerate(output_headers)
             if str(name).strip().casefold() == "status"),
            len(output_headers),
        )
        output_headers.insert(attainment_index, "Atingimento")
    formatted_rows = []
    for row in rows:
        values = list(row)
        for index in decimal_columns:
            if index < len(values) and values[index] is not None:
                values[index] = (
                    format_one_decimal(values[index])
                    if as_text else float(normalize_one_decimal(values[index]))
                )
        target_index = next(
            (index for index, name in enumerate(output_headers)
             if str(name).strip().casefold() == "valor_alvo"),
            None,
        )
        actual_index = next(
            (index for index, name in enumerate(output_headers)
             if str(name).strip().casefold() == "valor_real"),
            None,
        )
        if attainment_index is not None and target_index is not None and actual_index is not None:
            attainment = quality_attainment(values[target_index], values[actual_index])
            formatted_attainment = (
                f"{format_one_decimal(attainment * 100)}%"
                if as_text else attainment
            )
            if append_attainment:
                values.insert(attainment_index, formatted_attainment)
            elif attainment_index < len(values):
                values[attainment_index] = formatted_attainment
        formatted_rows.append(tuple(values))
    return output_headers, formatted_rows


def _write_csv_rows(writer, rows):
    writer.writerows(
        [csv_safe_value(value) for value in row]
        for row in rows
    )


def _write_excel_sheet(sheet, headers, rows):
    sheet.append(list(headers))
    decimal_columns = {
        index + 1 for index, name in enumerate(headers)
        if str(name).strip().casefold() in {"valor_alvo", "valor_real"}
    }
    attainment_columns = {
        index + 1 for index, name in enumerate(headers)
        if str(name).strip().casefold() == "atingimento"
    }
    for record in rows:
        sheet.append(["" if value is None else value for value in record])
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
            if cell.column in decimal_columns and cell.value != "":
                cell.number_format = "0.0"
            if cell.column in attainment_columns and cell.value != "":
                cell.number_format = "0.0%"


def write_csv_file(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as output:
        writer = csv.writer(output)
        writer.writerow(headers)
        _write_csv_rows(writer, rows)


def write_excel_file(path, headers, rows, sheet_name="Data"):
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name[:31]
    _write_excel_sheet(sheet, headers, rows)
    workbook.save(path)


def export_csv(parent, title, initialfile, headers, rows):
    path = filedialog.asksaveasfilename(parent=parent, title=title, defaultextension=".csv",
                                        filetypes=[("CSV", "*.csv")], initialfile=initialfile)
    if not path:
        return
    try:
        write_csv_file(path, headers, rows)
        messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{path}", parent=parent)
    except OSError as error:
        messagebox.showerror("Erro ao exportar CSV", str(error), parent=parent)


def export_excel(parent, title, initialfile, sheet_name, headers, rows):
    path = filedialog.asksaveasfilename(parent=parent, title=title, defaultextension=".xlsx",
                                        filetypes=[("Excel", "*.xlsx")], initialfile=initialfile)
    if not path:
        return
    try:
        write_excel_file(path, headers, rows, sheet_name)
        messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{path}", parent=parent)
    except ImportError:
        messagebox.showerror(DEPENDENCY_ERROR_TITLE, DEPENDENCY_ERROR_MESSAGE, parent=parent)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        messagebox.showerror("Erro ao exportar Excel", str(error), parent=parent)


def write_tables_csv_file(path, tables):
    with open(path, "w", newline="", encoding="utf-8-sig") as output:
        writer = csv.writer(output)
        for table_name, headers, rows in tables:
            writer.writerow((f"TABLE: {table_name}",))
            output_headers = headers
            if table_name.casefold() == "qualidade":
                output_headers, rows = _quality_table_rows(
                    headers, rows, as_text=True, include_attainment=True,
                )
            elif table_name.casefold() == "historico_sprints":
                rows = _history_table_rows(headers, rows)
            writer.writerow(output_headers)
            _write_csv_rows(writer, rows)
            writer.writerow(())


def write_tables_excel_file(path, tables):
    from openpyxl import Workbook
    workbook = Workbook()
    workbook.remove(workbook.active)
    for table_name, headers, rows in tables:
        sheet = workbook.create_sheet(table_name[:31])
        if table_name.casefold() == "qualidade":
            headers, rows = _quality_table_rows(
                headers, rows, include_attainment=True,
            )
        elif table_name.casefold() == "historico_sprints":
            rows = _history_table_rows(headers, rows)
        _write_excel_sheet(sheet, headers, rows)
    workbook.save(path)


def _pdf_table_lines(table_name, headers, rows):
    yield f"TABLE: {table_name}"
    if table_name.casefold() == "qualidade":
        headers, rows = _quality_table_rows(
            headers, rows, as_text=True, include_attainment=True,
        )
    elif table_name.casefold() == "historico_sprints":
        rows = _history_table_rows(headers, rows)
    yield "COLUMNS: " + " | ".join(str(value) for value in headers)
    for index, row in enumerate(rows, start=1):
        values = " | ".join(
            "" if value is None else str(value).replace("\r", "\\r").replace("\n", "\\n")
            for value in row
        )
        for line in textwrap.wrap(f"ROW {index}: {values}", width=145,
                                  replace_whitespace=False, drop_whitespace=False):
            yield line
    yield ""


def write_tables_pdf_file(path, tables):
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure
    lines = [line for table in tables for line in _pdf_table_lines(*table)]
    if not lines:
        lines = ["No tables found."]
    with PdfPages(path) as pdf:
        for start in range(0, len(lines), 48):
            figure = Figure(figsize=(11.7, 8.3))
            figure.text(0.04, 0.96, "\n".join(lines[start:start + 48]),
                        family="monospace", fontsize=7, va="top")
            pdf.savefig(figure)
            figure.clear()


def write_database_export(path, file_format, tables):
    if file_format == "csv":
        write_tables_csv_file(path, tables)
    elif file_format == "xlsx":
        write_tables_excel_file(path, tables)
    elif file_format == "pdf":
        write_tables_pdf_file(path, tables)
    else:
        raise ValueError(f"Formato de exportação não suportado: {file_format}")


def read_csv(parent, title):
    path = filedialog.askopenfilename(parent=parent, title=title, filetypes=[("CSV", "*.csv")])
    if not path:
        return None
    try:
        with open(path, newline="", encoding="utf-8-sig") as source:
            return list(csv.DictReader(source))
    except (OSError, csv.Error, UnicodeError) as error:
        messagebox.showerror("Erro ao importar CSV", str(error), parent=parent)
        return None


def read_excel(parent, title):
    path = filedialog.askopenfilename(parent=parent, title=title, filetypes=[("Excel", "*.xlsx")])
    if not path:
        return None
    try:
        from openpyxl import load_workbook
        workbook = load_workbook(path, read_only=True, data_only=True)
        rows = workbook.active.iter_rows(values_only=True)
        headers = next(rows, ())
        data = [dict(zip(headers, row)) for row in rows]
        workbook.close()
        return data
    except ImportError:
        messagebox.showerror(DEPENDENCY_ERROR_TITLE, DEPENDENCY_ERROR_MESSAGE, parent=parent)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        messagebox.showerror("Erro ao importar Excel", str(error), parent=parent)
    return None


def normalized(row):
    return {str(key).strip().casefold(): value for key, value in row.items() if key is not None}


def field(row, *names):
    value = next((row[name] for name in names if name in row), "")
    return "" if value is None else str(value).strip()


def has_required_fields(row, *field_groups):
    return all(
        any(field(row, name) for name in group)
        for group in field_groups
    )


def parse_number(value):
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as error:
        raise ValueError("Informe um valor numérico válido.") from error
    if not number.is_finite():
        raise ValueError("O valor numérico deve ser finito.")
    return float(number)


def parse_integer(value):
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as error:
        raise ValueError("Informe um número inteiro válido.") from error
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError("Informe um número inteiro válido.")
    return int(number)


def report(parent, imported, skipped):
    messagebox.showinfo("Importação concluída",
                        f"Importados: {imported}\nIgnorados ou inválidos: {skipped}", parent=parent)
