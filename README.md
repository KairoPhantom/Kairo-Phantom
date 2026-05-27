# 👻 Kairo Phantom

> ⚠️ **BETA — currently stabilizing the core engine.** Core ghost-writing works reliably on Windows. macOS and Linux support is actively being hardened. [Track progress →](ROADMAP.md)

**The 100% local, offline-first AI writing assistant that respects your privacy.**  
*Works in any Windows app — Word, Excel, PowerPoint, Notepad, browsers, and terminals. Press `Alt+M` and it writes.*

<!-- DEMO GIF: Replace this comment with a real screen recording once captured.
     Target: 90-second GIF showing Alt+M in Word → ghost-text streams in → Tab to accept.
     Tool: ShareX or OBS → convert to GIF via gifski. Upload to repo assets/ branch.
     ![Kairo Phantom demo — Alt+M ghost-writes in Word](assets/demo.gif)
-->

[![Tests](https://img.shields.io/badge/tests-787%20passing-brightgreen)](phantom-core/tests/)
[![KMB-1](https://img.shields.io/badge/KMB--1-0.9872-blue)](docs/benchmark/KMB1_RESULTS.md)
[![OWASP](https://img.shields.io/badge/OWASP%20Agentic%20Top%2010-10%2F10-green)](docs/security/OWASP_AGENTIC_TOP10_COMPLIANCE.md)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Offline](https://img.shields.io/badge/offline-100%25%20local-orange)](phantom-core/src/ai.rs)

---

## 🔒 The Privacy Divide: Kairo vs. Google Magic Pointer

Google's **Magic Pointer** sends *every single screen interaction* to cloud-based servers. For legal, healthcare, finance, and highly regulated industries, this architectural design is a critical compliance blocker.

**Kairo Phantom** is engineered for absolute privacy:
- **100% Local Execution**: All parser VLMs, model routing, and embedding operations execute entirely on your machine.
- **Air-Gapped by Design**: Works flawlessly with zero network connection. Your data never leaves your device.
- **MemMachine Style Memorization**: Remembers your formatting and style choices locally inside an encrypted SQLite database without sending them to the cloud.

---

## 🚀 Install

**Recommended — any platform:**
```bash
cargo install kairo-phantom
kairo first-run
```

**Windows one-click installer (no Rust required):**
```powershell
# Downloads, installs Ollama, pulls model, starts daemon — all in <90 seconds
irm https://raw.githubusercontent.com/Kartik24Hulmukh/Kairo-Phantom/master/install.ps1 | iex
```
Or download **[KairoSetup.exe](installer/Output/KairoSetup.exe)** directly.

**macOS:**
```bash
brew install kairo-phantom   # coming soon
# Until then: cargo install kairo-phantom
```

**Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/Kartik24Hulmukh/Kairo-Phantom/master/install.sh | bash
```

> ⏱️ **60-second quickstart:** [docs/QUICKSTART.md](docs/QUICKSTART.md)

---

## 💡 What Makes Kairo Different

| Capability | Grammarly | Google Magic Pointer | Copilot | **Kairo Phantom** |
| :--- | :---: | :---: | :---: | :---: |
| **Works in ANY Windows App** | ❌ | ❌ (Googlebook only) | ❌ (IDE/App-specific) | **✅ OS-Level Hook** |
| **100% Offline / Local** | ❌ | ❌ (Gemini Cloud) | ⚠️ Optional | **✅ Air-gapped SOTA** |
| **Learns Your Style** | ⚠️ Basic | ❌ | ⚠️ Repo-scoped | **✅ MemMachine Database** |
| **Full Document Structure** | ❌ | ❌ (VLM Screen Only) | ❌ | **✅ OOXML AST-Level** |
| **Swarm Routing Swarm** | ❌ | ❌ | ❌ | **✅ 8 Specialist Agents** |

---

## 🛠️ Key Commands

| Command | Action |
| :--- | :--- |
| `Alt+M` | Trigger Kairo overlay / ghost-writing contextually |
| `kairo seed <folder>` | Process a folder of existing documents to seed local style |
| `kairo owasp-report` | Generate a signed OWASP Security Audit matrix |
| `kairo export-memory` | Backup your MemMachine learning profile to an encrypted `.kpx` file |
| `kairo import <file.kpx>`| Restore a style profile on a fresh local device |

---

## 🧠 MemMachine Demo

Kairo includes a deterministic memory simulator demonstrating cross-session learning. Run the following command locally to see Session-1 seeding and Session-2 semantic recall:

```powershell
python scripts/mem_demo.py
```

---

## 🏗️ Technical Architecture

```
phantom-core/src/
├── main.rs               # Orchestration hub and named pipe IPC
├── memory/mem_machine.rs  # MemMachine — semantic memory (Model2Vec + SQLite)
├── swarm/                # 8 specialized Multi-Agent swarms
├── document_context.rs   # OOXML AST parser and 3-Tier PDF Router
├── injector.rs           # OS-level ghost-writing injection (SendInput)
├── hotkey.rs             # Low-level Windows global keyboard hook
└── compliance_scanner.rs  # HIPAA, GDPR, and custom corporate guardrails
```

---

*"Kairo doesn't replace your voice. It makes your first draft indistinguishable from your tenth."*

---

## 🏢 Enterprise & Trust

Kairo Phantom is built for regulated environments. Every component is designed to satisfy enterprise security and compliance requirements:

| Document | Description |
| :--- | :--- |
| [SOC 2 Readiness](docs/enterprise/SOC2_READINESS.md) | Trust Service Criteria mapping (CC6, CC7, CC8, CC9, A1, C1) |
| [KMB-1 Benchmark](docs/benchmark/KMB1_RESULTS.md) | Memory quality benchmark: **0.9872 / 1.0** (+57.7% over baseline) |
| [KMB-1 Blog Post](docs/benchmark/KMB1_BLOG_POST.md) | Full methodology + reproduction guide (`cargo bench --bench memory_benchmark`) |
| [OWASP Compliance](docs/security/OWASP_AGENTIC_TOP10_COMPLIANCE.md) | OWASP Agentic AI Top 10 — 10/10 controls |
| [Security Audit](docs/security/SECURITY_AUDIT.md) | Decepticon security audit report — clean bill of health |
| [Memory Deep Dive](docs/memory/MEMORY_SYSTEM_DEEP_DIVE.md) | Technical walkthrough of MemMachine, embeddings, and privacy architecture |
| [Premortem Tracker](docs/PREMORTEM_TRACKER.md) | Weekly failure-mode re-evaluation (all 10 risks tracked) |

### Security Architecture (Phase 1 Hardened)
- **`//` Protocol Gate** — every Alt+M triggers `PromptParser::parse()`. No `//` → silent abort, zero LLM calls
- **Sentinel Sanitizer** — per-session UUID injected into every system prompt; any leakage triggers automatic retry (max 2×) then audit-logged block
- **Prompt Injection Firewall** — 50 detectors across 6 layers (`prompt_injection_firewall.rs`)
- **SHA-256 Audit Chain** — every ghost-write session is recorded in a tamper-evident chain (`enterprise/audit.db`)
- **SPIFFE Identity** — Ed25519 keypair per agent instance; verifiable via `kairo agent identity show`

### Enterprise Commands

```bash
kairo audit-verify          # Verify SHA-256 audit chain integrity
kairo owasp-report          # Generate OWASP compliance matrix
kairo siem-export --format cef  # Export to Splunk/QRadar/Sentinel
kairo agent identity show   # Display SPIFFE agent identity
kairo rbac-check            # Validate RBAC policy
```

---

## 🧩 Waza Skills Marketplace

Install specialist writing agents with one command:

```bash
# Install from the seed registry
kairo skill add https://github.com/Kartik24Hulmukh/Kairo-Phantom/raw/main/skills/legal-review/manifest.toml
kairo skill add https://github.com/Kartik24Hulmukh/Kairo-Phantom/raw/main/skills/medical-scribe/manifest.toml
kairo skill add https://github.com/Kartik24Hulmukh/Kairo-Phantom/raw/main/skills/code-reviewer/manifest.toml
kairo skill add https://github.com/Kartik24Hulmukh/Kairo-Phantom/raw/main/skills/academic-editor/manifest.toml
kairo skill add https://github.com/Kartik24Hulmukh/Kairo-Phantom/raw/main/skills/marketing-copywriter/manifest.toml

# List installed skills
kairo skill list

# Build your own (scaffolds manifest.toml + SKILL.md)
kairo skill new my-skill
```

| Skill | Category | What It Does |
| :--- | :--- | :--- |
| [legal-review](skills/legal-review/) | Legal | Contract risk analysis with GDPR/liability flagging |
| [medical-scribe](skills/medical-scribe/) | Medical | Clinical note → SOAP format with ICD-10 suggestions |
| [code-reviewer](skills/code-reviewer/) | Developer | Security, bugs, performance review for Rust/Python/TS/Go |
| [academic-editor](skills/academic-editor/) | Academic | Passive voice, argument clarity, citation format |
| [marketing-copywriter](skills/marketing-copywriter/) | Marketing | AIDA/PAS copywriting, headlines, email subjects |

---

## 🎬 Launch

- [90-Second Demo Video Script](docs/launch/VIDEO_SCRIPT.md)
- [Show HN + Reddit Launch Kit](docs/launch/LAUNCH_KIT.md) — posts for r/rust, r/programming, r/LocalLLaMA, r/selfhosted
- [Waza Agent Builder Tutorial](docs/launch/WAZA_TUTORIAL.md) — build your first custom agent in 10 minutes
- [Quickstart Guide](docs/QUICKSTART.md) — 60-second path to your first ghost-write
- [Premortem Tracker](docs/PREMORTEM_TRACKER.md) — weekly risk monitoring

---

*"Kairo doesn't replace your voice. It makes your first draft indistinguishable from your tenth."*
