#!/usr/bin/env python3
"""
Simplified 39-Scenario Parallel Orchestration
Direct launcher for all GSD/Ruflo agents without PowerShell complexity
"""

import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

class ParallelOrchestrator:
    def __init__(self):
        self.repo_root = Path(r"c:\Users\SANDIP\Desktop\Memory\KairoPhantom")
        self.test_dir = Path("C:\\tests")
        self.log_dir = self.test_dir / "logs"
        self.result_dir = self.test_dir / "results"
        self.manifest_path = self.repo_root / "test_manifest_39scenarios.json"
        
        self.agents = [
            {
                "name": "agent_word",
                "scenarios": "W1,W2,W3,W4,W5,W6,W7,W8,W9,W10",
                "total": 10,
                "timeout": 600
            },
            {
                "name": "agent_ppt",
                "scenarios": "P1,P2,P3,P4,P5,P6,P7",
                "total": 7,
                "timeout": 480
            },
            {
                "name": "agent_excel",
                "scenarios": "E1,E2,E3,E4,E5",
                "total": 5,
                "timeout": 420
            },
            {
                "name": "agent_vscode",
                "scenarios": "V1,V2,V3,V4,V5,V6",
                "total": 6,
                "timeout": 420
            },
            {
                "name": "agent_browser",
                "scenarios": "G1,G2,G3,G4",
                "total": 4,
                "timeout": 360
            },
            {
                "name": "agent_notepad",
                "scenarios": "N1,N2,N3",
                "total": 3,
                "timeout": 240
            },
            {
                "name": "agent_terminal",
                "scenarios": "T1,T2,T3,T4",
                "total": 4,
                "timeout": 300
            }
        ]
        
        self.results = {}
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary directories."""
        for d in [self.log_dir, self.result_dir, self.test_dir / "screenshots"]:
            d.mkdir(parents=True, exist_ok=True)
        print(f"✓ Directories ready: {self.test_dir}")
    
    def create_test_fixtures(self):
        """Create minimal test fixture files."""
        print("\n[SETUP] Creating test fixtures...")
        
        # Create minimal docx (we can't create real Office docs without libraries)
        fixtures = {
            "report.docx": b"PK\x03\x04",  # Minimal ZIP header
            "deck.pptx": b"PK\x03\x04",
            "spreadsheet.xlsx": b"PK\x03\x04",
            "notes.txt": b"Test notes fixture\n"
        }
        
        for filename, content in fixtures.items():
            filepath = self.test_dir / filename
            if not filepath.exists():
                filepath.write_bytes(content)
                print(f"  ✓ Created: {filename}")
    
    def launch_agent(self, agent: Dict) -> Tuple[str, bool, str]:
        """Launch a single agent and return results."""
        agent_name = agent["name"]
        print(f"\n[AGENT] Launching {agent_name} ({agent['total']} scenarios)")
        
        log_file = self.log_dir / f"{agent_name}.log"
        cmd = [
            sys.executable,
            str(self.repo_root / "scripts" / "win" / "universal_orchestrator.py"),
            "--manifest", str(self.manifest_path),
            "--agent-id", agent_name,
            "--scenarios", agent["scenarios"],
            "--log-file", str(log_file),
            "--gate-enforce",
            "--max-retries", "3",
            "--screenshot-on-fail"
        ]
        
        try:
            # Execute agent
            result = subprocess.run(
                cmd,
                timeout=agent["timeout"],
                capture_output=True,
                text=True,
                cwd=str(self.repo_root)
            )
            
            # Parse results
            results_file = self.result_dir / f"{agent_name}_results.json"
            if results_file.exists():
                with open(results_file) as f:
                    data = json.load(f)
                    passed = data.get("passed", 0)
                    total = data.get("totalScenarios", agent["total"])
                    pass_rate = (passed / total * 100) if total > 0 else 0
                    
                    status = "PASS" if result.returncode == 0 else "FAIL"
                    msg = f"{passed}/{total} scenarios ({pass_rate:.1f}%)"
                    
                    print(f"  ✓ {agent_name}: {msg} [{status}]")
                    return agent_name, result.returncode == 0, msg
            else:
                print(f"  ⚠ {agent_name}: No results file generated")
                return agent_name, False, "No results file"
                
        except subprocess.TimeoutExpired:
            print(f"  ✗ {agent_name}: Timeout after {agent['timeout']}s")
            return agent_name, False, "Timeout"
        except Exception as e:
            print(f"  ✗ {agent_name}: {str(e)}")
            return agent_name, False, str(e)
    
    def orchestrate(self):
        """Launch all agents in parallel and aggregate results."""
        print("\n" + "="*80)
        print("KAIRO PHANTOM - 39 SCENARIO PARALLEL EXECUTION")
        print("="*80)
        
        self.create_test_fixtures()
        
        # Summary
        total_scenarios = sum(a["total"] for a in self.agents)
        print(f"\n[INFO] Launching {len(self.agents)} agents for {total_scenarios} total scenarios")
        print(f"[INFO] Expected duration: ~10-15 minutes")
        
        start_time = time.time()
        
        # Launch all agents in parallel
        print(f"\n[EXECUTION] Deploying all agents in parallel...")
        
        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = {executor.submit(self.launch_agent, agent): agent for agent in self.agents}
            
            for future in as_completed(futures):
                agent_name, success, message = future.result()
                self.results[agent_name] = {
                    "success": success,
                    "message": message
                }
        
        elapsed = time.time() - start_time
        
        # Aggregate results
        self.aggregate_results(elapsed)
    
    def aggregate_results(self, elapsed_time: float):
        """Aggregate and report final results."""
        print("\n" + "="*80)
        print("EXECUTION SUMMARY")
        print("="*80)
        
        total_passed = 0
        total_scenarios = 0
        agent_summary = []
        
        # Collect metrics from each agent
        for agent in self.agents:
            agent_name = agent["name"]
            results_file = self.result_dir / f"{agent_name}_results.json"
            
            if results_file.exists():
                with open(results_file) as f:
                    data = json.load(f)
                    passed = data.get("passed", 0)
                    failed = data.get("failed", 0)
                    total = data.get("totalScenarios", agent["total"])
                    
                    total_passed += passed
                    total_scenarios += total
                    
                    status = "✓" if failed == 0 else "✗"
                    agent_summary.append({
                        "agent": agent_name,
                        "passed": passed,
                        "total": total,
                        "status": status
                    })
            else:
                total_scenarios += agent["total"]
                agent_summary.append({
                    "agent": agent_name,
                    "passed": 0,
                    "total": agent["total"],
                    "status": "⚠"
                })
        
        # Print summary
        print(f"\nTotal Execution Time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
        print(f"\nAgent Results:")
        
        for summary in agent_summary:
            pct = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
            print(f"  {summary['status']} {summary['agent']:20s}: {summary['passed']:2d}/{summary['total']} ({pct:5.1f}%)")
        
        pass_rate = (total_passed / total_scenarios * 100) if total_scenarios > 0 else 0
        print(f"\n{'='*80}")
        print(f"OVERALL: {total_passed}/{total_scenarios} scenarios passed ({pass_rate:.1f}%)")
        print(f"{'='*80}")
        
        if pass_rate >= 95:
            print("\n✓ SUCCESS - 95%+ pass rate achieved!")
            exit_code = 0
        elif pass_rate >= 80:
            print("\n⚠ PARTIAL SUCCESS - 80%+ pass rate (below target of 95%)")
            exit_code = 0
        else:
            print("\n✗ NEEDS REVIEW - Pass rate below 80%")
            exit_code = 1
        
        # Save summary
        summary_file = self.result_dir / "SUMMARY.json"
        summary_data = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": elapsed_time,
            "total_scenarios": total_scenarios,
            "passed": total_passed,
            "failed": total_scenarios - total_passed,
            "pass_rate": pass_rate,
            "agents": agent_summary
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        print(f"\n✓ Summary saved: {summary_file}")
        print(f"✓ Logs: {self.log_dir}\\*.log")
        print(f"✓ Results: {self.result_dir}\\*_results.json")
        
        return exit_code


def main():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  KAIRO PHANTOM - 39 SCENARIO PARALLEL ORCHESTRATION".center(78) + "║")
    print("║" + " "*78 + "║")
    print("║" + "  Testing all 39 scenarios across 8 application types in parallel:".ljust(78) + "║")
    print("║" + "  • Word (W1-W10): 10 scenarios".ljust(78) + "║")
    print("║" + "  • PowerPoint (P1-P7): 7 scenarios".ljust(78) + "║")
    print("║" + "  • Excel (E1-E5): 5 scenarios".ljust(78) + "║")
    print("║" + "  • VS Code (V1-V6): 6 scenarios".ljust(78) + "║")
    print("║" + "  • Browser (G1-G4): 4 scenarios (Yjs collaborative)".ljust(78) + "║")
    print("║" + "  • Notepad (N1-N3): 3 scenarios".ljust(78) + "║")
    print("║" + "  • Terminal (T1-T4): 4 scenarios".ljust(78) + "║")
    print("║" + " "*78 + "║")
    print("║" + "  Execution mode: 7 parallel agents, sequential scenarios per agent".ljust(78) + "║")
    print("║" + "  Pass rate target: 95%+ (37+/39 scenarios)".ljust(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    orchestrator = ParallelOrchestrator()
    orchestrator.orchestrate()


if __name__ == "__main__":
    main()
