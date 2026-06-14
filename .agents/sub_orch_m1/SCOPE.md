# Scope: Calibration & Trust (Milestone 1)

## Architecture
- Unification of confidence calculations under `memory::feedback::ConfidenceEngine` and removal of `confidence.rs`.
- Configurable `relevance_floor` and `clarity_threshold` added to settings/config.
- `ResponseValidator` promoted to a hard block in `main.rs` triggering regeneration.
- Response validation against a plain-English user-editable constitution in `response_validator.rs`.
- Cryptographically signed execution trails (`AuditChainEntry` with signature field using `AgentIdentity`).
- E2E CI job post-processing to generate `task_completion_rate.json`.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Implementation & Testing | Code implementation and unit/integration verification for all R1 items. | None | IN_PROGRESS (Subagents: f18d7c7f-c213-416d-834f-e6b558bd1316, 0e29c27e-cc0a-4dfe-92ce-d80425ae51ee, 7b4da01b-65a6-4072-9b2d-e9c64b87ee4a) |

## Interface Contracts
- `ResponseValidator::validate` returns `ValidationResult::Failed` if below relevance floor or violating the constitution.
- `main.rs` retries generation inside the retry loop on validation failures.
- `AuditChainEntry` includes `signature: String` field.
