# Project: Kairo Phantom GA Hardening — KairoReal Gauntlet Rebuild

## Architecture
Kairo Phantom is a local-first AI copilot consisting of:
- `phantom-core` (Rust daemon): Core named-pipe orchestrator, input hook/injector, memory system, response validator, and identity/audit chain manager.
- `kairo-sidecar` (Python backend): Model router, specialists, docx/xlsx/pptx/pdf creators, and verifiers/oracles.
Rebuilding the KairoReal Gauntlet requires a headless runner that executes 200 distinct scenarios across 10 domains and validates them programmatically using falsifiable oracles.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | De-Rig CI Workflows & Production Gate (Phase P0 & P1) | Update CI readiness checks, assert gauntlet pass rate, rename e2e_chaos_gauntlet, fix PDF test skips. | None | DONE |
| 2 | Rebuild the Headless Gauntlet (Phase P2) | Rebuild scenarios.json and run_kairoreal_gauntlet.py with 200 scenarios across 14 domains. | M1 | DONE |
| 3 | Gate Production-Path Mocks (Phase P3) | Disable/gate production-path mocks behind explicit env flags. | M2 | DONE |
| 4 | Expand Coverage & Mutation Testing (Phase P4) | Increase coverage to >= 80%, expand mutation testing scope. | M3 | DONE |
| 5 | Verification & Integrity Audit (Headless) | Run integrity checks, no_skip_gates, and ensure gauntlet 100% pass. | M4 | DONE |

## Interface Contracts
### Gauntlet Executor ↔ Oracles
- Executors run real sidecar code on the scenario inputs.
- Oracles verify specific structure and content against expected outcomes (e.g. specific paragraphs/formulas/cells/slides/clauses/errors).
- Oracles must fail when given incorrect/empty inputs.

## Code Layout
- `scenarios.json`: 200 real-world scenarios across 10 domains.
- `scripts/run_kairoreal_gauntlet.py`: Headless gauntlet execution runner.
- `kairo-sidecar/tests/test_kairoreal_gauntlet.py`: Test suite for the gauntlet runner.
- `.github/workflows/ci.yml`: CI/CD configuration.

