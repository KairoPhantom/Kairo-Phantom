"""
scripts/eval_schema_compliance.py — Kairo Phantom Schema Compliance Evaluator
==============================================================================
Evaluates the JSON schema compliance rate of the active LiteLLM model against
Kairo's DocxOperation / ExcelOperation / SlideOperation schemas.

This is the gate condition for Step 2: "eval_schema_compliance.py reports ≥95%
schema compliance. Replace qwen2.5:7b with kairo-docwriter-4b in config."

Usage
-----
    python scripts/eval_schema_compliance.py [--model kairo-fast] [--samples 50]

Outputs
-------
    Composite Score: <score>   (0.00–1.00)
    Gate: PASS / FAIL
"""

import argparse
import json
import sys
import time
import logging
import urllib.request
import urllib.error
from typing import Type

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("eval_schema_compliance")


# ─── Schema Definitions ──────────────────────────────────────────────────────

DOCX_EXAMPLE_PROMPTS = [
    "Insert a heading 'Q3 Results' after paragraph 2 with Heading 2 style.",
    "Replace paragraph 5 with 'Revenue exceeded targets by 12%.'",
    "Add a bullet point 'Improved customer retention' after paragraph 3.",
    "Insert a table with headers Product, Revenue, Cost after paragraph 1.",
    "Delete the paragraph at index 4.",
    "Append a formal closing paragraph after paragraph 8.",
    "Change paragraph 2 to use Heading 1 style.",
    "Insert 3 bullet points about Q3 wins after paragraph 6.",
    "Replace paragraph 0 with a stronger executive summary.",
    "Add a 'Next Steps' section heading after the last paragraph.",
]

EXCEL_EXAMPLE_PROMPTS = [
    "Write a VLOOKUP formula in cell E2 to look up A2 in range A:B.",
    "Calculate total revenue in D10 using SUM(D2:D9).",
    "Add IFERROR wrapper around the formula in C5.",
    "Write an IF formula in G3: if F3>1000 then 'High' else 'Normal'.",
    "Insert PMT formula for a loan in B15.",
    "Calculate average in C20 for range C2:C19.",
    "Write XLOOKUP in D5 to find product name from Sheet2!A:B.",
    "Add conditional formula in H2: =IF(AND(F2>0,G2>0),F2*G2,0).",
    "Create a SUMIF formula summing column B where column A equals 'Widget A'.",
    "Write a date formula in A1 showing today's date.",
]

SLIDE_EXAMPLE_PROMPTS = [
    "Update slide 3 title to 'Q3 Performance Overview'.",
    "Replace bullet 2 on slide 5 with 'Revenue up 15% YoY'.",
    "Add a new slide after slide 4 with title 'Key Risks'.",
    "Insert 3 bullets on slide 2 about market expansion.",
    "Change slide 1 subtitle to 'Investor Update — June 2025'.",
    "Delete slide 7 entirely.",
    "Add speaker notes to slide 3: 'Emphasize the growth trajectory'.",
    "Replace all bullets on slide 4 with updated metrics.",
    "Insert a table on slide 6 with 3 columns: Region, Target, Actual.",
    "Move slide 2 to position 5.",
]

# JSON schema validation functions
def _validate_docx_response(data: dict) -> tuple:
    """Returns (valid: bool, reason: str)"""
    if "operations" not in data:
        return False, "missing 'operations' key"
    ops = data["operations"]
    if not isinstance(ops, list):
        return False, "'operations' must be a list"
    if len(ops) == 0:
        return False, "empty operations list"
    for op in ops:
        if not isinstance(op, dict):
            return False, f"operation not a dict: {op}"
        op_type = op.get("type") or op.get("action")
        if not op_type:
            return False, f"operation missing 'type': {op}"
        valid_types = {
            "insert_paragraph", "replace_paragraph", "delete_paragraph",
            "append", "insert_table", "append_to_run", "insert_after_heading",
        }
        if op_type not in valid_types:
            return False, f"unknown op type: {op_type!r}"
    return True, "ok"


def _validate_excel_response(data: dict) -> tuple:
    """Returns (valid: bool, reason: str)"""
    if "operations" not in data:
        return False, "missing 'operations' key"
    ops = data["operations"]
    if not isinstance(ops, list) or not ops:
        return False, "operations must be non-empty list"
    for op in ops:
        if not isinstance(op, dict):
            return False, "operation not a dict"
        op_type = op.get("type") or op.get("action")
        valid_types = {"write_cell", "write_range", "fill_formula", "create_chart", "create_pivot"}
        if op_type not in valid_types:
            return False, f"unknown op type: {op_type!r}"
    return True, "ok"


def _validate_slide_response(data: dict) -> tuple:
    """Returns (valid: bool, reason: str)"""
    if "operations" not in data:
        return False, "missing 'operations' key"
    ops = data["operations"]
    if not isinstance(ops, list) or not ops:
        return False, "operations must be non-empty list"
    for op in ops:
        if not isinstance(op, dict):
            return False, "operation not a dict"
        op_type = op.get("type") or op.get("action")
        valid_types = {
            "update_title", "replace_bullet", "add_slide", "delete_slide",
            "update_subtitle", "add_speaker_notes", "insert_table_slide",
        }
        if op_type not in valid_types:
            return False, f"unknown op type: {op_type!r}"
    return True, "ok"


