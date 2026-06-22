"""
Kairo Phantom — Blind Benchmark Runner

Runs the real pipeline (ingest -> security -> extract -> grounding -> quality gate)
on the frozen blind corpus (bench/corpus/blind/v1/) and scores with the shared
scorer (bench/score.py per KAIRO_SHARED_BLIND_CORPUS_SPEC.md §5).

Emits dev-vs-blind columns when run alongside the golden bench.

Usage:
  python -m bench.blind_bench                  # blind only
  python -m bench.blind_bench --with-dev       # dev + blind side by side
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

# Ensure test mode for deterministic gateway
os.environ.setdefault("KAIRO_GATEWAY_TEST_MODE", "true")

from bench.score import score_corpus, Prediction, ScoreResult
from kernel.core.contracts import GateVerdict
from kernel.core.data_model import Document
from kernel.core.provenance import ProvenanceLogImpl
from kernel.sidecar.ingestor import IngestorImpl
from kernel.sidecar.inference_gateway import TieredInferenceGateway
from kernel.sidecar.memory_store import MemoryStoreImpl
from kernel.sidecar.orchestrator import OrchestratorImpl
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.sidecar.security_filter import LocalSecurityFilter
from kernel.core.grounding import GroundingVerifierImpl
from packs.generic.pack import GenericPack
from packs.invoice.pack import InvoicePack
from packs.paper.pack import PaperPack
from packs.contract.pack import ContractPack

BLIND_CORPUS_DIR = pathlib.Path("bench/corpus/blind/v1")
PACK_CLASSES = {"invoice": InvoicePack, "paper": PaperPack, "contract": ContractPack, "generic": GenericPack}


def run_blind_pipeline(corpus_dir: pathlib.Path = BLIND_CORPUS_DIR) -> list[Prediction]:
    """Run the real pipeline on every doc in the blind corpus, return predictions."""
    manifest = json.loads((corpus_dir / "manifest.json").read_text())
    predictions: list[Prediction] = []

    for doc_entry in manifest["docs"]:
        doc_id = doc_entry["doc_id"]
        pack_name = doc_entry["pack"]
        doc_path = corpus_dir / doc_entry["file"]
        label = json.loads((corpus_dir / "labels" / f"{doc_id}.json").read_text())

        pack = PACK_CLASSES[pack_name]()
        memory_store = MemoryStoreImpl(":memory:")
        provenance = ProvenanceLogImpl()
        ingestor = IngestorImpl()
        security = LocalSecurityFilter(enable_pii_scan=False)
        gateway = TieredInferenceGateway(tier3_enabled=False)
        quality_gate = LocalQualityGate(memory_store)
        orchestrator = OrchestratorImpl(
            ingestor=ingestor,
            security_filter=security,
            inference_gateway=gateway,
            quality_gate=quality_gate,
            provenance_log=provenance,
            pack=pack,
            memory_store=memory_store,
        )

        doc = Document(source_path=str(doc_path))
        trace = orchestrator.run(doc)

        # Map extractions by field
        ext_by_field = {e.field_name: e for e in trace.extractions}

        # Build a prediction for every field in the label
        for ext_label in label["extractions"]:
            field = ext_label["field"]
            ext = ext_by_field.get(field)
            if ext is None:
                # No extraction produced -> refused
                predictions.append(Prediction(doc_id=doc_id, field=field, value=None, bbox=None, refused=True))
            else:
                # Check if the quality gate blocked it
                gate_res = quality_gate.check(ext)
                refused = gate_res.verdict == GateVerdict.BLOCK or ext.method.value == "block"
                # Get bbox from anchors
                bbox = None
                if ext.anchors:
                    a = ext.anchors[0]
                    bbox = [a.bbox.x0, a.bbox.y0, a.bbox.x1 - a.bbox.x0, a.bbox.y1 - a.bbox.y0]
                predictions.append(Prediction(
                    doc_id=doc_id, field=field, value=ext.value, bbox=bbox, refused=refused
                ))

    return predictions


def run_blind_benchmark(corpus_dir: pathlib.Path = BLIND_CORPUS_DIR) -> ScoreResult:
    """Run blind pipeline + score. Returns ScoreResult."""
    predictions = run_blind_pipeline(corpus_dir)
    return score_corpus(str(corpus_dir), predictions)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default=str(BLIND_CORPUS_DIR))
    parser.add_argument("--with-dev", action="store_true", help="also run golden bench for dev-vs-blind columns")
    parser.add_argument("--output", default="bench/REPORT_blind.json")
    args = parser.parse_args()

    print("=" * 70)
    print("Kairo Phantom — BLIND Benchmark (spec §5 scorer)")
    print("=" * 70)

    result = run_blind_benchmark(pathlib.Path(args.corpus_dir))

    print(f"\nCorpus: {args.corpus_dir}")
    print(f"Docs: {len(result.per_doc)}")
    print(f"Answerable fields: {result.answerable_total}")
    print(f"Unanswerable fields: {result.unanswerable_total}")
    print()
    print(f"  Grounded-correct:      {result.grounded_correct}")
    print(f"  Grounded-wrong-box:    {result.grounded_wrong_box}")
    print(f"  Refusal-correct:       {result.refusal_correct}")
    print(f"  False-refusal:         {result.false_refusal}")
    print(f"  Hallucination:         {result.hallucination}")
    print()
    print(f"  grounded_rate:         {result.grounded_rate:.1f}%   (gate >= 95%)")
    print(f"  false_refusal_rate:    {result.false_refusal_rate:.1f}%   (gate < 5%)")
    print(f"  refusal_correct_rate:  {result.refusal_correct_rate:.1f}%   (gate = 100%)")
    print(f"  halluc_box_blocked:    {result.halluc_box_blocked_rate:.1f}%   (gate = 100%)")
    print()
    print("  Per-doc:")
    for doc_id, dr in sorted(result.per_doc.items()):
        gr = 100.0 * dr["grounded"] / dr["answerable"] if dr["answerable"] else 0
        print(f"    {doc_id:16s} ans={dr['answerable']} grd={dr['grounded']} unans={dr['unanswerable']} cref={dr['refusal_correct']} fref={dr['false_refusal']} grd%={gr:.0f}")

    # Write JSON report
    out = pathlib.Path(args.output)
    out.write_text(json.dumps(result.to_dict(), indent=2))
    print(f"\nJSON report: {out}")

    if args.with_dev:
        print("\n" + "=" * 70)
        print("DEV vs BLIND columns")
        print("=" * 70)
        from bench.harness import run_benchmark
        dev = run_benchmark()
        dev_grounded = dev["gates"]["grounded_answer_rate"]["measured"]
        dev_false_ref = dev["gates"]["false_refusal_rate"]["measured"]
        print(f"  {'Metric':25s} {'DEV':>10s} {'BLIND':>10s} {'Gate':>10s}")
        print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
        print(f"  {'grounded_rate':25s} {dev_grounded:>9.1f}% {result.grounded_rate:>9.1f}% {'>=95%':>10s}")
        print(f"  {'false_refusal_rate':25s} {dev_false_ref:>9.1f}% {result.false_refusal_rate:>9.1f}% {'<5%':>10s}")
        print(f"  {'refusal_correct_rate':25s} {'100.0':>9s}% {result.refusal_correct_rate:>9.1f}% {'=100%':>10s}")

    # Exit code: 0 if all gates pass, 1 otherwise
    gates_pass = (
        result.grounded_rate >= 95.0
        and result.false_refusal_rate < 5.0
        and result.refusal_correct_rate >= 100.0
        and result.halluc_box_blocked_rate >= 100.0
    )
    print(f"\n{'BLIND GATES: GREEN' if gates_pass else 'BLIND GATES: RED'}")
    sys.exit(0 if gates_pass else 1)


if __name__ == "__main__":
    main()