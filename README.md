<div align="center">

# 👻 Kairo Phantom

### A local-first, cross-application agentic document-intelligence layer for Windows

[![Rust 1.78+](https://img.shields.io/badge/rust-1.78%2B-orange?logo=rust&logoColor=white)](phantom-core/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](kairo-sidecar/)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Tests: 779 passing](https://img.shields.io/badge/tests-779%20passing-brightgreen)](#-testing)
[![Local-first](https://img.shields.io/badge/architecture-local--first-blueviolet)](#-local-first--privacy)

*Kairo Phantom is not a single writing tool — it is an **operating layer for knowledge work**.*  
*An agent that perceives what you're doing across applications, reasons about it with a swarm of domain experts,*  
*and acts on real documents and desktop apps on your behalf — while keeping all data on your machine.*

</div>

---

## Table of Contents

- [What Is Kairo Phantom?](#-what-is-kairo-phantom)
- [Quick Start](#-quick-start)
- [How It Works](#-how-it-works)
- [Architecture](#-architecture)
- [Domain Coverage](#-domain-coverage)
- [Security Stack](#-security-stack)
- [Memory System](#-memory-system)
- [Computer-Use Agent (CUA)](#-computer-use-agent-cua)
- [Local-First & Privacy](#-local-first--privacy)
- [Repository Structure](#-repository-structure)
- [Testing](#-testing)
- [Configuration](#-configuration)
- [CLI Reference](#-cli-reference)
- [Competitive Positioning](#-competitive-positioning)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Security Policy](#-security-policy)
- [License](#-license)

---

## 🧠 What Is Kairo Phantom?

Most AI tools are a chat box bolted onto one app. Kairo Phantom inverts that — it's a **persistent agentic layer** that sits across your entire desktop, understands many document domains deeply, can drive apps directly (computer-use), and treats **trust and verification** as first-class features.

Press `Alt+Ctrl+M` in any Windows application and describe what you need. Kairo reads the document you have open, understands its structure, routes the work to the right domain expert, produces a result, verifies it for safety and quality, and writes it directly into your document — no copy/paste, no browser tab, no cloud.

**What sets Kairo apart:**

| Capability | Kairo Phantom | Copilot / ChatGPT | Other AI Tools |
|:---|:---:|:---:|:---:|
| Works across **any Windows app** (Word, Excel, PPT, Terminal, Browser…) | ✅ OS-level hook | ❌ Single-app | ❌ Browser-only |
| Writes **directly into** your document | ✅ Ghost-text injection | ⚠️ Copy/paste | ❌ Manual |
| **Learns** your writing style over sessions | ✅ MemMachine | ❌ Stateless | ❌ Stateless |
| **100% offline** — works air-gapped | ✅ Zero telemetry | ❌ Cloud-only | ❌ Cloud-only |
| **Real document I/O** (not screenshots) | ✅ python-docx/openpyxl/pptx | ❌ Text-only | ❌ Text-only |
| **Desktop automation** (CUA) | ✅ Windows UIAutomation | ❌ | ❌ |
| Open source | ✅ MIT | ❌ Proprietary | Varies |

---

## 🚀 Quick Start

### Option 1 — One-Click Install (Recommended)

```powershell
irm https://get.kairo.sh | iex
```

This installs Ollama, pulls the default model, registers the daemon as a Windows service, and configures the global `Alt+Ctrl+M` hotkey — all in under 90 seconds.

### Option 2 — winget

```powershell
winget install kairo-phantom
```

### Option 3 — Build From Source

**Prerequisites:** Rust 1.78+, Python 3.12+, Ollama

```bash
# Clone the repository
git clone https://github.com/KairoPhantom/Kairo-Phantom.git
cd Kairo-Phantom

# Build the Rust core
cargo build --workspace

# Install Python sidecar dependencies
cd kairo-sidecar && pip install -r requirements.txt && cd ..

# Run the first-time setup
kairo first-run
```

> 📘 **60-second quickstart guide:** [docs/QUICKSTART.md](docs/QUICKSTART.md)

**Then open Word, type `// your request`, and press `Alt+Ctrl+M`.**  
Kairo writes directly into your document.

---

## ⚡ How It Works

From the user's perspective, the loop is simple — even though a lot happens underneath:

1. **Work normally** in your apps. The Phantom overlay sits alongside, aware of your active document and context.
2. **Invoke Kairo** — type `// your request` or use voice activation, then press `Alt+Ctrl+M`.
3. **Kairo understands & routes** — the security stack vets the input, the intent gate scopes the request, the router dispatches it to the right expert or domain master.
4. **It acts** — the domain engine produces a real result. Where needed, the CUA engine performs actions directly in the live application.
5. **It verifies & applies** — the quality gate and response validator check the output; it's applied to your document with a provenance receipt of what changed.
6. **You stay in control** — accept, edit, or reject. Your feedback feeds the memory/optimizer loop so Kairo improves on your work over time.

---

## 🏗️ Architecture

Kairo Phantom is a three-layer polyglot stack. Input flows down from your context through security and intent understanding, into the expert swarm and domain engines, and back up through quality and safety gates before any action touches your files or apps.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Context Capture                                  │
│   Active app → document structure → user selection → clipboard          │
├─────────────────────────────────────────────────────────────────────────┤
│                        Security Stack                                   │
│   PromptShield → PromptGuard → PiiGuard → ResponseValidator            │
├─────────────────────────────────────────────────────────────────────────┤
│                        Intent Gate                                      │
│   Classifies user intent → scopes the request → selects domain          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────────────────────────┐  │
│  │      Router          │  │            Expert Swarm                 │  │
│  │  Dispatch to best    │→ │  10 specialist experts + domain masters │  │
│  │  expert(s)           │  │  (Word · Excel · PPT · Legal · Code)   │  │
│  └─────────────────────┘  └─────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                       CUA Executor                                      │
│   Plan → Gate → Execute → Verify (Windows UIAutomation)                 │
├─────────────────────────────────────────────────────────────────────────┤
│                       Quality Gate                                      │
│   Correctness check → relevance → safety → apply or reject              │
├─────────────────────────────────────────────────────────────────────────┤
│                        Memory Layer                                     │
│   MemMachine · Document Graph · Feedback · Optimizer                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|:---|:---|:---|
| **Core engine** | Rust (72 source files) | Memory-safe pipeline, security gates, crypto/verification, hotkey hook, ghost-text injection |
| **ML & document sidecars** | Python (48 modules) | Document parsing, LLM orchestration, domain masters, oracles, memory |
| **Desktop overlay** | Tauri (`phantom-overlay`) | Lightweight native UI shell rendered over your apps |
| **Tool/agent protocol** | MCP (`kairo-mcp`) | Model Context Protocol server for tool interoperability |
| **LLM access** | LiteLLM (local gateway) | Single API surface for local or remote language models |
| **Skills registry** | Waza (`skill_factory.rs`) | Packaged, versioned, Ed25519-signed agent skills |
| **IPC** | Named pipes + TCP | Rust core ↔ Python sidecar communication on `\\.\pipe\kairo_sidecar` / `127.0.0.1:7438` |

### Local Process Map

| Service | Endpoint |
|:---|:---|
| Sidecar (primary) | `127.0.0.1:7438` / `\\.\pipe\kairo_sidecar` |
| Voice (Moonshine STT) | `localhost:7439` |
| DeepPresenter engine | `localhost:8765` |
| LLM gateway (LiteLLM) | `localhost:4000/v1/chat/completions` |
| LAN collaboration sync | UDP `47381` (discovery) / TCP `47382` (sync) |

---

## 📱 Domain Coverage

Kairo targets 12+ professional domains. Each domain is backed by real document engines where possible, with an honest "Real vs Prompt-Only" label for transparency.

| Domain | Integration | Backing Technology |
|:---|:---:|:---|
| **Microsoft Word** | ⭐⭐⭐ Full | `python-docx` + tracked-change engine; OOXML AST parsing; headings, tables, lists, footnotes |
| **Microsoft Excel** | ⭐⭐⭐ Full | `openpyxl` + formula validation engine; real cell context, formula generation, data analysis |
| **Microsoft PowerPoint** | ⭐⭐ Deep | `python-pptx` + DeepPresenter engine; enterprise deck generation, slide layouts, speaker notes |
| **Legal / Contracts** | ⭐⭐ Deep | Legal master + redline engine; contract clause analysis, tracked edits (**beachhead domain**) |
| **PDF** | ⭐⭐ Deep | 3-tier router: text-native → OCR → VLM; `pdfplumber` / `PyMuPDF` extraction |
| **Code / VS Code** | ⭐⭐ Deep | Code master; project-aware completions with security and performance review |
| **Terminal** | ⭐⭐ Deep | Command generation, error explanation, git workflow |
| **Email** | ⭐ Standard | Thread-aware reply drafting |
| **Browser** | ⭐ Standard | Captures visible page text for context |
| **Design / Media** | ⭐ Standard | Design bridge + image generation pipeline |
| **Medical** | ⭐ Standard | Domain expert (prompt-backed; honesty-labelled) |
| **Any other app** | ✅ Universal | Clipboard-capture fallback for all Windows applications |

> **Key principle:** a domain that is currently prompt-only must *say so*. Breadth is the vision; honesty about depth is the trust mechanism.

---

## 🔒 Security Stack

Every request passes through the security stack *before* it is trusted, and every output passes through validation before it is applied. This is the most mature, well-tested subsystem.

| Component | Role |
|:---|:---|
| **PromptShield** | First-line prompt-injection defence — detects and neutralises hijack attempts across documents, pasted text, and tool output |
| **PromptGuard** | 6-layer, 50-pattern firewall (`prompt_injection_firewall.rs`) with DAN/override/system-probe detection, tested across 10 languages |
| **PiiGuard** | Detects and redacts SSNs, emails, credit cards, and API keys before they reach prompts, logs, or outputs |
| **ResponseValidator** | Hard-blocks low lexical overlap or hallucinated turns; validates safety, format, and relevance before output is applied |
| **Sentinel Sanitizer** | Hash verification + output encapsulation; prevents system prompt leakage |
| **WASM Sandbox** | Wasmtime JIT with Ed25519 plugin signature verification and mandatory security manifests |
| **SPIFFE Identity** | Ed25519 keypair + X.509 SVID machine identity; verified at every inter-agent boundary |
| **RBAC + JIT Revocation** | Scoped TTL tokens; no standing privilege for plugins or agents |
| **Audit Log** | Tamper-evident append-only JSONL with SHA-256 block-hash chaining |

**Design principle:** treat *all* external content — the document you opened, a pasted snippet, a tool result — as untrusted by default. The security stack is the boundary that turns untrusted input into a safe, scoped request.

> 📄 **OWASP Agentic AI Top 10:** [10/10 controls met](docs/security/OWASP_AGENTIC_TOP10_COMPLIANCE.md)  
> 🔐 **Full security documentation:** [docs/security/](docs/security/)

---

## 🧠 Memory System

Memory is what makes Kairo feel like a persistent collaborator rather than a stateless chatbot.

| Component | Purpose |
|:---|:---|
| **MemMachine** | Core memory engine — records what you wrote, how you wrote it, and which style choices you made, stored in a local SQLite database |
| **Document Graph** | `petgraph` + `rusqlite` knowledge graph of documents and relationships; enables GraphRAG search across your work |
| **Mem-GAS** | Memory garbage-and-aging strategy that keeps relevant context and ages out the rest |
| **Feedback Loop** | Captures accept/edit/reject signals — the data that drives improvement |
| **DSPy Optimizer** | Uses accumulated feedback to refine prompts and behaviour over time |

### See it working

```bash
python scripts/memmachine_demo.py
```

This runs a deterministic 3-session simulation showing how Kairo learns your style.

### Privacy

MemMachine stores everything in `~/.kairo/memmachine.db` — a file on your machine, never synced, never uploaded, never shared.

```bash
kairo export-memory            # Back up your style profile to an encrypted .kpx file
kairo import <file.kpx>        # Restore on a new machine
```

---

## 🖥️ Computer-Use Agent (CUA)

The CUA engine lets Kairo *do* things in real desktop applications — not just suggest text.

| Component | Role |
|:---|:---|
| **CUA Planner** | Decomposes goals into concrete desktop action sequences (open, navigate, click, type, save) |
| **CUA Gate** | Safety gate — decides what the agent is allowed to perform; blocklist includes sensitive apps (Task Manager, 1Password, Registry Editor) |
| **CUA Executor** | Windows UIAutomation + keyboard injection; performs actions on the live desktop |
| **World Model** | UIA-based persistent model of UI state; predicts outcomes and catches divergence |
| **VLM Bridge** | Vision-language bridge for reading UI elements visually when no API exists |

**Safety:** CUA is opt-in only (`CuaConfig.enabled = false` by default), rate-limited to 10 actions/60s, and gated behind a blocklist of sensitive applications. Actions are debounced to prevent recursive trigger loops.

---

## 🏠 Local-First & Privacy

Privacy is architectural, not a setting bolted on afterward:

- **On-device by default** — documents and reasoning stay on your machine; the LLM runs through a local gateway
- **Air-gap mode** — a verifiable mode (`KAIRO_OFFLINE=1`) that emits zero outbound network traffic, validated by a connection oracle
- **PII protection** — PiiGuard strips sensitive data from prompts, logs, and outputs
- **Local collaboration** — multi-device work via CRDT-based peer-to-peer sync over LAN (Yjs sub-documents + awareness debouncing)
- **Provenance** — SHA-256 hash-chained audit receipts for every agent action
- **Zero telemetry** — no data leaves your machine unless you explicitly configure a cloud LLM provider

---

## 📂 Repository Structure

```
kairo-phantom/
├── phantom-core/              # Rust core engine (72 source files)
│   ├── src/
│   │   ├── main.rs            # Named-pipe orchestrator
│   │   ├── hotkey.rs          # Global Alt+Ctrl+M hook
│   │   ├── injector.rs        # Ghost-text SendInput
│   │   ├── prompt_injection_firewall.rs  # 50-pattern security firewall
│   │   ├── pii_guard.rs       # PII redaction engine
│   │   ├── identity.rs        # SPIFFE + Ed25519 identity
│   │   ├── skill_factory.rs   # Waza skill registry
│   │   ├── memory/            # Document graph + memory vault
│   │   ├── cua/               # Computer-use automation
│   │   ├── swarm/             # Expert swarm coordination
│   │   └── collaborative/     # CRDT + Yjs peer sync
│   └── tests/                 # Rust integration test suites
│
├── kairo-sidecar/             # Python ML & document sidecar
│   ├── sidecar/
│   │   ├── router.py          # 10-expert domain routing
│   │   ├── mem_machine.py     # MemMachine SQLite client
│   │   ├── oracles.py         # Deterministic verification oracles
│   │   ├── drift_alarm.py     # Calibration drift detection
│   │   ├── masters/           # Domain masters (Word, Excel)
│   │   ├── creators/          # Native doc creators (docx, xlsx, pptx)
│   │   ├── safety/            # BMC gate, secret gate
│   │   ├── cua/               # CUA planner, executor, gate
│   │   └── schemas/           # Pydantic document schemas
│   └── tests/                 # 464 pytest tests
│
├── phantom-overlay/           # Tauri desktop overlay UI
├── kairo-mcp/                 # Model Context Protocol server
├── kairo-agent-sdk/           # Agent development SDK
├── mcp-servers/               # MCP server implementations
├── training/                  # DSPy prompt optimizer + training data
├── scripts/                   # CI gates, gauntlet runners, utilities
├── config/                    # kairo.toml + LiteLLM config
├── docs/                      # Architecture, security, quickstart
├── installer/                 # Windows installer scaffolding
└── plugins/                   # WASM plugin ecosystem
```

---

## 🧪 Testing

Kairo Phantom has a comprehensive, multi-layer test suite:

| Suite | Count | Framework | Coverage |
|:---|:---:|:---|:---|
| **Rust unit + integration** | 315 tests | `cargo test` (proptest, simulation, chaos, e2e) | 7 test layers: unit → property → chaos → e2e → sim → WASM → matrix |
| **Python sidecar** | 464 tests | `pytest` + `hypothesis` | 78% line coverage (4,564 statements measured) |
| **Production gates** | 19 gates | `pr_gate_runner.py` | Word fidelity, Excel formulas, security, CUA, memory, performance |
| **Mutation testing** | 10 mutants | `cargo-mutants` | 100% catch rate (0 survived) |
| **Gauntlet** | 200 scenarios | `run_phase12_gauntlet.py` | Multi-domain, multi-tier judging |

### Run the tests

```bash
# Rust test suite (315 tests)
cargo test --workspace

# Python sidecar tests (464 tests)
cd kairo-sidecar && python -m pytest tests/ -q

# With coverage measurement
python -m pytest tests/ --cov=sidecar --cov-config=../.coveragerc --cov-report=term-missing

# Production gate runner (19 automated gates)
python kairo-sidecar/pr_gate_runner.py

# CI integrity gates
python scripts/ci/no_skip_gates.py          # Forbids @pytest.mark.skip / #[ignore]
python scripts/ci/eval_integrity_guard.py   # Detects fabricated metrics
```

### Quality Gates

- **No-skip enforcement** — `no_skip_gates.py` fails the build if any `@pytest.mark.skip`, `#[ignore]`, or `xfail` is introduced
- **Eval integrity guard** — blocks fabricated metrics or mocked model calls in evaluations
- **Mutation testing** — `cargo mutants` ensures tests actually catch regressions
- **Coverage floor** — 80% line coverage target enforced via `.coveragerc` and CI

---

## ⚙️ Configuration

Kairo is configured through `config/kairo.toml`:

```toml
# Model selection — swap models with zero code changes
[model]
provider = "ollama"          # ollama | litellm | openai
model = "mistral:latest"     # Any GGUF model

# Privacy
[privacy]
offline_mode = false         # Set to true for air-gap mode
pii_redaction = true

# CUA (Computer-Use Agent)
[cua]
enabled = false              # Opt-in only
rate_limit = 10              # Max actions per 60 seconds

# Memory
[memory]
db_path = "~/.kairo/memmachine.db"
```

---

## 🛠️ CLI Reference

| Command | Description |
|:---|:---|
| `Alt+Ctrl+M` | Trigger Kairo in the active window |
| `kairo first-run` | Initial setup — pulls model, registers service, configures hotkey |
| `kairo seed <folder>` | Seed MemMachine from a folder of existing documents |
| `kairo export-memory` | Back up your style profile to an encrypted `.kpx` file |
| `kairo import <file.kpx>` | Restore a style profile on a new machine |
| `kairo owasp-report` | Generate a signed OWASP Agentic AI compliance matrix |
| `kairo audit-verify` | Verify SHA-256 audit chain integrity |
| `kairo --version` | Display version information |
| `kairo plugin list` | List installed WASM plugins |

---

## 🏆 Competitive Positioning

> *"After Google Magic Pointer, you still have to do the work. After Kairo, the work is done."*

| Capability | Kairo Phantom | GitHub Copilot | ChatGPT | Grammarly | Notion AI |
|:---|:---:|:---:|:---:|:---:|:---:|
| Writes into documents | ✅ | ✅ (IDE only) | ❌ | ❌ | ❌ (Notion only) |
| 100% offline capable | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cross-app (any Windows app) | ✅ | ❌ | ❌ | ❌ (browser) | ❌ (Notion) |
| Remembers your style | ✅ | ❌ | ❌ | ❌ | ❌ |
| Desktop automation (CUA) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Free / open source | ✅ MIT | ❌ | ❌ | Freemium | ❌ |
| SPIFFE-signed provenance | ✅ | ❌ | ❌ | ❌ | ❌ |
| Local fine-tuning | ✅ | ❌ | ❌ | ❌ | ❌ |

**The defensible moat:** It's not a single feature — it's the combination of **100% offline privacy** + **cross-application context** + **persistent memory** + **desktop automation** + **real document I/O** that no cloud-first tool can replicate.

---

## 🗺️ Roadmap

| Phase | Timeline | Goals |
|:---|:---|:---|
| **Stability & Core** | Current | Panic-proof engine, WASM sandbox, cross-platform ghost typing, canary beta |
| **Interoperability** | Months 2–3 | Wayland support, mobile companion app, cross-platform clipboard sync |
| **Plugin Ecosystem** | Months 4–5 | Community plugin registry, multi-modal overlay, Memory Nexus API |
| **Enterprise** | Month 6 | SSO/OIDC, air-gap certification, swarm clustering |

See the full roadmap: [ROADMAP.md](ROADMAP.md)

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for commit conventions, the PR checklist, and the development setup guide.

```bash
# Run the full test suite
cargo test --workspace                     # Rust (315 tests)
cd kairo-sidecar && python -m pytest       # Python (464 tests)

# Run the MemMachine demo
python scripts/memmachine_demo.py

# Verify CI gates locally
python scripts/ci/no_skip_gates.py
python scripts/ci/eval_integrity_guard.py
```

**Commit format:** `<type>: <description>` — Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

---

## 🔐 Security Policy

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately via [GitHub Security Advisories](https://github.com/KairoPhantom/Kairo-Phantom/security/advisories/new). We acknowledge reports within 48 hours and provide a resolution timeline within 7 days.

See the full policy: [SECURITY.md](SECURITY.md)

| Version | Support |
|:---|:---|
| 0.3.x | ✅ Active security updates |
| 0.2.x | ⚠️ Critical fixes only |
| < 0.2 | ❌ End of life |

---

## 📄 License

MIT © Kairo Phantom Contributors — see [LICENSE](LICENSE) for details.

---

<div align="center">

*Kairo doesn't replace your voice. It makes your first draft indistinguishable from your tenth.*

**[Documentation](docs/)** · **[Quick Start](docs/QUICKSTART.md)** · **[Security](docs/security/)** · **[Contributing](CONTRIBUTING.md)** · **[Roadmap](ROADMAP.md)**

</div>

