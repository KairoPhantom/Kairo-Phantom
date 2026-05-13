# 🧠 KAIRO PHANTOM — MASTER AGENT MEMORY
## Version: v4.0 → Production-Ready | Updated: 2026-05-13

---

## 1. WHAT KAIRO PHANTOM IS

**Kairo Phantom** is a Rust-native AI ghost-writer that overlays any desktop app (Word, PowerPoint, Excel, VS Code, Figma, Terminal) and injects AI-generated text via keyboard simulation + clipboard. The user presses **Alt+M**, types a `//` command, and Kairo streams AI output directly into the focused application.

**Core Binary:** `phantom-core/` → compiles to `kairo-phantom`  
**Entry Point:** `phantom-core/src/main.rs` (744 lines)  
**Language:** Rust 2021, async Tokio, WGPU, Wasmtime  
**Platform:** Windows primary, macOS + Linux partial  

---

## 2. CURRENT ARCHITECTURE (WHAT EXISTS)

### Files in `phantom-core/src/`:
| File | Purpose | Status |
|------|---------|--------|
| `main.rs` | Event loop, orchestration | ✅ Complete |
| `ai.rs` | LLM backends (Ollama/OpenAI/Anthropic/Gemini) | ✅ Complete |
| `sentinel.rs` | SentinelSanitizer (anti-leakage) | ✅ Complete |
| `guardrails.rs` | PromptGuard (injection detection) | ✅ Partial |
| `pii_guard.rs` | PII redaction | ✅ Complete |
| `quality_gate.rs` | 7-mode hallucination checker | ✅ Complete |
| `writing_pipeline.rs` | 5-stage pipeline (Plan→Write→Review→Revise→Finalize) | ✅ Partial |
| `memory.rs` | 3-layer memory (session/episodic/skill) | ✅ Partial |
| `memory_store.rs` | SQLite persistence | ✅ Complete |
| `context7.rs` | Context7 ground-truth docs | ✅ Complete |
| `command_protocol.rs` | `//` delimiter parsing | ✅ Complete |
| `swarm/` | Multi-agent routing | ✅ Complete |
| `document_context.rs` | Doc extraction (DOCX/PPTX/XLSX) | ✅ Complete |
| `kami_export.rs` | Kami export pipeline | ⚠️ Stub |
| `wgpu_effects.rs` | GPU rendering | ⚠️ Stub |
| `wasm_sandbox.rs` | WASM plugin sandbox | ⚠️ Partial |
| `identity.rs` | Ed25519 agent identity | ⚠️ Partial |
| `governance.rs` | Audit log | ✅ Complete |
| `yjs_peer.rs` | CRDT collaborative editing | ✅ Complete |
| `perf_engine.rs` | Zero-alloc Tokio runtime | ✅ Complete |
| `verify.rs` | `kairo verify` CLI | ✅ Complete |
| `skills/` | Waza skill directory | ✅ Structure exists |
| `context_optimizer.rs` | Token optimization | ⚠️ Stub |
| `aws_emulation.rs` | Floci AWS local | ⚠️ Stub |

### Skills directory (`skills/` in repo root):
- `think/`, `design/`, `check/`, `write/`, `learn/`, `read/`, `health/`, `facts-discover/`, `facts-implement/`
- All directories exist but SKILL.md files may be incomplete

---

## 3. THE COMPLETE REMAINING ROADMAP

### 🔴 CRITICAL — Must Fix First (Phase 1)
1. **SentinelLeakGuard hardening** — `sentinel.rs` needs real NLI verification (not placeholder `true`)
2. **PromptGuard completeness** — `guardrails.rs` needs all 20+ injection patterns
3. **WritingPipeline** — `writing_pipeline.rs` Devil's Advocate + Style Reviewer agents missing
4. **QualityGate** — `quality_gate.rs` needs real 7-mode blocking (not stubs)

### 🟠 HIGH — Core Intelligence (Phase 2)
5. **Kreuzberg extractor** — Replace commented-out dep in Cargo.toml; implement `KreuzbergExtractor` in `extractors/`
6. **spdf PDF extractor** — Spatial PDF extraction for `extractors/pdf_extractor.rs`
7. **text-splitter semantic chunking** — Already in Cargo.toml, wire into document pipeline
8. **Context7 enrichment** — Make `context7.rs` fetch real docs (not mock)
9. **Kairo.facts** — 48 facts file needs all 39-scenario commands

### 🟡 MEDIUM — Specialist Architecture (Phase 3)
10. **5 Specialist Agents** — Word, PPT, Excel, Design, Code each need full system prompts + tools in `swarm/`
11. **Waza Skills SKILL.md files** — All 8 skills need complete instructions
12. **Kami Export pipeline** — Full Markdown→PDF→RevealJS in `kami_export.rs`
13. **Brand profile** — `~/.config/kairo/brand.md` reader

### 🟢 MEDIUM — Memory & Learning (Phase 4)
14. **Learning loop** — After-action review recording accepted/rejected in `memory.rs`
15. **User model (Honcho-style)** — Per-app tone/formatting preferences
16. **`// health` full report** — Show all memory stats + component status

