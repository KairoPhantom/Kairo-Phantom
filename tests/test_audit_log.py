"""
Tests for X1 — Signed Audit Log (compliance infrastructure)

Tests:
1. Signature verification: entries have valid HMAC-SHA256 signatures
2. Tamper detection: modifying a log entry invalidates the chain
3. Every answer AND every refusal produces a log entry
4. Chain verification: the hash chain is intact
5. Wrong key fails verification
6. Export format produces valid JSON and markdown
"""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kernel.core.audit_log import SignedAuditLog, AuditEntry
from kernel.core.audit_export import export_json, export_markdown, export_to_files
from kernel.core.data_model import Answer, Anchor, BBox


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
SESSION_KEY = b"test-secret-session-key-for-audit-log"
DOC_HASH = "abc123def4567890abcdef1234567890abcdef1234567890abcdef1234567890"
MODEL_ID = "ollama-llama3-8b"


def make_grounded_answer(query="What is the governing law?", text="Delaware") -> Answer:
    """Create a grounded answer with a citation."""
    anchor = Anchor(
        chunk_id="chunk_001",
        char_span=(10, 18),
        page=1,
        bbox=BBox(0.1, 0.2, 0.8, 0.3),
    )
    return Answer(
        query=query,
        text=text,
        citations=(anchor,),
        grounded=True,
        refused=False,
    )


def make_refused_answer(query="What is the CEO's salary?") -> Answer:
    """Create a refused answer (no citations)."""
    return Answer(
        query=query,
        text="I cannot answer this question from the provided document.",
        citations=(),
        grounded=False,
        refused=True,
    )


# ---------------------------------------------------------------------------
# Test 1: Signature verification
# ---------------------------------------------------------------------------
class TestSignatureVerification:
    """Every entry must have a valid HMAC-SHA256 signature."""

    def test_answer_entry_has_valid_signature(self):
        """A logged answer must have a valid signature."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        answer = make_grounded_answer()
        entry = log.log_answer(answer, document_hash=DOC_HASH, model_id=MODEL_ID)

        assert entry.signature != "", "Signature must not be empty"
        assert len(entry.signature) == 64, "HMAC-SHA256 produces 64 hex chars"
        assert log.verify_entry(entry), "Signature must verify against the session key"

    def test_refusal_entry_has_valid_signature(self):
        """A logged refusal must have a valid signature."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        entry = log.log_refusal(
            question="What is the CEO's salary?",
            document_hash=DOC_HASH,
            cascade_stage="BLOCK",
            model_id=MODEL_ID,
        )

        assert entry.signature != "", "Signature must not be empty"
        assert len(entry.signature) == 64, "HMAC-SHA256 produces 64 hex chars"
        assert log.verify_entry(entry), "Signature must verify against the session key"

    def test_signature_is_deterministic(self):
        """Same content + same key + same prev_signature = same signature."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        answer = make_grounded_answer()
        entry = log.log_answer(answer, document_hash=DOC_HASH, model_id=MODEL_ID)

        # Recompute signature manually
        import hmac
        import hashlib
        expected = hmac.new(SESSION_KEY, entry.content_bytes(), hashlib.sha256).hexdigest()
        assert entry.signature == expected, "Signature must be deterministic"


# ---------------------------------------------------------------------------
# Test 2: Tamper detection
# ---------------------------------------------------------------------------
class TestTamperDetection:
    """Modifying a log entry must invalidate the chain."""

    def test_modifying_question_invalidates_chain(self):
        """Changing the question field breaks the chain."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        answer = make_grounded_answer(query="What is the governing law?")
        log.log_answer(answer, document_hash=DOC_HASH, model_id=MODEL_ID)
        log.log_refusal("What is X?", DOC_HASH, "BLOCK", MODEL_ID)

        # Chain should be valid before tampering
        assert log.verify_chain(), "Chain must be valid before tampering"

        # Tamper: modify the question in the first entry
        entry = log._entries[0]
        object.__setattr__(entry, "question", "TAMPERED QUESTION")

        # Chain should now be broken
        assert not log.verify_chain(), "Chain must be broken after tampering with question"

    def test_modifying_document_hash_invalidates_chain(self):
        """Changing the document_hash field breaks the chain."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        answer = make_grounded_answer()
        log.log_answer(answer, document_hash=DOC_HASH, model_id=MODEL_ID)

        assert log.verify_chain(), "Chain must be valid before tampering"

        entry = log._entries[0]
        object.__setattr__(entry, "document_hash", "tampered_hash")

        assert not log.verify_chain(), "Chain must be broken after tampering with document_hash"

    def test_modifying_cascade_stage_invalidates_chain(self):
        """Changing the cascade_stage field breaks the chain."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_refusal("What is X?", DOC_HASH, "BLOCK", MODEL_ID)

        assert log.verify_chain()

        entry = log._entries[0]
        object.__setattr__(entry, "cascade_stage", "EXACT")

        assert not log.verify_chain(), "Chain must be broken after tampering with cascade_stage"

    def test_modifying_middle_entry_invalidates_rest_of_chain(self):
        """Tampering with a middle entry breaks the chain from that point."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        # Add 3 entries
        log.log_answer(make_grounded_answer("Q1"), DOC_HASH, MODEL_ID)
        log.log_answer(make_grounded_answer("Q2"), DOC_HASH, MODEL_ID)
        log.log_answer(make_grounded_answer("Q3"), DOC_HASH, MODEL_ID)

        assert log.verify_chain(), "Chain must be valid with 3 entries"

        # Tamper with the middle entry
        entry = log._entries[1]
        object.__setattr__(entry, "question", "TAMPERED")

        assert not log.verify_chain(), "Chain must be broken after tampering with middle entry"

    def test_modifying_signature_invalidates_chain(self):
        """Changing the signature itself breaks the chain."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer(), DOC_HASH, MODEL_ID)

        assert log.verify_chain()

        entry = log._entries[0]
        object.__setattr__(entry, "signature", "0" * 64)

        assert not log.verify_chain(), "Chain must be broken after tampering with signature"


