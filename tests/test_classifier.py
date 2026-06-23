"""
Tests for Kairo Document Classifier and Connector Protocol.
"""
import pytest
from kairo.core.classifier import classify_document, build_source_link


def test_classify_invoice():
    """Invoice keywords trigger invoice classification."""
    text = "INVOICE\nInvoice Number: INV-2024-0001\nTotal Amount Due: $1250.00\nPayment Terms: Net 30"
    assert classify_document(text) == "invoice"


def test_classify_contract():
    """Contract keywords trigger contract classification."""
    text = "PARTNERSHIP AGREEMENT\nThis agreement is made between Party A and Party B. Governing Law: Delaware. Termination: 90 days notice."
    assert classify_document(text) == "contract"


def test_classify_paper():
    """Paper keywords trigger paper classification."""
    text = "Abstract\nWe present a novel approach. Methodology uses transformer architecture. References: [1] Smith et al. DOI: 10.1000/xyz"
    assert classify_document(text) == "paper"


def test_classify_generic():
    """No strong signals -> generic."""
    text = "Project Atlas Q4 Status Report\nExecutive Summary\nThe project has completed 52% of milestones."
    assert classify_document(text) == "generic"


def test_classify_empty():
    """Empty text -> generic."""
    assert classify_document("") == "generic"


def test_classify_multilingual_invoice():
    """Swedish invoice keywords trigger invoice."""
    text = "FAKTURA / INVOICE\nFakturanr: INV-2024-0004\nBetalningsvillkor: Due on Receipt"
    assert classify_document(text) == "invoice"


def test_classify_page_count_fallback():
    """Page count heuristics when no keywords match."""
    assert classify_document("some text", page_count=10) == "paper"
    assert classify_document("some text", page_count=6) == "contract"
    assert classify_document("some text", page_count=2) == "generic"


def test_build_source_link():
    """Source link format is correct."""
    link = build_source_link("doc123", 1, [100, 200, 300, 220])
    assert link == "kairo://doc/doc123?page=1&x=100&y=200&w=300&h=220"


def test_build_source_link_no_bbox():
    """Source link without bbox still works."""
    link = build_source_link("doc123", 1, [])
    assert link == "kairo://doc/doc123?page=1"


def test_build_source_link_zero_bbox():
    """Source link with zero bbox returns page-only link."""
    link = build_source_link("doc123", 2, [0, 0, 0, 0])
    assert "page=2" in link