"""
Kairo Phantom — Replication Tests (P2.3)

Runs the replication harness end-to-end on the public corpus and asserts
it completes and matches committed results within tolerance.

No mocks — this test runs the real replication harness.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"


# ---------------------------------------------------------------------------
# Replication harness tests
# ---------------------------------------------------------------------------
def test_replicate_module_imports():
    """The replicate module must import without error."""
    from scripts import replicate
    assert hasattr(replicate, "run_replication"), \
        "replicate module missing run_replication function"


def test_replication_runs_end_to_end():
    """The replication harness must run end-to-end on the public corpus."""
    from scripts.replicate import run_replication
    report = run_replication()
    assert report is not None, "Replication returned None"
    assert "packs" in report, "Replication report missing 'packs' key"
    assert "gates" in report, "Replication report missing 'gates' key"


def test_replication_covers_all_four_packs():
    """The replication must cover all 4 Packs: generic, invoice, paper, contract."""
    from scripts.replicate import run_replication
    report = run_replication()
    packs = report["packs"]
    for expected_pack in ("generic", "invoice", "paper", "contract"):
        assert expected_pack in packs, \
            f"Replication missing pack: {expected_pack}"


def test_replication_has_corpus_hash():
    """The replication report must include a corpus hash for reproducibility."""
    from scripts.replicate import run_replication
    report = run_replication()
    assert "corpus_hash" in report, "Replication report missing corpus_hash"
    assert len(report["corpus_hash"]) == 64, \
        f"Corpus hash must be 64 chars (SHA-256), got {len(report['corpus_hash'])}"


def test_replication_has_all_four_gates():
    """The replication report must include all 4 hard gates."""
    from scripts.replicate import run_replication
    report = run_replication()
    gates = report["gates"]
    for gate in ("grounded_answer_rate", "false_refusal_rate",
                 "refusal_on_unanswerable", "ungrounded_render_count"):
        assert gate in gates, f"Replication report missing gate: {gate}"


def test_replication_report_file_written():
    """The replication must write REPLICATE_REPORT.json."""
    from scripts.replicate import run_replication
    run_replication()
    report_path = REPO_ROOT / "bench" / "REPLICATE_REPORT.json"
    assert report_path.exists(), "REPLICATE_REPORT.json not written"
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert "packs" in data, "Report file missing 'packs' key"


def test_replication_markdown_report_written():
    """The replication must write REPLICATE_REPORT.md."""
    from scripts.replicate import run_replication
    run_replication()
    md_path = REPO_ROOT / "bench" / "REPLICATE_REPORT.md"
    assert md_path.exists(), "REPLICATE_REPORT.md not written"
    content = md_path.read_text(encoding="utf-8")
    assert "Replication Report" in content, "Markdown report missing title"
    assert "Grounded-Answer Rate" in content, "Markdown report missing metrics"


def test_replication_ungrounded_render_count_is_zero():
    """The replication must show zero ungrounded renders."""
    from scripts.replicate import run_replication
    report = run_replication()
    ungrounded = report["gates"]["ungrounded_render_count"]["measured"]
    assert ungrounded == 0, \
        f"REGRESSION: {ungrounded} ungrounded renders detected (must be 0)"


def test_replication_refusal_on_unanswerable_is_100():
    """Refusal on unanswerable must be 100%."""
    from scripts.replicate import run_replication
    report = run_replication()
    refusal = report["gates"]["refusal_on_unanswerable"]["measured"]
    assert refusal == 100.0, \
        f"REGRESSION: refusal_on_unanswerable is {refusal}%, expected 100%"


def test_replication_per_pack_has_documents():
    """Each pack in the replication report must have per-document results."""
    from scripts.replicate import run_replication
    report = run_replication()
    for pack_name, pack_data in report["packs"].items():
        assert "per_document" in pack_data, \
            f"Pack {pack_name} missing per_document results"
        assert len(pack_data["per_document"]) > 0, \
            f"Pack {pack_name} has no documents in replication"


def test_replication_results_match_committed_within_tolerance():
    """Replication results must match the committed bench report within tolerance."""
    from scripts.replicate import run_replication
    report = run_replication()

    # Compare against committed REPORT.json if it exists
    committed_path = REPO_ROOT / "bench" / "REPORT.json"
    if not committed_path.exists():
        pytest.skip("No committed REPORT.json to compare against")

    committed = json.loads(committed_path.read_text(encoding="utf-8"))

    # Compare gate values within ±5% tolerance (rates may vary slightly)
    tolerance = 5.0
    for gate_name in ("grounded_answer_rate", "false_refusal_rate"):
        if gate_name in committed.get("gates", {}) and gate_name in report["gates"]:
            committed_val = committed["gates"][gate_name]["measured"]
            replicated_val = report["gates"][gate_name]["measured"]
            diff = abs(replicated_val - committed_val)
            assert diff <= tolerance, \
                f"Gate {gate_name}: replicated={replicated_val}, committed={committed_val}, " \
                f"diff={diff} exceeds tolerance={tolerance}"


def test_replicate_md_exists():
    """REPLICATE.md documentation must exist."""
    replicate_md = REPO_ROOT / "REPLICATE.md"
    assert replicate_md.exists(), "REPLICATE.md not found"
    content = replicate_md.read_text(encoding="utf-8")
    assert "replicate.py" in content, "REPLICATE.md must reference scripts/replicate.py"
    assert "Step" in content, "REPLICATE.md must have step-by-step instructions"


def test_replication_is_deterministic():
    """Running replication twice should produce the same corpus hash."""
    from scripts.replicate import run_replication
    r1 = run_replication()
    r2 = run_replication()
    assert r1["corpus_hash"] == r2["corpus_hash"], \
        "Corpus hash is not deterministic across runs"
