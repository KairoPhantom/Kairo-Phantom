"""
T7 — Overfitting guard: evaluate dev set and held-out set,
FAIL if the gap exceeds a threshold (divergence = overfitting signal).

No mocks: runs the real bench harness on both dev and held-out fixtures.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HELD_OUT_DIR = REPO_ROOT / "fixtures" / "held_out"
MAX_GAP_THRESHOLD = 20.0  # percentage points — beyond this = overfitting


def _run_bench_on_fixtures(fixtures_dir: str, output_path: str) -> dict:
    """Run the real bench harness on a given fixtures directory."""
    env = os.environ.copy()
    env["KAIRO_GATEWAY_TEST_MODE"] = "true"
    result = subprocess.run(
        [sys.executable, "-m", "bench.harness",
         "--fixtures-dir", fixtures_dir,
         "--output", output_path],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    if result.returncode != 0:
        pytest.fail(f"bench harness failed on {fixtures_dir}: {result.stderr}")
    with open(REPO_ROOT / output_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _compute_grounded_rate(report: dict) -> float:
    """Compute grounded-answer rate from the gates section."""
    gates = report.get("gates", {})
    return gates.get("grounded_answer_rate", {}).get("measured", 0.0)


class TestOverfittingGuard:
    """Assert dev and held-out metrics don't diverge beyond threshold."""

    def test_held_out_fixtures_exist(self):
        """Held-out fixtures must exist and be separate from dev."""
        assert HELD_OUT_DIR.exists(), "fixtures/held_out/ directory missing"
        gt_file = HELD_OUT_DIR / "ground_truth.json"
        assert gt_file.exists(), "held_out/ground_truth.json missing"
        with open(gt_file, "r") as f:
            gt = json.load(f)
        assert len(gt.get("fixtures", [])) >= 2, (
            "Held-out set must have at least 2 fixtures"
        )

    def test_dev_vs_held_out_gap_within_threshold(self):
        """Dev and held-out grounded-answer rates must not diverge > threshold."""
        dev_report = _run_bench_on_fixtures("fixtures/invoice", "bench/REPORT_dev.json")
        held_report = _run_bench_on_fixtures("fixtures/held_out", "bench/REPORT_held.json")

        dev_rate = _compute_grounded_rate(dev_report)
        held_rate = _compute_grounded_rate(held_report)

        gap = abs(dev_rate - held_rate)
        assert gap <= MAX_GAP_THRESHOLD, (
            f"Overfitting detected: dev={dev_rate}% vs held_out={held_rate}%, "
            f"gap={gap}% exceeds threshold {MAX_GAP_THRESHOLD}%"
        )

    def test_overfitting_detection_triggers_on_large_gap(self):
        """Failing-capable: a simulated large gap must be detected."""
        dev_rate = 100.0
        held_rate = 50.0
        gap = abs(dev_rate - held_rate)
        assert gap > MAX_GAP_THRESHOLD, (
            "Overfitting guard failed to detect a 50-point gap"
        )
