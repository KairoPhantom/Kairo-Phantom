"""
Kairo Phantom — Quality Gate (SPEC §S4 line 6)

Checks extraction quality: grounding, correction history, calibrated confidence.
Routes low-confidence (< 0.5) to human_review (FLAG).
Very low confidence (< 0.2) → BLOCK.

The kernel imports NOTHING from /domains or /legacy.
"""

from __future__ import annotations

from typing import Final, Protocol, runtime_checkable

from kernel.core.contracts import GateResult, GateVerdict
from kernel.core.data_model import Correction, Extraction, GroundingMethod


# ---------------------------------------------------------------------------
# Minimal MemoryStore interface needed by QualityGate
# ---------------------------------------------------------------------------
@runtime_checkable
class CorrectionLookup(Protocol):
    """Subset of MemoryStore that QualityGate depends on."""

    def search_similar_corrections(
        self, field_name: str, value: str, k: int = 5
    ) -> list[Correction]: ...


# ---------------------------------------------------------------------------
# Confidence thresholds
# ---------------------------------------------------------------------------
_FLAG_THRESHOLD: Final[float] = 0.5
_BLOCK_THRESHOLD: Final[float] = 0.2


# ---------------------------------------------------------------------------
# QualityGate implementation
# ---------------------------------------------------------------------------
class LocalQualityGate:
    """Extraction quality gate implementing the QualityGate Protocol.

    1. Grounding check — value must be traceable to a chunk (has chunk_id).
    2. Correction calibration — prior corrections lower confidence.
    3. Confidence routing — low → FLAG, very low → BLOCK.
    """

    def __init__(
        self,
        correction_store: CorrectionLookup,
        *,
        flag_threshold: float = _FLAG_THRESHOLD,
        block_threshold: float = _BLOCK_THRESHOLD,
    ) -> None:
        if block_threshold >= flag_threshold:
            raise ValueError(
                f"block_threshold ({block_threshold}) must be < "
                f"flag_threshold ({flag_threshold})"
            )
        self._correction_store = correction_store
        self._flag_threshold = flag_threshold
        self._block_threshold = block_threshold

    def check(self, extraction: Extraction) -> GateResult:
        """Check extraction quality and return a verdict."""
        reasons: list[str] = []
        confidence = extraction.confidence

        # 1. Grounding check: chunk_id must be non-empty, method must not be BLOCK, and anchors must be resolved
        if (
            not extraction.chunk_id or
            not extraction.chunk_id.strip() or
            extraction.method == GroundingMethod.BLOCK or
            not extraction.anchors
        ):
            reasons.append(
                "UNGROUNDED: extraction has no chunk_id, has grounding method BLOCK, or has no anchors — "
                "value is not traceable to source."
            )
            # Ungrounded extraction gets a major penalty
            confidence = min(confidence, self._block_threshold - 0.01)

        # 2. Correction calibration
        confidence = self._calibrate_with_corrections(
            extraction, confidence, reasons
        )

        # 3. Clamp to [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        # 4. Route by confidence
        verdict = self._route_verdict(confidence, reasons)

        return GateResult(
            verdict=verdict,
            calibrated_confidence=round(confidence, 4),
            reasons=reasons,
        )

    def _calibrate_with_corrections(
        self,
        extraction: Extraction,
        confidence: float,
        reasons: list[str],
    ) -> float:
        """Consult correction history and lower confidence for contradictions."""
        corrections = self._correction_store.search_similar_corrections(
            field_name=extraction.field_name,
            value=extraction.value,
            k=5,
        )

        if not corrections:
            return confidence

        # Each contradicting correction lowers confidence
        penalty_per_correction: Final[float] = 0.15
        contradictions = 0

        for corr in corrections:
            if corr.corrected != extraction.value:
                contradictions += 1
                reasons.append(
                    f"CORRECTION_CONFLICT: prior correction "
                    f"(corr_id={corr.corr_id}) changed "
                    f"'{corr.original}' → '{corr.corrected}', "
                    f"but current value is '{extraction.value}'."
                )

        if contradictions > 0:
            total_penalty = contradictions * penalty_per_correction
            confidence -= total_penalty
            reasons.append(
                f"CONFIDENCE_LOWERED: {contradictions} contradicting "
                f"correction(s), penalty={total_penalty:.2f}."
            )

        return confidence

    def _route_verdict(
        self, confidence: float, reasons: list[str]
    ) -> GateVerdict:
        """Route to PASS/FLAG/BLOCK based on calibrated confidence."""
        if confidence < self._block_threshold:
            reasons.append(
                f"VERDICT_BLOCK: confidence {confidence:.4f} < "
                f"block_threshold {self._block_threshold}."
            )
            return GateVerdict.BLOCK

        if confidence < self._flag_threshold:
            reasons.append(
                f"VERDICT_FLAG: confidence {confidence:.4f} < "
                f"flag_threshold {self._flag_threshold}. "
                f"Routing to human_review."
            )
            return GateVerdict.FLAG

        return GateVerdict.PASS
