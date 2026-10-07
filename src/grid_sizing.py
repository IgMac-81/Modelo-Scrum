import tkinter.font as tkfont


def fit_tree_columns(tree, font_root, columns, rows):
    data_font = tkfont.Font(font_root, family="Segoe UI", size=9)
    heading_font = tkfont.Font(font_root, family="Segoe UI", size=9, weight="bold")
    for column, heading, value_index, minimum_width in columns:
        heading_width = heading_font.measure(heading) + 28
        content_width = max(
            (data_font.measure(str(row[value_index] or "")) + 24 for row in rows),
            default=0,
        )
        tree.column(column, width=max(minimum_width, heading_width, content_width), stretch=False)