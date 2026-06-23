"""
Tests for Kairo Context Compressor.
"""
import pytest
from kernel.core.data_model import BBox, Chunk
from kairo.context.compressor import (
    CompressionStats,
    _bbox_iou,
    compress_document_chunks,
    merge_overlapping_chunks,
    record_compression,
    get_compression_stats,
    _global_stats,
)


def test_bbox_iou_identical():
    """Identical boxes have IoU = 1.0."""
    b = BBox(10, 10, 100, 50)
    assert _bbox_iou(b, b) == 1.0


def test_bbox_iou_non_overlapping():
    """Non-overlapping boxes have IoU = 0.0."""
    b1 = BBox(0, 0, 10, 10)
    b2 = BBox(100, 100, 110, 110)
    assert _bbox_iou(b1, b2) == 0.0


def test_bbox_iou_partial():
    """Partially overlapping boxes have 0 < IoU < 1."""
    b1 = BBox(0, 0, 20, 20)
    b2 = BBox(10, 10, 30, 30)
    iou = _bbox_iou(b1, b2)
    assert 0 < iou < 1


def test_merge_overlapping_chunks():
    """Chunks with IoU > 0.8 are merged."""
    chunks = [
        Chunk(chunk_id="c1", text="Hello world", page=1, bbox=BBox(10, 10, 200, 30)),
        Chunk(chunk_id="c2", text="Hello world again", page=1, bbox=BBox(10, 10, 200, 30)),  # identical bbox
        Chunk(chunk_id="c3", text="Different region", page=1, bbox=BBox(10, 100, 200, 130)),
    ]
    merged = merge_overlapping_chunks(chunks, iou_threshold=0.8)
    assert len(merged) == 2  # c1+c2 merged, c3 separate
    assert "Hello world" in merged[0].text
    assert "Different region" in merged[1].text


def test_merge_non_overlapping():
    """Non-overlapping chunks are not merged."""
    chunks = [
        Chunk(chunk_id="c1", text="First", page=1, bbox=BBox(0, 0, 100, 50)),
        Chunk(chunk_id="c2", text="Second", page=1, bbox=BBox(0, 200, 100, 250)),
    ]
    merged = merge_overlapping_chunks(chunks)
    assert len(merged) == 2


def test_merge_different_pages():
    """Chunks on different pages are not merged even with same bbox."""
    chunks = [
        Chunk(chunk_id="c1", text="Page 1", page=1, bbox=BBox(10, 10, 200, 30)),
        Chunk(chunk_id="c2", text="Page 2", page=2, bbox=BBox(10, 10, 200, 30)),
    ]
    merged = merge_overlapping_chunks(chunks)
    assert len(merged) == 2


def test_compress_empty_chunks():
    """Empty chunk list returns empty result with zero stats."""
    result, stats = compress_document_chunks([])
    assert result == []
    assert stats.tokens_before == 0


def test_compress_preserves_metadata():
    """Compressed chunks preserve bbox, page, chunk_id from originals."""
    chunks = [
        Chunk(chunk_id="c1", text="This is a test document with some content.", page=1, bbox=BBox(10, 10, 200, 30)),
    ]
    result, stats = compress_document_chunks(chunks, target_ratio=0.5)
    assert len(result) == 1
    assert result[0].chunk_id == "c1"
    assert result[0].page == 1
    assert result[0].bbox is not None
    assert result[0].bbox.x0 == 10


def test_compression_stats():
    """CompressionStats has correct fields."""
    stats = CompressionStats(
        tokens_before=100,
        tokens_after=50,
        tokens_saved=50,
        reduction_pct=50.0,
        chunks_before=5,
        chunks_after=3,
    )
    d = stats.to_dict()
    assert d["tokens_before"] == 100
    assert d["tokens_after"] == 50
    assert d["reduction_pct"] == 50.0


def test_record_and_get_stats():
    """record_compression + get_compression_stats aggregate correctly."""
    _global_stats.clear()
    s1 = CompressionStats(tokens_before=100, tokens_after=60, tokens_saved=40, reduction_pct=40.0)
    s2 = CompressionStats(tokens_before=200, tokens_after=120, tokens_saved=80, reduction_pct=40.0)
    record_compression(s1)
    record_compression(s2)
    agg = get_compression_stats()
    assert agg["total_runs"] == 2
    assert agg["total_tokens_before"] == 300
    assert agg["total_tokens_after"] == 180
    assert agg["total_tokens_saved"] == 120
    assert agg["avg_reduction_pct"] == 40.0


def test_compress_reduces_tokens():
    """Compression actually reduces token count."""
    long_text = " ".join(["word"] * 200)  # ~150 tokens
    chunks = [
        Chunk(chunk_id="c1", text=long_text, page=1, bbox=BBox(0, 0, 100, 100)),
    ]
    result, stats = compress_document_chunks(chunks, target_ratio=0.3)
    assert stats.tokens_after <= stats.tokens_before
    assert stats.reduction_pct >= 0