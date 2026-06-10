# Handoff Report - explorer_v2_1

This report presents a self-contained compliance audit of the `kairo-phantom` repository against the v3.9.0 requirements.

---

## 1. Observation

### Test Suite Execution
- **Command Run**: `python -m pytest kairo-sidecar/tests/`
- **Output**: 
  ```
  ================== 261 passed, 1 warning in 63.65s (0:01:03) ==================
  ```
  All 261 tests passed without any failures or errors.

### Prompt Variable Injection Order & JSON Reminder (Tasks 2 & 3)
- **Word (`word_prompt_builder.py`)**:
  - Variable order: App context, Doc context, Mem context, Classification, User instruction last.
  - JSON reminder: Lacks the exact JSON reminder immediately before the user instruction.
- **Excel (Modern: `excel_master.py`)**:
  - Prompt construction:
    ```python
    === APP CONTEXT ===
    ...
    === DOCUMENT CONTEXT ===
    ...
    === MEMORY CONTEXT ===
    ...
    === INTENT CLASSIFICATION ===
    ...
    REMINDER: Your entire response must be a single JSON object. First character must be {{. Last character must be }}.
    USER INSTRUCTION:
    {user_prompt}
    ```
  - Both injection order and JSON reminder are present and compliant.
- **Excel (Legacy: `prompt_builder.py`)**:
  - Prompt construction is identical to modern; both order and JSON reminder are present and compliant.
- **PowerPoint, Code, PDF, Media (`other_masters.py`)**:
  - Follow the format: App context -> Doc context -> Mem context -> Classification -> JSON Reminder -> User instruction last. Fully compliant.
- **Browser, Terminal, Email, Notes, Design (`other_masters.py`)**:
  - Use custom monolithic context blocks (e.g. `WEB CONTEXT`, `SHELL CONTEXT`, etc.). Lacks the distinct App context/Doc context separation, Mem context separation, and Classification blocks. Lacks the JSON reminder before the user instruction. Non-compliant.
- **Data (`other_masters.py`)**:
  - Uses App, Doc, Mem, and JSON reminder, but completely lacks any Classification block. Non-compliant.

### `llm_caller.py` JSON Decode / Retry Logic (Task 4)
- **Code Segment**:
  ```python
  except json.JSONDecodeError as decode_err:
      log.warning(f"Attempt {attempt} JSON decode error: {decode_err}")
      if attempt == 1:
          current_prompt = (
              f"{prompt}\n\n"
              f"[ATTEMPT 1 FAILED WITH JSON DECODE ERROR]: {decode_err}\n"
              f"RAW RESPONSE WAS: {content}\n"
              f"Please output a correctly formatted JSON object conforming exactly to the schema."
          )
          continue
  ```
- **Fences**: Lines 50-74 slice the response string from the first brace/bracket to the last brace/bracket, stripping out markdown code fences.
- **Message**: It does *not* retry with the exact required string `'Your previous response was not valid JSON. Output ONLY the JSON object, nothing else.'`. Instead, it provides dynamic feedback detailing the JSON decode error and the raw response.

### `WordWriter._insert_paragraph()` & Operation Sorting (Task 5)
- **XML-Level Insertion** (`word_master.py` lines 470-472):
  ```python
  if 0 <= after_idx < len(doc.paragraphs):
      ref_para = doc.paragraphs[after_idx]
      ref_para._element.addnext(p_elem)
  ```
  It successfully inserts the paragraph after `ref_para` via `ref_para._element.addnext(p_elem)`.
- **Operation Sorting** (`word_master.py` lines 357-362):
  ```python
  sorted_ops = sorted(
      [op for op in operations if op.get("type", op.get("action")) in ("insert_paragraph", "replace_paragraph", "delete_paragraph", "append_to_run")],
      key=lambda x: x.get("paragraph_index", x.get("after_paragraph_index", 0)),
      reverse=True
  )
  ```
  Index-shifting operations are sorted in descending order (`reverse=True`) to maintain index stability during sequential changes.

### `WordWriter.apply_operations()` Atomic Save & Backup (Task 6)
- **Atomic Save & Backup Pattern** (`word_master.py` lines 398-448):
  - Temp path: `tmp_path = file_path + ".kairo_tmp"`
  - Backup path: `backup_path = file_path + ".kairo_bak"`
  - Original file is copied to backup via `shutil.copy2(file_path, backup_path)`.
  - Saved to temp path via `doc.save(tmp_path)` and renamed via `os.replace(tmp_path, file_path)`.
  - Automatically rolls back to the backup file (restoring the original) and removes temp/backup files if a `PermissionError` or any other `Exception` is raised during saving.

