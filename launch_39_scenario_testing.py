#!/usr/bin/env python3
"""
Pre-flight checks and execution gateway for 39-scenario parallel testing
Verifies all prerequisites before launching orchestration
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

class PreflightCheck:
    def __init__(self):
        self.repo_root = r"c:\Users\SANDIP\Desktop\Memory\KairoPhantom"
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.checks = []
    
    def check(self, name, condition, critical=False):
        """Log a check result."""
        status = "[PASS]" if condition else ("[FAIL]" if critical else "[WARN]")
        severity = "CRITICAL" if critical and not condition else ("WARNING" if not condition else "PASS")
        
        self.checks.append({
            "name": name,
            "result": condition,
            "severity": severity
        })
        
        if condition:
            self.passed += 1
            print(f"{status} {name}")
        else:
            if critical:
                self.failed += 1
                print(f"{status} {name} [CRITICAL]")
            else:
                self.warnings += 1
                print(f"{status} {name} [WARNING]")
    
    def run_all_checks(self):
        """Execute all preflight checks."""
        print("\n" + "="*80)
        print("PREFLIGHT CHECK - 39 Scenario Parallel Testing")
        print("="*80 + "\n")
        
        # File existence checks
        print("File Checks:")
        self.check(
            "Test manifest (test_manifest_39scenarios.json)",
            os.path.exists(f"{self.repo_root}\\test_manifest_39scenarios.json"),
            critical=True
        )
        
        self.check(
            "Master launch script (orchestrate_39_scenarios_parallel.ps1)",
            os.path.exists(f"{self.repo_root}\\orchestrate_39_scenarios_parallel.ps1"),
            critical=True
        )
        
        self.check(
            "GSD orchestration plan (.gsd/orchestrate_39_scenarios.yaml)",
            os.path.exists(f"{self.repo_root}\\.gsd\\orchestrate_39_scenarios.yaml"),
            critical=True
        )
        
        self.check(
            "Universal orchestrator (scripts/win/universal_orchestrator.py)",
            os.path.exists(f"{self.repo_root}\\scripts\\win\\universal_orchestrator.py"),
            critical=True
        )
        
        # Test fixtures
        print("\nTest Fixtures:")
        self.check(
            "Test documents directory (C:\\tests)",
            os.path.exists("C:\\tests"),
            critical=True
        )
        
        for fixture in ["report.docx", "deck.pptx", "spreadsheet.xlsx", "notes.txt"]:
            self.check(
                f"Fixture: {fixture}",
                os.path.exists(f"C:\\tests\\{fixture}"),
                critical=False  # Warnings only
            )
        
        # Application checks
        print("\nApplication Availability:")
        apps = {
            "Microsoft Word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            "Microsoft PowerPoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            "Microsoft Excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            "VS Code": r"C:\Users\SANDIP\AppData\Local\Programs\Microsoft VS Code\code.exe",
            "Google Chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "Notepad": r"C:\Windows\System32\notepad.exe",
            "Terminal": r"C:\Windows\System32\WindowsTerminal.exe",
        }
        
        for app_name, app_path in apps.items():
            self.check(
                app_name,
                os.path.exists(app_path),
                critical=False  # Warning if missing
            )
        
        # Python/Node checks
        print("\nRuntime Environment:")
        try:
            result = subprocess.run(["python", "--version"], capture_output=True, text=True, timeout=5)
            self.check("Python 3.11+", "3.11" in result.stdout or "3.12" in result.stdout)
        except:
            self.check("Python 3.11+", False, critical=False)
        
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            self.check("Node.js", True)
        except:
            self.check("Node.js", False, critical=False)
        
        # Kairo daemon check
        print("\nKairo Phantom:")
        try:
            result = subprocess.run(["tasklist"], capture_output=True, text=True)
            kairo_running = "kairo" in result.stdout.lower()
            self.check(
                "Kairo daemon running",
                kairo_running,
                critical=False  # Will be started by orchestrator
            )
        except:
            self.check("Kairo daemon check", False, critical=False)
        
        # Python package checks
        print("\nPython Packages:")
        packages = ["pywinauto", "pyautogui", "keyboard", "python-docx", "openpyxl"]
        for pkg in packages:
            try:
                __import__(pkg)
                self.check(f"Package: {pkg}", True)
            except ImportError:
                self.check(f"Package: {pkg}", False, critical=False)
        
        # Final report
        print("\n" + "="*80)
        print(f"PREFLIGHT SUMMARY")
        print("="*80)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Warnings: {self.warnings}")
        
        if self.failed > 0:
            print("\nFAIL - PREFLIGHT FAILED - Critical issues detected")
            print("Please fix critical issues before proceeding.")
            return False
        elif self.warnings > 0:
            print("\nWARN - PREFLIGHT PASSED WITH WARNINGS")
            print("Some optional components are missing but testing can proceed.")
            return True
        else:
            print("\nPASS - PREFLIGHT PASSED - All checks passed!")
            return True


def main():
    print("\n")
    print("+" + "-"*80 + "+")
    print("|" + " "*80 + "|")
    print("|        KAIRO PHANTOM - 39 SCENARIO PARALLEL EXECUTION LAUNCH GATEWAY           |")
    print("|" + " "*80 + "|")
    print("|  Testing all 39 scenarios across 8 application types in parallel:              |")
    print("|  - Word (W1-W10): 10 scenarios                                                 |")
    print("|  - PowerPoint (P1-P7): 7 scenarios                                             |")
    print("|  - Excel (E1-E5): 5 scenarios                                                  |")
    print("|  - VS Code (V1-V6): 6 scenarios                                                |")
    print("|  - Browser (G1-G4): 4 scenarios (Yjs collaborative)                            |")
    print("|  - Notepad (N1-N3): 3 scenarios                                                |")
    print("|  - Terminal (T1-T4): 4 scenarios                                               |")
    print("|  - Chaos Agent: Background fault injection                                     |")
    print("|" + " "*80 + "|")
    print("|  Expected execution time: ~10-15 minutes                                       |")
    print("|  Pass rate target: 95%+ (37+/39 scenarios)                                     |")
    print("|" + " "*80 + "|")
    print("+" + "-"*80 + "+")
    print()
    
    # Run preflight checks
    checker = PreflightCheck()
    if not checker.run_all_checks():
        print("\n✗ Cannot proceed - fix critical issues and try again")
        sys.exit(1)
    
    # Ask for confirmation
    print("\n" + "="*80)
    response = input("Ready to launch 39 scenario parallel testing? (yes/no): ").strip().lower()
    
    if response not in ["yes", "y"]:
        print("✗ Cancelled by user")
        sys.exit(0)
    
    # Launch the orchestration
    print("\n" + "="*80)
    print("LAUNCHING PARALLEL ORCHESTRATION...")
    print("="*80 + "\n")
    
    repo_root = r"c:\Users\SANDIP\Desktop\Memory\KairoPhantom"
    script_path = f"{repo_root}\\orchestrate_39_scenarios_parallel.ps1"
    
    try:
        # Run PowerShell script
        cmd = [
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path
        ]
        
        result = subprocess.run(cmd, cwd=repo_root)
        
        print("\n" + "="*80)
        print("EXECUTION COMPLETED")
        print("="*80)
        print(f"Exit code: {result.returncode}")
        print(f"\nCheck results at:")
        print(f"  • Master report: C:\\tests\\results\\MASTER_REPORT_39_SCENARIOS.json")
        print(f"  • Summary: C:\\tests\\results\\SUMMARY.md")
        print(f"  • Logs: C:\\tests\\logs\\*.log")
        print(f"  • Screenshots: C:\\tests\\screenshots\\*.png")
        
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"\n✗ Error launching orchestration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
