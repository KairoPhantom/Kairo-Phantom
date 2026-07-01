"""
FROZEN TEST — Ask Your Docs (PDF) End-to-End

This test is HUMAN-AUTHORED and FROZEN. The agent may NOT edit this file.
It tests the real flagship feature: drop in a PDF → ask a question →
get a correct answer with a citation to the source page. Fully OFFLINE.

Gates:
  pytest -k ask_your_docs_pdf                  # correct answer + correct citation
  KAIRO_NO_NET=1 pytest -k ask_your_docs_pdf   # whole flow works offline

The test uses a real sample PDF (tests/e2e/fixtures/sample_docintel.pdf)
containing an Acme Corporation annual report with known facts on known pages.

Ground truth:
  Q: "What was the total revenue in fiscal year 2025?"
  A: must contain "$42.7 million"
  Citation: page 1

  Q: "How many full-time employees does Acme Corporation have?"
  A: must contain "187"
  Citation: page 1

  Q: "Who founded Acme Corporation?"
  A: must contain "Elena Vasquez"
  Citation: page 1

NO MOCKS. The answer must come from the real PDF through the real pipeline.
"""

import os
import sys
import pathlib

import pytest

# Ensure the repo root is on sys.path
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from kairo.docintel.ingest import PdfIngestor, IngestError
from kairo.docintel.retrieval import RetrievalIndex
from kairo.docintel.ask import DocIntelSession, AskResult

FIXTURE_PDF = REPO_ROOT / "tests" / "e2e" / "fixtures" / "sample_docintel.pdf"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ingested_doc():
    """Ingest the sample PDF once for all tests in this module."""
    ingestor = PdfIngestor()
    result = ingestor.ingest(str(FIXTURE_PDF))
    assert result.page_count == 3, f"Expected 3 pages, got {result.page_count}"
    assert len(result.chunks) > 0, "No chunks extracted from PDF"
    return result


@pytest.fixture(scope="module")
def docintel_session(ingested_doc):
    """Build a retrieval index and session from the ingested PDF."""
    index = RetrievalIndex()
    index.add_document(ingested_doc)
    session = DocIntelSession(
        index,
        page_texts=ingested_doc.page_texts,
    )
    return session


# ---------------------------------------------------------------------------
# Ground-truth test cases: (question, expected_answer_substring, expected_page)
# ---------------------------------------------------------------------------

GROUND_TRUTH = [
    (
        "What was the total revenue in fiscal year 2025?",
        "$42.7 million",
        1,
    ),
    (
        "How many full-time employees does Acme Corporation have?",
        "187",
        1,
    ),
    (
        "Who founded Acme Corporation?",
        "Elena Vasquez",
        1,
    ),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAskYourDocsPdf:
    """End-to-end test: PDF → question → correct answer + citation."""

    @pytest.mark.parametrize("question,expected_answer,expected_page", GROUND_TRUTH)
    def test_correct_answer_with_citation(
        self, docintel_session, question, expected_answer, expected_page
    ):
        """Each question must get a correct answer with a correct page citation."""
        result = docintel_session.ask(question)

        # Must not be refused
        assert not result.refused, (
            f"Question was refused: {result.refusal_reason}"
        )

        # Answer must contain the expected substring (case-insensitive)
        assert expected_answer.lower() in result.answer.lower(), (
            f"Expected '{expected_answer}' in answer, got: '{result.answer[:200]}'"
        )

        # Must have a citation
        assert result.citation is not None, "No citation provided"

        # Citation must point to the correct page
        assert result.citation.page == expected_page, (
            f"Expected citation page {expected_page}, got {result.citation.page}"
        )

        # Citation must have a valid bbox
        assert result.citation.bbox is not None
        assert len(result.citation.bbox) == 4

        # Citation must have source text
        assert result.citation.source_text, "Citation has no source text"

    def test_offline_mode_works(self, ingested_doc):
        """The entire flow must work with KAIRO_NO_NET=1 (no network)."""
        os.environ["KAIRO_NO_NET"] = "1"

        index = RetrievalIndex()
        index.add_document(ingested_doc)
        session = DocIntelSession(index, page_texts=ingested_doc.page_texts)

        result = session.ask("What was the total revenue in fiscal year 2025?")

        assert not result.refused, f"Offline answer refused: {result.refusal_reason}"
        assert "$42.7 million" in result.answer.lower() or "42.7" in result.answer
        assert result.citation is not None
        assert result.citation.page == 1

        # Clean up
        del os.environ["KAIRO_NO_NET"]

    def test_bad_file_returns_typed_error(self):
        """A missing file must raise IngestError, not crash."""
        ingestor = PdfIngestor()
        with pytest.raises(IngestError) as exc_info:
            ingestor.ingest("nonexistent_file.pdf")

        assert exc_info.value.recoverable is False
        assert "not found" in exc_info.value.reason.lower()

    def test_non_pdf_returns_typed_error(self, tmp_path):
        """A non-PDF file must raise IngestError with a clear reason."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello world")

        ingestor = PdfIngestor()
        with pytest.raises(IngestError) as exc_info:
            ingestor.ingest(str(txt_file))

        assert ".pdf" in exc_info.value.reason.lower()

    def test_refusal_on_unrelated_question(self, docintel_session):
        """A question completely unrelated to the document should be refused."""
        result = docintel_session.ask(
            "What is the capital of France?"
        )
        # Either refused or the answer doesn't contain "Paris"
        if not result.refused:
            assert "paris" not in result.answer.lower(), (
                "Should not answer questions unrelated to the document"
            )