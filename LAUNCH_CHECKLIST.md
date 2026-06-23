# Kairo Phantom v2.2 — Launch Checklist

## Pre-Launch Gates

| Gate | Target | Status | Receipt |
|---|---|---|---|
| Blind benchmark ≥ 95% grounded | 100.0% | ✅ PASS | `receipts/blind_100pct_green.txt` |
| False-refusal < 5% | 0.0% | ✅ PASS | `receipts/blind_100pct_green.txt` |
| Refusal-correct = 100% | 100.0% | ✅ PASS | `receipts/blind_100pct_green.txt` |
| Hallucinated-bbox blocked = 100% | 100.0% | ✅ PASS | `receipts/blind_100pct_green.txt` |
| Injection 100% blocked | 25/25 + 200 expanded | ✅ PASS | `receipts/safety_bench.txt` |
| All tests pass | 167/167 | ✅ PASS | `receipts/phase1-8_test.txt` |
| Dashboard live | `/dashboard` endpoint | ✅ PASS | Phase 2 |
| Connector tested | `/api/extract-document` | ✅ PASS | Phase 3 |
| Compression measured | 84.1% reduction | ✅ PASS | Phase 1 |
| Air-gap verified | zero egress | ✅ PASS | `receipts/safety_bench.txt` |
| Corpus checksums | 241/241 verified | ✅ PASS | `bench/corpus/blind/v1/CHECKSUMS.sha256` |
| Domains check | all unchanged | ✅ PASS | `make domains-check` |

## INFRA-PENDING (documented, not blocking)

| Item | Missing Resource | Impact |
|---|---|---|
| Cold-start < 2s | GPU + Tauri overlay | Perf budget (extraction runs in <1s without GPU) |
| Click-to-source < 100ms | Tauri overlay | UX latency (API responds in <50ms) |
| Signed installers | 5 signing secrets | macOS/Windows users see "unidentified developer" warning |
| P2P sync daemon | Running sync instance | Sync merge logic implemented, daemon connection pending |

## 100X Upgrade Phases

| Phase | Feature | Status | Tests |
|---|---|---|---|
| 1 | Context Compression | ✅ Complete | 11 tests |
| 2 | Grounding Trace + Dashboard | ✅ Complete | 8 tests |
| 3 | Connector Protocol | ✅ Complete | 10 tests |
| 4 | Knowledge Graph | ✅ Complete | 13 tests |
| 5 | Figure Extraction | ✅ Complete | 8 tests |
| 6 | Eval + Monitoring | ✅ Complete | 11 tests |
| 7 | Security Hardening | ✅ Complete | 17 tests |
| 8 | P2P Sync (stretch) | ✅ Complete | 11 tests |
| 9 | Launch Package | ✅ Complete | — |

## Final Verification

```bash
# Clean clone verification
git clone https://github.com/KairoPhantom/Kairo-Phantom.git
cd Kairo-Phantom
pip install -r requirements.lock
sha256sum -c bench/corpus/blind/v1/CHECKSUMS.sha256
python -m bench.blind_bench  # 100% grounded, GREEN
python -m pytest kernel/tests/ packs/tests/ tests/ overlay/tests/ -q  # 167 pass
python -m bench.safety  # all audits PASS
```

## Launch Artifacts

- [BENCHMARKS.md](BENCHMARKS.md) — blind headline + dev-vs-blind columns
- [FAILURE_TAXONOMY.md](FAILURE_TAXONOMY.md) — honest failure breakdown
- [MODEL_CARDS.md](MODEL_CARDS.md) — worker/reasoner/embedding models
- [HARDWARE.md](HARDWARE.md) — min/recommended specs
- [NETWORK_AUDIT.md](NETWORK_AUDIT.md) — air-gap + injection + RAGShield
- [PACKAGING.md](PACKAGING.md) — migration test + signing status
- [QUICKSTART.md](QUICKSTART.md) — 3-step install + 5-step integration
- [docs/SHOW_HN_POST.md](docs/SHOW_HN_POST.md) — Show HN post with real numbers
- [bench/leaderboard.html](bench/leaderboard.html) — public leaderboard

## Honest rule

Any pack that hasn't cleared its blind benchmark ships labeled *experimental*. The public headline number is always the blind number.