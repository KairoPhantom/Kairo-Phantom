# Kairo Phantom — Benchmark Methodology

> How pack-specific benchmarks are structured, what hard cases they cover, and how false-refusal is measured.

## Overview

Kairo Phantom's benchmark suite runs pack-specific evaluations that test the grounding cascade against real-world document variations. Each Pack has hard cases designed to expose false-refusal regressions — cases where the system *should* ground an answer but incorrectly refuses.

## Benchmark Harness

The pack benchmark harness (`bench/pack_benchmarks.py`) runs each Pack against its fixture corpus and reports:

| Metric | Definition | Target |
|:---|:---|:---|
| Grounded-Answer Rate | % of answerable questions that receive a grounded answer | ≥ 95% |
| False-Refusal Rate | % of answerable questions that are incorrectly refused | < 5% |
| Refusal-Correctness | % of unanswerable questions correctly refused | 100% |
| Citation-Hallucination | % of citations that point to non-existent text | 0% |

## Pack-Specific Hard Cases

### Invoice Pack

**Hard cases:**
1. **Merged-cell totals** — invoices where the total amount is inside a table cell with box-drawing characters (┌─┐│├─┤└─┘) that can confuse regex extraction
2. **Partially-scanned invoices** — invoices with OCR artifacts (e.g., "T0tal Am0unt Due" instead of "Total Amount Due") that test fuzzy matching
3. **Varied vendors** — different vendor name formats (single line, multi-line, with addresses)
4. **Varied currencies** — USD, EUR, GBP, JPY
5. **Varied layouts** — different column orders, different label phrasings

**Key false-refusal question:** "What is the total amount due?"
- This should always be answerable on a complete invoice
- False-refusal on this question is a regression that CI must catch

### Contract Pack

**Hard cases:**
1. **Cross-referenced clauses** — contracts where Section 5 references "Section 2" and "Exhibit A", requiring the extractor to resolve references across sections
2. **Defined terms used across sections** — terms defined in Section 1 ("Effective Date", "Licensor", "Licensee") used throughout the document
3. **Exhibits** — separate exhibit sections (Exhibit A, Exhibit B) that reference back to main body sections

**Key false-refusal question:** "What does Section 5 reference?"
- Cross-referenced clauses should be extractable and grounded
- False-refusal on cross-referenced clauses is a regression

### Paper Pack

**Hard cases:**
1. **Figure-caption-only facts** — facts that appear *only* in figure captions (e.g., "BERT-Large has 340M parameters" appears only in "Figure 3: Comparison of BERT model sizes...")
2. **Table-caption facts** — facts in table captions
3. **Multi-figure papers** — papers with 3+ figures, each with distinct captions

**Key false-refusal question:** "How many parameters does BERT-Large have?"
- The answer is in Figure 3's caption only — not in the main text
- False-refusal on figure-caption findings is a regression

## Fixture Corpus

Fixtures are organized by Pack and hard-case category:

```
fixtures/
├── invoice/
│   ├── ground_truth.json              # base fixtures
│   ├── sample_invoice_01.txt
│   ├── sample_invoice_02.txt
│   ├── sample_invoice_03.txt
│   ├── merged_cells/
│   │   ├── ground_truth.json          # merged-cell totals
│   │   └── sample_invoice_merged_01.txt
│   └── partially_scanned/
│       ├── ground_truth.json          # OCR artifacts
│       ├── sample_invoice_partial_01.txt
│       └── sample_invoice_partial_02.txt
├── contract/
│   ├── ground_truth.json              # base fixtures
│   ├── sample_contract_01.txt
│   ├── sample_contract_02.txt
│   ├── sample_contract_03.txt
│   └── cross_refs/
│       ├── ground_truth.json          # cross-referenced clauses
│       ├── sample_contract_xref_01.txt
│       └── sample_contract_xref_02.txt
├── paper/
│   ├── ground_truth.json              # base fixtures
│   ├── sample_paper_01.txt
│   ├── sample_paper_02.txt
│   ├── sample_paper_03.txt
│   └── figure_captions/
│       ├── ground_truth.json          # figure-caption-only facts
│       ├── sample_paper_figcap_01.txt
│       └── sample_paper_figcap_02.txt
└── generic/
    ├── ground_truth.json
    ├── sample_generic_01.txt
    ├── sample_generic_02.txt
    └── sample_generic_03.txt
```

## Scoring Method

### Grounded-Answer Rate
For each answerable question (ground truth has a non-null expected value):
- **Grounded:** The extraction passes the quality gate AND the grounding verifier anchors it (method ≠ BLOCK)
- **Refused:** The extraction is blocked by the quality gate or grounding verifier returns BLOCK
- **Rate = grounded / (grounded + refused)**

### False-Refusal Rate
For each answerable question where the ground truth has a known answer:
- **False refusal:** The system refuses (BLOCK) but the ground truth says the answer exists in the document
- **Rate = false_refusals / total_answerable**

### Refusal-Correctness
For each unanswerable question (ground truth value is null/empty):
- **Correct refusal:** The system refuses (BLOCK)
- **Incorrect answer:** The system produces a grounded answer for a question with no ground truth
- **Rate = correct_refusals / total_unanswerable**

## Regression Testing

Each hard case is pinned to a named document in `tests/test_pack_benchmarks.py`. If a future change regresses false-refusal on:
- "invoice total" (merged cells or partially scanned)
- "cross-referenced clause" (contract cross-references)
- "figure-caption finding" (paper figure-caption-only facts)

...CI fails with a specific, named assertion that identifies the regression.

## Reproducibility

All benchmarks use deterministic test mode (`KAIRO_GATEWAY_TEST_MODE=true`) to ensure reproducible results. The held-out private set is evaluated only at release and published alongside dev scores so overfitting is visible. See `REPLICATE.md` for full replication instructions.
