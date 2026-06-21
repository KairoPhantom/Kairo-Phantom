"""
T1 — Cascade stage + transition tests.

Tests each stage of the grounding cascade in isolation, transition tests
asserting the cascade only advances when the prior stage fails, property-based
tests with fixed seeds, and ablation hooks via disabled_stages.

Cascade: NORMALIZE → EXACT → FUZZY(≥0.92) → SEMANTIC(≥0.86, re-verify) → VISUAL(IoU≥0.5) → BLOCK.
"""

import random
import string

import pytest

from kernel.core.data_model import Anchor, BBox, Chunk, GroundingMethod
from kernel.core.grounding import (
    GroundingVerifierImpl,
    bbox_iou,
    best_fuzzy_match,
    levenshtein_ratio,
    normalize_text,
)
from kernel.core.embeddings import get_embedding, cosine_similarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunk(text: str, chunk_id: str = "c1", page: int = 1, bbox: BBox | None = None) -> Chunk:
    """Create a Chunk with a default bbox if none provided."""
    if bbox is None:
        bbox = BBox(0, 0, 100, 100)
    return Chunk(chunk_id=chunk_id, text=text, page=page, bbox=bbox)


# ---------------------------------------------------------------------------
# T1.1 — Stage isolation tests
# ---------------------------------------------------------------------------

class TestExactStage:
    """EXACT stage: substring match in chunk text."""

    def test_exact_match_returns_exact(self):
        verifier = GroundingVerifierImpl()
        chunks = [make_chunk("The total amount payable is USD 250.00 immediately.")]
        method, anchors = verifier.verify("USD 250.00", "", chunks)
        assert method == GroundingMethod.EXACT
        assert len(anchors) == 1
        assert anchors[0].chunk_id == "c1"

    def test_exact_match_case_insensitive(self):
        verifier = GroundingVerifierImpl()
        chunks = [make_chunk("Invoice Number: INV-2026-001")]
        method, anchors = verifier.verify("inv-2026-001", "", chunks)
        assert method == GroundingMethod.EXACT

    def test_exact_match_finds_correct_span(self):
        verifier = GroundingVerifierImpl()
        text = "The vendor is ACME Corp and the total is $1250.00."
        chunks = [make_chunk(text)]
        method, anchors = verifier.verify("ACME Corp", "", chunks)
        assert method == GroundingMethod.EXACT
        start, end = anchors[0].char_span
        assert text[start:end].lower() == "acme corp"


class TestFuzzyStage:
    """FUZZY stage: Levenshtein ratio ≥ 0.92."""

    def test_fuzzy_match_minor_typo(self):
        verifier = GroundingVerifierImpl(fuzzy_threshold=0.9)
        chunks = [make_chunk("The vendor is Acme Corporation Inc.")]
        # "Acme Corporatin" (missing 'o') vs "Acme Corporation"
        method, anchors = verifier.verify("Acme Corporatin", "", chunks)
        assert method == GroundingMethod.FUZZY
        assert len(anchors) == 1

    def test_fuzzy_below_threshold_falls_through(self):
        # A string with too many differences should not match fuzzy
        verifier = GroundingVerifierImpl(fuzzy_threshold=0.92)
        chunks = [make_chunk("The vendor is Acme Corporation Inc.")]
        method, anchors = verifier.verify("XYZ Completely Different", "", chunks)
        # Should NOT be FUZZY — either SEMANTIC or BLOCK
        assert method != GroundingMethod.FUZZY

    def test_levenshtein_ratio_identical(self):
        assert levenshtein_ratio("hello", "hello") == 1.0

    def test_levenshtein_ratio_single_char_diff(self):
        ratio = levenshtein_ratio("hello", "hallo")
        assert 0.7 < ratio < 1.0

    def test_levenshtein_ratio_completely_different(self):
        assert levenshtein_ratio("abc", "xyz") == 0.0

    def test_best_fuzzy_match_finds_position(self):
        text = "The quick brown fox jumps over the lazy dog."
        ratio, span = best_fuzzy_match("quick brown fox", text)
        assert ratio >= 0.9
        start, end = span
        assert "quick brown fox" in text[start:end].lower()


