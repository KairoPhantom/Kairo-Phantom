"""
run_phase5_demo.py — Standalone Phase 5 batch demonstration script.

This script:
  1. Seeds 10 scenarios into a persistent DuckDB.
  2. Runs all 10 in parallel using SandboxRunner (4 workers, ThreadPoolExecutor).
  3. Stores results in DuckDB via scenario_store.
  4. Prints the full results table.
  5. Validates all acceptance criteria.

Run with:
    python scripts/run_phase5_demo.py
"""
from __future__ import annotations

import os
import sys
import uuid
import time
import shutil
import tempfile
from typing import Any, Dict, List

# ── Path setup ────────────────────────────────────────────────────────────────
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SIDECAR = os.path.join(_REPO_ROOT, "kairo-sidecar")
sys.path.insert(0, _SIDECAR)

from sidecar.sandbox_runner import SandboxRunner
from sidecar.oracle_dispatcher import dispatch
from sidecar.scenario_store import seed_scenarios, record_result, query_results

# ── Configuration ─────────────────────────────────────────────────────────────
RUN_ID = str(uuid.uuid4())[:8]
DB_PATH = os.path.join(tempfile.gettempdir(), f"kairo_phase5_demo_{RUN_ID}.duckdb")
BASE_DIR = tempfile.mkdtemp(prefix="kairo_phase5_demo_")
MAX_WORKERS = 4

# ── Scenario definitions ──────────────────────────────────────────────────────
SCENARIOS: List[Dict[str, Any]] = [
    {"id": "s01", "prompt": "Verify alpha.txt exists", "fixture": "alpha.txt",
     "oracle": "fixture_exists", "category": "fixture", "fix_budget": 1,
     "_create_fixture": True},
    {"id": "s02", "prompt": "Verify beta.txt exists", "fixture": "beta.txt",
     "oracle": "fixture_exists", "category": "fixture", "fix_budget": 1,
     "_create_fixture": True},
    {"id": "s03", "prompt": "Verify gamma.txt exists", "fixture": "gamma.txt",
     "oracle": "fixture_exists", "category": "fixture", "fix_budget": 1,
     "_create_fixture": True},
    {"id": "s04", "prompt": "Smoke PASS (1)", "fixture": "",
     "oracle": "always_pass", "category": "smoke", "fix_budget": 0},
    {"id": "s05", "prompt": "Smoke PASS (2)", "fixture": "",
     "oracle": "always_pass", "category": "smoke", "fix_budget": 0},
    {"id": "s06", "prompt": "Smoke PASS (3)", "fixture": "",
     "oracle": "always_pass", "category": "smoke", "fix_budget": 0},
    {"id": "s07", "prompt": "Network air-gap (1)", "fixture": "",
     "oracle": "network_sniffer", "category": "network", "fix_budget": 2},
    {"id": "s08", "prompt": "Network air-gap (2)", "fixture": "",
     "oracle": "network_sniffer", "category": "network", "fix_budget": 2},
    {"id": "s09", "prompt": "Negative: always FAIL", "fixture": "",
     "oracle": "always_fail", "category": "negative", "fix_budget": 0,
     "_expected_verdict": "FAIL"},
    {"id": "s10", "prompt": "Verify delta.txt absent = FAIL", "fixture": "delta.txt",
     "oracle": "fixture_exists", "category": "fixture", "fix_budget": 1,
     "_create_fixture": False, "_expected_verdict": "FAIL"},
]

