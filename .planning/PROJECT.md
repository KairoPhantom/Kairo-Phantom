# Kairo Phantom — PROJECT.md

## Mission
Kairo Phantom is the **universal document AI peer** for Windows, macOS, and Linux.
It is the only open-source tool that simultaneously:
1. Reads document structure (not just selected text) from Word, PPT, Excel, ODT, PDF
2. Fingerprints the host application (VS Code, Canva, Notion, Figma, Terminal) via UIA/accessibility APIs
3. Routes prompts to a specialized multi-agent swarm (Design, Reasoning, Content, Terminal agents)
4. Streams AI output via SSE and injects it atomically via Clipboard-First injection
5. Runs **offline-first** via Ollama (cloud providers as fallback)
6. Exposes itself as an **MCP server** so any Claude Code / Cursor / Goose user can invoke it

## What We Are NOT Building
- We do NOT copy external repos. We **reference** them, understand their design decisions, and build our own superior implementation from scratch.
- We do NOT build another clipboard copilot (ClipboardConqueror's design flaw).
- We do NOT build a code agent (Goose's design focus — wrong product).
- We do NOT build an OCR reader (GhostAI's design — read-only, no AI peer).

## Competitive Landscape (Why Kairo Wins)
| Competitor | Stars | What It Does | Why We Win |
|---|---|---|---|
| ClipboardConqueror | 433★ | Copy-paste delimiter AI | No UIA, no app awareness, no injection |
| Goose | 41.6k★ | General code agent | Not a document peer, no context routing |
| GhostAI | — | OCR local brain | Read-only, no LLM injection |
| agent-desktop | 125★ | 53-command CLI via a11y tree | No AI, no multi-agent, no injection |
| OculOS | 200★ | REST/MCP desktop control | No AI intelligence layer |
| mouseless | — | macOS MCP desktop control | macOS-only, no document AI |

**The exact gap Kairo fills:** No project combines UIA reading + app fingerprinting + swarm routing + streaming + clipboard injection into a single Rust binary across all platforms.

## Technology Stack (v3.0 Architecture)
```
Hotkey Listener (WH_KEYBOARD_LL / CGEventTap / XInput)
    │
    ▼
xa11y Cross-Platform Accessibility Layer
    │  Windows: UIAutomation │ macOS: AXUIElement │ Linux: AT-SPI2
    │
    ▼
Context Engine + Document Understanding
    │  office_oxide → DOCX/XLSX/PPTX structure
    │  litchi       → ODT/ODF/iWork (.pages, .key, .numbers)
    │  mdkit        → PDF/Markdown/universal fallback
    │  Plugin trait: AppFingerprinter
    │
    ▼
Swarm Brain (Multi-Agent Orchestrator)
    │  Brain LLM picks agent deterministically or via LLM routing
    │  Design Agent | Prose Agent | Code Agent | Terminal Agent | Data Agent
    │
    ▼
LLM Backend (Ollama-first, cloud-fallback)
    │  Ollama (offline) → OpenAI → Anthropic → Gemini → NVIDIA NIM
    │
    ▼
Injector (Clipboard-First, multi-strategy)
    │  Clipboard Ctrl+V → UIA SetValue → SendInput → Fallback
    │
    ├── MCP Server (kairo-mcp) — exposes tools to Claude/Cursor/Goose
    └── Tauri Overlay — glassmorphic status layer
```

## Milestone History

### Milestone 1: Production Engine v2.0 (COMPLETE)
- ✅ Global hotkey hook (WH_KEYBOARD_LL)
- ✅ UIA text extraction and clipboard-first injection
- ✅ App fingerprinting via process name + window title
- ✅ Multi-agent swarm (Design / Reasoning / Content agents)
- ✅ SSE streaming for OpenAI, Anthropic, Gemini, NVIDIA NIM, Ollama
- ✅ SwarmConfig in config.toml for per-agent API keys
- ✅ Context detection for: Word, PowerPoint, VS Code, Terminal, Notion, Figma, Canva, Slack, Teams

### Milestone 2: Kairo v3.0 — Universal Document Peer (IN PROGRESS)
**Goal:** Make Kairo the #1 trending open-source AI tool by becoming the only cross-platform, document-intelligent, offline-capable, MCP-distributed ghost-writing engine.

**5 Pillars:**
1. **Cross-Platform Core** — swap to xa11y for Windows + macOS + Linux (3x market expansion)
2. **Deep Document Understanding** — office_oxide + litchi + mdkit for structural context
3. **Offline Mode** — Ollama as the DEFAULT provider, cloud as fallback
4. **MCP Server** — distribute Kairo to every Claude Code / Cursor / Goose user instantly
5. **Plugin System + One-Liner Install** — community extensibility + cargo install

## Key Source Files
- `phantom-core/src/main.rs` — Tokio event loop orchestrator
- `phantom-core/src/swarm.rs` — Multi-agent routing (Brain + 3 agents)
- `phantom-core/src/context.rs` — App fingerprinting and prompt extraction
- `phantom-core/src/ai.rs` — All LLM backends (SSE streaming)
- `phantom-core/src/injector.rs` — Clipboard-first text injection
- `phantom-core/src/config.rs` — PhantomConfig + SwarmConfig structs
- `phantom-core/src/hotkey.rs` — Global keyboard hook
- `phantom-core/src/uia.rs` — Windows UIA reader
- `phantom-overlay/` — Tauri glassmorphic UI overlay

## Design Principles
1. **Single binary** — `cargo install kairo-phantom` must install everything
2. **Zero config for offline use** — Ollama + Qwen2.5 must work with zero API keys
3. **Trait-based extensibility** — AppContext + SwarmAgent traits enable community plugins
4. **We build, not copy** — Reference external repos for design inspiration only; every line is original
5. **Production first** — No experimental features in the main binary; all unstable behind feature flags