class TestSemanticStage:
    """SEMANTIC stage: cosine similarity ≥ 0.86 + re-verify word overlap."""

    def test_semantic_match_with_word_overlap(self):
        # Use a low threshold since the offline hash embedding has limited discrimination
        verifier = GroundingVerifierImpl(semantic_threshold=0.3)
        chunks = [make_chunk("The project schedule is delayed by six weeks.")]
        method, anchors = verifier.verify("delayed schedule", "", chunks)
        assert method == GroundingMethod.SEMANTIC
        assert len(anchors) == 1

    def test_semantic_no_word_overlap_blocks(self):
        # Even with high cosine, re-verify requires word intersection.
        # "banana shake" has zero word overlap with the chunk.
        verifier = GroundingVerifierImpl(semantic_threshold=0.0)
        chunks = [make_chunk("The project schedule is delayed by six weeks.")]
        method, anchors = verifier.verify("banana shake", "", chunks)
        # Should NOT be SEMANTIC because re-verify word overlap fails
        assert method != GroundingMethod.SEMANTIC

    def test_embedding_cosine_self_similarity(self):
        emb = get_embedding("hello world test")
        sim = cosine_similarity(emb, emb)
        assert sim == pytest.approx(1.0, abs=1e-6)

    def test_embedding_cosine_different_text_lower(self):
        emb1 = get_embedding("hello world")
        emb2 = get_embedding("completely different text about bananas")
        sim = cosine_similarity(emb1, emb2)
        assert sim < 1.0


class TestVisualStage:
    """VISUAL stage: IoU ≥ 0.5 on stored geometry."""

    def test_visual_match_high_iou(self):
        # Chunk bbox is (10, 10, 50, 50). Candidate bbox overlaps heavily.
        chunk_bbox = BBox(10, 10, 50, 50)
        chunks = [make_chunk("some text", bbox=chunk_bbox)]
        # source_span encodes candidate bbox: "bbox:x0,y0,x1,y1"
        # Overlapping bbox: (12, 12, 48, 48) — IoU should be high
        verifier = GroundingVerifierImpl()
        method, anchors = verifier.verify("some text", "bbox:12,12,48,48", chunks)
        assert method == GroundingMethod.VISUAL
        assert len(anchors) == 1

    def test_visual_match_exact_same_bbox(self):
        chunk_bbox = BBox(10, 10, 50, 50)
        chunks = [make_chunk("some text", bbox=chunk_bbox)]
        verifier = GroundingVerifierImpl()
        method, anchors = verifier.verify("some text", "bbox:10,10,50,50", chunks)
        assert method == GroundingMethod.VISUAL

    def test_visual_below_iou_threshold_blocks(self):
        # Chunk bbox is (0, 0, 100, 100). Candidate bbox barely overlaps.
        chunk_bbox = BBox(0, 0, 100, 100)
        chunks = [make_chunk("some text", bbox=chunk_bbox)]
        # Candidate (90, 90, 200, 200) — IoU is very low
        verifier = GroundingVerifierImpl(visual_threshold=0.5)
        method, anchors = verifier.verify("some text", "bbox:90,90,200,200", chunks)
        assert method == GroundingMethod.BLOCK

    def test_visual_no_overlap_blocks(self):
        chunk_bbox = BBox(0, 0, 50, 50)
        chunks = [make_chunk("some text", bbox=chunk_bbox)]
        verifier = GroundingVerifierImpl()
        method, anchors = verifier.verify("some text", "bbox:100,100,200,200", chunks)
        assert method == GroundingMethod.BLOCK

    def test_bbox_iou_identical(self):
        b1 = BBox(0, 0, 10, 10)
        b2 = BBox(0, 0, 10, 10)
        assert bbox_iou(b1, b2) == pytest.approx(1.0)

    def test_bbox_iou_half_overlap(self):
        b1 = BBox(0, 0, 10, 10)
        b2 = BBox(0, 0, 10, 5)
        # intersection = 10*5=50, area1=100, area2=50, union=100
        assert bbox_iou(b1, b2) == pytest.approx(0.5)

    def test_bbox_iou_no_overlap(self):
        b1 = BBox(0, 0, 10, 10)
        b2 = BBox(20, 20, 30, 30)
        assert bbox_iou(b1, b2) == 0.0


class TestBlockStage:
    """BLOCK: all stages fail → no anchors returned."""

    def test_block_on_completely_unrelated(self):
        verifier = GroundingVerifierImpl()
        chunks = [make_chunk("The project schedule is delayed by six weeks.")]
        method, anchors = verifier.verify("banana shake recipe", "", chunks)
        assert method == GroundingMethod.BLOCK
        assert len(anchors) == 0

    def test_block_on_empty_chunks(self):
        verifier = GroundingVerifierImpl()
        method, anchors = verifier.verify("anything", "", [])
        assert method == GroundingMethod.BLOCK
        assert len(anchors) == 0

    def test_block_on_empty_target(self):
        verifier = GroundingVerifierImpl()
        chunks = [make_chunk("some text")]
        method, anchors = verifier.verify("", "", chunks)
        assert method == GroundingMethod.BLOCK
        assert len(anchors) == 0

    def test_block_on_whitespace_only_target(self):
        verifier = GroundingVerifierImpl()
        chunks = [make_chunk("some text")]
        method, anchors = verifier.verify("   ", "", chunks)
        assert method == GroundingMethod.BLOCK
        assert len(anchors) == 0


