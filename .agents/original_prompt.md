## 2026-06-07T05:08:04Z
Implement the end-to-end features and integrations of Kairo Phantom as specified in kairoreal.docx, focusing on cross-platform accessibility reading, visual screen context, specialist domain masters (Word, Excel, PowerPoint, PDF, Collaborative Yjs docs), and the three-layer agentic architecture (Intent Gate, Planning Engine, Streaming Injection).

Working directory: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom
Integrity mode: development

## Requirements

### R1. Cross-Platform Accessibility Tree & Fallback Chain
Integrate platform accessibility readers natively using each platform's APIs (Windows UIA, macOS AXUIElement, Linux AT-SPI2) to read focused element text. Implement a context fallback chain: accessibility tree -> clipboard capture -> farscry screenshot-OCR -> pure prompt.

### R2. Specialist Domain Masters & Writers
Ensure native, format-preserving edits for:
- Word (DOCX): Track Changes edits via Adeu and headless safe-docx.
- Excel (Spreadsheets): surrounding cell context and Forge formula validation.
- PowerPoint: presentation layouts and slide edits.
- PDF: multi-tier extraction (spdf, OpenDataLoader, olmOCR) and normalized markdown.
- Collaborative: Yjs CRDT shared types and peer awareness sync.

### R3. Three-Layer Agentic Architecture
Implement a structured execution flow for all requests:
1. Intent Gate: classifies intent and filters prompt injections or compliance risks.
2. Planning Engine: decomposes the request into 3-7 discrete, user-approvable steps.
3. Streaming Injection: streams characters to the active document with real-time verification and post-injection checks.

## Acceptance Criteria

### Core Functionality
- [ ] Accessibility tree reading falls back gracefully to clipboard and screenshot-OCR.
- [ ] Word Track Changes and Excel formula validation run offline without external network queries.
- [ ] Planning Engine provides a fallback checklist when LLM planning fails.

### Test Coverage
- [ ] All 533 Python pytest scenarios pass successfully.
- [ ] All Rust core unit and integration tests pass successfully.
- [ ] The 39-scenario production gauntlet runs to completion with zero failures.

## 2026-06-07T06:30:17Z
Implement all launch features, domain master enhancements, and production fixes for Kairo Phantom v3.9.0 to ensure 100% compliance with all 14 production gates under a local-only, air-gapped execution profile.

Working directory: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom
Integrity mode: demo

## Requirements

### R1. Word Master Conformance & Architecture Fixes
- **Style Conformance**: Ensure the `WordContextExtractor` captures the exact style inventory, document purpose, paragraph inventory, and list levels.
- **XML-Level Insertion**: Ensure `WordWriter` uses XML-level `ref_para._element.addnext()` to insert paragraphs at the correct indices rather than appending to the end.
- **Variable Injection Order**: Enforce the prompt builder variable injection order: (1) app context, (2) doc context, (3) mem context, (4) classification, (5) user prompt last.
- **JSON Enforcement**: Include JSON rules in every master prompt, strip markdown fences, and retry on JSONDecodeError.
- **Atomic File Saves**: Save files atomically using the temporary file copy-and-rename pattern to prevent data corruption on crash.

### R2. MemMachine SQLite client & style recall loop
- SQLite storage backend must record interaction preferences and query them for top-K memories.
- Seamless write-back loop between domain masters and `MemMachineClient`.

### R3. Offline Execution Profile
- Zero cloud dependencies. Verify that all operations work entirely offline without outbound socket connections.

### R4. Kairo Eye AppWatcher & Context Preloader
- Monitor foreground application every 500ms using Win32 API.
- Preload context in the background for active documents to ensure sub-100ms assembly times.

### R5. Complete 14 Production Gates Compliance
- Execute and pass the full suite of 14 production gates (PR-01 through PR-14) under the offline test suite.

## Acceptance Criteria

### Domain Master Verification
- [ ] Pytest suite completes with 100% pass rate (all 544+ tests passing).
- [ ] `prompt_builder.py` produces correctly ordered prompts without unreplaced tokens.
- [ ] Word writer inserts paragraphs at correct index relative to original paragraphs.
- [ ] ForgeValidator successfully catches circular references in formulas.

