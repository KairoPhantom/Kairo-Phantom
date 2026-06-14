## 2026-06-14T04:14:54Z

Your working directory is: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\worker_implement_gauntlet.
Your mission is to implement:
1. Headless KairoReal gauntlet script at `scripts/run_kairoreal_gauntlet.py`
2. Pytest test for gauntlet scaffold at `kairo-sidecar/tests/test_kairoreal_gauntlet.py`
3. CI job integration in `.github/workflows/ci.yml`

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Detailed Implementation Requirements:

1. `scripts/run_kairoreal_gauntlet.py`:
- Load all 200 scenarios from `scenarios.json` at repo root.
- Command-line arguments: `python scripts/run_kairoreal_gauntlet.py [--workers N] [--output path]` (default output: `task_completion_rate.json`).
- If scenario status is "excluded", skip it (verdict: SKIP).
- If scenario status is "pending", record as SKIP (not FAIL) with appropriate reason.
- If scenario status is "active", run the headless executor based on `category`:
  - `Word`: Use `WordMaster` to parse/apply operations on a temporary docx file and verify the output was written.
  - `Excel`: Use `ExcelMaster` to write cells on a temporary xlsx file and verify cell value is updated.
  - `PPT`: Use `PowerPointMaster` to update titles on a temporary pptx file and verify title is updated.
  - `Legal`: Invoke the legal redline parser (`analyze_contract`), check suggested_redlines, and verify tracked-change settings (trackRevisions) on a document.
  - `CUA`: Implement gate logic checks based on prompt content (e.g. block prompts containing Task Manager, Registry Editor, etc., allow otherwise).
  - `Security`: Define/use `SecurityAuditor` in sidecar (e.g., `sidecar/security_auditor.py` or within sidecar package) checking for confidential, trade secret, internal use only, proprietary. Verify strict mode raises ValueError, and non-strict mode redacts.
  - `Memory`: Expose `MemSyncManager` in sidecar (e.g., `sidecar/mem_machine.py`) wrapping `MemMachineClient`'s record_interaction/query. Save preference and verify recall.
  - `Offline`: Set `KAIRO_OFFLINE=1`, verify sidecar `self_check` response has `offline_mode: True`, verify `check_for_update` in sidecar/updater.py returns None and does not perform urlopen.
  - `Degradation`: Set `sidecar.main.DOMAIN1_AVAILABLE = False` temporarily, invoke a docx action, assert return has `ok: False` and a descriptive error field.
  - `Performance`: Instantiate `ContextAssembler`, assemble a 100-page preloaded context (paragraphs index 1 to 100), and assert latency is < 2.0 seconds.
- Write report to `--output` path (e.g. task_completion_rate.json) matching the schema requested.
- Exit code 0 if `pass_rate_active >= 80%`, else 1.

2. `kairo-sidecar/tests/test_kairoreal_gauntlet.py`:
- Verify `scripts/run_kairoreal_gauntlet.py` is importable and has scenario count 200.
- Execute a mini gauntlet of <=5 scenarios (sampled from active across >=2 categories) using the real runner/executor functions and assert they all pass.
- Verify `task_completion_rate.json` matches the required schema and contains all fields.

3. `.github/workflows/ci.yml`:
- Add `kairoreal-gauntlet` job that runs after `headless-checks`.
- Set up Python 3.12, install dependencies (`pip install -r kairo-sidecar/requirements.txt pytest`), run `python scripts/run_kairoreal_gauntlet.py --output task_completion_rate.json`.
- Upload artifact `task_completion_rate.json` with `retention-days: 30`.
- In `production-gate` job: add `kairoreal-gauntlet` to `needs`, download `gauntlet-report` artifact, and run a python assert verifying that `pass_rate_active` is >= 80.0%.

4. Verification:
- Run the newly created test using pytest.
- Ensure the full regression suite (`pytest kairo-sidecar/tests/`) still compiles and passes (381+ tests).

When done, write a detailed handoff report to handoff.md in your working directory.
