"""
Kairo Phantom — Comprehensive Grounding Benchmark Harness (SPEC §S8, §S9)

Upgraded for P0.2: computes and prints ALL FOUR release gates with measured
values vs targets, corpus hash, model pinning, determinism guarantees,
per-document breakdowns, machine-readable JSON, human-readable table,
and historical run storage.

Release Gates (hard targets, MEASURED not asserted):
  1. grounded-answer rate: ≥ 95% of answerable questions get a grounded answer
  2. refusal-on-unanswerable: 100% of unanswerable questions correctly refused
  3. false-refusal rate: < 5% of answerable questions incorrectly refused
  4. ungrounded-render count: 0 answers rendered without verified grounding
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import pathlib
import platform
import sys
from datetime import datetime, timezone

from kernel.core.contracts import GateVerdict
from kernel.core.data_model import Document, GroundingMethod
from kernel.core.provenance import ProvenanceLogImpl
from kernel.sidecar.ingestor import IngestorImpl
from kernel.sidecar.inference_gateway import TieredInferenceGateway
from kernel.sidecar.memory_store import MemoryStoreImpl
from kernel.sidecar.orchestrator import OrchestratorImpl
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.sidecar.security_filter import LocalSecurityFilter
from kernel.core.grounding import GroundingVerifierImpl

# Import packs
from packs.generic.pack import GenericPack
from packs.invoice.pack import InvoicePack
from packs.paper.pack import PaperPack
from packs.contract.pack import ContractPack

logger = logging.getLogger("bench.harness")

# ---------------------------------------------------------------------------
# Determinism constants — pinned for reproducibility
# ---------------------------------------------------------------------------
PINNED_MODEL_ID = "kairo-test-mode-v1"
PINNED_SEED = 42
PINNED_PYTHON_VERSION = platform.python_version()
PINNED_PLATFORM = f"{platform.system()}-{platform.machine()}"

# Gate targets
TARGET_GROUNDED_ANSWER_RATE = 95.0
TARGET_REFUSAL_ON_UNANSWERABLE = 100.0
TARGET_FALSE_REFUSAL_RATE = 5.0
TARGET_UNGROUNDED_RENDER_COUNT = 0


# ---------------------------------------------------------------------------
# Corpus hashing — deterministic hash of all ground_truth.json files
# ---------------------------------------------------------------------------
def compute_corpus_hash(packs_config: list[dict]) -> str:
    """Compute a deterministic SHA-256 hash of all fixture ground_truth.json files.

    The hash covers every ground_truth.json across all packs, sorted by pack name
    and fixture_id, so the same corpus always yields the same hash.
    """
    hasher = hashlib.sha256()
    for config in sorted(packs_config, key=lambda c: c["name"]):
        pack_name = config["name"]
        fixtures_dir = pathlib.Path(config["dir"])
        gt_file = fixtures_dir / "ground_truth.json"
        if not gt_file.exists():
            continue
        # Hash the pack name + the file content
        pack_bytes = pack_name.encode("utf-8")
        file_bytes = gt_file.read_bytes()
        hasher.update(pack_bytes)
        hasher.update(b"\x00")  # separator
        hasher.update(file_bytes)
        hasher.update(b"\x00")

        # Also hash the actual fixture document files for full corpus integrity
        try:
            gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
            for fixture in gt_data.get("fixtures", []):
                fixture_file = fixtures_dir / fixture["file"]
                if fixture_file.exists():
                    hasher.update(fixture_file.read_bytes())
                    hasher.update(b"\x00")
        except Exception:
            pass

    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Per-field grounding check using the independent Rust-style verifier
# ---------------------------------------------------------------------------
def _is_field_answerable(expected_val) -> bool:
    """A field is answerable if ground truth has a non-empty value."""
    if expected_val is None:
        return False
    if isinstance(expected_val, str) and expected_val.strip() == "":
        return False
    if isinstance(expected_val, (list, dict)) and len(expected_val) == 0:
        return False
    return True


def _is_extraction_grounded(ext, quality_gate, verifier, memory_store) -> tuple[bool, bool]:
    """Check if an extraction is grounded and rendered.

    Returns (is_grounded, is_rendered).
    - is_grounded: the extraction has a valid grounding method (not BLOCK)
    - is_rendered: the extraction passed the quality gate (not BLOCK verdict)
    """
    gate_res = quality_gate.check(ext)
    is_rendered = gate_res.verdict != GateVerdict.BLOCK

    # Independent re-verification: check that anchors resolve to real chunks
    is_grounded = False
    if ext.method != GroundingMethod.BLOCK and ext.anchors:
        # Verify each anchor's chunk exists in memory store
        all_anchors_valid = True
        for anchor in ext.anchors:
            chunk = memory_store.get_chunk(anchor.chunk_id)
            if not chunk:
                all_anchors_valid = False
                break
            # Re-verify the value against the chunk using the independent verifier
            method, _ = verifier.verify(ext.value, ext.source_span, [chunk])
            if method == GroundingMethod.BLOCK:
                all_anchors_valid = False
                break
        is_grounded = all_anchors_valid

    return is_grounded, is_rendered


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------
def run_benchmark(packs_config: list[dict] | None = None) -> dict:
    """Run the full benchmark and return a results dict.

    This function is the core benchmark logic, separated from I/O so tests
    can call it directly and compare outputs for determinism.
    """
    if packs_config is None:
        packs_config = [
            {"name": "generic", "class": GenericPack, "dir": "fixtures/generic"},
            {"name": "invoice", "class": InvoicePack, "dir": "fixtures/invoice"},
            {"name": "paper", "class": PaperPack, "dir": "fixtures/paper"},
            {"name": "contract", "class": ContractPack, "dir": "fixtures/contract"},
        ]

    # Enable test mode for deterministic gateway response
    os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"

    corpus_hash = compute_corpus_hash(packs_config)
    verifier = GroundingVerifierImpl()

    # Global gate counters
    total_answerable = 0
    total_grounded = 0
    total_unanswerable = 0
    total_correct_refusals = 0
    total_false_refusals = 0
    ungrounded_render_count = 0

    pack_results = {}
    per_document_results = []

    for config in packs_config:
        pack_name = config["name"]
        pack_class = config["class"]
        fixtures_dir = config["dir"]

        fixtures_path = pathlib.Path(fixtures_dir)
        gt_file = fixtures_path / "ground_truth.json"

        if not gt_file.exists():
            print(f"Warning: ground_truth.json not found in {fixtures_dir}, skipping pack {pack_name}")
            continue

        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        fixtures = gt_data.get("fixtures", [])
        if not fixtures:
            continue

        pack = pack_class()
        print(f"Running benchmark for pack: {pack_name} ...")

        # Run pack oracle to get per-field accuracy
        per_field_accuracy = pack.oracle(str(fixtures_path))

        # Setup orchestrator
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

        # Pack-level counters
        pack_answerable = 0
        pack_grounded = 0
        pack_unanswerable = 0
        pack_correct_refusals = 0
        pack_false_refusals = 0
        pack_ungrounded_renders = 0
        pack_total_extractions = 0
        pack_passed_extractions = 0

        for fixture in fixtures:
            fixture_id = fixture["fixture_id"]
            file_path = fixtures_path / fixture["file"]
            if not file_path.exists():
                continue

            doc = Document(source_path=str(file_path))
            trace = orchestrator.run(doc)

            # Map trace extractions by field
            ext_by_field = {e.field_name: e for e in trace.extractions}
            ground_truth = fixture["ground_truth"]

            # Per-document tracking
            doc_answerable = 0
            doc_grounded = 0
            doc_unanswerable = 0
            doc_correct_refusals = 0
            doc_false_refusals = 0
            doc_ungrounded_renders = 0
            doc_field_details = []

            # Check every field in pack schema
            for field in pack.fields:
                expected_val = ground_truth.get(field)
                ext = ext_by_field.get(field)

                is_answerable = _is_field_answerable(expected_val)

                if is_answerable:
                    pack_answerable += 1
                    doc_answerable += 1
                    total_answerable += 1

                    if ext is None:
                        # No extraction produced for an answerable field → false refusal
                        pack_false_refusals += 1
                        doc_false_refusals += 1
                        total_false_refusals += 1
                        doc_field_details.append({
                            "field": field,
                            "status": "false_refusal",
                            "expected": str(expected_val)[:100],
                            "extracted": None,
                            "grounded": False,
                            "rendered": False,
                        })
                    else:
                        is_grounded, is_rendered = _is_extraction_grounded(
                            ext, quality_gate, verifier, memory_store
                        )
                        if is_grounded and is_rendered:
                            pack_grounded += 1
                            doc_grounded += 1
                            total_grounded += 1
                            doc_field_details.append({
                                "field": field,
                                "status": "grounded",
                                "expected": str(expected_val)[:100],
                                "extracted": ext.value[:100],
                                "grounded": True,
                                "rendered": True,
                                "method": ext.method.value,
                            })
                        elif is_rendered and not is_grounded:
                            # Rendered without grounding → ungrounded render!
                            pack_ungrounded_renders += 1
                            doc_ungrounded_renders += 1
                            ungrounded_render_count += 1
                            doc_field_details.append({
                                "field": field,
                                "status": "ungrounded_render",
                                "expected": str(expected_val)[:100],
                                "extracted": ext.value[:100],
                                "grounded": False,
                                "rendered": True,
                                "method": ext.method.value,
                            })
                        else:
                            # Not grounded and not rendered → false refusal (blocked when answer exists)
                            pack_false_refusals += 1
                            doc_false_refusals += 1
                            total_false_refusals += 1
                            doc_field_details.append({
                                "field": field,
                                "status": "false_refusal",
                                "expected": str(expected_val)[:100],
                                "extracted": ext.value[:100] if ext.value else None,
                                "grounded": False,
                                "rendered": False,
                                "method": ext.method.value,
                            })
                else:
                    # Unanswerable field
                    pack_unanswerable += 1
                    doc_unanswerable += 1
                    total_unanswerable += 1

                    # Correct refusal = no extraction OR extraction was BLOCKED
                    if ext is None:
                        pack_correct_refusals += 1
                        doc_correct_refusals += 1
                        total_correct_refusals += 1
                        doc_field_details.append({
                            "field": field,
                            "status": "correct_refusal",
                            "expected": None,
                            "extracted": None,
                            "grounded": False,
                            "rendered": False,
                        })
                    else:
                        gate_res = quality_gate.check(ext)
                        if gate_res.verdict == GateVerdict.BLOCK:
                            pack_correct_refusals += 1
                            doc_correct_refusals += 1
                            total_correct_refusals += 1
                            doc_field_details.append({
                                "field": field,
                                "status": "correct_refusal",
                                "expected": None,
                                "extracted": ext.value[:100],
                                "grounded": False,
                                "rendered": False,
                                "method": ext.method.value,
                            })
                        else:
                            # Produced an extraction for an unanswerable field
                            # This is not a correct refusal
                            is_grounded, is_rendered = _is_extraction_grounded(
                                ext, quality_gate, verifier, memory_store
                            )
                            if is_rendered and not is_grounded:
                                pack_ungrounded_renders += 1
                                doc_ungrounded_renders += 1
                                ungrounded_render_count += 1
                            doc_field_details.append({
                                "field": field,
                                "status": "incorrect_answer",
                                "expected": None,
                                "extracted": ext.value[:100],
                                "grounded": is_grounded,
                                "rendered": is_rendered,
                                "method": ext.method.value,
                            })

            # Count total/passed extractions for this document
            for ext in trace.extractions:
                pack_total_extractions += 1
                gate_res = quality_gate.check(ext)
                if gate_res.verdict != GateVerdict.BLOCK:
                    pack_passed_extractions += 1

            # Per-document summary
            doc_summary = {
                "fixture_id": fixture_id,
                "pack": pack_name,
                "file": fixture["file"],
                "answerable_fields": doc_answerable,
                "grounded_answers": doc_grounded,
                "unanswerable_fields": doc_unanswerable,
                "correct_refusals": doc_correct_refusals,
                "false_refusals": doc_false_refusals,
                "ungrounded_renders": doc_ungrounded_renders,
                "grounded_answer_rate": round(
                    (doc_grounded / doc_answerable * 100.0) if doc_answerable else 100.0, 4
                ),
                "refusal_on_unanswerable": round(
                    (doc_correct_refusals / doc_unanswerable * 100.0) if doc_unanswerable else 100.0, 4
                ),
                "false_refusal_rate": round(
                    (doc_false_refusals / doc_answerable * 100.0) if doc_answerable else 0.0, 4
                ),
                "field_details": doc_field_details,
            }
            per_document_results.append(doc_summary)

        # Calculate pack-level metrics
        pack_grounded_rate = (pack_grounded / pack_answerable * 100.0) if pack_answerable else 100.0
        pack_refusal_rate = (pack_correct_refusals / pack_unanswerable * 100.0) if pack_unanswerable else 100.0
        pack_false_refusal_rate = (pack_false_refusals / pack_answerable * 100.0) if pack_answerable else 0.0

        pack_results[pack_name] = {
            "total_documents": len(fixtures),
            "total_extractions": pack_total_extractions,
            "passed_extractions": pack_passed_extractions,
            "answerable_fields": pack_answerable,
            "grounded_answers": pack_grounded,
            "unanswerable_fields": pack_unanswerable,
            "correct_refusals": pack_correct_refusals,
            "false_refusals": pack_false_refusals,
            "ungrounded_render_count": pack_ungrounded_renders,
            "grounded_answer_rate": round(pack_grounded_rate, 4),
            "refusal_on_unanswerable": round(pack_refusal_rate, 4),
            "false_refusal_rate": round(pack_false_refusal_rate, 4),
            "per_field_accuracy": {k: round(v, 4) for k, v in sorted(per_field_accuracy.items())},
        }

    # Calculate global gate metrics
    global_grounded_rate = (total_grounded / total_answerable * 100.0) if total_answerable else 100.0
    global_refusal_rate = (total_correct_refusals / total_unanswerable * 100.0) if total_unanswerable else 100.0
    global_false_refusal_rate = (total_false_refusals / total_answerable * 100.0) if total_answerable else 0.0

    # Build the deterministic results dict (no timestamps, no random IDs)
    results = {
        "model_id": PINNED_MODEL_ID,
        "seed": PINNED_SEED,
        "corpus_hash": corpus_hash,
        "python_version": PINNED_PYTHON_VERSION,
        "platform": PINNED_PLATFORM,
        "gates": {
            "grounded_answer_rate": {
                "measured": round(global_grounded_rate, 4),
                "target": TARGET_GROUNDED_ANSWER_RATE,
                "unit": "percent",
                "numerator": total_grounded,
                "denominator": total_answerable,
                "passes": global_grounded_rate >= TARGET_GROUNDED_ANSWER_RATE,
            },
            "refusal_on_unanswerable": {
                "measured": round(global_refusal_rate, 4),
                "target": TARGET_REFUSAL_ON_UNANSWERABLE,
                "unit": "percent",
                "numerator": total_correct_refusals,
                "denominator": total_unanswerable,
                "passes": global_refusal_rate >= TARGET_REFUSAL_ON_UNANSWERABLE,
            },
            "false_refusal_rate": {
                "measured": round(global_false_refusal_rate, 4),
                "target": TARGET_FALSE_REFUSAL_RATE,
                "unit": "percent",
                "numerator": total_false_refusals,
                "denominator": total_answerable,
                "passes": global_false_refusal_rate < TARGET_FALSE_REFUSAL_RATE,
            },
            "ungrounded_render_count": {
                "measured": ungrounded_render_count,
                "target": TARGET_UNGROUNDED_RENDER_COUNT,
                "unit": "count",
                "passes": ungrounded_render_count == TARGET_UNGROUNDED_RENDER_COUNT,
            },
        },
        "packs": pack_results,
        "per_document": per_document_results,
    }

    return results


def print_gates_table(results: dict) -> None:
    """Print the four release gates with measured values vs targets."""
    print()
    print("=" * 72)
    print("KAIRO PHANTOM — RELEASE GATE BENCHMARK")
    print("=" * 72)
    print(f"  Model ID:     {results['model_id']}")
    print(f"  Seed:         {results['seed']}")
    print(f"  Corpus Hash:  {results['corpus_hash']}")
    print(f"  Python:       {results['python_version']}")
    print(f"  Platform:     {results['platform']}")
    print("-" * 72)
    print()
    print("  RELEASE GATES (measured vs target):")
    print()
    print(f"  {'Gate':<30} {'Measured':>12} {'Target':>12} {'Status':>8}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*8}")

    gates = results["gates"]
    for gate_name, gate_data in gates.items():
        measured = gate_data["measured"]
        target = gate_data["target"]
        unit = gate_data["unit"]
        passes = gate_data["passes"]

        if unit == "percent":
            measured_str = f"{measured}%"
            if gate_name == "false_refusal_rate":
                target_str = f"<{target}%"
            else:
                target_str = f"≥{target}%"
        else:
            measured_str = str(measured)
            target_str = f"={target}"

        status_str = "PASS" if passes else "FAIL"
        # Format gate name nicely
        display_name = gate_name.replace("_", " ").title()
        print(f"  {display_name:<30} {measured_str:>12} {target_str:>12} {status_str:>8}")

    print()
    print("-" * 72)
    print("  PER-PACK BREAKDOWN:")
    print()
    for pack_name, pack_data in sorted(results["packs"].items()):
        print(f"  Pack: {pack_name}")
        print(f"    Documents:              {pack_data['total_documents']}")
        print(f"    Answerable fields:      {pack_data['answerable_fields']}")
        print(f"    Grounded answers:       {pack_data['grounded_answers']}")
        print(f"    Ungrounded renders:     {pack_data['ungrounded_render_count']}")
        print(f"    Grounded-answer rate:   {pack_data['grounded_answer_rate']}%")
        print(f"    Refusal-on-unanswerable:{pack_data['refusal_on_unanswerable']}%")
        print(f"    False-refusal rate:     {pack_data['false_refusal_rate']}%")
        print()

    print("-" * 72)
    print("  PER-DOCUMENT BREAKDOWN:")
    print()
    print(f"  {'Fixture':<30} {'Pack':<12} {'Grounded%':>10} {'Refusal%':>10} {'FalseRef%':>10} {'Unground':>8}")
    print(f"  {'-'*30} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
    for doc in results["per_document"]:
        print(
            f"  {doc['fixture_id']:<30} {doc['pack']:<12} "
            f"{doc['grounded_answer_rate']:>10} {doc['refusal_on_unanswerable']:>10} "
            f"{doc['false_refusal_rate']:>10} {doc['ungrounded_renders']:>8}"
        )
    print()
    print("=" * 72)


def write_json_report(results: dict, output_path: pathlib.Path) -> None:
    """Write machine-readable JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, sort_keys=True)
    print(f"JSON report written to {output_path}")


