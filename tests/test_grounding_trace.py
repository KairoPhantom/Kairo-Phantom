"""
Tests for Kairo Grounding Trace.
"""
import pytest
from kernel.core.data_model import BBox, Chunk, GroundingMethod
from kernel.core.grounding import GroundingVerifierImpl
from kairo.observability.trace import (
    CascadeSpan, GroundingTrace,
    record_trace, get_traces, get_trace_stats,
    traced_cascade, _trace_store,
)


@pytest.fixture
def verifier():
    return GroundingVerifierImpl()


@pytest.fixture
def chunks():
    return [
        Chunk(chunk_id="c1", doc_id="doc1", page=1,
              bbox=BBox(10, 10, 200, 30),
              text="Invoice Number: INV-2024-0001"),
        Chunk(chunk_id="c2", doc_id="doc1", page=1,
              bbox=BBox(10, 40, 200, 60),
              text="Total Amount Due: $1250.00"),
    ]


def test_cascade_span_creation():
    """CascadeSpan has correct fields."""
    span = CascadeSpan(
        layer="EXACT", decision="grounded", confidence=1.0,
        method="exact", wall_time_ms=0.5, doc_id="doc1", field="invoice_number",
    )
    d = span.to_dict()
    assert d["layer"] == "EXACT"
    assert d["decision"] == "grounded"
    assert d["confidence"] == 1.0


def test_grounding_trace_creation():
    """GroundingTrace has correct fields."""
    trace = GroundingTrace(
        doc_id="doc1", field="invoice_number", value="INV-2024-0001",
        final_decision="grounded", final_method="exact",
        final_confidence=1.0, final_bbox=[10, 10, 190, 20],
        spans=[CascadeSpan(layer="EXACT", decision="grounded", confidence=1.0)],
        total_wall_time_ms=1.5,
    )
    d = trace.to_dict()
    assert d["final_decision"] == "grounded"
    assert d["final_method"] == "exact"
    assert len(d["spans"]) == 1


def test_record_and_get_traces():
    """record_trace + get_traces stores and retrieves traces."""
    _trace_store.clear()
    trace = GroundingTrace(
        doc_id="doc1", field="test", value="val",
        final_decision="grounded", final_method="exact",
        final_confidence=1.0, final_bbox=None,
    )
    record_trace(trace)
    traces = get_traces(limit=10)
    assert len(traces) == 1
    assert traces[0]["field"] == "test"


def test_trace_stats_empty():
    """Stats return zeros when no traces."""
    _trace_store.clear()
    stats = get_trace_stats()
    assert stats["total_traces"] == 0
    assert stats["grounded_pct"] == 0.0


def test_trace_stats_with_data():
    """Stats aggregate correctly with trace data."""
    _trace_store.clear()
    for i in range(10):
        record_trace(GroundingTrace(
            doc_id=f"doc{i}", field="f", value="v",
            final_decision="grounded" if i < 8 else "refused",
            final_method="exact" if i < 8 else "block",
            final_confidence=0.9, final_bbox=None,
        ))
    stats = get_trace_stats()
    assert stats["total_traces"] == 10
    assert stats["grounded_pct"] == 80.0
    assert stats["refused_pct"] == 20.0


def test_traced_cascade_exact(verifier, chunks):
    """traced_cascade records EXACT match correctly."""
    _trace_store.clear()
    method, anchors = traced_cascade(
        verifier, "INV-2024-0001", "INV-2024-0001", chunks,
        doc_id="doc1", field_name="invoice_number",
    )
    assert method == GroundingMethod.EXACT
    assert len(anchors) == 1
    traces = get_traces(limit=10)
    assert len(traces) == 1
    assert traces[0]["final_decision"] == "grounded"
    assert traces[0]["final_method"] == "exact"
    # Should have NORMALIZE + EXACT spans
    layers = [s["layer"] for s in traces[0]["spans"]]
    assert "NORMALIZE" in layers
    assert "EXACT" in layers


def test_traced_cascade_block(verifier, chunks):
    """traced_cascade records BLOCK when no match found."""
    _trace_store.clear()
    method, anchors = traced_cascade(
        verifier, "NONEXISTENT-VALUE-12345", "NONEXISTENT-VALUE-12345", chunks,
        doc_id="doc1", field_name="unknown_field",
    )
    assert method == GroundingMethod.BLOCK
    assert len(anchors) == 0
    traces = get_traces(limit=10)
    assert len(traces) == 1
    assert traces[0]["final_decision"] == "refused"
    assert traces[0]["final_method"] == "block"


def test_traced_cascade_empty_input(verifier):
    """traced_cascade blocks on empty input."""
    _trace_store.clear()
    method, anchors = traced_cascade(
        verifier, "", "", [], doc_id="doc1", field_name="test",
    )
    assert method == GroundingMethod.BLOCK
    traces = get_traces(limit=10)
    assert len(traces) == 1
    assert traces[0]["final_decision"] == "refused"