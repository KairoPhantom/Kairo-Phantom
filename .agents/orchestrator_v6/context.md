# Context Registry — KairoReal Gauntlet Rebuild

## Workspace Paths
- Project Root: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`
- Sidecar Root: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\kairo-sidecar`
- Scenarios File: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\scenarios.json`
- Gauntlet Runner: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\scripts\run_kairoreal_gauntlet.py`
- Gauntlet Tests: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\kairo-sidecar\tests\test_kairoreal_gauntlet.py`
- CI/CD Workflow: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.github\workflows\ci.yml`

## Constraints & Rules
1. Replace `scenarios.json` with exactly 200 distinct real-world tasks across 10 domains (Word, Excel, PPT, Legal, CUA, Security, Memory, Offline, Degradation, Performance), 20 each, all marked `"status": "active"`.
2. Delete `scratch/generate_scenarios.py` if present.
3. Modify executors in `scripts/run_kairoreal_gauntlet.py` to invoke actual sidecar APIs/methods (e.g. `WordWriter`, `ExcelWriter`, `detect_cuad_clauses`, etc.) using real inputs and verifying using falsifiable oracles. No simple non-empty/non-crash passes.
4. Output `task_completion_rate.json` at root; exit 0 if and only if `pass_rate_all >= 80%` and `skipped == 0`.
5. No UI automation libraries (`pyautogui`, `win32api`, etc.) in the headless gauntlet script.
6. The pytest test `tests/test_kairoreal_gauntlet.py` must run a mini gauntlet of <=5 scenarios and pass successfully in the headless/CI environment (no real apps/network).
7. CI workflow must contain `kairoreal-gauntlet` job gating the production gate on 80% pass rate.
8. NEVER modify code directly. Always spawn worker subagents.
9. Verify all work with reviewers, challengers, and forensic auditor.

## Verification Checklist
- [ ] 200 scenarios, 10 domains, status: active, expected_outcome present
- [ ] No boilerplate/duplicate scenarios
- [ ] scratch/generate_scenarios.py deleted
- [ ] executors run real sidecar code
- [ ] oracles assert specific text, structure, formulas, values, error codes (falsifiable)
- [ ] run_kairoreal_gauntlet.py runs 200 scenarios and exits 0 on >=80% pass rate
- [ ] pytest tests/test_kairoreal_gauntlet.py passes successfully
- [ ] ci.yml has kairoreal-gauntlet job and gate fails if pass rate < 80%
