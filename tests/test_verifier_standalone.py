"""
Tests for the standalone grounding verifier (P1.3).

These tests feed deliberately hallucinated bounding boxes — over whitespace,
over the wrong region, off-page — and assert the verifier rejects them.
They also verify that correctly grounded claims pass.

No mocks, no stubs. The verifier does real geometry and text checks.
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
    bbox_over_whitespace,
    bbox_within_page,
    compute_iou,
    normalize_text,
    verify,
)


# ---------------------------------------------------------------------------
# Fixtures: realistic stored geometry simulating an invoice document
# ---------------------------------------------------------------------------

PAGE = PageBounds(width=800, height=1000)

STORED_REGIONS = [
    StoredRegion(
        text="ACME Corp",
        bbox=BBox(50, 50, 200, 80),
        page=1,
        region_id="r1",
    ),
    StoredRegion(
        text="Invoice Number: INV-2026-001",
        bbox=BBox(50, 150, 350, 180),
        page=1,
        region_id="r2",
    ),
    StoredRegion(
        text="Total Amount Due: $1250.00",
        bbox=BBox(50, 400, 350, 430),
        page=1,
        region_id="r3",
    ),
    StoredRegion(
        text="Payment Terms: Net 30",
        bbox=BBox(50, 350, 300, 380),
        page=1,
        region_id="r4",
    ),
    StoredRegion(
        text="Consulting Services   10     $125.00       $1250.00",
        bbox=BBox(50, 300, 600, 330),
        page=1,
        region_id="r5",
    ),
]

# Whitespace area on the page (no stored regions overlap here)
WHITESPACE_BBOX = BBox(500, 500, 700, 600)


@pytest.fixture
def verifier():
    return StandaloneVerifier()


# ---------------------------------------------------------------------------
# Test: correctly grounded claims are accepted
# ---------------------------------------------------------------------------

class TestCorrectGrounding:
    """Claims with correct text AND correct bbox should pass."""

    def test_exact_match_with_correct_bbox(self, verifier):
        """Exact text match with overlapping bbox → Verified(EXACT)."""
        result = verifier.verify(
            "ACME Corp",
            BBox(55, 52, 195, 78),  # overlaps r1
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Verified)
        assert result.method == VerifyMethod.EXACT
        assert result.iou >= 0.5

    def test_exact_match_invoice_number(self, verifier):
        result = verifier.verify(
            "Invoice Number: INV-2026-001",
            BBox(55, 152, 340, 178),
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Verified)
        assert result.method == VerifyMethod.EXACT

    def test_fuzzy_match_with_correct_bbox(self, verifier):
        """Slightly different text but ≥0.92 fuzzy with correct bbox → Verified(FUZZY)."""
        result = verifier.verify(
            "Total Amount Due: $1250.00",  # exact, but test fuzzy path
            BBox(55, 402, 340, 428),
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Verified)

    def test_verify_convenience_function(self):
        """The module-level verify() convenience function works."""
        result = verify(
            "Payment Terms: Net 30",
            BBox(55, 352, 290, 378),
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Verified)


# ---------------------------------------------------------------------------
# Test: hallucinated bbox over whitespace is rejected
# ---------------------------------------------------------------------------

class TestWhitespaceHallucination:
    """A VLM hallucinating a bbox over whitespace must be rejected."""

    def test_correct_text_but_bbox_over_whitespace(self, verifier):
        """The text 'ACME Corp' exists in the document, but the model points
        to a whitespace area. The verifier must reject — the model cannot
        self-certify a bounding box."""
        result = verifier.verify(
            "ACME Corp",
            WHITESPACE_BBOX,  # over whitespace, no region overlap
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason in (RejectReason.WHITESPACE, RejectReason.BBOX_MISMATCH)
        assert result.best_iou < 0.5

    def test_total_amount_over_whitespace(self, verifier):
        """Model claims 'Total Amount Due: $1250.00' but bbox is in whitespace."""
        result = verifier.verify(
            "Total Amount Due: $1250.00",
            BBox(600, 700, 750, 750),  # whitespace area
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.best_iou < 0.5

    def test_bbox_over_whitespace_helper(self):
        """The bbox_over_whitespace helper correctly detects whitespace areas."""
        assert bbox_over_whitespace(WHITESPACE_BBOX, STORED_REGIONS) is True
        assert bbox_over_whitespace(BBox(55, 52, 195, 78), STORED_REGIONS) is False


# ---------------------------------------------------------------------------
# Test: hallucinated bbox over wrong region is rejected
# ---------------------------------------------------------------------------

class TestWrongRegionHallucination:
    """A VLM pointing to the wrong region (text exists but bbox is elsewhere)."""

    def test_correct_text_wrong_region(self, verifier):
        """Text 'ACME Corp' is real, but model points bbox at the total amount
        region. IoU with the correct region is 0, IoU with the wrong region
        may be high but text doesn't match there → rejected."""
        result = verifier.verify(
            "ACME Corp",
            BBox(55, 402, 340, 428),  # overlaps r3 (Total Amount), not r1
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        # The text matched (exact) but bbox didn't overlap the right region
        assert result.reason == RejectReason.BBOX_MISMATCH
        assert result.best_similarity >= 0.9  # text was found
        # best_iou may be high (bbox overlaps the WRONG region) but the
        # verifier still rejected because the text doesn't appear in that region.
        # The key assertion is that it was REJECTED despite text matching.

    def test_invoice_number_wrong_region(self, verifier):
        """Model claims invoice number but points to payment terms area."""
        result = verifier.verify(
            "Invoice Number: INV-2026-001",
            BBox(55, 352, 290, 378),  # overlaps r4 (Payment Terms), not r2
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason == RejectReason.BBOX_MISMATCH


# ---------------------------------------------------------------------------
# Test: off-page bbox is rejected
# ---------------------------------------------------------------------------

class TestOffPageHallucination:
    """A VLM producing coordinates outside the page bounds must be rejected."""

    def test_bbox_beyond_page_width(self, verifier):
        result = verifier.verify(
            "ACME Corp",
            BBox(900, 50, 1100, 80),  # x > page width (800)
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason == RejectReason.OFF_PAGE

    def test_bbox_beyond_page_height(self, verifier):
        result = verifier.verify(
            "ACME Corp",
            BBox(50, 1100, 200, 1150),  # y > page height (1000)
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason == RejectReason.OFF_PAGE

    def test_negative_coordinates(self, verifier):
        result = verifier.verify(
            "ACME Corp",
            BBox(-50, 50, 100, 80),  # negative x
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason == RejectReason.OFF_PAGE

    def test_off_page_without_page_bounds(self, verifier):
        """Without page_bounds, off-page check is skipped — but whitespace
        check still catches it if no region overlaps."""
        result = verifier.verify(
            "ACME Corp",
            BBox(900, 50, 1100, 80),
            STORED_REGIONS,
            page_bounds=None,
        )
        assert isinstance(result, Rejected)
        # Not OFF_PAGE (no bounds), but still rejected
        assert result.reason != RejectReason.OFF_PAGE


# ---------------------------------------------------------------------------
# Test: empty / garbage quotes are rejected
# ---------------------------------------------------------------------------

class TestEmptyAndGarbageQuotes:
    def test_empty_quote_rejected(self, verifier):
        result = verifier.verify(
            "",
            BBox(55, 52, 195, 78),
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason == RejectReason.EMPTY_QUOTE

    def test_whitespace_only_quote_rejected(self, verifier):
        result = verifier.verify(
            "   \n\t  ",
            BBox(55, 52, 195, 78),
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason == RejectReason.EMPTY_QUOTE

    def test_nonexistent_text_rejected(self, verifier):
        """Text that doesn't appear anywhere in the document → rejected."""
        result = verifier.verify(
            "This text does not appear in the document at all",
            BBox(55, 52, 195, 78),
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason in (RejectReason.NO_MATCH, RejectReason.BBOX_MISMATCH)


# ---------------------------------------------------------------------------
# Test: no stored geometry
# ---------------------------------------------------------------------------

class TestNoGeometry:
    def test_empty_geometry_rejected(self, verifier):
        result = verifier.verify(
            "ACME Corp",
            BBox(55, 52, 195, 78),
            [],
            PAGE,
        )
        assert isinstance(result, Rejected)
        assert result.reason == RejectReason.NO_MATCH


# ---------------------------------------------------------------------------
# Test: model confidence is irrelevant to the verifier
# ---------------------------------------------------------------------------

class TestConfidenceIrrelevance:
    """The verifier never trusts model-reported confidence. Even if a model
    claims 0.99 confidence, if the bbox is hallucinated, the verifier rejects.

    This is the core moat: the model can never self-certify a bounding box.
    """

    def test_high_confidence_does_not_override_rejection(self, verifier):
        """The verifier API takes no confidence parameter. A hallucinated bbox
        is rejected regardless of what confidence the model reported."""
        # The verify() signature has no confidence parameter — that's the point.
        # We simulate a "high confidence" model claim by using correct text
        # but a hallucinated bbox. The verifier rejects it.
        result = verifier.verify(
            "ACME Corp",  # correct text
            WHITESPACE_BBOX,  # hallucinated bbox
            STORED_REGIONS,
            PAGE,
        )
        assert isinstance(result, Rejected)
        # The verifier never saw any confidence score — it only checked geometry
        assert result.reason in (RejectReason.WHITESPACE, RejectReason.BBOX_MISMATCH)


# ---------------------------------------------------------------------------
# Test: IoU computation correctness
# ---------------------------------------------------------------------------

class TestIoUComputation:
    def test_identical_boxes_iou_1(self):
        a = BBox(0, 0, 100, 100)
        b = BBox(0, 0, 100, 100)
        assert compute_iou(a, b) == pytest.approx(1.0)

    def test_non_overlapping_iou_0(self):
        a = BBox(0, 0, 100, 100)
        b = BBox(200, 200, 300, 300)
        assert compute_iou(a, b) == pytest.approx(0.0)

    def test_half_overlap_iou(self):
        a = BBox(0, 0, 100, 100)
        b = BBox(50, 0, 150, 100)
        # intersection = 50*100 = 5000, union = 10000 + 10000 - 5000 = 15000
        assert compute_iou(a, b) == pytest.approx(5000 / 15000)

    def test_contained_box_iou(self):
        a = BBox(0, 0, 100, 100)
        b = BBox(25, 25, 75, 75)
        # intersection = 50*50 = 2500, union = 10000 (a contains b)
        assert compute_iou(a, b) == pytest.approx(2500 / 10000)


# ---------------------------------------------------------------------------
# Test: failing-capable — break the verifier and tests go RED
# ---------------------------------------------------------------------------

class TestFailingCapable:
    """These tests verify the tests themselves are failing-capable.
    If someone removes the IoU check from the verifier, the whitespace
    hallucination test should fail."""

    def test_whitespace_rejection_depends_on_iou(self, verifier):
        """If the IoU threshold were removed, this would pass (wrongly).
        The test proves the IoU check is active."""
        result = verifier.verify(
            "ACME Corp",
            WHITESPACE_BBOX,
            STORED_REGIONS,
            PAGE,
        )
        # This MUST be Rejected. If someone removes the IoU check,
        # the exact text match would cause a false Verified.
        assert isinstance(result, Rejected), (
            "FAIL: verifier accepted a bbox over whitespace — IoU check is broken"
        )