"""
Tests for PaperPack.
"""

from kernel.core.data_model import Chunk, BBox
from packs.paper.pack import PaperPack


def test_paper_pack_fields():
    pack = PaperPack()
    assert "title" in pack.fields
    assert "authors" in pack.fields
    assert "methods" in pack.fields


def test_paper_pack_extract():
    pack = PaperPack()
    chunks = [
        Chunk(chunk_id="c1", text="Title: Grounding LLMs with Pixel-Level Bounding Boxes\nAuthors: Jane Doe, John Smith\nAbstract: This paper introduces Kairo-Phantom.", page=1, bbox=BBox(0, 0, 1, 1)),
    ]
    extractions = pack.extract(chunks)
    fields = {e.field_name: e.value for e in extractions}

    assert "Grounding LLMs" in fields.get("title", "")
    assert "Jane Doe" in fields.get("authors", "")
