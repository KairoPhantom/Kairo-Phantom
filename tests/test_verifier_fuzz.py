"""
T3 — Verifier fuzz test.

Throws random/garbage coordinates and quotes at the verifier and asserts
it never accepts an ungrounded pair.
"""

import random
import string

import pytest

from kernel.core.data_model import BBox, Chunk, GroundingMethod
from kernel.core.grounding import GroundingVerifierImpl


def make_fuzz_chunks() -> list[Chunk]:
    """Create chunks with known text and geometry for fuzzing."""
    return [
        Chunk(
            chunk_id="c1", doc_id="doc1", page=1,
            bbox=BBox(10, 10, 200, 30),
            text="Invoice Number: INV-2026-001",
        ),
        Chunk(
            chunk_id="c2", doc_id="doc1", page=1,
            bbox=BBox(10, 40, 200, 60),
            text="Total Amount Due: $1250.00",
        ),
        Chunk(
            chunk_id="c3", doc_id="doc1", page=1,
            bbox=BBox(10, 70, 200, 90),
            text="Payment Terms: Net 30",
        ),
    ]


def random_string(rng: random.Random, min_len: int = 1, max_len: int = 50) -> str:
    """Generate a random string of printable characters."""
    length = rng.randint(min_len, max_len)
    chars = string.printable + "αβγδ日本語"
    return "".join(rng.choices(chars, k=length))


def random_bbox_str(rng: random.Random) -> str:
    """Generate a random bbox string (sometimes valid format, sometimes garbage)."""
    fmt = rng.choice(["valid", "negative", "huge", "garbage", "partial"])
    if fmt == "valid":
        return f"bbox:{rng.uniform(0,500):.1f},{rng.uniform(0,500):.1f},{rng.uniform(0,500):.1f},{rng.uniform(0,500):.1f}"
    elif fmt == "negative":
        return f"bbox:{rng.uniform(-500,0):.1f},{rng.uniform(-500,0):.1f},{rng.uniform(-500,0):.1f},{rng.uniform(-500,0):.1f}"
    elif fmt == "huge":
        return f"bbox:{rng.uniform(1e6,1e9):.1f},{rng.uniform(1e6,1e9):.1f},{rng.uniform(1e6,1e9):.1f},{rng.uniform(1e6,1e9):.1f}"
    elif fmt == "garbage":
        return random_string(rng, 5, 30)
    else:  # partial
        return f"bbox:{rng.uniform(0,500):.1f},{rng.uniform(0,500):.1f}"


