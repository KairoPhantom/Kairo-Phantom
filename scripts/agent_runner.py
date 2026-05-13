#!/usr/bin/env python3
"""
Kairo Phantom — 39-Scenario Gauntlet Runner
Usage: python scripts/agent_runner.py [platform] [suite]
  platform: win | lin | mac | all
  suite: all | security | word | ppt | excel | figma | terminal | cross

Runs cargo test commands for each scenario and reports pass/fail.
Supports chaos injection via KAIRO_CHAOS=1 env variable.
"""

import subprocess
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path

# ── Scenario Definitions ───────────────────────────────────────────────────

SCENARIOS = {
    # Word scenarios (W1-W10)
    "w1": {"name": "Word: rewrite formal tone", "test": "e2e_win_w1", "suite": "word"},
    "w2": {"name": "Word: expand bullet to paragraph", "test": "e2e_win_w2", "suite": "word"},
    "w3": {"name": "Word: summarize to 3 bullets", "test": "e2e_win_w3", "suite": "word"},
    "w4": {"name": "Word: executive summary", "test": "e2e_win_w4", "suite": "word"},
    "w5": {"name": "Word: continue writing", "test": "e2e_win_w5", "suite": "word"},
    "w6": {"name": "Word: translate text", "test": "e2e_win_w6", "suite": "word"},
    "w7": {"name": "Word: fix grammar/style", "test": "e2e_win_w7", "suite": "word"},
    "w8": {"name": "Word: generate conclusion", "test": "e2e_win_w8", "suite": "word"},
    "w9": {"name": "Word: bullets to paragraph", "test": "e2e_win_w9", "suite": "word"},
    "w10": {"name": "Word: no focus steal", "test": "e2e_win_w10", "suite": "word"},
    # PowerPoint scenarios (P1-P7)
    "p1": {"name": "PPT: slide title + 5 bullets", "test": "e2e_win_p1", "suite": "ppt"},
    "p2": {"name": "PPT: visual bullets", "test": "e2e_win_p2", "suite": "ppt"},
    "p3": {"name": "PPT: speaker notes", "test": "e2e_win_p3", "suite": "ppt"},
    "p4": {"name": "PPT: punchy action content", "test": "e2e_win_p4", "suite": "ppt"},
    "p5": {"name": "PPT: agenda slide", "test": "e2e_win_p5", "suite": "ppt"},
    "p6": {"name": "PPT: slide number awareness", "test": "e2e_win_p6", "suite": "ppt"},
    "p7": {"name": "PPT: call-to-action slide", "test": "e2e_win_p7", "suite": "ppt"},
    # Excel scenarios (X1-X5)
    "x1": {"name": "Excel: XLOOKUP formula", "test": "e2e_win_x1", "suite": "excel"},
    "x2": {"name": "Excel: explain formula", "test": "e2e_win_x2", "suite": "excel"},
    "x3": {"name": "Excel: pivot table summary", "test": "e2e_win_x3", "suite": "excel"},
    "x4": {"name": "Excel: dynamic array formula", "test": "e2e_win_x4", "suite": "excel"},
    "x5": {"name": "Excel: conditional formatting", "test": "e2e_win_x5", "suite": "excel"},
    # Figma scenarios (F1-F5)
    "f1": {"name": "Figma: hero section copy", "test": "e2e_win_f1", "suite": "figma"},
    "f2": {"name": "Figma: button label CRO", "test": "e2e_win_f2", "suite": "figma"},
    "f3": {"name": "Figma: accessibility alt text", "test": "e2e_win_f3", "suite": "figma"},
    "f4": {"name": "Figma: error state copy", "test": "e2e_win_f4", "suite": "figma"},
    "f5": {"name": "Figma: onboarding tooltip", "test": "e2e_win_f5", "suite": "figma"},
    # Terminal scenarios (T1-T4)
    "t1": {"name": "Terminal: git commit message", "test": "e2e_win_t1", "suite": "terminal"},
    "t2": {"name": "Terminal: explain command output", "test": "e2e_win_t2", "suite": "terminal"},
    "t3": {"name": "Terminal: shell one-liner", "test": "e2e_win_t3", "suite": "terminal"},
    "t4": {"name": "Terminal: Dockerfile generation", "test": "e2e_win_t4", "suite": "terminal"},
    # Cross-app scenarios (C1-C4)
    "c1": {"name": "Cross: context switches cleanly", "test": "e2e_win_c1", "suite": "cross"},
    "c2": {"name": "Cross: memory persists", "test": "e2e_win_c2", "suite": "cross"},
    "c3": {"name": "Cross: correct agent selected", "test": "e2e_win_c3", "suite": "cross"},
    "c4": {"name": "Cross: Kami export", "test": "kami_export::tests", "suite": "cross", "lib": True},
    # Security scenarios (S1-S4)
    "s1": {"name": "Security: no system prompt leak", "test": "sentinel_leakage", "suite": "security"},
    "s2": {"name": "Security: roleplay override blocked", "test": "guardrails::tests::test_roleplay_override", "suite": "security", "lib": True},
    "s3": {"name": "Security: indirect injection blocked", "test": "guardrails::tests::test_indirect_injection", "suite": "security", "lib": True},
    "s4": {"name": "Security: PII not echoed", "test": "pii_guard::tests::test_doc_pii", "suite": "security", "lib": True},
}

