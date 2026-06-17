"""
Tests for ContractPack.
"""

from kernel.core.data_model import Chunk, BBox
from packs.contract.pack import ContractPack


def test_contract_pack_fields():
    pack = ContractPack()
    assert "parties" in pack.fields
    assert "governing_law" in pack.fields


def test_contract_pack_extract():
    pack = ContractPack()
    chunks = [
        Chunk(chunk_id="c1", text="This contract is entered into by and between Alice Corp and Bob Inc.\nGoverning Law: The laws of the State of New York shall govern.", page=1, bbox=BBox(0, 0, 1, 1)),
    ]
    extractions = pack.extract(chunks)
    fields = {e.field_name: e.value for e in extractions}

    assert "Alice Corp" in fields.get("parties", "")
    assert "New York" in fields.get("governing_law", "")
