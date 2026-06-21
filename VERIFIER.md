# Kairo Phantom — Standalone Grounding Verifier

> **The moat:** the Rust verifier independently re-checks every quote/coordinate
> against stored document geometry. The model can never self-certify a bounding box.

## What the Verifier Is

The standalone verifier (`kernel/core/verifier_standalone.py`) is a
**model-independent** module that implements the full grounding cascade:

```
NORMALIZE → EXACT → FUZZY(≥0.92) → SEMANTIC(≥0.86, re-verify)
         → VISUAL(IoU≥0.5) → BLOCK
```

It imports **no model client** — only Python stdlib (`math`, `re`, `dataclasses`,
`enum`, `typing`). It takes geometry data as input and returns `Verified` or
`Rejected`. It never trusts model-reported confidence.

### API

```python
from kernel.core.verifier_standalone import (
    StandaloneVerifier, BBox, StoredRegion, PageBounds, Verified, Rejected
)

verifier = StandaloneVerifier()

result = verifier.verify(
    claimed_quote="Total Amount Due: $1250.00",
    claimed_bbox=BBox(50, 400, 350, 430),
    stored_geometry=[
        StoredRegion(text="Total Amount Due: $1250.00",
                     bbox=BBox(50, 400, 350, 430), region_id="r3"),
        # ... other regions
    ],
    page_bounds=PageBounds(width=800, height=1000),
)

if isinstance(result, Verified):
    print(f"ACCEPTED via {result.method}, IoU={result.iou:.3f}")
else:
    print(f"REJECTED: {result.reason.value} — {result.detail}")
```

The `verify()` function returns:
- **`Verified`** — the claim passed a cascade stage. Contains `method`,
  `matched_text`, `matched_bbox`, `similarity`, `iou`.
- **`Rejected`** — the claim must not be rendered. Contains `reason`,
  `best_similarity`, `best_iou`, `detail`.

### Reject Reasons

| Reason | When |
|:---|:---|
| `OFF_PAGE` | Bbox coordinates are outside page bounds |
| `EMPTY_QUOTE` | Claimed quote is empty after normalization |
| `NO_MATCH` | No text match found in any stored region |
| `BBOX_MISMATCH` | Text matched but bbox didn't overlap the right region (IoU < 0.5) |
| `WHITESPACE` | Bbox is over whitespace (no region overlap at all) |

## Why the Verifier Catches What Confidence Cannot

### The Problem with Confidence Thresholds

A standard RAG system renders an answer if the model's confidence score exceeds
a threshold (e.g., `confidence > 0.8`). This trusts the model to self-certify
its own output. But **a VLM can be confidently wrong**:

1. **Hallucinated bbox over whitespace**: The model reports a high-confidence
   answer with a bounding box that points to an empty area of the page. The text
   might exist elsewhere in the document, but the coordinates are fabricated.

2. **Hallucinated bbox over wrong region**: The model reports the correct text
   but points to a different region of the page. The answer "looks grounded"
   because the text exists, but the citation points to the wrong place.

3. **Off-page coordinates**: The model produces coordinates outside the page
   bounds entirely — a clear fabrication that no confidence threshold catches.

A confidence threshold sees `confidence=0.95` and renders the answer. It has no
way to check whether the bbox actually overlaps the text it claims to cite.

### How the Verifier Catches It

The verifier **never looks at model confidence**. Its `verify()` signature has
no confidence parameter. Instead, it independently checks:

1. **Is the bbox on the page?** (off-page → reject)
2. **Does the claimed text appear in a stored region?** (no match → reject)
3. **Does the claimed bbox overlap the matched region by IoU ≥ 0.5?**
   (bbox mismatch → reject)
4. **Is the bbox over whitespace?** (no region overlap → reject)

Only if all checks pass does the verifier return `Verified`.

## Concrete Worked Example

### Scenario: Invoice Total Amount

A user asks: *"What is the total amount due on this invoice?"*

The document (stored geometry from OCR/layout):

| Region ID | Text | BBox |
|:---|:---|:---|
| `r1` | `ACME Corp` | `(50, 50, 200, 80)` |
| `r2` | `Invoice Number: INV-2026-001` | `(50, 150, 350, 180)` |
| `r3` | `Total Amount Due: $1250.00` | `(50, 400, 350, 430)` |
| `r4` | `Payment Terms: Net 30` | `(50, 350, 300, 380)` |

Page bounds: `800 × 1000` pixels.

### Case 1: Correct grounding (accepted)

The VLM produces:
- Quote: `"Total Amount Due: $1250.00"`
- BBox: `(55, 402, 340, 428)` (overlaps `r3`)
- Confidence: `0.92`

Verifier cascade:
1. **NORMALIZE**: `"total amount due 1250.00"` — non-empty ✓
2. **EXACT**: `"total amount due 1250.00"` found in `r3`'s normalized text ✓
3. **IoU check**: `compute_iou((55,402,340,428), (50,400,350,430)) = 0.87 ≥ 0.5` ✓

→ **`Verified(method=EXACT, iou=0.87)`** — rendered to user with citation.

