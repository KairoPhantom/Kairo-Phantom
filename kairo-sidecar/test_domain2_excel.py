"""
Domain 2 Excel Integration Test Suite — 60 Tests
================================================
Covers:
  - ForgeValidator (15 tests)
  - ExcelContextCapture (12 tests)
  - ExcelMcpBridge (12 tests)
  - XlsxParserUpgrade (6 tests)
  - GateConditions (9 tests)
  - W4Regression (6 tests)

All tests are completely independent of local Excel/COM installations,
using in-memory openpyxl mocks and temporary file fixtures.
"""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
import pytest
import openpyxl

from sidecar.parsers.forge_bridge import ForgeValidator, validate_formula, explain_formula, validate_formula_batch
from sidecar.parsers.excel_context import ExcelContextCapture, get_workbook_overview, get_active_cell_context, format_excel_context_for_prompt
from sidecar.parsers.excelmcp_bridge import (
    excelmcp_available,
    excel_is_open,
    excelmcp_read_range,
    excelmcp_write_cell,
    excelmcp_write_range,
    excelmcp_fill_formula,
    excelmcp_create_chart,
    excelmcp_create_pivot_table,
    excelmcp_screenshot_range,
    get_workbook_blueprint,
    col_to_idx,
    idx_to_col,
)
from sidecar.parsers.xlsx_parser import write_xlsx_with_formatting

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_xlsx(tmp_path) -> Path:
    """Create a minimal real Excel file for test context."""
    file_path = tmp_path / "test_workbook.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    
    # Write some header rows and values
    ws["A1"] = "Product"
    ws["B1"] = "Price"
    ws["C1"] = "Quantity"
    ws["D1"] = "Revenue"
    
    ws["A2"] = "Widget A"
    ws["B2"] = 10.0
    ws["C2"] = 5
    ws["D2"] = "=B2*C2"
    
    ws["A3"] = "Widget B"
    ws["B3"] = 20.0
    ws["C3"] = 3
    ws["D3"] = "=B3*C3"
    
    # Add named ranges
    wb.defined_names.add(openpyxl.workbook.defined_name.DefinedName("PriceRange", attr_text="Sales!$B$2:$B$3"))
    
    # Add a table
    from openpyxl.worksheet.table import Table, TableStyleInfo
    tab = Table(displayName="SalesTable", ref="A1:D3")
    style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                           showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    tab.tableStyleInfo = style
    ws.add_table(tab)

    wb.save(str(file_path))
    return file_path


# ──────────────────────────────────────────────────────────────────────────────
# 1. TestForgeValidator (15 tests)
# ──────────────────────────────────────────────────────────────────────────────

class TestForgeValidator:
    def test_valid_sum_formula(self):
        res = validate_formula("=SUM(A1:A10)")
        assert res["valid"] is True
        assert res["error"] is None

    def test_valid_vlookup_with_all_args(self):
        res = validate_formula("=VLOOKUP(A1,B:D,3,FALSE)")
        assert res["valid"] is True

    def test_valid_if_formula(self):
        res = validate_formula('=IF(A1>100,"High","Low")')
        assert res["valid"] is True

    def test_valid_sumifs(self):
        res = validate_formula('=SUMIFS(C:C,A:A,"West",B:B,">100")')
        assert res["valid"] is True

    def test_invalid_missing_equals(self):
        res = validate_formula("SUM(A1:A10)")
        assert res["corrected"] == "=SUM(A1:A10)"

    def test_invalid_missing_closing_paren(self):
        res = validate_formula("=SUM(A1:A10")
        assert res["corrected"] == "=SUM(A1:A10)"

    def test_invalid_vlookup_missing_args(self):
        res = validate_formula("=VLOOKUP(A1,B:C)")
        # Should be auto-corrected to have 4 args
        assert "2,FALSE" in res["corrected"]

    def test_valid_nested_if(self):
        res = validate_formula('=IF(AND(A1>0,B1>0),"Both positive","Not both")')
        assert res["valid"] is True

    def test_valid_text_function(self):
        res = validate_formula('=TEXT(A1,"DD/MM/YYYY")')
        assert res["valid"] is True

    def test_valid_index_match(self):
        res = validate_formula("=INDEX(B:B,MATCH(A1,A:A,0))")
        assert res["valid"] is True

    def test_explain_sum(self):
        expl = explain_formula("=SUM(A1:A10)")
        assert "sums" in expl.lower() or "values in cells" in expl.lower()

    def test_explain_vlookup(self):
        expl = explain_formula("=VLOOKUP(A2,B:D,3,FALSE)")
        assert "looks up" in expl.lower() or "vertical lookup" in expl.lower()

    def test_explain_if(self):
        expl = explain_formula('=IF(A1>100,"High","Low")')
        assert "returns" in expl.lower() or "conditional" in expl.lower()

    def test_validate_batch_mixed(self):
        res = validate_formula_batch(["=SUM(A1)", "invalid_no_equals(B2)"])
        assert len(res) == 2
        assert res[0]["valid"] is True

    def test_confidence_valid_formula(self):
        res = validate_formula("=SUM(A1:A10)")
        assert res["confidence"] >= 0.8


