# Kairo Phantom — Implementation Tasks

## P0 — Repo Scaffold + Contracts
- [x] Create `cli/` directory with `__init__.py` and `__main__.py`
- [x] Create 4 pack directories: `generic`, `invoice`, `paper`, `contract`
- [x] Create `scripts/ci/license_check.py`
- [x] Update Makefile with new targets
- [x] Quarantine wedge pack to `legacy/wedge/`
- [x] Gate: `make build` passes

## P1 — Ingestion + Provenance Store
- [x] Update ingestor with Docling fallback path
- [x] Add page image width_px/height_px recording
- [x] Ensure SQLite provenance is append-only
- [x] Create invoice/paper/contract/generic fixtures with ground_truth.json
- [x] Gate: indexing fixtures produces correct chunk count

## P2 — The Grounding Verifier (THE MOAT)
- [x] Create `kernel/core/grounding.py` with 5-step cascade
- [x] Add `GroundingMethod` enum + `Answer`/`Anchor` to data_model
- [x] Add `GroundingVerifier` protocol to contracts
- [x] Create `kernel/core/embeddings.py`
- [x] Wire grounding into orchestrator pipeline
- [x] Add `kernel/tests/test_grounding.py`
- [x] Gate: grounded-answer ≥95%, refusal = 100%

## P3 — The CLI Product
- [x] Implement `cli/main.py`: index, run, ask, correct
- [x] Gate: `kairo run` returns grounded JSON; unanswerable triggers refusal

## P4 — The 4 Launch Packs
- [x] Implement generic pack with LangExtract pattern
- [x] Implement invoice pack
- [x] Implement paper pack
- [x] Implement contract pack
- [x] Add tests for all 4 packs
- [x] Gate: each pack ≥95% grounded-answer rate on fixtures

## P5 — Public Grounding Benchmark
- [x] Refactor bench/harness.py for all 4 packs
- [x] Add FACTUM-style citation-hallucination scoring
- [x] Create HTML leaderboard generator
- [x] Gate: leaderboard reproduces on clean checkout

## P6 — Overlay (PENDING-REAL-APP interim)
- [x] Add click-to-source `/source/{id}` endpoint
- [x] Create glass UI HTML template with source chips
- [x] Gate: click highlights land correctly

## P7 — Web Demo (PENDING-REAL-APP)
- [x] Create web_demo_spec.md

## P8 — De-rigged README
- [x] Rewrite README with real metrics, no inflated claims
- [x] Update ACCEPTANCE.md with honest labels
- [x] Gate: no "100%/10/10/1000x" claims

## P9 — Release Gate + Acceptance
- [x] Wire acceptance to run all 5 hard gates
- [x] Update gauntlet for all 4 packs
- [x] Gate: `make acceptance` green
