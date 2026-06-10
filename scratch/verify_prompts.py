import os
import sys
import re

# Add kairo-sidecar directory to path to make imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kairo-sidecar")))

from sidecar.prompt_builder import (
    build_word_prompt,
    build_excel_prompt,
    build_powerpoint_prompt
)

def check_unreplaced_vars(prompt: str, name: str) -> bool:
    # Look for placeholders like {variable} or {context.variable} or {something}
    # But exclude JSON blocks (like those starting with double-braces or standard JSON syntax).
    # We search for any { followed by word characters and dots, ending with }
    pattern = r"\{([a-zA-Z_][a-zA-Z0-9_\.]*)\}"
    matches = re.findall(pattern, prompt)
    
    # We want to ignore any valid JSON constructs or schema details if they matched (though they usually won't match if they don't have just a variable name inside braces)
    # Actually, we should check if there are any templates left.
    if matches:
        print(f"[-] {name} prompt has potential unreplaced variables: {matches}")
        return False
    else:
        print(f"[+] {name} prompt verified: zero unreplaced variables.")
        return True

# Scenario W-01: Word
user_prompt_w = "write a professional email about quarterly results"
doc_ctx_w = {
    "styles": {"paragraph": ["Normal", "Heading 1", "Heading 2", "List Bullet", "List Number"]},
    "paragraphs": [
        {"index": 0, "text": "// write a professional email about quarterly results", "style": "Normal"}
    ],
    "tables": [],
    "theme_fonts": {"major": "Arial", "minor": "Calibri"},
    "list_sequences": [],
    "document_purpose": "business_memo",
    "cursor_paragraph_index": 0,
    "total_paragraphs": 1
}
mem_ctx_w = "Use a polite, concise professional tone."

# Scenario E-01: Excel
user_prompt_e = "write a SUMIF formula for cells A1:A10 where value > 100"
doc_ctx_e = {
    "active_cell": "B1",
    "active_sheet": "Sheet1",
    "sheet_names": ["Sheet1"],
    "grid": [
        [{"ref": f"A{i}", "value": str(i * 20), "formula": "", "is_active": False} for i in range(1, 11)]
    ],
    "headers": ["Values"],
    "named_ranges": [],
    "column_types": {"A": "Number"},
    "locale": "en",
    "cells": [{"address": f"A{i}", "value": str(i * 20), "formula": ""} for i in range(1, 11)]
}
mem_ctx_e = "Prefer uppercase for formula names."

# Scenario P-01: PowerPoint
user_prompt_p = "write 4 bullet points about digital transformation benefits"
doc_ctx_p = {
    "slide_index": 0,
    "total_slides": 1,
    "layout_name": "Title and Content",
    "major_font": "Segoe UI Light",
    "minor_font": "Segoe UI",
    "shapes_json": "[]",
    "deck_purpose": "sales_deck",
    "file_path": "Unknown"
}
mem_ctx_p = "Keep bullet points highly concise."

print("==================== ASSEMBLING W-01 PROMPT ====================")
w_prompt = build_word_prompt(user_prompt_w, doc_ctx_w, mem_ctx_w)
print(w_prompt[:800])
print("... [TRUNCATED] ...")
print(w_prompt[-400:])

print("\n==================== ASSEMBLING E-01 PROMPT ====================")
e_prompt = build_excel_prompt(user_prompt_e, doc_ctx_e, mem_ctx_e)
print(e_prompt[:800])
print("... [TRUNCATED] ...")
print(e_prompt[-400:])

print("\n==================== ASSEMBLING P-01 PROMPT ====================")
p_prompt = build_powerpoint_prompt(user_prompt_p, doc_ctx_p, mem_ctx_p)
print(p_prompt[:800])
print("... [TRUNCATED] ...")
print(p_prompt[-400:])

print("\n==================== VERIFICATION RESULTS ====================")
w_ok = check_unreplaced_vars(w_prompt, "W-01 (Word)")
e_ok = check_unreplaced_vars(e_prompt, "E-01 (Excel)")
p_ok = check_unreplaced_vars(p_prompt, "P-01 (PowerPoint)")

if w_ok and e_ok and p_ok:
    print("\nSUCCESS: All prompts verified successfully!")
    sys.exit(0)
else:
    print("\nFAILURE: One or more prompts failed verification.")
    sys.exit(1)
