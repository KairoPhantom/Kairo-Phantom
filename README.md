# Kairo Phantom 👻

> The first open-source, Rust-native AI ghost writer for any Windows app.

Press `Ctrl+Space` anywhere — in Word, a PDF reader, your browser, VS Code, Notepad — and Kairo Phantom reads what you are writing, sends it to your local AI, and **ghost-types the completion directly into your document** at human-like speed.

No copy-paste. No drag-and-drop. No browser extension. A true AI peer writing alongside you at the OS level.

---

## How It Works

```
You type in Word/Chrome/VS Code/Notepad
         ↓
[Ctrl+Space]
         ↓
Kairo reads your text via Windows UI Automation
         ↓
Text streams into a CRDT session (yrs — pure Rust Yjs)
         ↓  
Local Ollama LLM generates continuation
         ↓
Ghost-types the suggestion back into your app
character by character at 15ms/char
```

## Quick Start

### Prerequisites
- Windows 10/11
- [Ollama](https://ollama.com/) running locally with `ollama pull llama3`
- [Rust](https://rustup.rs/) installed

### Run from source
```bash
git clone https://github.com/Kartik24Hulmukh/KairoPhantom
cd KairoPhantom
cargo run --release -p phantom-core
```

### Usage
1. Open any text editor (Word, Notepad, VS Code, your browser)
2. Start typing something
3. Press `Ctrl+Space`
4. Watch the Ghost write alongside you

## Configuration

Config lives at `~/.kairo-phantom/config.toml` (auto-created on first run):

```toml
hotkey = "ctrl+space"
typing_delay_ms = 15

[model]
provider = "ollama"           # "ollama" | "openai" | "anthropic" | "gemini"
model_name = "llama3"
base_url = "http://localhost:11434"

# For cloud providers:
# provider = "openai"
# model_name = "gpt-4o-mini"
# api_key = "sk-..."
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Kairo Phantom Core (Rust)               │
│                                                  │
│  UIA Reader    ──→  CRDT Session (yrs)           │
│  (any app)          (AI peer: clientID 999)      │
│                           ↓                      │
│                    AI Backend                    │
│                    (Ollama/OpenAI/etc.)          │
│                           ↓                      │
│  Injector      ←──  Suggestion text              │
│  (enigo — ghost typing into active app)         │
└─────────────────────────────────────────────────┘
```

### Core Crates
| Crate | Version | Purpose |
|-------|---------|---------|
| `uiautomation` | 0.25 | Read text from any Windows app |
| `enigo` | 0.2 | Ghost-type into any Windows app |
| `yrs` | 0.21 | Pure Rust CRDT (Yjs port) — AI peer state |
| `rdev` | 0.5 | Global hotkey listener |
| `tokio` | 1.44 | Async runtime |

### AI Providers
- **Ollama** (default, local, private)
- **OpenAI** (GPT-4o-mini etc.)
- **Anthropic** (Claude Haiku etc.)
- **Google Gemini** (Gemini 1.5 Flash etc.)

## Why Rust?

- Sub-millisecond hotkey response
- ~8MB binary (vs 270MB for Electron apps)
- No JavaScript runtime embedded — pure native
- Zero GC pauses during ghost typing
- Binary-compatible CRDT state with `@docscode/core` (TypeScript)

## Companion Library

Kairo Phantom is the desktop runtime of the [Kairo](https://github.com/Kartik24Hulmukh/Kairo) ecosystem.
The CRDT state it maintains is binary-compatible with `@docscode/core` — enabling seamless sync between desktop ghost writing and web-based collaborative editing.

```bash
npm install @docscode/core
```

## Roadmap

- [x] UIA text reader (Windows)
- [x] Ghost typing via enigo
- [x] CRDT session via yrs
- [x] Ollama / OpenAI / Anthropic / Gemini adapters
- [x] Ctrl+Space global hotkey
- [ ] Tauri glassmorphic overlay
- [ ] macOS support (Accessibility API)
- [ ] MCP server mode (Claude Code / Cursor integration)
- [ ] Autocomplete / Summarize behavior plugins

## License

MIT
