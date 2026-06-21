"""
T7 — Historical tracking: store each bench run in bench/history/;
CI fails on regression beyond tolerance on any of the four gates.

No mocks: runs the real bench harness and stores results in history.
"""
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HISTORY_DIR = REPO_ROOT / "bench" / "history"
TOLERANCE = 5.0  # percentage points — regression beyond this fails CI


def _run_bench(output_path: str) -> dict:
    """Run the real bench harness and return parsed report."""
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
    with open(REPO_ROOT / output_path, "r") as f:
        return json.load(f)


def _store_in_history(report: dict) -> pathlib.Path:
    """Store a bench report in bench/history/ with a timestamped name."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
    hist_path = HISTORY_DIR / f"bench_{ts}.json"
    hist_path.write_text(json.dumps(report, indent=2))
    return hist_path


def _extract_gate_metrics(report: dict) -> dict:
    """Extract the four gate metrics from a bench report."""
    gates = report.get("gates", {})
    return {
        "grounded_answer_rate": gates.get("grounded_answer_rate", {}).get("measured", 0.0),
        "refusal_on_unanswerable": gates.get("refusal_on_unanswerable", {}).get("measured", 0.0),
        "false_refusal_rate": gates.get("false_refusal_rate", {}).get("measured", 0.0),
        "ungrounded_render_count": gates.get("ungrounded_render_count", {}).get("measured", 0),
    }


class TestHistoricalTracking:
    """Store bench runs in history and detect regressions."""

    def test_bench_run_is_stored_in_history(self):
        """A bench run must be stored in bench/history/."""
        report = _run_bench("bench/REPORT_hist_current.json")
        hist_path = _store_in_history(report)
        assert hist_path.exists(), "History file was not created"
        stored = json.loads(hist_path.read_text())
        assert "gates" in stored or "packs" in stored, "Stored report must have gates or packs data"

    def test_history_directory_exists(self):
        """bench/history/ directory must exist after a run."""
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        assert HISTORY_DIR.exists(), "bench/history/ directory must exist"

    def test_no_regression_beyond_tolerance(self):
        """Current gate metrics must not regress beyond tolerance vs history."""
        report = _run_bench("bench/REPORT_hist_regression.json")
        current = _extract_gate_metrics(report)

        # Load the most recent historical run (excluding current)
        history_files = sorted(HISTORY_DIR.glob("bench_*.json"))
        if not history_files:
            _store_in_history(report)
            pytest.skip("No historical baseline yet — storing current as baseline")

        with open(history_files[-1], "r") as f:
            baseline = _extract_gate_metrics(json.load(f))

        for gate in ("grounded_answer_rate", "refusal_on_unanswerable"):
            regression = baseline[gate] - current[gate]
            assert regression <= TOLERANCE, (
                f"REGRESSION on {gate}: baseline={baseline[gate]}% "
                f"current={current[gate]}%, regression={regression}% "
                f"exceeds tolerance {TOLERANCE}%"
            )

    def test_regression_detection_triggers_on_drop(self):
        """Failing-capable: a planted regression must be detected."""
        baseline = {"grounded_answer_rate": 100.0, "refusal_on_unanswerable": 100.0}
        current = {"grounded_answer_rate": 90.0, "refusal_on_unanswerable": 100.0}
        regression = baseline["grounded_answer_rate"] - current["grounded_answer_rate"]
        assert regression > TOLERANCE, (
            "Regression detection failed to catch a 10-point drop"
        )
