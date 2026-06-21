"""
Test: running bench twice yields byte-identical metric values for the four gates.

This test is failing-capable: if any of the four gate metrics changes
between two runs on the same machine, the test goes RED.

Determinism is the core requirement — the same corpus + same model + same
seed must always produce the same numbers.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

GATE_NAMES = [
    "grounded_answer_rate",
    "refusal_on_unanswerable",
    "false_refusal_rate",
    "ungrounded_render_count",
]


def _run_bench_and_get_results() -> dict:
    """Run the bench harness and return the parsed JSON results."""
    output_path = REPO_ROOT / "bench" / "REPORT.json"
    result = subprocess.run(
        [sys.executable, "-m", "bench.harness", "--output", str(output_path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert output_path.exists(), (
        f"bench/REPORT.json was not produced.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    with open(output_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_gate_metrics(results: dict) -> dict:
    """Extract the four gate measured values as comparable primitives."""
    gates = results["gates"]
    metrics = {}
    for gate_name in GATE_NAMES:
        gate = gates[gate_name]
        metrics[gate_name] = {
            "measured": gate["measured"],
            "target": gate["target"],
            "passes": gate["passes"],
            "numerator": gate.get("numerator"),
            "denominator": gate.get("denominator"),
        }
    return metrics


def test_gate_metrics_identical_across_two_runs():
    """Running bench twice must yield identical gate metric values."""
    results1 = _run_bench_and_get_results()
    metrics1 = _extract_gate_metrics(results1)

    results2 = _run_bench_and_get_results()
    metrics2 = _extract_gate_metrics(results2)

    for gate_name in GATE_NAMES:
        m1 = metrics1[gate_name]
        m2 = metrics2[gate_name]
        assert m1["measured"] == m2["measured"], (
            f"Gate '{gate_name}' measured value differs between runs!\n"
            f"Run 1: {m1['measured']}\n"
            f"Run 2: {m2['measured']}"
        )
        assert m1["numerator"] == m2["numerator"], (
            f"Gate '{gate_name}' numerator differs between runs!\n"
            f"Run 1: {m1['numerator']}\n"
            f"Run 2: {m2['numerator']}"
        )
        assert m1["denominator"] == m2["denominator"], (
            f"Gate '{gate_name}' denominator differs between runs!\n"
            f"Run 1: {m1['denominator']}\n"
            f"Run 2: {m2['denominator']}"
        )
        assert m1["passes"] == m2["passes"], (
            f"Gate '{gate_name}' passes flag differs between runs!\n"
            f"Run 1: {m1['passes']}\n"
            f"Run 2: {m2['passes']}"
        )


def test_corpus_hash_identical_across_two_runs():
    """The corpus hash must be identical across two runs."""
    results1 = _run_bench_and_get_results()
    results2 = _run_bench_and_get_results()
    assert results1["corpus_hash"] == results2["corpus_hash"], (
        f"Corpus hash differs between runs!\n"
        f"Run 1: {results1['corpus_hash']}\n"
        f"Run 2: {results2['corpus_hash']}"
    )


def test_model_id_identical_across_two_runs():
    """The model ID must be identical across two runs."""
    results1 = _run_bench_and_get_results()
    results2 = _run_bench_and_get_results()
    assert results1["model_id"] == results2["model_id"], (
        f"Model ID differs between runs!\n"
        f"Run 1: {results1['model_id']}\n"
        f"Run 2: {results2['model_id']}"
    )


def test_per_document_metrics_identical_across_two_runs():
    """Per-document metrics must be identical across two runs."""
    results1 = _run_bench_and_get_results()
    results2 = _run_bench_and_get_results()

    docs1 = {d["fixture_id"]: d for d in results1["per_document"]}
    docs2 = {d["fixture_id"]: d for d in results2["per_document"]}

    assert set(docs1.keys()) == set(docs2.keys()), (
        f"Document sets differ between runs!\n"
        f"Run 1: {set(docs1.keys())}\n"
        f"Run 2: {set(docs2.keys())}"
    )

    for fixture_id in docs1:
        d1 = docs1[fixture_id]
        d2 = docs2[fixture_id]
        assert d1["grounded_answer_rate"] == d2["grounded_answer_rate"], (
            f"Document {fixture_id}: grounded_answer_rate differs!\n"
            f"Run 1: {d1['grounded_answer_rate']}\n"
            f"Run 2: {d2['grounded_answer_rate']}"
        )
        assert d1["refusal_on_unanswerable"] == d2["refusal_on_unanswerable"], (
            f"Document {fixture_id}: refusal_on_unanswerable differs!"
        )
        assert d1["false_refusal_rate"] == d2["false_refusal_rate"], (
            f"Document {fixture_id}: false_refusal_rate differs!"
        )
        assert d1["ungrounded_renders"] == d2["ungrounded_renders"], (
            f"Document {fixture_id}: ungrounded_renders differs!"
        )


def test_per_pack_metrics_identical_across_two_runs():
    """Per-pack metrics must be identical across two runs."""
    results1 = _run_bench_and_get_results()
    results2 = _run_bench_and_get_results()

    packs1 = results1["packs"]
    packs2 = results2["packs"]

    assert set(packs1.keys()) == set(packs2.keys()), (
        f"Pack sets differ between runs!\n"
        f"Run 1: {set(packs1.keys())}\n"
        f"Run 2: {set(packs2.keys())}"
    )

    for pack_name in packs1:
        p1 = packs1[pack_name]
        p2 = packs2[pack_name]
        for metric in ["grounded_answer_rate", "refusal_on_unanswerable",
                       "false_refusal_rate", "ungrounded_render_count"]:
            assert p1[metric] == p2[metric], (
                f"Pack {pack_name}: {metric} differs!\n"
                f"Run 1: {p1[metric]}\n"
                f"Run 2: {p2[metric]}"
            )


def test_json_output_byte_identical_gate_section():
    """The gates section of the JSON must be byte-identical across two runs.

    We compare the serialized JSON of just the gates section to ensure
    no floating-point drift or ordering changes.
    """
    results1 = _run_bench_and_get_results()
    results2 = _run_bench_and_get_results()

    gates1_json = json.dumps(results1["gates"], sort_keys=True)
    gates2_json = json.dumps(results2["gates"], sort_keys=True)

    assert gates1_json == gates2_json, (
        f"Gates JSON differs between runs!\n"
        f"Run 1: {gates1_json}\n"
        f"Run 2: {gates2_json}"
    )