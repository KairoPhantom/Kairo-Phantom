# Kairo Phantom v2.2 — Master Go/No-Go Ledger

> Source of truth: `KAIRO_PHANTOM_V22_SHIP_PLAN.md` Part 8. Ship ONLY when ALL rows GREEN on a clean checkout, twice, with receipts.
> Every number below comes from a live command + saved receipt in `/receipts/`. Anti-bluff: no tuning to the eval/blind set.

## Legend
- 🟢 GREEN — measured ≥ gate, receipt on disk
- 🔴 RED — measured < gate, or not yet measured
- 🟡 INFRA-PENDING — code/config delivered; blocked on a real secret/infra (exact missing item listed)

## Baseline receipts (clean checkout, branch `ship/v2.2-ledger-init`)
| Receipt | Command | Key numbers |
|---|---|---|
| `receipts/bench_baseline.txt` | `make bench` (dev/golden) | grounded 100% / refusal 100% / false-ref 0% / ungrounded 0 |
| `receipts/blind_baseline.txt` | blind scorer on `fixtures/blind_holdout` (11 docs) | **grounded 67.5% / false-ref 32.5% / refusal-correct 100% / ungrounded 0** |
| `receipts/safety_baseline.txt` | `make safety` | air-gap PASS / injection 25/25 / ingestor PASS / gate-bypass PASS |
| `receipts/release_check_baseline.txt` | `make release-check` | held_out(3 docs) 100% — **NOT the blind set** |

---

## PART 8 — Go/No-Go Ledger

### Grounding & eval
| # | Gate | Target | Measured | Status | Receipt | Branch |
|---|---|---|---|---|---|---|
| G1 | Grounded-answer rate (golden) | ≥95% | 100.0% | 🟢 GREEN | `receipts/bench_baseline.txt` | master |
| G2 | Grounded-answer rate (blind) | ≥95% | 96.1% | 🟢 GREEN | `receipts/blind_bench_GREEN.txt` | ship/t2-grounding-cascade |
| G3 | Refusal-on-unanswerable | =100% | 100.0% | 🟢 GREEN | `receipts/blind_baseline.txt` | master |
| G4 | False-refusal rate (near-miss/blind) | <5% | 3.9% | 🟢 GREEN | `receipts/blind_bench_GREEN.txt` | ship/t2-grounding-cascade |
| G5 | Hallucinated-bbox blocked | =100% | 100% (0 ungrounded renders) | 🟢 GREEN | `receipts/blind_baseline.txt` | master |
| G6 | Zero ungrounded renders (overlay fuzz + injection) | =0 | 0 (pipeline); overlay fuzz not yet run | 🔴 RED (partial) | — | — |

### Evidence
| # | Gate | Target | Measured | Status | Receipt | Branch |
|---|---|---|---|---|---|---|
| E1 | Blind corpus frozen + labeled (spec §3 layout) | `bench/corpus/blind/v1/` committed | 11 docs, manifest + checksums (23/23 verified) | 🟢 GREEN | `receipts/blind_bench_GREEN.txt` | ship/t1-blind-corpus-scorer |
| E2 | Shared scorer `bench/score.py` (spec §5) | exists, unit-tested | `bench/score.py` self-test PASS | 🟢 GREEN | `receipts/blind_bench_GREEN.txt` | ship/t1-blind-corpus-scorer |
| E3 | dev-vs-blind columns published (`BENCHMARKS.md`) | per-pack dev+blind | not present | 🔴 RED | — | — |
| E4 | `FAILURE_TAXONOMY.md` published | honest, from blind | not present | 🔴 RED | — | — |
| E5 | `MODEL_CARDS.md` + `HARDWARE.md` published | worker/reasoner/VRAM | not present | 🔴 RED | — | — |
| E6 | `bench/history.jsonl` per-commit | exists | `bench/history/` dir exists (per-run json) | 🟡 partial | — | master |
| E7 | Public leaderboard reproducible via `make bench` | reproduces on stranger machine | `make bench` reproducible (golden only) | 🔴 RED (blind not wired) | — | — |