---

## 2. Logic Chain

1. **Test Suite**: Direct execution of pytest returned `261 passed, 1 warning`. This confirms the correctness of the existing test suites under `kairo-sidecar/tests/`.
2. **Prompts Injection Order**:
   - Trace domain prompt builder methods (e.g. `build_word_prompt`, `build_excel_prompt`, `PowerPointMaster.build_prompt`, etc.) in `word_prompt_builder.py`, `prompt_builder.py`, `excel_master.py`, and `other_masters.py`.
   - By matching the literal template substrings to the defined variables, we verified PowerPoint, Code, PDF, Media, and Excel prompts correctly sequence App, Doc, Mem, and Classification.
   - For Browser, Terminal, Email, Notes, and Design, their prompts are built dynamically as a single block that fails to implement the required multi-variable sequence.
   - Data prompt misses the intent classification block.
3. **JSON Reminder**:
   - Reviewing the line immediately preceding `USER INSTRUCTION:` in all prompt formats showed that PowerPoint, Code, PDF, Media, Excel, and Data contain the exact JSON reminder template.
   - Word, Browser, Terminal, Email, Notes, and Design completely lack the reminder at that location.
4. **LLM Caller**:
   - In `llm_caller.py`, the `call_with_schema` function contains a try-except block catching `json.JSONDecodeError` on attempt 1.
   - Inside this block, `current_prompt` is modified to include a diagnostic error description and raw response content, then it issues a `continue` to start the second attempt.
   - The string literal used is distinct from the requested `'Your previous response was not valid JSON. Output ONLY the JSON object, nothing else.'` string.
5. **WordWriter Insertion**:
   - `_insert_paragraph` does not use the default doc-level append; it fetches `doc.paragraphs[after_idx]` and utilizes python-docx's low-level `_element.addnext(p_elem)` to insert at XML level.
   - In `apply_operations`, `sorted_ops` utilizes Python's built-in `sorted` function with `reverse=True` on the target index (`paragraph_index` or `after_paragraph_index`). Operations targeting later indices are processed first, leaving preceding indices unaffected.
6. **WordWriter Backup**:
   - Reviewing `apply_operations` lines 398-448 confirms that a copy is created using `shutil.copy2(file_path, backup_path)`, and exceptions are wrapped in `try...except` statements that restore the original by copying backup back to the source file path and cleaning up.

---

## 3. Caveats

- **COM Live Write Path**: In `WordWriter.apply_operations()`, if the document is currently open in MS Word on Windows, it will try to write via a live COM interface (`win32com.client`). This path skips python-docx XML manipulation and file backup routines entirely. The compliance of the live COM writing path was not fully verified because it only triggers when Word is actively running and has the target document open.
- **Excel COM Live Write Path**: Similarly, `ExcelWriter.apply_operations()` attempts live COM write if Excel is running. The backup and temp patterns are skipped in this COM path, applying directly via open workbook references.

---

## 4. Conclusion

- The codebase is **partially compliant** with v3.9.0 requirements.
- **Compliant Areas**:
  - PowerPoint, Code, PDF, and Media domain prompts are fully compliant with injection order and JSON reminder positioning.
  - Excel prompt builders (both Legacy and Modern) are fully compliant.
  - `WordWriter` is fully compliant with paragraph insertion, operation sorting, and atomic save/backup patterns.
  - `llm_caller.py` correctly strips markdown fences and retries once on JSON parse errors.
- **Non-compliant Areas**:
  - Word domain prompt lacks the JSON reminder immediately preceding the user instruction.
  - Browser, Terminal, Email, Notes, and Design prompts lack distinct variable injection blocks and the JSON reminder.
  - Data domain prompt lacks the Intent Classification block.
  - `llm_caller.py` retries once but does not use the exact error message required for JSON retries.

---

## 5. Verification Method

To verify these findings independently:
1. **Pytest Run**: Execute `python -m pytest kairo-sidecar/tests/` to verify all 261 test cases pass.
2. **File Inspection**:
   - Open `kairo-sidecar/sidecar/llm_caller.py` and inspect lines 80-89 to verify the exact retry message mismatch.
   - Open `kairo-sidecar/sidecar/masters/word_master.py` and inspect `_insert_paragraph()` (lines 456-487) and `apply_operations()` (lines 357-362 & lines 398-448) to confirm XML-level insertions, sorting order, and backup routines.
   - Open `kairo-sidecar/sidecar/masters/other_masters.py` and inspect the `build_prompt` functions for the respective masters.
