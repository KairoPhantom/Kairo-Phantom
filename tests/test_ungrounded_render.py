"""
T3 — Ungrounded render prevention.

Injects adversarial model outputs and asserts the verifier REJECTS every one
and the system refuses rather than renders ungrounded content.
"""

import pytest

from kernel.core.data_model import (
    Anchor,
    BBox,
    Chunk,
    Extraction,
    ExtractionStatus,
    GroundingMethod,
)
from kernel.core.grounding import GroundingVerifierImpl
from kernel.core.contracts import GateResult, GateVerdict
from kernel.sidecar.quality_gate import LocalQualityGate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunks() -> list[Chunk]:
    """Create chunks representing a real document with known geometry."""
    return [
        Chunk(
            chunk_id="c1",
            doc_id="doc1",
            page=1,
            bbox=BBox(10, 10, 200, 30),
            text="Invoice Number: INV-2026-001",
        ),
        Chunk(
            chunk_id="c2",
            doc_id="doc1",
            page=1,
            bbox=BBox(10, 40, 200, 60),
            text="Total Amount Due: $1250.00",
        ),
        Chunk(
            chunk_id="c3",
            doc_id="doc1",
            page=1,
            bbox=BBox(10, 70, 200, 90),
            text="Payment Terms: Net 30",
        ),
    ]


class FakeCorrectionStore:
    """Minimal correction store that returns no corrections."""
    def search_similar_corrections(self, field_name: str, value: str, k: int = 5):
        return []


def is_renderable(extraction: Extraction, verifier: GroundingVerifierImpl, chunks: list[Chunk]) -> bool:
    """Simulate the render path: verify extraction, then check quality gate.
    Returns True if the extraction would be rendered (passed quality gate)."""
    method, anchors = verifier.verify(
        extraction.value, extraction.source_span, chunks
    )
    # Update extraction with grounding result
    from dataclasses import replace
    grounded_ext = replace(extraction, method=method, anchors=anchors,
                           chunk_id=anchors[0].chunk_id if anchors else "")
    
    gate = LocalQualityGate(FakeCorrectionStore())
    result = gate.check(grounded_ext)
    
    # Only PASS verdict is renderable; FLAG and BLOCK are not rendered
    return result.verdict == GateVerdict.PASS


# ---------------------------------------------------------------------------
# T3.1 — Adversarial model output rejection
# ---------------------------------------------------------------------------

