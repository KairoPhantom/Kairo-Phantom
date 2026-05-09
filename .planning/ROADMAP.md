# Kairo Phantom — ROADMAP v3.0 (Universal Document Peer)

## Current Status
- **Milestone 1 (Engine v2.0):** ✅ COMPLETE
- **Milestone 2 (v3.0 Universal):** 🚧 PLANNED

---

## Milestone 2: v3.0 — Universal Document AI Peer
**Target:** 12 weeks | **Goal:** #1 trending open-source AI tool

### Architecture Reference
```
Hotkey Listener
     │
     ▼
[Platform Accessibility Layer] ← Pillar 1: Cross-Platform (xa11y-inspired, original impl)
     │  Windows (UIAutomation) | macOS (AXUIElement) | Linux (AT-SPI2)
     │
     ▼
[Context Engine + Document Understanding] ← Pillar 2: Deep Doc Context
     │  office_oxide (DOCX/XLSX/PPTX) | litchi (ODT/iWork) | mdkit (PDF/MD)
     │  DocumentContext { outline, tables, active_slide, tracked_changes }
     │
     ▼
[Swarm Brain — Multi-Agent Orchestrator] ← Plugin System (Pillar 5)
     │  Design Agent | Prose Agent | Code Agent | Terminal Agent | Data Agent
     │  Plugin trait: SwarmAgent | AppFingerprinter
     │
     ▼
[LLM Backend] ← Pillar 3: Offline-First
     │  Ollama (DEFAULT, offline) → OpenAI → Anthropic → Gemini → NVIDIA NIM
     │
     ▼
[Injector — Clipboard-First, multi-strategy]
     │
     ├── [MCP Server: kairo-mcp] ← Pillar 4: Distribution to Claude/Cursor/Goose
     └── [Tauri Overlay — glassmorphic]
```

---

## Phase Breakdown

### Phase 1: Cross-Platform Accessibility Foundation
**Week 1-2 | Pillar 1**

| Task | Agent | Details |
|---|---|---|
| Create `platform/` module structure | Backend Architect | `mod.rs` + `windows.rs` + `macos.rs` + `linux.rs` |
| Extract `AccessibilityReader` trait | Backend Architect | `get_focused_text()` + `get_clipboard_text()` |
| Windows implementation | Backend Architect | Refactor `uia.rs` → `platform/windows.rs` |
| macOS implementation stub | Backend Architect | `accessibility-rs` + graceful compile |
| Linux implementation stub | Backend Architect | `atspi` crate integration |
| CI: GitHub Actions matrix build | DevOps | Ubuntu + macOS + Windows |
| All existing tests pass | QA | `cargo test` green |

**Deliverable:** `cargo build --release` passes on all 3 platforms.

---

### Phase 2: Deep Document Understanding
**Week 3-4 | Pillar 2**

| Task | Agent | Details |
|---|---|---|
| Design `DocumentContext` struct | Software Architect | Per `newfeature.md` spec |
| Design `DocumentContextExtractor` trait | Software Architect | `async_trait` compatible |
| Implement `OfficeOxideExtractor` (DOCX) | Backend Dev | Heading outline, tables, tracked changes |
| Implement `OfficeOxideExtractor` (PPTX) | Backend Dev | Slide count, per-slide text extraction |
| Implement `OfficeOxideExtractor` (XLSX) | Backend Dev | Sheet names + CSV extraction |
| Implement `PlainTextFallback` extractor | Backend Dev | Notepad, VS Code, Terminal path |
| Implement `ExtractorRegistry` | Backend Dev | Plugin-ready registry |
| Wire to `context.rs` → file path resolution | Backend Dev | Window title → process args → Registry path |
| Wire `to_system_prompt_fragment()` → Swarm Brain | Backend Dev | Inject into all agent prompts |
| Feature flag `--features office` | Backend Dev | Clean compile with/without office_oxide |
| Integration test: DOCX → Swarm prompt | QA | Verify heading outline appears in LLM call |

**Deliverable:** Pressing Alt+M in Word sends structured document context to the LLM, not just raw text.

---

### Phase 3: Offline Mode — Ollama First
**Week 5-6 | Pillar 3**

| Task | Agent | Details |
|---|---|---|
| Change default config to Ollama | Backend Dev | `provider = "ollama"`, `model = "qwen2.5-coder:14b"` |
| Startup Ollama health check | Backend Dev | GET `/api/tags`, 5s timeout |
| One-liner setup prompt | UX/Dev | Clear, non-panicking startup message |
| Auto-pull model (with consent) | Backend Dev | `ollama pull <model>` via subprocess |
| Config: `fallback` provider field | Backend Dev | Retry once on fallback if Ollama fails |
| Refactor `OllamaBackend` streaming | Backend Dev | Official Ollama streaming API, proper context length |
| Startup log: "Active backend: Ollama (offline)" | Backend Dev | Clear provider status |
| E2E test: no API keys, Ollama running → full flow | QA | Zero-config offline use case |

