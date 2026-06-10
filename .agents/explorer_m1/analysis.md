# Milestone 1: Baseline Verification & Exploration Report

## 1. Production Gates Verification (14 Gates)

Below is the status of the 14 production gates checked via `kairo-sidecar/pr_gate_runner.py` and direct execution.

| Gate ID | Title / Description | Status | Details / Observations |
|---|---|---|---|
| **PR-01** | Word injection uses correct paragraph style | **PASS** | Successfully verified style fuzzy-matching ("Heading2" -> "Heading 2"). |
| **PR-02** | GRP never injects without Tab approval (Esc test) | **PASS** | Document paragraph count remains unchanged when user cancels GRP (0 operations). |
| **PR-03** | System prompt never leaks | **PASS** | Detected leaked system-prompt keywords (`waza_agent`, `memmachine`, `waza+ghost-writer`) in verifier tests. |
| **PR-04** | Zero external connections in offline mode | **PASS** | DomainMasterRouter initializes and imports modules with network blocked without raising errors. |
| **PR-05** | Ctrl+Z undoes entire injection | **PASS** | Pre-injection MD5 hash matches post-undo MD5 hash exactly. |
| **PR-06** | Excel E-11: adjacent cells unchanged | **PASS** | Changing a single cell formulas does not modify any surrounding cells. |
| **PR-07** | Sidecar crash leaves original file intact | **PASS** | Atomic save prevents file corruption during disk crash simulation. |
| **PR-08** | First token latency <2s (5-run context prep) | **PASS** | Context assembly completed in <1ms over 5 runs (headroom budget of 500ms+ preserved). |
| **PR-09** | Fresh Windows 11 install to first Alt+M | **MANUAL** | Requires fresh Windows 11 VM setup + installation via `KairoSetup.exe`. |
| **PR-10** | Alt+M stress test (10 presses in 1.5s) | **MANUAL** | Requires live Word running + keyboard automation to test debounce behavior. |
| **PR-11** | AppWatcher domain detection accuracy | **PASS** | Correctly identified 49/49 process names to correct Kairo domains. |
| **PR-12** | MemMachine session recall | **PASS** | Session 2 GRP output correctly recalls Session 1 style preference from SQLite database. |
| **PR-13** | Memory benchmark score | **PASS / FALSE PASS** | The PR gate runner reports **PASS** because it detects a score output. However, running the memory benchmark script directly fails with **FAIL (Composite Score: 0.0000)** because the local Kairo sidecar daemon (port 7437) is offline. |
| **PR-14** | 100-page .docx context assembly time | **PASS** | 200 paragraphs (~100 pages) context prep completed in 90ms (65ms extract + 25ms assemble), well under 2000ms threshold. |

### PR-13 Gate False-Pass Vulnerability
- In `pr_gate_runner.py` (lines 551–556):
  ```python
  score_line = [l for l in output.split("\n") if "score" in l.lower() or "Score" in l]
  if score_line:
      results["PR-13"] = f"PASS — Score={score_line[0].strip()}"
  ```
- Because the script prints `Composite Score  : 0.0000`, the gate runner finds the word "Score", extracts `Composite Score  : 0.0000`, and marks it as a `PASS`.
- Directly running the memory benchmark (`python scripts/memory_benchmark.py`) shows a result of **FAIL** (Composite Score: 0.0000 / Threshold >= 0.40) because the sidecar daemon is offline.

---

## 2. Python-Docx Write-Back Implementation

We analyzed python-docx write-back implementations in two locations:
1. **Production Implementation**: `kairo-sidecar/sidecar/masters/word_master.py` (Class: `WordWriter`)
2. **Alternative/Test Implementation**: `kairo-sidecar/sidecar/masters/word/writer.py` (Class: `WordWriter`)

### XML-Level Paragraph Insertion Correctness
Standard python-docx only supports appending paragraphs to the end of a document via `doc.add_paragraph()`. To insert a paragraph at an arbitrary index without disrupting formatting, both writers implement a custom XML-level insertion:
```python
p_elem = OxmlElement('w:p')
ref_para._element.addnext(p_elem)
new_para = Paragraph(p_elem, doc)
```
This directly accesses the underlying `lxml` element tree of the Office Open XML document structure and places the new paragraph node (`w:p`) next to the reference paragraph.

### Key Differences
- **`word_master.py:WordWriter`**:
  - Implements live injection via Word COM APIs first (`WordAgent(file_path).apply_operations(...)` and `_try_com_write`).
  - If Word is not running or COM fails, it falls back to standard file-writing.
  - Slices operations in reverse index order to prevent index shifting during insertion/deletion.
  - Supports detailed paragraph runs containing bold and italic configurations.
  - Contains robust error handling with automatic rollback from copy-back backups (`.kairo_bak`) if exceptions occur.
- **`word/writer.py:WordWriter`**:
  - A clean, standalone module used by adjacent unit tests.
  - Supports paragraph insertion, editing, style change, and deletion.
  - Does not support COM live injection or rich-text formatting (adds text in a single flat run).
  - Uses `tempfile` and `os.replace` for atomic saves, but lacks rollback logic to restore the backup file if save fails.

