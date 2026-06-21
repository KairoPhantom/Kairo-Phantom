"""
Tests for X4 — Golden Corpus Snapshot Tests

The test itself IS the test: it asserts current output matches golden snapshots.
If grounding changes, the test fails and the diff is reviewable.

A changed grounding is a deliberate, reviewed decision — never an accident.
"""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kernel.core.grounding import GroundingVerifierImpl
from kernel.core.data_model import Chunk, BBox, GroundingMethod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
GOLDEN_CORPUS_DIR = os.path.join(REPO_ROOT, "fixtures", "golden_corpus")
SNAPSHOTS_FILE = os.path.join(GOLDEN_CORPUS_DIR, "snapshots.json")
FIXTURES_DIR = os.path.join(REPO_ROOT, "fixtures")


def make_chunks_from_text(text: str, doc_id: str) -> list[Chunk]:
    """Split text into chunks with bboxes, matching the snapshot generation logic."""
    lines = [l for l in text.split('\n') if l.strip()]
    chunks = []
    for i, line in enumerate(lines):
        chunks.append(Chunk(
            chunk_id=f"{doc_id}_chunk_{i}",
            doc_id=doc_id,
            page=1,
            bbox=BBox(0.05, 0.05 + i * 0.05, 0.95, 0.10 + i * 0.05),
            text=line,
        ))
    return chunks


def load_golden_snapshots() -> list[dict]:
    """Load the golden snapshots from disk."""
    with open(SNAPSHOTS_FILE) as f:
        data = json.load(f)
    return data["snapshots"]


def run_current_grounding(snapshot: dict) -> dict:
    """Re-run the grounding verifier for a single snapshot case and return current results."""
    doc_path = os.path.join(REPO_ROOT, snapshot["doc_file"])
    with open(doc_path) as f:
        doc_text = f.read()

    chunks = make_chunks_from_text(doc_text, snapshot["doc_id"])
    verifier = GroundingVerifierImpl()
    method, anchors = verifier.verify(
        value=snapshot["value"],
        source_span=snapshot["source_span"],
        chunks=chunks,
    )

    return {
        "grounding_method": method.value,
        "grounded": method != GroundingMethod.BLOCK,
        "anchor_count": len(anchors),
        "anchor_page": anchors[0].page if anchors else None,
        "anchor_chunk_id": anchors[0].chunk_id if anchors else None,
        "anchor_char_span": list(anchors[0].char_span) if anchors else None,
        "anchor_bbox": (
            [anchors[0].bbox.x0, anchors[0].bbox.y0, anchors[0].bbox.x1, anchors[0].bbox.y1]
            if (anchors and anchors[0].bbox) else None
        ),
    }


# ---------------------------------------------------------------------------
# Test 1: Golden snapshots file exists and is valid
# ---------------------------------------------------------------------------
class TestGoldenSnapshotsExist:
    """The golden snapshots file must exist and be valid."""

    def test_snapshots_file_exists(self):
        """snapshots.json must exist."""
        assert os.path.exists(SNAPSHOTS_FILE), \
            f"Golden snapshots file must exist at {SNAPSHOTS_FILE}"

    def test_snapshots_file_is_valid_json(self):
        """snapshots.json must be valid JSON with a 'snapshots' key."""
        data = load_golden_snapshots()
        assert isinstance(data, list), "snapshots must be a list"
        assert len(data) > 0, "snapshots must not be empty"

    def test_readme_exists(self):
        """The golden corpus README must exist."""
        readme = os.path.join(GOLDEN_CORPUS_DIR, "README.md")
        assert os.path.exists(readme), "Golden corpus README must exist"


