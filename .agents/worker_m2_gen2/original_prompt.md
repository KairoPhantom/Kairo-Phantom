## 2026-06-08T17:48:00Z
You are teamwork_preview_worker.
Your role is: python-docx Write-Back Integrator.
Your working directory is: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\worker_m2_gen2\

YOUR TASKS:
1. Update `kairo-sidecar/sidecar/writers/docx_writer.py`:
   - Refactor the save and replace blocks in `write_docx`.
   - In case of `PermissionError` or general `Exception`, restore from backup `shutil.copy2(str(backup_path), str(path))` and clean up the backup and temporary files (`tmp_path.unlink()`).
   - Clean up `backup_path` only when the save/replace was successful and there are no errors.

2. Update `kairo-sidecar/sidecar/writers/pptx_writer.py`:
   - Refactor the save and replace blocks in `write_pptx`.
   - In case of `PermissionError` or general `Exception`, restore from backup `shutil.copy2(str(backup_path), str(path))` and clean up the backup and temporary files (`tmp_path.unlink()`).
   - Clean up `backup_path` only when the save/replace was successful and there are no errors.

3. Update `kairo-sidecar/sidecar/prompt_builder.py`:
   - Ensure the wrapper `build_word_prompt` passes `app_name="Microsoft Word"` and `app_type="Word Processor"` explicitly in the call to `_build_word` to prevent default value overrides.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

TESTING:
- Run `pytest` or `python -m pytest` inside `kairo-sidecar` directory. Specifically verify that `tests/test_word_master.py` passes.
- Run `python pr_gate_runner.py` inside `kairo-sidecar` directory to verify gates.
- Report all test results and output in your handoff.

HANDOFF:
- Create `progress.md` and `handoff.md` in your working directory.
- Send a message to the orchestrator (conversation ID: 5c9a2074-8886-4eb9-9564-e98f5b57bcad) with the paths to these files and a summary of your results.
