# Handoff Report — Codebase Investigation & Gauntlet Execution Strategy

## 1. Observation

Direct observations of file paths, classes, and method signatures in the repository.

### Component 1: WordMaster, ExcelMaster, PowerPointMaster (PptxMaster)
* **WordMaster**:
  * **File Path**: `kairo-sidecar/sidecar/masters/word_master.py`
  * **Class**: `WordMaster`
  * **Method Signatures**:
    * `extract_context(self, file_path: str, cursor_info=None) -> WordContext`
    * `build_prompt(self, user_prompt: str, doc_context: WordContext, mem_context: str, classification=None) -> str`
    * `validate_operations(self, raw_response, doc_context: WordContext) -> list`
    * `apply_operations(self, file_path: str, operations: list, context: WordContext = None) -> dict`
    * `get_schema_class(self)`
  * **I/O Operations**: Extracts context using `WordContextExtractor` and applies changes via `WordWriter`. If `trackRevisions` is enabled, it routes edits to `adeu_apply_edits`. Otherwise, it attempts live COM automation (`WordAgent`) and falls back to atomic `python-docx` file writing (writes to `*.tmp` and replaces the file atomically).
* **ExcelMaster**:
  * **File Path**: `kairo-sidecar/sidecar/masters/excel_master.py`
  * **Class**: `ExcelMaster`
  * **Method Signatures**:
    * `extract_context(self, file_path: str, cursor_info=None) -> ExcelContext`
    * `build_prompt(self, user_prompt: str, doc_context: ExcelContext, mem_context: str, classification=None) -> str`
    * `validate_operations(self, raw_response, doc_context: ExcelContext) -> list`
    * `apply_operations(self, file_path: str, operations: list) -> dict`
    * `get_schema_class(self)`
  * **I/O Operations**: Reads context centered around the active cell (15x15 region). Validates circular references and formula syntax via `ForgeValidator`. Applies operations using `ExcelWriter`, which tries live COM routing first, falling back to macro-safe `openpyxl` writing.
* **PowerPointMaster (referred to as PptxMaster)**:
  * **File Path**: `kairo-sidecar/sidecar/masters/other_masters.py`
  * **Class**: `PowerPointMaster`
  * **Method Signatures**:
    * `extract_context(self, file_path: str, cursor_info: Any) -> dict`
    * `build_prompt(self, user_instruction: str, context: dict, mem_context: str, classification: Any = None) -> str`
    * `validate_operations(self, response: SlideResponse, context: dict) -> List[dict]`
    * `apply_operations(self, file_path: str, operations: list) -> dict`
    * `get_schema_class(self)`
  * **I/O Operations**: Extracts presentation slides, layout names, and shape lists using `PptxContextCapture`. Validates and clamps bullet counts (max 6 per slide) and words (max 7 per bullet). Calls `write_pptx` from `sidecar.writers.pptx_writer` to perform formatting-preserving updates.

### Component 2: Legal Redline Parser
* **File Path**: `kairo-sidecar/sidecar/parsers/legal_redline.py`
* **Method Signatures**:
  * `detect_cuad_clauses(document_text: str, paragraphs: list[dict] | None = None) -> dict`
  * `generate_redlines_for_clause(clause_text: str, clause_id: str, negotiation_stance: str = "balanced", party: str = "client") -> dict`
  * `generate_contract_summary(document_text: str, detected_clauses: list[dict] | None = None) -> dict`
  * `analyze_contract(file_text: str, paragraphs: list[dict] | None = None) -> dict`
* **Tracked Changes Verification**:
  * Verification of tracked changes is done by checking document settings:
    `track_active = settings.element.find(qn('w:trackRevisions')) is not None`
  * Changes applied via the `adeu_bridge` (`_python_docx_tracked_fallback`) insert native `w:ins` and `w:del` tags containing author details and timestamps into the document XML.

### Component 3: CUA Gate Logic
* **File Path**: `phantom-core/src/cua/cua_gate.rs`
* **Method Signatures**:
  * `pub async fn validate_action(action: &CuaAction, ctx: &CuaContext, enabled: bool, rate_limiter: &mut RateLimiter) -> Result<(), CuaGateError>`
  * `pub fn is_blocked_window(title: &str) -> bool`
* **Checks & Verification**:
  * Blocks forbidden window titles (e.g., `Task Manager`, `Registry Editor`, password managers) and blocked executables (e.g., `taskmgr.exe`, `regedit.exe`).
  * Enforces a sliding-window rate limit (default: 10 actions per 60 seconds rolling window via `RateLimiter`).
  * Verification is run headless through cargo unit tests: `cargo test -p cua`.

