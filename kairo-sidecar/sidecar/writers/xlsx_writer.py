import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any

log = logging.getLogger("kairo-sidecar.xlsx_writer")

def write_xlsx(file_path: str, operations: List[Dict[str, Any]]) -> dict:
    """
    Apply ExcelOperation list to .xlsx file atomically.
    """
    try:
        import openpyxl
    except ImportError:
        return {"error": "openpyxl not installed — run: pip install openpyxl"}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    # Backup original
    backup_path = path.with_suffix(path.suffix + ".kairo_backup")
    try:
        shutil.copy2(path, backup_path)
    except Exception as e:
        return {"error": f"Failed to create backup of spreadsheet: {e}"}

    applied = []
    errors = []

    try:
        wb = openpyxl.load_workbook(str(path))
        ws = wb.active

        for op in operations:
            try:
                cell_ref = op.get("cell", "A1")
                value = op.get("value", "")
                formula = op.get("formula", "")
                write_val = formula if formula else value
                ws[cell_ref] = write_val
                applied.append({"cell": cell_ref, "written": write_val})
            except Exception as e:
                errors.append(f"Excel write error {op}: {e}")

        tmp_path = path.with_suffix(path.suffix + ".tmp")
        wb.save(str(tmp_path))
        
        try:
            os.replace(str(tmp_path), str(path))
        except PermissionError:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "error": "Excel has this file open. Save and close the workbook first, then press Alt+M again.",
                "path": str(path),
            }
            
        if not errors:
            try:
                backup_path.unlink(missing_ok=True)
            except Exception:
                pass

        return {"applied_count": len(applied), "cells": applied, "errors": errors}
    except Exception as e:
        log.error(f"Failed to write Excel file {file_path}: {e}")
        return {"error": f"Failed to write Excel: {e}"}
