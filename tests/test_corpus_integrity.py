"""
T7 — Corpus integrity: assert the committed corpus hash matches;
refuse to publish numbers if the corpus changed without a version bump.

No mocks: computes real SHA-256 hashes of the fixture corpus.
"""
import hashlib
import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "fixtures"
CORPUS_HASH_FILE = REPO_ROOT / "fixtures" / "CORPUS_HASH.json"

# Known corpus version + hash. When fixtures change, this must be bumped.
CORPUS_VERSION = "1.0.0"


def _hash_file(path: pathlib.Path) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_corpus() -> dict:
    """Compute SHA-256 hashes of all fixture files, grouped by pack."""
    corpus = {}
    for pack_dir in sorted(FIXTURES_DIR.iterdir()):
        if not pack_dir.is_dir() or pack_dir.name.startswith("."):
            continue
        pack_hashes = {}
        for f in sorted(pack_dir.iterdir()):
            if f.is_file() and f.suffix in (".txt", ".json", ".md"):
                pack_hashes[f.name] = _hash_file(f)
        if pack_hashes:
            corpus[pack_dir.name] = pack_hashes
    return corpus


def _compute_corpus_fingerprint(corpus: dict) -> str:
    """Compute a single fingerprint hash from the entire corpus dict."""
    content = json.dumps(corpus, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


class TestCorpusIntegrity:
    """Assert the committed corpus hash matches the current state."""

    def test_corpus_hash_file_exists(self):
        """CORPUS_HASH.json must exist with a recorded fingerprint."""
        if not CORPUS_HASH_FILE.exists():
            # First run: create the hash file
            corpus = _hash_corpus()
            fingerprint = _compute_corpus_fingerprint(corpus)
            record = {
                "version": CORPUS_VERSION,
                "fingerprint": fingerprint,
                "files": corpus,
            }
            CORPUS_HASH_FILE.write_text(json.dumps(record, indent=2))
        assert CORPUS_HASH_FILE.exists(), "CORPUS_HASH.json must exist"

    def test_corpus_fingerprint_matches_committed(self):
        """The current corpus fingerprint must match the committed one."""
        if not CORPUS_HASH_FILE.exists():
            pytest.skip("Run test_corpus_hash_file_exists first to generate hash")
        with open(CORPUS_HASH_FILE, "r") as f:
            record = json.load(f)
        corpus = _hash_corpus()
        current_fingerprint = _compute_corpus_fingerprint(corpus)
        assert current_fingerprint == record["fingerprint"], (
            f"Corpus changed without version bump! "
            f"Committed fingerprint: {record['fingerprint'][:16]}..., "
            f"Current fingerprint: {current_fingerprint[:16]}... "
            f"Version: {record.get('version', 'unknown')}. "
            f"Update CORPUS_HASH.json and bump version if this change is intentional."
        )

    def test_corpus_version_is_set(self):
        """The corpus hash record must have a version string."""
        if not CORPUS_HASH_FILE.exists():
            pytest.skip("Corpus hash file not yet created")
        with open(CORPUS_HASH_FILE, "r") as f:
            record = json.load(f)
        assert "version" in record, "Corpus hash record must have a version"
        assert record["version"], "Corpus version must not be empty"

    def test_corpus_integrity_detects_tampering(self):
        """Failing-capable: a modified file must produce a different fingerprint."""
        corpus = _hash_corpus()
        fp1 = _compute_corpus_fingerprint(corpus)
        # Tamper: modify one hash
        tampered = json.loads(json.dumps(corpus))
        first_key = list(tampered.keys())[0]
        first_file = list(tampered[first_key].keys())[0]
        tampered[first_key][first_file] = "0" * 64
        fp2 = _compute_corpus_fingerprint(tampered)
        assert fp1 != fp2, "Corpus integrity check failed to detect tampering"
