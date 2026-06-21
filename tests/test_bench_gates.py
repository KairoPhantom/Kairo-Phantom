"""
Test: bench output contains all four release-gate metrics with proper field names.

This test is failing-capable: if any gate metric is missing or renamed,
the test goes RED.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

REQUIRED_GATE_NAMES = [
    "grounded_answer_rate",
    "refusal_on_unanswerable",
    "false_refusal_rate",
    "ungrounded_render_count",
]

REQUIRED_GATE_FIELDS = ["measured", "target", "unit", "passes"]


def _run_bench_and_load_results() -> dict:
    """Run the bench harness and load the JSON output."""
    output_path = REPO_ROOT / "bench" / "REPORT.json"
    result = subprocess.run(
        [sys.executable, "-m", "bench.harness", "--output", str(output_path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    # Bench may exit 1 if gates fail — that's fine, we still check the output
    assert output_path.exists(), (
        f"bench/REPORT.json was not produced. stderr:\n{result.stderr}"
    )
    with open(output_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_bench_output_has_all_four_gates():
    """The bench JSON must contain exactly the four required gate metrics."""
    results = _run_bench_and_load_results()
    assert "gates" in results, "Results dict missing 'gates' key"
    gates = results["gates"]
    for gate_name in REQUIRED_GATE_NAMES:
        assert gate_name in gates, (
            f"Gate '{gate_name}' missing from bench output gates. "
            f"Found: {list(gates.keys())}"
        )


def test_each_gate_has_required_fields():
    """Each gate must have measured, target, unit, and passes fields."""
    results = _run_bench_and_load_results()
    gates = results["gates"]
    for gate_name in REQUIRED_GATE_NAMES:
        gate = gates[gate_name]
        for field in REQUIRED_GATE_FIELDS:
            assert field in gate, (
                f"Gate '{gate_name}' missing field '{field}'. "
                f"Found: {list(gate.keys())}"
            )


def test_gate_measured_values_are_numeric():
    """All gate measured values must be numeric (not strings or None)."""
    results = _run_bench_and_load_results()
    gates = results["gates"]
    for gate_name in REQUIRED_GATE_NAMES:
        measured = gates[gate_name]["measured"]
        assert isinstance(measured, (int, float)), (
            f"Gate '{gate_name}' measured value is {type(measured)}, expected int/float. "
            f"Got: {measured}"
        )


def test_gate_targets_match_spec():
    """Gate targets must match the spec: ≥95, 100, <5, 0."""
    results = _run_bench_and_load_results()
    gates = results["gates"]
    assert gates["grounded_answer_rate"]["target"] == 95.0
    assert gates["refusal_on_unanswerable"]["target"] == 100.0
    assert gates["false_refusal_rate"]["target"] == 5.0
    assert gates["ungrounded_render_count"]["target"] == 0


def test_gate_passes_is_boolean():
    """Each gate's 'passes' field must be a boolean."""
    results = _run_bench_and_load_results()
    gates = results["gates"]
    for gate_name in REQUIRED_GATE_NAMES:
        passes = gates[gate_name]["passes"]
        assert isinstance(passes, bool), (
            f"Gate '{gate_name}' passes is {type(passes)}, expected bool. "
            f"Got: {passes}"
        )


def test_gates_have_numerator_denominator():
    """Percent gates must have numerator and denominator for traceability."""
    results = _run_bench_and_load_results()
    gates = results["gates"]
    for gate_name in ["grounded_answer_rate", "refusal_on_unanswerable", "false_refusal_rate"]:
        gate = gates[gate_name]
        assert "numerator" in gate, f"Gate '{gate_name}' missing 'numerator'"
        assert "denominator" in gate, f"Gate '{gate_name}' missing 'denominator'"
        assert isinstance(gate["numerator"], int), (
            f"Gate '{gate_name}' numerator is {type(gate['numerator'])}, expected int"
        )
        assert isinstance(gate["denominator"], int), (
            f"Gate '{gate_name}' denominator is {type(gate['denominator'])}, expected int"
        )


def test_per_document_breakdown_exists():
    """Results must include per-document breakdown for traceability."""
    results = _run_bench_and_load_results()
    assert "per_document" in results, "Results missing 'per_document' key"
    assert len(results["per_document"]) > 0, "per_document list is empty"
    # Each document entry must have traceable fields
    for doc in results["per_document"]:
        assert "fixture_id" in doc, f"per_document entry missing fixture_id: {doc}"
        assert "pack" in doc, f"per_document entry missing pack: {doc}"
        assert "grounded_answer_rate" in doc
        assert "field_details" in doc, f"per_document entry missing field_details: {doc}"


def test_per_pack_breakdown_exists():
    """Results must include per-pack breakdown."""
    results = _run_bench_and_load_results()
    assert "packs" in results, "Results missing 'packs' key"
    assert len(results["packs"]) > 0, "packs dict is empty"
    for pack_name, pack_data in results["packs"].items():
        assert "grounded_answer_rate" in pack_data
        assert "refusal_on_unanswerable" in pack_data
        assert "false_refusal_rate" in pack_data
        assert "ungrounded_render_count" in pack_data


def test_stdout_contains_gate_names():
    """The printed output must contain the four gate names."""
    output_path = REPO_ROOT / "bench" / "REPORT.json"
    result = subprocess.run(
        [sys.executable, "-m", "bench.harness", "--output", str(output_path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    stdout = result.stdout
    # Check for gate display names in the printed table
    assert "Grounded Answer Rate" in stdout, "stdout missing 'Grounded Answer Rate'"
    assert "Refusal On Unanswerable" in stdout, "stdout missing 'Refusal On Unanswerable'"
    assert "False Refusal Rate" in stdout, "stdout missing 'False Refusal Rate'"
    assert "Ungrounded Render Count" in stdout, "stdout missing 'Ungrounded Render Count'"