# 👻 Kairo Phantom

### The AI copilot that works in any Windows app. 100% offline. Remembers how you write.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](kairo-sidecar/)
[![Rust 1.78+](https://img.shields.io/badge/rust-1.78%2B-orange?logo=rust&logoColor=white)](phantom-core/)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Tests passing](https://img.shields.io/badge/tests-787%20passing-brightgreen)](phantom-core/tests/)
[![100% Offline](https://img.shields.io/badge/offline-100%25%20local-blueviolet)](phantom-core/src/ai.rs)

---

```powershell
# One-click install — sets up Ollama, pulls the model, and starts the daemon
irm https://get.kairo.sh | iex
# or: winget install kairo-phantom
```

**Then open Word, type `// your request`, and press `Alt+Ctrl+M`.**  
Kairo writes directly into your document — no copy/paste, no browser tab, no cloud.

![Kairo in action](docs/demo.gif)

---

## What is Kairo?

You already know how to write. Kairo makes sure your *first* draft reads like your *tenth*.

Press `Alt+Ctrl+M` in any Windows application and describe what you need — Kairo reads the document you have open, understands its structure, and writes the next section for you, in your voice, right where your cursor is. It runs entirely on your machine using a local LLM, so nothing you type ever reaches a server.

**Three things no other AI writing tool does:**

| | Kairo Phantom | GitHub Copilot | ChatGPT |
|---|:---:|:---:|:---:|
| **Works in Word, Excel, PowerPoint, Terminal, PDF, Browser…** | ✅ OS-level hook | ❌ IDE only | ❌ Browser tab only |
| **Writes IN your document** (no copy/paste) | ✅ Ghost-text injection | ⚠️ Inline suggestions | ❌ You paste manually |
| **Gets smarter the more you use it** | ✅ MemMachine local memory | ⚠️ Repo-scoped only | ❌ Forgets every session |
| **100% offline — works air-gapped** | ✅ | ⚠️ Optional | ❌ Requires internet |
| **Your data stays on your machine** | ✅ Zero telemetry | ⚠️ Code sent to cloud | ❌ All prompts logged |

---

## 🚀 Quick Start

### Option 1 — One-click (recommended)

```powershell
irm https://get.kairo.sh | iex
```

This script installs Ollama, pulls the default model, registers the daemon as a Windows service, and configures the global `Alt+Ctrl+M` hotkey — all in under 90 seconds.

### Option 2 — winget

```powershell
winget install kairo-phantom
```

### Option 3 — Build from source (Rust required)

```bash
cargo install kairo-phantom
kairo first-run
```

> **60-second quickstart guide:** [docs/QUICKSTART.md](docs/QUICKSTART.md)

---

## 🧠 MemMachine — Kairo Gets Smarter Every Session

Every time you use Kairo, it quietly records what you wrote, how you wrote it, and which style choices you made. That data is stored in a local SQLite database on your machine.

The next time you press `Alt+Ctrl+M`, Kairo doesn't start from scratch — it looks up your writing history for that app and injects your style profile directly into the prompt before it calls the model.

**The result:** Kairo's second response in Word will sound more like you than its first. By the tenth session, it feels like a ghostwriter who has been with you for years.

### See it working right now

```bash
python scripts/memmachine_demo.py
```

This runs a deterministic 3-session simulation:

- **Session 1** — records a formal cover letter, an Excel formula, and a bullet-point summary
- **Session 2** — queries MemMachine and shows the recalled style context
- **Session 3** — displays the side-by-side diff between a generic prompt and a memory-augmented one

### Privacy promise

MemMachine stores everything in `~/.kairo/memmachine.db` — a file on your machine. It is never synced, never uploaded, never shared. You own it completely.

```bash
kairo export-memory   # back up your style profile to an encrypted .kpx file
kairo import <file.kpx>  # restore on a new machine
```

---

## 📱 Supported Apps

Kairo's OS-level keyboard hook means it works in *every* window, but these apps receive deepest structural support:

| App | Integration depth | What Kairo can do |
|:---|:---:|:---|
| **Microsoft Word** | ⭐⭐⭐ Full | Reads OOXML AST; writes headings, tables, lists, footnotes |
| **Microsoft Excel** | ⭐⭐⭐ Full | Understands cell context; generates formulas, comments, summaries |
| **Microsoft PowerPoint** | ⭐⭐ Deep | Reads slide structure; writes speaker notes and bullet content |
| **VS Code / Terminal** | ⭐⭐ Deep | Code-aware completions with security and performance review |
| **PDF Viewer** | ⭐⭐ Deep | 3-tier router (text-native → OCR → VLM) extracts full content |
| **Browser** | ⭐ Standard | Captures visible page text for context |
| **Email clients** | ⭐ Standard | Thread-aware reply drafting |
| **Obsidian** | ⭐ Standard | Markdown-native; respects vault structure |
| **Any other app** | ✅ Text | Universal fallback via clipboard capture |

---

## 🏗️ Architecture (for developers)

Kairo Phantom is a three-layer stack communicating over named pipes:

```
┌─────────────────────────────────────────────────────┐
│  phantom-core  (Rust daemon)                        │
│  ├── hotkey.rs          — global Alt+Ctrl+M hook    │
│  ├── injector.rs        — ghost-text SendInput      │
│  ├── document_context.rs — OOXML AST + PDF router   │
│  └── main.rs            — named pipe orchestrator   │
├─────────────────────────────────────────────────────┤
│  kairo-sidecar  (Python, LiteLLM)                   │
│  ├── mem_machine.py     — MemMachine SQLite client  │
│  ├── router.py          — model routing             │
│  └── swarm/             — 8 specialist agents       │
├─────────────────────────────────────────────────────┤
│  Local LLM  (Ollama / LiteLLM)                      │
│  └── Any GGUF model — Mistral, Llama3, Qwen…        │
└─────────────────────────────────────────────────────┘
```

**IPC:** Rust daemon ↔ Python sidecar communicate over a local named pipe (`\\.\pipe\kairo`).  
**Model routing:** LiteLLM abstracts the local model; swap models in `config/kairo.toml` with zero code changes.

Full technical documentation: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🛠️ Key Commands

| Command | What it does |
|:---|:---|
| `Alt+Ctrl+M` | Trigger Kairo in the active window |
| `kairo seed <folder>` | Seed MemMachine from a folder of existing documents |
| `kairo export-memory` | Back up your style profile to an encrypted `.kpx` file |
| `kairo import <file.kpx>` | Restore a style profile on a new machine |
| `kairo owasp-report` | Generate a signed OWASP Agentic AI compliance matrix |
| `kairo audit-verify` | Verify SHA-256 audit chain integrity |

---

## 🔒 Enterprise & Security

Kairo is built for regulated environments — legal, healthcare, finance, and government — where sending data to a cloud is not an option.

| Control | Implementation |
|:---|:---|
| **`//` Protocol Gate** | No `//` prefix → silent abort, zero LLM calls |
| **Prompt Injection Firewall** | 50 detectors across 6 layers (`prompt_injection_firewall.rs`) |
| **SHA-256 Audit Chain** | Every ghost-write session recorded in a tamper-evident chain |
| **OWASP Agentic Top 10** | [10/10 controls met](docs/security/OWASP_AGENTIC_TOP10_COMPLIANCE.md) |

Full security documentation: [docs/security/](docs/security/)

## Competitive Positioning

> "After Google Pointer, you still have to do the work. After Kairo, the work is done."

| Feature | Kairo Phantom | Google Magic Pointer | Copilot | Grammarly | Notion AI |
|---------|:---:|:---:|:---:|:---:|:---:|
| Writes into documents | ✅ | ❌ suggests only | ✅ cloud | ❌ suggestions | ❌ Notion only |
| 100% offline | ✅ | ❌ cloud | ❌ cloud | ❌ cloud | ❌ cloud |
| Remembers your style | ✅ | ❌ | ❌ | ❌ | ❌ |
| Any Windows app | ✅ | ❌ hardware-specific | ❌ M365 only | ❌ browser only | ❌ Notion only |
| Free / open source | ✅ MIT | ❌ | ❌ subscription | freemium | ❌ subscription |
| SPIFFE-signed edits | ✅ | ❌ | ❌ | ❌ | ❌ |
| Local fine-tuning | ✅ | ❌ | ❌ | ❌ | ❌ |

**The 1000x Argument**: It's not a feature list — it's the combination of **100% offline privacy** + **cross-application context** + **local fine-tuning** that creates the ultimate defensible moat.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for the commit conventions and PR checklist.

```bash
# Run the full test suite
cargo test --workspace

# Run the Python sidecar tests
cd kairo-sidecar && pytest

# Run the MemMachine demo
python scripts/memmachine_demo.py
```

See [ROADMAP.md](ROADMAP.md) for planned features and [docs/launch/](docs/launch/) for the launch kit.

---

## 📄 License

MIT © Kartik Hulmukh — see [LICENSE](LICENSE) for details.

---

*"Kairo doesn't replace your voice. It makes your first draft indistinguishable from your tenth."*