### 🔵 OPTIMIZATION — Engine Hardening (Phase 5-6)
17. **SIMD text diffs** — `memchr` in `ghost_session.rs`
18. **Zero-alloc SSE parser** — `ai.rs` streaming upgrade
19. **WGPU real rendering** — `wgpu_effects.rs` needs real fragment shaders
20. **Wasmtime real JIT** — `wasm_sandbox.rs` replace stub with real Engine+Module
21. **Ed25519 real keypair** — `identity.rs` use `ed25519-dalek` properly
22. **Append-only audit JSONL** — `governance.rs` chain-hashed log
23. **Yjs sub-document segmentation** — `yjs_peer.rs`

### 🟣 ENTERPRISE — Tier 8 (Phase 7)
24. **OIDC/SSO integration** — Enterprise auth in `identity.rs`
25. **Cloud Sync** — Document sync infrastructure
26. **Floci AWS emulation** — `aws_emulation.rs` real implementation
27. **Plugin registry** — `plugins.kairo.dev` manifest + ed25519 signing

### ✅ VERIFICATION — Gauntlet (Phase 8)
28. **39-scenario test matrix** — `kairo verify` must exit 0
29. **Chaos monkey validation** — `chaos.rs` integration
30. **CI/CD** — `.github/workflows/ci.yml` gate enforcement

---

## 4. KEY FILES TO KNOW

### Cargo.toml dependencies (already added):
- `tokio`, `reqwest`, `serde`, `anyhow`, `uuid`, `text-splitter`, `memchr`
- `wgpu = "22"`, `wasmtime = "21.0"`, `ed25519-dalek = "2.1"`, `rusqlite`
- `once_cell`, `axum`, `yrs`, `ollama-rs`, `rdev`, `enigo`, `uiautomation`

### Command Protocol (`//` delimiter):
- `//` = ghost-write
- `//!` = critical/urgent
- `//? ` = query mode (no modify)
- `// think` = planning mode
- `// design` = design mode
- `// check` = review mode
- `// write` = prose mode
- `// learn` = research mode
- `// read` = fetch URL
- `// health` = system audit
- `// kami` = document export

### Memory Layers:
1. **Session** — in-memory, reset on restart
2. **Episodic** — SQLite `~/.kairo-phantom/memory.db`
3. **Skill** — SQLite + skills dir, self-improving

---

## 5. PRODUCTION REQUIREMENTS (ALL MUST PASS)

### Zero-Tolerance Rules:
1. ZERO system-prompt leakage in any output
2. ZERO hallucinated APIs or facts (Context7 grounds all)
3. ZERO injection attacks getting through (PromptGuard blocks)
4. ALL 39 W1-T4 scenarios pass on Windows + Linux
5. `kairo verify` exits 0 with ≥35 @implemented facts
6. 3 consecutive gauntlet runs with zero failures

### 39-Scenario Matrix:
- **W1-W10**: Word ghost-write scenarios
- **P1-P7**: PowerPoint generation scenarios
- **X1-X5**: Excel formula/data scenarios
- **F1-F5**: Figma design scenarios
- **T1-T4**: Terminal command scenarios
- **C1-C4**: Cross-app scenarios
- **S1-S4**: Security scenarios (injection/leakage)

---

## 6. AGENT ASSIGNMENTS

| Agent | Responsibility | Target Files |
|-------|---------------|-------------|
| **Alpha (Security)** | Sentinel + PromptGuard + QualityGate hardening | `sentinel.rs`, `guardrails.rs`, `quality_gate.rs`, `pii_guard.rs` |
| **Beta (Intelligence)** | Kreuzberg + Context7 + WritingPipeline | `extractors/`, `context7.rs`, `writing_pipeline.rs` |
| **Gamma (Specialists)** | 5 Waza specialist agents + skills | `swarm/`, `skills/*/SKILL.md` |
| **Delta (Memory)** | Learning loop + user model + Kami | `memory.rs`, `memory_store.rs`, `kami_export.rs` |
| **Epsilon (Engine)** | SIMD + WGPU + Wasmtime + Ed25519 | `wgpu_effects.rs`, `wasm_sandbox.rs`, `identity.rs`, `perf_engine.rs` |
| **Zeta (Verification)** | Kairo.facts + 39-scenario gauntlet + CI/CD | `verify.rs`, `Kairo.facts`, `.github/workflows/` |

---

## 7. VERIFICATION COMMANDS

```bash
# Build
cd KairoPhantom/phantom-core && cargo build --release

# Run facts verification
./kairo-phantom verify

# Run single scenario test
cargo test --test e2e_win_t1 -- --nocapture

# Run full gauntlet
python scripts/agent_runner.py win all

# Check for leakage
cargo test --test sentinel_leakage -- --nocapture
```

---

## 8. ARCHITECTURE INVARIANTS

1. **Injection Layer is UNCHANGED** — clipboard → UIA SetValue → Enigo → Figma-MCP → PPTX-MCP
2. **Rust is the core** — Python/JS only for MCP servers and scripts
3. **Offline is primary** — Ollama first, cloud fallback second
4. **Silent by default** — NEVER auto-modify without user Tab confirmation
5. **One-operation undo** — Ctrl+Z reverts entire AI operation
6. **XML prompt structure** — `<system>`, `<document_context>`, `<user_prompt>`, output ONLY in `<output>` tags

---
*This memory document is the ground truth for all agents. Read this first before touching any file.*