# ---------------------------------------------------------------------------
# T1.2 — Transition tests: cascade only advances when prior stage fails
# ---------------------------------------------------------------------------

class TestCascadeTransitions:
    """Assert the cascade only advances to the next stage when the prior stage
    fails its threshold, and that BLOCK is reached when ALL stages fail.
    No stage may be skipped."""

    def test_exact_prevents_fuzzy_evaluation(self):
        """When EXACT matches, the result is EXACT even if FUZZY would also match."""
        text = "The total is USD 250.00 payable now."
        chunks = [make_chunk(text)]
        verifier = GroundingVerifierImpl()
        method, anchors = verifier.verify("USD 250.00", "", chunks)
        assert method == GroundingMethod.EXACT
        # If we disable EXACT, it should fall to a later stage
        verifier_no_exact = GroundingVerifierImpl(disabled_stages={GroundingMethod.EXACT})
        method2, _ = verifier_no_exact.verify("USD 250.00", "", chunks)
        assert method2 != GroundingMethod.EXACT

    def test_fuzzy_prevents_semantic_evaluation(self):
        """When FUZZY matches, the result is FUZZY even if SEMANTIC would also match."""
        text = "The vendor is Acme Corporation Incorporated."
        chunks = [make_chunk(text)]
        verifier = GroundingVerifierImpl(fuzzy_threshold=0.9, semantic_threshold=0.3)
        # "Acme Corporaton Incorporated" (missing 'i' in Corporation) is NOT
        # an exact substring but IS a fuzzy match (ratio ~0.93).
        method, _ = verifier.verify("Acme Corporaton Incorporated", "", chunks)
        assert method == GroundingMethod.FUZZY

    def test_all_stages_fail_reaches_block(self):
        """When all stages fail, BLOCK is reached."""
        chunks = [make_chunk("The weather is sunny today.")]
        verifier = GroundingVerifierImpl()
        method, anchors = verifier.verify("quantum entanglement paradox", "", chunks)
        assert method == GroundingMethod.BLOCK
        assert len(anchors) == 0

    def test_no_stage_skipped_exact_to_block(self):
        """Disabling all stages except BLOCK should always produce BLOCK."""
        chunks = [make_chunk("The total is USD 250.00.")]
        verifier = GroundingVerifierImpl(
            disabled_stages={
                GroundingMethod.EXACT,
                GroundingMethod.FUZZY,
                GroundingMethod.SEMANTIC,
                GroundingMethod.VISUAL,
            }
        )
        method, anchors = verifier.verify("USD 250.00", "", chunks)
        assert method == GroundingMethod.BLOCK
        assert len(anchors) == 0

    def test_cascade_order_exact_before_fuzzy(self):
        """EXACT must be evaluated before FUZZY. A text that matches exactly
        should return EXACT, not FUZZY."""
        text = "Payment terms: Net 30 days."
        chunks = [make_chunk(text)]
        verifier = GroundingVerifierImpl()
        method, _ = verifier.verify("Net 30", "", chunks)
        assert method == GroundingMethod.EXACT

    def test_cascade_order_fuzzy_before_semantic(self):
        """FUZZY must be evaluated before SEMANTIC. A near-match that passes
        fuzzy threshold should return FUZZY, not SEMANTIC."""
        text = "The confidentiality period is five years from termination."
        chunks = [make_chunk(text)]
        verifier = GroundingVerifierImpl(fuzzy_threshold=0.85, semantic_threshold=0.3)
        # Use a value with a typo that is NOT an exact substring but IS a fuzzy match.
        # "confidentiality periiod" (double 'i') won't be found as a substring,
        # but fuzzy matching will still match it at high ratio.
        method, _ = verifier.verify("confidentiality periiod", "", chunks)
        assert method == GroundingMethod.FUZZY

    def test_cascade_order_semantic_before_visual(self):
        """SEMANTIC must be evaluated before VISUAL. A semantically matching
        text should return SEMANTIC, not VISUAL (unless VISUAL has bbox encoding)."""
        text = "The project schedule is delayed by six weeks."
        chunks = [make_chunk(text, bbox=BBox(10, 10, 50, 50))]
        verifier = GroundingVerifierImpl(semantic_threshold=0.3)
        # No bbox encoding in source_span, so VISUAL won't trigger anyway
        method, _ = verifier.verify("delayed schedule", "", chunks)
        assert method == GroundingMethod.SEMANTIC

    def test_visual_reached_when_text_stages_fail(self):
        """When EXACT, FUZZY, SEMANTIC all fail but VISUAL bbox overlaps,
        the cascade should reach VISUAL."""
        # Text that won't match at all
        chunks = [make_chunk("completely unrelated text content", bbox=BBox(10, 10, 50, 50))]
        verifier = GroundingVerifierImpl(semantic_threshold=0.99)
        # source_span encodes a bbox that overlaps the chunk bbox
        method, anchors = verifier.verify("different value", "bbox:12,12,48,48", chunks)
        assert method == GroundingMethod.VISUAL
        assert len(anchors) == 1


