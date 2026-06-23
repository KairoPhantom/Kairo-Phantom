"""
Kairo P2P Sync Manager — Zero-Cloud Document Sync.

Wraps a P2P sync engine for document synchronization between Kairo instances.
Data only moves between paired devices — no relay, no third party, no cloud.

The sync protocol:
  1. Manifest exchange: compute {doc_hash, doc_type, fields_count} for all docs
  2. Compare manifests between devices
  3. Extraction merge: merge per field keeping higher confidence
     If equal confidence, keep deeper cascade (VISUAL > SEMANTIC > FUZZY > EXACT)

Note: The actual P2P transport requires a running sync daemon on each device.
In this build environment, the daemon is not available (INFRA-PENDING:NETWORK).
The merge logic and manifest format are fully implemented and tested.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kernel.core.data_model import Extraction, GroundingMethod

logger = logging.getLogger(__name__)

# Cascade depth ordering (deeper = higher priority for merge tiebreaker)
_CASCADE_DEPTH = {
    GroundingMethod.VISUAL: 4,
    GroundingMethod.SEMANTIC: 3,
    GroundingMethod.FUZZY: 2,
    GroundingMethod.EXACT: 1,
    GroundingMethod.BLOCK: 0,
}


@dataclass
class DocumentManifest:
    """Manifest entry for a single document."""
    doc_id: str
    doc_hash: str
    doc_type: str
    fields_count: int
    file_path: str
    extractions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "doc_hash": self.doc_hash,
            "doc_type": self.doc_type,
            "fields_count": self.fields_count,
            "file_path": self.file_path,
            "extractions": self.extractions,
        }


def compute_doc_hash(file_path: str) -> str:
    """Compute SHA256 hash of a document file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(doc_id: str, file_path: str, doc_type: str,
                   extractions: list[Extraction]) -> DocumentManifest:
    """Build a manifest entry for a document with its extractions.

    Args:
        doc_id: Document ID.
        file_path: Path to the document file.
        doc_type: Document type (invoice, contract, paper, generic).
        extractions: List of Extraction objects.

    Returns:
        DocumentManifest with hash and serialized extractions.
    """
    doc_hash = compute_doc_hash(file_path)
    ext_data = []
    for ext in extractions:
        ext_data.append({
            "field": ext.field_name,
            "value": ext.value,
            "confidence": ext.confidence,
            "method": ext.method.value,
            "chunk_id": ext.chunk_id,
        })
    return DocumentManifest(
        doc_id=doc_id,
        doc_hash=doc_hash,
        doc_type=doc_type,
        fields_count=len(extractions),
        file_path=file_path,
        extractions=ext_data,
    )


def compare_manifests(local: list[DocumentManifest],
                      remote: list[DocumentManifest]) -> dict[str, Any]:
    """Compare local and remote manifests.

    Returns:
        Dict with: new_remote (docs only on remote), new_local (docs only on local),
        shared (docs on both), conflicts (same doc, different extractions).
    """
    local_map = {m.doc_hash: m for m in local}
    remote_map = {m.doc_hash: m for m in remote}

    new_remote = [m for h, m in remote_map.items() if h not in local_map]
    new_local = [m for h, m in local_map.items() if h not in remote_map]
    shared_hashes = [h for h in local_map if h in remote_map]
    conflicts = []

    for h in shared_hashes:
        local_m = local_map[h]
        remote_m = remote_map[h]
        if local_m.fields_count != remote_m.fields_count:
            conflicts.append(h)
        else:
            # Check if extractions differ
            local_fields = {e["field"] for e in local_m.extractions}
            remote_fields = {e["field"] for e in remote_m.extractions}
            if local_fields != remote_fields:
                conflicts.append(h)

    return {
        "new_remote": [m.to_dict() for m in new_remote],
        "new_local": [m.to_dict() for m in new_local],
        "shared": shared_hashes,
        "conflicts": conflicts,
    }


