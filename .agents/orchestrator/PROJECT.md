# Project: Kairo Phantom

## Architecture
Kairo Phantom is a digital copilot structured as a three-layer agentic swarm architecture:
1. **Layer 1: Intent Gate** (Rust - `phantom-core/src/intent_gate.rs`) - Classifies request intent and filters compliance/security risks.
2. **Layer 2: Planning Engine / Swarm Routing** (Rust & Python - `phantom-core/src/swarm/` & `kairo-sidecar/sidecar/`) - Decomposes requests and orchestrates specialized domain masters.
3. **Layer 3: Streaming Injection** (Rust - `phantom-core/src/injector.rs`) - Streams characters to document interfaces using keystroke simulation.

It utilizes application-specific **Domain Masters** (under `kairo-sidecar/sidecar/masters/` and `sidecar/parsers/`) for format-preserving extraction and modification:
- Word (DOCX): Track changes, formatting.
- Excel (XLSX): Formula validation, context grids.
- PowerPoint (PPTX): Slide mapping, presentation layout.
- PDF: PyMuPDF / OpenDataLoader / olmOCR / Surya density routing.
- Collaborative Yjs: CRDT shared state sync.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Fix Word Master Performance Flake | Optimize sentence-length scan in `word_master.py` to sample first 50 paragraphs | None | DONE |
| 2 | Fix Tauri Headless Test Crash | Add `test = false` and `doctest = false` under `[lib]` in `phantom-overlay/src-tauri/Cargo.toml` | None | DONE |
| 3 | Full Verification & E2E Gauntlet | Run all Rust tests, Python tests, and the 39-scenario production gauntlet | M1, M2 | DONE |

## Interface Contracts
- **Tauri Overlay ↔ Core daemon**: Uses localhost:7437 IPC POST request to `/materialize`.
- **Sidecar ↔ Core daemon**: Python and Rust communicate via local TCP / HTTP channels to invoke domain masters.

## Code Layout
- `phantom-core/`: Rust daemon core.
- `phantom-overlay/src-tauri/`: Tauri frontend overlay backend.
- `kairo-sidecar/`: Python background services, parsers, and domain masters.
- `kairo-agent-sdk/`: SDK for writing integrations.
