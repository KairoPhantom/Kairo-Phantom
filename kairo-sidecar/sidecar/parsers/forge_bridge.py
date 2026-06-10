"""
Forge Validator — Pure-Python deterministic Excel formula validation for Kairo Phantom.
======================================================================================
Ensures formula correctness and handles auto-correction of common LLM mistakes before
cell injection.
"""

from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger("kairo-sidecar.forge_bridge")

class ForgeValidator:
    """
    Deterministic Excel formula validator.
    Catches 7 real-world LLM mistakes:
      1. Missing closing parentheses
      2. Missing VLOOKUP / HLOOKUP arguments
      3. Semicolons instead of commas
      4. Missing '=' prefix
      5. Invalid cell references (e.g. Row 0, invalid column letters)
      6. Wrong argument counts for common functions
      7. Circular references (same cell in formula and target)
    """

    KNOWN_FUNCTIONS: dict[str, tuple[int, int]] = {
        # function_name: (min_args, max_args)
        "SUM": (1, 255),
        "AVERAGE": (1, 255),
        "COUNT": (1, 255),
        "COUNTA": (1, 255),
        "COUNTIF": (2, 2),
        "COUNTIFS": (2, 254), # must be pairs, so even number of args
        "VLOOKUP": (3, 4),
        "HLOOKUP": (3, 4),
        "INDEX": (2, 4),
        "MATCH": (2, 3),
        "IF": (2, 3),
        "IFS": (2, 254),
        "IFERROR": (2, 2),
        "IFNA": (2, 2),
        "SUMIF": (2, 3),
        "SUMIFS": (3, 255),
        "AVERAGEIF": (2, 3),
        "AVERAGEIFS": (3, 255),
        "LEFT": (1, 2),
        "RIGHT": (1, 2),
        "MID": (3, 3),
        "LEN": (1, 1),
        "TRIM": (1, 1),
        "UPPER": (1, 1),
        "LOWER": (1, 1),
        "PROPER": (1, 1),
        "TEXT": (2, 2),
        "VALUE": (1, 1),
        "DATE": (3, 3),
        "TODAY": (0, 0),
        "NOW": (0, 0),
        "YEAR": (1, 1),
        "MONTH": (1, 1),
        "DAY": (1, 1),
        "ROUND": (2, 2),
        "ROUNDUP": (2, 2),
        "ROUNDDOWN": (2, 2),
        "INT": (1, 1),
        "ABS": (1, 1),
        "MOD": (2, 2),
        "CONCATENATE": (1, 255),
        "CONCAT": (1, 255),
        "TEXTJOIN": (3, 255),
        "OFFSET": (3, 5),
        "INDIRECT": (1, 2),
        "ADDRESS": (2, 5),
        "SUBTOTAL": (2, 255),
        "AGGREGATE": (3, 255),
        "POWER": (2, 2),
        "SQRT": (1, 1),
        "LOG": (1, 2),
        "EXP": (1, 1),
    }

    def _fix_single_quotes(self, formula: str) -> str:
        if "'" not in formula:
            return formula
        i = 0
        in_single_quote = False
        quote_start = -1
        while i < len(formula):
            char = formula[i]
            if char == "'":
                if not in_single_quote:
                    in_single_quote = True
                    quote_start = i
                else:
                    is_sheet = False
                    j = i + 1
                    while j < len(formula) and formula[j].isspace():
                        j += 1
                    if j < len(formula) and formula[j] == '!':
                        is_sheet = True
                    
                    if is_sheet:
                        in_single_quote = False
                    else:
                        formula = formula[:quote_start] + '"' + formula[quote_start+1:i] + '"' + formula[i+1:]
                        return self._fix_single_quotes(formula)
            i += 1
        return formula

    def validate(self, formula: str, context: dict | None = None) -> dict:
        """
        Validate formula and return full details.
        """
        if not formula:
            return {
                "valid": False,
                "corrected": "",
                "error": "Formula is empty or None",
                "fix_applied": None,
                "confidence": 0.0,
                "explanation": "",
            }

        # Convert single quotes to double quotes for text literals
        formula = self._fix_single_quotes(formula)

        # 1. Missing '=' prefix check & correction
        formula_stripped = formula.strip()
        has_equals = formula_stripped.startswith("=")
        working_formula = formula_stripped if has_equals else f"={formula_stripped}"

        # 2. Semicolons instead of commas correction
        # Replace semicolons with commas, but avoid replacing within quotes.
        # Simple heuristic: if we have semicolons outside quotes, replace them.
        semicolon_fix = False
        if ";" in working_formula:
            parts = working_formula.split('"')
            for i in range(len(parts)):
                if i % 2 == 0:  # outside quotes
                    if ";" in parts[i]:
                        parts[i] = parts[i].replace(";", ",")
                        semicolon_fix = True
            working_formula = '"'.join(parts)

        # 3. Missing closing parenthesis check & correction
        paren_fix = False
        open_count = working_formula.count("(")
        close_count = working_formula.count(")")
        if open_count > close_count:
            working_formula = working_formula + ")" * (open_count - close_count)
            paren_fix = True

        # 4. Check for invalid cell references (like row 0 or too large/small)
        # Match references like A0, B0, Z0, etc.
        invalid_ref_found = False
        ref_pattern = r"\b([A-Za-z]+)(\d+)\b"
        for col_str, row_str in re.findall(ref_pattern, working_formula):
            row_val = int(row_str)
            if row_val <= 0:
                invalid_ref_found = True
                break

        # 5. Extract function calls and validate args
        # Tokenize formula and inspect function args (simplified parser)
        arg_errors = []
        # Find matches of FUNCTION_NAME(
        fn_pattern = r"\b([A-Z_]+)\("
        for fn_name in re.findall(fn_pattern, working_formula.upper()):
            if fn_name in self.KNOWN_FUNCTIONS:
                min_args, max_args = self.KNOWN_FUNCTIONS[fn_name]
                # Try to extract the arguments string for this function
                # E.g., for VLOOKUP(A1, B:C), we find the matching closing paren.
                start_idx = working_formula.upper().find(f"{fn_name}(")
                if start_idx != -1:
                    args_start = start_idx + len(fn_name) + 1
                    depth = 1
                    args_end = args_start
                    while args_end < len(working_formula) and depth > 0:
                        char = working_formula[args_end]
                        if char == "(":
                            depth += 1
                        elif char == ")":
                            depth -= 1
                        args_end += 1
                    args_str = working_formula[args_start:args_end - 1]
                    # Split args by commas outside parens and quotes
                    args_list = []
                    current_arg = []
                    in_quotes = False
                    p_depth = 0
                    for char in args_str:
                        if char == '"':
                            in_quotes = not in_quotes
                        elif char == "(" and not in_quotes:
                            p_depth += 1
                        elif char == ")" and not in_quotes:
                            p_depth -= 1
                        
                        if char == "," and not in_quotes and p_depth == 0:
                            args_list.append("".join(current_arg).strip())
                            current_arg = []
                        else:
                            current_arg.append(char)
                    if current_arg:
                        args_list.append("".join(current_arg).strip())

                    # Filter out empty arguments (e.g. if the function is TODAY())
                    args_list = [a for a in args_list if a]
                    num_args = len(args_list)

                    if num_args < min_args or num_args > max_args:
                        arg_errors.append(f"Function {fn_name} expected {min_args}-{max_args} arguments, but got {num_args}")

        # VLOOKUP specific auto-correction for missing arguments
        vlookup_fix = False
        if "VLOOKUP(" in working_formula.upper():
            # If VLOOKUP only has 2 args (e.g. VLOOKUP(A1, B:C)), append default column index 2 and FALSE
            # Let's count args inside VLOOKUP
            vlookup_match = re.search(r"VLOOKUP\(([^)]+)\)", working_formula, re.IGNORECASE)
            if vlookup_match:
                v_args = [a.strip() for a in vlookup_match.group(1).split(",")]
                if len(v_args) == 2:
                    working_formula = working_formula.replace(vlookup_match.group(0), f"VLOOKUP({v_args[0]},{v_args[1]},2,FALSE)")
                    vlookup_fix = True

        # Determine if valid
        error_msg = None
        valid = True
        fix_desc = []

        if invalid_ref_found:
            valid = False
            error_msg = "Invalid cell reference (e.g., row 0) found in formula"
        elif arg_errors:
            valid = False
            error_msg = arg_errors[0]

        # Gather fix descriptions
        if not has_equals:
            fix_desc.append("Added '=' prefix")
        if semicolon_fix:
            fix_desc.append("Replaced semicolons with commas")
        if paren_fix:
            fix_desc.append("Closed missing parentheses")
        if vlookup_fix:
            fix_desc.append("Appended default VLOOKUP parameters")

        # Circular reference check
        if context and "active_cell" in context:
            active = context["active_cell"].upper()
            if active in working_formula.upper():
                valid = False
                error_msg = f"Circular reference detected: target cell {active} referenced inside formula"

        corrected_formula = working_formula if not valid or fix_desc else formula_stripped

        # If we successfully corrected the formula to a valid state, mark it as valid!
        # E.g. SUM(A1:A10 -> corrected to =SUM(A1:A10) which has no errors now.
        if error_msg and fix_desc:
            # Re-run validation on corrected formula
            sub_val = self.validate(corrected_formula, context)
            if sub_val["valid"]:
                valid = True
                error_msg = None

        return {
            "valid": valid,
            "corrected": corrected_formula,
            "error": error_msg,
            "fix_applied": ", ".join(fix_desc) if fix_desc else None,
            "confidence": 1.0 if valid else 0.5,
            "explanation": self.explain(corrected_formula),
        }

    def auto_correct(self, formula: str) -> tuple[str, str | None]:
        """Returns (corrected_formula, fix_description | None)"""
        res = self.validate(formula)
        return res["corrected"], res["fix_applied"]

    def explain(self, formula: str) -> str:
        """Plain-language explanation of what the formula does."""
        if not formula:
            return ""
        
        formula_upper = formula.upper()
        if "SUM(" in formula_upper:
            # extract SUM range
            m = re.search(r"SUM\(([^)]+)\)", formula_upper)
            r = m.group(1) if m else "cells"
            return f"Sums all values in cells {r}"
        
        if "VLOOKUP(" in formula_upper:
            m = re.search(r"VLOOKUP\(([^,)]+),([^,)]+),?([^,)]*)?,?([^,)]*)?\)", formula_upper)
            if m:
                lookup_val = m.group(1).strip()
                table_arr = m.group(2).strip()
                col_idx = m.group(3).strip() or "2"
                exact = "exact match" if "FALSE" in m.group(4) or "0" in m.group(4) else "approximate match"
                return f"Looks up the value in {lookup_val} in column 1 of {table_arr}, returns column {col_idx} of the matching row ({exact})"
            return "Performs a vertical lookup on a table range"

        if "IF(" in formula_upper:
            m = re.search(r"IF\(([^,]+),([^,]+),?([^)]*)?\)", formula_upper)
            if m:
                cond = m.group(1).strip()
                true_val = m.group(2).strip()
                false_val = m.group(3).strip() or "empty"
                return f"Returns {true_val} if {cond} is true, otherwise returns {false_val}"
            return "Performs conditional IF logic"

        if "SUMIFS(" in formula_upper:
            m = re.search(r"SUMIFS\(([^,]+),([^)]+)\)", formula_upper)
            if m:
                sum_rng = m.group(1).strip()
                criteria = m.group(2).strip()
                return f"Sums values in {sum_rng} matching criteria: {criteria}"
            return "Sums cells that meet multiple criteria"

        return f"Calculates standard Excel formula: {formula}"

    def validate_batch(self, formulas: list[str], context: dict | None = None) -> list[dict]:
        """Validate a list of formulas, return results in order."""
        return [self.validate(f, context) for f in formulas]


# ──────────────────────────────────────────────────────────────────────────────
# Standalone functions used by dispatcher
# ──────────────────────────────────────────────────────────────────────────────

def validate_formula(formula: str, context: dict | None = None) -> dict:
    v = ForgeValidator()
    return v.validate(formula, context)

def explain_formula(formula: str) -> str:
    v = ForgeValidator()
    return v.explain(formula)

def validate_formula_batch(formulas: list[str]) -> list[dict]:
    v = ForgeValidator()
    return v.validate_batch(formulas)
