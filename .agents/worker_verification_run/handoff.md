# Handoff Report

## 1. Observation
We ran three verification commands within the repository root `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`:

### Run 1: PR Gate Runner
Command: `python kairo-sidecar/pr_gate_runner.py`
Exit Code: `0`
Output:
```
DebounceGuard: debounced request (elapsed=10.5ms < 200.0ms)
DebounceGuard: debounced request (elapsed=21.8ms < 200.0ms)
DebounceGuard: debounced request (elapsed=32.6ms < 200.0ms)
DebounceGuard: debounced request (elapsed=43.3ms < 200.0ms)
DebounceGuard: debounced request (elapsed=54.1ms < 200.0ms)
DebounceGuard: debounced request (elapsed=64.9ms < 200.0ms)
DebounceGuard: debounced request (elapsed=75.8ms < 200.0ms)
DebounceGuard: debounced request (elapsed=86.4ms < 200.0ms)
DebounceGuard: debounced request (elapsed=97.0ms < 200.0ms)
Running PR-01...
  PASS — style=Heading 2
Running PR-02...
  PASS — Before=3 After=3 (equal)
Running PR-03...
  PASS — Clean output passed (no false positives). Leaked keywords [waza_agent, memmachine, waza+ghost-writer] ALL detected. System prompt internals never appear in GRP.
Running PR-04...
  PASS — Zero external connections attempted during DomainMasterRouter init + core module imports. netstat -n | findstr ESTABLISHED | findstr -v 127.0.0.1 = (empty)
Running PR-05...
  PASS — Before=dd972fcb31d2d8bb... After-inject (different)=50518424dd045b6b... After-undo=dd972fcb31d2d8bb... (Before==After-undo: file fully restored)
Running PR-06...
  PASS — Changed cells besides target D2: NONE. Target D2==IFERROR((B2-C2)/B2,0)
Running PR-07...
  PASS — Pre-op hash=c5f471a5059571a4... Post-kill hash=c5f471a5059571a4... (equal — atomic save protected file)
Running PR-08...
  PASS — Context assembly (5 runs): [0.05, 0.01, 0.0, 0.0, 0.0]ms [all <100ms = leaves 500ms+ margin for 2000ms first-token target]
Running PR-09...
  MANUAL REQUIRED — Requires fresh Windows 11 VM snapshot + KairoSetup.exe. Cannot be measured programmatically. Target: <120s from setup start to first working Alt+M.
Running PR-10...
  PASS — Programmatic Alt+M stress test: 10 presses in <0.2s. Allowed=1, Denied=9 (debounce guard successfully enforced single dispatch).
Running PR-11...
  PASS — Correct=49/49 (100.0%) domain detections
Running PR-12...
  PASS — Session 2 GRP output reflects Session 1 style preference. Recalled context contains: bullets=YES, sign-off=YES. Excerpt: '[MemMachine — word style history for local]
— insert: User prefers bullet points. Uses 'Best regards' sign-off....'
Running PR-13...
  PASS — Score=0.494 [avg record=5.62ms/op, avg query=0.68ms/op over 100 ops]
Running PR-14...
  PASS — 0.045s (45ms) context prep for ~210-para doc (extract=29ms + assemble=16ms) — leaves full 2000ms budget for 7B model first-token

======================================================================
KAIRO PHANTOM — 14-GATE PRODUCTION CERTIFICATION REPORT
======================================================================

PR-01: [PASS — style=Heading 2]
PR-02: [PASS — Before=3 After=3 (equal)]
PR-03: [PASS — Clean output passed (no false positives). Leaked keywords [waza_agent, memmachine, waza+ghost-writer] ALL detected. System prompt internals never appear in GRP.]
PR-04: [PASS — Zero external connections attempted during DomainMasterRouter init + core module imports. netstat -n | findstr ESTABLISHED | findstr -v 127.0.0.1 = (empty)]
PR-05: [PASS — Before=dd972fcb31d2d8bb... After-inject (different)=50518424dd045b6b... After-undo=dd972fcb31d2d8bb... (Before==After-undo: file fully restored)]
PR-06: [PASS — Changed cells besides target D2: NONE. Target D2==IFERROR((B2-C2)/B2,0)]
PR-07: [PASS — Pre-op hash=c5f471a5059571a4... Post-kill hash=c5f471a5059571a4... (equal — atomic save protected file)]
PR-08: [PASS — Context assembly (5 runs): [0.05, 0.01, 0.0, 0.0, 0.0]ms [all <100ms = leaves 500ms+ margin for 2000ms first-token target]]
PR-09: [MANUAL REQUIRED — Requires fresh Windows 11 VM snapshot + KairoSetup.exe. Cannot be measured programmatically. Target: <120s from setup start to first working Alt+M.]
PR-10: [PASS — Programmatic Alt+M stress test: 10 presses in <0.2s. Allowed=1, Denied=9 (debounce guard successfully enforced single dispatch).]
PR-11: [PASS — Correct=49/49 (100.0%) domain detections]
PR-12: [PASS — Session 2 GRP output reflects Session 1 style preference. Recalled context contains: bullets=YES, sign-off=YES. Excerpt: '[MemMachine — word style history for local]
— insert: User prefers bullet points. Uses 'Best regards' sign-off....']
PR-13: [PASS — Score=0.494 [avg record=5.62ms/op, avg query=0.68ms/op over 100 ops]]
PR-14: [PASS — 0.045s (45ms) context prep for ~210-para doc (extract=29ms + assemble=16ms) — leaves full 2000ms budget for 7B model first-token]

TOTAL AUTOMATED: [13/13 passed]
MANUAL (require live UI): [1/14] — PR-09
ALL AUTOMATED CHECKS: [13/13]

LAUNCH DECISION: READY (all automated gates pass; manual UI checks pending)
```

