## 2026-06-14T14:38:45Z

You are a worker agent. Your working directory is: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\worker_rebuild_gauntlet_v6.
Please rebuild the KairoReal Gauntlet according to these requirements:

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Rebuild scenarios.json:
- Replace scenarios.json at the repository root with 200 distinct, real-world task scenarios (20 per category across the 10 domains: Word, Excel, PPT, Legal, CUA, Security, Memory, Offline, Degradation, Performance).
- Each scenario must contain: 'id' (unique), 'category', 'name', 'description', 'prompt', and a concrete 'expected_outcome' (e.g. expected substrings, formulas, cells, slides, clauses, or error contracts).
- Mark all 200 scenarios status: 'active'.
- Delete scratch/generate_scenarios.py if present.

2. Modify scripts/run_kairoreal_gauntlet.py:
- Update executors (e.g. _exec_word, _exec_excel, etc.) to read prompt and expected_outcome from the scenario.
- Run Kairo's real pipeline/apis:
  * Word: use write_docx() or WordWriter().apply_operations() and verify output file content matches expected substrings.
  * Excel: use write_xlsx() or ExcelWriter().apply_operations() and verify output cell values/formulas.
  * PPT: use write_pptx() and verify slide count, text substrings, and lack of placeholders.
  * Legal: use detect_cuad_clauses() and verify specific expected clauses are detected.
  * CUA: use Python CUAGate class (impl window titles/exec blocklist, coordinate bounds, rate limiters to mirror Rust CuaGate) and verify it blocks/allows correctly.
  * Security: use subprocess to run scripts/ci/eval_integrity_guard.py on clean and violating temp files and check correct exit codes.
  * Memory: use MemSyncManager to record a preference and verify recall.
  * Offline: set KAIRO_OFFLINE=1, reload/invoke sidecar main handle_request and use NetworkSnifferOracle to verify offline_mode: true and zero outbound connections.
  * Degradation: check that handle_request on an unsupported domain returns ok: False and a descriptive error field.
  * Performance: assemble a docx with 500 paragraphs (to stub a 100-page document) and assert WordMaster().extract_context() takes < 2.0s.
- Write task_completion_rate.json with full schema.
- Exit with 0 only if pass_rate_all >= 80% and skipped == 0. Else exit 1.
- No pyautogui, win32api or UI automation.

3. Rebuild kairo-sidecar/tests/test_kairoreal_gauntlet.py:
- Verify that python scripts/run_kairoreal_gauntlet.py is importable, scenario count is 200, all executors exist.
- Run a mini-gauntlet of <=5 scenarios and assert they pass.
- Verify task_completion_rate.json is produced with correct schema.
- Must run and pass cleanly in pytest tests/ run without real UI or network.

4. Update .github/workflows/ci.yml:
- Add a kairoreal-gauntlet job to run python scripts/run_kairoreal_gauntlet.py --output task_completion_rate.json and upload as artifact.
- Gate the production-gate job on this check passing.

Please run the build/tests to verify your work and write a detailed handoff.md in your working directory. Use ECC rules and follow TDD.
