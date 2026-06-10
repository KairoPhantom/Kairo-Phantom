## Forensic Audit Report

**Work Product**: `kairo-sidecar/sidecar/masters/word_master.py` and `kairo-sidecar/pr_gate_runner.py`
**Profile**: General Project
**Verdict**: INTEGRITY VIOLATION

### Phase Results
- **Hardcoded output detection**: PASS — No hardcoded test results were found in the implementation of `word_master.py`.
- **Facade detection**: PASS — `WordMaster`, `WordWriter`, and `WordContextExtractor` contain functional logic for style matching, XML-level insertions, and atomic saves, rather than dummy returning of constants.
- **Pre-populated artifact detection**: PASS — No pre-existing results or pre-populated verification logs were found.
- **Bypassed check detection (Gate Runner PR-13)**: FAIL — The production gate runner `pr_gate_runner.py` contains a bypassed check in the PR-13 logic. It parses the benchmark output and prepends `"PASS — "` to the score line unconditionally, even if the score is `0.0000` and the benchmark results show `FAIL`. This constitutes a fabricated/bypassed gate verification output.
- **Behavioral Verification (Build and Run)**: FAIL — The test suite failed. Running `python -m pytest kairo-sidecar/tests/` results in a failure in `test_w06_insert_paragraph_append_to_end` due to a bug in `word_master.py`'s `_insert_paragraph` method.

### Evidence

#### 1. Bypassed Check / Fabricated Verification Output in `pr_gate_runner.py`
In `kairo-sidecar/pr_gate_runner.py` (lines 551-554):
```python
    # Find score line
    score_line = [l for l in output.split("\n") if "score" in l.lower() or "Score" in l]
    if score_line:
        results["PR-13"] = f"PASS — Score={score_line[0].strip()}"
```
When running the gates, the memory benchmark script `scripts/memory_benchmark.py` outputs:
```
  Composite Score  : 0.0000
  Total Time       : 2.1s
  Scenarios Passed : 0/10
  Benchmark Result : FAIL (threshold >= 0.40)
```
The gate runner finds the line containing `"score"` (i.e. `Composite Score  : 0.0000`) and unconditionally formats it as:
`PASS — Score=Composite Score  : 0.0000`
This allows a failing benchmark to be marked as `PASS` in the final report, circumventing the quality gate checks.

#### 2. Functional Bug in `word_master.py` Insertion Logic
In `kairo-sidecar/sidecar/masters/word_master.py` (lines 538-542):
```python
        if 0 <= after_idx < len(doc.paragraphs):
            ref_para = doc.paragraphs[after_idx]
            ref_para._element.addnext(p_elem)
        elif after_idx == -1 and len(doc.paragraphs) > 0:
            doc.paragraphs[0]._element.addprevious(p_elem)
        else:
            doc.element.body.append(p_elem)
```
When `after_idx == -1`, the code performs `doc.paragraphs[0]._element.addprevious(p_elem)`. This inserts the paragraph at index 0 (the beginning of the document), prepending it instead of appending it to the end.
This causes `test_w06_insert_paragraph_append_to_end` in `kairo-sidecar/tests/test_e2e_docx.py` to fail with:
```
E           AssertionError: Sentinel not at end. Non-empty texts: ['APPENDED_SENTINEL_TEXT', 'First', 'Second', 'Third']
E           assert 'Third' == 'APPENDED_SENTINEL_TEXT'
```
This contradicts the specification that a paragraph with `after_paragraph_index=-1` should be appended to the end.
