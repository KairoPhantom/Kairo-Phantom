# Phase 0.1 Receipt: Opik Observability + Provenance Receipts

> **Date**: 2026-06-24
> **Status**: EMIT LAYER DONE — proven end-to-end on 4 real domain masters

---

## What Was Built

### Rust Side (identity.rs extension)
Extended the existing `ProvenanceReceipt` struct with three new fields:
- `opik_trace_id: String` — links to the Python-side Opik trace
- `opik_trace_url: String` — clickable URL to the trace viewer
- `domain: String` — which domain master produced this receipt

All fields use `#[serde(default)]` for backward compatibility with existing receipts.

New method `ReceiptLog::emit_with_trace()` — extends the existing `emit()` method,
not a parallel system. The original `emit()` delegates to `emit_with_trace()` with
empty trace fields.

### Python Side (observability emit layer)
- `sidecar/observability/opik_tracer.py`: Local JSONL trace sink with `@track` decorator
  - `OpikTracer` class: writes traces to `~/.kairo-phantom/opik_traces.jsonl`
  - `TraceContext`: captures domain, action, spans, latency, metadata
  - `@track(domain, action)` decorator: wraps domain master methods
  - PII redaction: SSN, email, phone, credit card patterns redacted before storage
  - Errors loudly on write failure — never silently drops traces

- `sidecar/observability/provenance_bridge.py`: Links Python traces to Rust receipts
  - `read_receipts()`: reads the Rust receipts.jsonl
  - `verify_receipt_chain()`: verifies hash chain integrity
  - `verify_trace_receipt_linkage()`: checks each trace_id has a matching receipt
  - `find_receipts_by_trace_id()`: lookup receipts by trace ID

### Domain Masters Wrapped with @track
1. **WordMaster.apply_operations** → `@track("word", "apply_operations")`
2. **ExcelMaster.apply_operations** → `@track("excel", "apply_operations")`
3. **PDFMaster.extract_context** → `@track("pdf", "extract_context")`
4. **PowerPointMaster.apply_operations** → `@track("pptx", "apply_operations")`
5. **legal_redline.analyze_contract** → `@track("legal", "analyze_contract")`

### Masters NOT YET Wrapped (tracked as sub-items)
- DesignMaster (Domain 6 — still mocked, will be wrapped when un-mocked)
- CodeMaster, BrowserMaster, TerminalMaster, EmailMaster, NotesMaster, MediaMaster, DataMaster
- Memory recall (MemMachine — will be wrapped in Phase 0.4)

## Tests

### Rust Tests (test_audit_chain.rs)
```
cargo test --test test_audit_chain
test result: ok. 22 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

New tests added:
- `test_receipt_05_emit_with_trace_metadata` — verifies trace fields populated
- `test_receipt_06_emit_without_trace_defaults_empty` — backward compatibility
- `test_receipt_07_flagship_provenance_not_faked` — 5 domain calls → 5 receipts with non-empty trace data; tampering detected
- `test_receipt_08_backward_compatible_deserialization` — old receipts still parse

### Python Tests (test_phase0_1_opik.py)
```
pytest test_phase0_1_opik.py
17 passed in 0.38s
```

Covers: trace emission, PII redaction (SSN/email/phone/CC), system prompt leakage (PR-03),
provenance bridge, @track decorator, error handling.

### End-to-End Tests (test_phase0_1_e2e.py)
```
pytest test_phase0_1_e2e.py
6 passed in 2.00s
```

Proves: real WordMaster call → trace emitted → receipt created → chain verified.
Proves: real ExcelMaster, PDFMaster, analyze_contract calls → traces emitted.
Proves: multi-domain chain (4 calls → 4 traces → 4 receipts → 0 violations).
Proves: fake receipt with empty trace_id is correctly detected.

## Receipt Inspection (non-UI)
```bash
python3 -c "
from sidecar.observability.provenance_bridge import read_receipts, verify_receipt_chain
receipts = read_receipts('~/.kairo-phantom/receipts.jsonl')
for r in receipts:
    print(f'  seq={r[\"seq\"]} domain={r[\"domain\"]} action={r[\"action\"]} trace={r[\"opik_trace_id\"]}')
print(f'Chain violations: {verify_receipt_chain()}')
"
```

Sample output:
```
Receipts in chain: 3
  seq=0 domain=word action=apply_operations trace=trace_001
  seq=1 domain=excel action=apply_operations trace=trace_002
  seq=2 domain=legal action=analyze_contract trace=trace_003
Chain violations: 0
```

## Tauri Provenance Panel
DEFERRED to overlay phase. Reason: the Tauri overlay requires a display server
for runtime testing, which is not available in this sandbox. The non-UI inspection
command above provides full receipt visibility now. The panel will be built when
the overlay is tested on real hardware.

## INFRA_PENDING
- Opik self-hosted dashboard (needs Docker) — emit layer works, only the UI dashboard is deferred
- Full Rust workspace `cargo test --workspace` can OOM on <4GB RAM machines — individual targets compile and pass

## Full Rust Test Baseline (verified in this sandbox)
```
cargo test --workspace --lib:     126 passed, 0 failed
cargo test --bin kairo-phantom:   100 passed, 0 failed
cargo test --test * (31 files):   252 passed, 0 failed
Total:                            478 passed, 0 failed
```

## Python Test Baseline
```
294 passed, 44 KNOWN-RED-BY-DESIGN (Domain 6 design bridges — tied to Domain 6 un-mock work)
12 pre-existing Excel failures (missing 'formulas' module — not caused by Phase 0.1)
```