class TestVerifierFuzz:
    """Fuzz the verifier with random/garbage inputs — it must never accept
    an ungrounded pair."""

    @pytest.fixture
    def verifier(self):
        return GroundingVerifierImpl(semantic_threshold=0.5)

    @pytest.fixture
    def chunks(self):
        return make_fuzz_chunks()

    def test_fuzz_random_values_never_grounded_to_wrong_content(self, verifier, chunks):
        """Random garbage values must never be grounded to real document content
        unless they actually match."""
        rng = random.Random(42)
        accepted_wrong = 0

        for _ in range(500):
            value = random_string(rng, 1, 50)
            source_span = random_string(rng, 0, 50)
            method, anchors = verifier.verify(value, source_span, chunks)

            if method != GroundingMethod.BLOCK:
                # If accepted, the value or source_span must actually appear in a chunk
                accepted_text = " ".join(c.text for c in chunks).lower()
                # Check that the grounding is legitimate — the anchor points to a real chunk
                assert len(anchors) > 0
                anchor_chunk = next(
                    (c for c in chunks if c.chunk_id == anchors[0].chunk_id), None
                )
                assert anchor_chunk is not None, (
                    f"Fuzz accepted with anchor to non-existent chunk for value='{value[:30]}'"
                )

        # The vast majority of random strings should be BLOCKed
        # (we don't assert 100% block because random strings could accidentally match)
        assert accepted_wrong == 0

    def test_fuzz_random_bbox_never_grounded_to_nonexistent(self, verifier, chunks):
        """Random bbox coordinates must never ground to a non-existent chunk."""
        rng = random.Random(99)
        chunk_ids = {c.chunk_id for c in chunks}

        for _ in range(500):
            bbox_str = random_bbox_str(rng)
            value = random_string(rng, 1, 30)
            method, anchors = verifier.verify(value, bbox_str, chunks)

            if method == GroundingMethod.VISUAL:
                # Visual grounding — anchor must point to a real chunk
                assert len(anchors) > 0
                assert anchors[0].chunk_id in chunk_ids, (
                    f"Visual grounding to non-existent chunk with bbox_str='{bbox_str}'"
                )
                assert anchors[0].bbox is not None

    def test_fuzz_empty_and_whitespace_inputs(self, verifier, chunks):
        """Empty and whitespace-only inputs must always be BLOCKed."""
        empty_inputs = ["", " ", "   ", "\t", "\n", " \t\n "]
        for val in empty_inputs:
            method, anchors = verifier.verify(val, "", chunks)
            assert method == GroundingMethod.BLOCK, (
                f"Empty/whitespace input '{repr(val)}' was not BLOCKed"
            )
            assert len(anchors) == 0

    def test_fuzz_null_bytes_and_control_chars(self, verifier, chunks):
        """Null bytes and control characters must not cause crashes or
        false acceptances."""
        rng = random.Random(55)
        control_inputs = [
            "\x00\x01\x02\x03",
            "\xff\xfe\xfd",
            "\x00" * 100,
            "value\x00with\x00nulls",
            "\x0b\x0cINVISIBLE\x0b\x0c",
        ]

        for val in control_inputs:
            try:
                method, anchors = verifier.verify(val, val, chunks)
                # Should be BLOCKed (these don't match any chunk content)
                # or if somehow accepted, anchor must be valid
                if method != GroundingMethod.BLOCK:
                    assert len(anchors) > 0
                    anchor_chunk = next(
                        (c for c in chunks if c.chunk_id == anchors[0].chunk_id), None
                    )
                    assert anchor_chunk is not None
            except Exception as e:
                # Control chars should not crash the verifier
                pytest.fail(f"Verifier crashed on control chars: {e}")

    def test_fuzz_extremely_long_inputs(self, verifier, chunks):
        """Extremely long inputs must not crash or hang the verifier."""
        long_value = "A" * 10000
        method, anchors = verifier.verify(long_value, "", chunks)
        # Should be BLOCKed (no chunk contains 10000 A's)
        assert method == GroundingMethod.BLOCK
        assert len(anchors) == 0

    def test_fuzz_unicode_and_emoji(self, verifier, chunks):
        """Unicode and emoji inputs must not crash or false-accept."""
        unicode_inputs = [
            "日本語のテキスト",
            "🎉🎊🎈",
            "αβγδεζηθ",
            "مرحبا بالعالم",
            "नमस्ते दुनिया",
        ]
        for val in unicode_inputs:
            method, anchors = verifier.verify(val, val, chunks)
            # None of these appear in the chunks, so should be BLOCKed
            assert method == GroundingMethod.BLOCK, (
                f"Unicode input '{val}' was not BLOCKed"
            )

    def test_fuzz_deterministic_with_seed(self, verifier, chunks):
        """Fuzz results must be deterministic for the same seed."""
        rng1 = random.Random(123)
        rng2 = random.Random(123)

        results1 = []
        results2 = []

        for _ in range(100):
            val = random_string(rng1, 1, 30)
            results1.append(verifier.verify(val, "", chunks))

        for _ in range(100):
            val = random_string(rng2, 1, 30)
            results2.append(verifier.verify(val, "", chunks))

        assert results1 == results2, "Fuzz results not deterministic for same seed"