def write_markdown_report(results: dict, md_path: pathlib.Path) -> None:
    """Write human-readable Markdown report."""
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Kairo Phantom — Grounding Benchmark Report\n\n")
        f.write(f"> Model ID: `{results['model_id']}` | Seed: `{results['seed']}` | ")
        f.write(f"Corpus Hash: `{results['corpus_hash']}`\n\n")
        f.write(f"> Python: `{results['python_version']}` | Platform: `{results['platform']}`\n\n")

        f.write("## Release Gates\n\n")
        f.write("| Gate | Measured | Target | Status | Numerator | Denominator |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for gate_name, gate_data in results["gates"].items():
            display = gate_name.replace("_", " ").title()
            unit = gate_data["unit"]
            measured = gate_data["measured"]
            target = gate_data["target"]
            if unit == "percent":
                measured_str = f"{measured}%"
                target_str = f"<{target}%" if gate_name == "false_refusal_rate" else f"≥{target}%"
            else:
                measured_str = str(measured)
                target_str = f"={target}"
            status = "✅ PASS" if gate_data["passes"] else "❌ FAIL"
            numerator = gate_data.get("numerator", "—")
            denominator = gate_data.get("denominator", "—")
            f.write(
                f"| {display} | {measured_str} | {target_str} | {status} | "
                f"{numerator} | {denominator} |\n"
            )
        f.write("\n")

        f.write("## Per-Pack Breakdown\n\n")
        for pack_name, metrics in sorted(results["packs"].items()):
            f.write(f"### Pack: `{pack_name}`\n\n")
            f.write("| Metric | Value |\n")
            f.write("| :--- | :--- |\n")
            f.write(f"| Total Documents | {metrics['total_documents']} |\n")
            f.write(f"| Answerable Fields | {metrics['answerable_fields']} |\n")
            f.write(f"| Grounded Answers | {metrics['grounded_answers']} |\n")
            f.write(f"| Ungrounded Render Count | {metrics['ungrounded_render_count']} |\n")
            f.write(f"| Grounded-Answer Rate | {metrics['grounded_answer_rate']}% |\n")
            f.write(f"| Refusal-on-Unanswerable | {metrics['refusal_on_unanswerable']}% |\n")
            f.write(f"| False-Refusal Rate | {metrics['false_refusal_rate']}% |\n\n")

            f.write(f"#### Per-Field Accuracy ({pack_name})\n\n")
            f.write("| Field | Accuracy |\n")
            f.write("| :--- | :--- |\n")
            for field, acc in sorted(metrics["per_field_accuracy"].items()):
                f.write(f"| `{field}` | {acc * 100:.1f}% |\n")
            f.write("\n")

        f.write("## Per-Document Breakdown\n\n")
        f.write("| Fixture | Pack | Grounded% | Refusal% | FalseRef% | Ungrounded |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for doc in results["per_document"]:
            f.write(
                f"| {doc['fixture_id']} | {doc['pack']} | "
                f"{doc['grounded_answer_rate']}% | "
                f"{doc['refusal_on_unanswerable']}% | "
                f"{doc['false_refusal_rate']}% | "
                f"{doc['ungrounded_renders']} |\n"
            )
        f.write("\n")

        f.write("## Per-Document Quality Details\n\n")
        for doc in results["per_document"]:
            f.write(f"### {doc['fixture_id']} ({doc['pack']})\n\n")
            f.write("| Field | Status | Expected | Extracted | Grounded | Rendered | Method |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for fd in doc["field_details"]:
                f.write(
                    f"| {fd['field']} | {fd['status']} | "
                    f"{str(fd['expected'])[:50]} | "
                    f"{str(fd['extracted'])[:50] if fd['extracted'] else '—'} | "
                    f"{'✅' if fd['grounded'] else '❌'} | "
                    f"{'✅' if fd['rendered'] else '❌'} | "
                    f"{fd.get('method', '—')} |\n"
                )
            f.write("\n")

    print(f"Markdown report written to {md_path}")


def save_historical_run(results: dict, history_dir: pathlib.Path) -> None:
    """Save a copy of the results to bench/history/ for regression tracking.

    The filename uses the corpus hash (not timestamp) so the same corpus
    always overwrites the same history file, making regressions visible
    when the file changes.
    """
    history_dir.mkdir(parents=True, exist_ok=True)
    # Use corpus hash for deterministic filename
    hist_filename = f"bench_{results['corpus_hash'][:16]}.json"
    hist_path = history_dir / hist_filename
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, sort_keys=True)
    print(f"Historical run saved to {hist_path}")


def main():
    parser = argparse.ArgumentParser(description="Kairo Phantom Benchmark Harness")
    parser.add_argument(
        "--fixtures-dir",
        default="fixtures/invoice",
        help="Fixtures directory (for single-pack mode; default runs all packs)",
    )
    parser.add_argument(
        "--output",
        default="bench/REPORT.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--all-packs",
        action="store_true",
        default=True,
        help="Run all packs (default: true)",
    )
    parser.add_argument(
        "--single-pack",
        action="store_true",
        default=False,
        help="Run only the pack specified by --fixtures-dir",
    )
    args = parser.parse_args()

    if args.single_pack:
        # Determine pack class from fixtures dir name
        pack_map = {
            "generic": GenericPack,
            "invoice": InvoicePack,
            "paper": PaperPack,
            "contract": ContractPack,
        }
        pack_name = pathlib.Path(args.fixtures_dir).name
        pack_class = pack_map.get(pack_name, GenericPack)
        packs_config = [{"name": pack_name, "class": pack_class, "dir": args.fixtures_dir}]
    else:
        packs_config = [
            {"name": "generic", "class": GenericPack, "dir": "fixtures/generic"},
            {"name": "invoice", "class": InvoicePack, "dir": "fixtures/invoice"},
            {"name": "paper", "class": PaperPack, "dir": "fixtures/paper"},
            {"name": "contract", "class": ContractPack, "dir": "fixtures/contract"},
        ]

    results = run_benchmark(packs_config)

    # Print the gates table to stdout
    print_gates_table(results)

    # Write JSON report
    output_path = pathlib.Path(args.output)
    write_json_report(results, output_path)

    # Write Markdown report
    md_path = output_path.with_suffix(".md")
    write_markdown_report(results, md_path)

    # Save historical run
    history_dir = pathlib.Path("bench/history")
    save_historical_run(results, history_dir)

    # Print gate status summary (do NOT exit non-zero — make bench must
    # always produce output for determinism checks; gate pass/fail is
    # reported in the output, not the exit code. A separate CI check
    # can parse the JSON for gate validation.)
    all_pass = all(g["passes"] for g in results["gates"].values())
    if not all_pass:
        print("\n⚠  One or more release gates FAILED — see measured values above.")
        print("   (make bench always exits 0; gate status is in bench/REPORT.json)")
    else:
        print("\n✅  All release gates PASS.")


if __name__ == "__main__":
    main()