### Security
| # | Gate | Target | Measured | Status | Receipt | Branch |
|---|---|---|---|---|---|---|
| S1 | Injection corpus 100% blocked | =100% | 100% (25/25) | 🟢 GREEN | `receipts/safety_baseline.txt` | master |
| S2 | RAGShield poisoning neutralized | neutralized | not tested | 🔴 RED | — | — |
| S3 | Secrets keychain-only; logs redacted | clean scan | not tested | 🔴 RED | — | — |
| S4 | `NETWORK_AUDIT.md` + air-gap zero-traffic | pcap + zero traffic | air-gap egress PASS; pcap not produced | 🟡 partial | `receipts/safety_baseline.txt` | master |
| S5 | `make domains-check` (license) green | green | GREEN (via `make build`) | 🟢 GREEN | `receipts/bench_baseline.txt` | master |

### Perf & packaging
| # | Gate | Target | Measured | Status | Receipt | Branch |
|---|---|---|---|---|---|---|
| P1 | cold-start | <2s | not measured | 🔴 RED | — | — |
| P2 | click-to-source | <100ms | not measured | 🔴 RED | — | — |
| P3 | native-PDF parse | ≥20 pg/s | not measured | 🔴 RED | — | — |
| P4 | worker RSS | <4GB | not measured | 🔴 RED | — | — |
| P5 | Signed installers build (or INFRA-PENDING) | builds or labeled | not built | 🔴 RED (likely INFRA-PENDING: signing certs) | — | — |
| P6 | Migration upgrade test | passes | not tested | 🔴 RED | — | — |

### Launch
| # | Gate | Target | Measured | Status | Receipt | Branch |
|---|---|---|---|---|---|---|
| L1 | Refusal-hero demo recorded (≤90s) | recorded | not recorded | 🔴 RED | — | — |
| L2 | Show HN post pre-empts 3 killer comments | written | not written | 🔴 RED | — | — |
| L3 | Leaderboard live | live | not live | 🔴 RED | — | — |
| L4 | Legacy metrics quarantined to `/legacy` | done | `/legacy` exists; audit of public artifacts pending | 🟡 partial | — | master |

---

## Backlog execution order (Parts 2→7)
1. **T1 — Blind corpus + shared scorer (E1, E2):** build `bench/corpus/blind/v1/` per spec §3 + `bench/score.py` per spec §5. Wire `make bench` to emit dev+blind columns.
2. **T2 — Grounding cascade + pack extractors (G2, G4):** close 67.5%→95% blind gap. Broaden pack regex for real-world formats (multilingual labels, currency detection, "by and between" parties). Add fuzzy/semantic cascade steps. **Tune ONLY on dev split.**
3. **T3 — Hallucinated-bbox + overlay fuzz (G6):** overlay fuzz test + adversarial bbox corpus.
4. **T4 — Security hardening (S2, S3, S4):** RAGShield poisoning corpus, secret-scan, NETWORK_AUDIT.md pcap.
5. **T5 — Perf budget (P1–P4):** `make perf` target measuring cold-start/click-to-source/parse/RSS.
6. **T6 — Packaging (P5, P6):** installer build path (INFRA-PENDING signing) + migration test.
7. **T7 — Evidence artifacts (E3, E4, E5, E6, E7):** BENCHMARKS.md, FAILURE_TAXONOMY.md, MODEL_CARDS.md, HARDWARE.md, leaderboard.
8. **T8 — Launch artifacts (L1–L4):** demo, Show HN, leaderboard live, legacy quarantine audit.

---

## Clean-checkout double-green (final)
- [ ] Run 1: all gates green on fresh clone + `make build` — receipts in `/receipts/final_run1/`
- [ ] Run 2: all gates green on fresh clone + `make build` — receipts in `/receipts/final_run2/`