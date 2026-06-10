## 2026-06-07T05:15:52Z
Please perform the following implementation tasks:

1. Create a `PROJECT.md` file at the workspace root (`c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\PROJECT.md`) using the exact content from `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\orchestrator\PROJECT.md`.
2. Apply the performance optimization in `kairo-sidecar/sidecar/masters/word_master.py`:
   - Locate the function `_detect_document_purpose` and the line:
     `all_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())`
   - Modify it to slice the first 50 paragraphs to avoid a performance bottleneck on large documents:
     `all_text = "\n".join(p.text for p in doc.paragraphs[:50] if p.text.strip())`
3. Modify `phantom-overlay/src-tauri/Cargo.toml` to disable testing for `phantom_overlay_lib`:
   - Under the `[lib]` section:
     ```toml
     [lib]
     name = "phantom_overlay_lib"
     crate-type = ["rlib"]
     ```
   - Add `test = false` and `doctest = false` to prevent cargo test from executing window/UI initialization routines in headless/CI test environments:
     ```toml
     [lib]
     name = "phantom_overlay_lib"
     crate-type = ["rlib"]
     test = false
     doctest = false
     ```
4. Verify your changes:
   - Run the Python unit tests for the word master: `python -m pytest tests/test_word_master.py -v` inside `kairo-sidecar`. Ensure all tests pass, especially `test_large_document_parsing_performance` under 0.8s.
   - Run the Rust test suite: `cargo test --workspace` to ensure all workspace tests pass without the `STATUS_ACCESS_VIOLATION` crash.
   - Run the production gate runner script: `python pr_gate_runner.py` at the workspace root to ensure all automated gate checks pass.
5. Write your implementation report and handoff details (including test command outputs and layout checks) to `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\worker_m1_m2\handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