### 14 Production Gates Verification
- [ ] PR-01: Word injection uses correct paragraph style (e.g., Heading 2 instead of Normal).
- [ ] PR-02: GRP never injects without Tab approval (Esc cancels, zero chars added).
- [ ] PR-03: System prompt never leaks (OutputVerifier fails on instruction leakage).
- [ ] PR-04: Zero outbound socket connections in offline mode.
- [ ] PR-05: Ctrl+Z undoes entire injection atomically.
- [ ] PR-06: Excel formulas validated before injection (balanced parens autofix, invalid functions rejected).
- [ ] PR-07: Adjacent cells/paragraphs never modified.
- [ ] PR-08: Sidecar crash leaves original file intact (atomic saves via tmp + rename pattern).
- [ ] PR-09: First token under 2s (7B) / 600ms (3B).
- [ ] PR-10: One-click installer installs under 90s on fresh VM.
- [ ] PR-11: Rapid Alt+M (10x in 2s) causes zero crashes.
- [ ] PR-12: 8-hour memory leak test passes.
- [ ] PR-13: Domain master correctly identified 95%+ of the time.
- [ ] PR-14: MemMachine style recall across sessions.

## 2026-06-07T07:55:52Z

Verify and implement all 5 critical engineering fixes for Microsoft Word integration and 14 production launch gates described in the Kairo Phantom v3.9.0 Executive Summary & Engineering Brief.

Working directory: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom
Integrity mode: development

## Requirements

### R1. Forensic Audit of the 5 Word Master Fixes
- **Fix 1 (Variable Injection Order)**: Audit `sidecar/prompt_builder.py` and `word_prompt_builder.py` to ensure context variables are injected in order: app_name -> doc_context -> mem_context -> classification -> user_prompt last. Ensure fallback defaults are active.
- **Fix 2 (XML Paragraph Insertion)**: Ensure `WordWriter._insert_paragraph()` uses XML-level `ref_para._element.addnext(new_para._element)` and operations are sorted in reverse index order.
- **Fix 3 (WordContextExtractor & Validator)**: Ensure context extractor builds a rich document snapshot in <200ms and validator handles fuzzy style matching and index clamping.
- **Fix 4 (JSON Enforcement & Retry)**: Ensure the JSON output reminder is appended immediately before the user instruction in every domain master prompt. Audit the LiteLLM calling wrapper (`llm_caller.py`) to ensure it strips markdown fences, retries exactly once on JSONDecodeError with the specific error correction prompt, and sets `response_format` JSON mode.
- **Fix 5 (Atomic Saves)**: Ensure `WordWriter.apply_operations()` uses the tmp+rename pattern (`.kairo_tmp` saved and then `os.replace` to original) with a `.kairo_bak` backup.

### R2. Verification of all 14 Production Gates
- Audit and run all 14 production gate test suites (`kairo-sidecar/tests/test_*.py` for PR-01 to PR-14) to confirm they execute successfully, cover all required specifications, and properly mock hardware (such as Win32 COM APIs).

## Acceptance Criteria

### Prompt & Code Validation
- [ ] Assembled prompts for all domains place user instructions at the very end of the prompt string.
- [ ] The string 'REMINDER: Your entire response must be a single JSON object. First character must be {. Last character must be }.' appears immediately before the user instruction in all domain master prompts (including Word, Excel, PowerPoint, Code, PDF, Browser, Terminal, Email, Notes, Design, Media, and Data).
- [ ] `llm_caller.py` retries once with the exact text 'Your previous response was not valid JSON. Output ONLY the JSON object, nothing else.' when `json.JSONDecodeError` is raised.
- [ ] All 261/261 unit tests pass successfully with 0 failures and 0 errors when running `python -m pytest kairo-sidecar/tests/`.

## 2026-06-07T13:38:27Z

Upgrade and launch Kairo Phantom to support offline 1000x document writing with correct python-docx write-backs, Smart routing, from-scratch creation, local memory graph, and pass all 14 production gates.

