# Kairo Phantom — Golden Corpus

Curated golden set of (document, question) → (expected grounded region OR expected refusal+stage).

## Purpose

These snapshot tests ensure that grounding behavior is **stable and deliberate**. If grounding changes, the test fails and the diff is reviewable. A changed grounding is a deliberate, reviewed decision — never an accident.

## Structure

- `snapshots.json` — The golden snapshots. Each entry records:
  - `case_id`: Unique identifier
  - `doc_file`: Source fixture file
  - `question`: The question asked
  - `value` / `source_span`: The value to ground
  - `expected_outcome`: `answer` or `refusal`
  - `grounding_method`: The cascade stage that matched (or `block`)
  - `anchor_*`: The exact source region (page, bbox, char_span) when grounded

## How to Update

When you **intentionally** change grounding behavior:

1. Run `python3 -m pytest tests/test_golden_corpus.py -v` — it will fail
2. Review the diff to confirm the change is deliberate
3. Regenerate snapshots: `python3 -c "from tests.test_golden_corpus import regenerate; regenerate()"`
4. Commit the updated `snapshots.json` with a message explaining WHY grounding changed

**Never** update snapshots to make a test pass without understanding why the grounding changed.