---
name: kairo-test-harness
description: >-
  Orchestrates local gauntlet stress-testing, mock model setup, and memory benchmarking for the Kairo-Phantom digital copilot.
---

# Kairo Phantom Test Harness

## Overview
This skill encapsulates the workflow for testing, verifying, and certifying the Kairo-Phantom copilot daemon and agent squads. It automatically runs a 69-scenario parallel E2E gauntlet, performs the KMB-1 memory recall benchmark, manages background mock endpoints, and compiles final compliance reports.

## Dependencies
- None (self-contained CLI suite)

## Quick Start
To set up, run the gauntlet, run the benchmark, and generate the final report:
```bash
uv run --directory C:\Users\praja\.gemini\config\plugins\science\skills\kairo-test-harness\scripts\ kairo_test_harness.py run-all --repo-path C:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom --output C:\tests\results\master_run.json
```

## Utility Scripts
The skill is backed by a multi-command helper script `kairo_test_harness.py` supporting the following subcommands:

### 1. `setup`
Starts the mock Ollama server and launches the Kairo-Phantom daemon process.
```bash
uv run kairo_test_harness.py setup --repo-path C:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom
```

### 2. `run-gauntlet`
Executes all 69 scenarios across the 12 parallel squads using a configurable concurrency cap.
```bash
uv run kairo_test_harness.py run-gauntlet --repo-path C:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom --max-parallel 4 --output C:\tests\results\gauntlet_results.json
```

### 3. `run-benchmark`
Executes the memory recall benchmark and checks if the composite score exceeds the threshold of 0.95.
```bash
uv run kairo_test_harness.py run-benchmark --repo-path C:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom --output C:\tests\results\benchmark_results.json
```

### 4. `cleanup`
Termates any running background daemon and mock processes safely.
```bash
uv run kairo_test_harness.py cleanup --repo-path C:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom
```

## Common Mistakes
- **Port conflicts**: Running the harness when another process is already listening on ports 7437 or 11435.
- **Wrong execution path**: Running without setting up the workspace repository path. Specify the repository path using `--repo-path` if not executing from the workspace root.