SCHEMA_GROUPS = [
    ("DocxOperation", DOCX_EXAMPLE_PROMPTS, _validate_docx_response,
     "You are KairoDocWriter. Output ONLY valid JSON with this structure: "
     '{\"operations\": [{\"type\": \"insert_paragraph\", \"after_paragraph_index\": 0, '
     '\"style\": \"Heading 2\", \"runs\": [{\"text\": \"...\", \"bold\": false, \"italic\": false}]}]}'),

    ("ExcelOperation", EXCEL_EXAMPLE_PROMPTS, _validate_excel_response,
     "You are KairoExcelWriter. Output ONLY valid JSON with this structure: "
     '{\"operations\": [{\"type\": \"write_cell\", \"sheet\": \"Sheet1\", '
     '\"cell\": \"A1\", \"formula\": \"=SUM(B1:B10)\"}]}'),

    ("SlideOperation", SLIDE_EXAMPLE_PROMPTS, _validate_slide_response,
     "You are KairoPptxWriter. Output ONLY valid JSON with this structure: "
     '{\"operations\": [{\"type\": \"update_title\", \"slide_index\": 0, \"title\": \"...\"}]}'),
]


def call_model(prompt: str, system: str, model: str, timeout: float = 60.0) -> str:
    """Calls LiteLLM proxy on port 4000 and returns raw content string."""
    endpoint = "http://localhost:4000/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def extract_json(content: str) -> dict:
    """Extracts the first valid JSON object from a string."""
    first = content.find("{")
    last = content.rfind("}")
    if first != -1 and last != -1 and last > first:
        return json.loads(content[first:last + 1])
    raise ValueError(f"No JSON object found in: {content[:200]!r}")


def run_evaluation(model: str = "kairo-standard", samples_per_group: int = 5) -> dict:
    """
    Runs schema compliance evaluation across all three schema groups.

    Returns a dict with per-group stats and a composite compliance rate.
    """
    results = {}
    total_pass = 0
    total_fail = 0

    for schema_name, prompts, validator, system_prompt in SCHEMA_GROUPS:
        group_pass = 0
        group_fail = 0
        failures = []

        selected_prompts = prompts[:samples_per_group]
        log.info(f"Evaluating {schema_name}: {len(selected_prompts)} prompts on model={model!r}")

        for prompt in selected_prompts:
            try:
                raw = call_model(prompt, system_prompt, model)
                data = extract_json(raw)
                valid, reason = validator(data)
                if valid:
                    group_pass += 1
                else:
                    group_fail += 1
                    failures.append({"prompt": prompt[:60], "reason": reason})
            except urllib.error.URLError as e:
                group_fail += 1
                failures.append({"prompt": prompt[:60], "reason": f"LiteLLM connection error: {e}"})
            except json.JSONDecodeError as e:
                group_fail += 1
                failures.append({"prompt": prompt[:60], "reason": f"JSON decode error: {e}"})
            except Exception as e:
                group_fail += 1
                failures.append({"prompt": prompt[:60], "reason": str(e)})

        group_total = group_pass + group_fail
        group_rate = (group_pass / group_total) if group_total > 0 else 0.0
        results[schema_name] = {
            "pass": group_pass,
            "fail": group_fail,
            "total": group_total,
            "compliance_rate": round(group_rate * 100, 1),
            "failures": failures[:3],  # Cap reported failures
        }
        total_pass += group_pass
        total_fail += group_fail

    total = total_pass + total_fail
    composite = (total_pass / total) if total > 0 else 0.0
    results["composite"] = {
        "pass": total_pass,
        "fail": total_fail,
        "total": total,
        "compliance_rate": round(composite * 100, 1),
    }
    return results


def main():
    parser = argparse.ArgumentParser(description="Kairo Schema Compliance Evaluator")
    parser.add_argument("--model", default="kairo-standard", help="LiteLLM model alias")
    parser.add_argument("--samples", type=int, default=5, help="Prompts per schema group (max 10)")
    args = parser.parse_args()

    samples = min(10, max(1, args.samples))
    print(f"\nKairo Schema Compliance Evaluation")
    print(f"Model: {args.model}  |  Samples per group: {samples}")
    print("=" * 60)

    try:
        results = run_evaluation(model=args.model, samples_per_group=samples)
    except Exception as e:
        print(f"ERROR: Evaluation failed: {e}")
        print("Ensure the LiteLLM proxy is running: python -m sidecar.start_litellm")
        sys.exit(1)

    for schema_name in ["DocxOperation", "ExcelOperation", "SlideOperation"]:
        r = results.get(schema_name, {})
        print(f"\n{schema_name}:")
        print(f"  Passed : {r.get('pass', 0)}/{r.get('total', 0)}")
        print(f"  Rate   : {r.get('compliance_rate', 0):.1f}%")
        if r.get("failures"):
            print(f"  Failures:")
            for f in r["failures"]:
                print(f"    - {f['prompt']!r}: {f['reason']}")

    comp = results.get("composite", {})
    composite_rate = comp.get("compliance_rate", 0.0)
    print(f"\n{'='*60}")
    print(f"Composite Score  : {composite_rate / 100:.4f}")
    print(f"Compliance Rate  : {composite_rate:.1f}%")
    print(f"Gate Threshold   : 95.0%")

    if composite_rate >= 95.0:
        print(f"Gate             : PASS [PASS] ({composite_rate:.1f}% >= 95%)")
        print("ACTION: Replace kairo-standard with kairo-fast in litellm_config.yaml")
        sys.exit(0)
    else:
        gap = 95.0 - composite_rate
        print(f"Gate             : FAIL [FAIL] ({composite_rate:.1f}% < 95% - gap: {gap:.1f}%)")
        print("ACTION: Continue fine-tuning or investigate failure patterns above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