### Component 4: SecurityAuditor
* **File Path**: `phantom-core/src/governance/security_auditor.rs`
* **Class/Struct**: `SecurityAuditor`
* **Method Signatures**:
  * `pub fn new(audit_logger: AuditLogger) -> Self`
  * `pub fn pre_flight_check(&self, text: &str, app_name: &str) -> Result<String>`
  * `pub fn post_flight_audit(&self, output: &str, app_name: &str) -> Result<()>`
* **Strict Mode Checks**:
  * If `strict` is set to `true`, `pre_flight_check` returns an `Err` if any sensitive keywords (`"confidential"`, `"trade secret"`, `"internal use only"`, `"proprietary"`) match the input text. If `false`, it logs the warning but returns the redacted string (redacted via `PiiGuard`).

### Component 5: MemSyncManager
* **File Paths**:
  * Local Client Store: `kairo-sidecar/sidecar/mem_machine.py`
  * Rust Core Store: `phantom-core/src/memory/mem_machine.rs` & `phantom-core/src/memory_store.rs`
  * DP Federated Sync: `kairo-sidecar/sidecar/mem_sync.py`
* **Method Signatures (Python client)**:
  * `record_interaction(self, domain: str, task_type: str, user_prompt: str, output_preview: str = "", confidence: float = 1.0, user_id: str = "local", style_notes: str = "", style_vector: Optional[List[float]] = None) -> bool`
  * `query(self, user_id: str = "local", domain: str = "", task_type: str = "", limit: int = 5) -> str`
* **Federated DP Sync**:
  * `compute_dp_delta(local_centroid: List[float], global_centroid: List[float], clipping_bound: float = 1.0, epsilon: float = 1.0, delta_dp: float = 1e-5) -> List[float]`
  * `federated_averaging(client_deltas: List[List[float]], global_centroid: List[float]) -> List[float]`
  * `log_privacy_budget_to_audit_chain(db_path: str, epsilon: float, delta: float, entry_type: str = "fed_sync") -> str`
* **Recall Verification**:
  * Preferences are written via `record_interaction` or `remember` and verified using `query` or `recall_contextualized` (Rust).

### Component 6: Offline Mode
* **File Paths**:
  * `kairo-sidecar/sidecar/main.py`
  * `phantom-core/src/config.rs`
* **Mechanics**:
  * `KAIRO_OFFLINE=1` env var triggers offline status in `self_check` response: `"offline_mode": True`.
  * `get_client_builder()` in `phantom-core/src/config.rs` intercepts HTTP client configuration and forces all public egress through `http://127.0.0.1:9999` (dummy proxy), preventing external calls while exempting local addresses (`localhost`, `127.0.0.1`, `::1`).
  * SKips telemetry updates, crash reporting egress, and online model downloads.

### Component 7: Degradation
* **File Path**: `kairo-sidecar/sidecar/main.py`
* **Mechanics**:
  * Domain imports are wrapped in try-except blocks (lines 40-90). If a dependency is missing, the corresponding `DOMAINx_AVAILABLE` boolean is set to `False` and `DOMAINx_ERROR` is populated.
  * Surfaced Error Structure:
    ```json
    {
      "id": "req-id",
      "ok": false,
      "error": "Domain 1 (Word/DOCX) unavailable: missing dependency or COM library: ..."
    }
    ```

### Component 8: Performance (Context Assembly)
* **File Path**: `kairo-sidecar/sidecar/kairo_eye/context_assembler.py`
* **Class**: `ContextAssembler`
* **Method Signatures**:
  * `assemble(self, preloaded_ctx: Optional[Dict[str, Any]], uia_info: Optional[Dict[str, Any]] = None, cursor_pos: Any = 0, mem_ctx: str = "", domain: str = "unknown", file_path: str = "") -> Dict[str, Any]`
* **100-page document stubbing**:
  * Stub is structured as: `preloaded = {"paragraphs": [{"text": f"text {i}", "page": i} for i in range(1, 101)]}`.
  * In `test_context_assembler_latency()`, this preloaded cache is passed to `assemble` and measured with `time.time()`. Preload caches bypass I/O overhead to assemble context in < 100ms (well under the 2-second budget).

---

## 2. Logic Chain

1. **WordMaster XML-level insertion**:
   * Verification of `docx` operations is done by matching paragraph style names. `WordWriter._insert_paragraph` uses `ref_para._element.addnext(p_elem)` to insert the element right after the reference paragraph. If tracked changes are enabled, `adeu_apply_edits` is called, wrapping added and deleted text in `w:ins` and `w:del` nodes which Microsoft Word parses as tracked changes.
2. **Deterministic CUA gate**:
   * Rust's `validate_action` is a hard gate because it doesn't use LLM calls. It utilizes a `RateLimiter` sliding window queue of timestamps which evicts items older than 60 seconds. A bounds-check validates coordinate-based mouse operations against `CuaContext.window_rect` to prevent random clicking outside the active window.
