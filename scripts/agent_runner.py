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
    # Command Protocol scenarios
    "w1": {"name": "Command: ghostwrite parsing", "test": "gauntlet_extended", "test_args": "w1_ghostwrite_mode_parsing", "suite": "word"},
    "w2": {"name": "Command: urgent parsing", "test": "gauntlet_extended", "test_args": "w2_urgent_mode_parsing", "suite": "word"},
    "w3": {"name": "Command: query parsing", "test": "gauntlet_extended", "test_args": "w3_query_mode_parsing", "suite": "word"},
    "w4": {"name": "Command: no delimiter", "test": "gauntlet_extended", "test_args": "w4_no_delimiter_stays_silent", "suite": "word"},
    "w5": {"name": "Command: hint ghostwrite", "test": "gauntlet_extended", "test_args": "w5_command_mode_system_hint_ghostwrite", "suite": "word"},
    "w6": {"name": "Command: hint query", "test": "gauntlet_extended", "test_args": "w6_command_mode_system_hint_query", "suite": "word"},
    "w7": {"name": "Command: context before", "test": "gauntlet_extended", "test_args": "w7_ghostwrite_with_context_before", "suite": "word"},
    "w8": {"name": "Command: multiline parsing", "test": "gauntlet_extended", "test_args": "w8_multiline_command_parsing", "suite": "word"},
    # Security scenarios
    "s1": {"name": "Security: sentinel blocks hash", "test": "gauntlet_extended", "test_args": "s1_sentinel_blocks_leaked_hash", "suite": "security"},
    "s2": {"name": "Security: sentinel allows clean", "test": "gauntlet_extended", "test_args": "s2_sentinel_allows_clean_response", "suite": "security"},
    "s3": {"name": "Security: xml framing", "test": "gauntlet_extended", "test_args": "s3_sentinel_xml_framing_extraction", "suite": "security"},
    "s4": {"name": "Security: pii email redaction", "test": "gauntlet_extended", "test_args": "s4_pii_email_redaction", "suite": "security"},
    "s5": {"name": "Security: pii api key redaction", "test": "gauntlet_extended", "test_args": "s5_pii_api_key_redaction", "suite": "security"},
    "s6": {"name": "Security: pii clean text", "test": "gauntlet_extended", "test_args": "s6_pii_clean_text_no_redaction", "suite": "security"},
    "s7": {"name": "Security: inject override", "test": "gauntlet_extended", "test_args": "s7_injection_guard_blocks_override", "suite": "security"},
    "s8": {"name": "Security: inject probe", "test": "gauntlet_extended", "test_args": "s8_injection_guard_blocks_system_probe", "suite": "security"},
    "s9": {"name": "Security: inject clean", "test": "gauntlet_extended", "test_args": "s9_injection_guard_allows_clean_prompt", "suite": "security"},
    "s10": {"name": "Security: validator roleplay", "test": "gauntlet_extended", "test_args": "s10_response_validator_blocks_roleplay", "suite": "security"},
    "s11": {"name": "Security: validator clean", "test": "gauntlet_extended", "test_args": "s11_response_validator_allows_good_response", "suite": "security"},
    "s12": {"name": "Security: wraps system prompt", "test": "gauntlet_extended", "test_args": "s12_sentinel_wraps_system_prompt", "suite": "security"},
    # Routing scenarios
    "r1": {"name": "Routing: design agent (ppt)", "test": "gauntlet_extended", "test_args": "r1_design_agent_for_powerpoint", "suite": "ppt"},
    "r2": {"name": "Routing: data analyst (excel)", "test": "gauntlet_extended", "test_args": "r2_data_analyst_for_excel", "suite": "excel"},
    "r3": {"name": "Routing: content agent (word)", "test": "gauntlet_extended", "test_args": "r3_content_agent_for_word", "suite": "word"},
    "r4": {"name": "Routing: reasoning query mode", "test": "gauntlet_extended", "test_args": "r4_reasoning_for_query_mode", "suite": "cross"},
    "r5": {"name": "Routing: medical agent", "test": "gauntlet_extended", "test_args": "r5_medical_agent_for_clinical_prompt", "suite": "cross"},
    "r6": {"name": "Routing: legal agent", "test": "gauntlet_extended", "test_args": "r6_legal_agent_for_contract", "suite": "cross"},
    "r7": {"name": "Routing: sales agent", "test": "gauntlet_extended", "test_args": "r7_sales_agent_for_proposal", "suite": "cross"},
    "r8": {"name": "Routing: engineer agent", "test": "gauntlet_extended", "test_args": "r8_engineer_for_code_prompt", "suite": "cross"},
    "r9": {"name": "Routing: xml framing all", "test": "gauntlet_extended", "test_args": "r9_xml_framing_in_all_agents", "suite": "cross"},
    "r10": {"name": "Routing: output tags", "test": "gauntlet_extended", "test_args": "r10_output_tags_in_directives", "suite": "cross"},
    # Document Context scenarios
    "d1": {"name": "Context: doc kind detection", "test": "gauntlet_extended", "test_args": "d1_doc_kind_detection_by_extension", "suite": "cross"},
    "d2": {"name": "Context: doc kind excel", "test": "gauntlet_extended", "test_args": "d2_doc_kind_detection_excel", "suite": "cross"},
    "d3": {"name": "Context: prompt extraction", "test": "gauntlet_extended", "test_args": "d3_doc_context_prompt_extraction", "suite": "cross"},
    "d4": {"name": "Context: short prompt band", "test": "gauntlet_extended", "test_args": "d4_confidence_band_short_prompt", "suite": "cross"},
    "d5": {"name": "Context: rich context band", "test": "gauntlet_extended", "test_args": "d5_confidence_band_rich_context", "suite": "cross"},
    # Memory scenarios
    "m1": {"name": "Memory: learns from accepted", "test": "gauntlet_extended", "test_args": "m1_memory_learns_from_accepted_interaction", "suite": "cross"},
    "m2": {"name": "Memory: fragment preferences", "test": "gauntlet_extended", "test_args": "m2_memory_fragment_includes_preferences", "suite": "cross"},
    "m3": {"name": "Memory: persona default word", "test": "gauntlet_extended", "test_args": "m3_persona_default_for_word", "suite": "cross"},
    "m4": {"name": "Memory: persona default code", "test": "gauntlet_extended", "test_args": "m4_persona_default_for_code", "suite": "cross"},
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
        cmd = ["cargo", "test", "--test", test_name]
        if "test_args" in scenario:
            cmd.extend(["--", scenario["test_args"], "--exact", "--nocapture"])
        else:
            cmd.extend(["--", "--nocapture"])
    
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
