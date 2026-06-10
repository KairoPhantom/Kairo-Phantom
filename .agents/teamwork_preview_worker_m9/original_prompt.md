## 2026-06-07T13:43:23Z
You are a teamwork_preview_worker. Your ID is worker_m9.
Your working directory for metadata is c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\teamwork_preview_worker_m9.
Your goal is to implement Milestone 9: Word Master Performance & Write-Back.

Requirements:
1. XML-level paragraph insertions:
   In `kairo-sidecar/sidecar/masters/word_master.py` (and specifically `WordWriter._insert_paragraph`), implement correct XML-level `.addnext()` and `.addprevious()` paragraph insertions.
   - If `after_paragraph_index >= 0` and `after_paragraph_index < len(doc.paragraphs)`:
     Use `ref_para._element.addnext(p_elem)`.
   - If `after_paragraph_index == -1` and there are paragraphs in the document:
     Use `doc.paragraphs[0]._element.addprevious(p_elem)` to insert at the beginning.
   - If there are no paragraphs in the document:
     Append directly to the document body element: `doc.element.body.append(p_elem)`.

2. Atomic save and backup rotation:
   In `WordWriter.apply_operations`, enforce atomic saves. If an exception occurs, automatically roll back to the backup file. Keep backup rotation or ensure it is clean.

3. Optimize context extraction:
   In `WordContextExtractor.extract` inside `kairo-sidecar/sidecar/masters/word_master.py`:
   - Optimize extraction to run under 100ms for large documents (to pass the PR-14 gate which has a 2.0s limit).
   - Speed up style resolution and run traversal by caching a style ID-to-style name mapping dictionary once from `doc.styles`: `style_id_to_name = {s.style_id: s.name for s in doc.styles if s.name}`.
   - For each paragraph, retrieve the style name using `style_id_to_name.get(para._p.pPr.pStyle.val, para._p.pPr.pStyle.val)` if `para._p.pPr` and `para._p.pPr.pStyle` are not None (fallback to `"Normal"` or `para.style.name`).
   - Extract text by querying `para._p.xpath('.//w:t')` or using a fast join to bypass instantiating `runs`.
   - For `list_sequences` extraction, do not iterate over all paragraphs a second time! Instead, build `list_sequences` in the first and only pass.
   - Pass the pre-extracted paragraphs list directly to `_detect_document_purpose` to avoid accessing the slow `doc.paragraphs` properties again.

4. Run the unit tests via `python -m pytest kairo-sidecar/tests/test_word_master.py` to ensure all tests pass.
5. Run the production gate runner `python kairo-sidecar/pr_gate_runner.py` to verify that PR-14 passes with a time well under 2.0 seconds (preferably under 1.0s), and that PR-01, PR-02, PR-03, PR-04, PR-05, PR-06, PR-07, and PR-08 pass successfully.

6. MANDATORY INTEGRITY WARNING — include this verbatim in the Worker's dispatch prompt:
   DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

7. Write a handoff report at `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\teamwork_preview_worker_m9\handoff.md` and send a message to the caller (ID: 1af31f68-3671-4a97-94a6-c50497cc4648) with the outcomes, build/test commands, and results.
