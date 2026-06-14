# Project: Headless KairoReal Gauntlet Runner and CI Integration

## Architecture
- `scripts/run_kairoreal_gauntlet.py`: Headless gauntlet runner orchestrating 200 scenarios from `scenarios.json`.
- `kairo-sidecar/tests/test_kairoreal_gauntlet.py`: Pytest test suite for validating the runner scaffold.
- `.github/workflows/ci.yml`: CI workflow integration to run the gauntlet.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Investigation & Plan | Research how to call Masters, Legal, CUA, Security, Memory, Offline, Degradation, and Performance components. | none | DONE |
| 2 | Gauntlet Implementation | Write scripts/run_kairoreal_gauntlet.py executing all 200 scenarios. | M1 | DONE |
| 3 | Pytest Scaffold Test | Write kairo-sidecar/tests/test_kairoreal_gauntlet.py testing the runner. | M2 | DONE |
| 4 | CI Integration & Verification | Update ci.yml and verify that the gauntlet runs in CI correctly. | M3 | DONE |

## Interface Contracts
### Gauntlet Runner ↔ scenarios.json
- Input: JSON array from `scenarios.json` at repo root.
- Output: `task_completion_rate.json` in repo root.
- Exit code: 0 if pass_rate_active >= 80%, else 1.