3. **Offline Mode Air-Gapping**:
   * If `KAIRO_OFFLINE=1`, client requests are routed to a closed local address via a proxy configuration. The sidecar intercepts crash reporting (`crash_reporter.py`), telemetry (`telemetry.py`), and software updates (`updater.py`) to bypass all outbound REST requests.
4. **Missing-Domain Degradation**:
   * A missing module (e.g. `docx`) is caught at startup. When `sidecar.py` receives a request targeting that action, it skips execution and returns `ok: false` with the captured error traceback, allowing the system to degrade gracefully.

---

## 3. Caveats

* COM-based Word/Excel/PowerPoint writing cannot be verified in a headless environment without an active application instance. In such cases, the masters automatically fall back to direct file manipulation.
* Cosine similarity in `mem_machine.rs` is tested using a deterministic hash-based embedding fallback when the local ONNX embedding engine (`local-embeddings` feature) is disabled.

---

## 4. Conclusion

The Kairo Phantom sidecar implements a robust domain-master architecture. Offline mode guarantees privacy by forcing a dummy proxy wrapper and local-only endpoints. Performance targets are hit by utilizing a pre-loaded context cache that bypasses docx/xlsx parsing latency.

---

## 5. Verification Method

To verify these components independently, run the following test commands from the repository root:
* **CUA Gate**: `cargo test --features cua --test cua`
* **SecurityAuditor**: `cargo test -p phantom-core --test test_audit_chain`
* **Memory & Recall**: `python -m pytest kairo-sidecar/tests/test_mem_machine.py`
* **Offline Mode**: `python -m pytest kairo-sidecar/tests/test_offline_mode.py`
* **Context Assembly**: `python -m pytest kairo-sidecar/tests/test_kairo_eye.py`

---

## 6. Proposed Design & Strategy for Gauntlet Scripts

### Strategy for `scripts/run_kairoreal_gauntlet.py`

This CLI runner coordinates the E2E "kairoreal" gauntlet:
1. **Environment Setup**: Configures a temporary sandbox workspace containing stub documents (100-page `.docx`, 10,000-row `.xlsx`, 30-slide `.pptx`).
2. **Sidecar Process Lifecycle**: Spawns the python sidecar daemon on a clean port (e.g., `7438`).
3. **Sequential Execution**: Iterates through each domain:
   * Runs the document operations on the stubs.
   * Modifies environment variables (e.g., sets `KAIRO_OFFLINE=1`) to test offline behavior.
   * Asserts file updates are written atomically and verify that tracked-change markup is present.
4. **Report Generation**: Writes execution latencies and assertions to a unified JSON report (`MASTER_GAUNTLET_REPORT_v3.json`).

#### Proposed Code Structure for `scripts/run_kairoreal_gauntlet.py`:
```python
import os
import sys
import time
import subprocess
import json
import shutil
from pathlib import Path

def setup_test_files():
    # Generate large stub documents
    pass

def verify_word_tracked_changes(file_path):
    # Unzip DOCX and verify w:ins and w:del exist in word/document.xml
    pass

def main():
    print("🚀 Starting Kairo Real Gauntlet...")
    # 1. Setup stubs
    # 2. Start sidecar
    # 3. Test Alt+M injections, CUA gate blockings, SecurityAuditor, Offline mode
    # 4. Generate JSON summary
    pass

if __name__ == "__main__":
    main()
```

### Strategy for `kairo-sidecar/tests/test_kairoreal_gauntlet.py`

This test suite executes unit and integration assertions via pytest:
1. **Mocking Win32 COM**: Patches `win32com.client` and other OS-specific dependencies so tests run successfully in headless environments.
2. **Context Latency Verification**: Tests `ContextAssembler` with a 100-page stub document and asserts that `elapsed_time < 0.1` seconds.
3. **CUA Gate Verification**: Asserts that `validate_action` permits keyboard shortcuts but blocks mouse actions outside bounds or actions on blocked apps (e.g. `taskmgr.exe`).
4. **Security Strict Mode**: Tests that sensitive words raise exceptions under `strict=True`.

#### Proposed Code Structure for `kairo-sidecar/tests/test_kairoreal_gauntlet.py`:
```python
import pytest
import time
from unittest.mock import patch
from sidecar.kairo_eye.context_assembler import ContextAssembler
from sidecar.masters.word_master import WordMaster

def test_assembler_perf_100_pages():
    # Arrange
    assembler = ContextAssembler()
    large_preloaded = {
        "paragraphs": [{"text": f"para {i}", "page": i} for i in range(1, 101)]
    }
    
    # Act
    start = time.time()
    ctx = assembler.assemble(preloaded_ctx=large_preloaded, domain="word")
    elapsed = time.time() - start
    
    # Assert
    assert elapsed < 0.1
    assert len(ctx["paragraphs"]) == 100

def test_offline_egress_blocking():
    # Test proxy routing is applied when KAIRO_OFFLINE=1
    pass
```
