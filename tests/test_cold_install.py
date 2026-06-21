"""
Kairo Phantom — P0.1 Cold-Install Integration Test

Simulates a fresh environment check and verifies all required dependencies
are documented. This test is FAILING-CAPABLE: if a required dependency is
missing from the documentation or the environment, this test will fail.

No mocks, no stubs. Checks real files and real importability.
"""
from __future__ import annotations

import importlib
import pathlib
import re
import subprocess
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Required dependencies (must be documented + importable)
# ---------------------------------------------------------------------------

# Core dependencies that the kernel + pipeline require.
# Each entry: (import_name, pip_name, description)
REQUIRED_DEPS = [
    ("numpy", "numpy", "Numerical computing for embeddings"),
]

# Kernel modules that must be importable
REQUIRED_KERNEL_MODULES = [
    "kernel",
    "kernel.core.data_model",
    "kernel.core.contracts",
    "kernel.core.grounding",
    "kernel.core.embeddings",
    "kernel.core.provenance",
    "kernel.sidecar.ingestor",
    "kernel.sidecar.orchestrator",
    "kernel.sidecar.security_filter",
    "kernel.sidecar.inference_gateway",
    "kernel.sidecar.quality_gate",
    "kernel.sidecar.memory_store",
]


# ---------------------------------------------------------------------------
# Tests: Dependencies are documented
# ---------------------------------------------------------------------------

def test_readme_documents_dependencies():
    """The README must document all required dependencies in the quickstart."""
    readme = (_REPO_ROOT / "README.md").read_text()
    # Must mention pip install or equivalent
    assert "pip install" in readme.lower() or "pip3 install" in readme.lower(), (
        "README does not document pip install step for dependencies"
    )
    # Must mention numpy
    assert "numpy" in readme.lower(), (
        "README does not document numpy as a dependency"
    )


def test_readme_has_quickstart_section():
    """The README must have a quickstart section that is copy-paste exact."""
    readme = (_REPO_ROOT / "README.md").read_text()
    # Must have a quickstart or getting started section
    has_quickstart = any(
        kw in readme.lower()
        for kw in ["quickstart", "quick start", "getting started", "## install"]
    )
    assert has_quickstart, (
        "README does not have a quickstart/getting-started section"
    )


def test_readme_documents_make_run():
    """The README must document the `make run` command."""
    readme = (_REPO_ROOT / "README.md").read_text()
    assert "make run" in readme, (
        "README does not document the `make run` command"
    )


def test_readme_documents_sidecar_purpose():
    """The README must explain WHY the sidecar is Python."""
    readme = (_REPO_ROOT / "README.md").read_text()
    # Must mention OCR, Docling, or layout as the reason for Python sidecar
    has_reason = any(
        kw in readme.lower()
        for kw in ["docling", "ocr", "layout", "python-native", "python native"]
    )
    assert has_reason, (
        "README does not explain why the sidecar is Python "
        "(OCR/layout engines like Docling are Python-native)"
    )


# ---------------------------------------------------------------------------
# Tests: Dependencies are importable (simulates fresh env check)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("import_name,pip_name,description", REQUIRED_DEPS)
def test_dependency_importable(import_name, pip_name, description):
    """Each required dependency must be importable in the current environment."""
    try:
        importlib.import_module(import_name)
    except ImportError:
        pytest.fail(
            f"Required dependency '{pip_name}' ({description}) is not installed. "
            f"Install with: pip install {pip_name}"
        )


@pytest.mark.parametrize("module_name", REQUIRED_KERNEL_MODULES)
def test_kernel_module_importable(module_name):
    """Each required kernel module must be importable."""
    try:
        importlib.import_module(module_name)
    except ImportError as e:
        pytest.fail(
            f"Required kernel module '{module_name}' is not importable: {e}"
        )


