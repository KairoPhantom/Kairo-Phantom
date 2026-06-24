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
- [x] Tests (embedding, vector memory, air-gap) — 12 tests, all green
- [x] KNN not-insertion-order test — proves vector search is real
- [ ] **SEMANTIC RELEVANCE**: test_semantic_relevance_paraphrase_retrieval — PENDING real fastembed model
  - Test exists, gated behind `--features local-embeddings`
  - Hash embeddings are NON-SEMANTIC (documented in test_hash_embeddings_are_non_semantic)
  - **Semantic retrieval verified = PENDING real model; hash path is a NON-SEMANTIC fallback only**
- [ ] **AIR-GAP SEMANTIC SEARCH = NOT yet real (hash fallback)**
  - Air-gap currently falls back to hash embeddings which are non-semantic
  - Real air-gap requires pre-caching the fastembed model (one-time fetch, then offline)
  - Tracked in INFRA_PENDING.md with exact fetch command
- [ ] Integration with existing MemMachine recall_contextualized — not yet wired
- [ ] PR-14 verification with new semantic recall — needs integration
- **STATUS**: CORE MECHANICS DONE — vector store + KNN proven real; SEMANTIC retrieval PENDING real model
- **EVIDENCE**: `cargo test --lib -p phantom-core embedding → 12 passed` | `cargo test --lib -p phantom-core → 138 passed (no regressions)`
- **BUILD IMPACT**: sqlite-vec adds 244KB rlib — negligible

#### Phase 0.5: MCP Server + Messaging Connectors
- [x] Telegram connector — security pipeline (PromptShield + PiiGuard) implemented and tested
- [x] Discord connector — reuses telegram security pipeline, tested
- [x] Email connector — reuses telegram security pipeline, tested
- [x] Air-gap enforcement — all 3 connectors blocked when air-gap ON
- [x] InjectionGuard on inbound — 6 injection tests, all BLOCKED
- [x] PiiGuard on outbound — SSN/email/phone redacted
- [x] Pattern parity — Python PromptShield has 84 patterns (29 Rust hard + 27 Rust soft + 28 additional)
  - Parity test (test_phase0_5_parity.py) verifies every Rust pattern is covered by Python
  - Sync: when guardrails.rs is updated, update prompt_shield.py and run parity test
- [x] E2E connector injection test — malicious messages blocked through all 3 connector handlers
- [x] Tests — 34 tests (13 parity + 21 connector), all green
- [ ] MCP server: expose 12 domain tools — PENDING (not yet done)
- [ ] MCP manifest submission — PENDING (not yet done)
- [ ] Live bot testing — PENDING (needs real tokens, INFRA_PENDING)
- **STATUS**: CONNECTOR SECURITY DONE + PATTERN PARITY PROVEN — MCP server tools + live bots PENDING
- **EVIDENCE**: `pytest test_phase0_5_parity.py test_phase0_5_connectors.py → 34 passed`
- **SECURITY**: Fail-closed design. If PromptShield unavailable → BLOCK. Air-gap → BLOCK.

#### Phase 0.6: Repo Slimming + Installer
- [x] Identify large artifacts — target_check_tmp (401MB), playground/target (89MB), graphify-out/graph.json (17MB)
- [x] Remove from git tracking — git rm --cached on all build artifacts
- [x] Update .gitignore — prevent re-tracking
- [x] MEASURED blob-filtered clone: 101MB total (8.2MB .git + 93MB working tree) — UNDER 500MB ✅
- [ ] Model download script (scripts/download_models.sh) — not yet done
- [ ] Tauri installer build config — not yet verified
- [ ] Installer signing/notarization — INFRA_PENDING (needs real secrets)
- **STATUS**: REPO SLIMMING DONE (101MB < 500MB) — installer + model script pending
- **EVIDENCE**: `git clone --filter=blob:none → 101MB total (was 749MB before slimming)`

#### Phase 0.7: Paperless-ngx + Karakeep Bridges
- [x] Paperless-ngx bridge — real API client (urllib, auth, JSON parsing)
- [x] Karakeep bridge — real API client (urllib, auth, JSON parsing)
- [x] Both bridges FAIL LOUDLY when service unreachable — never silently no-op
- [x] Both bridges disabled by default
- [x] Document content treated as untrusted (PromptShield screening)
- [x] Tests — 17 tests, all green (mock HTTP servers clearly labeled as non-production)
- [ ] docker-compose.kairo-paperless.yml — not yet created (needs Docker, INFRA_PENDING)
- [ ] Live integration against real paperless-ngx/Karakeep — INFRA_PENDING (needs Docker)
- **STATUS**: BRIDGE LOGIC DONE — real API clients tested against mock servers; live integration pending Docker
- **EVIDENCE**: `pytest test_phase0_7_bridges.py → 17 passed`

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