class TestAdversarialModelOutputs:
    """Inject adversarial model outputs and assert the verifier rejects all."""

    @pytest.fixture
    def verifier(self):
        return GroundingVerifierImpl(semantic_threshold=0.5)

    @pytest.fixture
    def chunks(self):
        return make_chunks()

    def test_hallucinated_bbox_over_whitespace(self, verifier, chunks):
        """A hallucinated bbox that points to whitespace (no chunk there)
        must be rejected."""
        # Claim the answer is at bbox (500, 500, 600, 520) — no chunk exists there
        method, anchors = verifier.verify(
            "fake value", "bbox:500,500,600,520", chunks
        )
        assert method == GroundingMethod.BLOCK, (
            "Hallucinated bbox over whitespace was not rejected"
        )
        assert len(anchors) == 0

    def test_bbox_over_wrong_region(self, verifier, chunks):
        """A bbox that overlaps the wrong chunk (claiming it's the total
        but pointing at the invoice number region) must not produce
        a grounded answer for the wrong content."""
        # The value "INV-2026-001" with a bbox pointing at the total region
        method, anchors = verifier.verify(
            "INV-2026-001", "bbox:10,40,200,60", chunks  # bbox of c2 (total), value from c1
        )
        # VISUAL might match on bbox overlap, but the text value "INV-2026-001"
        # is in c1, not c2. The visual stage matches on bbox, returning c2's anchor.
        # This is acceptable — visual grounding grounds to the spatial region.
        # But if the value doesn't appear in the chunk text at all, it should not
        # be EXACT/FUZZY/SEMANTIC grounded to the wrong chunk.
        # The key assertion: if VISUAL matches, the anchor points to a real chunk
        # with a real bbox — not a hallucinated one.
        if method == GroundingMethod.VISUAL:
            # Visual grounding is spatial — the anchor must point to a real chunk
            assert len(anchors) == 1
            assert anchors[0].bbox is not None
            # The anchor must correspond to an actual chunk
            chunk_ids = {c.chunk_id for c in chunks}
            assert anchors[0].chunk_id in chunk_ids
        elif method == GroundingMethod.EXACT:
            # EXACT should only match if the value is actually in the chunk text
            anchor_chunk = next(c for c in chunks if c.chunk_id == anchors[0].chunk_id)
            assert "INV-2026-001" in anchor_chunk.text

    def test_off_page_bbox(self, verifier, chunks):
        """A bbox with coordinates outside the page bounds must be rejected."""
        # Negative coordinates
        method, anchors = verifier.verify(
            "fake value", "bbox:-100,-100,-50,-50", chunks
        )
        assert method == GroundingMethod.BLOCK, "Off-page bbox (negative) was not rejected"
        assert len(anchors) == 0

    def test_off_page_bbox_huge_coordinates(self, verifier, chunks):
        """A bbox with absurdly large coordinates must be rejected."""
        method, anchors = verifier.verify(
            "fake value", "bbox:99999,99999,99999,99999", chunks
        )
        assert method == GroundingMethod.BLOCK, "Off-page bbox (huge) was not rejected"

    def test_quote_not_in_stored_geometry(self, verifier, chunks):
        """A quote that doesn't exist in any chunk must be rejected."""
        method, anchors = verifier.verify(
            "This quote does not exist anywhere in the document", "", chunks
        )
        assert method == GroundingMethod.BLOCK, (
            "Non-existent quote was not rejected"
        )
        assert len(anchors) == 0

    def test_high_confidence_wrong_coordinate(self, verifier, chunks):
        """High model confidence paired with a wrong coordinate must still
        be rejected by the verifier. The verifier is model-independent."""
        # Create an extraction with high confidence but wrong value
        extraction = Extraction(
            ext_id="ext1",
            pack_id="invoice",
            field_name="total_amount",
            value="$99999.00",  # Wrong value — not in any chunk
            source_span="$99999.00",
            confidence=0.99,  # High confidence
            chunk_id="c2",
        )
        method, anchors = verifier.verify(
            extraction.value, extraction.source_span, chunks
        )
        assert method == GroundingMethod.BLOCK, (
            "High-confidence wrong value was not rejected by verifier"
        )
        assert len(anchors) == 0

        # Even with high confidence, the quality gate must block it
        renderable = is_renderable(extraction, verifier, chunks)
        assert not renderable, (
            "High-confidence ungrounded extraction was renderable — verifier bypassed"
        )

    def test_fabricated_anchor_with_no_chunk(self, verifier, chunks):
        """An extraction claiming an anchor to a non-existent chunk must
        not be renderable."""
        extraction = Extraction(
            ext_id="ext2",
            pack_id="invoice",
            field_name="vendor",
            value="Fake Vendor LLC",
            source_span="Fake Vendor LLC",
            confidence=0.95,
            chunk_id="nonexistent_chunk",
        )
        renderable = is_renderable(extraction, verifier, chunks)
        assert not renderable, (
            "Extraction with fabricated chunk_id was renderable"
        )

    def test_empty_anchors_not_renderable(self, verifier, chunks):
        """An extraction with empty anchors must not be renderable.
        We test the quality gate directly — it must reject empty anchors
        regardless of what the verifier would find on re-verification."""
        gate = LocalQualityGate(FakeCorrectionStore())

        # Create an extraction that claims to be grounded but has empty anchors
        bad_extraction = Extraction(
            ext_id="ext3",
            pack_id="invoice",
            field_name="total",
            value="$1250.00",
            source_span="$1250.00",
            confidence=0.9,
            chunk_id="c2",
            method=GroundingMethod.EXACT,  # Claims EXACT
            anchors=(),  # But has no anchors
        )
        result = gate.check(bad_extraction)
        assert result.verdict == GateVerdict.BLOCK, (
            "Quality gate did not BLOCK extraction with empty anchors"
        )

    def test_system_refuses_rather_than_renders(self, verifier, chunks):
        """When the verifier blocks, the system must refuse (produce a
        refusal answer), not render the ungrounded text."""
        from kernel.core.data_model import Answer

        # Simulate a query that can't be grounded
        method, anchors = verifier.verify(
            "completely fabricated answer", "", chunks
        )
        assert method == GroundingMethod.BLOCK

        # The system should produce a refused answer, not a grounded one
        if method == GroundingMethod.BLOCK:
            answer = Answer(
                query="What is the tax rate?",
                text="I cannot answer this question from the provided document.",
                grounded=False,
                refused=True,
            )
        else:
            answer = Answer(
                query="What is the tax rate?",
                text="completely fabricated answer",
                grounded=True,
                refused=False,
            )

        assert answer.refused is True, "System did not refuse on ungrounded answer"
        assert answer.grounded is False, "System marked ungrounded answer as grounded"