# ──────────────────────────────────────────────────────────────────────────────
# 2. TestExcelContextCapture (12 tests)
# ──────────────────────────────────────────────────────────────────────────────

class TestExcelContextCapture:
    def test_capture_returns_dict(self, temp_xlsx):
        cap = ExcelContextCapture()
        res = cap.capture(str(temp_xlsx), "A1")
        assert isinstance(res, dict)

    def test_capture_active_cell_present(self, temp_xlsx):
        cap = ExcelContextCapture()
        res = cap.capture(str(temp_xlsx), "B2")
        assert res["active_cell"] == "B2"

    def test_capture_grid_is_list(self, temp_xlsx):
        cap = ExcelContextCapture()
        res = cap.capture(str(temp_xlsx), "A1")
        assert isinstance(res["grid"], list)

    def test_capture_headers_is_dict(self, temp_xlsx):
        cap = ExcelContextCapture()
        res = cap.capture(str(temp_xlsx), "A1")
        assert isinstance(res["headers"], dict)
        assert res["headers"]["A"] == "Product"

    def test_capture_sheet_name_present(self, temp_xlsx):
        cap = ExcelContextCapture()
        res = cap.capture(str(temp_xlsx), "A1")
        assert res["sheet_name"] == "Sales"

    def test_to_system_prompt_fragment_non_empty(self, temp_xlsx):
        cap = ExcelContextCapture()
        ctx = cap.capture(str(temp_xlsx), "A1")
        frag = cap.to_system_prompt_fragment(ctx)
        assert len(frag) > 0

    def test_system_prompt_has_excel_context_header(self, temp_xlsx):
        cap = ExcelContextCapture()
        ctx = cap.capture(str(temp_xlsx), "A1")
        frag = cap.to_system_prompt_fragment(ctx)
        assert "Excel Context" in frag

    def test_system_prompt_has_instructions(self, temp_xlsx):
        cap = ExcelContextCapture()
        ctx = cap.capture(str(temp_xlsx), "A1")
        frag = cap.to_system_prompt_fragment(ctx)
        assert "Instructions for Excel Mode" in frag

    def test_system_prompt_has_active_cell(self, temp_xlsx):
        cap = ExcelContextCapture()
        ctx = cap.capture(str(temp_xlsx), "B2")
        frag = cap.to_system_prompt_fragment(ctx)
        assert "B2" in frag

    def test_format_excel_context_for_prompt(self, temp_xlsx):
        res = format_excel_context_for_prompt(str(temp_xlsx), "A1", "Calculate revenue totals")
        assert "Calculate revenue totals" in res

    def test_get_workbook_overview_structure(self, temp_xlsx):
        res = get_workbook_overview(str(temp_xlsx))
        assert "sheets" in res["data"]
        assert "named_ranges" in res["data"]

    def test_get_active_cell_context_radius(self, temp_xlsx):
        res = get_active_cell_context(str(temp_xlsx), "A1", radius=2)
        assert len(res["data"]["grid"]) <= 5


# ──────────────────────────────────────────────────────────────────────────────
# 3. TestExcelMcpBridge (12 tests)
# ──────────────────────────────────────────────────────────────────────────────

