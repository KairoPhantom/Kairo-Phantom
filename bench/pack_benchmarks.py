"""
Kairo Phantom — Pack-Specific Benchmarks (P2.2)

Runs pack-specific benchmarks with hard cases:
- Invoice Pack: merged-cell totals, partially-scanned invoices
- Contract Pack: cross-referenced clauses, exhibits
- Paper Pack: figure-caption-only facts

Reports false-refusal specifically on key questions for each pack.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from datetime import datetime, timezone

# Ensure repo root is on path
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


def _run_pack_on_fixtures(
    pack_name: str,
    pack_class,
    fixtures_dir: pathlib.Path,
    hard_case_dirs: list[pathlib.Path] | None = None,
) -> dict:
    """Run a pack on its base fixtures + hard-case fixtures, return metrics."""
    os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"

    pack = pack_class()
    verifier = GroundingVerifierImpl()

    # Collect all fixture sources
    sources = []
    base_gt = fixtures_dir / "ground_truth.json"
    if base_gt.exists():
        sources.append(("base", base_gt))

    if hard_case_dirs:
        for hd in hard_case_dirs:
            gt = hd / "ground_truth.json"
            if gt.exists():
                sources.append((hd.name, gt))

    total_answerable = 0
    total_grounded = 0
    total_false_refusals = 0
    total_correct_refusals = 0
    total_unanswerable = 0
    total_ungrounded_renders = 0
    per_document = []
    hard_case_results = {}

    for source_label, gt_file in sources:
        gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
        fixtures = gt_data.get("fixtures", [])
        if not fixtures:
            continue

        # Setup orchestrator per source
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

        source_answerable = 0
        source_grounded = 0
        source_false_refusals = 0
        source_correct_refusals = 0
        source_unanswerable = 0
        source_ungrounded = 0

        for fixture in fixtures:
            file_path = gt_file.parent / fixture["file"]
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
            field_details = []

            for field in pack.fields:
                expected_val = ground_truth.get(field)
                ext = ext_by_field.get(field)

                is_unanswerable = expected_val is None or expected_val == ""
                if is_unanswerable:
                    doc_unanswerable += 1
                    if not ext or quality_gate.check(ext).verdict == GateVerdict.BLOCK:
                        doc_correct_refusals += 1
                        field_details.append({
                            "field": field,
                            "status": "correct_refusal",
                            "grounded": False,
                            "rendered": False,
                        })
                    else:
                        # Produced an answer for an unanswerable question
                        doc_ungrounded += 1
                        field_details.append({
                            "field": field,
                            "status": "ungrounded_render",
                            "grounded": False,
                            "rendered": True,
                        })
                else:
                    doc_answerable += 1
                    if ext:
                        gate_res = quality_gate.check(ext)
                        if gate_res.verdict != GateVerdict.BLOCK:
                            # Check grounding
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
                                field_details.append({
                                    "field": field,
                                    "status": "grounded",
                                    "grounded": True,
                                    "rendered": True,
                                    "method": method.value if method else "unknown",
                                })
                            else:
                                doc_false_refusals += 1
                                field_details.append({
                                    "field": field,
                                    "status": "false_refusal",
                                    "grounded": False,
                                    "rendered": False,
                                })
                        else:
                            doc_false_refusals += 1
                            field_details.append({
                                "field": field,
                                "status": "false_refusal",
                                "grounded": False,
                                "rendered": False,
                            })
                    else:
                        doc_false_refusals += 1
                        field_details.append({
                            "field": field,
                            "status": "false_refusal",
                            "grounded": False,
                            "rendered": False,
                        })

            source_answerable += doc_answerable
            source_grounded += doc_grounded
            source_false_refusals += doc_false_refusals
            source_correct_refusals += doc_correct_refusals
            source_unanswerable += doc_unanswerable
            source_ungrounded += doc_ungrounded

            per_document.append({
                "fixture_id": fixture["fixture_id"],
                "file": fixture["file"],
                "pack": pack_name,
                "source": source_label,
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
                "field_details": field_details,
            })

        # Record hard-case specific results
        if source_label != "base":
            hard_case_results[source_label] = {
                "answerable_fields": source_answerable,
                "grounded_answers": source_grounded,
                "false_refusals": source_false_refusals,
                "false_refusal_rate": round(
                    source_false_refusals / source_answerable * 100.0, 2
                ) if source_answerable > 0 else 0.0,
                "grounded_answer_rate": round(
                    source_grounded / source_answerable * 100.0, 2
                ) if source_answerable > 0 else 100.0,
            }

        total_answerable += source_answerable
        total_grounded += source_grounded
        total_false_refusals += source_false_refusals
        total_correct_refusals += source_correct_refusals
        total_unanswerable += source_unanswerable
        total_ungrounded_renders += source_ungrounded

    return {
        "pack": pack_name,
        "total_documents": len(per_document),
        "total_answerable": total_answerable,
        "grounded_answers": total_grounded,
        "false_refusals": total_false_refusals,
        "correct_refusals": total_correct_refusals,
        "unanswerable_fields": total_unanswerable,
        "ungrounded_renders": total_ungrounded_renders,
        "grounded_answer_rate": round(
            total_grounded / total_answerable * 100.0, 2
        ) if total_answerable > 0 else 100.0,
        "false_refusal_rate": round(
            total_false_refusals / total_answerable * 100.0, 2
        ) if total_answerable > 0 else 0.0,
        "refusal_correctness": round(
            total_correct_refusals / total_unanswerable * 100.0, 2
        ) if total_unanswerable > 0 else 100.0,
        "hard_cases": hard_case_results,
        "per_document": per_document,
    }


def run_pack_benchmarks() -> dict:
    """Run all pack-specific benchmarks and return the full report."""
    fixtures_base = REPO_ROOT / "fixtures"

    pack_configs = [
        {
            "name": "invoice",
            "class": InvoicePack,
            "base_dir": fixtures_base / "invoice",
            "hard_dirs": [
                fixtures_base / "invoice" / "merged_cells",
                fixtures_base / "invoice" / "partially_scanned",
            ],
        },
        {
            "name": "contract",
            "class": ContractPack,
            "base_dir": fixtures_base / "contract",
            "hard_dirs": [
                fixtures_base / "contract" / "cross_refs",
            ],
        },
        {
            "name": "paper",
            "class": PaperPack,
            "base_dir": fixtures_base / "paper",
            "hard_dirs": [
                fixtures_base / "paper" / "figure_captions",
            ],
        },
        {
            "name": "generic",
            "class": GenericPack,
            "base_dir": fixtures_base / "generic",
            "hard_dirs": [],
        },
    ]

    results = {}
    for config in pack_configs:
        print(f"Running pack benchmark: {config['name']} ...")
        result = _run_pack_on_fixtures(
            pack_name=config["name"],
            pack_class=config["class"],
            fixtures_dir=config["base_dir"],
            hard_case_dirs=config["hard_dirs"],
        )
        results[config["name"]] = result

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "packs": results,
    }

    # Write JSON report
    output_path = REPO_ROOT / "bench" / "PACK_BENCHMARK_REPORT.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"JSON report written to {output_path}")

    # Write Markdown report
    md_path = output_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Kairo Phantom — Pack-Specific Benchmark Report\n\n")
        f.write(f"> Generated: {report['timestamp']}\n\n")

        for pack_name, metrics in results.items():
            f.write(f"## Pack: `{pack_name}`\n\n")
            f.write("| Metric | Value | Target |\n")
            f.write("| :--- | :--- | :--- |\n")
            f.write(f"| Grounded-Answer Rate | {metrics['grounded_answer_rate']}% | ≥95% |\n")
            f.write(f"| False-Refusal Rate | {metrics['false_refusal_rate']}% | <5% |\n")
            f.write(f"| Refusal-Correctness | {metrics['refusal_correctness']}% | 100% |\n")
            f.write(f"| Ungrounded Renders | {metrics['ungrounded_renders']} | 0 |\n\n")

            if metrics["hard_cases"]:
                f.write(f"### Hard Cases ({pack_name})\n\n")
                f.write("| Case | Answerable | Grounded | False Refusals | False-Refusal Rate |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- |\n")
                for case_name, case_metrics in metrics["hard_cases"].items():
                    f.write(
                        f"| {case_name} | {case_metrics['answerable_fields']} | "
                        f"{case_metrics['grounded_answers']} | "
                        f"{case_metrics['false_refusals']} | "
                        f"{case_metrics['false_refusal_rate']}% |\n"
                    )
                f.write("\n")

            f.write(f"### Per-Document ({pack_name})\n\n")
            f.write("| Fixture | Source | Answerable | Grounded | False Refusals | FR Rate |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for doc in metrics["per_document"]:
                f.write(
                    f"| {doc['fixture_id']} | {doc['source']} | "
                    f"{doc['answerable_fields']} | {doc['grounded_answers']} | "
                    f"{doc['false_refusals']} | {doc['false_refusal_rate']}% |\n"
                )
            f.write("\n")

    print(f"Markdown report written to {md_path}")
    return report


if __name__ == "__main__":
    run_pack_benchmarks()
