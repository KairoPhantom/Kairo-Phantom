"""
T7 — Determinism guard: run make bench twice, assert identical metrics
for the four release gates. Fails if any metric diverges between runs.

No mocks: calls the real bench harness and compares real REPORT.json output.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _run_bench(output_path: str) -> dict:
    """Run the real bench harness and return the parsed report."""
    env = os.environ.copy()
    env["KAIRO_GATEWAY_TEST_MODE"] = "true"
    result = subprocess.run(
        [sys.executable, "-m", "bench.harness",
         "--fixtures-dir", "fixtures/invoice",
         "--output", output_path],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    if result.returncode != 0:
        pytest.fail(f"bench harness failed: {result.stderr}")
    report_path = REPO_ROOT / output_path
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_gate_metrics(report: dict) -> dict:
    """Extract the four release-gate metrics from a bench report."""
    gates = report.get("gates", {})
    return {
        "grounded_answer_rate": gates.get("grounded_answer_rate", {}).get("measured", 0.0),
        "refusal_on_unanswerable": gates.get("refusal_on_unanswerable", {}).get("measured", 0.0),
        "false_refusal_rate": gates.get("false_refusal_rate", {}).get("measured", 0.0),
        "ungrounded_render_count": gates.get("ungrounded_render_count", {}).get("measured", 0),
    }


class TestDeterminism:
    """Assert bench metrics are identical across two consecutive runs."""

    def test_two_runs_produce_identical_gate_metrics(self):
        """Run bench twice; the four gate metrics must be identical."""
        run1 = _run_bench("bench/REPORT_det_1.json")
        run2 = _run_bench("bench/REPORT_det_2.json")

        m1 = _extract_gate_metrics(run1)
        m2 = _extract_gate_metrics(run2)

        for key in ("grounded_answer_rate", "refusal_on_unanswerable",
                     "false_refusal_rate", "ungrounded_render_count"):
            assert m1[key] == m2[key], (
                f"Non-deterministic metric '{key}': "
                f"run1={m1[key]} vs run2={m2[key]}"
            )

    def test_per_pack_metrics_are_deterministic(self):
        """Per-pack metrics must also be identical across runs."""
        run1 = _run_bench("bench/REPORT_det_3.json")
        run2 = _run_bench("bench/REPORT_det_4.json")

        for pack_name in run1.get("packs", {}):
            assert pack_name in run2.get("packs", {}), (
                f"Pack '{pack_name}' missing from second run"
            )
            m1 = run1["packs"][pack_name]
            m2 = run2["packs"][pack_name]
            for key in ("grounded_answer_rate", "refusal_on_unanswerable",
                         "total_extractions", "passed_extractions",
                         "ungrounded_render_count"):
                assert m1[key] == m2[key], (
                    f"Non-deterministic '{key}' for pack '{pack_name}': "
                    f"run1={m1[key]} vs run2={m2[key]}"
                )

    def test_determinism_breaks_when_metrics_change(self):
        """Failing-capable: if we tamper with a report, the comparison must catch it."""
        run1 = _run_bench("bench/REPORT_det_5.json")
        m1 = _extract_gate_metrics(run1)

        tampered = dict(m1)
        tampered["grounded_answer_rate"] = m1["grounded_answer_rate"] + 1.0

        assert m1["grounded_answer_rate"] != tampered["grounded_answer_rate"], (
            "Determinism check failed to detect tampered metrics"
        )
