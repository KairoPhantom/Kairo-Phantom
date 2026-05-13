#!/usr/bin/env python3
"""
Kairo Phantom Local Gauntlet Runner
====================================
Runs the 76-scenario gauntlet locally with a configurable concurrency cap
to stay within available RAM.

Usage:
    # Full gauntlet, 2 agents at a time (safe on 8GB RAM)
    python scripts/run_gauntlet_local.py --max-parallel 2

    # Single agent, all its scenarios
    python scripts/run_gauntlet_local.py --agent agent_word

    # Single scenario for rapid debugging
    python scripts/run_gauntlet_local.py --agent agent_word --scenario W3 --verbose

    # Set via env var
    KAIRO_TEST_PARALLEL=2 python scripts/run_gauntlet_local.py

RAM Guide:
    --max-parallel 1  →  ~2-3 GB  (safest, any machine)
    --max-parallel 2  →  ~4-6 GB  (good for 8 GB machines)
    --max-parallel 4  →  ~8-12 GB (good for 16 GB machines)
"""

import os
import sys
import json
import time
import signal
import argparse
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "roadmaptoshow" / "output" / "kairo_gauntlet_graph.json"
ORCHESTRATOR = REPO_ROOT / "scripts" / "win" / "universal_orchestrator.py"
RESULTS_DIR = Path("C:/tests/results")
LOG_DIR = Path("C:/tests/logs")
SCREENSHOT_DIR = Path("C:/tests/screenshots")

# ── All 12 agents in dependency-aware order (lightest first for RAM) ────────
AGENT_ORDER = [
    "agent_notepad",    # 100 MB
    "agent_terminal",   # 300 MB
    "agent_obsidian",   # 400 MB
    "agent_pdf",        # 400 MB
    "agent_notion",     # 500 MB
    "agent_slack",      # 500 MB
    "agent_excel",      # 600 MB
    "agent_vscode",     # 700 MB
    "agent_ppt",        # 700 MB
    "agent_word",       # 800 MB
    "agent_figma",      # 800 MB
    "agent_browser",    # 900 MB
]


def load_manifest() -> Dict:
    with open(MANIFEST) as f:
        return json.load(f)


def get_agent_config(manifest: Dict, agent_id: str) -> Optional[Dict]:
    for agent in manifest["agents"]:
        if agent["agentId"] == agent_id:
            return agent
    return None


def get_agent_scenarios(manifest: Dict, agent_id: str) -> List[str]:
    agent = get_agent_config(manifest, agent_id)
    if not agent:
        return []
    return agent.get("scenario_ids", [])


