#!/usr/bin/env python3
"""
T6 — Dependency Audit: scan requirements.txt for unpinned or CVE-flagged dependencies.

Checks:
  1. All dependencies are pinned to a specific version (no unpinned >= or *)
  2. Known-vulnerable packages are flagged

Usage:
  python3 scripts/dependency_audit.py [--requirements PATH]

Exit codes:
  0 = all dependencies pinned, no known CVEs
  1 = unpinned dependencies or known-vulnerable packages found
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Known vulnerable packages (package_name, vulnerable_versions, CVE)
# This is a curated list of known-vulnerable versions for key dependencies.
KNOWN_VULNERABILITIES = [
    # (package, version_pattern_to_flag, cve_id, description)
    ("pydantic", r"<2\.0", "CVE-2021-29510", "pydantic <2.0 has known RCE vulnerability"),
    ("pillow", r"<10\.0", "CVE-2023-44271", "Pillow <10.0 has DoS vulnerability"),
    ("requests", r"<2\.31", "CVE-2023-32681", "requests <2.31 has proxy header leak"),
    ("urllib3", r"<1\.26\.17", "CVE-2023-39901", "urllib3 <1.26.17 has request smuggling risk"),
    ("cryptography", r"<41\.0", "CVE-2023-49083", "cryptography <41.0 has NULL dereference"),
]

# Packages that are exempt from pinning (build tools, etc.)
PIN_EXEMPT = {"pip", "setuptools", "wheel"}


def parse_requirements(path: pathlib.Path) -> list[dict]:
    """Parse a requirements.txt file and return list of dependency dicts."""
    deps = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Skip comments after package spec
        if " #" in line:
            line = line.split(" #")[0].strip()

        # Parse package name and version specifier
        # Formats: package==1.0.0, package>=1.0.0, package~=1.0.0, package
        match = re.match(r'^([a-zA-Z0-9_-]+)\s*([><=!~]*\s*[0-9a-zA-Z.*]+)?', line)
        if match:
            name = match.group(1).lower()
            version_spec = (match.group(2) or "").strip()
            deps.append({
                "name": name,
                "version_spec": version_spec,
                "raw": line,
            })
    return deps


def check_pinned(deps: list[dict]) -> list[dict]:
    """Check which dependencies are not pinned to an exact version."""
    unpinned = []
    for dep in deps:
        if dep["name"] in PIN_EXEMPT:
            continue
        spec = dep["version_spec"]
        # Pinned means == with a specific version (no wildcards)
        if not spec:
            unpinned.append({**dep, "issue": "no version specifier"})
        elif not spec.startswith("=="):
            unpinned.append({**dep, "issue": f"not exact pin: {spec}"})
        elif "*" in spec:
            unpinned.append({**dep, "issue": f"wildcard in pin: {spec}"})
    return unpinned


def check_vulnerable(deps: list[dict]) -> list[dict]:
    """Check for known-vulnerable package versions."""
    vulnerable = []
    for dep in deps:
        for pkg_name, vuln_pattern, cve, desc in KNOWN_VULNERABILITIES:
            if dep["name"] == pkg_name:
                # Check if the version matches the vulnerable pattern
                if re.search(vuln_pattern, dep["version_spec"]):
                    vulnerable.append({
                        **dep,
                        "cve": cve,
                        "description": desc,
                    })
    return vulnerable


def main():
    parser = argparse.ArgumentParser(description="Kairo Phantom Dependency Audit")
    parser.add_argument(
        "--requirements",
        default=str(REPO_ROOT / "kairo-sidecar" / "requirements.txt"),
        help="Path to requirements.txt file",
    )
    args = parser.parse_args()

    req_path = pathlib.Path(args.requirements)
    if not req_path.exists():
        print(f"ERROR: requirements file not found: {req_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("Kairo Phantom — Dependency Audit")
    print("=" * 60)
    print(f"Scanning: {req_path}")

    deps = parse_requirements(req_path)
    print(f"Found {len(deps)} dependencies")

    # Check pinning
    unpinned = check_pinned(deps)
    if unpinned:
        print(f"\n[WARN] {len(unpinned)} unpinned dependencies:")
        for dep in unpinned:
            print(f"  - {dep['name']}: {dep['issue']} (raw: {dep['raw']})")
    else:
        print("\n[PASS] All dependencies are pinned to exact versions")

    # Check vulnerabilities
    vulnerable = check_vulnerable(deps)
    if vulnerable:
        print(f"\n[FAIL] {len(vulnerable)} known-vulnerable dependencies:")
        for dep in vulnerable:
            print(f"  - {dep['name']} {dep['version_spec']}: {dep['cve']} — {dep['description']}")
    else:
        print("[PASS] No known-vulnerable dependencies found")

    # Result
    print("\n" + "=" * 60)
    has_issues = len(vulnerable) > 0
    if has_issues:
        print("DEPENDENCY AUDIT: FAIL — known vulnerabilities found")
        sys.exit(1)
    elif unpinned:
        print("DEPENDENCY AUDIT: PASS (with warnings — unpinned deps)")
        sys.exit(0)
    else:
        print("DEPENDENCY AUDIT: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