### Case 2: Hallucinated bbox over whitespace (rejected)

The VLM produces:
- Quote: `"Total Amount Due: $1250.00"` (correct text!)
- BBox: `(600, 700, 750, 750)` (whitespace area — no region here)
- Confidence: `0.95` (high — the model is confidently wrong)

**Confidence-threshold baseline**: `0.95 > 0.8` → **renders the answer** with a
citation pointing to whitespace. The user sees a grounded-looking answer that
cites an empty area of the page. This is an ungrounded render.

**Verifier cascade**:
1. **NORMALIZE**: `"total amount due 1250.00"` — non-empty ✓
2. **EXACT**: found in `r3` ✓ — but...
3. **IoU check**: `compute_iou((600,700,750,750), (50,400,350,430)) = 0.0 < 0.5` ✗
4. **FUZZY**: best fuzzy match in `r3` (ratio=1.0) — but IoU still 0.0 ✗
5. **SEMANTIC**: best Jaccard in `r3` (score=1.0) — but IoU still 0.0 ✗
6. **VISUAL**: no region overlaps `(600,700,750,750)` by IoU ≥ 0.5 ✗
7. **BLOCK**: → **`Rejected(reason=BBOX_MISMATCH, best_similarity=1.0, best_iou=0.0)`**

The verifier rejected the claim even though:
- The text is correct (it exists in the document)
- The model reported 0.95 confidence

The verifier never looked at the confidence. It checked the geometry and found
the bbox points to whitespace. **The answer is not rendered.**

### Case 3: Hallucinated bbox over wrong region (rejected)

The VLM produces:
- Quote: `"Total Amount Due: $1250.00"` (correct text!)
- BBox: `(55, 52, 195, 78)` (overlaps `r1` = "ACME Corp", not `r3`)
- Confidence: `0.88`

**Confidence-threshold baseline**: `0.88 > 0.8` → **renders the answer** with a
citation pointing to "ACME Corp". The user sees the total amount cited to the
vendor name region. This is a misattribution — an ungrounded render.

**Verifier cascade**:
1. **EXACT**: text found in `r3` — but `compute_iou((55,52,195,78), (50,400,350,430)) = 0.0` ✗
2. **VISUAL**: bbox overlaps `r1` (IoU ≈ 0.8 ≥ 0.5) — but `"total amount due"` does NOT
   appear in `r1`'s text (`"ACME Corp"`) ✗
3. **BLOCK**: → **`Rejected(reason=BBOX_MISMATCH, best_similarity=1.0, best_iou=0.0)`**

The verifier caught that the bbox points to the wrong region. The text exists,
but not at the claimed location. **The answer is not rendered.**

### Case 4: Off-page coordinates (rejected)

The VLM produces:
- Quote: `"Total Amount Due: $1250.00"`
- BBox: `(900, 1100, 1000, 1150)` (outside 800×1000 page)
- Confidence: `0.91`

**Confidence-threshold baseline**: `0.91 > 0.8` → **renders the answer** with
off-page coordinates.

**Verifier**: `bbox_within_page((900,1100,1000,1150), 800×1000)` → `False`
→ **`Rejected(reason=OFF_PAGE)`** at step 0, before any text matching.

## The VISUAL Stage (IoU ≥ 0.5)

The VISUAL stage is a **bbox-first fallback** that handles OCR-degraded text.
If text matching (EXACT/FUZZY/SEMANTIC) fails but the claimed bbox overlaps a
stored region by IoU ≥ 0.5, and the claimed quote appears in that region's text,
the claim is accepted as a visual match.

This handles cases where OCR errors prevent text matching but the spatial
location is correct:

| Stored text (OCR degraded) | Claimed quote | BBox overlap |
|:---|:---|:---|
| `Invoce Numbr: INV-2026-001` | `Invoice Number: INV-2026-001` | IoU=0.92 |

The FUZZY stage may catch this (ratio ≥ 0.92 for 2-char diffs in a long string),
but the VISUAL stage provides an additional fallback path.

## Ablation Results

Run `make ablation` to see the live comparison. The ablation demonstrates:

| Condition | Ungrounded-Render Rate |
|:---|:---|
| Verifier ACTIVE | **0%** (all hallucinated bboxes blocked) |
| Verifier BYPASSED | High (all hallucinated bboxes rendered) |
| Confidence-threshold (>0.8) | High (all hallucinated bboxes rendered) |

The verifier catches hallucinated coordinates that both the bypassed and
confidence-threshold conditions miss — because it checks geometry, not confidence.

## Standalone Usage

The verifier can be used without importing the rest of the kernel:

```python
# This works with zero kernel dependencies:
from kernel.core.verifier_standalone import verify, BBox, StoredRegion, PageBounds

result = verify(
    "some text",
    BBox(10, 10, 100, 50),
    [StoredRegion(text="some text", bbox=BBox(10, 10, 100, 50), region_id="r1")],
    PageBounds(width=800, height=1000),
)
```

The module imports only: `math`, `re`, `dataclasses`, `enum`, `typing` — all
Python stdlib. No model clients, no embedding models, no inference gateways.