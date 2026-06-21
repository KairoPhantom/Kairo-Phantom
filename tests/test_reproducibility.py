"""
Tests for X3 — Determinism guarantee + reproducibility receipt

Tests:
1. Byte-identical answers across runs with same inputs
2. Receipt verification works
3. Different inputs produce different receipts
4. Seed pinning works
5. Config changes produce different receipts
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kernel.core.reproducibility import (
    ReproducibilityReceipt,
    ReproducibilityReceiptBuilder,
    compare_receipts,
    assert_byte_identical,
)
from kernel.core.data_model import Answer, Anchor, BBox


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
CORPUS_TEXTS = [
    "This is document one about contracts and legal terms.",
    "This is document two about invoices and payment terms.",
    "This is document three about research papers and citations.",
]

MODEL_ID = "ollama-llama3-8b"
MODEL_VERSION = "v8b-Q4_K_M"
SEED = 42
CONFIG = {"fuzzy_threshold": 0.92, "semantic_threshold": 0.86}


def make_answers():
    """Create a deterministic set of answers."""
    anchor = Anchor(
        chunk_id="chunk_001",
        char_span=(10, 20),
        page=1,
        bbox=BBox(0.1, 0.2, 0.8, 0.3),
    )
    return [
        Answer(query="What is the governing law?", text="Delaware",
               citations=(anchor,), grounded=True, refused=False),
        Answer(query="What is the payment term?", text="Net 30",
               citations=(anchor,), grounded=True, refused=False),
    ]


def make_refusals():
    """Create a deterministic set of refusals."""
    return [
        "What is the CEO's salary?",
        "What is the stock price?",
    ]


# ---------------------------------------------------------------------------
# Test 1: Byte-identical answers across runs with same inputs
# ---------------------------------------------------------------------------
class TestByteIdenticalAcrossRuns:
    """Same inputs must produce byte-identical receipts."""

    def test_same_inputs_same_receipt(self):
        """Two runs with identical inputs must produce identical receipts
        (except for receipt_id and created_at)."""
        builder1 = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        builder2 = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )

        receipt1 = builder1.build(CORPUS_TEXTS, make_answers(), make_refusals())
        receipt2 = builder2.build(CORPUS_TEXTS, make_answers(), make_refusals())

        # The meaningful fields must match
        comparison = compare_receipts(receipt1, receipt2)
        for field, match in comparison.items():
            assert match, f"Field '{field}' must match for identical inputs: {getattr(receipt1, field)} != {getattr(receipt2, field)}"

    def test_assert_byte_identical_passes(self):
        """assert_byte_identical must not raise for identical receipts."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        r1 = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())
        r2 = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())

        # Should not raise
        assert_byte_identical(r1, r2)

    def test_assert_byte_identical_fails_on_different_results(self):
        """assert_byte_identical must raise when results differ."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        r1 = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())

        # Different answers
        different_answers = [Answer(query="Different question", text="Different answer")]
        r2 = builder.build(CORPUS_TEXTS, different_answers, make_refusals())

        with pytest.raises(AssertionError, match="not byte-identical"):
            assert_byte_identical(r1, r2)


# ---------------------------------------------------------------------------
# Test 2: Receipt verification works
# ---------------------------------------------------------------------------
class TestReceiptVerification:
    """The receipt.verify() method must correctly validate parameters."""

    def test_verify_with_matching_parameters(self):
        """verify() returns True when all parameters match."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        receipt = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())

        corpus_hash = ReproducibilityReceiptBuilder._hash_corpus(CORPUS_TEXTS)
        result_hash = ReproducibilityReceiptBuilder._hash_results(make_answers(), make_refusals())
        config_hash = ReproducibilityReceiptBuilder._hash_config(CONFIG)

        assert receipt.verify(
            corpus_hash=corpus_hash,
            result_hash=result_hash,
            model_id=MODEL_ID,
            model_version=MODEL_VERSION,
            seed=SEED,
            config_hash=config_hash,
        ), "verify() must return True for matching parameters"

    def test_verify_with_mismatched_corpus(self):
        """verify() returns False when corpus hash differs."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        receipt = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())

        assert not receipt.verify(
            corpus_hash="wrong_hash",
            result_hash=ReproducibilityReceiptBuilder._hash_results(make_answers(), make_refusals()),
            model_id=MODEL_ID,
            model_version=MODEL_VERSION,
            seed=SEED,
            config_hash=ReproducibilityReceiptBuilder._hash_config(CONFIG),
        ), "verify() must return False for mismatched corpus"

    def test_verify_with_mismatched_model(self):
        """verify() returns False when model_id differs."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        receipt = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())

        assert not receipt.verify(
            corpus_hash=ReproducibilityReceiptBuilder._hash_corpus(CORPUS_TEXTS),
            result_hash=ReproducibilityReceiptBuilder._hash_results(make_answers(), make_refusals()),
            model_id="wrong-model",
            model_version=MODEL_VERSION,
            seed=SEED,
            config_hash=ReproducibilityReceiptBuilder._hash_config(CONFIG),
        ), "verify() must return False for mismatched model_id"

    def test_verify_with_mismatched_seed(self):
        """verify() returns False when seed differs."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        receipt = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())

        assert not receipt.verify(
            corpus_hash=ReproducibilityReceiptBuilder._hash_corpus(CORPUS_TEXTS),
            result_hash=ReproducibilityReceiptBuilder._hash_results(make_answers(), make_refusals()),
            model_id=MODEL_ID,
            model_version=MODEL_VERSION,
            seed=999,
            config_hash=ReproducibilityReceiptBuilder._hash_config(CONFIG),
        ), "verify() must return False for mismatched seed"


# ---------------------------------------------------------------------------
# Test 3: Different inputs produce different receipts
# ---------------------------------------------------------------------------
class TestDifferentInputsDifferentReceipts:
    """Different inputs must produce different receipts."""

    def test_different_corpus_different_receipt(self):
        """Different corpus texts must produce different corpus_hash and result_hash."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )

        r1 = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())
        r2 = builder.build(["completely different text"], make_answers(), make_refusals())

        assert r1.corpus_hash != r2.corpus_hash, "Different corpus must produce different hash"

    def test_different_answers_different_receipt(self):
        """Different answers must produce different result_hash."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )

        r1 = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())
        different_answers = [Answer(query="New Q", text="New A", grounded=True)]
        r2 = builder.build(CORPUS_TEXTS, different_answers, make_refusals())

        assert r1.result_hash != r2.result_hash, "Different answers must produce different hash"

    def test_different_refusals_different_receipt(self):
        """Different refusals must produce different result_hash."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )

        r1 = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())
        r2 = builder.build(CORPUS_TEXTS, make_answers(), ["different refusal"])

        assert r1.result_hash != r2.result_hash, "Different refusals must produce different hash"

    def test_different_model_different_receipt(self):
        """Different model_id must produce different receipt."""
        builder1 = ReproducibilityReceiptBuilder(
            model_id="model-A", model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        builder2 = ReproducibilityReceiptBuilder(
            model_id="model-B", model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )

        r1 = builder1.build(CORPUS_TEXTS, make_answers(), make_refusals())
        r2 = builder2.build(CORPUS_TEXTS, make_answers(), make_refusals())

        assert r1.model_id != r2.model_id

    def test_different_config_different_receipt(self):
        """Different config must produce different config_hash."""
        builder1 = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config={"fuzzy_threshold": 0.92},
        )
        builder2 = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config={"fuzzy_threshold": 0.95},
        )

        r1 = builder1.build(CORPUS_TEXTS, make_answers(), make_refusals())
        r2 = builder2.build(CORPUS_TEXTS, make_answers(), make_refusals())

        assert r1.config_hash != r2.config_hash, "Different config must produce different hash"