# ── Execute function (oracle dispatcher wrapper) ───────────────────────────────
def execute(sandbox_path: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Set up fixture, dispatch oracle, return verdict dict."""
    fixture_name = scenario.get("fixture", "")
    if fixture_name and scenario.get("_create_fixture", False):
        with open(os.path.join(sandbox_path, fixture_name), "w") as fh:
            fh.write(f"fixture for {scenario['id']}\n")
    verdict = dispatch(sandbox_path, scenario)
    return {
        "oracle_verdict": verdict["verdict"],
        "reason": verdict["reason"],
        "success": verdict["verdict"] == "PASS",
    }

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'=' * 72}")
    print("Phase 5 -- Sandbox + Parallel Runner Demo")
    print(f"{'=' * 72}")
    print(f"Run ID      : {RUN_ID}")
    print(f"DuckDB path : {DB_PATH}")
    print(f"Workers     : {MAX_WORKERS}")
    print(f"Scenarios   : {len(SCENARIOS)}\n")

    # 1. Seed scenarios
    public_fields = {"id", "prompt", "fixture", "oracle", "category", "fix_budget"}
    seed_scenarios([{k: v for k, v in s.items() if k in public_fields} for s in SCENARIOS],
                   db_path=DB_PATH)

    # 2. Run in parallel
    runner = SandboxRunner(base_dir=BASE_DIR, max_workers=MAX_WORKERS)
    t_start = time.perf_counter()
    results = runner.run_all(SCENARIOS, execute)
    total_elapsed = round(time.perf_counter() - t_start, 2)

    # 3. Persist results to DuckDB
    for r in results:
        record_result(
            run_id=RUN_ID,
            scenario_id=r["id"],
            worker_id=r.get("worker_id", "main"),
            sandbox_path=r.get("sandbox_path") or "",
            oracle_verdict=r.get("oracle_verdict", r.get("status", "UNKNOWN")),
            elapsed_s=r.get("elapsed_s", 0.0),
            db_path=DB_PATH,
        )

    # 4. Query and print results
    rows = query_results(run_id=RUN_ID, db_path=DB_PATH)
    _print_table(rows)

    # 5. Validate acceptance criteria
    print(f"\n{'-' * 72}")
    print("Acceptance Criteria Validation")
    print(f"{'-' * 72}")

    worker_ids = {r["worker_id"] for r in rows}
    verdicts = [r["oracle_verdict"] for r in rows]
    sandbox_paths = [r["sandbox_path"] for r in rows if r["sandbox_path"]]
    unique_paths = len(set(sandbox_paths)) == len(sandbox_paths)
    unknown = [v for v in verdicts if v not in ("PASS", "FAIL")]
    leftover_sandboxes = [p for p in sandbox_paths if p and os.path.exists(p)]

    print(f"[OK]  10 scenarios ran           : {len(rows) == 10}")
    print(f"[OK]  All sandbox_paths unique    : {unique_paths}")
    print(f"[OK]  No leftover sandbox dirs   : {len(leftover_sandboxes) == 0}")
    print(f"[OK]  No UNKNOWN verdicts        : {len(unknown) == 0}")
    print(f"[OK]  >=2 distinct workers       : {len(worker_ids) >= 2} ({sorted(worker_ids)})")
    print(f"      PASS count                 : {verdicts.count('PASS')}")
    print(f"      FAIL count                 : {verdicts.count('FAIL')}")
    print(f"      Total wall time            : {total_elapsed}s")

    print(f"{'=' * 72}\n")

    # Cleanup
    try:
        os.remove(DB_PATH)
    except Exception:
        pass
    try:
        shutil.rmtree(BASE_DIR, ignore_errors=True)
    except Exception:
        pass

    # Return exit code
    passed_criteria = (
        len(rows) == 10
        and unique_paths
        and len(leftover_sandboxes) == 0
        and len(unknown) == 0
        and len(worker_ids) >= 2
    )
    return 0 if passed_criteria else 1


def _print_table(rows: List[Dict]) -> None:
    headers = ["id", "category", "worker_id", "sandbox_path", "oracle_verdict", "elapsed_s"]
    display = []
    for r in sorted(rows, key=lambda x: x.get("scenario_id", "")):
        sp = r.get("sandbox_path") or ""
        parts = sp.replace("\\", "/").split("/")
        sp_short = "/".join(parts[-2:]) if len(parts) >= 2 else sp
        display.append([
            r.get("scenario_id", ""),
            r.get("category", ""),
            r.get("worker_id", ""),
            sp_short,
            r.get("oracle_verdict", ""),
            str(r.get("elapsed_s", "")),
        ])
    col_widths = [max(len(h), max((len(str(row[i])) for row in display), default=0))
                  for i, h in enumerate(headers)]
    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_row = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    print(f"\n{'-' * 72}")
    print("Oracle Results Table")
    print(sep)
    print(header_row)
    print(sep)
    for row in display:
        print("| " + " | ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(row)) + " |")
    print(sep)


if __name__ == "__main__":
    sys.exit(main())
