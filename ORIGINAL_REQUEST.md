# Original User Request

## Initial Request — 2026-06-08T21:26:29+05:30

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

## Follow-up — 2026-06-08T23:05:32+05:30

Implement and verify the Kairo Phantom v3.9.0 1000x Upgrade Master Roadmap and Launch Checklist. The goals are: (1) python-docx write-back with XML-level insertion, (2) QLoRA 4B model schema compliance, (3) LiteLLM 3-Tier/4-Tier smart routing, (4) create-from-scratch creators (DocxCreator, PptxCreator, XlsxCreator), and (5) passing all 14 production gates.

Working directory: `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom`
Integrity mode: development

### Open Questions

> [!IMPORTANT]
> 1. **Model Fine-Tuning Execution**: Since running Unsloth QLoRA fine-tuning for a 4B model requires GPU resources that may not be active in this headless local test environment, should the agent team simulate the fine-tuned model or use a mock model helper for the compliance evaluator, or should they attempt to run the full training loop locally?
> 2. **Manual Gates**: PR-09 (Windows installation time) and PR-10 (Alt+M hotkey stress test) are designated as MANUAL. Should the agent team implement automated script simulations for these to achieve a 100% automated test run?

### Requirements

#### R1. python-docx Write-Back Integration
- Wire python-docx write-back into `sidecar/masters/word_master.py` to write directly to `.docx` files with correct styles.
- `WordWriter.apply_operations()` must use XML-level `ref_para._element.addnext(new_para._element)` for paragraph insertion (never `doc.add_paragraph()` which appends to end).
- Implement atomic write via `tmp+rename` pattern with a backup copy before saving.

#### R2. Unsloth Fine-Tuning & Model Swap
- Evaluate compliance of model against Kairo's DocxOperation, ExcelOperation, and SlideOperation schemas using `scripts/eval_schema_compliance.py`.
- If compliance rate is >= 95%, replace `kairo-standard` with `kairo-fast` in `litellm_config.yaml` to route simple operations to the fast fine-tuned model.

#### R3. Routa Smart Routing (LiteLLM 3-Tier/4-Tier)
- Configure `sidecar/litellm_config.yaml` with 4 tiers: `kairo-fast` (fine-tuned 4B model), `kairo-standard` (Qwen2.5-7B), `kairo-think` (Qwen3-8B reasoning), and `kairo-cloud` (Claude Sonnet).
- Set up fallback chains: `kairo-fast` -> `kairo-standard` -> `kairo-cloud` and routing logic based on prompt token count, confidence, and task type.

#### R4. Document Creators
- Implement `sidecar/creators/docx_creator.py`, `pptx_creator.py`, and `xlsx_creator.py` from scratch.
- These creators must generate new files using standard libraries and open them using `os.startfile()`.

#### R5. Production Gates Execution
- Run all production gates using `kairo-sidecar/pr_gate_runner.py` and ensure they are all fully automated and verified.
- Target: Pass at least 13/14 gates, with PR-01, PR-02, PR-03, PR-04, and PR-08 being non-negotiable.

### Acceptance Criteria

#### Production Gate Compliance
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

## Follow-up — 2026-06-09T01:15:38+05:30

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

