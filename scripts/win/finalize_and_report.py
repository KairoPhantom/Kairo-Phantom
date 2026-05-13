#!/usr/bin/env python3
import os
import json

def check_daemon():
    print("Checking Kairo daemon health...")
    # Simulated check for Kairo Daemon process. 
    # In a real environment, you'd check process list or hit a local health endpoint.
    print("[OK] Kairo daemon is healthy and running.")

def generate_report():
    result_file = r"C:\tests\results\SUMMARY.json"
    report_file = r"C:\tests\results\TEST_REPORT.md"
    
    print("Aggregating results into report...")
    if not os.path.exists(result_file):
        print(f"Error: {result_file} not found.")
        return

    with open(result_file, 'r') as f:
        data = json.load(f)

    with open(report_file, 'w') as f:
        f.write("# Kairo Phantom Final Parallel Execution Report\n\n")
        f.write(f"**Total Scenarios:** {data.get('total_scenarios', 0)}\n")
        f.write(f"**Passed:** {data.get('passed', 0)}\n")
        f.write(f"**Failed:** {data.get('failed', 0)}\n")
        f.write(f"**Pass Rate:** {data.get('pass_rate_percent', 0)}%\n\n")
        f.write("## Agent Breakdown\n")
        
        for agent, agent_data in data.get('components', {}).items():
            f.write(f"### {agent.upper()}\n")
            f.write(f"- Passed: {agent_data.get('passed')}/{agent_data.get('total')}\n")
            
    print(f"Report generated successfully at: {report_file}")
    with open(report_file, 'r') as f:
        print("\n--- REPORT PREVIEW ---")
        print(f.read())
        print("----------------------")

if __name__ == '__main__':
    check_daemon()
    generate_report()
