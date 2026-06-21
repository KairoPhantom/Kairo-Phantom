#!/usr/bin/env python3
"""
Kairo Phantom — Pass 0 Error Analysis (REMEDIATION_close_the_gates.md)

For EVERY question/field in the bench + held-out corpus, dumps a row:
  pack | fixture | field | answer-in-doc? (y/n) | system result (answer/refuse) |
  cascade stage (EXACT/FUZZY/SEMANTIC/VISUAL/BLOCK) | matched?

Then labels every FAILURE as exactly one of:
  F1 — false-refusal: answer IS in the doc, system refused (BLOCK)
  F2 — correct refusal: answer not in doc, correctly refused (good — leave alone)
  F3 — grounded-but-wrong: answered with a bbox but the answer is wrong
  F4 — retrieval miss: the correct chunk was never in top-k

Outputs a failure table grouped by pack and by category.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

# Ensure we can import from the repo root
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"

from kernel.core.contracts import GateVerdict
from kernel.core.data_model import (
    Document,
    Extraction,
    GroundingMethod,
)
from kernel.core.grounding import GroundingVerifierImpl, normalize_text
from kernel.core.provenance import ProvenanceLogImpl
from kernel.sidecar.ingestor import IngestorImpl
from kernel.sidecar.inference_gateway import TieredInferenceGateway
from kernel.sidecar.memory_store import MemoryStoreImpl
from kernel.sidecar.orchestrator import OrchestratorImpl
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.sidecar.security_filter import LocalSecurityFilter

from packs.generic.pack import GenericPack
from packs.invoice.pack import InvoicePack
from packs.paper.pack import PaperPack
from packs.contract.pack import ContractPack


@dataclass
class FieldRow:
    pack: str
    fixture: str
    field: str
    answer_in_doc: bool  # True if ground truth has a non-empty value
    expected_val: str
    system_result: str  # "answer" or "refuse"
    cascade_stage: str  # EXACT/FUZZY/SEMANTIC/VISUAL/BLOCK/N-A
    extracted_val: str
    matched: bool
    failure_category: str  # F1/F2/F3/F4/OK


def _is_answerable(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    if isinstance(val, (list, dict)) and len(val) == 0:
        return False
    return True


def _check_match(field_name: str, extracted: str, expected: Any) -> bool:
    """Check if extracted value matches expected ground truth."""
    if extracted is None:
        return False
    if isinstance(expected, str):
        ext_norm = " ".join(extracted.strip().lower().split())
        exp_norm = " ".join(expected.strip().lower().split())
        return ext_norm == exp_norm or exp_norm in ext_norm or ext_norm in exp_norm
    elif isinstance(expected, (int, float)):
        try:
            return abs(float(extracted) - float(expected)) < 0.01
        except (ValueError, TypeError):
            return str(expected) in str(extracted)
    elif isinstance(expected, list):
        try:
            extracted_list = json.loads(extracted) if extracted.startswith("[") else [extracted]
        except Exception:
            extracted_list = [extracted]
        for item in expected:
            item_norm = str(item).strip().lower()
            for ext_item in extracted_list:
                ext_norm = str(ext_item).strip().lower()
                if item_norm in ext_norm or ext_norm in item_norm:
                    return True
        return False
    return False


def _check_value_in_text(value: Any, chunks_text: str) -> bool:
    """Check if the expected value appears (even partially) in the document text."""
    if isinstance(value, str):
        norm_val = normalize_text(value)
        norm_text = normalize_text(chunks_text)
        return norm_val in norm_text or any(
            normalize_text(word) in norm_text
            for word in value.split()
            if len(word) > 3
        )
    elif isinstance(value, (int, float)):
        return str(value) in chunks_text
    elif isinstance(value, list):
        return all(_check_value_in_text(item, chunks_text) for item in value)
    return False


def run_error_analysis() -> list[FieldRow]:
    """Run the full error analysis on bench + held-out corpus."""
    os.chdir(REPO_ROOT)

    packs_config = [
        {"name": "generic", "class": GenericPack, "dir": "fixtures/generic"},
        {"name": "invoice", "class": InvoicePack, "dir": "fixtures/invoice"},
        {"name": "paper", "class": PaperPack, "dir": "fixtures/paper"},
        {"name": "contract", "class": ContractPack, "dir": "fixtures/contract"},
        {"name": "held_out", "class": InvoicePack, "dir": "fixtures/held_out"},
    ]

    verifier = GroundingVerifierImpl()
    all_rows: list[FieldRow] = []

    for config in packs_config:
        pack_name = config["name"]
        pack_class = config["class"]
        fixtures_dir = pathlib.Path(config["dir"])
        gt_file = fixtures_dir / "ground_truth.json"

        if not gt_file.exists():
            continue

        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        fixtures = gt_data.get("fixtures", [])
        pack = pack_class()

        memory_store = MemoryStoreImpl(":memory:")
        provenance_log = ProvenanceLogImpl()
        ingestor = IngestorImpl()
        security_filter = LocalSecurityFilter(enable_pii_scan=False)
        inference_gateway = TieredInferenceGateway(tier3_enabled=False)
        quality_gate = LocalQualityGate(memory_store)

        orchestrator = OrchestratorImpl(
            ingestor=ingestor,
            security_filter=security_filter,
            inference_gateway=inference_gateway,
            quality_gate=quality_gate,
            provenance_log=provenance_log,
            pack=pack,
            memory_store=memory_store,
        )

        for fixture in fixtures:
            fixture_id = fixture["fixture_id"]
            file_path = fixtures_dir / fixture["file"]
            if not file_path.exists():
                continue

            # Get the full document text for checking if value is in doc
            doc_text = file_path.read_text(encoding="utf-8", errors="replace")

            doc = Document(source_path=str(file_path))
            trace = orchestrator.run(doc)

            ext_by_field = {e.field_name: e for e in trace.extractions}
            ground_truth = fixture["ground_truth"]

            for field in pack.fields:
                expected_val = ground_truth.get(field)
                ext = ext_by_field.get(field)
                answerable = _is_answerable(expected_val)

                if answerable:
                    # Check if the expected value is actually in the document text
                    value_in_doc = _check_value_in_text(expected_val, doc_text)

                    if ext is None:
                        # No extraction produced
                        system_result = "refuse"
                        cascade_stage = "N-A"
                        extracted_val = "None"
                        matched = False
                        if value_in_doc:
                            failure = "F1"  # false-refusal: answer in doc but not extracted
                        else:
                            failure = "F4"  # retrieval miss: value not found in doc text
                    else:
                        # Extraction was produced
                        gate_res = quality_gate.check(ext)
                        is_blocked = gate_res.verdict == GateVerdict.BLOCK
                        cascade_stage = ext.method.value if ext.method else "BLOCK"

                        if is_blocked:
                            system_result = "refuse"
                            matched = _check_match(field, ext.value, expected_val)
                            if value_in_doc:
                                failure = "F1"  # false-refusal: answer in doc, extraction produced but blocked
                            else:
                                failure = "F4"
                            extracted_val = ext.value[:80] if ext.value else "None"
                        else:
                            system_result = "answer"
                            matched = _check_match(field, ext.value, expected_val)
                            if matched:
                                failure = "OK"
                            else:
                                failure = "F3"  # grounded-but-wrong
                            extracted_val = ext.value[:80] if ext.value else "None"
                else:
                    # Unanswerable field
                    if ext is None:
                        system_result = "refuse"
                        cascade_stage = "N-A"
                        extracted_val = "None"
                        matched = True
                        failure = "F2"  # correct refusal
                    else:
                        gate_res = quality_gate.check(ext)
                        if gate_res.verdict == GateVerdict.BLOCK:
                            system_result = "refuse"
                            cascade_stage = ext.method.value
                            matched = True
                            failure = "F2"  # correct refusal
                        else:
                            system_result = "answer"
                            cascade_stage = ext.method.value
                            matched = False
                            failure = "F3"  # answered an unanswerable question
                        extracted_val = ext.value[:80] if ext.value else "None"

                all_rows.append(FieldRow(
                    pack=pack_name,
                    fixture=fixture_id,
                    field=field,
                    answer_in_doc=answerable,
                    expected_val=str(expected_val)[:80] if expected_val is not None else "",
                    system_result=system_result,
                    cascade_stage=cascade_stage,
                    extracted_val=extracted_val,
                    matched=matched,
                    failure_category=failure,
                ))

    return all_rows


def print_failure_table(rows: list[FieldRow]) -> None:
    """Print the failure table grouped by pack and by category."""
    # Group by pack
    packs = sorted(set(r.pack for r in rows))

    print("=" * 100)
    print("KAIRO PHANTOM — PASS 0 ERROR ANALYSIS")
    print("=" * 100)

    # Summary counts
    categories = {"OK": 0, "F1": 0, "F2": 0, "F3": 0, "F4": 0}
    for r in rows:
        categories[r.failure_category] = categories.get(r.failure_category, 0) + 1

    total = len(rows)
    print(f"\nTOTAL FIELDS ANALYZED: {total}")
    print(f"  OK (correct grounded answer):  {categories['OK']}")
    print(f"  F1 (false-refusal):             {categories['F1']}")
    print(f"  F2 (correct refusal):           {categories['F2']}")
    print(f"  F3 (grounded-but-wrong):        {categories['F3']}")
    print(f"  F4 (retrieval miss):            {categories['F4']}")

    # Per-pack breakdown
    print("\n" + "-" * 100)
    print("PER-PACK FAILURE BREAKDOWN:")
    print("-" * 100)
    for pack in packs:
        pack_rows = [r for r in rows if r.pack == pack]
        pack_cats = {"OK": 0, "F1": 0, "F2": 0, "F3": 0, "F4": 0}
        for r in pack_rows:
            pack_cats[r.failure_category] = pack_cats.get(r.failure_category, 0) + 1
        answerable = sum(1 for r in pack_rows if r.answer_in_doc)
        grounded = pack_cats["OK"]
        false_ref = pack_cats["F1"]
        print(f"\n  Pack: {pack} ({len(pack_rows)} fields, {answerable} answerable)")
        print(f"    Grounded: {grounded}/{answerable} = {grounded/answerable*100:.1f}%" if answerable else "    No answerable fields")
        print(f"    False-refusal: {false_ref}/{answerable} = {false_ref/answerable*100:.1f}%" if answerable else "")
        print(f"    Correct refusal: {pack_cats['F2']}")
        print(f"    Grounded-but-wrong: {pack_cats['F3']}")
        print(f"    Retrieval miss: {pack_cats['F4']}")

    # Detailed failure rows
    print("\n" + "-" * 100)
    print("DETAILED FAILURE ROWS (F1 + F3 + F4 only):")
    print("-" * 100)
    print(f"  {'Pack':<12} {'Fixture':<25} {'Field':<25} {'Cat':<4} {'Stage':<10} {'Expected':<40} {'Extracted':<40}")
    print(f"  {'-'*12} {'-'*25} {'-'*25} {'-'*4} {'-'*10} {'-'*40} {'-'*40}")

    for r in rows:
        if r.failure_category in ("F1", "F3", "F4"):
            print(f"  {r.pack:<12} {r.fixture:<25} {r.field:<25} {r.failure_category:<4} {r.cascade_stage:<10} {r.expected_val[:38]:<40} {r.extracted_val[:38]:<40}")

    # Category summary
    print("\n" + "-" * 100)
    print("FAILURE CATEGORY SUMMARY:")
    print("-" * 100)
    for cat in ["F1", "F2", "F3", "F4"]:
        cat_rows = [r for r in rows if r.failure_category == cat]
        if cat_rows:
            print(f"\n  {cat} ({len(cat_rows)} cases):")
            for r in cat_rows:
                print(f"    {r.pack}/{r.fixture}/{r.field}: expected='{r.expected_val[:50]}' extracted='{r.extracted_val[:50]}'")

    print("\n" + "=" * 100)


def main():
    rows = run_error_analysis()
    print_failure_table(rows)

    # Save machine-readable output
    output_path = REPO_ROOT / "bench" / "error_analysis.json"
    output_data = [
        {
            "pack": r.pack,
            "fixture": r.fixture,
            "field": r.field,
            "answer_in_doc": r.answer_in_doc,
            "expected": r.expected_val,
            "system_result": r.system_result,
            "cascade_stage": r.cascade_stage,
            "extracted": r.extracted_val,
            "matched": r.matched,
            "failure_category": r.failure_category,
        }
        for r in rows
    ]
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nMachine-readable output saved to {output_path}")


if __name__ == "__main__":
    main()