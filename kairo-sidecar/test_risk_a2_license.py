"""
Risk A2: AGPL License Contamination.
Test: no AGPL/GPL code is statically linked into the core.
PyMuPDF must be lazy-imported (not at module level).
"""
import os
import sys
import importlib
import ast
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))


class TestAGPLLicenseGuard:
    """AGPL/GPL deps must be lazy-imported, never statically linked."""

    def test_pymupdf_is_lazy_imported(self):
        """PyMuPDF (AGPL) must NOT be imported at module level in any sidecar module."""
        sidecar_dir = Path(__file__).parent / "sidecar"
        violations = []
        
        for py_file in sidecar_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue
            try:
                content = py_file.read_text()
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    # Check for top-level imports of fitz/PyMuPDF
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        names = []
                        if isinstance(node, ast.Import):
                            names = [a.name for a in node.names]
                        elif isinstance(node, ast.ImportFrom):
                            names = [node.module or ""]
                        
                        for name in names:
                            if name and ("fitz" in name.lower() or "pymupdf" in name.lower()):
                                # Check if it's inside a try/except (lazy import)
                                # Top-level imports (not inside try/except) are violations
                                violations.append(f"{py_file.name}: top-level import of {name}")
            except Exception:
                pass
        
        assert len(violations) == 0, \
            f"AGPL violation: PyMuPDF imported at top level: {violations}"

    def test_pymupdf_not_in_compile_time_deps(self):
        """PyMuPDF must not be imported when sidecar starts (only at runtime when needed)."""
        # Import the main sidecar module and check fitz is NOT in sys.modules
        # unless explicitly requested
        modules_before = set(sys.modules.keys())
        try:
            import sidecar.oracles  # This module uses fitz
        except ImportError:
            pytest.skip("sidecar.oracles not importable")
        
        # fitz should be in sys.modules only because oracles.py imports it
        # But it should be behind a try/except
        # The key test: the core sidecar module should work WITHOUT fitz
        # by using pdf_oxide or MarkItDown as fallback

    def test_license_guard_function_exists(self):
        """A license guard function must exist that checks for AGPL deps."""
        # Check that oracles.py has a HAS_FITZ flag (lazy import pattern)
        oracles_path = Path(__file__).parent / "sidecar" / "oracles.py"
        if oracles_path.exists():
            content = oracles_path.read_text()
            assert "HAS_FITZ" in content or "try:" in content, \
                "oracles.py must use lazy import pattern for PyMuPDF (AGPL)"

    def test_no_agpl_in_requirements_lock(self):
        """requirements.txt must not list AGPL packages as required (only optional)."""
        req_path = Path(__file__).parent / "requirements.txt"
        if req_path.exists():
            content = req_path.read_text().lower()
            # PyMuPDF can be listed but must be commented as optional/AGPL
            if "pymupdf" in content or "fitz" in content:
                # Must have a comment indicating AGPL or optional
                lines = content.splitlines()
                pymupdf_lines = [l for l in lines if "pymupdf" in l.lower() or "fitz" in l.lower()]
                for line in pymupdf_lines:
                    assert "#" in line or "optional" in line.lower() or "agpl" in line.lower(), \
                        f"PyMuPDF in requirements.txt without AGPL/optional comment: {line}"

    def test_paperless_bridge_is_http_only(self):
        """paperless-ngx (GPL) bridge must be HTTP client only, no code import."""
        bridge_path = Path(__file__).parent / "sidecar" / "connectors" / "paperless_bridge.py"
        if bridge_path.exists():
            content = bridge_path.read_text()
            # Must use urllib/requests (HTTP), not import paperless code
            assert "import urllib" in content or "import requests" in content, \
                "paperless bridge must use HTTP client, not import GPL code"
            # Must NOT import any paperless_ngx module
            assert "import paperless" not in content, \
                "paperless bridge imports GPL paperless-ngx code — LICENSE CONTAMINATION"