# ---------------------------------------------------------------------------
# Test 3: Every answer AND refusal produces a log entry
# ---------------------------------------------------------------------------
class TestEveryActionLogged:
    """Every answer and every refusal must produce a log entry."""

    def test_answer_produces_entry(self):
        """Logging an answer creates exactly one entry."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        assert log.entry_count == 0

        answer = make_grounded_answer()
        log.log_answer(answer, document_hash=DOC_HASH, model_id=MODEL_ID)

        assert log.entry_count == 1, "One answer must produce one entry"
        assert log.entries[0].outcome == "answer"
        assert log.entries[0].grounded is True

    def test_refusal_produces_entry(self):
        """Logging a refusal creates exactly one entry."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        assert log.entry_count == 0

        log.log_refusal("What is X?", DOC_HASH, "BLOCK", MODEL_ID)

        assert log.entry_count == 1, "One refusal must produce one entry"
        assert log.entries[0].outcome == "refusal"
        assert log.entries[0].grounded is False

    def test_mixed_answers_and_refusals_all_logged(self):
        """A mix of answers and refusals all produce entries."""
        log = SignedAuditLog(session_key=SESSION_KEY)

        log.log_answer(make_grounded_answer("Q1"), DOC_HASH, MODEL_ID)
        log.log_refusal("Q2", DOC_HASH, "BLOCK", MODEL_ID)
        log.log_answer(make_grounded_answer("Q3"), DOC_HASH, MODEL_ID)
        log.log_refusal("Q4", DOC_HASH, "BLOCK", MODEL_ID)
        log.log_answer(make_grounded_answer("Q5"), DOC_HASH, MODEL_ID)

        assert log.entry_count == 5, "All 5 actions must be logged"
        outcomes = [e.outcome for e in log.entries]
        assert outcomes == ["answer", "refusal", "answer", "refusal", "answer"]

    def test_refused_answer_object_produces_refusal_entry(self):
        """A refused Answer object (refused=True) logged as answer produces
        an entry with grounded=False."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        refused = make_refused_answer()
        log.log_answer(refused, document_hash=DOC_HASH, model_id=MODEL_ID)

        assert log.entry_count == 1
        assert log.entries[0].grounded is False
        assert log.entries[0].outcome == "answer"

    def test_source_region_recorded_for_grounded_answer(self):
        """A grounded answer's entry must record the source region (bbox)."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        answer = make_grounded_answer()
        log.log_answer(answer, document_hash=DOC_HASH, model_id=MODEL_ID)

        entry = log.entries[0]
        assert entry.source_region != {}, "Source region must be recorded"
        assert "bbox" in entry.source_region, "BBox must be in source region"
        assert entry.source_region["page"] == 1
        assert entry.source_region["chunk_id"] == "chunk_001"

    def test_no_source_region_for_refusal(self):
        """A refusal's entry must have an empty source region."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_refusal("What is X?", DOC_HASH, "BLOCK", MODEL_ID)

        entry = log.entries[0]
        assert entry.source_region == {}, "Refusal must have empty source region"


# ---------------------------------------------------------------------------
# Test 4: Chain verification
# ---------------------------------------------------------------------------
class TestChainVerification:
    """The hash chain must be intact and verifiable."""

    def test_empty_log_chain_valid(self):
        """An empty log has a valid (trivially) chain."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        assert log.verify_chain(), "Empty log chain must be valid"

    def test_single_entry_chain_valid(self):
        """A single entry forms a valid chain."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer(), DOC_HASH, MODEL_ID)
        assert log.verify_chain(), "Single entry chain must be valid"

    def test_multi_entry_chain_valid(self):
        """Multiple entries form a valid chain."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        for i in range(10):
            log.log_answer(make_grounded_answer(f"Q{i}"), DOC_HASH, MODEL_ID)
        assert log.verify_chain(), "10-entry chain must be valid"

    def test_chain_linkage_prev_signature(self):
        """Each entry's prev_signature must match the previous entry's signature."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer("Q1"), DOC_HASH, MODEL_ID)
        log.log_answer(make_grounded_answer("Q2"), DOC_HASH, MODEL_ID)

        assert log.entries[0].prev_signature == "", "First entry has empty prev_signature"
        assert log.entries[1].prev_signature == log.entries[0].signature, \
            "Second entry's prev_signature must match first entry's signature"


# ---------------------------------------------------------------------------
# Test 5: Wrong key fails verification
# ---------------------------------------------------------------------------
class TestWrongKeyFails:
    """A different session key must fail verification."""

    def test_wrong_key_fails_verification(self):
        """Verifying with a different key must fail."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer(), DOC_HASH, MODEL_ID)

        wrong_key = b"wrong-key"
        assert not log.verify_chain_with_key(wrong_key), \
            "Verification with wrong key must fail"

    def test_correct_key_passes_verification(self):
        """Verifying with the correct key must pass."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer(), DOC_HASH, MODEL_ID)

        assert log.verify_chain_with_key(SESSION_KEY), \
            "Verification with correct key must pass"


# ---------------------------------------------------------------------------
# Test 6: Export format
# ---------------------------------------------------------------------------
class TestExportFormat:
    """The export format must produce valid JSON and markdown."""

    def test_json_export_contains_all_entries(self):
        """JSON export must contain all log entries."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer("Q1"), DOC_HASH, MODEL_ID)
        log.log_refusal("Q2", DOC_HASH, "BLOCK", MODEL_ID)

        exported = export_json(log)
        data = json.loads(exported)

        assert "entries" in data
        assert len(data["entries"]) == 2
        assert data["summary"]["total_answers"] == 1
        assert data["summary"]["total_refusals"] == 1
        assert data["export_metadata"]["chain_integrity"] == "VALID"

    def test_markdown_export_contains_answers_and_refusals(self):
        """Markdown export must have sections for answers and refusals."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer("Q1"), DOC_HASH, MODEL_ID)
        log.log_refusal("Q2", DOC_HASH, "BLOCK", MODEL_ID)

        md = export_markdown(log)

        assert "## 1. Answers" in md, "Markdown must have answers section"
        assert "## 2. Refusals" in md, "Markdown must have refusals section"
        assert "Q1" in md, "Markdown must contain the answer question"
        assert "Q2" in md, "Markdown must contain the refusal question"
        assert "BLOCK" in md, "Markdown must contain the cascade stage"
        assert "Chain" in md, "Markdown must contain chain verification section"

    def test_export_to_files(self, tmp_path):
        """Export to files creates both JSON and markdown files."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer(), DOC_HASH, MODEL_ID)

        json_path, md_path = export_to_files(log, str(tmp_path))

        assert os.path.exists(json_path), "JSON file must be created"
        assert os.path.exists(md_path), "Markdown file must be created"

        with open(json_path) as f:
            data = json.load(f)
        assert len(data["entries"]) == 1

        with open(md_path) as f:
            md = f.read()
        assert "Audit Log Export" in md


