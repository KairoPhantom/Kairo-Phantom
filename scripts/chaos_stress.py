#!/usr/bin/env python3
"""
Kairo Phantom — Chaos Stress Script
====================================
Simulates the 10-minute production chaos run from the battle plan.
Toggles FAULT_* flags randomly every 30-120 seconds via the kairo-phantom
CLI's --chaos flag, monitors for panics, and reports a consolidated bug report.

Usage:
    python scripts/chaos_stress.py --duration 600 --platforms windows
    python scripts/chaos_stress.py --duration 60  # Quick 1-minute test
"""

import subprocess
import random
import time
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

FAULTS = [
    "FAULT_UIA_TIMEOUT",
    "FAULT_CLIPBOARD_FAILURE", 
    "FAULT_SSE_DISCONNECT",
    "FAULT_OLLAMA_SLOW",
]

SCENARIOS = [
    {"name": "Flaky UIA",        "fault": "FAULT_UIA_TIMEOUT"},
    {"name": "Dead Clipboard",   "fault": "FAULT_CLIPBOARD_FAILURE"},
    {"name": "SSE Storm",        "fault": "FAULT_SSE_DISCONNECT"},
    {"name": "Ollama Overload",  "fault": "FAULT_OLLAMA_SLOW"},
    {"name": "All Faults",       "fault": "ALL"},
    {"name": "Rapid Spam",       "fault": "NONE"},  # No fault, just rapid
]

class ChaosReport:
    def __init__(self):
        self.start_time = datetime.now()
        self.results = []
        self.total_panics = 0
        self.total_errors = 0
        self.iterations = 0

    def record(self, scenario: str, fault: str, duration: float, 
               panicked: bool, error: str = ""):
        self.iterations += 1
        if panicked:
            self.total_panics += 1
        if error:
            self.total_errors += 1
        self.results.append({
            "scenario": scenario,
            "fault": fault,
            "duration_ms": round(duration * 1000),
            "panicked": panicked,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })

    def print_summary(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print("\n" + "="*70)
        print("🧨 KAIRO PHANTOM CHAOS STRESS REPORT")
        print("="*70)
        print(f"Duration:    {elapsed:.1f}s")
        print(f"Iterations:  {self.iterations}")
        print(f"Panics:      {self.total_panics}  ← MUST BE 0 FOR PRODUCTION")
        print(f"Errors:      {self.total_errors}")
        print(f"Status:      {'✅ PASS' if self.total_panics == 0 else '❌ FAIL — PANICS DETECTED'}")
        print("="*70)
        
        if self.total_panics > 0:
            print("\n🚨 PANIC DETAILS:")
            for r in self.results:
                if r["panicked"]:
                    print(f"  Scenario: {r['scenario']} | Fault: {r['fault']}")
                    print(f"  Error: {r['error']}")
        
        # Write machine-readable report
        report_path = Path("chaos_report.json")
        report_path.write_text(json.dumps({
            "summary": {
                "panics": self.total_panics,
                "errors": self.total_errors,
                "iterations": self.iterations,
                "duration_seconds": elapsed,
                "passed": self.total_panics == 0,
            },
            "results": self.results,
        }, indent=2))
        print(f"\n📄 Full report: {report_path.absolute()}")
        return self.total_panics == 0


def run_cargo_tests(fault_env: dict, timeout: int = 30) -> tuple[bool, str]:
    """Run the chaos test suite with specific fault flags."""
    env = {
        "RUST_BACKTRACE": "1",
        "RUST_LOG": "error",
        **fault_env
    }
    
    try:
        result = subprocess.run(
            ["cargo", "test", "--test", "layer3_chaos_tests", "--", "--nocapture"],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**dict(__import__('os').environ), **env},
            cwd=Path(__file__).parent.parent / "phantom-core"
        )
        
        output = result.stdout + result.stderr
        panicked = "FAILED" in output or "panicked" in output.lower() or result.returncode != 0
        error_msg = ""
        if panicked:
            # Extract panic message
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if 'panic' in line.lower() or 'FAILED' in line:
                    error_msg = '\n'.join(lines[max(0,i-2):i+5])
                    break
        
        return panicked, error_msg
        
    except subprocess.TimeoutExpired:
        return True, f"Test timed out after {timeout}s"
    except Exception as e:
        return True, str(e)


def main():
    parser = argparse.ArgumentParser(description="Kairo Phantom Chaos Stress Test")
    parser.add_argument("--duration", type=int, default=600, 
                       help="Total stress test duration in seconds (default: 600 = 10 min)")
    parser.add_argument("--min-interval", type=int, default=10,
                       help="Min seconds between fault toggles (default: 10)")
    parser.add_argument("--max-interval", type=int, default=30,
                       help="Max seconds between fault toggles (default: 30)")
    args = parser.parse_args()

    print("🧨 Kairo Phantom Chaos Stress Test")
    print(f"   Duration: {args.duration}s ({args.duration//60}m {args.duration%60}s)")
    print(f"   Fault interval: {args.min_interval}–{args.max_interval}s")
    print("   Starting in 3 seconds...\n")
    time.sleep(3)

    report = ChaosReport()
    start = time.time()
    
    while time.time() - start < args.duration:
        # Pick a random scenario
        scenario = random.choice(SCENARIOS)
        elapsed = time.time() - start
        remaining = args.duration - elapsed
        
        print(f"[{elapsed:.0f}s/{args.duration}s] 💥 Scenario: {scenario['name']} "
              f"(fault={scenario['fault']})", flush=True)
        
        # Build fault environment
        fault_env = {}
        if scenario["fault"] == "ALL":
            for f in FAULTS:
                fault_env[f"KAIRO_{f}"] = "1"
        elif scenario["fault"] != "NONE":
            fault_env[f"KAIRO_{scenario['fault']}"] = "1"
        
        # Run tests with this fault configuration
        t0 = time.time()
        panicked, error = run_cargo_tests(fault_env, timeout=60)
        duration = time.time() - t0
        
        report.record(scenario["name"], scenario["fault"], duration, panicked, error)
        
        status = "❌ PANIC" if panicked else "✅ ok"
        print(f"         → {status} ({duration:.1f}s)", flush=True)
        
        if panicked:
            print(f"         ⚠️  PANIC DETECTED! Continuing stress test...", flush=True)
            print(f"         Error: {error[:200]}...", flush=True)
        
        # Random interval before next fault toggle
        if remaining > args.min_interval:
            interval = min(random.randint(args.min_interval, args.max_interval), remaining)
            time.sleep(interval)
    
    passed = report.print_summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
