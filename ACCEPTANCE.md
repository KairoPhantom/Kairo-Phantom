# Kairo Phantom — ACCEPTANCE.md

Generated at: 2026-06-22T14:17:17.918695+00:00Z  
Target file: `sample_invoice_01.txt`  
Processing time: 33.49ms

## 1. Acceptance Checklist (DoD Checklist Status)

| Criterion | Expected | Measured | Status |
| --- | --- | --- | --- |
| Kernel Purity Guard | Imports nothing from `/domains` or `/legacy` | pure | [PASS] |
| Domains Unchanged Guard | `/domains` files byte-for-byte unchanged | unchanged | [PASS] |
| Ingestor Invariant | All chunks have non-null page + bbox | 100% chunks | [PASS] |
| Air-Gap Egress | Tier3 (cloud) blocked when disabled | blocked | [PASS] |
| Provenance Coverage | 100.0% of suggestions have full grounded chain | 100.0% | [PASS] |
| CUA Read+Suggest | Suggest action generated, no autonomous write | ref-refused/read-suggest only | [PASS] |

## 2. Pipeline Execution Trace

```
 1. context_capture    [OK]       (elapsed: 0.7ms)
    Input : {'path': 'fixtures/invoice/sample_invoice_01.txt'}
    Output: {'chunk_count': 6, 'page_count': 1}
 2. security_filter    [OK]       (elapsed: 0.7ms)
    Input : {'text_length': 392}
    Output: {'blocked': False, 'reasons': []}
 3. intent_gate        [OK]       (elapsed: 0.0ms)
    Input : {'chunk_count': 6}
    Output: {'type': 'extract', 'pack': 'InvoicePack', 'fields': ['vendor_name', 'invoice_number', 'invoice_date', 'due_date', 'total_amount', 'currency', 'line_items', 'tax_amount', 'payment_terms']}
 4. router             [OK]       (elapsed: 0.0ms)
    Input : {'type': 'extract', 'pack': 'InvoicePack', 'fields': ['vendor_name', 'invoice_number', 'invoice_date', 'due_date', 'total_amount', 'currency', 'line_items', 'tax_amount', 'payment_terms']}
    Output: {'selected_pack': 'InvoicePack', 'fields_to_extract': ['vendor_name', 'invoice_number', 'invoice_date', 'due_date', 'total_amount', 'currency', 'line_items', 'tax_amount', 'payment_terms']}
 5. extractor          [OK]       (elapsed: 13.9ms)
    Input : {'chunk_count': 6}
    Output: {'extraction_count': 9}
 6. quality_gate       [OK]       (elapsed: 0.5ms)
    Input : {'extraction_count': 9}
    Output: {'results': [{'ext_id': '2a56f8fe-876a-4651-8ca4-70995d05d169', 'field': 'vendor_name', 'verdict': 'pass', 'confidence': 0.9}, {'ext_id': '169aa086-6ffa-47a4-bad7-195715aab566', 'field': 'invoice_number', 'verdict': 'pass', 'confidence': 0.95}, {'ext_id': '3d21d781-dc51-418c-bac8-8acfbe118882', 'field': 'invoice_date', 'verdict': 'pass', 'confidence': 0.9}, {'ext_id': '1e214f5b-ffbe-4d94-8999-64cf3c486c48', 'field': 'due_date', 'verdict': 'pass', 'confidence': 0.9}, {'ext_id': 'b1e93afb-2b03-44ac-80bb-591d334a0545', 'field': 'total_amount', 'verdict': 'pass', 'confidence': 0.95}, {'ext_id': '7a2d4117-e72c-483a-bfa9-87e7518a2f75', 'field': 'currency', 'verdict': 'pass', 'confidence': 0.9}, {'ext_id': '527bde04-66cb-49b1-8f51-efdef7d88520', 'field': 'tax_amount', 'verdict': 'pass', 'confidence': 0.85}, {'ext_id': '4b47790d-c0eb-4c5b-92d2-ee2d3d626d37', 'field': 'payment_terms', 'verdict': 'pass', 'confidence': 0.85}, {'ext_id': 'd1aa7e41-d98d-45ce-99c3-20338f339f7d', 'field': 'line_items', 'verdict': 'pass', 'confidence': 0.8}], 'passed': 9, 'flagged_or_blocked': 0}
 7. suggest            [OK]       (elapsed: 0.0ms)
    Input : {'passed_count': 9}
    Output: {'suggestions': [{'ext_id': '2a56f8fe-876a-4651-8ca4-70995d05d169', 'field': 'vendor_name', 'value': 'ACME Corp', 'confidence': 0.9}, {'ext_id': '169aa086-6ffa-47a4-bad7-195715aab566', 'field': 'invoice_number', 'value': 'INV-2026-001', 'confidence': 0.95}, {'ext_id': '3d21d781-dc51-418c-bac8-8acfbe118882', 'field': 'invoice_date', 'value': '2026-06-15', 'confidence': 0.9}, {'ext_id': '1e214f5b-ffbe-4d94-8999-64cf3c486c48', 'field': 'due_date', 'value': '2026-07-15', 'confidence': 0.9}, {'ext_id': 'b1e93afb-2b03-44ac-80bb-591d334a0545', 'field': 'total_amount', 'value': '1250.00', 'confidence': 0.95}, {'ext_id': '7a2d4117-e72c-483a-bfa9-87e7518a2f75', 'field': 'currency', 'value': 'USD', 'confidence': 0.9}, {'ext_id': '527bde04-66cb-49b1-8f51-efdef7d88520', 'field': 'tax_amount', 'value': '0.00', 'confidence': 0.85}, {'ext_id': '4b47790d-c0eb-4c5b-92d2-ee2d3d626d37', 'field': 'payment_terms', 'value': 'Net 30', 'confidence': 0.85}, {'ext_id': 'd1aa7e41-d98d-45ce-99c3-20338f339f7d', 'field': 'line_items', 'value': '[{"description": "Consulting Services", "quantity": 10, "unit_price": 125.0, "total": 1250.0}]', 'confidence': 0.8}]}
```

