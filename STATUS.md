# Kairo Phantom — Production Readiness STATUS.md

**Last updated:** 2026-06-21

## Summary

Kairo Phantom is a local-first, verifiable document-intelligence tool. Core promise: "No source → no answer." This file tracks every prompt from the Pre-Launch & Production-Hardening Prompt Pack and its implementation status.

## Current Baseline (verified)

| Check | State | Evidence |
|:---|:---:|:---|
| Python kernel imports | PASS | `import kernel; import packs; import bench` OK |
| 45 unit/integration tests | PASS | `pytest kernel/tests/ packs/tests/` → 45 passed |
| `make bench` runs | PASS | `bench/harness.py` produces REPORT.json/md |
| `make safety` runs | PASS | Air-gap, injection (25/25), ingestor fuzz, gate-bypass all PASS |
| `make acceptance` runs | PASS | ACCEPTANCE.md generated |
| Grounding cascade | PASS | exact→fuzzy→semantic→block in `kernel/core/grounding.py` |
| 4 Packs | PASS | generic/invoice/paper/contract with fixtures |
| Provenance chain | PASS | Action→Extraction→Chunk→Document in `kernel/core/provenance.py` |

## Prompt Status Ledger

| ID | Prompt | State | Evidence | Agent |
|:---|:---|:---:|:---|:---|
| Ctx | Context Primer | PASS | Loaded into working memory | — |
| P0.1 | Runnable artifact + quickstart | PASS | `pytest tests/test_runnable_artifact.py tests/test_cold_install.py` → 48 passed; `make run DOC=samples/invoice/sample_invoice_01.txt Q="What is the invoice number?"` → grounded answer with page+bbox; `make samples` → grounded + refusal demo; `python3 scripts/first_run.py` → first-run flow works; README quickstart updated with copy-paste OS instructions; `docker/Dockerfile` created | Agent-A |
| P0.2 | Real `make bench` with 4 gates | PASS | `make bench` prints 4 gates (grounded=83.13%, refusal=100%, false-refusal=16.87%, ungrounded=0); `pytest tests/test_bench_determinism.py tests/test_bench_gates.py tests/test_bench_corpus_hash.py` → 22 passed; corpus hash `8101742f91ae4b38...` deterministic across runs; failing-capable verified (renaming gate key → test RED) | Agent-B |
| P1.1 | Hardware matrix + degradation | PASS | `pytest tests/test_hardware_check.py` → 23/23 passed; `scripts/hardware_check.py` CLI detects GPU/VRAM/RAM, reports tier, blocks OOM with precise message | Agent-D |
| P1.2 | Threat model + air-gap proof | PASS | `pytest tests/test_airgap_zero_egress.py tests/test_keychain_storage.py` → 26/26 passed; `scripts/airgap_proof.py` asserts zero egress via real socket monkey-patching; `THREAT_MODEL.md` published | Agent-D |
| P1.3 | Standalone verifier crate + ablation | PASS | `python3 -m pytest tests/test_verifier_standalone.py tests/test_ablation.py tests/test_visual_stage.py -v` → 49 passed; `make ablation` → verifier-active 0.00% ungrounded vs bypassed 48.57%; failing-capable proven (IoU threshold→0.0 breaks 2 tests); standalone module imports zero model clients | Agent-C |
| P2.1 | GUI installer + overlay | PASS | `pytest tests/test_installer_smoke.py tests/test_refusal_ui.py` → 31 passed; docs/INSTALLER_GUIDE.md, docs/GUI_SPEC.md, docs/ONBOARDING_WIZARD.md created | Agent-G |
| P2.2 | Pack-specific benchmarks | PASS | `pytest tests/test_pack_benchmarks.py` → 18 passed; bench/pack_benchmarks.py runs, docs/BENCHMARK_METHODOLOGY.md created, hard-case fixtures added | Agent-G |
| P2.3 | Replication kit | PASS | `pytest tests/test_replication.py` → 15 passed; scripts/replicate.py runs end-to-end, REPLICATE.md created | Agent-G |
| T1 | Cascade stage + transition tests | PASS | `pytest tests/test_cascade_stages.py` → 41 passed; failing-capable: breaking EXACT stage turns 3 tests RED | Agent-E |
| T2 | False-refusal corpus + trust-collapse | PASS | `pytest tests/test_false_refusal.py tests/test_trust_collapse.py` → 15 passed; refusal-on-unanswerable=100%, false-refusal<5% | Agent-E |
| T3 | Ungrounded render prevention | PASS | `pytest tests/test_ungrounded_render.py tests/test_verifier_fuzz.py tests/test_verifier_no_bypass.py` → 37 passed; verifier rejects all adversarial outputs | Agent-E |
| T4 | Air-gap egress CI proof | PASS | `pytest tests/test_airgap_ci.py` → 7 passed; zero egress in air-gap, BYO-key egress only to configured endpoint | Agent-E |
| T5 | Adversarial document corpus | PASS | `pytest tests/test_adversarial_docs.py` → 23 passed; no injection alters refusal, no egress, no crash/hang; THREAT_MODEL.md residual risk appended | Agent-E |
| T6 | Cross-platform CI matrix | PASS | `.github/workflows/cross-platform.yml` with macOS-13/14, ubuntu, windows matrix; `scripts/dependency_audit.py` runs clean (0 CVEs, 14 unpinned warnings); no caching of cold-install deps | Agent-F |
| T7 | Determinism + overfitting guard | PASS | `tests/test_determinism.py` (3 tests), `tests/test_overfitting_guard.py` (3 tests), `tests/test_corpus_integrity.py` (4 tests), `tests/test_historical_tracking.py` (4 tests) — 14/14 pass; held-out fixtures in `fixtures/held_out/` | Agent-F |
| T8 | Refusal diagnostic UX | PASS | `kernel/core/refusal.py` with `format_refusal()`, `get_refusal_metadata()`, `log_refusal()`; `kernel/core/data_model.py` Answer has `refusal_stage`, `refusal_reason`, `refusal_suggestion`; `tests/test_refusal_diagnostic.py` 9/9 pass | Agent-F |
| T9 | Sidecar lifecycle robustness | PASS | `tests/test_sidecar_lifecycle.py` (6 tests), `tests/test_resource_bounds.py` (5 tests), `tests/test_ipc_robustness.py` (8 tests), `tests/test_concurrency.py` (5 tests) — 24/24 pass | Agent-F |
| T10 | `make release-check` automation | PASS | `scripts/release_check.py` asserts 4 gates + air-gap + verifier + trust-collapse; `make release-check` target added; `RELEASE_REPORT.md` generated with date+signature; `tests/test_release_check.py` 8/8 pass including planted regression test | Agent-F |
| A1 | Hero video shot list | PASS | docs/HERO_VIDEO_SHOT_LIST.md created with segment-by-segment table (0–90s) | Agent-G |
| A2 | Show HN post | PASS | docs/SHOW_HN_POST.md created with post body + 3 prepared replies | Agent-G |
| A3 | FAQ.md | PASS | FAQ.md created with 6 anti-bluff Q&A answers | Agent-G |
| A4 | Launch seeding plan | PASS | docs/LAUNCH_SEEDING_PLAN.md created with T-14 to T+3 checklist | Agent-G |
| X1 | Signed audit log (compliance) | PASS | `kernel/core/audit_log.py` + `audit_export.py` + `docs/COMPLIANCE_BRIEF.md`; 30 tests in `test_audit_log.py` all pass; tamper detection verified (modifying any field breaks HMAC-SHA256 chain) | Agent-H |
| X2 | Verifier crate public release | PASS | `docs/VERIFIER_CRATE_RELEASE.md` with 10-line integration example; 17 tests in `test_verifier_integration_example.py` all pass; grounds real citations, blocks hallucinations | Agent-H |
| X3 | Determinism guarantee + receipt | PASS | `kernel/core/reproducibility.py` with `ReproducibilityReceipt` + builder; 20 tests in `test_reproducibility.py` all pass; byte-identical receipts verified, different inputs produce different receipts | Agent-H |
| X4 | Golden corpus snapshot tests | PASS | `fixtures/golden_corpus/snapshots.json` with 14 golden cases (10 answers, 4 refusals) across 4 Packs; 14 tests in `test_golden_corpus.py` all pass; snapshots generated from real verifier runs | Agent-H |
| X5 | Adversarial corpus + submission flow | PASS | `red-team/` with 5 adversarial documents, README, CHANGELOG, submit_template; 22 tests in `test_red_team_corpus.py` all pass; grounding maintained, no egress, no behavior change | Agent-H |
| X6 | Scope discipline + CONTRIBUTING | PASS | Updated `CONTRIBUTING.md` with scope boundaries + help wanted; `CODEOWNERS` created; `docs/PUBLIC_ROADMAP.md` created; README scope section appended; 36 tests in `test_scope_discipline.py` all pass | Agent-H |

## Definition of Production-Ready Checklist

- [ ] 4 hard gates pass on real runs: grounded-answer ≥ 95% · refusal-on-unanswerable = 100% · false-refusal < 5% · zero ungrounded renders
- [ ] `make acceptance` green on Mac + Windows + Linux with zero skipped tests, planted regression turns it red
- [ ] Clean machine reaches grounded answer in < 5 minutes via documented path
- [ ] Air-gap mode emits zero network egress, proven by packet/syscall capture in CI
- [ ] Grounding verifier is standalone crate importing no model client; ablation shows leak with OFF, blocked with ON
- [ ] `make bench` numbers reproducible from clean checkout; held-out set reported next to dev; no bluff phrase survives grep
- [ ] Signed installers exist; overlay can never render unanchored value (fuzz + injection corpus green)