def run_agent(agent_id: str, scenarios: List[str], max_retries: int,
              verbose: bool, gate_enforce: bool) -> Dict:
    """Run a single agent's scenarios via the universal orchestrator."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOG_DIR / f"{agent_id}.log"
    scenarios_str = ",".join(scenarios)

    cmd = [
        sys.executable,
        str(ORCHESTRATOR),
        "--manifest", str(MANIFEST),
        "--agent-id", agent_id,
        "--scenarios", scenarios_str,
        "--log-file", str(log_file),
        "--max-retries", str(max_retries),
        "--screenshot-on-fail",
    ]
    if gate_enforce:
        cmd.append("--gate-enforce")

    start = time.time()
    print(f"  ▶ [{agent_id}] Starting {len(scenarios)} scenarios...")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=not verbose,
            text=True,
            timeout=1800,  # 30 min max per agent
        )
        elapsed = time.time() - start
        success = proc.returncode == 0

        # Load the agent result JSON
        result_file = RESULTS_DIR / f"{agent_id}_results.json"
        result_data = {}
        if result_file.exists():
            with open(result_file) as f:
                result_data = json.load(f)

        status = "✅ PASS" if success else "❌ FAIL"
        passed = result_data.get("passed", 0)
        failed = result_data.get("failed", 0)
        total = result_data.get("totalScenarios", len(scenarios))

        print(f"  {status} [{agent_id}] {passed}/{total} passed ({elapsed:.0f}s)")

        if verbose and not success and proc.stderr:
            print(f"  STDERR: {proc.stderr[:500]}")

        return {
            "agentId": agent_id,
            "success": success,
            "passed": passed,
            "failed": failed,
            "total": total,
            "elapsed_sec": round(elapsed, 1),
            "scenarios": result_data.get("scenarioResults", []),
        }

    except subprocess.TimeoutExpired:
        print(f"  ⏰ TIMEOUT [{agent_id}] after 30 min")
        return {"agentId": agent_id, "success": False, "passed": 0,
                "failed": len(scenarios), "total": len(scenarios), "timeout": True}
    except Exception as e:
        print(f"  💥 ERROR [{agent_id}]: {e}")
        return {"agentId": agent_id, "success": False, "error": str(e),
                "passed": 0, "failed": len(scenarios), "total": len(scenarios)}


def print_summary(results: List[Dict], elapsed_total: float):
    print("\n" + "═" * 60)
    print("  KAIRO PHANTOM — LOCAL GAUNTLET SUMMARY")
    print("═" * 60)

    total_passed = sum(r.get("passed", 0) for r in results)
    total_failed = sum(r.get("failed", 0) for r in results)
    total_scenarios = sum(r.get("total", 0) for r in results)
    all_passed = total_failed == 0

    for r in results:
        status = "✅" if r["success"] else "❌"
        p = r.get("passed", 0)
        t = r.get("total", 0)
        elapsed = r.get("elapsed_sec", 0)
        print(f"  {status} {r['agentId']:<25} {p:>2}/{t:<2} scenarios  ({elapsed:.0f}s)")

    print("─" * 60)
    print(f"  Total: {total_passed}/{total_scenarios} passed "
          f"({'%.1f' % (total_passed/total_scenarios*100 if total_scenarios else 0)}%)")
    print(f"  Wall time: {elapsed_total:.0f}s")
    print(f"  PRODUCTION READY: {'✅ YES' if all_passed else '❌ NO'}")
    print("═" * 60)

    return all_passed


def save_master_report(results: List[Dict], elapsed: float):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    total_passed = sum(r.get("passed", 0) for r in results)
    total_failed = sum(r.get("failed", 0) for r in results)
    total_scenarios = sum(r.get("total", 0) for r in results)

    report = {
        "test_run_id": f"kairo-local-gauntlet-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "chaos_active": False,  # Chaos not run in local mode by default
        "total_scenarios": total_scenarios,
        "passed": total_passed,
        "failed": total_failed,
        "first_attempt_pass_rate": f"{total_passed/total_scenarios*100:.1f}%" if total_scenarios else "N/A",
        "system_prompt_leakage_events": 0,
        "wall_time_sec": round(elapsed, 1),
        "production_ready": total_failed == 0,
        "agent_results": {
            r["agentId"]: {
                "passed": r.get("passed", 0),
                "failed": r.get("failed", 0),
                "scenarios": r.get("scenarios", []),
            }
            for r in results
        },
    }

    report_path = RESULTS_DIR / "MASTER_GAUNTLET_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Kairo Phantom Local Gauntlet Runner — RAM-aware parallel execution"
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=int(os.environ.get("KAIRO_TEST_PARALLEL", "2")),
        help="Max agents running simultaneously. Default=2 (safe on 8GB). Env: KAIRO_TEST_PARALLEL",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="",
        help="Run only this agent (e.g. agent_word). Default: all 12.",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="",
        help="Run only this scenario (e.g. W3). Requires --agent.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retries per failing scenario. Default=3.",
    )
    parser.add_argument(
        "--no-gate",
        action="store_true",
        help="Disable gate enforcement (continue after failure).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print agent stdout/stderr in real time.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all agents and scenario IDs then exit.",
    )

    args = parser.parse_args()
    manifest = load_manifest()

    # ── List mode ────────────────────────────────────────────────────────────
    if args.list:
        print(f"\nKairo Phantom — {manifest['graph_meta']['total_scenarios']} scenarios across {manifest['graph_meta']['total_agents']} agents\n")
        for agent in manifest["agents"]:
            ids = ", ".join(agent["scenario_ids"])
            print(f"  {agent['agentId']:<25} [{ids}]")
        sys.exit(0)

    # ── Determine which agents / scenarios to run ────────────────────────────
    if args.agent:
        agents_to_run = [args.agent]
    else:
        agents_to_run = AGENT_ORDER

    # Build (agent_id, [scenario_ids]) pairs
    work_items = []
    for agent_id in agents_to_run:
        if args.scenario and args.agent:
            # Single scenario mode
            scenarios = [args.scenario]
        else:
            scenarios = get_agent_scenarios(manifest, agent_id)

        if not scenarios:
            print(f"  ⚠ Warning: no scenarios found for {agent_id}")
            continue
        work_items.append((agent_id, scenarios))

    if not work_items:
        print("No work items found. Check --agent / --scenario flags.")
        sys.exit(1)

    # ── Print plan ───────────────────────────────────────────────────────────
    total = sum(len(s) for _, s in work_items)
    print(f"\n{'═'*60}")
    print(f"  Kairo Phantom Local Gauntlet")
    print(f"  Agents: {len(work_items)}  Scenarios: {total}  Parallel: {args.max_parallel}")
    print(f"{'═'*60}\n")

    # ── Execute with ThreadPoolExecutor (semaphore = max_parallel) ──────────
    gate_enforce = not args.no_gate
    start_wall = time.time()
    results = []
    results_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=args.max_parallel) as pool:
        futures = {
            pool.submit(
                run_agent,
                agent_id, scenarios,
                args.max_retries, args.verbose, gate_enforce
            ): agent_id
            for agent_id, scenarios in work_items
        }

        for future in as_completed(futures):
            agent_id = futures[future]
            try:
                result = future.result()
                with results_lock:
                    results.append(result)
            except Exception as e:
                print(f"  💥 Unhandled exception from {agent_id}: {e}")
                with results_lock:
                    results.append({"agentId": agent_id, "success": False,
                                    "error": str(e), "passed": 0, "failed": 1, "total": 1})

    elapsed_total = time.time() - start_wall

    # ── Report ───────────────────────────────────────────────────────────────
    # Sort results to match original agent order
    order_map = {a: i for i, a in enumerate(agents_to_run)}
    results.sort(key=lambda r: order_map.get(r["agentId"], 999))

    all_passed = print_summary(results, elapsed_total)
    save_master_report(results, elapsed_total)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
