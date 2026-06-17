#!/usr/bin/env python3
"""
Kernel Purity Guard (SPEC §S0, CI-blocking)

Ensures the kernel imports NOTHING from /domains or /legacy.
Scans all .py files under kernel/ for prohibited imports.

Exit 0 = clean. Exit 1 = violation found.
"""

from __future__ import annotations

import ast
import pathlib
import sys

KERNEL_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "kernel"

# Patterns that indicate an import from domains or legacy code.
# We check both the file paths referenced and the module names.
PROHIBITED_MODULES = [
    "kairo-sidecar.sidecar.masters",
    "kairo-sidecar.sidecar.parsers",
    "kairo-sidecar.sidecar.creators",
    "kairo-sidecar.sidecar.writers",
    "kairo-sidecar.sidecar.exporters",
    "kairo-sidecar.sidecar.safety",
    "kairo-sidecar.sidecar.speech",
    "kairo_sidecar.sidecar",
    "sidecar.masters",
    "sidecar.parsers",
    "sidecar.creators",
    "sidecar.writers",
    "sidecar.exporters",
    "sidecar.safety",
    "sidecar.speech",
    "sidecar.cua",
    "sidecar.kairo_eye",
    "domains",
    "legacy",
]

# Also check for relative imports that reach outside kernel
PROHIBITED_PATH_FRAGMENTS = [
    "domains",
    "legacy",
    "kairo-sidecar",
    "phantom-core",
    "phantom-overlay",
]


def _extract_imports(filepath: pathlib.Path) -> list[str]:
    """Extract all import module names from a Python file."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    except SyntaxError:
        return []

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def check_kernel_purity() -> list[str]:
    """Scan kernel/ for prohibited imports. Returns list of violations."""
    violations: list[str] = []

    if not KERNEL_DIR.exists():
        violations.append(f"KERNEL_DIR not found: {KERNEL_DIR}")
        return violations

    for py_file in KERNEL_DIR.rglob("*.py"):
        # Skip __pycache__
        if "__pycache__" in str(py_file):
            continue

        imports = _extract_imports(py_file)
        rel_path = py_file.relative_to(KERNEL_DIR)

        for imp in imports:
            for prohibited in PROHIBITED_MODULES:
                if imp.startswith(prohibited) or prohibited in imp:
                    violations.append(
                        f"  {rel_path}: imports '{imp}' (matches prohibited '{prohibited}')"
                    )

        # Also check for string references to prohibited paths in the source
        content = py_file.read_text(encoding="utf-8")
        for frag in PROHIBITED_PATH_FRAGMENTS:
            # Only flag if it looks like a path/import, not a doc comment
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                if f"from {frag}" in line or f"import {frag}" in line:
                    violations.append(
                        f"  {rel_path}:{i}: references prohibited path '{frag}'"
                    )

    return violations


def main() -> int:
    print("=" * 60)
    print("KERNEL PURITY GUARD (SPEC §S0)")
    print("Checking: kernel imports nothing from /domains or /legacy")
    print("=" * 60)

    violations = check_kernel_purity()

    if violations:
        print(f"\nFAILED — {len(violations)} violation(s) found:\n")
        for v in violations:
            print(v)
        print("\nThe kernel MUST NOT import from domains or legacy code.")
        return 1

    print("\nPASSED — kernel is pure (no domain/legacy imports)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
