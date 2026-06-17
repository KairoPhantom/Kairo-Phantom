# Kairo Phantom — DOMAINS.md

> Catalogue of the **12 preserved domains**. Each domain is READ-ONLY for the kernel/wedge work.
> No kernel/wedge PR may modify or delete anything listed here.
> Future launches promote each into a Pack via the re-activation steps below.

---

## Domain Inventory

| # | Domain | Location | Status | Description |
|---|--------|----------|--------|-------------|
| 1 | **Word** | `kairo-sidecar/sidecar/masters/word_master.py`, `masters/word/`, `masters/word_prompt_builder.py`, `writers/docx_writer.py`, `creators/docx_creator.py`, `parsers/docx_parser.py` | PRESERVED | Word document generation, editing, tracked changes, mail merge, TOC |
| 2 | **Excel** | `kairo-sidecar/sidecar/masters/excel_master.py`, `writers/xlsx_writer.py`, `creators/xlsx_creator.py`, `parsers/xlsx_parser.py`, `parsers/excel_context.py`, `parsers/excelmcp_bridge.py`, `parsers/forge_bridge.py` | PRESERVED | Spreadsheet analysis, formula validation, chart generation, pivot tables |
| 3 | **PowerPoint** | `kairo-sidecar/sidecar/masters/other_masters.py` (pptx sections), `writers/pptx_writer.py`, `creators/pptx_creator.py`, `parsers/pptx_parser.py`, `parsers/pptx_context.py`, `parsers/pptx_mcp_bridge.py`, `parsers/slide_image_gen.py` | PRESERVED | Presentation creation, slide design, image generation, deep presenter |
| 4 | **PDF** | `kairo-sidecar/sidecar/parsers/pdf_parser.py`, `parsers/pdf_extraction_engine.py`, `parsers/docling_parser.py`, `parsers/mineru_parser.py`, `writers/pdf_output_writer.py` | PRESERVED | PDF parsing, OCR, extraction, structured data output |
| 5 | **Legal** | `kairo-sidecar/sidecar/parsers/legal_redline.py` | PRESERVED | Legal document redlining, clause comparison, contract analysis |
| 6 | **Design** | `kairo-sidecar/sidecar/parsers/design_bridge.py`, `parsers/figma_design_bridge.py`, `parsers/tldraw_bridge.py`, `parsers/comfyui_bridge.py` | PRESERVED | Design tools integration (Figma, tldraw, ComfyUI) |
| 7 | **Code** | `phantom-core/src/code_context.rs`, `src/code_injector.rs` | PRESERVED | Code context understanding, injection, IDE integration |
| 8 | **Voice/Speech** | `kairo-sidecar/sidecar/speech/`, `kairo-sidecar/sidecar/voice_bridge.py`, `phantom-core/src/voice_engine.rs`, `src/wake_word.rs`, `src/tts_engine.rs` | PRESERVED | Voice commands, TTS, wake word, speech recognition |
| 9 | **Media/Image** | `phantom-core/src/image_pipeline.rs`, `phantom-core/src/deep_presenter.rs` | PRESERVED | Image processing, media pipeline, visual AI |
| 10 | **Memory** | `kairo-sidecar/sidecar/mem_machine.py`, `sidecar/mem_sync.py`, `phantom-core/src/memory/`, `src/memory_store.rs`, `src/memory_vault.rs`, `src/memory_seeder.rs` | PRESERVED | Document graph, memory persistence, semantic search, sync |
| 11 | **Export** | `kairo-sidecar/sidecar/exporters/`, `phantom-core/src/kami_export.rs`, `src/kpx_export.rs` | PRESERVED | Multi-format export (KAMI, KPX), document packaging |
| 12 | **Security/Governance** | `kairo-sidecar/sidecar/safety/`, `sidecar/secret_gate.py`, `sidecar/security_auditor.py`, `phantom-core/src/governance/`, `src/guardrails.rs`, `src/pii_guard.rs`, `src/prompt_injection_firewall.rs`, `src/sentinel.rs` | PRESERVED | Security audit, PII guard, prompt injection firewall, governance |

---

## Re-activation Contract (SPEC §S10)

To promote a domain into a Pack (future, per domain, on its own schedule):

1. **Copy/adapt** the domain code to `PackInterface` in `/packs/<domain>/`
   - Leave the `/domains` original INTACT as the source
   - Implement the `fields`, `extract(chunks)`, and `oracle(fixtures)` methods

2. **Add labeled fixtures + an oracle**
   - Create `fixtures/<domain>/` with real test documents + ground-truth keys
   - Publish a real, measured accuracy number (never fabricated)

3. **Pass the gauntlet** on the full denominator before launch
   - The domain Pack must pass all verification gates
   - PENDING-REAL-APP scenarios counted in the denominator, not passed

4. **No breaking changes** to other domains or the kernel
   - Each domain promotion is independent

---

## CI Guards (SPEC §S0)

Two CI-blocking guards enforce domain preservation:

1. **Kernel Purity** (`scripts/ci/kernel_purity_guard.py`):
   The kernel imports nothing from `/domains` or `/legacy`.

2. **Domains Unchanged** (`scripts/ci/domains_unchanged_guard.py`):
   A kernel PR leaves every file under the domain locations byte-for-byte unchanged.

---

*Kairo Phantom · DOMAINS.md · 12 domains preserved for future launch · never deleted, never modified by kernel work.*