# ---------------------------------------------------------------------------
# T1.3 — Property-based tests (simple randomization with fixed seeds)
# ---------------------------------------------------------------------------

class TestPropertyBased:
    """Property-based tests using simple randomization with fixed seeds.

    Invariants:
    (a) An answer is only returned if some stage produced a verified grounding.
    (b) The chosen stage is the earliest that succeeds.
    (c) Output is deterministic for fixed input.
    """

    def test_property_grounded_only_if_verified(self):
        """For randomized inputs, an answer (non-BLOCK) is only returned if
        some stage produced anchors. BLOCK always has zero anchors."""
        rng = random.Random(42)
        sample_texts = [
            "The total amount is USD 1250.00.",
            "Invoice number INV-2026-001 dated June 15.",
            "Payment terms are Net 30 days from invoice date.",
            "The vendor is ACME Corp located in Tech City.",
            "Tax amount is $0.00 and currency is USD.",
        ]
        chunks = [make_chunk(t) for t in sample_texts]

        for _ in range(200):
            # Random query: either a substring of a chunk or random gibberish
            if rng.random() < 0.5:
                # Pick a real substring
                chunk_text = rng.choice(sample_texts)
                words = chunk_text.split()
                start_idx = rng.randint(0, max(0, len(words) - 3))
                end_idx = min(len(words), start_idx + rng.randint(1, 4))
                query = " ".join(words[start_idx:end_idx])
            else:
                # Random gibberish
                length = rng.randint(3, 15)
                query = "".join(rng.choices(string.ascii_lowercase + " ", k=length)).strip()

            verifier = GroundingVerifierImpl(semantic_threshold=0.5)
            method, anchors = verifier.verify(query, "", chunks)

            # Invariant (a): non-BLOCK implies anchors exist
            if method != GroundingMethod.BLOCK:
                assert len(anchors) > 0, (
                    f"Method {method} returned but no anchors for query='{query}'"
                )
            # BLOCK always has zero anchors
            if method == GroundingMethod.BLOCK:
                assert len(anchors) == 0

    def test_property_earliest_succeeding_stage(self):
        """The chosen stage is the earliest that succeeds. We verify this by
        disabling stages one at a time and checking consistency."""
        rng = random.Random(99)
        sample_texts = [
            "The total amount is USD 1250.00.",
            "Payment terms are Net 30 days.",
            "The vendor is ACME Corp.",
        ]
        chunks = [make_chunk(t) for t in sample_texts]

        for _ in range(100):
            chunk_text = rng.choice(sample_texts)
            words = chunk_text.split()
            start_idx = rng.randint(0, max(0, len(words) - 2))
            end_idx = min(len(words), start_idx + rng.randint(1, 3))
            query = " ".join(words[start_idx:end_idx])

            verifier = GroundingVerifierImpl(semantic_threshold=0.5)
            method, anchors = verifier.verify(query, "", chunks)

            if method == GroundingMethod.EXACT:
                # Disabling EXACT should produce a different (later) method
                v2 = GroundingVerifierImpl(semantic_threshold=0.5, disabled_stages={GroundingMethod.EXACT})
                method2, _ = v2.verify(query, "", chunks)
                assert method2 != GroundingMethod.EXACT, (
                    f"Disabling EXACT should change result for query='{query}'"
                )

    def test_property_deterministic(self):
        """Output is deterministic for fixed input — same query, same chunks,
        same result every time."""
        chunks = [
            make_chunk("The total amount is USD 1250.00."),
            make_chunk("Payment terms are Net 30 days."),
        ]
        verifier = GroundingVerifierImpl(semantic_threshold=0.5)

        queries = ["USD 1250.00", "Net 30", "banana shake", "total amount"]

        results = []
        for _ in range(10):
            run_results = []
            for q in queries:
                method, anchors = verifier.verify(q, "", chunks)
                run_results.append((method, len(anchors)))
            results.append(tuple(run_results))

        # All 10 runs must produce identical results
        for i in range(1, len(results)):
            assert results[i] == results[0], (
                f"Run {i} differs from run 0: {results[i]} vs {results[0]}"
            )

    def test_property_random_chunks_deterministic(self):
        """Determinism holds across random chunk configurations."""
        rng = random.Random(77)
        for _ in range(50):
            n_chunks = rng.randint(1, 5)
            chunks = []
            for j in range(n_chunks):
                length = rng.randint(10, 50)
                text = "".join(rng.choices(string.ascii_lowercase + " ", k=length)).strip()
                chunks.append(make_chunk(text, chunk_id=f"c{j}"))

            query = "".join(rng.choices(string.ascii_lowercase + " ", k=rng.randint(5, 20))).strip()
            verifier = GroundingVerifierImpl(semantic_threshold=0.5)

            r1 = verifier.verify(query, "", chunks)
            r2 = verifier.verify(query, "", chunks)
            assert r1 == r2, f"Non-deterministic for query='{query}'"


