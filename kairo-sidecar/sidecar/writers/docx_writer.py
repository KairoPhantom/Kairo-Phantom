import os
import shutil
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Any

from docx import Document

log = logging.getLogger("kairo-sidecar.docx_writer")

def write_docx(file_path: str, operations: List[Dict[str, Any]]) -> dict:
    """
    Applies a list of Pydantic-validated DocxOperations to a .docx file using python-docx.
    Performs atomic writes, backups, and graceful Word file lock handling.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"Document not found: {path}"}

    # 1. Create a Backup
    backup_path = path.with_suffix(path.suffix + ".kairo_backup")
    try:
        shutil.copy2(path, backup_path)
    except Exception as e:
        return {"error": f"Failed to create backup of document: {e}"}

    applied = []
    errors = []

    try:
        doc = Document(str(path))
        
        for op in operations:
            op_type = op.get("type", "")
            try:
                if op_type == "insert_paragraph":
                    _op_insert_paragraph(doc, op)
                    applied.append(op)
                elif op_type == "replace_paragraph":
                    _op_replace_paragraph(doc, op)
                    applied.append(op)
                elif op_type == "insert_table":
                    _op_insert_table(doc, op)
                    applied.append(op)
                elif op_type == "delete_paragraph":
                    _op_delete_paragraph(doc, op)
                    applied.append(op)
                else:
                    errors.append(f"Unknown operation type: {op_type}")
            except Exception as e:
                errors.append(f"Operation {op_type} failed: {e}")
                log.error(f"Operation error: {e}\n{traceback.format_exc()}")

        # 2. Atomic Save using a temp file
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        doc.save(str(tmp_path))
        
        try:
            os.replace(str(tmp_path), str(path))
        except PermissionError:
            # Word has the file open and locked
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "error": "Word has this file open. Save and close the document first, then press Alt+M again.",
                "path": str(path),
            }

        # 3. Clean up backup on complete success
        if not errors:
            try:
                backup_path.unlink(missing_ok=True)
            except Exception:
                pass

        return {
            "applied_count": len(applied),
            "errors": errors,
            "path": str(path),
        }

    except Exception as e:
        log.error(f"Failed to write docx: {e}\n{traceback.format_exc()}")
        return {"error": f"Failed to write document: {e}", "traceback": traceback.format_exc()}


def _add_runs_to_paragraph(para, runs_data: List[Dict[str, Any]]):
    """Adds styled runs to an existing paragraph element."""
    for run_item in runs_data:
        text = run_item.get("text", "")
        if text:
            run = para.add_run(text)
            run.bold = run_item.get("bold", False)
            run.italic = run_item.get("italic", False)


def _make_paragraph(doc, style: str, runs_data: List[Dict[str, Any]]):
    """Creates a new paragraph with styled runs, not yet added to document body."""
    para = doc.add_paragraph()
    try:
        para.style = doc.styles[style]
    except Exception:
        # Fallback to standard word built-in style if doc doesn't have it
        log.warning(f"Style '{style}' not found in document, falling back to Normal")
        try:
            para.style = doc.styles["Normal"]
        except Exception:
            pass
    _add_runs_to_paragraph(para, runs_data)
    # Remove from doc body so we can place it precisely
    para._element.getparent().remove(para._element)
    return para


def _op_insert_paragraph(doc, op: Dict[str, Any]):
    """Inserts a styled paragraph after a specific index."""
    after_idx = op.get("after_paragraph_index", -1)
    style = op.get("style", "Normal")
    runs_data = op.get("runs", [])

    if after_idx < 0 or after_idx >= len(doc.paragraphs):
        # Append to end of document
        para = doc.add_paragraph()
        try:
            para.style = doc.styles[style]
        except Exception:
            pass
        _add_runs_to_paragraph(para, runs_data)
    else:
        ref_para = doc.paragraphs[after_idx]
        new_para = _make_paragraph(doc, style, runs_data)
        ref_para._element.addnext(new_para._element)


def _op_replace_paragraph(doc, op: Dict[str, Any]):
    """Replaces text and style of a paragraph at specific index."""
    idx = op.get("paragraph_index", -1)
    style = op.get("style", "Normal")
    runs_data = op.get("runs", [])

    if 0 <= idx < len(doc.paragraphs):
        para = doc.paragraphs[idx]
        # Clear existing text safely
        for run in para.runs:
            run.text = ""
        # Apply style if found
        try:
            para.style = doc.styles[style]
        except Exception:
            pass
        _add_runs_to_paragraph(para, runs_data)


def _op_insert_table(doc, op: Dict[str, Any]):
    """Inserts a table after a specific paragraph index."""
    after_idx = op.get("after_paragraph_index", -1)
    headers = op.get("headers", [])
    rows_data = op.get("rows", [])

    # Let's count columns
    cols = len(headers) if headers else (max(len(r) for r in rows_data) if rows_data else 0)
    if cols == 0:
        return

    # Create table in document first (python-docx appends to end of body element)
    table = doc.add_table(rows=0, cols=cols)
    table.style = "Table Grid"

    # Add header
    if headers:
        row = table.add_row()
        for i, h in enumerate(headers):
            row.cells[i].text = str(h)

    # Add rows
    for r in rows_data:
        row = table.add_row()
        for i, cell_text in enumerate(r):
            if i < cols:
                row.cells[i].text = str(cell_text)

    # Move table immediately after after_idx paragraph
    if 0 <= after_idx < len(doc.paragraphs):
        ref_para = doc.paragraphs[after_idx]
        ref_para._element.addnext(table._element)


def _op_delete_paragraph(doc, op: Dict[str, Any]):
    """Deletes a paragraph at specific index."""
    idx = op.get("paragraph_index", -1)
    if 0 <= idx < len(doc.paragraphs):
        para = doc.paragraphs[idx]
        para._element.getparent().remove(para._element)
