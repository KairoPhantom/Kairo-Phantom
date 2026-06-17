# Kairo Phantom — ACCEPTANCE.md

Generated at: 2026-06-17T13:15:38.813870+00:00Z  
Target file: `sample_invoice_01.txt`  
Processing time: 47.00ms

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
 1. context_capture    [OK]       (elapsed: 0.0ms)
    Input : {'path': 'fixtures\\invoice\\sample_invoice_01.txt'}
    Output: {'chunk_count': 6, 'page_count': 1}
 2. security_filter    [OK]       (elapsed: 0.0ms)
    Input : {'text_length': 392}
    Output: {'blocked': False, 'reasons': []}
 3. intent_gate        [OK]       (elapsed: 0.0ms)
    Input : {'chunk_count': 6}
    Output: {'type': 'extract', 'pack': 'InvoicePack', 'fields': ['vendor_name', 'invoice_number', 'invoice_date', 'due_date', 'total_amount', 'currency', 'line_items', 'tax_amount', 'payment_terms']}
 4. router             [OK]       (elapsed: 0.0ms)
    Input : {'type': 'extract', 'pack': 'InvoicePack', 'fields': ['vendor_name', 'invoice_number', 'invoice_date', 'due_date', 'total_amount', 'currency', 'line_items', 'tax_amount', 'payment_terms']}
    Output: {'selected_pack': 'InvoicePack', 'fields_to_extract': ['vendor_name', 'invoice_number', 'invoice_date', 'due_date', 'total_amount', 'currency', 'line_items', 'tax_amount', 'payment_terms']}
 5. extractor          [OK]       (elapsed: 0.0ms)
    Input : {'chunk_count': 6}
    Output: {'extraction_count': 9}
 6. quality_gate       [OK]       (elapsed: 0.0ms)
    Input : {'extraction_count': 9}
    Output: {'results': [{'ext_id': 'b3d59601-9e50-4cdd-a92b-70c1fdde698c', 'field': 'vendor_name', 'verdict': 'pass', 'confidence': 0.9}, {'ext_id': '63bddd23-3c24-4b04-966c-4559674c1017', 'field': 'invoice_number', 'verdict': 'pass', 'confidence': 0.95}, {'ext_id': 'f3ca3495-f500-4749-8e83-cf3654d968b3', 'field': 'invoice_date', 'verdict': 'pass', 'confidence': 0.9}, {'ext_id': '2ae3106d-36fb-4792-8191-648c9fae6360', 'field': 'due_date', 'verdict': 'pass', 'confidence': 0.9}, {'ext_id': '9b64118d-c912-47e8-8ef3-01ff727728e3', 'field': 'total_amount', 'verdict': 'pass', 'confidence': 0.95}, {'ext_id': 'a3ba39bc-a6fe-40f0-8fc4-a3e0ecaa1021', 'field': 'currency', 'verdict': 'pass', 'confidence': 0.9}, {'ext_id': 'ae3bd0d9-d0a6-48dc-ad4e-3caf5f602a97', 'field': 'tax_amount', 'verdict': 'pass', 'confidence': 0.85}, {'ext_id': 'f7e3f69f-b8af-4a85-9218-aa959cbcbd1b', 'field': 'payment_terms', 'verdict': 'pass', 'confidence': 0.85}, {'ext_id': '1a2e7a38-48af-4fd9-90ab-15e886d4ac2e', 'field': 'line_items', 'verdict': 'pass', 'confidence': 0.8}], 'passed': 9, 'flagged_or_blocked': 0}
 7. suggest            [OK]       (elapsed: 0.0ms)
    Input : {'passed_count': 9}
    Output: {'suggestions': [{'ext_id': 'b3d59601-9e50-4cdd-a92b-70c1fdde698c', 'field': 'vendor_name', 'value': 'ACME Corp', 'confidence': 0.9}, {'ext_id': '63bddd23-3c24-4b04-966c-4559674c1017', 'field': 'invoice_number', 'value': 'vation', 'confidence': 0.95}, {'ext_id': 'f3ca3495-f500-4749-8e83-cf3654d968b3', 'field': 'invoice_date', 'value': '2026-06-15', 'confidence': 0.9}, {'ext_id': '2ae3106d-36fb-4792-8191-648c9fae6360', 'field': 'due_date', 'value': '2026-07-15', 'confidence': 0.9}, {'ext_id': '9b64118d-c912-47e8-8ef3-01ff727728e3', 'field': 'total_amount', 'value': '1250.00', 'confidence': 0.95}, {'ext_id': 'a3ba39bc-a6fe-40f0-8fc4-a3e0ecaa1021', 'field': 'currency', 'value': 'USD', 'confidence': 0.9}, {'ext_id': 'ae3bd0d9-d0a6-48dc-ad4e-3caf5f602a97', 'field': 'tax_amount', 'value': '0.00', 'confidence': 0.85}, {'ext_id': 'f7e3f69f-b8af-4a85-9218-aa959cbcbd1b', 'field': 'payment_terms', 'value': 'Net 30', 'confidence': 0.85}, {'ext_id': '1a2e7a38-48af-4fd9-90ab-15e886d4ac2e', 'field': 'line_items', 'value': '[{"description": "Consulting Services", "quantity": 10, "unit_price": 125.0, "total": 1250.0}]', 'confidence': 0.8}]}
```

## 3. Grounded Suggestions & Provenance

| Field Name | Extracted Value | Confidence | Provenance Source | Status |
| --- | --- | --- | --- | --- |
| vendor_name | ACME Corp | 0.90 | Grounded (page 1, bbox [0.00, 0.00, 1.00, 0.03]) | suggested |
| invoice_number | vation | 0.95 | Grounded (page 1, bbox [0.00, 0.00, 1.00, 0.03]) | suggested |
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
============================= 45 passed in 0.79s ==============================
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