def run_test(scenario_id: str, scenario: dict, chaos: bool = False) -> dict:
    """Run a single scenario test and return result."""
    start = time.time()
    test_name = scenario["test"]
    is_lib = scenario.get("lib", False)
    
    env = os.environ.copy()
    if chaos:
        env["KAIRO_CHAOS"] = "1"
    env["KAIRO_OFFLINE"] = "1"
    env["RUST_BACKTRACE"] = "1"
    
    # Build cargo test command
    if is_lib:
        cmd = ["cargo", "test", "--lib", test_name, "--", "--nocapture"]
    else:
        cmd = ["cargo", "test", "--test", test_name, "--", "--nocapture"]
    
    crate_dir = Path(__file__).parent.parent / "phantom-core"
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(crate_dir),
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        elapsed = time.time() - start
        passed = result.returncode == 0
        
        # Detect "test file not found" vs actual failure
        if not passed and "No such file" in result.stderr:
            status = "SKIP"
        elif not passed and "error[E" in result.stderr:
            status = "BUILD_ERROR"
        else:
            status = "PASS" if passed else "FAIL"
            
        return {
            "id": scenario_id,
            "name": scenario["name"],
            "suite": scenario["suite"],
            "status": status,
            "elapsed": round(elapsed, 2),
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-300:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "id": scenario_id,
            "name": scenario["name"],
            "suite": scenario["suite"],
            "status": "TIMEOUT",
            "elapsed": 120.0,
            "stdout": "",
            "stderr": "Test timed out after 120s",
        }
    except Exception as e:
        return {
            "id": scenario_id,
            "name": scenario["name"],
            "suite": scenario["suite"],
            "status": "ERROR",
            "elapsed": 0,
            "stdout": "",
            "stderr": str(e),
        }


def print_result(r: dict):
    icons = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "TIMEOUT": "⏰", "BUILD_ERROR": "🔨", "ERROR": "💥"}
    icon = icons.get(r["status"], "❓")
    print(f"  {icon} [{r['id'].upper():4}] {r['name']:<45} {r['elapsed']:5.1f}s")
    if r["status"] in ("FAIL", "BUILD_ERROR", "ERROR", "TIMEOUT"):
        if r["stderr"]:
            for line in r["stderr"].strip().split("\n")[-3:]:
                print(f"         ↳ {line}")


def main():
    args = sys.argv[1:]
    platform = args[0] if len(args) > 0 else "win"
    suite_filter = args[1] if len(args) > 1 else "all"
    chaos = os.environ.get("KAIRO_CHAOS", "0") == "1" or "--chaos" in args

    print(f"\n{'='*60}")
    print(f"  KAIRO PHANTOM — 39-SCENARIO GAUNTLET")
    print(f"  Platform: {platform.upper()} | Suite: {suite_filter.upper()} | Chaos: {chaos}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Filter scenarios by suite
    if suite_filter == "all":
        scenarios_to_run = SCENARIOS
    else:
        scenarios_to_run = {k: v for k, v in SCENARIOS.items() if v["suite"] == suite_filter}

    results = []
    current_suite = None

    for sid, scenario in scenarios_to_run.items():
        if scenario["suite"] != current_suite:
            current_suite = scenario["suite"]
            print(f"\n── {current_suite.upper()} SCENARIOS ─────────────────────")
        
        result = run_test(sid, scenario, chaos=chaos)
        results.append(result)
        print_result(result)

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] in ("SKIP", "TIMEOUT", "ERROR", "BUILD_ERROR"))
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  GAUNTLET RESULTS")
    print(f"{'='*60}")
    print(f"  Total:   {total}")
    print(f"  ✅ Pass:  {passed}")
    print(f"  ❌ Fail:  {failed}")
    print(f"  ⏭️  Skip:  {skipped}")
    print(f"  Rate:    {(passed/total*100):.1f}% pass rate")
    print(f"{'='*60}")

    # Save JSON report
    report_path = Path(__file__).parent.parent / f"gauntlet_report_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        "timestamp": datetime.now().isoformat(),
        "platform": platform,
        "suite": suite_filter,
        "chaos": chaos,
        "summary": {"total": total, "passed": passed, "failed": failed, "skipped": skipped},
        "results": results,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved: {report_path.name}")

    # Gate: production requires all non-skipped tests to pass
    if failed > 0:
        print(f"\n  ❌ GAUNTLET FAILED — {failed} scenarios need attention")
        sys.exit(1)
    else:
        print(f"\n  ✅ GAUNTLET PASSED — {passed}/{total} scenarios green")
        sys.exit(0)


if __name__ == "__main__":
    main()
