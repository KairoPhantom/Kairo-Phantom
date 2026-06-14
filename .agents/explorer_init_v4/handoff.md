# Codebase Investigation Report: GA Hardening Plan for Kairo Phantom

## Summary of Core Findings
This report details the codebase analysis of Kairo Phantom for the remaining GA Hardening requirements across Calibration & Trust, Hardening & Release, Production Ops, and Autonomous Gauntlet Infrastructure. The investigation reveals that while basic tests and core execution pipelines are solid and pass 100% locally, the 19 targeted hardening features are either unimplemented stubs, uncompiled files, or completely missing from scratch. This report details their exact mappings, structural gaps, and provides an actionable blueprint for implementation.

---

## 1. Observation

Direct observations of file locations, code structures, and test suites across the repository:

### R1. Calibration & Trust (Sprint 4)
*   **1.1 Confidence Unification (Item 20)**:
    *   *File Location*: `phantom-core/src/confidence.rs` is currently sitting in the source directory but is **not** declared as a module in `lib.rs` or `main.rs`, meaning it is uncompiled dead code.
    *   *Logic/Signature*: It defines `ConfidenceLevel`, `ConfidenceScore`, and `calculate_confidence` (lines 6-67), as well as a Tauri floating UI window launcher `show_confidence_band` (lines 70-88).
    *   *Unification Target*: `phantom-core/src/memory/feedback.rs` defines a different `ConfidenceEngine` structure (line 66) with `calculate_confidence(app: &str, response: &str, history: &[FeedbackSignal]) -> f64` based on Levenshtein-similarity formatting history.
*   **1.2 E2E Measurement CI Job (Item 22)**:
    *   *File Location*: `.github/workflows/gui_gauntlet.yml` exists.
    *   *Logic/Signature*: It runs a Windows-based end-to-end runner that executes AHK-style `wscript.shell` automation against real Word/Excel/PowerPoint applications (lines 198-216), saves screenshots, and compiles a `results.json` per app group, combining them into a final `report.json` (lines 315-322).
    *   *Gap*: It does **not** generate or publish the required `task_completion_rate.json` artifact containing completion rate metrics.
*   **1.3 Response Validator Hard Block (Item 26)**:
    *   *File Location*: `phantom-core/src/response_validator.rs` (lines 9-119).
    *   *Logic/Signature*: `ResponseValidator::validate(&self, user_prompt: &str, response: &str) -> ValidationResult` returns `ValidationResult::Irrelevant { overlap_score: f32 }` when lexical overlap is below a hardcoded `0.05` threshold (line 81).
    *   *Execution Gap*: In `phantom-core/src/main.rs` (lines 3630-3644), if `validation_failed` is true, the system simply outputs warning logs and types `[SECURITY ALERT: RESPONSE BLOCKED]` via clipboard injection. It does **not** trigger regeneration. The retry mechanism in `retry_policy.rs` is unused in `main.rs`.
*   **1.4 Calibrated Uncertainty (Item 27)**:
    *   *File Location*: `phantom-core/src/intent_gate.rs` (lines 378-408).
    *   *Logic/Signature*: `check_clarity(prompt: &str, confidence: f32, intent_type: &IntentType, doc_kind: &DocKind) -> (bool, Option<String>)` has a hardcoded clarity threshold `const CLARITY_THRESHOLD: f32 = 0.40;` (line 384).
    *   *Gap*: The calibrated uncertainty threshold cannot be configured from `config.rs` or settings.
*   **1.5 Document Constitution (Item 28)**:
    *   *File Location*: No constitution file or validation logic exists in `response_validator.rs` or elsewhere.
    *   *Gap*: Completely missing from scratch.
*   **1.6 Verifiable-Work Receipts (Item 29)**:
    *   *File Location*: `phantom-core/src/identity.rs` (lines 198-296).
    *   *Logic/Signature*: `AuditChainEntry` models hash chaining with `prev_hash` and `self_hash` (lines 199-210) and is written by `TamperEvidentAuditLog::append` (line 261). `AgentIdentity` contains a cryptographically secure Ed25519 signing function `sign(&self, data: &[u8]) -> Result<String, String>` (line 81) using `ed25519_dalek::SigningKey`.
    *   *Gap*: `AuditChainEntry` does **not** have a `signature` field, and entries are never signed with the agent's private key.

### R2. Hardening & Release Readiness (Sprint 5)
*   **2.1 Signed Updates (Item 23)**:
    *   *File Location*: `kairo-sidecar/sidecar/updater.py` (lines 18-45).
    *   *Logic/Signature*: `check_for_update() -> Optional[Tuple[str, str]]` requests `https://api.github.com/repos/KairoPhantom/Kairo-Phantom/releases/latest` to check for newer tags.
    *   *Gap*: Only performs a simple tag comparison. There is no downloader, no SHA-256 package validation, and no Ed25519 signature verification.
