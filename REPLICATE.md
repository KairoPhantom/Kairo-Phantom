# Kairo Phantom — Replication Guide

> Step-by-step instructions for an outsider to reproduce the grounding benchmark from scratch on a clean machine.

## Prerequisites

- Python 3.10+ (no Rust toolchain required for benchmarking — the Python kernel is used)
- Git
- ~500MB disk space for fixtures + dependencies

## Step 1: Clone the Repository

```bash
git clone https://github.com/KairoPhantom/Kairo-Phantom.git
cd Kairo-Phantom
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

If no `requirements.txt` exists, the core dependencies are:
```bash
pip install pytest numpy
```

## Step 3: Run the Replication Harness (One Command)

```bash
python3 scripts/replicate.py
```

This single command will:
1. Load the public corpus from `fixtures/` (4 Packs: generic, invoice, paper, contract)
2. Run the full grounding pipeline: ingest → extract → ground → verify
3. Emit the same metric table that `make bench` produces
4. Write results to `bench/REPLICATE_REPORT.json` and `bench/REPLICATE_REPORT.md`

## Step 4: Compare Results

The harness prints a metric table to stdout and writes it to `bench/REPLICATE_REPORT.md`. Compare your output against the committed baseline in `bench/REPORT.md`.

### Expected Metrics (dev set)

| Pack | Grounded-Answer Rate | False-Refusal Rate | Refusal-Correctness | Citation-Hallucination |
|:---|:---|:---|:---|:---|
| generic | ≥ 95% | < 5% | 100% | 0% |
| invoice | ≥ 95% | < 5% | 100% | 0% |
| paper | ≥ 95% | < 5% | 100% | 0% |
| contract | ≥ 95% | < 5% | 100% | 0% |

Results should match within tolerance (±2% for rates). If they don't match, file an issue with your `REPLICATE_REPORT.json` attached.

## Step 5: Run the Pack-Specific Benchmarks (Optional)

For pack-specific hard cases (merged-cell invoices, cross-referenced contracts, figure-caption papers):

```bash
python3 bench/pack_benchmarks.py
```

This produces `bench/PACK_BENCHMARK_REPORT.json` with per-hard-case false-refusal rates.

## Held-Out Private Set

A held-out private evaluation set is evaluated **only at release time** and is not included in the public repository. This prevents overfitting to the dev set. The held-out score is published alongside the dev score in each release's benchmark report so that any gap between dev and held-out performance is visible.

| Set | When Evaluated | Published |
|:---|:---|:---|
| Dev set (public) | Every `make bench` / `scripts/replicate.py` run | In `bench/REPORT.md` |
| Held-out set (private) | Release time only | In release notes alongside dev score |

If the held-out score is significantly worse than the dev score, it indicates overfitting and is flagged in the release notes.

## Verification Commands

```bash
# Run the full test suite
python3 -m pytest tests/ -v

# Run just the replication test
python3 -m pytest tests/test_replication.py -v

# Run the pack benchmark tests
python3 -m pytest tests/test_pack_benchmarks.py -v
```

## Troubleshooting

| Issue | Fix |
|:---|:---|
| `ModuleNotFoundError: kernel` | Run from the repo root: `cd Kairo-Phantom` |
| `FileNotFoundError: fixtures/` | Ensure you cloned with `git clone --recursive` or the fixtures are present |
| Metrics don't match | Check Python version (3.10+); file an issue with your report |
| Air-gap verification fails | See FAQ.md §6 — run `strace` to verify zero egress |