### Run 2: Creators Unit Tests
Command: `$env:PYTHONPATH="kairo-sidecar"; python -m pytest kairo-sidecar/tests/test_creators.py -v`
Exit Code: `0`
Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.0, pytest-9.0.3, pluggy-1.6.0 -- C:\Program Files\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom
plugins: anyio-4.12.1, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 6 items

kairo-sidecar/tests/test_creators.py::test_docx_creator PASSED           [ 16%]
kairo-sidecar/tests/test_creators.py::test_docx_creator_create_and_open PASSED [ 33%]
kairo-sidecar/tests/test_creators.py::test_xlsx_creator PASSED           [ 50%]
kairo-sidecar/tests/test_creators.py::test_xlsx_creator_create_and_open PASSED [ 66%]
kairo-sidecar/tests/test_creators.py::test_pptx_creator PASSED           [ 83%]
kairo-sidecar/tests/test_creators.py::test_pptx_creator_create_and_open PASSED [100%]

============================== 6 passed in 0.72s ==============================
```
*(Note: Initial invocation of `python -m pytest kairo-sidecar/tests/test_creators.py -v` without `PYTHONPATH` failed with `ModuleNotFoundError: No module named 'sidecar'` because the test targets elements inside the `kairo-sidecar` directory. Setting `PYTHONPATH=kairo-sidecar` resolves this).*

### Run 3: Schema Compliance Evaluation
Command: `python scripts/eval_schema_compliance.py`
Exit Code: `0`
Output:
```
2026-06-09 01:21:34,536 INFO Evaluating DocxOperation: 5 prompts on model='kairo-standard'
2026-06-09 01:21:44,830 INFO Evaluating ExcelOperation: 5 prompts on model='kairo-standard'
2026-06-09 01:21:55,086 INFO Evaluating SlideOperation: 5 prompts on model='kairo-standard'

Kairo Schema Compliance Evaluation
Model: kairo-standard  |  Samples per group: 5
============================================================

DocxOperation:
  Passed : 5/5
  Rate   : 100.0%

ExcelOperation:
  Passed : 5/5
  Rate   : 100.0%

SlideOperation:
  Passed : 5/5
  Rate   : 100.0%

============================================================
Composite Score  : 1.0000
Compliance Rate  : 100.0%
Gate Threshold   : 95.0%
Gate             : PASS [PASS] (100.0% >= 95%)
ACTION: Replace kairo-standard with kairo-fast in litellm_config.yaml
```

## 2. Logic Chain
1. We successfully ran `python kairo-sidecar/pr_gate_runner.py` which executes the 14-gate suite. The execution concluded with `13/13 automated checks passed`, exiting with 0. The remaining gate `PR-09` is a manual VM task that cannot be automated.
2. The unit tests command `python -m pytest kairo-sidecar/tests/test_creators.py -v` initially failed due to `ModuleNotFoundError: No module named 'sidecar'`. Since the module `sidecar` resides in `kairo-sidecar/sidecar`, setting the `PYTHONPATH` environment variable to `kairo-sidecar` allows `import sidecar` to resolve. Running with `$env:PYTHONPATH="kairo-sidecar"; python -m pytest kairo-sidecar/tests/test_creators.py -v` succeeded with all 6 tests passing (exit code 0).
3. The evaluation script `python scripts/eval_schema_compliance.py` ran successfully. It evaluated 15 prompts (5 for DocxOperation, 5 for ExcelOperation, 5 for SlideOperation) on model `kairo-standard`. It recorded a 100% compliance rate (Composite Score: 1.0000), which exceeds the 95% gate threshold.

## 3. Caveats
- `PR-09` requires manual GUI verification under a live VM, so it was excluded from the automated runner's success count (as expected).
- The creators unit tests require `PYTHONPATH` environment configuration to locate the `sidecar` module when run from the root of the workspace.

## 4. Conclusion
All three verification commands passed successfully with exit code 0. No code errors or regressions were detected in the automated suite.

## 5. Verification Method
To reproduce and verify the outcomes independently, execute the following commands in the workspace root:
1. `python kairo-sidecar/pr_gate_runner.py` (Expected: 13/13 automated gates passed, 0 failures, exit code 0).
2. `$env:PYTHONPATH="kairo-sidecar"; python -m pytest kairo-sidecar/tests/test_creators.py -v` (Expected: 6 passed in <1s, exit code 0).
3. `python scripts/eval_schema_compliance.py` (Expected: Composite Score 1.0000, 100.0% compliance rate, exit code 0).
