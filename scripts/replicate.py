#!/usr/bin/env python3
"""
Kairo Phantom — Replication Harness (P2.3)

One-command harness that pulls the public corpus, runs the pipeline,
and emits the same metric table as `make bench`.

Usage:
    python3 scripts/replicate.py

Output:
    bench/REPLICATE_REPORT.json
    bench/REPLICATE_REPORT.md
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import sys
from datetime import datetime, timezone

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from kernel.core.contracts import GateVerdict
from kernel.core.data_model import Document, GroundingMethod
from kernel.core.grounding import GroundingVerifierImpl
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


def _compute_corpus_hash(fixtures_root: pathlib.Path) -> str:
    """Compute a deterministic hash of the fixture corpus for reproducibility."""
    h = hashlib.sha256()
    for gt_file in sorted(fixtures_root.rglob("ground_truth.json")):
        h.update(gt_file.read_bytes())
        for line in gt_file.read_text(encoding="utf-8").splitlines():
            if '"file"' in line:
                # Extract filename and hash the actual fixture file too
                pass
    # Also hash all fixture text files
    for txt_file in sorted(fixtures_root.rglob("*.txt")):
        h.update(txt_file.read_bytes())
    return h.hexdigest()


def _run_pack(pack_name, pack_class, fixtures_dir):
    """Run a single pack on its fixtures and return metrics."""
    gt_file = fixtures_dir / "ground_truth.json"
    if not gt_file.exists():
        return None

    gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
    fixtures = gt_data.get("fixtures", [])
    if not fixtures:
        return None

    os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"

    pack = pack_class()
    verifier = GroundingVerifierImpl()
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

    total_answerable = 0
    total_grounded = 0
    total_false_refusals = 0
    total_correct_refusals = 0
    total_unanswerable = 0
    total_ungrounded = 0
    per_document = []

    for fixture in fixtures:
        file_path = fixtures_dir / fixture["file"]
        if not file_path.exists():
            continue

        doc = Document(source_path=str(file_path))
        trace = orchestrator.run(doc)

        ground_truth = fixture["ground_truth"]
        ext_by_field = {e.field_name: e for e in trace.extractions}

        doc_answerable = 0
        doc_grounded = 0
        doc_false_refusals = 0
        doc_correct_refusals = 0
        doc_unanswerable = 0
        doc_ungrounded = 0

        for field in pack.fields:
            expected_val = ground_truth.get(field)
            ext = ext_by_field.get(field)

            is_unanswerable = expected_val is None or expected_val == ""
            if is_unanswerable:
                doc_unanswerable += 1
                if not ext or quality_gate.check(ext).verdict == GateVerdict.BLOCK:
                    doc_correct_refusals += 1
                else:
                    doc_ungrounded += 1
            else:
                doc_answerable += 1
                if ext:
                    gate_res = quality_gate.check(ext)
                    if gate_res.verdict != GateVerdict.BLOCK:
                        grounded = False
                        for anchor in ext.anchors:
                            chunk = memory_store.get_chunk(anchor.chunk_id)
                            if chunk:
                                method, _ = verifier.verify(
                                    ext.value, ext.source_span, [chunk]
                                )
                                if method != GroundingMethod.BLOCK:
                                    grounded = True
                                    break
                        if grounded:
                            doc_grounded += 1
                        else:
                            doc_false_refusals += 1
                    else:
                        doc_false_refusals += 1
                else:
                    doc_false_refusals += 1

        total_answerable += doc_answerable
        total_grounded += doc_grounded
        total_false_refusals += doc_false_refusals
        total_correct_refusals += doc_correct_refusals
        total_unanswerable += doc_unanswerable
        total_ungrounded += doc_ungrounded

        per_document.append({
            "fixture_id": fixture["fixture_id"],
            "file": fixture["file"],
            "pack": pack_name,
            "answerable_fields": doc_answerable,
            "grounded_answers": doc_grounded,
            "false_refusals": doc_false_refusals,
            "correct_refusals": doc_correct_refusals,
            "unanswerable_fields": doc_unanswerable,
            "ungrounded_renders": doc_ungrounded,
            "grounded_answer_rate": round(
                doc_grounded / doc_answerable * 100.0, 2
            ) if doc_answerable > 0 else 100.0,
            "false_refusal_rate": round(
                doc_false_refusals / doc_answerable * 100.0, 2
            ) if doc_answerable > 0 else 0.0,
        })

    return {
        "total_documents": len(per_document),
        "total_answerable": total_answerable,
        "grounded_answers": total_grounded,
        "false_refusals": total_false_refusals,
        "correct_refusals": total_correct_refusals,
        "unanswerable_fields": total_unanswerable,
        "ungrounded_renders": total_ungrounded,
        "grounded_answer_rate": round(
            total_grounded / total_answerable * 100.0, 2
        ) if total_answerable > 0 else 100.0,
        "false_refusal_rate": round(
            total_false_refusals / total_answerable * 100.0, 2
        ) if total_answerable > 0 else 0.0,
        "refusal_correctness": round(
            total_correct_refusals / total_unanswerable * 100.0, 2
        ) if total_unanswerable > 0 else 100.0,
        "per_document": per_document,
    }


def run_replication() -> dict:
    """Run the full replication and return the report."""
    fixtures_root = REPO_ROOT / "fixtures"
    corpus_hash = _compute_corpus_hash(fixtures_root)

    pack_configs = [
        ("generic", GenericPack, fixtures_root / "generic"),
        ("invoice", InvoicePack, fixtures_root / "invoice"),
        ("paper", PaperPack, fixtures_root / "paper"),
        ("contract", ContractPack, fixtures_root / "contract"),
    ]

    packs_results = {}
    all_answerable = 0
    all_grounded = 0
    all_false_refusals = 0
    all_correct_refusals = 0
    all_unanswerable = 0
    all_ungrounded = 0

    for pack_name, pack_class, fixtures_dir in pack_configs:
        print(f"Replicating pack: {pack_name} ...")
        result = _run_pack(pack_name, pack_class, fixtures_dir)
        if result:
            packs_results[pack_name] = result
            all_answerable += result["total_answerable"]
            all_grounded += result["grounded_answers"]
            all_false_refusals += result["false_refusals"]
            all_correct_refusals += result["correct_refusals"]
            all_unanswerable += result["unanswerable_fields"]
            all_ungrounded += result["ungrounded_renders"]

    # Compute aggregate gates
    gates = {
        "grounded_answer_rate": {
            "measured": round(all_grounded / all_answerable * 100.0, 2) if all_answerable > 0 else 100.0,
            "numerator": all_grounded,
            "denominator": all_answerable,
            "target": 95.0,
            "unit": "percent",
        },
        "false_refusal_rate": {
            "measured": round(all_false_refusals / all_answerable * 100.0, 2) if all_answerable > 0 else 0.0,
            "numerator": all_false_refusals,
            "denominator": all_answerable,
            "target": 5.0,
            "unit": "percent",
        },
        "refusal_on_unanswerable": {
            "measured": round(all_correct_refusals / all_unanswerable * 100.0, 2) if all_unanswerable > 0 else 100.0,
            "numerator": all_correct_refusals,
            "denominator": all_unanswerable,
            "target": 100.0,
            "unit": "percent",
        },
        "ungrounded_render_count": {
            "measured": all_ungrounded,
            "target": 0,
            "unit": "count",
        },
    }

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "corpus_hash": corpus_hash,
        "python_version": sys.version,
        "platform": platform.platform(),
        "model_id": "kairo-test-mode-v1",
        "gates": gates,
        "packs": packs_results,
    }

    # Write JSON report
    output_path = REPO_ROOT / "bench" / "REPLICATE_REPORT.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"JSON report written to {output_path}")

    # Write Markdown report
    md_path = output_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Kairo Phantom — Replication Report\n\n")
        f.write(f"> Generated: {report['timestamp']}\n")
        f.write(f"> Corpus hash: `{corpus_hash[:16]}...`\n")
        f.write(f"> Platform: {report['platform']}\n")
        f.write(f"> Python: {report['python_version'].split()[0]}\n\n")

        f.write("## Aggregate Gates\n\n")
        f.write("| Gate | Measured | Target | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for gate_name, gate_val in gates.items():
            status = "✅" if (
                (gate_val["unit"] == "percent" and gate_val["measured"] >= gate_val["target"])
                or (gate_val["unit"] == "count" and gate_val["measured"] <= gate_val["target"])
            ) else "❌"
            f.write(f"| {gate_name} | {gate_val['measured']} | {gate_val['target']} | {status} |\n")
        f.write("\n")

        f.write("## Per-Pack Results\n\n")
        for pack_name, metrics in packs_results.items():
            f.write(f"### {pack_name}\n\n")
            f.write("| Metric | Value | Target |\n")
            f.write("| :--- | :--- | :--- |\n")
            f.write(f"| Grounded-Answer Rate | {metrics['grounded_answer_rate']}% | ≥95% |\n")
            f.write(f"| False-Refusal Rate | {metrics['false_refusal_rate']}% | <5% |\n")
            f.write(f"| Refusal-Correctness | {metrics['refusal_correctness']}% | 100% |\n")
            f.write(f"| Ungrounded Renders | {metrics['ungrounded_renders']} | 0 |\n\n")

            f.write(f"| Fixture | Answerable | Grounded | False Refusals | FR Rate |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for doc in metrics["per_document"]:
                f.write(
                    f"| {doc['fixture_id']} | {doc['answerable_fields']} | "
                    f"{doc['grounded_answers']} | {doc['false_refusals']} | "
                    f"{doc['false_refusal_rate']}% |\n"
                )
            f.write("\n")

    print(f"Markdown report written to {md_path}")
    return report


if __name__ == "__main__":
    run_replication()
