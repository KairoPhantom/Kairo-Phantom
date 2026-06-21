# Kairo Phantom — IT Security & Compliance Brief

**Document classification:** Internal / For IT Security Review
**Purpose:** Unblocks the lawyer whose purchase is gated by IT approval.

---

## What Kairo Phantom Is

Kairo Phantom is a **local-first, verifiable document-intelligence tool**. It answers questions about documents by citing the exact bounding-box region the answer came from. Its core promise: **"No source → no answer."**

It **reads** documents and **suggests** actions. It **never writes** to or drives source applications (Word, Excel, desktop) in v1.

---

## The Compliance Headline: Signed Audit Log

Every answer AND every refusal is recorded in a **tamper-evident, cryptographically signed audit log**. This is the Contract/Compliance Pack's headline feature.

### What the log records

| Field | Description |
|:---|:---|
| Question | The user's question |
| Document hash | SHA-256 of the source document |
| Outcome | `answer` or `refusal` |
| Source region | For answers: exact page, bounding box, character span cited |
| Cascade stage | For refusals: which grounding stage blocked (e.g. `BLOCK`) |
| Model ID | Which model produced the answer |
| Timestamp | ISO-8601 UTC |
| Signature | HMAC-SHA256 over (content + previous entry's signature) |

### Tamper-evidence

The log uses **HMAC-SHA256 hash chaining**: each entry's signature covers its own content plus the previous entry's signature. Modifying any field in any entry invalidates the chain from that entry forward. Tampering is **detectable by construction**, not by policy.

### Export format

The audit log exports to two formats:
1. **JSON** — machine-readable, for ingestion by SIEM/compliance systems.
2. **Markdown (PDF-ready)** — human-readable, for legal review. Says: *"Here is exactly what the AI cited, and here is what it refused to answer and why."*

---

## Security Posture

### Local-first by default
- All computation runs on-device. No data leaves the machine unless the user explicitly enables BYO-key cloud mode (off by default).
- Air-gap mode emits **zero network egress**, proven by syscall/packet capture in CI.

### No autonomous writes
- v1 is **READ + SUGGEST ONLY**. Kairo never writes to or drives source applications.
- All suggestions require human confirmation before any action is taken.

### Grounding verifier (the moat)
- The Rust-core verifier **independently re-checks** every quote/coordinate against stored document geometry.
- The model can **never self-certify** a bounding box. If the verifier cannot ground a claim to source, the answer is blocked.
- Grounding cascade: `NORMALIZE → EXACT → FUZZY(≥0.92) → SEMANTIC(≥0.86, re-verify) → VISUAL(IoU≥0.5) → BLOCK`

### No ungrounded renders
- There is no code path that displays ungrounded text. The Tauri overlay is render-only.
- If an answer cannot be grounded, Kairo **stays silent** (refuses).

---

## Data Handling

| Concern | Kairo's approach |
|:---|:---|
| Where is data stored? | Local SQLite + LanceDB. No cloud storage by default. |
| Does data leave the device? | No, unless BYO-key cloud is explicitly enabled. |
| Are API keys stored on disk? | No. BYO-key material never hits disk/logs. |
| Can the AI fabricate answers? | No. Every answer is independently verified against source geometry. |
| Is there an audit trail? | Yes — signed, tamper-evident, exportable. |
| Can the audit log be altered? | No — HMAC-SHA256 chaining detects any modification. |

---

## Reproducibility

Every run produces a **reproducibility receipt**: corpus hash + model ID + result hash. Re-running with the same inputs produces a byte-identical receipt. This proves determinism: the same document + same question always yields the same grounded answer or the same refusal.

---

## IT Security Checklist

- [x] Local-first: no cloud dependency by default
- [x] Air-gap mode: zero network egress (CI-proven)
- [x] No BYO-key material on disk or in logs
- [x] Signed, tamper-evident audit log for every answer and refusal
- [x] Independent grounding verification (model cannot self-certify)
- [x] READ + SUGGEST ONLY (no autonomous writes)
- [x] Deterministic, reproducible results with receipts
- [x] Exportable audit trail (JSON + PDF-ready markdown)

---

*This brief is intended for IT security teams evaluating Kairo Phantom for deployment. For technical integration details, see `docs/VERIFIER_CRATE_RELEASE.md`. For the full security audit, see `SECURITY_AUDIT.md`.*