# ---------------------------------------------------------------------------
# Tests: Required files exist
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filepath", [
    "scripts/qa_pipeline.py",
    "scripts/first_run.py",
    "docker/Dockerfile",
    "Makefile",
    "README.md",
    "samples/invoice/sample_invoice_01.txt",
    "samples/invoice/ground_truth.json",
    "samples/contract/sample_contract_01.txt",
    "samples/contract/ground_truth.json",
    "samples/paper/sample_paper_01.txt",
    "samples/paper/ground_truth.json",
    "samples/generic/sample_generic_01.txt",
    "samples/generic/ground_truth.json",
])
def test_required_file_exists(filepath):
    """All required files for the runnable artifact must exist."""
    path = _REPO_ROOT / filepath
    assert path.exists(), (
        f"Required file missing: {filepath}"
    )


# ---------------------------------------------------------------------------
# Tests: Sample ground_truth.json files are valid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pack_dir", [
    "samples/invoice",
    "samples/contract",
    "samples/paper",
    "samples/generic",
])
def test_sample_ground_truth_valid(pack_dir):
    """Each sample's ground_truth.json must have answerable + unanswerable questions."""
    import json
    gt_path = _REPO_ROOT / pack_dir / "ground_truth.json"
    assert gt_path.exists(), f"ground_truth.json missing in {pack_dir}"

    data = json.loads(gt_path.read_text())
    assert "questions" in data, f"No 'questions' key in {gt_path}"
    assert len(data["questions"]) >= 2, (
        f"Expected at least 2 questions in {gt_path}, got {len(data['questions'])}"
    )

    has_answerable = any(q.get("answerable") for q in data["questions"])
    has_unanswerable = any(not q.get("answerable") for q in data["questions"])
    assert has_answerable, (
        f"No answerable question in {gt_path} — need at least one grounded answer demo"
    )
    assert has_unanswerable, (
        f"No unanswerable question in {gt_path} — need at least one refusal demo"
    )


# ---------------------------------------------------------------------------
# Tests: Dockerfile exists and is valid
# ---------------------------------------------------------------------------

def test_dockerfile_valid():
    """The Dockerfile must be a valid Dockerfile with required instructions."""
    dockerfile = (_REPO_ROOT / "docker" / "Dockerfile").read_text()
    assert "FROM" in dockerfile, "Dockerfile missing FROM instruction"
    assert "COPY" in dockerfile, "Dockerfile missing COPY instruction"
    assert "CMD" in dockerfile or "ENTRYPOINT" in dockerfile, (
        "Dockerfile missing CMD or ENTRYPOINT"
    )
    # Must set local-first environment
    assert "KAIRO" in dockerfile, (
        "Dockerfile should set KAIRO environment variables for local-first mode"
    )


# ---------------------------------------------------------------------------
# Tests: Makefile has run and samples targets
# ---------------------------------------------------------------------------

def test_makefile_has_run_target():
    """The Makefile must have a `run` target."""
    makefile = (_REPO_ROOT / "Makefile").read_text()
    assert re.search(r"^run\s*:", makefile, re.MULTILINE), (
        "Makefile does not have a 'run' target"
    )


def test_makefile_has_samples_target():
    """The Makefile must have a `samples` target."""
    makefile = (_REPO_ROOT / "Makefile").read_text()
    assert re.search(r"^samples\s*:", makefile, re.MULTILINE), (
        "Makefile does not have a 'samples' target"
    )


# ---------------------------------------------------------------------------
# Tests: first_run.py is executable and functional
# ---------------------------------------------------------------------------

def test_first_run_script_exists_and_runs():
    """scripts/first_run.py must exist and run successfully."""
    result = subprocess.run(
        [sys.executable, "scripts/first_run.py"],
        capture_output=True, text=True, timeout=30,
        cwd=str(_REPO_ROOT),
    )
    # exit 0 = grounded answer produced (success)
    assert result.returncode == 0, (
        f"first_run.py failed with exit code {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "GROUNDED" in result.stdout, (
        f"first_run.py did not produce a grounded answer\n"
        f"stdout: {result.stdout}"
    )
    assert "bounding box" in result.stdout.lower() or "bbox" in result.stdout.lower(), (
        f"first_run.py did not show source region (bounding box)\n"
        f"stdout: {result.stdout}"
    )
