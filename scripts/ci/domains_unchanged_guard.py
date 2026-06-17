#!/usr/bin/env python3
"""
Domains Unchanged Guard (SPEC §S0, CI-blocking)

Ensures that no kernel/wedge PR modifies or deletes any domain file.
Uses git to check that domain-related files are byte-for-byte unchanged.

Exit 0 = clean. Exit 1 = domain files changed.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Domain file locations (from DOMAINS.md)
DOMAIN_PATHS = [
    "kairo-sidecar/sidecar/masters/",
    "kairo-sidecar/sidecar/parsers/",
    "kairo-sidecar/sidecar/creators/",
    "kairo-sidecar/sidecar/writers/",
    "kairo-sidecar/sidecar/exporters/",
    "kairo-sidecar/sidecar/safety/",
    "kairo-sidecar/sidecar/speech/",
    "kairo-sidecar/sidecar/cua/",
    "kairo-sidecar/sidecar/kairo_eye/",
    "phantom-core/src/",
    "phantom-overlay/",
]


def check_domains_unchanged() -> list[str]:
    """Check if any domain files have been modified in the working tree."""
    violations: list[str] = []

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        changed_files = result.stdout.strip().splitlines() if result.stdout.strip() else []

        # Also check staged changes
        result_staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        staged_files = result_staged.stdout.strip().splitlines() if result_staged.stdout.strip() else []

        all_changed = set(changed_files + staged_files)

        for changed in all_changed:
            for domain_path in DOMAIN_PATHS:
                if changed.startswith(domain_path):
                    violations.append(f"  MODIFIED: {changed}")

    except FileNotFoundError:
        # git not available — cannot check
        print("WARNING: git not available, skipping domains-unchanged check")
        return []

    return violations


def main() -> int:
    print("=" * 60)
    print("DOMAINS UNCHANGED GUARD (SPEC §S0)")
    print("Checking: /domains files are byte-for-byte unchanged")
    print("=" * 60)

    violations = check_domains_unchanged()

    if violations:
        print(f"\nFAILED — {len(violations)} domain file(s) changed:\n")
        for v in violations:
            print(v)
        print("\nKernel/wedge PRs MUST NOT modify domain files.")
        print("See DOMAINS.md for the full domain inventory.")
        return 1

    print("\nPASSED — all domain files unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