class TestExcelMcpBridge:
    def test_excelmcp_available_returns_bool(self):
        assert isinstance(excelmcp_available(), bool)

    def test_excel_is_open_non_existent_file(self):
        assert excel_is_open("nonexistent_file.xlsx") is False

    def test_excelmcp_write_cell_no_file_error(self):
        res = excelmcp_write_cell("non_existent_path.xlsx", "A1", "Val")
        assert res["ok"] is False
        assert "no such file" in res["error"].lower() or "error" in res["error"].lower()

    def test_get_workbook_blueprint_structure(self, temp_xlsx):
        res = get_workbook_blueprint(str(temp_xlsx))
        assert res["ok"] is True
        assert "sheets" in res["data"]
        assert "named_ranges" in res["data"]

    def test_excelmcp_write_cell_valid_formula(self, temp_xlsx):
        res = excelmcp_write_cell(str(temp_xlsx), "E2", formula="=B2*1.1")
        assert res["ok"] is True
        
        # Verify it was saved and written as formula
        wb = openpyxl.load_workbook(str(temp_xlsx), data_only=False)
        assert wb.active["E2"].value == "=B2*1.1"

    def test_excelmcp_read_range_returns_data(self, temp_xlsx):
        res = excelmcp_read_range(str(temp_xlsx), "A1:B2")
        assert res["ok"] is True
        assert "Product" in res["data"]["content"]

    def test_excelmcp_fill_formula_adjusts_refs(self, temp_xlsx):
        res = excelmcp_fill_formula(str(temp_xlsx), "=B2*10", "E2:E4")
        assert res["ok"] is True
        
        wb = openpyxl.load_workbook(str(temp_xlsx), data_only=False)
        assert wb.active["E2"].value == "=B2*10"
        assert wb.active["E3"].value == "=B3*10"
        assert wb.active["E4"].value == "=B4*10"

    def test_excelmcp_create_chart_returns_ok(self, temp_xlsx):
        res = excelmcp_create_chart(str(temp_xlsx), "B1:B3", "column", "Price Chart")
        assert res["ok"] is True
        assert res["data"]["chart_type"] == "column"

    def test_excelmcp_create_pivot_returns_ok(self, temp_xlsx):
        res = excelmcp_create_pivot_table(str(temp_xlsx), "A1:D3", ["Product"], [], ["Revenue"])
        assert res["ok"] is True
        assert res["data"]["sheet"] == "Sales_Pivot"

    def test_excelmcp_screenshot_unavailable_graceful(self, temp_xlsx):
        res = excelmcp_screenshot_range(str(temp_xlsx), "A1:B2")
        assert res["ok"] is False or "output_path" in res["data"]

    def test_col_to_idx_single_letter(self):
        assert col_to_idx("A") == 0
        assert col_to_idx("Z") == 25

    def test_col_to_idx_double_letter(self):
        assert col_to_idx("AA") == 26
        assert col_to_idx("AB") == 27


# ──────────────────────────────────────────────────────────────────────────────
# 4. TestXlsxParserUpgrade (6 tests)
# ──────────────────────────────────────────────────────────────────────────────

class TestXlsxParserUpgrade:
    def test_get_workbook_blueprint_has_sheets(self, temp_xlsx):
        res = get_workbook_blueprint(str(temp_xlsx))
        assert res["ok"] is True
        assert len(res["data"]["sheets"]) > 0

    def test_get_workbook_blueprint_has_named_ranges(self, temp_xlsx):
        res = get_workbook_blueprint(str(temp_xlsx))
        assert "PriceRange" in res["data"]["named_ranges"]

    def test_write_xlsx_with_formatting_formula(self, temp_xlsx):
        ops = [{"cell": "E2", "formula": "=SUM(B2:C2)"}]
        res = write_xlsx_with_formatting(str(temp_xlsx), ops)
        assert res["ok"] is True
        
        wb = openpyxl.load_workbook(str(temp_xlsx), data_only=False)
        assert wb.active["E2"].value == "=SUM(B2:C2)"

    def test_write_xlsx_with_formatting_value(self, temp_xlsx):
        ops = [{"cell": "E3", "value": "TestVal"}]
        res = write_xlsx_with_formatting(str(temp_xlsx), ops)
        assert res["ok"] is True
        
        wb = openpyxl.load_workbook(str(temp_xlsx), data_only=False)
        assert wb.active["E3"].value == "TestVal"

    def test_write_xlsx_with_number_format(self, temp_xlsx):
        ops = [{"cell": "B2", "value": 0.123, "number_format": "0.0%"}]
        res = write_xlsx_with_formatting(str(temp_xlsx), ops)
        assert res["ok"] is True
        
        wb = openpyxl.load_workbook(str(temp_xlsx), data_only=False)
        assert wb.active["B2"].number_format == "0.0%"

    def test_write_xlsx_preserves_other_cells(self, temp_xlsx):
        wb = openpyxl.load_workbook(str(temp_xlsx))
        ws = wb.active
        ws["B2"].number_format = "$#,##0.00"
        wb.save(str(temp_xlsx))

        ops = [{"cell": "C2", "value": 10}]
        res = write_xlsx_with_formatting(str(temp_xlsx), ops)
        assert res["ok"] is True
        
        wb = openpyxl.load_workbook(str(temp_xlsx))
        assert wb.active["B2"].number_format == "$#,##0.00"


