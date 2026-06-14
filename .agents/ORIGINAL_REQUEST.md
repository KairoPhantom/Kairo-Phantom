# Original User Request

## Initial Request — 2026-06-12T16:10:41Z

Hardening Kairo Phantom to GA Production-Ready status by implementing remaining items across Calibration, Hardening, Production-Ops, and Autonomous Gauntlet Infrastructure.

Working directory: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom
Integrity mode: development

## Requirements

### R1. Calibration & Trust (Sprint 4)
- **1.1 Confidence Unification (Item 20)**: Collapse `confidence.rs` into `memory::feedback::ConfidenceEngine` for a unified API.
- **1.2 E2E Measurement CI Job (Item 22)**: Set up a CI job that runs scenarios on a real display and publishes `task_completion_rate.json`.
- **1.3 Response Validator Hard Block (Item 26)**: Promote irrelevant responses (below a configurable relevance floor) to a hard `ValidationFailure` triggering regeneration.
- **1.4 Calibrated Uncertainty (Item 27)**: Implement clarification prompts/abstention when confidence falls below the calibrated uncertainty threshold.
- **1.5 Document Constitution (Item 28)**: Validate all output against a plain-English, user-editable constitution in `response_validator.rs`.
- **1.6 Verifiable-Work Receipts (Item 29)**: Cryptographically sign every execution trail using a hash chain.

### R2. Hardening & Release Readiness (Sprint 5)
- **2.1 Signed Updates (Item 23)**: Integrate Ed25519 signatures and SHA-256 checks in `updater.py`.
- **2.2 Remove pro.rs Stub (Item 24)**: Return a clear "Unavailable" error rather than a silent success.
- **2.3 Thin Domain Capabilities (Item 30)**: Ensure all thin expert domains correctly report `PromptOnly` capabilities and strip them from public marketing endpoints.
- **2.4 Best-of-N Oracle Selection (Item 31)**: Score N candidates at inference time using the newly implemented deterministic docx/xlsx/pptx/pdf oracles and return the best.
- **2.5 Adaptive Compute (Item 32)**: Estimate task difficulty and dynamically allocate thinking/reasoning budget.

### R3. Production Ops Layer (Sprint 5.5)
- **3.1 Auto-Update Rollback (Item 54)**: Ensure update rollbacks on health check failure.
- **3.2 Crash Reporting (Item 55)**: symbolicated stack trace collection with PII-scrubbing, disabled in air-gap mode.
- **3.3 Observability (Item 56)**: OpenTelemetry local instrumentation, zero outbound in air-gap mode.
- **3.4 Security & Dependency Gates (Item 57 & 58)**: Integrate Syft (SBOM), cargo-audit, Gitleaks, and fail CI on finding secrets or severe CVEs.

### R4. Autonomous Gauntlet Infrastructure (Sprint 6 & 7)
- **4.1 Sandbox & Parallel Runner (Item 33)**: Build Hyper-V/Vagrant snapshot reset scripting and pytest-xdist runner.
- **4.2 Test-Fix-Test Loop (Item 35)**: Build a bounded loop with the 4 guardrails (protected paths, oracle immutability, regression gate, convergence detection).
- **4.3 No-Skip Gates (Item 36)**: Integrate mutation testing (cargo-mutants, mutmut) and strictly fail CI on skipped/fake tests.
- **4.4 Verified Outcome Store (Item 37)**: DuckDB database schema + Gymnasium `KairoDocEnv` wrapper.
- **4.5 Synthetic Personas & Judging (Item 38 & 39)**: Stand up the 7 user persona-agents and the 4-tier judging hierarchy.
- **4.6 Drift Alarm (Item 40)**: Drift monitoring checking synthetic vs human calibration with automatic training freeze.

## Acceptance Criteria

### Verification & Testing
- [ ] Confidence API unified and all references compiled successfully.
- [ ] Low-relevance output triggers regeneration instead of warning logs.
- [ ] Document constitution successfully flags unauthorized edits.
- [ ] Updates with invalid signatures or modified SHA-256 checksums are rejected.
- [ ] pro.rs functions return clean errors when pro features are requested.
- [ ] IPC, sidecar, and core tests pass with 100% success rate.
- [ ] Drift alarm triggers freeze correctly when gap exceeds threshold.

## Follow-up — 2026-06-14T04:04:23Z

Extend the Kairo Phantom production hardening to implement a **headless KairoReal
200-scenario gauntlet runner** that executes all 200 scenarios from `scenarios.json`
through the Python sidecar layer (no UI automation), produces `task_completion_rate.json`,
and gates the CI pipeline on ≥80% pass rate.

