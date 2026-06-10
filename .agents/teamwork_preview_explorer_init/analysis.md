# Kairo Phantom Upgrade Project: Layout, Findings, & Implementation Report

This report outlines the codebase layout, baseline test/gate execution results, and detailed recommendations for implementing the version upgrade requirements of the Kairo Phantom project.

---

## 1. Codebase Layout & File locations

Per `PROJECT.md`, the repository follows a multi-language architecture:
- `phantom-core/`: Rust daemon core.
- `phantom-overlay/src-tauri/`: Tauri frontend overlay backend.
- `kairo-sidecar/`: Python background services, parsers, and domain masters.
- `kairo-agent-sdk/`: SDK for writing integrations.

### Located Source Files
- **WordWriter and WordContextExtractor**:
  - `WordWriter`: `kairo-sidecar/sidecar/masters/word/writer.py` (handles XML-level additions via `.addnext()` and atomic saves).
  - `WordContextExtractor`: `kairo-sidecar/sidecar/masters/word/context_extractor.py` (extracts styles, heading levels, and lists).
  - `WordMaster` facade: `kairo-sidecar/sidecar/masters/word_master.py` (orchestrates extraction and write-back).
- **LiteLLM / Routing Setup**:
  - `DomainMasterRouter`: `kairo-sidecar/sidecar/router.py` (orchestrates pre-gate validation, LLM execution, and memory storage).
  - LLM Caller Wrapper: `kairo-sidecar/sidecar/llm_caller.py` (manages direct JSON object schema verification, cleaning markdown fences, and retries).
- **MemMachine database & styling recall**:
  - `MemMachineClient` / `MemorySeeder`: `kairo-sidecar/sidecar/mem_machine.py` (SQLite backend default at `~/.kairo/memmachine.db`, queries top-5 style history).
- **Create from scratch templates/handlers**:
  - Currently **not implemented**. Creators need to be designed from scratch.
- **Atomic save/undo mechanisms**:
  - Atomic saves for Word: `WordWriter.atomic_save_docx` in `kairo-sidecar/sidecar/masters/word/writer.py`.
  - Atomic saves for Excel / PowerPoint: in `kairo-sidecar/sidecar/writers/xlsx_writer.py` and `pptx_writer.py` (but with missing rollback capabilities under exceptions).
  - Undo mechanism: `HumanizedInjector` in `kairo-sidecar/sidecar/humanized_injector.py` (restores pre-injection snapshots).

---

## 2. Baseline Test & Gate Execution Results

### 2.1 Pytest Suite Execution
- **Command**: `python -m pytest kairo-sidecar/tests/`
- **Result**: **PASS** (100% success rate)
- **Baseline Count**: **293 / 293** tests passed.
- **Execution Time**: 101.12 seconds.

### 2.2 Production Gates Runner Execution
- **Command**: `python kairo-sidecar/pr_gate_runner.py`
- **Result**: **LAUNCH DECISION: NOT READY**
- **Automated Gate Success Count**: **11/12** passed, **1** failed, **2** manual checks required.
- **Gate Breakdown**:
  - **PR-01**: `PASS` — Style fuzzy match mapping correctly used "Heading 2".
  - **PR-02**: `PASS` — Esc key cancellation leaves paragraph counts unchanged.
  - **PR-03**: `PASS` — System prompt internal keywords [waza, memmachine] never leaked.
  - **PR-04**: `PASS` — Zero external socket connections in offline mode.
  - **PR-05**: `PASS` — Ctrl+Z undo fully restores the file (MD5 comparison matched).
  - **PR-06**: `PASS` — Excel cell modification preserves adjacent cells.
  - **PR-07**: `PASS` — Disk crash simulation does not corrupt original files.
  - **PR-08**: `PASS` — Context assembly time under 100ms.
  - **PR-09**: `MANUAL` — Requires VM setup validation.
  - **PR-10**: `MANUAL` — Alt+M stress test / debounce protection requires live UI.
  - **PR-11**: `PASS` — AppWatcher domain detection accuracy is 100%.
  - **PR-12**: `PASS` — MemMachine style preferences persisted and recalled.
  - **PR-13**: `PASS` — Memory benchmark composite score verified.
  - **PR-14**: `FAIL` — **2.448 seconds context preparation** (extract=2386ms, assemble=62ms). Threshold is **2.0s**.

---

## 3. Implementation Recommendations for the Upgrade Project

We recommend addressing each requirement as follows:

### R1. Fix python-docx Write-Back and Extraction Latency
- **XML-level insertions**: Ensure `WordWriter._insert_paragraph` handles prepending / appending safely using both XML-level `.addnext()` and `.addprevious()` on paragraph references depending on insertion parameters.
- **Extraction Optimization (PR-14 Fix)**:
  - The current `WordContextExtractor.extract` takes over 2.3 seconds on large documents. This is due to python-docx wrapper instantiation overhead (specifically accessing `para.style` and `para.runs` properties).
  - **Recommendation**: Rewrite `WordContextExtractor` to parse the document's XML directly using `lxml` / `element.xpath()`.
  - Traversing the document tree directly, looking up style IDs in `w:pPr/w:pStyle`, and finding `w:r` elements manually will bypass the python-docx overhead completely.
  - Doing this in a single-pass XML traversal will reduce extraction times from >2000ms down to `<100ms`, resolving the **PR-14** failure.

### R2. Implement Create From Scratch
- **Proposed Module Structure**: Create `sidecar/creators/docx_creator.py`, `sidecar/creators/pptx_creator.py`, and `sidecar/creators/xlsx_creator.py`.
- **Implementation**:
  - Implement a `DocxCreator` class utilizing `python-docx` to generate files using structured markdown templates.
  - Implement `PptxCreator` and `XlsxCreator` classes utilizing `python-pptx` and `openpyxl`.
  - Save files to `C:/Users/<username>/Documents/Kairo/`.
  - Call `os.startfile(filepath)` to automatically open the generated document in the user's default app.

### R3. Wire Routa/LiteLLM 4-Tier Smart Routing
- **Routing Setup**:
  - In `sidecar/router.py`, introduce a tier selection algorithm based on the task classification (simple/medium/complex) and confidence score:
    1. **kairo-fast**: (e.g. `ollama/qwen2.5:4b`, simple tasks, short outputs <=150 tokens, high confidence >=0.75).
    2. **kairo-standard**: (`ollama/qwen2.5:7b`, standard tasks).
    3. **kairo-think**: (`ollama/qwen3-reasoning:8b` or standard reasoning model, complex tasks).
    4. **kairo-cloud**: (Claude/Gemini APIs, fallback or complex multi-document reasoning).
  - Implement a fallback chain: if a call fails with a timeout or connection issue on `fast`, retry on `standard`, and then fallback to `cloud`.

### R5. Integrate Local Repositories
- Implement the indexing pipeline using `docsagent`.
- Set up a query interface with `knowhere` to query semantic graphs.
- Add interaction counters in the database; when a user reaches >10,000 interactions, run a migration script to copy memory history from SQLite to SurrealDB (CodaCite).