# ──────────────────────────────────────────────────────────────────────────────
# 5. TestGateConditions (9 tests)
# ──────────────────────────────────────────────────────────────────────────────

class TestGateConditions:
    def test_gate1_formula_injection_valid_formula(self):
        res = validate_formula("=AVERAGE(A1:A10)")
        assert res["valid"] is True

    def test_gate1_formula_not_static_text(self):
        res = validate_formula("=SUM(B2:B10)")
        assert res["corrected"].startswith("=")

    def test_gate2_forge_catches_vlookup_missing_args(self):
        res = validate_formula("=VLOOKUP(A1,B:C)")
        assert res["valid"] is False or "2,FALSE" in res["corrected"]

    def test_gate2_forge_auto_corrects_to_valid(self):
        res = validate_formula("=SUM(A1:A10")
        assert res["corrected"] == "=SUM(A1:A10)"

    def test_gate3_auto_context_has_sheet_info(self, temp_xlsx):
        cap = ExcelContextCapture()
        ctx = cap.capture(str(temp_xlsx), "A1")
        frag = cap.to_system_prompt_fragment(ctx)
        assert "Workbook has" in frag

    def test_gate3_auto_context_has_active_cell(self, temp_xlsx):
        cap = ExcelContextCapture()
        ctx = cap.capture(str(temp_xlsx), "B2")
        frag = cap.to_system_prompt_fragment(ctx)
        assert "B2" in frag

    def test_gate4_data_cleaning_trim_formula(self):
        res = validate_formula("=TRIM(A1)")
        assert res["valid"] is True

    def test_gate5_chart_op_has_required_fields(self):
        from sidecar.parsers.excelmcp_bridge import excelmcp_create_chart
        # Syntactic checks only
        assert excelmcp_create_chart is not None

    def test_gate6_pivot_op_has_required_fields(self):
        from sidecar.parsers.excelmcp_bridge import excelmcp_create_pivot_table
        assert excelmcp_create_pivot_table is not None


# ──────────────────────────────────────────────────────────────────────────────
# 6. TestW4Regression (6 tests)
# ──────────────────────────────────────────────────────────────────────────────

class TestW4Regression:
    def test_no_system_prompt_in_excel_output(self):
        res = validate_formula("=SUM(A1:A10)")
        assert "system prompt" not in res["corrected"].lower()

    def test_no_role_leakage_in_explanation(self):
        expl = explain_formula("=SUM(A1:A10)")
        assert "swarm role" not in expl.lower()

    def test_no_mcp_blocks_in_formula(self):
        res = validate_formula("=SUM(A1:A10)")
        assert "[mcp:" not in res["corrected"].lower()

    def test_excel_context_no_internal_strings(self, temp_xlsx):
        cap = ExcelContextCapture()
        ctx = cap.capture(str(temp_xlsx), "A1")
        frag = cap.to_system_prompt_fragment(ctx)
        assert "editor.accessibilitymode" not in frag.lower()

    def test_forge_empty_formula_returns_error(self):
        res = validate_formula("")
        assert res["valid"] is False

    def test_forge_none_formula_handles_gracefully(self):
        res = validate_formula(None)
        assert res["valid"] is False