## 3. Grounded Suggestions & Provenance

| Field Name | Extracted Value | Confidence | Provenance Source | Status |
| --- | --- | --- | --- | --- |
| vendor_name | ACME Corp | 0.90 | Grounded (page 1, bbox [0.00, 0.00, 1.00, 0.03]) | suggested |
| invoice_number | INV-2026-001 | 0.95 | Grounded (page 1, bbox [0.00, 0.05, 1.00, 0.13]) | suggested |
| invoice_date | 2026-06-15 | 0.90 | Grounded (page 1, bbox [0.00, 0.05, 1.00, 0.13]) | suggested |
| due_date | 2026-07-15 | 0.90 | Grounded (page 1, bbox [0.00, 0.05, 1.00, 0.13]) | suggested |
| total_amount | 1250.00 | 0.95 | Grounded (page 1, bbox [0.00, 0.22, 1.00, 0.25]) | suggested |
| currency | USD | 0.90 | Grounded (page 1, bbox [0.00, 0.27, 1.00, 0.32]) | suggested |
| tax_amount | 0.00 | 0.85 | Grounded (page 1, bbox [0.00, 0.22, 1.00, 0.25]) | suggested |
| payment_terms | Net 30 | 0.85 | Grounded (page 1, bbox [0.00, 0.05, 1.00, 0.13]) | suggested |
| line_items | [{"description": "Consulting Services", "quantity": 10, "unit_price": 125.0, "total": 1250.0}] | 0.80 | Grounded (page 1, bbox [0.00, 0.22, 1.00, 0.25]) | suggested |

## 4. Verification Gauntlet Results

Real commands executed during acceptance check:

```bash
$ make build
kernel + packs + bench import OK
BUILD: GREEN

$ make test
packs/tests/test_paper_pack.py::test_paper_pack_fields PASSED            [ 97%]
packs/tests/test_paper_pack.py::test_paper_pack_extract PASSED           [100%]
============================== 45 passed in 0.34s ==============================
TEST: GREEN

$ make safety
    [PASS] Gate-bypass audit PASSED: Ungrounded extraction was successfully BLOCKED.
=====================================================================
[PASS] SAFETY AUDITS: ALL PASSED
SAFETY: GREEN

$ make domains-check
Checking: /domains files are byte-for-byte unchanged
============================================================
PASSED — all domain files unchanged
DOMAINS-CHECK: GREEN

```

## 5. Design Partner Sign-Off

> [!NOTE]
> This report confirms that Kairo Phantom is functional on synthetic launch documents
> using a **SYNTHETIC / self-graded — unvalidated** ground-truth key (fixtures/invoice/ground_truth.json)
> and preserves the 12 legacy domains intact for future progressive migration.
> Production-ready status is NOT claimed.

### Open Items
- [ ] Notepad/Browser/Office real-app CUA actions remain **BLOCKED** and are marked `PENDING-REAL-APP` (require live host VM with MS Office + Ollama).