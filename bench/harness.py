"""
Kairo Phantom — Comprehensive Grounding Benchmark Harness (SPEC §S8, §S9)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
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


def main():
    packs_config = [
        {"name": "generic", "class": GenericPack, "dir": "fixtures/generic"},
        {"name": "invoice", "class": InvoicePack, "dir": "fixtures/invoice"},
        {"name": "paper", "class": PaperPack, "dir": "fixtures/paper"},
        {"name": "contract", "class": ContractPack, "dir": "fixtures/contract"},
    ]

    results = {}
    verifier = GroundingVerifierImpl()

    # Enable test mode for deterministic gateway response
    os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"

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

        total_extractions = 0
        passed_extractions = 0
        hallucinated_citations = 0
        total_citations = 0

        correct_refusals = 0
        total_unanswerable = 0

        for fixture in fixtures:
            file_path = fixtures_path / fixture["file"]
            if not file_path.exists():
                continue

            doc = Document(source_path=str(file_path))
            trace = orchestrator.run(doc)

            # Map trace extractions by field
            ext_by_field = {e.field_name: e for e in trace.extractions}
            ground_truth = fixture["ground_truth"]

            # Refusal analysis: check every field in pack schema
            for field in pack.fields:
                expected_val = ground_truth.get(field)
                ext = ext_by_field.get(field)

                is_unanswerable = (expected_val is None or expected_val == "")
                if is_unanswerable:
                    total_unanswerable += 1
                    # A correct refusal means no extraction passed quality gate
                    if not ext or quality_gate.check(ext).verdict == GateVerdict.BLOCK:
                        correct_refusals += 1

            for ext in trace.extractions:
                total_extractions += 1
                gate_res = quality_gate.check(ext)
                if gate_res.verdict != GateVerdict.BLOCK:
                    passed_extractions += 1

                    # Check citations (FACTUM-style)
                    for anchor in ext.anchors:
                        total_citations += 1
                        chunk = memory_store.get_chunk(anchor.chunk_id)
                        if not chunk:
                            hallucinated_citations += 1
                            continue

                        # Verify target actually appears in chunk text
                        method, verification_anchors = verifier.verify(ext.value, ext.source_span, [chunk])
                        if method == GroundingMethod.BLOCK:
                            hallucinated_citations += 1

        # Calculate metrics
        grounded_answer_rate = (passed_extractions / total_extractions * 100.0) if total_extractions else 100.0
        citation_hallucination_rate = (hallucinated_citations / total_citations * 100.0) if total_citations else 0.0
        refusal_correctness = (correct_refusals / total_unanswerable * 100.0) if total_unanswerable else 100.0

        results[pack_name] = {
            "total_documents": len(fixtures),
            "total_extractions": total_extractions,
            "passed_extractions": passed_extractions,
            "grounded_answer_rate": round(grounded_answer_rate, 2),
            "citation_hallucination_rate": round(citation_hallucination_rate, 2),
            "refusal_correctness": round(refusal_correctness, 2),
            "per_field_accuracy": {k: round(v, 4) for k, v in per_field_accuracy.items()},
        }

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "packs": results,
    }

    # Write JSON report
    output_path = pathlib.Path("bench/REPORT.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"JSON report written to {output_path}")

    # Write Markdown report
    md_path = output_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Kairo Phantom — Grounding Benchmark Report\n\n")
        f.write(f"> Generated: {report['timestamp']}\n\n")

        for pack_name, metrics in results.items():
            f.write(f"## Pack: `{pack_name}`\n\n")
            f.write(f"| Metric | Value | Target |\n")
            f.write(f"| :--- | :--- | :--- |\n")
            f.write(f"| Grounded-Answer Rate | {metrics['grounded_answer_rate']}% | ≥95% |\n")
            f.write(f"| Citation-Hallucination Rate | {metrics['citation_hallucination_rate']}% | 0.0% |\n")
            f.write(f"| Refusal-Correctness | {metrics['refusal_correctness']}% | 100% |\n\n")

            f.write(f"### Per-Field Accuracy ({pack_name})\n\n")
            f.write(f"| Field | Accuracy |\n")
            f.write(f"| :--- | :--- |\n")
            for field, acc in sorted(metrics["per_field_accuracy"].items()):
                f.write(f"| `{field}` | {acc * 100:.1f}% |\n")
            f.write("\n")

    print(f"Markdown report written to {md_path}")


if __name__ == "__main__":
    main()