# ---------------------------------------------------------------------------
# Test 2: Current output matches golden snapshots
# ---------------------------------------------------------------------------
class TestCurrentMatchesGolden:
    """Current grounding output must match the golden snapshots exactly.

    If this test fails, grounding has changed. Review the diff to confirm
    the change is deliberate, then regenerate snapshots.
    """

    @pytest.fixture
    def snapshots(self):
        return load_golden_snapshots()

    def test_snapshot_count_matches(self, snapshots):
        """The number of snapshots must be stable."""
        assert len(snapshots) == 14, \
            f"Expected 14 golden snapshots, got {len(snapshots)}. " \
            "If you added/removed cases, update this count and regenerate."

    def test_all_grounded_answers_match(self, snapshots):
        """Every grounded answer snapshot must produce the same grounding method."""
        grounded_snapshots = [s for s in snapshots if s["expected_outcome"] == "answer"]
        assert len(grounded_snapshots) > 0, "Must have at least one answer snapshot"

        mismatches = []
        for snap in grounded_snapshots:
            current = run_current_grounding(snap)
            if current["grounding_method"] != snap["grounding_method"]:
                mismatches.append(
                    f"  {snap['case_id']}: expected {snap['grounding_method']}, "
                    f"got {current['grounding_method']} (Q: {snap['question'][:40]})"
                )

        assert not mismatches, \
            "Grounding method changed for answer cases:\n" + "\n".join(mismatches)

    def test_all_refusals_match(self, snapshots):
        """Every refusal snapshot must still be refused (BLOCK)."""
        refusal_snapshots = [s for s in snapshots if s["expected_outcome"] == "refusal"]
        assert len(refusal_snapshots) > 0, "Must have at least one refusal snapshot"

        mismatches = []
        for snap in refusal_snapshots:
            current = run_current_grounding(snap)
            if current["grounded"] != snap["grounded"]:
                mismatches.append(
                    f"  {snap['case_id']}: expected grounded={snap['grounded']}, "
                    f"got grounded={current['grounded']} (Q: {snap['question'][:40]})"
                )

        assert not mismatches, \
            "Refusal behavior changed — a previously refused question is now grounded:\n" \
            + "\n".join(mismatches)

    def test_anchor_pages_match(self, snapshots):
        """Anchor page numbers must match the golden snapshots."""
        for snap in snapshots:
            if snap["expected_outcome"] != "answer":
                continue
            current = run_current_grounding(snap)
            if current["anchor_page"] != snap["anchor_page"]:
                pytest.fail(
                    f"{snap['case_id']}: anchor page changed from {snap['anchor_page']} "
                    f"to {current['anchor_page']}"
                )

    def test_anchor_bboxes_match(self, snapshots):
        """Anchor bounding boxes must match the golden snapshots."""
        for snap in snapshots:
            if snap["expected_outcome"] != "answer" or snap["anchor_bbox"] is None:
                continue
            current = run_current_grounding(snap)
            if current["anchor_bbox"] is None:
                pytest.fail(f"{snap['case_id']}: anchor bbox is None but golden has one")
            if current["anchor_bbox"] != snap["anchor_bbox"]:
                pytest.fail(
                    f"{snap['case_id']}: anchor bbox changed from {snap['anchor_bbox']} "
                    f"to {current['anchor_bbox']}"
                )

    def test_answer_count_in_snapshots(self, snapshots):
        """There must be a mix of answers and refusals in the golden corpus."""
        answers = [s for s in snapshots if s["expected_outcome"] == "answer"]
        refusals = [s for s in snapshots if s["expected_outcome"] == "refusal"]
        assert len(answers) >= 10, f"Must have at least 10 answer snapshots, got {len(answers)}"
        assert len(refusals) >= 4, f"Must have at least 4 refusal snapshots, got {len(refusals)}"


