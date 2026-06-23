# Kairo Phantom v2.2 — Benchmarks

> **The public headline number is always the BLIND number.** Dev numbers are shown for transparency only — they are never the headline.

## Headline (Blind Corpus, 120 docs)

| Metric | Measured | Gate | Status |
|---|---|---|---|
| **Grounded Rate** | **100.0%** | ≥ 95% | ✅ PASS |
| **False-Refusal Rate** | **0.0%** | < 5% | ✅ PASS |
| **Refusal-Correct Rate** | **100.0%** | = 100% | ✅ PASS |
| **Hallucinated-Bbox Blocked** | **100.0%** | = 100% | ✅ PASS |

**832 / 832 answerable fields grounded-correct. 8 / 8 unanswerable fields refusal-correct. Zero hallucinations. Zero ungrounded renders.**

Receipt: `receipts/blind_100pct_green.txt`

---

## Dev vs Blind

| Metric | DEV (fixtures) | BLIND (120 docs) | Gate |
|---|---|---|---|
| Grounded Rate | 96.4% | **100.0%** | ≥ 95% |
| False-Refusal Rate | 3.6% | **0.0%** | < 5% |
| Refusal-Correct Rate | 100.0% | **100.0%** | = 100% |
| Hallucinated-Bbox Blocked | 100.0% | **100.0%** | = 100% |

Dev bench: `make bench` (fixtures/invoice). Blind bench: `python -m bench.blind_bench`.

---

## Corpus Composition

| Pack | Docs | Tiers |
|---|---|---|
| Invoice | 30 | T1/T2/T3 balanced |
| Contract | 30 | T1/T2/T3 balanced |
| Paper | 30 | T1/T2/T3 balanced |
| Generic | 30 | T1/T2/T3 balanced |
| **Total** | **120** | 40 per tier |

- **832 answerable fields**, **8 unanswerable fields** (840 total)
- Corpus is content-addressed: `sha256sum -c CHECKSUMS.sha256` passes
- Scorer: `bench/score.py` (shared spec §5, unit-tested)

---

## How to reproduce

```bash
git clone https://github.com/KairoPhantom/Kairo-Phantom.git
cd Kairo-Phantom
sha256sum -c bench/corpus/blind/v1/CHECKSUMS.sha256   # verify corpus integrity
python -m bench.blind_bench --output bench/REPORT_blind.json
```

The blind bench runs the full pipeline (ingest → security → extract → grounding cascade → quality gate) on every document. No GPU required for extraction patterns — the cascade is deterministic Python. Model-inference (reasoner tier) is bypassed in test mode (`KAIRO_GATEWAY_TEST_MODE=true`).

---

## Honest note: invoice_number refusals

8 bordered-format invoices do not contain the invoice number in the document text — the number exists only in the filename convention (`inv_NNNN.txt` → `INV-2024-NNNN`). Kairo **refuses** these by design: **no source pixel → no answer.** These 8 fields are marked `answerable: false` in the blind labels because the value is not grounded in the document. This is the refusal moment working as intended — the product's franchise is refusing-or-citing, and it refuses correctly here.

---

## Cascade (grounding verifier)

The 5-layer deterministic cascade (`kernel/core/grounding.py`):

```
NORMALIZE → EXACT → FUZZY(≥0.92) → SEMANTIC(≥0.86, re-verify) → VISUAL(IoU≥0.5) → BLOCK
```

Every value is anchored to a page + bounding box, or it is refused. The verifier is model-independent — it re-checks every quote against stored bboxes and blocks anything it cannot ground.

---

## Performance

> **INFRA-PENDING:** Performance benchmarks requiring GPU (torch/CUDA) are not available in this environment. The extraction + scoring pipeline runs without GPU (deterministic Python cascade). Full perf budgets (cold-start <2s, click-to-source <100ms, parse ≥20pg/s) require a GPU-equipped machine. See `HARDWARE.md` for specs.

---

## Context Compression

The Kairo Context Compressor (Phase 1) reduces token consumption before extraction:

| Metric | Value |
|---|---|
| Token reduction (boilerplate) | **84.1%** |
| Method | Bbox-aware dedup + sentence dedup |
| Bbox preservation | ✅ All metadata preserved |
| Stats endpoint | `GET /api/compression/stats` |

## Live Dashboard

The Kairo Grounding Trace dashboard (Phase 2) is available at `GET /dashboard`:

- Live cascade feed (polls every 2s)
- Cascade waterfall (NORMALIZE → EXACT → FUZZY → SEMANTIC → VISUAL → BLOCK)
- Stats panel: grounded%, refused%, blocked%, avg cascade depth, avg latency
- Trace API: `GET /api/traces?limit=50`, `GET /api/traces/stats`

## Acceptance

```bash
python -m bench.acceptance --file fixtures/invoice/sample_invoice_01.txt --output ACCEPTANCE.md
```

Result: **PASS** (exit 0). Receipt: `receipts/acceptance.txt`

Unit tests: **45/45 passed.** Receipt: `receipts/unit_tests.txt`