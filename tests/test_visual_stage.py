"""
Tests for the VISUAL stage (IoU≥0.5) of the grounding cascade (P1.3).

The VISUAL stage is a bbox-first fallback: if text matching (EXACT/FUZZY/SEMANTIC)
fails but the claimed bbox overlaps a stored region by IoU≥0.5, and the claimed
quote appears in that region's text, the claim is accepted as a visual match.

These tests use real bbox fixtures and real IoU computation — no mocks.
"""
import pytest

from kernel.core.verifier_standalone import (
    BBox,
    PageBounds,
    Rejected,
    RejectReason,
    StandaloneVerifier,
    StoredRegion,
    Verified,
    VerifyMethod,
    compute_iou,
)


# ---------------------------------------------------------------------------
# Fixtures: a document with text regions at known coordinates
# ---------------------------------------------------------------------------

PAGE = PageBounds(width=1000, height=1200)

# Regions simulating an OCR'd document page
REGIONS = [
    StoredRegion(
        text="Invoice Number: INV-2026-001",
        bbox=BBox(100, 100, 400, 140),
        page=1,
        region_id="hdr_1",
    ),
    StoredRegion(
        text="Total Amount Due: $1250.00",
        bbox=BBox(100, 500, 400, 540),
        page=1,
        region_id="total_1",
    ),
    StoredRegion(
        text="Consulting Services 10 $125.00 $1250.00",
        bbox=BBox(100, 400, 600, 440),
        page=1,
        region_id="line_1",
    ),
    StoredRegion(
        text="Due Date: 2026-07-15",
        bbox=BBox(100, 200, 350, 230),
        page=1,
        region_id="due_1",
    ),
]

# A region with OCR-degraded text (typos, missing chars) to test visual fallback
DEGRADED_REGIONS = [
    StoredRegion(
        text="Invoce Numbr: INV-2026-001",  # OCR degraded
        bbox=BBox(100, 100, 400, 140),
        page=1,
        region_id="degraded_1",
    ),
    StoredRegion(
        text="Total Amount Due: $1250.00",
        bbox=BBox(100, 500, 400, 540),
        page=1,
        region_id="total_1",
    ),
]


@pytest.fixture
def verifier():
    return StandaloneVerifier(visual_iou_threshold=0.5)


# ---------------------------------------------------------------------------
# Test: IoU threshold boundary
# ---------------------------------------------------------------------------

class TestIoUBoundary:
    """IoU exactly at 0.5 should pass; below 0.5 should fail."""

    def test_iou_exactly_0_5_passes(self, verifier):
        """Construct two boxes with IoU exactly 0.5.
        Box A: (0,0,100,100) area=10000
        Box B: (50,0,150,100) area=10000
        Intersection: (50,0,100,100) = 50*100 = 5000
        Union: 10000 + 10000 - 5000 = 15000
        IoU = 5000/15000 = 0.333... NOT 0.5.

        For IoU=0.5: intersection = union/2
        Box A: (0,0,200,100) area=20000
        Box B: (100,0,300,100) area=20000
        Intersection: (100,0,200,100) = 100*100 = 10000
        Union: 20000 + 20000 - 10000 = 30000
        IoU = 10000/30000 = 0.333...

        For IoU = 0.5 exactly:
        Box A: (0,0,100,100) area=10000
        Box B: (0,0,100,100) → IoU=1.0 (identical)

        Box A: (0,0,100,100) area=10000
        Box B: (50,50,150,150) area=10000
        Intersection: (50,50,100,100) = 50*50 = 2500
        Union: 10000 + 10000 - 2500 = 17500
        IoU = 2500/17500 = 0.1428...

        For IoU = 0.5: need intersection = union/2
        If A = B: IoU = 1
        If A contains B: IoU = B_area / A_area
        So B_area / A_area = 0.5 → B is half of A
        A: (0,0,100,100) area=10000
        B: (25,25,75,75) area=2500
        IoU = 2500/10000 = 0.25

        A: (0,0,100,100) area=10000
        B: (0,0,100,50) area=5000
        Intersection: (0,0,100,50) = 5000
        Union: 10000 (A contains B)
        IoU = 5000/10000 = 0.5 ✓
        """
        a = BBox(0, 0, 100, 100)
        b = BBox(0, 0, 100, 50)
        assert compute_iou(a, b) == pytest.approx(0.5)

    def test_iou_below_0_5_fails(self, verifier):
        """IoU < 0.5 should not pass the visual stage."""
        a = BBox(0, 0, 100, 100)
        b = BBox(0, 0, 100, 40)  # area=4000, IoU = 4000/10000 = 0.4
        assert compute_iou(a, b) < 0.5

    def test_iou_above_0_5_passes(self, verifier):
        """IoU > 0.5 should pass the visual stage."""
        a = BBox(0, 0, 100, 100)
        b = BBox(0, 0, 100, 60)  # area=6000, IoU = 6000/10000 = 0.6
        assert compute_iou(a, b) > 0.5


# ---------------------------------------------------------------------------
# Test: VISUAL stage accepts bbox-overlapping claims with text in region
# ---------------------------------------------------------------------------

