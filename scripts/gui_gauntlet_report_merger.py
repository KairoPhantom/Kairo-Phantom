#!/usr/bin/env python3
import argparse
import glob
import json
import os
import sys
from typing import List, Dict, Any

def merge_reports(directory: str, gate_threshold: float) -> int:
    """
    Search recursively for results.json files under directory.
    Consolidate them, enforce gate_threshold (pass_rate >= gate_threshold),
    write the consolidated gui_gauntlet_report.json, and return exit code (0 or 1).
    """
    pattern = os.path.join(directory, "**", "results.json")
    files = glob.glob(pattern, recursive=True)

    all_results: List[Dict[str, Any]] = []
    
    if not files:
        print(f"Error: No results.json files found under '{directory}'", file=sys.stderr)
        # If no files found, write an empty report and exit 1
        report = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "results": []
        }
        with open("gui_gauntlet_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return 1

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Empty file")
                data = json.loads(content)
                if isinstance(data, list):
                    all_results.extend(data)
                elif isinstance(data, dict):
                    all_results.append(data)
                else:
                    raise ValueError(f"Invalid JSON type: {type(data)}")
        except Exception as e:
            print(f"Error: Malformed results file {file_path}: {e}", file=sys.stderr)
            # We treat malformed file as a failure case
            # Write empty/partial report and return 1
            report = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "results": [],
                "error": f"Malformed results file {file_path}: {e}"
            }
            with open("gui_gauntlet_report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            return 1

    total = len(all_results)
    passed_scenarios = [r for r in all_results if r.get("status") == "PASSED"]
    failed_scenarios = [r for r in all_results if r.get("status") != "PASSED"]

    passed = len(passed_scenarios)
    failed = len(failed_scenarios)
    
    pass_rate = (passed / total) * 100.0 if total > 0 else 0.0

    report = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(pass_rate, 2),
        "results": all_results
    }

    with open("gui_gauntlet_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Consolidated GUI Gauntlet Report:")
    print(f"  Total: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Pass Rate: {pass_rate:.2f}% (Gate: {gate_threshold:.2f}%)")

    if pass_rate < gate_threshold:
        print("\nFailed Scenarios:")
        for r in failed_scenarios:
            print(f"  - {r.get('id', 'UNKNOWN')} ({r.get('app', 'UNKNOWN')}): {r.get('status', 'UNKNOWN')} - {r.get('error', '')}")
        return 1

    return 0

def main():
    parser = argparse.ArgumentParser(description="Merge parallel GUI gauntlet results.json reports.")
    parser.add_argument(
        "--dir",
        default="gui-screenshots",
        help="Directory to search recursively for results.json files (default: gui-screenshots)"
    )
    parser.add_argument(
        "--gate-threshold",
        type=float,
        default=80.0,
        help="Pass rate percentage threshold to pass the CI gate (default: 80.0)"
    )
    args = parser.parse_args()
    
    exit_code = merge_reports(args.dir, args.gate_threshold)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
