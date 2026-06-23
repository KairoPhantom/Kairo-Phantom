"""
Tests for Kairo P2P Sync Manager.
"""
import pytest
import tempfile
import os
from kernel.core.data_model import Extraction, GroundingMethod
from kairo.sync.sync_manager import (
    DocumentManifest, SyncManager,
    compute_doc_hash, build_manifest, compare_manifests, merge_extractions,
)


def _make_extraction(field, value, confidence=0.9, method=GroundingMethod.EXACT):
    return Extraction(
        pack_id="test", field_name=field, value=value,
        source_span=str(value), confidence=confidence,
        chunk_id="c1", method=method, anchors=(),
    )


def _make_temp_file(content="test content"):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    f.write(content)
    f.close()
    return f.name


def test_compute_doc_hash():
    """Document hash is consistent."""
    path = _make_temp_file("hello world")
    h1 = compute_doc_hash(path)
    h2 = compute_doc_hash(path)
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex
    os.unlink(path)


def test_build_manifest():
    """Manifest is built correctly from extractions."""
    path = _make_temp_file("invoice content")
    exts = [_make_extraction("vendor_name", "Acme Corp"), _make_extraction("total", "100")]
    manifest = build_manifest("doc1", path, "invoice", exts)
    assert manifest.doc_id == "doc1"
    assert manifest.doc_type == "invoice"
    assert manifest.fields_count == 2
    assert len(manifest.extractions) == 2
    os.unlink(path)


def test_compare_manifests_no_overlap():
    """No overlap between local and remote."""
    local = [DocumentManifest(doc_id="d1", doc_hash="h1", doc_type="invoice", fields_count=5, file_path="")]
    remote = [DocumentManifest(doc_id="d2", doc_hash="h2", doc_type="contract", fields_count=7, file_path="")]
    result = compare_manifests(local, remote)
    assert len(result["new_remote"]) == 1
    assert len(result["new_local"]) == 1
    assert len(result["shared"]) == 0


def test_compare_manifests_shared():
    """Shared docs are identified by hash."""
    local = [DocumentManifest(doc_id="d1", doc_hash="shared_hash", doc_type="invoice", fields_count=5, file_path="")]
    remote = [DocumentManifest(doc_id="d1", doc_hash="shared_hash", doc_type="invoice", fields_count=5, file_path="")]
    result = compare_manifests(local, remote)
    assert len(result["shared"]) == 1
    assert len(result["new_remote"]) == 0


def test_merge_extractions_higher_confidence():
    """Higher confidence extraction wins."""
    local = [{"field": "vendor_name", "value": "Acme", "confidence": 0.8, "method": "exact"}]
    remote = [{"field": "vendor_name", "value": "Acme Corp", "confidence": 0.95, "method": "exact"}]
    merged = merge_extractions(local, remote)
    assert len(merged) == 1
    assert merged[0]["value"] == "Acme Corp"  # higher confidence


def test_merge_extractions_deeper_cascade():
    """Deeper cascade wins on confidence tie."""
    local = [{"field": "total", "value": "100", "confidence": 0.9, "method": "exact"}]
    remote = [{"field": "total", "value": "100", "confidence": 0.9, "method": "visual"}]
    merged = merge_extractions(local, remote)
    assert merged[0]["method"] == "visual"  # deeper cascade


def test_merge_extractions_new_field():
    """New field from remote is added."""
    local = [{"field": "vendor_name", "value": "Acme", "confidence": 0.9, "method": "exact"}]
    remote = [{"field": "total", "value": "100", "confidence": 0.9, "method": "exact"}]
    merged = merge_extractions(local, remote)
    assert len(merged) == 2
    fields = {e["field"] for e in merged}
    assert "vendor_name" in fields
    assert "total" in fields


def test_sync_manager_add_document():
    """SyncManager adds documents to manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = SyncManager(data_dir=tmpdir)
        path = _make_temp_file("content")
        exts = [_make_extraction("vendor_name", "Acme")]
        manifest = mgr.add_document("doc1", path, "invoice", exts)
        assert len(mgr.get_manifests()) == 1
        assert manifest.doc_id == "doc1"
        os.unlink(path)


def test_sync_manager_sync_with_remote():
    """SyncManager syncs with remote manifests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = SyncManager(data_dir=tmpdir)
        path = _make_temp_file("content")
        exts = [_make_extraction("vendor_name", "Acme")]
        mgr.add_document("doc1", path, "invoice", exts)

        # Remote has same doc with different extraction
        remote = [DocumentManifest(
            doc_id="doc1", doc_hash=compute_doc_hash(path),
            doc_type="invoice", fields_count=1, file_path=path,
            extractions=[{"field": "total", "value": "100", "confidence": 0.9, "method": "exact"}],
        )]

        result = mgr.sync_with_remote(remote)
        assert result["shared_docs"] == 1
        assert "merged_extractions" in result
        os.unlink(path)


def test_sync_manager_connect_infra_pending():
    """Connect returns False (INFRA-PENDING:NETWORK)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = SyncManager(data_dir=tmpdir)
        result = mgr.connect()
        assert result is False  # no daemon in build env


def test_sync_manager_save_load():
    """Manifests persist and load correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = SyncManager(data_dir=tmpdir)
        path = _make_temp_file("content")
        exts = [_make_extraction("vendor_name", "Acme")]
        mgr.add_document("doc1", path, "invoice", exts)
        mgr.save_manifests()

        mgr2 = SyncManager(data_dir=tmpdir)
        mgr2.load_manifests()
        assert len(mgr2.get_manifests()) == 1
        os.unlink(path)