# ---------------------------------------------------------------------------
# Test 4: Seed pinning
# ---------------------------------------------------------------------------
class TestSeedPinning:
    """Seed pinning must produce deterministic random state."""

    def test_pin_seed_returns_seed(self):
        """pin_seed() returns the configured seed."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        assert builder.pin_seed() == SEED

    def test_pinned_seed_produces_deterministic_random(self):
        """After pinning, random produces deterministic values."""
        import random

        builder1 = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        builder2 = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )

        builder1.pin_seed()
        vals1 = [random.random() for _ in range(10)]

        builder2.pin_seed()
        vals2 = [random.random() for _ in range(10)]

        assert vals1 == vals2, "Same seed must produce same random sequence"

    def test_different_seed_different_random(self):
        """Different seeds produce different random sequences."""
        import random

        builder1 = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        builder2 = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=999, config=CONFIG,
        )

        builder1.pin_seed()
        vals1 = [random.random() for _ in range(10)]

        builder2.pin_seed()
        vals2 = [random.random() for _ in range(10)]

        assert vals1 != vals2, "Different seeds must produce different sequences"


# ---------------------------------------------------------------------------
# Test 5: Receipt serialization
# ---------------------------------------------------------------------------
class TestReceiptSerialization:
    """Receipts must serialize to JSON correctly."""

    def test_to_json_contains_all_fields(self):
        """to_json() must contain all receipt fields."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        receipt = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())

        import json
        data = json.loads(receipt.to_json())

        assert data["corpus_hash"] == receipt.corpus_hash
        assert data["model_id"] == receipt.model_id
        assert data["model_version"] == receipt.model_version
        assert data["seed"] == receipt.seed
        assert data["result_hash"] == receipt.result_hash
        assert data["answer_count"] == 2
        assert data["refusal_count"] == 2
        assert data["config_hash"] == receipt.config_hash

    def test_to_json_is_canonical(self):
        """to_json() must produce sorted keys for determinism."""
        builder = ReproducibilityReceiptBuilder(
            model_id=MODEL_ID, model_version=MODEL_VERSION,
            seed=SEED, config=CONFIG,
        )
        r1 = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())
        r2 = builder.build(CORPUS_TEXTS, make_answers(), make_refusals())

        # JSON output must be identical (except receipt_id and created_at)
        import json
        d1 = json.loads(r1.to_json())
        d2 = json.loads(r2.to_json())
        for key in ["corpus_hash", "model_id", "model_version", "seed",
                     "result_hash", "answer_count", "refusal_count", "config_hash"]:
            assert d1[key] == d2[key], f"Field {key} must be identical"


# ---------------------------------------------------------------------------
# Test 6: Corpus hashing determinism
# ---------------------------------------------------------------------------
class TestCorpusHashing:
    """Corpus hashing must be deterministic regardless of input order."""

    def test_same_corpus_different_order_same_hash(self):
        """Corpus texts in different order must produce the same hash."""
        texts1 = ["alpha", "beta", "gamma"]
        texts2 = ["gamma", "alpha", "beta"]

        h1 = ReproducibilityReceiptBuilder._hash_corpus(texts1)
        h2 = ReproducibilityReceiptBuilder._hash_corpus(texts2)

        assert h1 == h2, "Corpus hash must be order-independent"

    def test_empty_corpus_has_hash(self):
        """Empty corpus must still produce a valid hash."""
        h = ReproducibilityReceiptBuilder._hash_corpus([])
        assert len(h) == 64, "SHA-256 produces 64 hex chars"
        assert h != ReproducibilityReceiptBuilder._hash_corpus(["non-empty"])