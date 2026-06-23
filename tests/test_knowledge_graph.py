"""
Tests for Kairo Grounded Knowledge Graph.
"""
import pytest
import json
from kernel.core.data_model import BBox, Chunk, Extraction, GroundingMethod, Anchor
from kairo.graph.entities import GroundedEntity, extract_entities
from kairo.graph.relationships import infer_relationships
from kairo.graph.store import GroundedKnowledgeGraph


def _make_extraction(field, value, method=GroundingMethod.EXACT, bbox=None):
    """Helper to create an Extraction with an anchor."""
    anchors = ()
    if bbox:
        anchors = (Anchor(chunk_id="c1", char_span=(0, 10), page=1, bbox=BBox(*bbox)),)
    return Extraction(
        pack_id="test", field_name=field, value=value,
        source_span=str(value), confidence=0.9,
        chunk_id="c1", method=method, anchors=anchors,
    )


def test_extract_entities_org():
    """ORG entity extracted from vendor_name."""
    ext = _make_extraction("vendor_name", "Acme Corp", bbox=[10, 20, 200, 40])
    entities = extract_entities([ext], "doc1")
    assert len(entities) == 1
    assert entities[0].entity_type == "ORG"
    assert entities[0].value == "Acme Corp"
    assert entities[0].source_doc == "doc1"
    assert entities[0].source_bbox is not None


def test_extract_entities_date():
    """DATE entity extracted from effective_date."""
    ext = _make_extraction("effective_date", "2024-06-18", bbox=[10, 20, 200, 40])
    entities = extract_entities([ext], "doc1")
    assert len(entities) == 1
    assert entities[0].entity_type == "DATE"


def test_extract_entities_amount():
    """AMOUNT entity extracted from total_amount."""
    ext = _make_extraction("total_amount", "1250.00", bbox=[10, 20, 200, 40])
    entities = extract_entities([ext], "doc1")
    assert len(entities) == 1
    assert entities[0].entity_type == "AMOUNT"


def test_extract_entities_jurisdiction():
    """JURISDICTION entity extracted from governing_law."""
    ext = _make_extraction("governing_law", "Delaware", bbox=[10, 20, 200, 40])
    entities = extract_entities([ext], "doc1")
    assert len(entities) == 1
    assert entities[0].entity_type == "JURISDICTION"


def test_extract_entities_persons():
    """PERSON entities extracted from authors."""
    ext = _make_extraction("authors", json.dumps(["Jane Doe", "John Smith"]), bbox=[10, 20, 200, 40])
    entities = extract_entities([ext], "doc1")
    assert len(entities) == 2
    assert all(e.entity_type == "PERSON" for e in entities)


def test_extract_entities_skip_blocked():
    """Blocked extractions are skipped."""
    ext = _make_extraction("vendor_name", "Acme Corp", method=GroundingMethod.BLOCK)
    entities = extract_entities([ext], "doc1")
    assert len(entities) == 0


def test_infer_relationships_appears_in():
    """Same entity in multiple docs -> appears_in edge."""
    e1 = GroundedEntity("ORG", "Acme Corp", "doc1", [10, 20, 200, 40], 1, 0.9, "vendor_name")
    e2 = GroundedEntity("ORG", "Acme Corp", "doc2", [10, 20, 200, 40], 1, 0.9, "vendor_name")
    edges = infer_relationships({"doc1": [e1], "doc2": [e2]})
    assert len(edges) >= 1
    assert any(e["relation"] == "appears_in" for e in edges)


def test_infer_relationships_supplies_to():
    """Same vendor across invoices -> supplies_to edge."""
    e1 = GroundedEntity("ORG", "Acme Corp", "inv1", [10, 20, 200, 40], 1, 0.9, "vendor_name")
    e2 = GroundedEntity("ORG", "Acme Corp", "inv2", [10, 20, 200, 40], 1, 0.9, "vendor_name")
    edges = infer_relationships({"inv1": [e1], "inv2": [e2]})
    assert any(e["relation"] == "supplies_to" for e in edges)


def test_infer_relationships_governed_by():
    """Same jurisdiction across contracts -> governed_by edge."""
    e1 = GroundedEntity("JURISDICTION", "Delaware", "con1", [10, 20, 200, 40], 1, 0.9, "governing_law")
    e2 = GroundedEntity("JURISDICTION", "Delaware", "con2", [10, 20, 200, 40], 1, 0.9, "governing_law")
    edges = infer_relationships({"con1": [e1], "con2": [e2]})
    assert any(e["relation"] == "governed_by" for e in edges)


def test_graph_build_from_extractions():
    """Graph builds nodes and edges from extractions."""
    g = GroundedKnowledgeGraph()
    ext1 = _make_extraction("vendor_name", "Acme Corp", bbox=[10, 20, 200, 40])
    ext2 = _make_extraction("governing_law", "Delaware", bbox=[10, 20, 200, 40])
    stats = g.build_from_extractions({"doc1": [ext1], "doc2": [ext2]})
    assert stats["total_nodes"] > 0
    assert "ORG:acme corp" in g.graph


def test_graph_query():
    """Graph query returns matching nodes with provenance."""
    g = GroundedKnowledgeGraph()
    ext = _make_extraction("vendor_name", "Acme Corp", bbox=[10, 20, 200, 40])
    g.build_from_extractions({"doc1": [ext]})
    results = g.query("acme")
    assert len(results) >= 1
    assert results[0]["value"] == "Acme Corp"
    assert results[0]["source_bbox"] is not None


def test_graph_save_load(tmp_path):
    """Graph persists and loads correctly."""
    g = GroundedKnowledgeGraph()
    ext = _make_extraction("vendor_name", "Acme Corp", bbox=[10, 20, 200, 40])
    g.build_from_extractions({"doc1": [ext]})
    path = tmp_path / "graph.json"
    g.save(path)
    assert path.exists()
    g2 = GroundedKnowledgeGraph()
    g2.load(path)
    assert g2.graph.number_of_nodes() == g.graph.number_of_nodes()


def test_graph_to_dict():
    """Graph serializes to dict with nodes, edges, stats."""
    g = GroundedKnowledgeGraph()
    ext = _make_extraction("vendor_name", "Acme Corp", bbox=[10, 20, 200, 40])
    g.build_from_extractions({"doc1": [ext]})
    d = g.to_dict()
    assert "nodes" in d
    assert "edges" in d
    assert "stats" in d
    assert d["stats"]["total_nodes"] > 0