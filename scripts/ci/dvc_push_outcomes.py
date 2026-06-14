"""
dvc_push_outcomes.py — DVC tracking helper for the DuckDB outcome store.

Runs `dvc add target/gauntlet_outcomes.duckdb` to version-control the DB,
then prints a summary.  Gracefully degrades if DVC is not installed.

Usage:
    python scripts/ci/dvc_push_outcomes.py [--db-path PATH]
"""
import argparse
import os
import shutil
import subprocess
import sys


def _find_db(db_path: str | None) -> str:
    if db_path and os.path.exists(db_path):
        return db_path
    default = os.path.join(
        os.path.dirname(__file__), "..", "..", "kairo-sidecar", "target",
        "gauntlet_outcomes.duckdb",
    )
    return os.path.normpath(default)


def run(db_path: str | None = None) -> bool:
    """
    Track the DuckDB outcome store with DVC.
    Returns True on success, False on graceful-degrade.
    """
    db = _find_db(db_path)

    if not os.path.exists(db):
        print(f"[dvc_push_outcomes] DB not found at {db} — nothing to track.")
        return True

    dvc_bin = shutil.which("dvc")
    if not dvc_bin:
        print(
            "[dvc_push_outcomes] WARNING: dvc not found on PATH. "
            "Install with: pip install dvc\n"
            f"  Would have tracked: {db}"
        )
        return False   # graceful degrade

    print(f"[dvc_push_outcomes] Tracking {db} with DVC...")
    try:
        result = subprocess.run(
            [dvc_bin, "add", db],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        dvc_file = db + ".dvc"
        size_mb = os.path.getsize(db) / (1024 * 1024)
        print(
            f"[dvc_push_outcomes] ✅ Tracked: {dvc_file}\n"
            f"  DB size: {size_mb:.2f} MB"
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[dvc_push_outcomes] dvc add failed:\n{exc.stderr}", file=sys.stderr)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DVC-track the DuckDB outcome store.")
    parser.add_argument("--db-path", default=None, help="Override DB path.")
    args = parser.parse_args()
    ok = run(args.db_path)
    sys.exit(0 if ok else 1)
