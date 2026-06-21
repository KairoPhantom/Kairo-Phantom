"""
T8 — Refusal diagnostic UX: assert every refusal payload contains
label + stage + suggestion — never an empty/blank response.
Also asserts a log entry is written for every refusal (audit trail).

No mocks: uses the real Answer dataclass and refusal.format_refusal().
"""
import logging
import io

import pytest

from kernel.core.data_model import Answer
from kernel.core.refusal import (
    format_refusal,
    get_refusal_metadata,
    log_refusal,
)


class TestRefusalDiagnostic:
    """Every refusal must have label + stage + suggestion, never blank."""

    def test_refusal_with_block_stage(self):
        """A BLOCK-stage refusal must produce a full diagnostic message."""
        answer = Answer(
            query="What is the tax rate?",
            text="",
            grounded=False,
            refused=True,
            refusal_stage="BLOCK",
            refusal_reason="no exact/fuzzy/semantic/visual match above threshold",
            refusal_suggestion="The answer may not be in this document.",
        )
        msg = format_refusal(answer)
        assert "No grounded source found" in msg, "Missing label"
        assert "BLOCK" in msg, "Missing stage name"
        assert "The answer may not be in this document" in msg, "Missing suggestion"
        assert len(msg) > 20, "Refusal message too short"

    def test_refusal_metadata_has_all_fields(self):
        """get_refusal_metadata must return label, stage, reason, suggestion."""
        answer = Answer(
            query="What is the vendor?",
            text="",
            grounded=False,
            refused=True,
            refusal_stage="FUZZY",
            refusal_reason="fuzzy match below 0.92",
            refusal_suggestion="Check for typos in source text.",
        )
        meta = get_refusal_metadata(answer)
        assert meta["label"], "Label must not be empty"
        assert meta["stage"], "Stage must not be empty"
        assert meta["reason"], "Reason must not be empty"
        assert meta["suggestion"], "Suggestion must not be empty"

    def test_refusal_with_empty_stage_defaults_to_block(self):
        """A refusal with no stage must default to BLOCK with full diagnostic."""
        answer = Answer(
            query="Unknown question",
            text="",
            grounded=False,
            refused=True,
            refusal_stage="",
            refusal_reason="",
            refusal_suggestion="",
        )
        meta = get_refusal_metadata(answer)
        assert meta["stage"] == "BLOCK", "Empty stage must default to BLOCK"
        assert meta["label"], "Label must not be empty even with empty stage"
        assert meta["reason"], "Reason must not be empty even with empty stage"
        assert meta["suggestion"], "Suggestion must not be empty even with empty stage"

    def test_non_refusal_returns_empty_metadata(self):
        """A grounded answer must not produce refusal metadata."""
        answer = Answer(
            query="What is the total?",
            text="$1,250.00",
            grounded=True,
            refused=False,
        )
        meta = get_refusal_metadata(answer)
        assert meta["label"] == "", "Non-refusal must have empty label"
        assert meta["stage"] == "", "Non-refusal must have empty stage"

    def test_refusal_message_never_blank(self):
        """format_refusal must never return an empty string for a refusal."""
        for stage in ("BLOCK", "FUZZY", "SEMANTIC", "VISUAL", "NORMALIZE", "EXACT", ""):
            answer = Answer(
                query="test query",
                text="",
                grounded=False,
                refused=True,
                refusal_stage=stage,
                refusal_reason="",
                refusal_suggestion="",
            )
            msg = format_refusal(answer)
            assert msg.strip(), f"Refusal message for stage '{stage}' must not be blank"

    def test_refusal_log_entry_written(self):
        """Every refusal must produce an audit-trail log entry."""
        # Capture log output
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.WARNING)
        ref_logger = logging.getLogger("kairo.refusal")
        ref_logger.addHandler(handler)
        ref_logger.setLevel(logging.WARNING)

        answer = Answer(
            query="What is the hidden field?",
            text="",
            grounded=False,
            refused=True,
            refusal_stage="BLOCK",
            refusal_reason="no match found",
            refusal_suggestion="Try rephrasing the query.",
        )
        log_refusal(answer)

        log_output = log_stream.getvalue()
        ref_logger.removeHandler(handler)

        assert "REFUSAL_AUDIT" in log_output, "Log entry must contain REFUSAL_AUDIT"
        assert "BLOCK" in log_output, "Log entry must contain the stage"
        assert "no match found" in log_output, "Log entry must contain the reason"

    def test_no_log_for_non_refusal(self):
        """A non-refusal answer must NOT produce a refusal log entry."""
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.WARNING)
        ref_logger = logging.getLogger("kairo.refusal")
        ref_logger.addHandler(handler)
        ref_logger.setLevel(logging.WARNING)

        answer = Answer(
            query="What is the total?",
            text="$1,250.00",
            grounded=True,
            refused=False,
        )
        log_refusal(answer)

        log_output = log_stream.getvalue()
        ref_logger.removeHandler(handler)

        assert "REFUSAL_AUDIT" not in log_output, (
            "Non-refusal must not produce a refusal audit log entry"
        )

    def test_refusal_format_matches_example(self):
        """The formatted refusal must match the spec example pattern."""
        answer = Answer(
            query="What is the tax rate?",
            text="",
            grounded=False,
            refused=True,
            refusal_stage="BLOCK",
            refusal_reason="no exact/fuzzy/semantic/visual match above threshold",
            refusal_suggestion="The answer may not be in this document, or the relevant section wasn't extracted cleanly.",
        )
        msg = format_refusal(answer)
        # Must contain: label + stage + reason + suggestion
        assert "No grounded source found" in msg
        assert "BLOCK" in msg
        assert "no exact/fuzzy/semantic/visual match above threshold" in msg
        assert "The answer may not be in this document" in msg

    def test_existing_answer_fields_preserved(self):
        """Existing Answer fields must still work after adding refusal metadata."""
        answer = Answer(
            query="test",
            text="some text",
            grounded=True,
            refused=False,
        )
        # All original fields must be accessible
        assert answer.query == "test"
        assert answer.text == "some text"
        assert answer.grounded is True
        assert answer.refused is False
        # New fields must exist and have defaults
        assert answer.refusal_stage == ""
        assert answer.refusal_reason == ""
        assert answer.refusal_suggestion == ""
