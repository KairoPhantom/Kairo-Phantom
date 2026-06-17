"""
Tests for InvoicePack.
"""

from kernel.core.data_model import Chunk, BBox
from packs.invoice.pack import InvoicePack


def test_invoice_pack_fields():
    pack = InvoicePack()
    assert "vendor_name" in pack.fields
    assert "total_amount" in pack.fields
    assert "invoice_number" in pack.fields


def test_invoice_pack_extract():
    pack = InvoicePack()
    chunks = [
        Chunk(chunk_id="c1", text="TechCorp Solutions\nInvoice Number: INV-9988\nDate: 2026-06-15", page=1, bbox=BBox(0, 0, 1, 1)),
        Chunk(chunk_id="c2", text="Total: $5000.00", page=1, bbox=BBox(0, 0, 1, 1)),
    ]
    extractions = pack.extract(chunks)
    fields = {e.field_name: e.value for e in extractions}

    # InvoicePack uses regex patterns. TechCorp Solutions is matched as vendor name.
    # Total 5000.00 is matched as total amount.
    # Let's check some extracted fields
    assert "TechCorp Solutions" in fields.get("vendor_name", "")
    assert "5000.00" in fields.get("total_amount", "")
