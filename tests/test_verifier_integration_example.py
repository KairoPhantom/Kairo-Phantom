"""
Tests for X2 — Verifier Crate Integration Example

Tests that the 10-line integration example from docs/VERIFIER_CRATE_RELEASE.md
works correctly. The verifier must:
1. Ground real citations (return EXACT/FUZZY/SEMANTIC)
2. Block hallucinated citations (return BLOCK)
3. Work with any chunks from any RAG pipeline
4. Return correct anchors with bbox information
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kernel.core.grounding import GroundingVerifierImpl
from kernel.core.data_model import Chunk, BBox, GroundingMethod, Anchor


# ---------------------------------------------------------------------------
# The 10-line integration example (from VERIFIER_CRATE_RELEASE.md)
# ---------------------------------------------------------------------------
def run_integration_example(value, source_span, chunks):
    """This is the exact 10-line integration example from the docs.

    1. Initialize the verifier
    2. Prepare your source chunks
    3. Verify a citation
    4. If BLOCK, refuse; otherwise show the grounded answer
    """
    # 1. Initialize the verifier
    verifier = GroundingVerifierImpl()

    # 2. (chunks are passed in)

    # 3. Verify a citation from your LLM's answer
    method, anchors = verifier.verify(
        value=value,
        source_span=source_span,
        chunks=chunks,
    )

    # 4. If method == BLOCK, the citation is hallucinated — refuse to show it
    if method.name == "BLOCK":
        return "REFUSED: citation not grounded in source", method, anchors
    else:
        return f"Grounded via {method.name}: {anchors[0].bbox}", method, anchors


# ---------------------------------------------------------------------------
# Fixtures: realistic chunks from a RAG pipeline
# ---------------------------------------------------------------------------
def make_contract_chunks():
    """Simulate chunks retrieved by a RAG pipeline from a contract document."""
    return [
        Chunk(
            chunk_id="chunk_001",
            doc_id="contract_01",
            page=1,
            bbox=BBox(0.1, 0.05, 0.9, 0.15),
            text="This Agreement is governed by the laws of the State of Delaware.",
        ),
        Chunk(
            chunk_id="chunk_002",
            doc_id="contract_01",
            page=1,
            bbox=BBox(0.1, 0.20, 0.9, 0.30),
            text="The license fees shall be paid within 30 days of invoice.",
        ),
        Chunk(
            chunk_id="chunk_003",
            doc_id="contract_01",
            page=2,
            bbox=BBox(0.1, 0.05, 0.9, 0.15),
            text="This Agreement terminates on June 1, 2029.",
        ),
    ]


# ---------------------------------------------------------------------------
# Test 1: The integration example grounds real citations
# ---------------------------------------------------------------------------
class TestIntegrationExampleGroundsRealCitations:
    """The 10-line example must correctly ground real citations."""

    def test_grounds_delaware_governing_law(self):
        """A real citation (Delaware) must be grounded."""
        chunks = make_contract_chunks()
        result, method, anchors = run_integration_example(
            value="Delaware",
            source_span="Delaware",
            chunks=chunks,
        )

        assert method != GroundingMethod.BLOCK, "Real citation must not be blocked"
        assert "Grounded" in result, "Result must indicate grounding"
        assert len(anchors) == 1, "Must return exactly one anchor"
        assert anchors[0].page == 1, "Anchor must be on page 1"
        assert anchors[0].bbox is not None, "Anchor must have a bbox"

    def test_grounds_payment_terms(self):
        """A real citation (within 30 days) must be grounded."""
        chunks = make_contract_chunks()
        result, method, anchors = run_integration_example(
            value="within 30 days",
            source_span="within 30 days of invoice",
            chunks=chunks,
        )

        assert method != GroundingMethod.BLOCK, "Real citation must not be blocked"
        assert len(anchors) >= 1

    def test_grounds_termination_date(self):
        """A real citation (June 1, 2029) must be grounded."""
        chunks = make_contract_chunks()
        result, method, anchors = run_integration_example(
            value="June 1, 2029",
            source_span="June 1, 2029",
            chunks=chunks,
        )

        assert method != GroundingMethod.BLOCK, "Real citation must not be blocked"
        assert anchors[0].page == 2, "Termination date is on page 2"


# ---------------------------------------------------------------------------
# Test 2: The integration example blocks hallucinated citations
# ---------------------------------------------------------------------------
class TestIntegrationExampleBlocksHallucinations:
    """The 10-line example must block hallucinated citations."""

    def test_blocks_fabricated_value(self):
        """A fabricated value not in the source must be blocked."""
        chunks = make_contract_chunks()
        result, method, anchors = run_integration_example(
            value="$5,000,000",
            source_span="$5,000,000",
            chunks=chunks,
        )

        assert method == GroundingMethod.BLOCK, "Hallucinated citation must be blocked"
        assert "REFUSED" in result, "Result must indicate refusal"
        assert len(anchors) == 0, "No anchors for blocked citation"

    def test_blocks_wrong_attribution(self):
        """A value that exists but is attributed to the wrong context must be blocked."""
        chunks = make_contract_chunks()
        # "California" is not in the document — the governing law is Delaware
        result, method, anchors = run_integration_example(
            value="California",
            source_span="California",
            chunks=chunks,
        )

        assert method == GroundingMethod.BLOCK, "Wrong attribution must be blocked"

    def test_blocks_completely_unrelated_text(self):
        """Completely unrelated text must be blocked."""
        chunks = make_contract_chunks()
        result, method, anchors = run_integration_example(
            value="The moon is made of cheese",
            source_span="The moon is made of cheese",
            chunks=chunks,
        )

        assert method == GroundingMethod.BLOCK, "Unrelated text must be blocked"


# ---------------------------------------------------------------------------
# Test 3: The verifier works with any chunks (model-independent)
# ---------------------------------------------------------------------------
class TestVerifierModelIndependent:
    """The verifier must work with chunks from any source."""

    def test_works_with_single_chunk(self):
        """Verifier works with a single chunk."""
        chunks = [Chunk(
            chunk_id="c1", doc_id="d1", page=1,
            bbox=BBox(0, 0, 1, 1),
            text="The answer is 42.",
        )]
        result, method, anchors = run_integration_example(
            value="42", source_span="42", chunks=chunks,
        )
        assert method != GroundingMethod.BLOCK

    def test_works_with_many_chunks(self):
        """Verifier works with many chunks."""
        chunks = [
            Chunk(chunk_id=f"c{i}", doc_id="d1", page=i+1,
                  bbox=BBox(0, 0, 1, 1),
                  text=f"Page {i+1} content with keyword_{i}.")
            for i in range(20)
        ]
        result, method, anchors = run_integration_example(
            value="keyword_10", source_span="keyword_10", chunks=chunks,
        )
        assert method != GroundingMethod.BLOCK
        assert anchors[0].page == 11, "Must find the correct page"

    def test_works_with_empty_chunks(self):
        """Verifier returns BLOCK for empty chunks list."""
        result, method, anchors = run_integration_example(
            value="anything", source_span="anything", chunks=[],
        )
        assert method == GroundingMethod.BLOCK


# ---------------------------------------------------------------------------
# Test 4: Anchor correctness
# ---------------------------------------------------------------------------
class TestAnchorCorrectness:
    """Anchors must contain correct source localization info."""

    def test_anchor_has_chunk_id(self):
        """Anchor must reference the correct chunk."""
        chunks = make_contract_chunks()
        _, method, anchors = run_integration_example(
            value="Delaware", source_span="Delaware", chunks=chunks,
        )
        assert anchors[0].chunk_id == "chunk_001"

    def test_anchor_has_bbox(self):
        """Anchor must have a bbox."""
        chunks = make_contract_chunks()
        _, method, anchors = run_integration_example(
            value="Delaware", source_span="Delaware", chunks=chunks,
        )
        assert anchors[0].bbox is not None
        assert isinstance(anchors[0].bbox, BBox)

    def test_anchor_has_page(self):
        """Anchor must have the correct page number."""
        chunks = make_contract_chunks()
        _, method, anchors = run_integration_example(
            value="June 1, 2029", source_span="June 1, 2029", chunks=chunks,
        )
        assert anchors[0].page == 2

    def test_anchor_has_char_span(self):
        """Anchor must have a character span."""
        chunks = make_contract_chunks()
        _, method, anchors = run_integration_example(
            value="Delaware", source_span="Delaware", chunks=chunks,
        )
        assert anchors[0].char_span[0] >= 0
        assert anchors[0].char_span[1] > anchors[0].char_span[0]


# ---------------------------------------------------------------------------
# Test 5: LangChain-style integration pattern
# ---------------------------------------------------------------------------
class TestLangChainStyleIntegration:
    """Test the LangChain integration pattern from the docs."""

    def test_verified_generate_blocks_hallucination(self):
        """The verified_generate pattern blocks hallucinated answers."""
        chunks = make_contract_chunks()
        verifier = GroundingVerifierImpl()

        def verified_generate(query, retrieved_chunks, answer, citation_text):
            """LangChain-style: verify after generation."""
            method, anchors = verifier.verify(citation_text, citation_text, retrieved_chunks)
            if method.name == "BLOCK":
                return "I cannot ground this answer to the source document."
            return answer

        # Real citation — should pass
        result = verified_generate(
            "What is the governing law?",
            chunks,
            "The governing law is Delaware.",
            "Delaware",
        )
        assert "Delaware" in result, "Real citation should pass through"

        # Hallucinated citation — should be blocked
        result = verified_generate(
            "What is the contract value?",
            chunks,
            "The contract value is $5,000,000.",
            "$5,000,000",
        )
        assert "cannot ground" in result, "Hallucinated citation should be blocked"
        assert "$5,000,000" not in result, "Hallucinated value must not appear in output"