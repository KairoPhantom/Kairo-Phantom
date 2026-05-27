import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("kairo-sidecar.xlsx_parser")

def parse_xlsx(file_path: str, active_cell: Optional[str] = None) -> dict:
    """
    Read Excel file and return surrounding context grid and named ranges.
    """
    try:
        import openpyxl
        from openpyxl.utils import column_index_from_string, get_column_letter
    except ImportError:
        return {"error": "openpyxl not installed — run: pip install openpyxl"}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    try:
        wb = openpyxl.load_workbook(str(path), data_only=False)
        ws = wb.active

        # Parse active cell (e.g. "G5")
        if active_cell:
            col_str = ''.join(c for c in active_cell if c.isalpha())
            row = int(''.join(c for c in active_cell if c.isdigit()))
            col = column_index_from_string(col_str)
        else:
            row, col = 1, 1

        # Extract 10x10 window around active cell
        r_start = max(1, row - 5)
        r_end = min(ws.max_row, row + 5)
        c_start = max(1, col - 5)
        c_end = min(ws.max_column, col + 5)

        grid = []
        for r in range(r_start, r_end + 1):
            row_data = []
            for c in range(c_start, c_end + 1):
                cell = ws.cell(row=r, column=c)
                row_data.append({
                    "ref": f"{get_column_letter(c)}{r}",
                    "value": str(cell.value) if cell.value is not None else "",
                    "formula": str(cell.value) if str(cell.value).startswith("=") else "",
                    "is_active": (r == row and c == col),
                })
            grid.append(row_data)

        # Column headers (row 1)
        headers = {}
        for c in range(1, ws.max_column + 1):
            val = ws.cell(row=1, column=c).value
            if val:
                headers[get_column_letter(c)] = str(val)

        # Named ranges
        try:
            named_ranges = list(wb.defined_names.keys())
        except Exception:
            named_ranges = []

        return {
            "active_cell": active_cell or "A1",
            "active_row": row,
            "active_col": col,
            "sheet_name": ws.title,
            "sheet_names": wb.sheetnames,
            "grid": grid,
            "headers": headers,
            "named_ranges": named_ranges,
            "max_row": ws.max_row,
            "max_col": ws.max_column,
        }
    except Exception as e:
        log.error(f"Failed to parse Excel file {file_path}: {e}")
        return {"error": f"Failed to parse Excel: {e}"}


def get_workbook_blueprint(file_path: str) -> dict:
    """
    Get structural overview of an Excel workbook.
    """
    from sidecar.parsers.excelmcp_bridge import get_workbook_blueprint as get_bp
    res = get_bp(file_path)
    if res.get("ok"):
        return res["data"]
    return {"sheets": [], "named_ranges": [], "total_sheets": 0, "total_named_ranges": 0}


def write_xlsx_with_formatting(file_path: str, operations: list[dict]) -> dict:
    """
    Write Excel operations WITH formatting preservation.
    Each operation: {cell, formula?, value?, number_format?, bold?}
    """
    try:
        import openpyxl
        from openpyxl.styles import Font
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        wb = openpyxl.load_workbook(str(path), data_only=False)
        ws = wb.active

        written = 0
        for op in operations:
            cell_ref = op.get("cell")
            if not cell_ref:
                continue
            
            cell = ws[cell_ref]
            formula = op.get("formula")
            value = op.get("value")

            if formula:
                cell.value = formula if formula.startswith("=") else f"={formula}"
            elif value is not None and value != "":
                cell.value = value

            num_fmt = op.get("number_format")
            if num_fmt:
                cell.number_format = num_fmt

            if op.get("bold"):
                existing = cell.font
                cell.font = Font(
                    bold=True,
                    name=existing.name if existing else "Calibri",
                    size=existing.size if existing else 11,
                )
            written += 1

        wb.save(str(path))
        return {"ok": True, "cells_written": written}
    except Exception as e:
        log.error(f"Failed write_xlsx_with_formatting: {e}")
        return {"error": str(e)}

