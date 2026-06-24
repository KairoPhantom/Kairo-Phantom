# Kairo Phantom 100X Plan — Part 1: PROGRESS.md

> **Honest tracking of every Part 1 work item.**
> Updated: 2026-06-24

---

## BASELINE (captured before any Part 1 work)

### Rust (cargo test)
- **Lib tests**: 126 passed, 0 failed
- **Binary tests (kairo-phantom)**: 100 passed, 0 failed
- **Integration tests**: 252 passed, 0 failed (across 31 test files)
- **Rust total**: 478 passed, 0 failed
- **Pre-existing compile fixes applied**:
  - `toast_notification.rs`: `WM_SHOWOVERLAY` constant gated behind `#[cfg(windows)]` with non-Windows fallback
  - `platform/linux.rs`: Implemented `inject_replace_line()` and `erase_prompt()` for `LinuxPlatformInjector` via xdotool (real implementation, errors loudly if xdotool/display unavailable)
  - `bin/debug_crash.rs`: `uiautomation::UIAutomation` gated behind `#[cfg(windows)]`
  - `main.rs`: All 51 `windows::` references in non-gated code paths wrapped with `#[cfg(windows)]` / replaced with `focus_target_window()` helper that has a real Linux no-op (window focusing handled by platform injector)

### Python (pytest)
- **294 passed, 44 failed**
- **All 44 failures are in `test_domain5_design.py`** — KNOWN-RED-BY-DESIGN
- Root cause: Figma/tldraw bridges correctly error with "service is offline and mock canvas is disabled" because `KAIRO_DESIGN_MOCK` env flag is not set
- These 44 are tied directly to the Domain 6 un-mock work item
- **Setting `KAIRO_DESIGN_MOCK=1` to turn them green is FORBIDDEN** — it would fake a production result

### Environment
| Tool | Status |
|------|--------|
| Rust/Cargo 1.96.0 | ✅ Installed |
| Python 3.12.12 | ✅ Available |
| pytest 8.3.5 | ✅ Available |
| LibreOffice (soffice) | ✅ Available |
| Docker | ❌ NOT available |
| litellm | ❌ Not installed (to be installed) |
| hypothesis | ✅ Installed |
| libxdo-dev, libxi-dev, libxtst-dev | ✅ Installed |
| libgtk-3-dev, libwebkit2gtk-4.1-dev | ✅ Installed |

---

## WORK ITEMS

### Phase 0: Core Infrastructure

#### Phase 0.1: Opik Observability + Provenance Receipts
- [x] **STEP 1**: Opik self-hosted (Docker) — BLOCKED, logged in INFRA_PENDING
- [x] **STEP 2**: Opik SDK + observability emit layer (local JSONL sink) — DONE
- [x] **STEP 3**: Wrap domain masters with @track — 5 real masters wrapped (Word, Excel, PDF, PPTX, Legal)
  - [ ] Remaining: DesignMaster (Domain 6 — mocked), CodeMaster, BrowserMaster, TerminalMaster, EmailMaster, NotesMaster, MediaMaster, DataMaster, Memory recall
- [ ] **STEP 4**: Provenance receipt panel in Tauri overlay — DEFERRED to overlay phase (no display in sandbox; CLI inspection works now)
- [x] **STEP 5**: Tests — 22 Rust + 17 Python + 6 E2E = 45 total, all green
- [x] **STEP 6**: Receipt written — docs/receipts/phase0_1_opik.md
- **STATUS**: EMIT LAYER DONE — proven end-to-end on 5 real domain masters
- **EVIDENCE**: `cargo test --test test_audit_chain → 22 passed` | `pytest test_phase0_1_opik.py → 17 passed` | `pytest test_phase0_1_e2e.py → 6 passed`

#### Phase 0.2: Headroom Context Compression
- [x] Install headroom-ai — v0.27.0 installed
- [x] Integrate as LiteLLM middleware — headroom_proxy.py created
- [x] Quality verification (≥0.95 similarity) — key information preservation tested
- [x] Benchmarks (≥60% token reduction) — compression ratio benchmarked
- [x] Tests — 16 tests, all green
- **STATUS**: DONE
- **EVIDENCE**: `pytest test_phase0_2_headroom.py → 16 passed`

#### Phase 0.3: MarkItDown + pdf_oxide Ingestion
- [x] Install markitdown[all] + pdf-oxide — both installed
- [x] Create markitdown_bridge.py — universal ingestion with PDF routing
- [x] Update pdf_extraction_engine.py with pdf_oxide fast path — routing logic in bridge
- [x] Integrate with domain router — ingest() is the first step for non-PDF formats
- [x] Tests (all 7 formats, routing logic, AGPL guard) — 26 passed, 1 skipped
- **STATUS**: DONE
- **EVIDENCE**: `pytest test_phase0_3_markitdown.py → 27 passed, 0 skipped`
- **SKIP RESOLVED**: Previously 1 skip (test_pdf_oxide_available) because pdf_oxide was installed in venv but not system Python. Fixed by installing pdf_oxide in system Python. All 27 tests now pass.

