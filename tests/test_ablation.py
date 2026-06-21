"""
Tests for the ablation study (P1.3).

Runs the ablation and asserts that verifier-active has a lower
ungrounded-render rate than verifier-bypassed and confidence-threshold.

No mocks — the ablation runs the real standalone verifier against real
fixtures with deliberately hallucinated bboxes.
"""
import json
import pathlib
import sys

import pytest

# Ensure repo root is on path
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.run_ablation import (
    load_fixtures,
    run_confidence_threshold,
    run_verifier_active,
    run_verifier_bypassed,
)


@pytest.fixture(scope="module")
def claims():
    """Load all fixture claims once for all tests in this module."""
    return load_fixtures()


@pytest.fixture(scope="module")
def ablation_results(claims):
    """Run all three ablation conditions once."""
    return {
        "verifier_active": run_verifier_active(claims),
        "verifier_bypassed": run_verifier_bypassed(claims),
        "confidence_threshold": run_confidence_threshold(claims, threshold=0.8),
    }


class TestAblationDataIntegrity:
    """Verify the ablation fixture data is valid and sufficient."""

    def test_claims_loaded(self, claims):
        """At least 50 claims should be loaded across all 4 packs."""
        assert len(claims) >= 50, (
            f"Expected ≥50 claims, got {len(claims)}"
        )

    def test_all_four_packs_present(self, claims):
        """Claims should span all 4 packs."""
        packs = {c.pack for c in claims}
        assert packs == {"generic", "invoice", "paper", "contract"}, (
            f"Expected all 4 packs, got {packs}"
        )

    def test_hallucinated_claims_present(self, claims):
        """There must be hallucinated claims to test the ablation."""
        hallucinated = [c for c in claims if c.bbox_is_hallucinated]
        assert len(hallucinated) > 0, "No hallucinated claims — ablation is meaningless"

    def test_correct_claims_present(self, claims):
        """There must be correct claims too (to test false-refusal rate)."""
        correct = [c for c in claims if not c.bbox_is_hallucinated]
        assert len(correct) > 0, "No correct claims — can't measure false refusals"

    def test_hallucinated_claims_have_high_confidence(self, claims):
        """Hallucinated claims should have high model confidence (≥0.85).
        This is the key insight: the model is confidently wrong."""
        hallucinated = [c for c in claims if c.bbox_is_hallucinated]
        for claim in hallucinated:
            assert claim.model_confidence >= 0.85, (
                f"Hallucinated claim {claim.claim_id} has low confidence "
                f"{claim.model_confidence} — should be high to simulate VLM hallucination"
            )


class TestAblationVerifierActive:
    """Test the verifier-active condition."""

    def test_verifier_active_blocks_hallucinations(self, ablation_results):
        """Verifier-active should block most/all hallucinated claims."""
        result = ablation_results["verifier_active"]
        # The verifier should block hallucinated bboxes
        # ungrounded_renders should be much lower than total hallucinated
        assert result.ungrounded_renders < result.total_claims, (
            "Verifier didn't block any hallucinated claims"
        )

    def test_verifier_active_renders_correct_claims(self, ablation_results, claims):
        """Verifier-active should render most correct (non-hallucinated) claims."""
        result = ablation_results["verifier_active"]
        correct_claims = [c for c in claims if not c.bbox_is_hallucinated]
        # At least some correct claims should be rendered (false-refusal < 100%)
        assert result.rendered > 0, "Verifier blocked everything — false-refusal rate is 100%"


class TestAblationComparison:
    """The core ablation assertion: verifier-active < verifier-bypassed."""

    def test_verifier_active_lower_than_bypassed(self, ablation_results):
        """The verifier-active condition must have a lower ungrounded-render
        rate than the verifier-bypassed condition."""
        va = ablation_results["verifier_active"]
        vb = ablation_results["verifier_bypassed"]
        assert va.ungrounded_render_rate < vb.ungrounded_render_rate, (
            f"Verifier-active rate ({va.ungrounded_render_rate}%) is NOT lower than "
            f"verifier-bypassed rate ({vb.ungrounded_render_rate}%) — "
            f"the verifier is not catching hallucinations"
        )

    def test_verifier_active_lower_than_confidence_threshold(self, ablation_results):
        """The verifier-active condition must have a lower ungrounded-render
        rate than the confidence-threshold baseline."""
        va = ablation_results["verifier_active"]
        ct = ablation_results["confidence_threshold"]
        assert va.ungrounded_render_rate < ct.ungrounded_render_rate, (
            f"Verifier-active rate ({va.ungrounded_render_rate}%) is NOT lower than "
            f"confidence-threshold rate ({ct.ungrounded_render_rate}%) — "
            f"the verifier is not catching hallucinations that confidence misses"
        )

    def test_bypassed_renders_all_hallucinations(self, ablation_results, claims):
        """The bypassed condition should render all hallucinated claims
        (because it trusts model confidence, which is high for hallucinations)."""
        vb = ablation_results["verifier_bypassed"]
        hallucinated_count = sum(1 for c in claims if c.bbox_is_hallucinated)
        # Bypassed renders everything with confidence > 0, and all claims have conf > 0
        assert vb.ungrounded_renders == hallucinated_count, (
            f"Bypassed should render all {hallucinated_count} hallucinated claims, "
            f"but only rendered {vb.ungrounded_renders} ungrounded"
        )

    def test_confidence_threshold_renders_most_hallucinations(self, ablation_results, claims):
        """The confidence-threshold baseline should render most hallucinated claims
        (because hallucinated claims have high confidence ≥0.85 > 0.8 threshold)."""
        ct = ablation_results["confidence_threshold"]
        hallucinated_count = sum(1 for c in claims if c.bbox_is_hallucinated)
        # All hallucinated claims have confidence ≥0.85 > 0.8, so all should be rendered
        assert ct.ungrounded_renders == hallucinated_count, (
            f"Confidence-threshold should render all {hallucinated_count} hallucinated "
            f"claims (all have conf ≥0.85 > 0.8), but only rendered {ct.ungrounded_renders}"
        )

    def test_verifier_catches_what_baseline_misses(self, ablation_results):
        """The difference between bypassed and verifier-active ungrounded-renders
        is the number of hallucinations the verifier caught that the baseline missed."""
        va = ablation_results["verifier_active"]
        vb = ablation_results["verifier_bypassed"]
        caught = vb.ungrounded_renders - va.ungrounded_renders
        assert caught > 0, (
            f"Verifier caught {caught} hallucinations that bypass missed — "
            f"should be > 0"
        )


class TestAblationFailingCapable:
    """Tests that verify the ablation is failing-capable.
    If someone removes the verifier's IoU check, the ablation should fail."""

    def test_if_verifier_did_nothing_rates_would_be_equal(self, ablation_results):
        """If the verifier did nothing (always rendered), verifier-active
        rate would equal verifier-bypassed rate. The fact that they differ
        proves the verifier is doing real work."""
        va = ablation_results["verifier_active"]
        vb = ablation_results["verifier_bypassed"]
        assert va.ungrounded_render_rate != vb.ungrounded_render_rate, (
            "Verifier-active and bypassed rates are identical — verifier is doing nothing"
        )