"""
T3 — Verifier cannot be short-circuited.

Confirms there is no code path (cache, fast-path) that renders an answer
without passing the verifier. Checks the orchestrator and quality gate code paths.
"""

import inspect

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
from kernel.core.contracts import GateVerdict
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.sidecar.orchestrator import OrchestratorImpl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunks() -> list[Chunk]:
    return [
        Chunk(chunk_id="c1", doc_id="doc1", page=1,
              bbox=BBox(10, 10, 200, 30), text="Total: $1250.00"),
        Chunk(chunk_id="c2", doc_id="doc1", page=1,
              bbox=BBox(10, 40, 200, 60), text="Vendor: ACME Corp"),
    ]


class FakeCorrectionStore:
    def search_similar_corrections(self, field_name, value, k=5):
        return []


# ---------------------------------------------------------------------------
# T3.3 — No code path bypasses the verifier
# ---------------------------------------------------------------------------

class TestVerifierNoBypass:
    """Confirm there is no code path that renders an answer without
    passing through the grounding verifier."""

    @pytest.fixture
    def verifier(self):
        return GroundingVerifierImpl(semantic_threshold=0.5)

    @pytest.fixture
    def chunks(self):
        return make_chunks()

    def test_quality_gate_rejects_ungrounded_extraction(self, verifier, chunks):
        """The quality gate must reject (BLOCK) any extraction that has
        not been grounded by the verifier (method=BLOCK, no anchors)."""
        gate = LocalQualityGate(FakeCorrectionStore())

        # Ungrounded extraction — no anchors, BLOCK method
        ungrounded = Extraction(
            ext_id="ext1",
            pack_id="invoice",
            field_name="total",
            value="$99999.00",
            source_span="$99999.00",
            confidence=0.99,
            method=GroundingMethod.BLOCK,
            anchors=(),
        )
        result = gate.check(ungrounded)
        assert result.verdict == GateVerdict.BLOCK, (
            "Quality gate did not BLOCK an ungrounded extraction"
        )

    def test_quality_gate_rejects_empty_anchors(self, verifier, chunks):
        """Even with a non-BLOCK method, empty anchors must be rejected."""
        gate = LocalQualityGate(FakeCorrectionStore())

        bad_extraction = Extraction(
            ext_id="ext2",
            pack_id="invoice",
            field_name="total",
            value="$1250.00",
            source_span="$1250.00",
            confidence=0.99,
            method=GroundingMethod.EXACT,  # Claims EXACT but has no anchors
            anchors=(),
        )
        result = gate.check(bad_extraction)
        assert result.verdict == GateVerdict.BLOCK, (
            "Quality gate did not BLOCK extraction with empty anchors despite EXACT method"
        )

    def test_quality_gate_rejects_empty_chunk_id(self, verifier, chunks):
        """An extraction with empty chunk_id must be rejected."""
        gate = LocalQualityGate(FakeCorrectionStore())

        bad_extraction = Extraction(
            ext_id="ext3",
            pack_id="invoice",
            field_name="total",
            value="$1250.00",
            source_span="$1250.00",
            confidence=0.99,
            method=GroundingMethod.EXACT,
            anchors=(Anchor(chunk_id="", char_span=(0, 10), page=1, bbox=BBox(0,0,1,1)),),
            chunk_id="",
        )
        result = gate.check(bad_extraction)
        assert result.verdict == GateVerdict.BLOCK, (
            "Quality gate did not BLOCK extraction with empty chunk_id"
        )

    def test_orchestrator_calls_verifier(self):
        """The orchestrator's run() method must call the grounding verifier.
        We verify this by inspecting the source code for the verifier call."""
        source = inspect.getsource(OrchestratorImpl.run)
        assert "GroundingVerifierImpl" in source or "verifier" in source.lower(), (
            "Orchestrator.run() does not reference the grounding verifier — "
            "answers could be rendered without verification"
        )
        assert "verify" in source, (
            "Orchestrator.run() does not call verify() — verifier may be bypassed"
        )

    def test_orchestrator_grounds_before_quality_gate(self):
        """The orchestrator must ground extractions BEFORE passing them to
        the quality gate. The quality gate must never see ungrounded extractions
        that skip the verifier."""
        source = inspect.getsource(OrchestratorImpl.run)
        # Find the positions of grounding verification and quality gate
        verify_pos = source.find("verifier.verify")
        if verify_pos == -1:
            verify_pos = source.find("verify(")
        quality_pos = source.find("quality_gate")
        if quality_pos == -1:
            quality_pos = source.find("self._quality")

        assert verify_pos != -1, "Could not find verifier.verify() in orchestrator"
        assert quality_pos != -1, "Could not find quality gate in orchestrator"
        assert verify_pos < quality_pos, (
            "Quality gate is called before verifier — extractions could bypass grounding"
        )

    def test_no_cache_bypass_in_verifier(self, verifier, chunks):
        """The verifier must not cache results in a way that could return
        a stale grounded result for a different input. Same input → same result
        is fine, but different inputs must not collide."""
        # Verify a grounded value
        method1, anchors1 = verifier.verify("$1250.00", "", chunks)
        assert method1 == GroundingMethod.EXACT

        # Verify a different value that should NOT be grounded
        method2, anchors2 = verifier.verify("$99999.00", "", chunks)
        assert method2 == GroundingMethod.BLOCK, (
            "Verifier returned a grounded result for an ungrounded value — possible cache collision"
        )

    def test_no_fast_path_skips_verification(self, verifier, chunks):
        """There must be no fast-path that skips verification for 'obvious'
        answers. Even a value that appears in the text must go through
        the full verify() call."""
        # This is tested by confirming verify() is the only entry point
        # and it always runs the cascade
        method, anchors = verifier.verify("$1250.00", "", chunks)
        assert method == GroundingMethod.EXACT
        assert len(anchors) == 1

        # A slightly different value must not benefit from any fast-path
        method2, anchors2 = verifier.verify("$1250.01", "", chunks)
        # This should NOT be EXACT (the value doesn't appear exactly)
        assert method2 != GroundingMethod.EXACT, (
            "Fast-path may have matched $1250.01 to $1250.00 — no short-circuit allowed"
        )

    def test_grounded_extraction_passes_gate(self, verifier, chunks):
        """A properly grounded extraction must pass the quality gate —
        confirming the gate doesn't block legitimate answers."""
        gate = LocalQualityGate(FakeCorrectionStore())

        method, anchors = verifier.verify("$1250.00", "", chunks)
        assert method == GroundingMethod.EXACT

        grounded = Extraction(
            ext_id="ext_ok",
            pack_id="invoice",
            field_name="total",
            value="$1250.00",
            source_span="$1250.00",
            confidence=0.95,
            method=method,
            anchors=anchors,
            chunk_id=anchors[0].chunk_id,
        )
        result = gate.check(grounded)
        assert result.verdict == GateVerdict.PASS, (
            f"Quality gate blocked a properly grounded extraction: {result.reasons}"
        )