*   **2.2 Remove pro.rs Stub (Item 24)**:
    *   *File Location*: `phantom-core/src/pro.rs` exists in the codebase but is **not** compiled (omitted from `lib.rs` modules).
    *   *Logic/Signature*: Defines a mock `KairoPro` class (line 11), a daemon loop, a `pro_only!` macro, and stubs for Tolaria Bridge, S3 Sync, CSV export, and advanced agents (lines 110-158).
    *   *Gap*: If license verification fails, calling `TeamMemoryVault::sync_to_s3` returns an error, but this module is not integrated anywhere in the rest of the compiled codebase.
*   **2.3 Thin Domain Capabilities (Item 30)**:
    *   *File Location*: `phantom-core/src/plugin.rs` (lines 38-40).
    *   *Logic/Signature*: `SwarmAgent::capability` default implementation returns `DomainCapability::PromptOnly`.
    *   *Gap*: There is no public marketing endpoint or list interface that exposes capabilities or strips `PromptOnly` domains.
*   **2.4 Best-of-N Oracle Selection (Item 31)**:
    *   *File Location*: `kairo-sidecar/sidecar/oracles.py` contains structural verification methods (`verify_docx`, `verify_xlsx`, `verify_pptx`, `verify_pdf`, `verify_screenshot_diff`, `NetworkSnifferOracle`).
    *   *Gap*: No Best-of-N inference selection loop exists to generate multiple candidates, evaluate them against these oracles, and select the highest-scoring candidate.
*   **2.5 Adaptive Compute (Item 32)**:
    *   *File Location*: `kairo-sidecar/sidecar/model_router.py` (lines 46-102) and `llm_caller.py` (lines 15-46).
    *   *Logic/Signature*: `select_model` chooses the reasoning tier `kairo-think` for high-complexity agents.
    *   *Gap*: `llm_caller.py` does **not** support or pass dynamic thinking/reasoning budget parameters (such as Anthropic's `thinking` or OpenAI/Ollama's equivalent budget fields) in the API payloads.

### R3. Production Ops Layer (Sprint 5.5)
*   **3.1 Auto-Update Rollback (Item 54)**:
    *   *Gap*: Completely missing from scratch. No rollback mechanism exists.
*   **3.2 Crash Reporting (Item 55)**:
    *   *File Location*: `kairo-sidecar/sidecar/crash_reporter.py` (lines 19-74).
    *   *Logic/Signature*: `_crash_handler` writes exception type, message, and standard traceback to `~/.kairo-phantom/crashes/crash_*.json`.
    *   *Gap*: No PII-scrubbing is performed on the traceback string (it can expose local user paths and doc snippets). There is no air-gap mode disabling logic. The Rust core has no panic/crash logging at all.
*   **3.3 Observability (Item 56)**:
    *   *File Location*: `kairo-sidecar/sidecar/telemetry.py` (lines 29-52).
    *   *Logic/Signature*: Custom local JSONL writer.
    *   *Gap*: Does not integrate OpenTelemetry SDK. No OpenTelemetry collector or file-exporter exists on Python or Rust sides.
*   **3.4 Security & Dependency Gates (Item 57 & 58)**:
    *   *File Location*: `.github/workflows/ci.yml`.
    *   *Gap*: Syft (SBOM), cargo-audit, and Gitleaks checks are not configured.

### R4. Autonomous Gauntlet Infrastructure (Sprint 6 & 7)
*   **4.1 Sandbox & Parallel Runner (Item 33)** to **4.6 Drift Alarm (Item 40)**:
    *   *Gap*: Completely missing from scratch. No Vagrant/Hyper-V scripts, Test-Fix-Test loop engine, mutation testing integration, DuckDB outcome schemas, Gymnasium environment wrappers, synthetic persona-agents, or drift alarm algorithms exist.

---

## 2. Logic Chain

Step-by-step reasoning from observed code patterns to conclusions:

1.  **Confidence Unification**: Since `confidence.rs` is uncompiled dead code and `feedback.rs` maintains an active, compiled `ConfidenceEngine`, any effort to unify confidence scoring must consolidate both systems under `memory::feedback::ConfidenceEngine` and remove `confidence.rs` to avoid duplication.
2.  **E2E Measurement CI Job**: `.github/workflows/gui_gauntlet.yml` already contains a consolidation step running shell scripts to generate a unified `report.json`. To support R1.2, we must append a post-processing script to this job that parses `report.json`, extracts task statuses, calculates the percentage rate, writes `task_completion_rate.json`, and uploads it.
3.  **Response Validator Hard Block**: Irrelevant responses currently trigger inline clipboard warnings in `main.rs` but do not block injection. Because `main.rs` lacks a loop structure that can request the AI backend for a new response on validation failures, a proper regeneration flow requires integrating `ResponseValidator` checks directly inside the `'retry` loop block (where Sentinel blocks are already handled).
4.  **Verifiable-Work Receipts**: `AgentIdentity::sign` works on raw bytes and produces hex-encoded Ed25519 signatures. Since `AuditChainEntry` relies on serializing the struct to JSON to calculate hashes, signing can be achieved by:
    *   Serializing the entry (sans signature field).
    *   Signing the resulting JSON bytes using `AgentIdentity::sign`.
    *   Inserting the hex signature into a new `signature` field in `AuditChainEntry`.