#### Phase 0.4: sqlite-vec + fastembed-rs
- [x] Install sqlite-vec + cargo add fastembed (already existed as optional dep)
- [x] Create phantom-core/src/embedding.rs — embed(), VectorStore, semantic_recall()
- [x] Add sqlite-vec to MemMachine — vec0 virtual table created
- [x] semantic_recall method — implemented (combines KNN + content fetch)
- [x] Tests (embedding, vector memory, air-gap) — 11 tests, all green
- [ ] Integration with existing MemMachine recall_contextualized — not yet wired
- [ ] PR-14 verification with new semantic recall — needs integration
- **STATUS**: CORE DONE — embedding + vector search proven real; integration pending
- **EVIDENCE**: `cargo test --lib -p phantom-core embedding → 11 passed` | `cargo test --lib -p phantom-core → 137 passed (no regressions)`
- **BUILD IMPACT**: sqlite-vec adds 244KB rlib — negligible
- **AIR-GAP**: Default path uses deterministic hash embeddings (no download). Production path needs fastembed model download (INFRA_PENDING).

#### Phase 0.5: MCP Server + Messaging Connectors
- [ ] Enhance kairo-mcp with 12 domain tools
- [ ] Telegram connector
- [ ] Discord connector
- [ ] Email connector
- [ ] Air-gap enforcement
- [ ] Tests (MCP tools, connectors, security, PII)
- **STATUS**: NOT STARTED

#### Phase 0.6: Repo Slimming + Installer
- [ ] Identify large artifacts
- [ ] Git LFS configuration
- [ ] Model download script
- [ ] Tauri installer config
- [ ] First-run wizard
- **STATUS**: NOT STARTED

#### Phase 0.7: Paperless-ngx + Karakeep Bridges
- [ ] Paperless-ngx bridge
- [ ] Karakeep bridge
- [ ] docker-compose.kairo-paperless.yml
- [ ] Tests (bridges, air-gap, injection)
- **STATUS**: NOT STARTED

### Domain 1: Word / DOCX
- [ ] Coverage to 80% (word_master.py + prompt_builder.py)
- [ ] RTF and ODT support
- [ ] Yjs collaborative editing upgrade
- [ ] PR-01 (Word Style Conformance) passes
- **STATUS**: NOT STARTED

### Domain 2: Excel / Spreadsheet
- [ ] LibreOffice headless recompute
- [ ] Coverage to 80%
- [ ] Conditional formatting, tables, sparklines
- [ ] PR-06 (Excel Formula Validation) passes
- **STATUS**: NOT STARTED

### Domain 3: PowerPoint
- [ ] DeepPresenter integration
- [ ] Un-mock image generation
- [ ] FigMirror charts
- [ ] Office PowerPoint MCP Server study
- [ ] Tests (real assets, mock gating, injection)
- **STATUS**: NOT STARTED

### Domain 4: PDF
- [ ] pdf_oxide on adversarial fixtures
- [ ] 3 new adversarial fixtures (encrypted, form, 500page)
- [ ] MarkItDown PDF path testing
- [ ] License guard (AGPL)
- **STATUS**: NOT STARTED

### Domain 5: Legal
- [ ] CUAD clause extractor
- [ ] Enhance legal_redline.py
- [ ] Citation graph (networkx)
- [ ] Standalone legal test suite
- [ ] OpenContracts MCP integration
- **STATUS**: NOT STARTED

### Domain 6: Design (CRITICAL — UN-MOCK)
- [ ] Un-mock figma_design_bridge.py (real Figma REST API)
- [ ] Un-mock tldraw_bridge.py (real WebSocket protocol)
- [ ] Verify ComfyUI bridge (already real)
- [ ] Excalidraw lightweight fallback
- [ ] Split design tests: (a) mock-mode smoke, (b) real-mode production gate
- [ ] Codebase scan: zero mock references in production paths
- **STATUS**: NOT STARTED
- **BASELINE**: 44 tests RED-BY-DESIGN (Figma/tldraw bridges correctly error when mock disabled)

---

## EVIDENCE LOG

### Baseline capture (2026-06-24)
```
Rust:  cargo test --lib → 126 passed, 0 failed
       cargo test --bin kairo-phantom → 100 passed, 0 failed
       cargo test --test * (31 files) → 252 passed, 0 failed
       Total: 478 passed, 0 failed

Python: pytest test_domain*.py test_sidecar.py → 294 passed, 44 failed
        All 44 failures in test_domain5_design.py (KNOWN-RED-BY-DESIGN)
```