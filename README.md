# 👻 Kairo Phantom

**The AI ghost-writer that haunts every desktop app.**  
Word, Excel, PowerPoint, terminals, browsers — press `Alt+M` and it writes.

[![Tests](https://img.shields.io/badge/tests-174%20passing-brightgreen)](phantom-core/tests/)
[![KMB-1](https://img.shields.io/badge/KMB--1-0.9872-blue)](phantom-core/tests/kmb1_benchmark.rs)
[![OWASP](https://img.shields.io/badge/OWASP%20Agentic%20Top%2010-10%2F10-green)](KAIRO_OWASP_COMPLIANCE.md)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Offline](https://img.shields.io/badge/offline-100%25%20local-orange)](phantom-core/src/ai.rs)

---

## Install in 60 seconds

```powershell
# Windows — one command
irm https://raw.githubusercontent.com/Kartik24Hulmukh/Kairo-Phantom/master/install.ps1 | iex
```

Or download **[KairoSetup.exe](installer/Output/KairoSetup.exe)** (no Rust required).

**That's it.** Kairo starts in your system tray. Press `Alt+M` in any app.

---

## What makes Kairo different

| Capability | Grammarly | Copilot | ChatGPT Desktop | Kairo Phantom |
|------------|-----------|---------|-----------------|---------------|
| Works in ANY desktop app | ❌ Browser only | ❌ IDE only | ⚠️ Limited | ✅ **OS-level** |
| 100% offline / local | ❌ | ⚠️ Opt-in | ❌ | ✅ **Air-gapped** |
| Learns your style permanently | ⚠️ Basic | ⚠️ Repo-scoped | ❌ Per-session | ✅ **MemMachine** |
| Full document structure (OOXML) | ❌ | ❌ | ❌ | ✅ **AST-level** |
| Enterprise governance (OWASP) | ✅ SOC2 | ✅ | ❌ | ✅ **10/10 controls** |
| Multi-agent swarm routing | ❌ | ❌ | ❌ | ✅ **8 specialists** |

**KMB-1 score: 0.9872** (industry-first memory benchmark — [see methodology](phantom-core/tests/kmb1_benchmark.rs))

---

## How it works

```
You press Alt+M
    → Kairo reads document structure (UIA + OOXML AST)
    → Recalls your style from MemMachine (learned from 174 past interactions)
    → Routes to the right specialist agent (Design / Engineering / Legal / ...)
    → Multi-agent swarm drafts + reviews + revises
    → Ghost-types the result directly into your app
    → Learns from your edits for next time
    
Zero clipboard. Zero network. Zero context switching.
```

---

## Key commands

| Command | What it does |
|---------|-------------|
| `Alt+M` | Activate in any app |
| `kairo seed <folder>` | Teach Kairo your style from existing docs |
| `kairo owasp-report` | Generate OWASP compliance matrix PDF |
| `kairo export-memory` | Export your MemMachine as `.kpx` |
| `kairo import <file.kpx>` | Import memory on a new machine |
| `kairo --version` | Show version |

---

## Enterprise features

- **OWASP Agentic Top 10** — 10/10 controls covered (`kairo owasp-report`)
- **RBAC + Audit Logs** — cryptographically signed session logs
- **Compliance Scanner** — HIPAA/GDPR/custom rules (`~/.kairo-phantom/compliance/`)
- **Memory Portability** — `.kpx` export for team onboarding
- **Skills Marketplace** — domain-specific agent packs (Legal, Medical, Finance)
- **AD/LDAP Integration** — map Active Directory groups to skill scopes

---

## Build from source

```powershell
git clone https://github.com/Kartik24Hulmukh/Kairo-Phantom
cd Kairo-Phantom\phantom-core
cargo build --release
.\target\release\kairo-phantom.exe
```

**Requirements:** Rust 1.78+, Windows 10 1803+  
**Optional:** [Ollama](https://ollama.com) for local AI (auto-detected on startup)

---

## Architecture

```
phantom-core/src/
├── main.rs              # Orchestration hub
├── memory/mem_machine.rs # MemMachine — semantic memory (ONNX + SQLite)
├── swarm/               # 8 specialist agents
├── document_context.rs  # OOXML AST parser (97+ formats)
├── injector.rs          # OS-level ghost-typing (SendInput)
├── hotkey.rs            # WH_KEYBOARD_LL keyboard hook
├── sentinel.rs          # Prompt injection protection
├── governance/          # Tool gate + audit logs
├── wasm_sandbox.rs      # Wasmtime plugin isolation
├── health_check.rs      # Document health analysis
├── compliance_scanner.rs # HIPAA/GDPR compliance scanning
└── owasp_compliance.rs  # OWASP matrix generator
```

---

*"Kairo doesn't replace you. It makes your first draft indistinguishable from your tenth."*
