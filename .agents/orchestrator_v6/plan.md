# Plan — KairoReal Gauntlet Rebuild

## Objectives
1. Replace `scenarios.json` with 200 distinct, real-world tasks across 10 domains (Word, Excel, PPT, Legal, CUA, Security, Memory, Offline, Degradation, Performance), each with distinct expected outcomes.
2. Modify `scripts/run_kairoreal_gauntlet.py` to invoke actual sidecar APIs/methods and verify outputs against expected outcomes using falsifiable oracles.
3. Integrate pytest test suite to verify the gauntlet runner behavior.
4. Update GitHub Actions workflows to include the gauntlet gate.
5. Verify correctness and integrity via worker, reviewer, challenger, and forensic auditor.

## Phase 1: Exploration
- Locate and understand all masters/writers/detectors (e.g., `WordMaster`/`WordWriter`, `ExcelMaster`/`ExcelWriter`, `PptxMaster`/`PptxWriter`).
- Analyze how they execute operations and how we can check their side-effects or return values.
- Verify how CUA, Security, Legal, Memory, Offline, Degradation, and Performance are currently handled or can be mock-run or real-run.
- Inspect the existing `scripts/run_kairoreal_gauntlet.py` and `kairo-sidecar/tests/test_parallel_sandbox.py` or existing tests.

## Phase 2: Design & PRD
- Generate a comprehensive `PROJECT.md` defining the new architecture, interface contracts, and 200 distinct real scenarios.
- Define what constitutes a falsifiable oracle for each domain.
- Define the code layout.

## Phase 3: Scenario Generator / scenarios.json Rebuilding
- Populate `scenarios.json` with the 200 scenarios.
- Ensure all 200 scenarios have status active.
- Verify that `scratch/generate_scenarios.py` is removed.

## Phase 4: Implementation
- Implement the gauntlet runner executors and oracles in `scripts/run_kairoreal_gauntlet.py`.
- Implement `kairo-sidecar/tests/test_kairoreal_gauntlet.py` verifying gauntlet runner and mini-gauntlet run.
- Update `.github/workflows/ci.yml` to gate on `pass_rate_all >= 80%` and 0 skipped.

## Phase 5: Verification & Auditing
- Spawn challenger to execute and verify the full gauntlet runner.
- Spawn reviewer to evaluate code quality, correctness, and adherence to requirements.
- Spawn forensic auditor to check for any integrity violations (hardcoded values, fake mock behaviors, etc.).
- Complete handoff and report to Sentinel.