Working directory: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`
Integrity mode: development

## Requirements

### R1. Fix python-docx Write-Back and Extraction Latency
- Implement XML-level `addnext()`/`addprevious()` paragraph insertions inside `WordWriter`.
- Enforce the atomic `tmp+rename` save pattern and rotate backup files.
- Optimize `WordContextExtractor.extract` to run in under **100ms** (or under **300ms** on larger documents) by using a single-pass loop and direct XML node verification instead of multiple iterations and slow python-docx properties. This is required to pass the **PR-14** gate.

### R2. Implement Create From Scratch
- Implement `DocxCreator`, `PptxCreator`, and `XlsxCreator` to programmatically build new files from structured layouts.
- Save created documents under `~/Documents/Kairo/` and open them automatically using `os.startfile()`.

### R3. Wire Routa/LiteLLM 4-Tier Smart Routing
- Configure LiteLLM routing with four tiers: `kairo-fast` (4B model, <=150 tokens, confidence >=0.75, latency ~400ms), `kairo-standard` (Qwen2.5-7B, latency ~1.8s), `kairo-think` (Qwen3-8B reasoning model, latency ~4s), and `kairo-cloud` (Claude/Gemini API, latency ~3s).
- Set up fallback chain: `fast` -> `standard` -> `cloud`.

### R4. Complete the 5 Highest-Traction Features
- **Personal Model Fine-Tuning**: Auto-trigger overnight QLoRA fine-tuning on user's style corrections (at 2:00 AM local time).
- **MemMachine Style Recall**: Persist style preferences in SQLite/Model2Vec on Tab press and retrieve them dynamically.
- **Atomic Undo**: Restore pre-injection state via MD5 hash verification in one Ctrl+Z.
- **GRP Reasoning Trace**: Display the reasoning/style rules in a collapsible side panel.
- **Air-Gap Installer**: WiX/NSIS setup bundling Ollama and local model GGUF.

### R5. Integrate Local Repositories
- Index files with `docsagent` on load.
- Query semantic graphs with `Ontos-AI/knowhere`.
- Migrate to SurrealDB (CodaCite) for users with >10,000 interactions.
- Automate Canva editing via background `trope-cua` and `agent-computer-use` accessibility trees.
- Upgrade browser injection with `xa11y` direct `set_value()` / `type_text()`.
- Incorporate `WeKnora` citation pipeline for PDF Q&A.

---

## Acceptance Criteria

### Production Gate Success
- [ ] Run `python kairo-sidecar/pr_gate_runner.py` and verify that all automated checks pass.
- [ ] Specifically, **PR-14** (100-page docx context assembly time) must pass with an execution time under **2.0 seconds** (target <1.0s).
- [ ] Ensure non-negotiables PR-01, PR-02, PR-03, PR-04, and PR-08 all report `PASS`.
- [ ] The composite score of the memory benchmark (PR-13) must be verified and passing.

## 2026-06-07T18:14:53Z

Integrate three advanced capabilities (Autonomous Skill Creation, Document Graph Memory, and Feynman Verification Agent) into Kairo Phantom following strict architectural boundaries (consume as a dependency/subprocess, thin bridge, layer Kairo's intelligence) and update licensing attribution in THIRD_PARTY_NOTICES.md.

Working directory: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`
Integrity mode: demo

## Requirements

### R1. Autonomous Skill Creation (Hermes Agent Pattern)
- Create `phantom-core/src/skill_factory.rs` to watch the Planning Engine trace for successful multi-step tasks.
- Extract the sequence of operations (e.g. Adeu, ExcelMcp, PPTAgent calls) based on the document specialist and original prompt.
- Generate a Waza agent manifest (TOML) with keyword triggers, app contexts, and system prompts derived from the task.
- Store the manifest and a `SKILL.md` file in `~/.kairo-phantom/skills/auto/<skill_id>/`.
- Display a native overlay prompt using `show_overlay` asking: “Save this workflow as a skill? [Tab] Yes”.
- Intercept the next Tab keypress in `hotkey.rs` low-level keyboard proc if `SKILL_SAVE_PENDING` is active to register the skill immediately.

### R2. Document Graph Memory (Graphify / GraphRAG Pattern)
- Add `petgraph = "0.6.5"` to `phantom-core/Cargo.toml`.
- Create `phantom-core/src/memory/document_graph.rs` to build a persistent document entity graph. Use SQLite (`rusqlite`) for database persistence and `petgraph` for in-memory graph operations.
- On first run, scan directories listed in the `document_graph_folders` configuration setting in `config.toml` (defaulting to `~/Documents/Kairo/`).
- Parse document text and extract entities (people, companies, dates, legal clauses, monetary values) using local LLM/Ollama structured prompts.
- Map nodes (documents and entities) and edges (relationships like MENTIONS).
- In `intent_gate.rs` and `main.rs`, query the graph when the prompt references an entity or asks a cross-document question and inject the enriched context into the LLM system prompt.
- Handle `//?` commands (like `//? list entities` or `//? query <name>`) directly in `main.rs` to query the local graph.

### R3. Feynman Verification Agent (Self-Critique Pattern)
- Create a Waza agent manifest and `SKILL.md` for "Feynman Verifier" in `~/.kairo-phantom/skills/feynman-verifier/`.
- Add a verification step in `main.rs` before final text injection: call the local backend with the Feynman system prompt to explain the output simply.
- If the model output flags any logical gap or unexplained concept with `[GAP: <reason>]`, return the gap for a targeted re-generation attempt (max 1 retry).
- Create `scripts/training/dspy_prompt_optimizer.py` (and root wrapper `training/dspy_prompt_optimizer.py`) to run a DSPy program offline, executing `cargo test --test kmb1_benchmark` as the evaluation metric to optimize Waza agent system prompts.