# ---------------------------------------------------------------------------
# Test 7: Serialization round-trip
# ---------------------------------------------------------------------------
class TestSerializationRoundTrip:
    """The log must survive JSON serialization and deserialization."""

    def test_round_trip_preserves_chain(self):
        """Serializing and deserializing preserves the chain."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer("Q1"), DOC_HASH, MODEL_ID)
        log.log_refusal("Q2", DOC_HASH, "BLOCK", MODEL_ID)
        log.log_answer(make_grounded_answer("Q3"), DOC_HASH, MODEL_ID)

        json_str = log.to_json()
        restored = SignedAuditLog.from_json(json_str, SESSION_KEY)

        assert restored.entry_count == 3, "Restored log must have same entry count"
        assert restored.verify_chain(), "Restored chain must be valid"

    def test_round_trip_tampered_json_raises(self):
        """Loading a tampered JSON must raise ValueError."""
        log = SignedAuditLog(session_key=SESSION_KEY)
        log.log_answer(make_grounded_answer("Q1"), DOC_HASH, MODEL_ID)

        json_str = log.to_json()
        data = json.loads(json_str)
        # Tamper with the question
        data["entries"][0]["question"] = "TAMPERED"
        tampered_json = json.dumps(data)

        with pytest.raises(ValueError, match="chain is broken"):
            SignedAuditLog.from_json(tampered_json, SESSION_KEY)


# ---------------------------------------------------------------------------
# Test 8: Empty key rejected
# ---------------------------------------------------------------------------
class TestEmptyKeyRejected:
    """An empty session key must be rejected."""

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="session_key must not be empty"):
            SignedAuditLog(session_key=b"")

    def test_none_key_raises(self):
        with pytest.raises((ValueError, TypeError)):
            SignedAuditLog(session_key=None)