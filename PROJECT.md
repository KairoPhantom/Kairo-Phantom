# Project: Kairo Phantom GA Hardening

## Architecture
Kairo Phantom is a local-first AI copilot consisting of:
- `phantom-core` (Rust daemon): Core named-pipe orchestrator, input hook/injector, memory system, response validator, and identity/audit chain manager.
- `kairo-sidecar` (Python backend): Model router, specialists, docx/xlsx/pptx/pdf creators, and verifiers/oracles.
GA Hardening integrates robust calibration (uncertainty thresholds, responses constitution validation), cryptographic audit trail signing, signed updates verification, adaptive compute, production observability/telemetry, crash reporting, security gates, and autonomous gauntlet infrastructure.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Calibration & Trust (Sprint 4) | Confidence Unification, E2E Measurement CI Job, Response Validator Hard Block, Calibrated Uncertainty, Document Constitution, Verifiable-Work Receipts | None | DONE |
| 2 | Hardening & Release Readiness (Sprint 5) | Signed Updates, Remove pro.rs Stub, Thin Domain Capabilities, Best-of-N Oracle Selection, Adaptive Compute | M1 | IN_PROGRESS |
| 3 | Production-Ops & Autonomous Gauntlet (Sprint 5.5 - 7) | Auto-Update Rollback, Crash Reporting, Observability, SBOM/cargo-audit/Gitleaks Gates, Sandbox & Parallel Runner, Test-Fix-Test Loop, No-Skip Gates, Verified Outcome Store, Synthetic Personas, Drift Alarm | M2 | PLANNED |

## Interface Contracts
### Response Validator ↔ Core Retry Loop
- `ResponseValidator::validate` checks output against `relevance_floor` and `constitution.txt`.
- On failure, returns `ValidationResult::Failed`. Core `'retry` loop catches this and triggers up to N regenerations before returning an error.
- Configurable thresholds loaded from `KairoConfig`.

### Cryptographic Audit Chain
- `AuditChainEntry` has `signature: String`.
- Signature is generated using `AgentIdentity::sign` on serialization of the rest of the entry.

### Updater ↔ Releases
- `updater.py` checks releases, verifies packages against SHA-256, and checks Ed25519 signature against trusted public key.

## Code Layout
- `phantom-core/src/`: Core Rust source code.
- `kairo-sidecar/sidecar/`: Python sidecar services.
- `kairo-sidecar/tests/`: Sidecar unit and integration tests.