## Acceptance Criteria

### Licensing & Attribution
- [ ] `THIRD_PARTY_NOTICES.md` is updated with exact entries for petgraph, GraphRAG, Hermes Agent, Feynman, and DSPy.
- [ ] No external source code is copied into the Kairo Phantom source tree.

### Autonomous Skill Creation
- [ ] `phantom-core/src/skill_factory.rs` exists and watches/reflects on Planning Engine traces.
- [ ] Native overlay is shown and Tab keypress is intercepted in `hotkey.rs` to save the skill.
- [ ] The saved skill TOML and `SKILL.md` are stored in `~/.kairo-phantom/skills/auto/` and automatically loadable.

### Document Graph Memory
- [ ] `petgraph` crate dependency is added to `Cargo.toml`.
- [ ] `phantom-core/src/memory/document_graph.rs` exists, indexes configured folders, and enriches Intent Gate context.
- [ ] `//?` query commands return correct entity relationship text from the graph.

### Feynman Verification Agent
- [ ] "Feynman Verifier" manifest and `SKILL.md` exist.
- [ ] Verification step filters Planning Engine output and triggers targeted re-generation on flagged gaps.
- [ ] Python sidecar includes `training/dspy_prompt_optimizer.py` using DSPy.

## 2026-06-08T17:35:32Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Implement and verify the Kairo Phantom v3.9.0 1000x Upgrade Master Roadmap and Launch Checklist. The goals are: (1) python-docx write-back with XML-level insertion, (2) QLoRA 4B model schema compliance, (3) LiteLLM 3-Tier/4-Tier smart routing, (4) create-from-scratch creators (DocxCreator, PptxCreator, XlsxCreator), and (5) passing all 14 production gates.

Working directory: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`
Integrity mode: development

## Open Questions

> [!IMPORTANT]
> 1. **Model Fine-Tuning Execution**: Since running Unsloth QLoRA fine-tuning for a 4B model requires GPU resources that may not be active in this headless local test environment, should the agent team simulate the fine-tuned model or use a mock model helper for the compliance evaluator, or should they attempt to run the full training loop locally?
> 2. **Manual Gates**: PR-09 (Windows installation time) and PR-10 (Alt+M hotkey stress test) are designated as MANUAL. Should the agent team implement automated script simulations for these to achieve a 100% automated test run?

## Requirements

### R1. python-docx Write-Back Integration
- Wire python-docx write-back into `sidecar/masters/word_master.py` to write directly to `.docx` files with correct styles.
- `WordWriter.apply_operations()` must use XML-level `ref_para._element.addnext(new_para._element)` for paragraph insertion (never `doc.add_paragraph()` which appends to end).
- Implement atomic write via `tmp+rename` pattern with a backup copy before saving.

### R2. Unsloth Fine-Tuning & Model Swap
- Evaluate compliance of model against Kairo's DocxOperation, ExcelOperation, and SlideOperation schemas using `scripts/eval_schema_compliance.py`.
- If compliance rate is >= 95%, replace `kairo-standard` with `kairo-fast` in `litellm_config.yaml` to route simple operations to the fast fine-tuned model.

### R3. Routa Smart Routing (LiteLLM 3-Tier/4-Tier)
- Configure `sidecar/litellm_config.yaml` with 4 tiers: `kairo-fast` (fine-tuned 4B model), `kairo-standard` (Qwen2.5-7B), `kairo-think` (Qwen3-8B reasoning), and `kairo-cloud` (Claude Sonnet).
- Set up fallback chains: `kairo-fast` -> `kairo-standard` -> `kairo-cloud` and routing logic based on prompt token count, confidence, and task type.

### R4. Document Creators
- Implement `sidecar/creators/docx_creator.py`, `pptx_creator.py`, and `xlsx_creator.py` from scratch.
- These creators must generate new files using standard libraries and open them using `os.startfile()`.

### R5. Production Gates Execution
- Run all production gates using `kairo-sidecar/pr_gate_runner.py` and ensure they are all fully automated and verified.
- Target: Pass at least 13/14 gates, with PR-01, PR-02, PR-03, PR-04, and PR-08 being non-negotiable.

## Acceptance Criteria

### Production Gate Compliance
- [ ] Running `python kairo-sidecar/pr_gate_runner.py` reports `LAUNCH DECISION: READY`.
- [ ] Gate PR-01 passes: injected paragraph uses correct paragraph style name.
- [ ] Gate PR-02 passes: Esc cancels injection and leaves paragraph count unchanged.
- [ ] Gate PR-03 passes: system prompt/internal terms never leak to GRP output.
- [ ] Gate PR-04 passes: zero external connections made in offline mode.
- [ ] Gate PR-08 passes: context assembly latency is under 100ms.
- [ ] Gate PR-11 passes: domain detection is >= 94% correct.
- [ ] Gate PR-12 passes: MemMachine recalls style preferences correctly across sessions.
- [ ] Gate PR-13 passes: Memory benchmark score is compiled and recorded.
- [ ] Gate PR-14 passes: 100-page document context prep time is under 2 seconds.
- [ ] At least 13 out of 14 gates pass.



## 2026-06-08T19:45:38Z

Implement and verify the Kairo Phantom v3.9.0 1000x Upgrade Master Roadmap and Launch Checklist. The goals are: (1) python-docx write-back with XML-level insertion, (2) QLoRA 4B model schema compliance, (3) LiteLLM 3-Tier/4-Tier smart routing, (4) create-from-scratch creators (DocxCreator, PptxCreator, XlsxCreator), and (5) passing all 14 production gates.

Working directory: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`
Integrity mode: development

