# Fixtures

Real wedge documents and ground-truth keys for the declassification triage Pack.

## Contents

- `wedge/` — Declassification / FOIA triage fixtures
  - `ground_truth.json` — Per-field expected values for labeled fixtures
  - `sample_memo_*.txt` — Synthetic classified memos for testing

## Usage

```bash
make bench FIXTURES_DIR=fixtures/wedge
make demo FILE=fixtures/wedge/sample_memo_01.txt
```

## Note

These are **synthetic** fixtures created for development and testing.
Real classified documents must be supplied by design partners.
The ground-truth keys are human-verified labels for each fixture field.