---

## 3. LiteLLM Configuration Routing Analysis

- **File Location**: `kairo-sidecar/sidecar/litellm_config.yaml`
- **Tiers Setup**: Implements the 4-tier model strategy exactly:
  1. **kairo-fast**: Points to the local fine-tuned 4B model `ollama/kairo-docwriter-4b`. Falls back to local `ollama/qwen2.5:7b` if unavailable.
  2. **kairo-standard**: Points to `ollama/qwen2.5:7b` on port 11434.
  3. **kairo-think**: Points to the local reasoning model `ollama/qwen3:8b`.
  4. **kairo-cloud**: Points to `anthropic/claude-sonnet-4-5` (authenticated via `os.environ/ANTHROPIC_API_KEY`).
- **Backward Compatibility**: Configures legacy model aliases (`ollama/qwen2.5:7b`, `ollama/qwen2.5:3b`, `claude-3-5-sonnet`, `gemini-2.5-flash`).
- **Routing and Failover Logic**:
  - `routing_strategy` is set to `usage-based-routing-v2`.
  - Fallbacks are defined hierarchically:
    - `kairo-fast` -> `kairo-standard` -> `kairo-cloud`
    - `kairo-standard` -> `kairo-cloud`
    - `kairo-think` -> `kairo-cloud`
  - Re-tries: 2 attempts with a `retry_after` of 0.5 seconds.
  - Settings: `drop_params: true` is enabled to strip unsupported parameters before forwarding to local ollama instances.

---

## 4. Fine-Tuning Compliance Script & Compliance Rate

- **File Location**: `scripts/eval_schema_compliance.py`
- **Purpose**: Evaluates model adherence to Kairo's JSON operations formatting requirements. Serves as the gatekeeper for replacing `kairo-standard` with `kairo-fast`.
- **How it Works**:
  - Loads 10 realistic test prompts for each schema group: `DocxOperation`, `ExcelOperation`, and `SlideOperation`.
  - Calls the LiteLLM proxy at `http://localhost:4000/v1/chat/completions` in JSON-object response mode.
  - Validates returned JSON keys and operation types against pre-defined validators.
  - Aggregates results to produce a **Composite Score** (between 0.0000 and 1.0000) and **Compliance Rate**.
  - **Threshold**: Requires a **>=95.0%** compliance rate to pass the gate.
- **Current Compliance Rate**:
  - The LiteLLM proxy is currently offline. As a result, running `python scripts/eval_schema_compliance.py` fails with connection refused (`urllib.error.URLError`), returning a **0.0%** compliance rate (FAIL).
  - A running proxy connected to a competent model is required to reach the 95.0% threshold.

---

## 5. Document Creators Analysis

The creators in `kairo-sidecar/sidecar/creators/` generate new Office documents from scratch and open them in their respective applications.

### 5.1 docx_creator.py (DocxCreator)
- **Library**: `python-docx`
- **Output Directory**: Saved to `~/Documents/Kairo/{safe_title}.docx`.
- **Formatting & Layout**:
  - Formats the document with Title (level 0), Headings (levels 1-4), Body Paragraphs, and Bullet points (styled with `"List Bullet"`).
  - Supports simple table generation with headers and cell rows (pre-styled with `"Table Grid"`).
- **Automation**: Features a `create_and_open` method that uses `os.startfile(path)` to automatically launch Microsoft Word after generation.

### 5.2 pptx_creator.py (PptxCreator)
- **Library**: `python-pptx` (imported as `from pptx import Presentation`)
- **Output Directory**: Saved to `~/Documents/Kairo/{safe_title}.pptx`.
- **Formatting & Layout**:
  - Automatically sets presentation dimensions to standard **widescreen 16:9** (13.33 x 7.5 inches).
  - Supports four distinct layouts:
    1. `title`: Standard slide with Title and Subtitle.
    2. `content`: Slide with Title and Bullet items/Body text.
    3. `two_column`: Creates left/right columns on a blank slide layout, manually calculating text box sizes.
    4. `blank`: Plain layout with optional Title/Body.
- **Automation**: Includes `create_and_open` which launches the presentation using `os.startfile(path)`.

### 5.3 xlsx_creator.py (XlsxCreator)
- **Library**: `openpyxl`
- **Output Directory**: Saved to `~/Documents/Kairo/{safe_title}.xlsx`.
- **Formatting & Layout**:
  - Clears the default blank workbook sheet and creates sheet tabs named after the structured content.
  - Pre-styles headers with a dark blue fill (`"366092"`), white bold text, and center alignment.
  - Supports formulas starting with `=`.
  - Can calculate totals automatically: if `totals=True`, it appends a bold "TOTAL" row at the bottom containing `=IFERROR(SUM(...), "")` for numeric columns.
  - Dynamically fits column widths based on cell text length (bounded between 8 and 50 characters).
- **Automation**: Supports `create_and_open` using `os.startfile(path)`.