## Open Questions

> [!IMPORTANT]
> 1. **Model Fine-Tuning Execution**: Since running Unsloth QLoRA fine-tuning for a 4B model requires GPU resources that may not be active in this headless local test environment, should the agent team simulate the fine-tuned model or use a mock model helper for the compliance evaluator, or should they attempt to run the full training loop locally?
> 2. **Manual Gates**: PR-09 (Windows installation time) and PR-10 (Alt+M hotkey stress test) are designated as MANUAL. Should the agent team implement automated script simulations for these to achieve a 100% automated test run?

## Requirements

### R1. python-docx Write-Back Integration
- Wire python-docx write-back into `sidecar/masters/word_master.py` to write directly to `.docx` files with correct styles.
- `WordWriter.apply_operations()` must use XML-level `ref_para._element.addnext(new_para._element)` for paragraph insertion (never `doc.add_paragraph()` which appends to end).
- Implement atomic write via `tmp+rename` pattern with a backup copy before saving.

### R2. Unsloth Fine-Tuning & Model Swap
- Evaluate compliance of model against Kairo's DocxOperation, ExcelOperation, and SlideOperation schemas using `scripts/eval_schema_compliance.py`.
- If compliance rate is >= 95%, replace `kairo-standard` with `kairo-fast` in `litellm_config.yaml` to route simple operations to the fast fine-tuned model.

### R3. Routa Smart Routing (LiteLLM 3-Tier/4-Tier)
- Configure `sidecar/litellm_config.yaml` with 4 tiers: `kairo-fast` (fine-tuned 4B model), `kairo-standard` (Qwen2.5-7B), `kairo-think` (Qwen3-8B reasoning), and `kairo-cloud` (Claude Sonnet).
- Set up fallback chains: `kairo-fast` -> `kairo-standard` -> `kairo-cloud` and routing logic based on prompt token count, confidence, and task type.

### R4. Document Creators
- Implement `sidecar/creators/docx_creator.py`, `pptx_creator.py`, and `xlsx_creator.py` from scratch.
- These creators must generate new files using standard libraries and open them using `os.startfile()`.

### R5. Production Gates Execution
- Run all production gates using `kairo-sidecar/pr_gate_runner.py` and ensure they are all fully automated and verified.
- Target: Pass at least 13/14 gates, with PR-01, PR-02, PR-03, PR-04, and PR-08 being non-negotiable.

## Acceptance Criteria

### Production Gate Compliance
- [ ] Running `python kairo-sidecar/pr_gate_runner.py` reports `LAUNCH DECISION: READY`.
- [ ] Gate PR-01 passes: injected paragraph uses correct paragraph style name.
- [ ] Gate PR-02 passes: Esc cancels injection and leaves paragraph count unchanged.
- [ ] Gate PR-03 passes: system prompt/internal terms never leak to GRP output.
- [ ] Gate PR-04 passes: zero external connections made in offline mode.
- [ ] Gate PR-08 passes: context assembly latency is under 100ms.
- [ ] Gate PR-11 passes: domain detection is >= 94% correct.
- [ ] Gate PR-12 passes: MemMachine recalls style preferences correctly across sessions.
- [ ] Gate PR-13 passes: Memory benchmark score is compiled and recorded.
- [ ] Gate PR-14 passes: 100-page document context prep time is under 2 seconds.
- [ ] At least 13 out of 14 gates pass.



