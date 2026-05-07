# Kairo Phantom

## What This Is

Kairo Phantom is the first open-source, Rust-native "Ghost AI Writer" for the Windows desktop. It is a system-level AI peer that:

1. **Reads** text from ANY active Windows application (Word, PDF viewers, browsers, VS Code, Notepad) using the Windows UI Automation (UIA) API via `uiautomation-rs`.
2. **Streams** the captured text into a pure-Rust CRDT session (`yrs` — Rust port of Yjs) maintaining full collaborative state with an AI as a named peer.
3. **Gets AI suggestions** from a local or cloud LLM (Ollama first, then OpenAI/Anthropic/Gemini adapters) that are aware of the full document context via the CRDT state.
4. **Ghost-types** the AI suggestion back into the active application character-by-character via `enigo` input simulation, creating the illusion of a "ghost" typing alongside the user.
5. **Overlays** a borderless, semi-transparent glassmorphic Tauri UI widget that floats above all windows, showing AI activity, suggestion previews, and presence indicators. Invisible to screen capture via `SetWindowDisplayAffinity`.

## Activation
- **Hotkey**: `Ctrl+Space` (or configurable) to trigger AI suggestion materialization.
- The ghost types at human-like speed (15ms per character) directly into whatever app is focused.
- No drag-and-drop. No copy-paste. The AI peer types for you.

## Core Value
"Your AI writes with you, not for you — in any app, at any time, invisibly."

This is NOT a clipboard tool (like ClipboardConqueror). This is NOT a meeting assistant (like Cluely/Pluely). This is NOT a browser extension. This is a desktop-native AI peer that operates at the OS level.

## Technical Stack
- **Language**: Rust (100% — no JavaScript runtime embedded)
- **CRDT**: `yrs` crate (pure Rust Yjs port by Anysphere, binary protocol compatible with Kairo's `@docscode/core`)
- **UIA Reader**: `uiautomation-rs` (Windows UI Automation wrapper)
- **Input Injection**: `enigo` crate (keyboard simulation, cross-platform fallback)
- **Overlay UI**: Tauri v2 (glassmorphic, always-on-top, screen-share invisible)
- **Hotkey**: `rdev` or `global-hotkey` crate
- **AI Backends**: Ollama (local, default), OpenAI, Anthropic, Gemini (via HTTP adapters in Rust)
- **Screen Context (optional)**: `xcap` crate for screenshot-based context

## Architecture
```
┌─────────────────────────────────────────────────┐
│          Tauri Overlay (Glassmorphic UI)          │
│  - Always-on-top transparent window               │
│  - Screen-share invisible                         │
│  - Hotkey activation                              │
└──────────────────────┬────────────────────────────┘
                       │ Tauri commands (IPC)
┌──────────────────────┴────────────────────────────┐
│           Kairo Phantom Core (Rust)                │
│                                                    │
│  UIA Reader  │  Enigo Writer  │  xcap (optional)   │
│      ↓               ↑                            │
│         CRDT Session (yrs)                        │
│              ↓                                    │
│         AI Peer Engine                            │
│   (Ollama/OpenAI/Anthropic adapters)              │
└───────────────────────────────────────────────────┘
```

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| yrs over neon/deno_core | Pure Rust, no JS runtime, binary-compatible with @docscode/core | Eliminates JavaScript entirely |
| enigo for injection | Universal — works on Chromium, custom controls, elevated apps | Clipboard fallback for edge cases |
| Tauri over Electron | 27x smaller binary, native Rust backend, same JS/TS frontend | ~10MB vs 270MB |
| Ollama as default AI | Local, private, no API key needed for first run | Reduces friction for initial users |
| uiautomation-rs | Battle-tested Windows UIA wrapper in Rust | Read from Word, Chrome, VSCode, Notepad |

## Requirements

### Validated
(None yet — greenfield)

### Active
- [ ] Read focused element text from any Windows app via UIA
- [ ] Integrity-level detection + clipboard fallback for elevated processes
- [ ] Pure Rust CRDT session via `yrs` with AI as named peer
- [ ] Ollama HTTP adapter for local AI inference
- [ ] OpenAI/Anthropic/Gemini HTTP adapters
- [ ] Character-by-character ghost typing via enigo (15ms delay)
- [ ] Configurable hotkey to trigger materialization
- [ ] Tauri v2 glassmorphic overlay (always-on-top, semi-transparent)
- [ ] Screen-share invisibility via SetWindowDisplayAffinity
- [ ] Autocomplete behavior plugin (complete current sentence)
- [ ] Summarize behavior plugin (summarize active document)
- [ ] MCP server integration (Claude Code / Cursor / Windsurf trigger)
- [ ] TOML config file (~/.kairo-phantom/config.toml)
- [ ] GitHub releases with pre-built Windows .exe installer
- [ ] 20-second demo video for HN/X launch

### Out of Scope
- macOS/Linux support in v1 — Windows UIA is the priority
- Browser extension — native OS approach is the differentiator
- Direct UIA SetValue injection — enigo keyboard simulation is more universal

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-05-07 after initialization*