**Deliverable:** A user with Ollama installed can use Kairo fully offline with zero API keys.

---

### Phase 4: MCP Server — kairo-mcp
**Week 7-8 | Pillar 4**

| Task | Agent | Details |
|---|---|---|
| Create `kairo-mcp/` crate | Backend Architect | Sibling to `phantom-core/` |
| MCP stdio transport protocol impl | Backend Dev | Original implementation per MCP spec |
| Tool: `kairo_read_context` | Backend Dev | Read focused window → JSON response |
| Tool: `kairo_ghost_write` | Backend Dev | Inject text → clipboard → success/error |
| Tool: `kairo_ask` | Backend Dev | Full Alt+M round-trip programmatically |
| Tool: `kairo_detect_app` | Backend Dev | Active process + AppEnvironment → JSON |
| Tool: `kairo_switch_agent` | Backend Dev | Override Swarm Brain routing |
| MCP manifest JSON | Backend Dev | Tool definitions per MCP spec |
| Integration with `phantom-core` HTTP API | Backend Dev | All tools proxy through port 7437 |
| Test with Claude Code | QA | `claude mcp add kairo-phantom-mcp` → works |
| README: Claude Code + Cursor + Goose integration | Technical Writer | Step-by-step setup guide |

**Deliverable:** Any Claude Code or Cursor user can invoke Kairo as an MCP tool in their AI workflow.

---

### Phase 5: Plugin System + Trait Extraction
**Week 9-10 | Pillar 5**

| Task | Agent | Details |
|---|---|---|
| Extract `AppFingerprinter` trait | Software Architect | From `context.rs` |
| Extract `SwarmAgent` trait | Software Architect | From `swarm.rs` |
| Refactor built-in agents to implement trait | Backend Dev | Design, Reasoning, Content → trait impl |
| `AgentRegistry` and `FingerprinterRegistry` | Backend Dev | Mirrors ExtractorRegistry pattern |
| Plugin TOML format spec | Software Architect | Community plugin definition format |
| `[plugins]` section in `config.toml` | Backend Dev | Point to plugin TOML files |
| `kairo-plugin init <name>` CLI | Backend Dev | Scaffold new plugin template |
| Plugin loading at startup | Backend Dev | Deserialize TOML → register in registries |
| Documentation: "Building a Plugin" guide | Technical Writer | From trait definition to TOML file |

**Deliverable:** Community can add new app fingerprinters and AI agents without recompiling Kairo.

---

### Phase 6: Distribution + One-Liner Install
**Week 11-12 | Pillar 5**

| Task | Agent | Details |
|---|---|---|
| Bump version to `0.3.0` all Cargo.toml | DevOps | Workspace version bump |
| `CHANGELOG.md` | Technical Writer | v3.0 feature list |
| GitHub Actions CI matrix | DevOps | Ubuntu + macOS + Windows → artifacts |
| Publish `kairo-phantom` to crates.io | DevOps | `cargo publish` |
| Winget manifest | DevOps | Submit PR to microsoft/winget-pkgs |
| Homebrew formula | DevOps | Submit PR to homebrew-core |
| Final README update | Technical Writer | Full v3.0 arch diagram, install one-liners, MCP guide |
| Demo video script | Content | Ghost-typing demo across Word + VS Code + Notion |

**Deliverable:** `cargo install kairo-phantom` works. GitHub trending potential achieved.

---

## Reference Libraries (for API inspiration only — we build original implementations)
| Crate | Purpose | License | Key Learning |
|---|---|---|---|
| `office_oxide` | DOCX/XLSX/PPTX parsing API patterns | MIT/Apache | Document struct API design |
| `litchi` | ODT/iWork parsing (future) | Unknown | ODF format handling |
| `mdkit` | Universal document → Markdown | Unknown | Format dispatch patterns |
| `atspi` | Linux AT-SPI2 accessibility | LGPL | AT-SPI2 D-Bus protocol |
| `accessibility-rs` | macOS AXUIElement bindings | MIT | macOS a11y API patterns |
| `mouseless` | macOS MCP server reference | Apache | MCP stdio transport design |
| `local-ai-llm-playground` | Ollama + Rust examples | Unknown | Ollama API usage patterns |

## Competing Projects NOT to Copy
- ClipboardConqueror (clipboard delimiter pattern)
- Goose (code agent architecture)
- GhostAI (OCR-only read approach)
- agent-desktop (53-command CLI design)
- OculOS (REST infrastructure approach)