Working directory: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`
Integrity mode: development

## Context & Infrastructure

The following already exists — build on it, do not recreate it:

- `scenarios.json` (repo root): 200 scenarios with fields `id, category, name, description, prompt, status, fix_budget`.
  - Status breakdown: 50 `active`, 100 `pending`, 50 `excluded`
  - 10 categories × 20 scenarios: `Word, Excel, PPT, Legal, CUA, Security, Memory, Offline, Degradation, Performance`
- `kairo-sidecar/sidecar/sandbox_runner.py`: `SandboxRunner` class for parallel disposable sandboxes.
- `kairo-sidecar/sidecar/oracle_dispatcher.py`: `dispatch(oracle_name, sandbox_path, scenario)` → `{verdict, reason}`.
- `kairo-sidecar/sidecar/scenario_store.py`: DuckDB-backed store for seeding and recording results.
- `kairo-sidecar/sidecar/masters/`: `WordMaster`, `ExcelMaster`, `PptxMaster` for document ops.
- `kairo-sidecar/sidecar/main.py`: action dispatcher (action `self_check` is available).
- `scripts/run_sequential_gauntlet.py`: existing gauntlet that uses UI automation — **do not modify**.
- `MASTER_GAUNTLET_REPORT_v3.json`: baseline reference (52 scenarios, 92.31% on those tested).
- `kairo-sidecar/tests/test_parallel_sandbox.py`: reference for how to wire `SandboxRunner` + oracles in tests (381 passing).

## Requirements

### R1. Headless KairoReal Gauntlet Script

Create `scripts/run_kairoreal_gauntlet.py` that:

- Loads all 200 scenarios from `scenarios.json` (repo root).
- For each scenario, applies the appropriate headless executor based on `category`:
  - `Word`, `Excel`, `PPT`: route to the corresponding sidecar master (`WordMaster`, `ExcelMaster`, `PptxMaster`), run the scenario prompt as a document operation, and verify the output file was written correctly.
  - `Legal`: invoke the legal redline parser and verify tracked-change markers are present.
  - `CUA`: verify the CUA gate correctly blocks/allows based on prompt content (no real UI open — use the gate logic directly).
  - `Security`: invoke `SecurityAuditor` and confirm strict mode blocks or allows correctly.
  - `Memory`: write a preference to `MemSyncManager` and verify recall succeeds.
  - `Offline`: set `KAIRO_OFFLINE=1` and verify the sidecar's `self_check` reports `offline_mode: true` and no external calls are made.
  - `Degradation`: verify that missing-domain errors surface correctly (check `ok: False` + descriptive `error` field).
  - `Performance`: verify context assembly for a 100-page document stub completes within 2 seconds.
- Scenarios with `status == "excluded"` are **skipped** (counted as skipped, not passed/failed).
- Scenarios with `status == "pending"` are run; if the executor is not yet implemented for that category, the scenario records `SKIP` (not FAIL). The script must not crash on pending scenarios.
- Output `task_completion_rate.json` in the repo root with this schema:

```json
{
  "product": "Kairo Phantom",
  "gauntlet_version": "kairoreal-headless-v1",
  "run_at": "<ISO timestamp>",
  "elapsed_seconds": 0.0,
  "total": 200,
  "active": 50,
  "pending": 100,
  "excluded": 50,
  "passed": 0,
  "failed": 0,
  "skipped": 0,
  "pass_rate_active": 0.0,
  "pass_rate_all": 0.0,
  "verdict": "PASS | FAIL | PARTIAL",
  "gate_threshold": 80.0,
  "categories": {
    "Word":   {"total": 20, "active": 5, "passed": 0, "failed": 0, "skipped": 0},
    "...": {}
  },
  "results": [
    {"id": "W1", "category": "Word", "status": "active", "oracle_verdict": "PASS", "reason": "...", "elapsed_s": 0.0},
    "..."
  ]
}
```

- Exit 0 if `pass_rate_active ≥ 80%`; exit 1 otherwise.
- Must work in a **headless/CI environment** with no open applications, no display, no network.
- Runs with: `python scripts/run_kairoreal_gauntlet.py [--workers N] [--output path]`

### R2. Pytest Test for Gauntlet Scaffold

Create `kairo-sidecar/tests/test_kairoreal_gauntlet.py` that:

- Verifies `scripts/run_kairoreal_gauntlet.py` is importable and the scenario count is 200.
- Runs a **mini gauntlet** of ≤5 scenarios (sampled from `active` across ≥2 categories) through the real executor and asserts all pass.
- Verifies `task_completion_rate.json` is produced with the correct schema after a run.
- Must pass in the existing `pytest tests/` run without requiring real apps or network.

### R3. CI Job — KairoReal Gauntlet Gate

Add a `kairoreal-gauntlet` job to `.github/workflows/ci.yml` that:

- Runs **after** the `build` job and **in parallel** with other non-dependent jobs.
- Sets up Python 3.12, installs `kairo-sidecar` dependencies.
- Runs: `python scripts/run_kairoreal_gauntlet.py --output task_completion_rate.json`
- Uploads `task_completion_rate.json` as a CI artifact (`retention-days: 30`).
- **Fails the job** if exit code is non-zero (i.e., pass_rate_active < 80%). No `|| true`.
- On the `production-gate` job: add a step that verifies `pass_rate_active` from the JSON is ≥ 80%.

## Acceptance Criteria

### Gauntlet Script
- [ ] `scripts/run_kairoreal_gauntlet.py` exists and loads all 200 scenarios from `scenarios.json`.
- [ ] Running `python scripts/run_kairoreal_gauntlet.py` exits 0 when active-scenario pass rate ≥ 80%.
- [ ] `task_completion_rate.json` is produced with the full schema above after every run.
- [ ] All 10 category executor functions exist (some may return SKIP for pending scenarios, none crash).
- [ ] The script does not import `pyautogui`, `win32api`, or any UI automation library.
- [ ] `pass_rate_active` reported is ≥ 80% on the actual run.

### Test Coverage
- [ ] `tests/test_kairoreal_gauntlet.py` passes in `pytest tests/` with no network or UI required.
- [ ] The mini gauntlet (≤5 scenarios) runs end-to-end and all pass.
- [ ] The full regression suite (`pytest tests/`) still passes at 381+ tests.

### CI Integration
- [ ] `.github/workflows/ci.yml` contains a `kairoreal-gauntlet` job.
- [ ] The job uploads `task_completion_rate.json` as a CI artifact.
- [ ] The `production-gate` job fails if `pass_rate_active < 80%`.

## Follow-up — 2026-06-14T14:28:35Z

Rebuild the KairoReal Gauntlet to make it honest, replacing scenarios.json with 200 distinct real-world tasks across 10 domains and updating run_kairoreal_gauntlet.py to run the real sidecar pipeline and verify results using falsifiable oracles.

Working directory: C:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom
Integrity mode: demo

## Requirements

### R1. Real scenarios in scenarios.json
- Replace the existing `scenarios.json` with 200 distinct, real-world task scenarios (20 per category across the 10 domains: Word, Excel, PPT, Legal, CUA, Security, Memory, Offline, Degradation, Performance).
- Each scenario must contain a unique `id`, `category`, `name`, `description`, `prompt`, and a concrete `expected_outcome` (e.g. expected paragraphs, cells, slides, clauses, or error contracts).
- All 200 scenarios must be marked `"status": "active"` so they are all executed.
- Delete `scratch/generate_scenarios.py` if present.

### R2. Scenario-aware executors in run_kairoreal_gauntlet.py
- Modify the executors (e.g. `_exec_word`, `_exec_excel`, etc.) to read the scenario's `prompt` and `expected_outcome`.
- Run Kairo's *real* end-to-end pipeline (e.g., calling actual sidecar APIs/methods like `WordWriter().apply_operations()`, `ExcelWriter`, `detect_cuad_clauses`, etc.) using the scenario input.
- Reject any simple pass/fail checks that pass on any non-empty or non-crashed output.
- Expected outcomes must come from real-world ground truth, not from whatever the current code happens to emit.

### R3. Falsifiable oracles
- Verify the generated files/outputs programmatically against the expected outcomes.
- For Word/Excel/PPT, open the generated `.docx`/`.xlsx`/`.pptx` and assert specific structure, paragraphs, formulas, or values.
- For Legal, verify that specific expected clauses are detected.
- For Degradation, assert a specific error contract/code/message.
- For Security, run the integrity guard against a set of actual files and verify the correct output.
- All oracles must be falsifiable (i.e. if we pass incorrect/empty inputs, they must fail).

### R4. Honest results
- Prove the gauntlet works by reporting the honest `pass_rate_all`. If some scenarios are unimplemented or fail, they must show as `FAIL` and decrease `pass_rate_all`.
- The runner must write a detailed `task_completion_rate.json` and exit with 0 only if `pass_rate_all >= 80%` and `skipped == 0`.

## Acceptance Criteria

### Scenarios
- [ ] `scenarios.json` contains exactly 200 distinct scenarios with real prompts and expected outcomes.
- [ ] No boilerplate prompts or duplicate scenarios.
- [ ] `scratch/generate_scenarios.py` is deleted.

### Executors & Oracles
- [ ] Executors run real sidecar code on the scenario prompts.
- [ ] Oracles verify specific expected outcomes (e.g. word paragraphs, excel cells, ppt slides) rather than just "non-None".
- [ ] Oracles are falsifiable (asserting specific text, numbers, structure, or errors).

### Execution
- [ ] Running `python scripts/run_kairoreal_gauntlet.py` runs all 200 scenarios.
- [ ] Reports the honest `pass_rate_all` in `task_completion_rate.json`.
- [ ] Exits with 0 if and only if `pass_rate_all >= 80%` and `skipped == 0` (or exits 1 if the gate fails).
- [ ] `pytest kairo-sidecar/tests/test_kairoreal_gauntlet.py` passes successfully.
