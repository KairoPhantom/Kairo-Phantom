"""
Tests for GenericPack.
"""

from kernel.core.data_model import Chunk, BBox
from packs.generic.pack import GenericPack


def test_generic_pack_fields():
    pack = GenericPack()
    assert "summary" in pack.fields
    assert "key_claims" in pack.fields
    assert "entities" in pack.fields
    assert "topics" in pack.fields


def test_generic_pack_extract():
    pack = GenericPack()
    chunks = [
        Chunk(chunk_id="c1", text="This is the first sentence. This is the second sentence. Key claim: Kairo Phantom is production-ready.", page=1, bbox=BBox(0, 0, 1, 1)),
    ]
    extractions = pack.extract(chunks)
    fields = {e.field_name: e.value for e in extractions}

    assert "This is the first sentence" in fields.get("summary", "")
    assert "key_claims" in fields