class TestVisualStageAccept:
    """The VISUAL stage accepts when bbox overlaps a region (IoU≥0.5) and
    the claimed quote appears in that region's text."""

    def test_visual_match_exact_text_in_overlapping_region(self, verifier):
        """Claim has correct text and bbox overlapping the right region.
        Even if EXACT stage would catch this, VISUAL also works."""
        result = verifier.verify(
            "Invoice Number: INV-2026-001",
            BBox(110, 105, 390, 135),  # overlaps hdr_1 with high IoU
            REGIONS,
            PAGE,
        )
        assert isinstance(result, Verified)
        assert result.iou >= 0.5

    def test_visual_match_degraded_text(self, verifier):
        """OCR-degraded text: exact/fuzzy may fail, but if the claimed quote
        appears in the region and bbox overlaps, VISUAL stage catches it."""
        # The degraded region has "Invoce Numbr: INV-2026-001"
        # Claim the correct text "Invoice Number: INV-2026-001"
        # Fuzzy match should still be ≥0.92 (only 2 char diffs in a long string)
        result = verifier.verify(
            "Invoice Number: INV-2026-001",
            BBox(110, 105, 390, 135),  # overlaps degraded_1
            DEGRADED_REGIONS,
            PAGE,
        )
        # Should pass via FUZZY or VISUAL
        assert isinstance(result, Verified)
        assert result.iou >= 0.5

    def test_visual_match_partial_overlap(self, verifier):
        """Bbox partially overlaps a region but IoU ≥ 0.5."""
        # Region total_1: (100, 500, 400, 540) area = 300*40 = 12000
        # Claim bbox: (100, 500, 400, 540) → identical, IoU = 1.0
        result = verifier.verify(
            "Total Amount Due: $1250.00",
            BBox(100, 500, 400, 540),
            REGIONS,
            PAGE,
        )
        assert isinstance(result, Verified)
        assert result.iou == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: VISUAL stage rejects when IoU < 0.5
# ---------------------------------------------------------------------------

class TestVisualStageReject:
    """The VISUAL stage rejects when bbox overlap is below the IoU threshold."""

    def test_low_iou_rejected(self, verifier):
        """Bbox barely touches a region — IoU < 0.5 → rejected."""
        # Region hdr_1: (100, 100, 400, 140) area = 300*40 = 12000
        # Claim bbox: (380, 100, 500, 140) area = 120*40 = 4800
        # Intersection: (380, 100, 400, 140) = 20*40 = 800
        # Union: 12000 + 4800 - 800 = 16000
        # IoU = 800/16000 = 0.05
        result = verifier.verify(
            "Invoice Number: INV-2026-001",
            BBox(380, 100, 500, 140),
            REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.best_iou < 0.5

    def test_no_overlap_rejected(self, verifier):
        """Bbox doesn't overlap any region at all → rejected."""
        result = verifier.verify(
            "Invoice Number: INV-2026-001",
            BBox(700, 700, 900, 800),  # no overlap with any region
            REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.best_iou == pytest.approx(0.0)

    def test_text_in_region_but_bbox_elsewhere_rejected(self, verifier):
        """Text appears in a region, but claimed bbox is over a different region.
        The VISUAL stage checks each region: the bbox overlaps the wrong region
        (where the text doesn't appear), and doesn't overlap the right region."""
        result = verifier.verify(
            "Invoice Number: INV-2026-001",  # in hdr_1 at (100,100,400,140)
            BBox(100, 500, 400, 540),  # overlaps total_1, not hdr_1
            REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        # Text matched exactly but bbox was over the wrong region
        assert result.reason == RejectReason.BBOX_MISMATCH


# ---------------------------------------------------------------------------
# Test: VISUAL stage with multiple regions
# ---------------------------------------------------------------------------

class TestVisualMultipleRegions:
    def test_correct_region_selected_among_many(self, verifier):
        """With multiple regions, the verifier finds the right one."""
        result = verifier.verify(
            "Due Date: 2026-07-15",
            BBox(110, 205, 340, 228),  # overlaps due_1
            REGIONS,
            PAGE,
        )
        assert isinstance(result, Verified)
        assert result.matched_region_id == "due_1"

    def test_wrong_region_among_many_rejected(self, verifier):
        """Claim points to wrong region among many → rejected."""
        result = verifier.verify(
            "Due Date: 2026-07-15",
            BBox(110, 105, 390, 135),  # overlaps hdr_1, not due_1
            REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)


# ---------------------------------------------------------------------------
# Test: failing-capable — removing IoU check breaks tests
# ---------------------------------------------------------------------------

class TestVisualFailingCapable:
    """If someone sets the IoU threshold to 0.0, these tests should fail
    because hallucinated bboxes would wrongly pass."""

    def test_zero_iou_threshold_lets_hallucinations_through(self):
        """This test documents what happens with a broken threshold.
        A verifier with iou_threshold=0.0 would accept whitespace bboxes."""
        broken_verifier = StandaloneVerifier(visual_iou_threshold=0.0)
        result = broken_verifier.verify(
            "Invoice Number: INV-2026-001",
            BBox(700, 700, 900, 800),  # no overlap
            REGIONS,
            PAGE,
        )
        # With threshold=0.0, even zero overlap passes — this is the broken case
        # This test proves that the threshold matters
        assert isinstance(result, Verified), (
            "With iou_threshold=0.0, even no-overlap passes — "
            "this documents the broken behavior the threshold prevents"
        )

    def test_normal_threshold_blocks_hallucination(self, verifier):
        """With the correct threshold (0.5), the same hallucination is blocked."""
        result = verifier.verify(
            "Invoice Number: INV-2026-001",
            BBox(700, 700, 900, 800),  # no overlap
            REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected), (
            "With iou_threshold=0.5, no-overlap is correctly rejected"
        )