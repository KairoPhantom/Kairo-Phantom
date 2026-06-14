# Project: Kairo Phantom GA Hardening — KairoReal Gauntlet Rebuild

## Architecture
Kairo Phantom is a local-first AI copilot consisting of:
- `phantom-core` (Rust daemon): Core named-pipe orchestrator, input hook/injector, memory system, response validator, and identity/audit chain manager.
- `kairo-sidecar` (Python backend): Model router, specialists, docx/xlsx/pptx/pdf creators, and verifiers/oracles.
Rebuilding the KairoReal Gauntlet requires a headless runner that executes 200 distinct scenarios across 10 domains and validates them programmatically using falsifiable oracles.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Scenarios Rebuilding | Replace scenarios.json with 200 distinct real-world scenarios across 10 domains, all active | None | IN_PROGRESS |
| 2 | Executors & Oracles | Update run_kairoreal_gauntlet.py to use actual sidecar APIs and falsifiable oracles | M1 | PLANNED |
| 3 | Pytest Integration | Rebuild kairo-sidecar/tests/test_kairoreal_gauntlet.py to verify runner behavior | M2 | PLANNED |
| 4 | CI Workflow Update | Add kairoreal-gauntlet job to ci.yml and gate the production-gate job on pass rate | M3 | PLANNED |
| 5 | Validation & Verification | Execute full gauntlet, verify 100% pass/skip correctness, run reviews/audits | M4 | PLANNED |

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