def merge_extractions(local_exts: list[dict[str, Any]],
                      remote_exts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge extractions from two devices.

    Per-field merge rules:
      - Keep higher confidence
      - If equal confidence, keep deeper cascade (VISUAL > SEMANTIC > FUZZY > EXACT)

    Args:
        local_exts: Local extraction dicts (field, value, confidence, method).
        remote_exts: Remote extraction dicts.

    Returns:
        Merged list of extraction dicts.
    """
    merged: dict[str, dict[str, Any]] = {}

    # Add local extractions
    for ext in local_exts:
        merged[ext["field"]] = ext

    # Merge remote extractions
    for ext in remote_exts:
        field = ext["field"]
        if field not in merged:
            merged[field] = ext
        else:
            existing = merged[field]
            # Keep higher confidence
            if ext["confidence"] > existing["confidence"]:
                merged[field] = ext
            elif ext["confidence"] == existing["confidence"]:
                # Tiebreaker: deeper cascade
                ext_depth = _CASCADE_DEPTH.get(GroundingMethod(ext["method"]), 0)
                existing_depth = _CASCADE_DEPTH.get(GroundingMethod(existing["method"]), 0)
                if ext_depth > existing_depth:
                    merged[field] = ext

    return list(merged.values())


class SyncManager:
    """Manages P2P document sync between Kairo instances.

    Note: The actual P2P transport requires a running sync daemon.
    INFRA-PENDING:NETWORK — the daemon is not available in this build env.
    The merge logic and manifest format are fully implemented.
    """

    def __init__(self, data_dir: str = "data") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._manifests: list[DocumentManifest] = []
        self._connected = False

    def add_document(self, doc_id: str, file_path: str, doc_type: str,
                     extractions: list[Extraction]) -> DocumentManifest:
        """Add a document to the local manifest."""
        manifest = build_manifest(doc_id, file_path, doc_type, extractions)
        self._manifests.append(manifest)
        return manifest

    def get_manifests(self) -> list[DocumentManifest]:
        """Get all local manifests."""
        return self._manifests

    def connect(self, api_key: str = "", port: int = 8384) -> bool:
        """Connect to the local sync daemon.

        INFRA-PENDING:NETWORK — requires a running sync daemon.
        """
        try:
            # In production, this would connect to the sync daemon's REST API
            # from syncthing import Syncthing
            # self._client = Syncthing(api_key=api_key, port=port)
            # self._connected = True
            logger.warning("Sync daemon connection is INFRA-PENDING:NETWORK (no daemon in build env)")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect to sync daemon: {e}")
            return False

    def sync_with_remote(self, remote_manifests: list[DocumentManifest]) -> dict[str, Any]:
        """Sync with a remote device's manifests.

        Args:
            remote_manifests: Manifests from the remote device.

        Returns:
            Sync result with new docs, conflicts, and merged extractions.
        """
        comparison = compare_manifests(self._manifests, remote_manifests)

        # Merge extractions for shared docs
        merged = {}
        local_map = {m.doc_hash: m for m in self._manifests}
        remote_map = {m.doc_hash: m for m in remote_manifests}
        for h in comparison["shared"]:
            if h in local_map and h in remote_map:
                merged[h] = merge_extractions(
                    local_map[h].extractions,
                    remote_map[h].extractions,
                )

        return {
            "new_remote_docs": len(comparison["new_remote"]),
            "new_local_docs": len(comparison["new_local"]),
            "shared_docs": len(comparison["shared"]),
            "conflicts": len(comparison["conflicts"]),
            "merged_extractions": merged,
            "comparison": comparison,
        }

    def save_manifests(self) -> None:
        """Save manifests to disk."""
        path = self._data_dir / "manifests.json"
        data = [m.to_dict() for m in self._manifests]
        path.write_text(json.dumps(data, indent=2))

    def load_manifests(self) -> None:
        """Load manifests from disk."""
        path = self._data_dir / "manifests.json"
        if path.exists():
            data = json.loads(path.read_text())
            self._manifests = [
                DocumentManifest(
                    doc_id=m["doc_id"], doc_hash=m["doc_hash"],
                    doc_type=m["doc_type"], fields_count=m["fields_count"],
                    file_path=m["file_path"], extractions=m.get("extractions", []),
                )
                for m in data
            ]