# ---------------------------------------------------------------------------
# Test 3: All four Packs are represented
# ---------------------------------------------------------------------------
class TestAllPacksRepresented:
    """The golden corpus must cover all four launch Packs."""

    def test_contract_pack_represented(self):
        """Contract pack must have golden cases."""
        snapshots = load_golden_snapshots()
        contract_cases = [s for s in snapshots if "contract" in s["doc_id"]]
        assert len(contract_cases) >= 3, "Must have at least 3 contract golden cases"

    def test_invoice_pack_represented(self):
        """Invoice pack must have golden cases."""
        snapshots = load_golden_snapshots()
        invoice_cases = [s for s in snapshots if "invoice" in s["doc_id"]]
        assert len(invoice_cases) >= 3, "Must have at least 3 invoice golden cases"

    def test_paper_pack_represented(self):
        """Paper pack must have golden cases."""
        snapshots = load_golden_snapshots()
        paper_cases = [s for s in snapshots if "paper" in s["doc_id"]]
        assert len(paper_cases) >= 2, "Must have at least 2 paper golden cases"

    def test_generic_pack_represented(self):
        """Generic pack must have golden cases."""
        snapshots = load_golden_snapshots()
        generic_cases = [s for s in snapshots if "generic" in s["doc_id"]]
        assert len(generic_cases) >= 2, "Must have at least 2 generic golden cases"


# ---------------------------------------------------------------------------
# Test 4: Snapshot integrity (each snapshot has required fields)
# ---------------------------------------------------------------------------
class TestSnapshotIntegrity:
    """Each golden snapshot must have all required fields."""

    def test_all_snapshots_have_required_fields(self):
        """Every snapshot must have case_id, doc_file, question, expected_outcome."""
        snapshots = load_golden_snapshots()
        required_fields = [
            "case_id", "doc_file", "doc_id", "question", "value",
            "source_span", "expected_outcome", "grounding_method", "grounded",
        ]
        for snap in snapshots:
            for field in required_fields:
                assert field in snap, \
                    f"Snapshot {snap.get('case_id', '?')} missing field '{field}'"

    def test_doc_files_exist(self):
        """Every snapshot's doc_file must exist on disk."""
        snapshots = load_golden_snapshots()
        for snap in snapshots:
            doc_path = os.path.join(REPO_ROOT, snap["doc_file"])
            assert os.path.exists(doc_path), \
                f"Document file does not exist: {snap['doc_file']} (case {snap['case_id']})"


# ---------------------------------------------------------------------------
# Regeneration utility (not a test — used when intentionally updating snapshots)
# ---------------------------------------------------------------------------
def regenerate():
    """Regenerate golden snapshots from current verifier output.

    Only call this when you have intentionally changed grounding behavior
    and reviewed the diff. See fixtures/golden_corpus/README.md.
    """
    from kernel.core.grounding import GroundingVerifierImpl
    from kernel.core.data_model import Chunk, BBox, GroundingMethod

    verifier = GroundingVerifierImpl()
    snapshots = load_golden_snapshots()

    updated = []
    for snap in snapshots:
        doc_path = os.path.join(REPO_ROOT, snap["doc_file"])
        with open(doc_path) as f:
            doc_text = f.read()
        chunks = make_chunks_from_text(doc_text, snap["doc_id"])
        method, anchors = verifier.verify(
            value=snap["value"], source_span=snap["source_span"], chunks=chunks,
        )
        snap["grounding_method"] = method.value
        snap["grounded"] = method != GroundingMethod.BLOCK
        snap["anchor_count"] = len(anchors)
        snap["anchor_page"] = anchors[0].page if anchors else None
        snap["anchor_chunk_id"] = anchors[0].chunk_id if anchors else None
        snap["anchor_char_span"] = list(anchors[0].char_span) if anchors else None
        snap["anchor_bbox"] = (
            [anchors[0].bbox.x0, anchors[0].bbox.y0, anchors[0].bbox.x1, anchors[0].bbox.y1]
            if (anchors and anchors[0].bbox) else None
        )
        updated.append(snap)

    with open(SNAPSHOTS_FILE, "w") as f:
        json.dump({"snapshots": updated}, f, indent=2)
    print(f"Regenerated {len(updated)} golden snapshots")