5.  **Remove pro.rs Stub**: Since `pro.rs` is uncompiled, it must first be declared in `lib.rs`. The stubs (e.g. `TeamMemoryVault::sync_to_s3`) currently return empty `Ok(())` or simple placeholder errors. To fulfill R2.2, all pro-tier APIs must return `Err("This feature requires Kairo Pro.")` when license validation fails.
6.  **Best-of-N Oracle Selection**: The oracles in `oracles.py` take file paths. To implement Best-of-N selection:
    *   The sidecar must receive the prompt and generate $N$ candidate suggestions (using temperature > 0).
    *   For each candidate, the sidecar writes it to a temporary document.
    *   The sidecar runs the respective verifier (e.g. `verify_docx`) on each temp file.
    *   Candidates that fail assertions get a score of `0.0`. Others are ranked by word counts, format consistency, or structural checks.
    *   The highest-scoring candidate is chosen and returned.

---

## 3. Caveats

*   **LibreOffice Dependency**: The `excel_libreoffice_recompute` oracle relies on `soffice.exe` being installed locally. If it is missing (as on standard Github Actions runners), the conversion step will raise a `FileNotFoundError`. The gauntlet must be configured to gracefully bypass or skip this specific test if LibreOffice is not found.
*   **Wasmtime Compilation Issue on Windows**: As documented in the active context, the Rust `kairo-agent-sdk` target fails to compile on Windows due to platform-specific Wasmtime dependency errors. Because of this, workspace-wide test commands (`cargo test --all`) will fail. We must target `phantom-core` explicitly using `cargo test -p phantom-core --tests`.
*   **Npcap/Admin Rights for Network Sniffer**: The Scapy sniffer in `NetworkSnifferOracle` requires admin privileges and Npcap/libpcap drivers on Windows. Since standard runner environments do not support this, we must ensure the `psutil`-based socket scanner fallback is robust and fully covered by tests.

---

## 4. Conclusion

The codebase possesses excellent foundation logic and stable test execution pipelines (both Rust and Python test suites pass 100% locally). However, all 19 GA Hardening requirements are currently stubs or missing entirely. 

To achieve GA Hardening systematically, we recommend a **3-Milestone Execution Plan**:

### Milestone 1: Calibration & Trust (Sprint 4 Core)
*   Unify confidence logic into `memory::feedback::ConfidenceEngine`.
*   Add configurable fields in `config.rs` for `relevance_floor` (R1.3) and `clarity_threshold` (R1.4).
*   Integrate `ResponseValidator` into `main.rs` `'retry` loop for hard-block regeneration.
*   Implement `constitution.txt` verification in `ResponseValidator`.
*   Add Ed25519 signatures to `AuditChainEntry` in `identity.rs`.
*   Add a post-process step in `gui_gauntlet.yml` to generate `task_completion_rate.json`.

### Milestone 2: Hardening & Release (Sprint 5 Core)
*   Add Ed25519 signature checks and SHA-256 validation to `updater.py` (verify downloads).
*   Activate `pro.rs` in `lib.rs` and update all stubs to return strict `Result` errors on invalid license checks.
*   Filter out `PromptOnly` domains in a new `/capabilities` API endpoint in `api.rs`.
*   Implement the Best-of-N candidate generation & oracle scoring loop in the sidecar.
*   Configure dynamic reasoning budget parameters in `llm_caller.py` payloads when `kairo-think` is selected.

### Milestone 3: Production-Ops & Autonomous Gauntlet (Sprint 5.5 - 7 Core)
*   Integrate Syft, cargo-audit, and Gitleaks into `ci.yml`.
*   Implement PII-scrubbing (regex-based regex mapping for paths, usernames, and document content) in `crash_reporter.py`.
*   Add OpenTelemetry local JSONL file-exporting telemetry for Python and Rust.
*   Build the Vagrant/Hyper-V sandbox automation scripts.
*   Implement the Test-Fix-Test loop engine with the four guards.
*   Set up mutation testing and synthetic persona agents.

---

## 5. Verification Method

To verify the codebase status and test infrastructure independently, run the following commands:

### Rust Core Tests Verification
Run the core Rust test suite targeting `phantom-core`:
```powershell
cargo test -p phantom-core --tests
```
*Expected Result*: All 140+ unit/integration tests pass (including prompt injection, governance, WASM sandbox, and sentinel tests).

### Python Sidecar Tests Verification
Run the Python test suite inside the `kairo-sidecar` directory:
```powershell
cd kairo-sidecar
python -m pytest
```
*Expected Result*: All 670+ tests pass (verifying Word/Excel/PowerPoint masters, creators, and telemetry stubs).

### Specific Stub Verification
*   **Updater Test**: Verify the updater stubs pass:
    ```powershell
    python -m pytest tests/test_updater.py
    ```
*   **Domain Degradation Test**: Verify that domain capabilities are correctly configured:
    ```powershell
    cargo test -p phantom-core --test test_domain_degradation
    ```
