# Handoff Report — worker_m3_fixes

## 1. Observation

- **Encoding issue in Python optimizer script**:
  - Exact file path: `scripts/training/dspy_prompt_optimizer.py`
  - In `run_kmb1_benchmark()`, lines 34-40 originally ran `subprocess.run` to call cargo test on `kmb1_benchmark` without an explicit encoding parameter:
    ```python
    res = subprocess.run(
        ["cargo", "test", "--test", "kmb1_benchmark", "--", "--nocapture"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False
    )
    ```
  - Running this on Windows causes `UnicodeDecodeError` because the benchmark's console output uses UTF-8 emojis (`✅`, `🏆`, `📊`) and decorative characters (`━━`), whereas Windows defaults to the system's ANSI code page (e.g. `cp1252`).

- **Redundant index-skipping in DocumentGraph**:
  - Exact file path: `phantom-core/src/memory/document_graph.rs`
  - In `index_directory`, lines 74-80 originally contained:
    ```rust
    let exists: bool = {
        let mut stmt = conn.prepare("SELECT 1 FROM nodes WHERE id = ?1")?;
        stmt.exists(params![file_id])?
    };
    if exists {
        continue;
    }
    ```
  - This logic simply skipped re-indexing if `file_id` was present in the database, ignoring whether the document content had been modified.

- **Cargo Test and Optimizer run outputs**:
  - All workspace tests passed: `test result: ok. 41 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out`
  - KMB-1 recall tests passed: `test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out`
  - Running the optimizer with `python scripts/training/dspy_prompt_optimizer.py` completed successfully:
    ```
    2026-06-08 21:57:57,653 [WARNING] DSPy package is not available. Using simulated prompt optimization fallback.
    2026-06-08 21:57:57,653 [INFO] Running kmb1_benchmark integration tests...
    2026-06-08 21:57:58,860 [INFO] Parsed KMB-1 Score from leaderboard: 1.0000
    2026-06-08 21:57:58,860 [INFO] Initial kmb1_benchmark baseline score: 1.0000
    2026-06-08 21:57:58,860 [INFO] Running simulated prompt optimization pass...
    2026-06-08 21:57:58,863 [INFO] Successfully saved optimized prompt to C:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\skills\feynman-verifier\SKILL.md
    2026-06-08 21:57:58,863 [INFO] Running kmb1_benchmark integration tests...
    2026-06-08 21:58:00,229 [INFO] Parsed KMB-1 Score from leaderboard: 1.0000
    2026-06-08 21:58:00,229 [INFO] Final optimized kmb1_benchmark score: 1.0000
    2026-06-08 21:58:00,229 [INFO] Optimization successful.
    ```

## 2. Logic Chain

1. To prevent the `UnicodeDecodeError` on Windows systems during the optimizer execution, we must force the decoding process to interpret the stdout/stderr stream using UTF-8 and safely ignore any invalid/unmappable sequences. Adding `encoding="utf-8"` and `errors="ignore"` to the `subprocess.run` call guarantees this.
2. In order to implement clean file re-indexing on modification, we must compare the freshly extracted text of the file against the previously stored content in the SQL database.
3. If they are identical, it is safe to skip indexing.
4. If they differ (or if the file is new), we must clean up the document node and any existing outbound relationship edges first (`DELETE FROM nodes WHERE id = ?1` and `DELETE FROM edges WHERE source = ?1`) before proceeding to the LLM extraction logic. This avoids duplicate/stale entities and edges.
5. To test this behavior, we added a mock AI backend with state (using `AtomicUsize`) to output different extracted entities across multiple indexing runs and asserted that the old edges are correctly deleted and replaced in the SQLite database.

## 3. Caveats

- We assumed that the extractor registry behaves deterministically and does not fail intermittently for the same file structure.
- Entity nodes themselves are inserted with `INSERT OR IGNORE` and are not deleted from the database even if they have no remaining edges. This matches the spec and database model where entity definitions persist, but their relationships (edges) to specific modified documents are cleaned up and replaced.

## 4. Conclusion

The Windows encoding issue in `scripts/training/dspy_prompt_optimizer.py` has been resolved. The document graph in `phantom-core/src/memory/document_graph.rs` has been successfully updated to perform change-aware re-indexing, safely replacing old nodes and edges. All cargo tests compile and pass successfully, and a new unit test verifies the correctness of the database cleanup during re-indexing.

## 5. Verification Method

To independently verify the changes, execute the following commands in the workspace root directory (`c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`):

1. **Verify Rust Test Suite**:
   ```powershell
   cargo test
   ```
   All tests, including the new `unit_document_graph_reindexing_on_modification` test in `layer1_unit_tests`, must compile and pass successfully.

2. **Verify Memory Recall Benchmark**:
   ```powershell
   cargo test --test kmb1_benchmark
   ```
   All 3 benchmark tests must pass successfully.

3. **Verify DSPy Optimizer Script Run**:
   ```powershell
   python scripts/training/dspy_prompt_optimizer.py
   ```
   The script must run without raising any Unicode/decoding exceptions on Windows and complete successfully.
