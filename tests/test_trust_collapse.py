"""
T2 — Trust-collapse hard-fail tests.

Specific high-value questions that must NOT be falsely refused.
If any of these are falsely refused, CI fails HARD.
"""

import json
import os
from pathlib import Path

import pytest

from kernel.core.data_model import BBox, Chunk, GroundingMethod
from kernel.core.grounding import GroundingVerifierImpl

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
TRUST_CASES_PATH = FIXTURES_DIR / "trust_collapse_cases.json"
CORPUS_DIR = FIXTURES_DIR / "labeled_corpus"


def load_trust_cases() -> dict:
    with open(TRUST_CASES_PATH) as f:
        return json.load(f)


def text_to_chunks(text: str, doc_id: str = "doc1") -> list[Chunk]:
    """Convert document text into chunks with bounding boxes."""
    lines = [l for l in text.split("\n") if l.strip()]
    chunks = []
    for i, line in enumerate(lines):
        y0 = float(i * 20)
        y1 = float((i + 1) * 20)
        chunks.append(Chunk(
            chunk_id=f"{doc_id}_c{i}",
            doc_id=doc_id,
            page=1,
            bbox=BBox(0, y0, 500, y1),
            text=line,
        ))
    return chunks


class TestTrustCollapse:
    """Trust-collapse cases: if any of these are falsely refused, CI fails hard."""

    @pytest.fixture
    def verifier(self):
        return GroundingVerifierImpl(
            fuzzy_threshold=0.85,
            semantic_threshold=0.3,
        )

    @pytest.fixture
    def trust_cases(self):
        return load_trust_cases()

    def test_all_trust_cases_grounded(self, verifier, trust_cases):
        """Every trust-collapse case must be grounded (not refused).
        A false refusal on any of these is a trust collapse."""
        failures = []

        for case in trust_cases["cases"]:
            doc_path = CORPUS_DIR / case["document"]
            assert doc_path.exists(), f"Trust collapse document not found: {doc_path}"

            with open(doc_path) as f:
                text = f.read()
            chunks = text_to_chunks(text, doc_id=case["document"])

            method, anchors = verifier.verify(
                case["expected_answer"],
                case["source_span"],
                chunks,
            )

            is_grounded = method != GroundingMethod.BLOCK and len(anchors) > 0

            if not is_grounded:
                failures.append({
                    "id": case["id"],
                    "question": case["question"],
                    "expected": case["expected_answer"],
                    "source_span": case["source_span"],
                    "method": method.value,
                    "reason": case["reason"],
                })

        if failures:
            failure_report = "\n".join(
                f"  TRUST COLLAPSE: {f['id']} — q='{f['question']}' "
                f"expected='{f['expected']}' method={f['method']}\n"
                f"    reason: {f['reason']}"
                for f in failures
            )
            pytest.fail(
                f"{len(failures)} trust-collapse case(s) were falsely refused:\n{failure_report}"
            )

    @pytest.mark.parametrize("case_id", [
        "tc_invoice_total",
        "tc_notice_period_crossref",
        "tc_figure_caption_finding",
    ])
    def test_individual_trust_collapse_case(self, verifier, trust_cases, case_id):
        """Each critical trust-collapse case is tested individually for clear
        CI failure reporting."""
        case = next(c for c in trust_cases["cases"] if c["id"] == case_id)
        doc_path = CORPUS_DIR / case["document"]

        with open(doc_path) as f:
            text = f.read()
        chunks = text_to_chunks(text, doc_id=case["document"])

        method, anchors = verifier.verify(
            case["expected_answer"],
            case["source_span"],
            chunks,
        )

        assert method != GroundingMethod.BLOCK, (
            f"TRUST COLLAPSE: {case_id} — '{case['question']}' was falsely refused. "
            f"Expected answer '{case['expected_answer']}' should be grounded. "
            f"Reason: {case['reason']}"
        )
        assert len(anchors) > 0, (
            f"TRUST COLLAPSE: {case_id} — no anchors returned for grounded answer"
        )

    def test_poor_ocr_trust_case(self, verifier, trust_cases):
        """Poor OCR invoice total must not be falsely refused — fuzzy matching
        must handle OCR degradation."""
        case = next(c for c in trust_cases["cases"] if c["id"] == "tc_poor_ocr_total")
        doc_path = CORPUS_DIR / case["document"]

        with open(doc_path) as f:
            text = f.read()
        chunks = text_to_chunks(text, doc_id=case["document"])

        method, anchors = verifier.verify(
            case["expected_answer"],
            case["source_span"],
            chunks,
        )

        assert method != GroundingMethod.BLOCK, (
            f"TRUST COLLAPSE: Poor OCR invoice total was falsely refused. "
            f"Fuzzy matching must handle OCR degradation."
        )