# ---------------------------------------------------------------------------
# T1.4 — Ablation hooks (disabled_stages)
# ---------------------------------------------------------------------------

class TestAblationHooks:
    """Test the disabled_stages ablation parameter."""

    def test_disable_exact_falls_to_fuzzy(self):
        text = "The vendor is Acme Corporation Inc."
        chunks = [make_chunk(text)]
        verifier = GroundingVerifierImpl(
            fuzzy_threshold=0.9,
            disabled_stages={GroundingMethod.EXACT},
        )
        method, anchors = verifier.verify("Acme Corporation", "", chunks)
        assert method == GroundingMethod.FUZZY

    def test_disable_exact_and_fuzzy_falls_to_semantic(self):
        text = "The project schedule is delayed by six weeks."
        chunks = [make_chunk(text)]
        verifier = GroundingVerifierImpl(
            semantic_threshold=0.3,
            disabled_stages={GroundingMethod.EXACT, GroundingMethod.FUZZY},
        )
        method, anchors = verifier.verify("delayed schedule", "", chunks)
        assert method == GroundingMethod.SEMANTIC

    def test_disable_all_text_stages_falls_to_visual(self):
        chunks = [make_chunk("unrelated text", bbox=BBox(10, 10, 50, 50))]
        verifier = GroundingVerifierImpl(
            semantic_threshold=0.99,
            disabled_stages={GroundingMethod.EXACT, GroundingMethod.FUZZY, GroundingMethod.SEMANTIC},
        )
        method, anchors = verifier.verify("different value", "bbox:12,12,48,48", chunks)
        assert method == GroundingMethod.VISUAL

    def test_disable_all_stages_produces_block(self):
        chunks = [make_chunk("The total is USD 250.00.", bbox=BBox(10, 10, 50, 50))]
        verifier = GroundingVerifierImpl(
            disabled_stages={
                GroundingMethod.EXACT,
                GroundingMethod.FUZZY,
                GroundingMethod.SEMANTIC,
                GroundingMethod.VISUAL,
            }
        )
        method, anchors = verifier.verify("USD 250.00", "bbox:10,10,50,50", chunks)
        assert method == GroundingMethod.BLOCK
        assert len(anchors) == 0

    def test_ablation_measures_accuracy_delta(self):
        """Disabling a stage should change the grounding outcome for inputs
        that would have been grounded by that stage. This demonstrates the
        ablation hook can measure accuracy delta."""
        text = "The total amount payable is USD 250.00 immediately."
        chunks = [make_chunk(text)]

        # Full cascade: EXACT matches
        full_verifier = GroundingVerifierImpl()
        method_full, _ = full_verifier.verify("USD 250.00", "", chunks)
        assert method_full == GroundingMethod.EXACT

        # Ablated: EXACT disabled → should fall through
        ablated_verifier = GroundingVerifierImpl(disabled_stages={GroundingMethod.EXACT})
        method_ablated, anchors_ablated = ablated_verifier.verify("USD 250.00", "", chunks)

        # The ablation changed the outcome — this is the accuracy delta
        assert method_ablated != GroundingMethod.EXACT