"""
push_argilla_queue.py — Push pending human-review records to Argilla.

Reads target/argilla_queue.jsonl and pushes rows where label==null to a
local Argilla dataset named `kairo_fix_loop_review`.

If the argilla package is not installed, prints the pending records and
exits 0 (graceful degrade).

Usage:
    python scripts/ci/push_argilla_queue.py [--queue-path PATH]
"""
import argparse
import json
import os
import sys


DEFAULT_QUEUE = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "kairo-sidecar",
        "target", "argilla_queue.jsonl",
    )
)
ARGILLA_DATASET = "kairo_fix_loop_review"


def _load_pending(queue_path: str) -> list:
    """Return all records from the JSONL queue where label is None."""
    if not os.path.exists(queue_path):
        return []
    records = []
    with open(queue_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("label") is None:
                    records.append(rec)
            except json.JSONDecodeError:
                pass
    return records


def _push_to_argilla(records: list) -> bool:
    """Push records to Argilla. Returns True on success."""
    try:
        import argilla as rg  # type: ignore[import]
    except ImportError:
        return False

    try:
        rg.init(api_url="http://localhost:6900", api_key="admin.apikey")
        dataset = rg.FeedbackDataset(
            fields=[
                rg.TextField(name="scenario_id"),
                rg.TextField(name="terminal_state"),
                rg.TextField(name="failure_reason"),
                rg.TextField(name="attempt_log"),
            ],
            questions=[
                rg.LabelQuestion(
                    name="label",
                    title="Should this scenario be ACCEPTED for human re-labelling?",
                    labels=["yes", "no"],
                )
            ],
        )
        argilla_records = []
        for rec in records:
            argilla_records.append(
                rg.FeedbackRecord(
                    fields={
                        "scenario_id":    rec.get("scenario_id", ""),
                        "terminal_state": rec.get("terminal_state", ""),
                        "failure_reason": rec.get("failure_reason", ""),
                        "attempt_log":    json.dumps(rec.get("attempt_log", [])),
                    }
                )
            )
        dataset.add_records(argilla_records)
        dataset.push_to_argilla(name=ARGILLA_DATASET, workspace="admin")
        return True
    except Exception as exc:
        print(f"[push_argilla_queue] Argilla push failed: {exc}", file=sys.stderr)
        return False


def run(queue_path: str | None = None) -> int:
    """
    Main entry point.  Returns exit code (0 = success / graceful-degrade).
    """
    path = queue_path or DEFAULT_QUEUE
    pending = _load_pending(path)

    if not pending:
        print(f"[push_argilla_queue] No pending records in {path}.")
        return 0

    print(f"[push_argilla_queue] Found {len(pending)} pending record(s).")

    try:
        import argilla  # noqa: F401
        argilla_available = True
    except ImportError:
        argilla_available = False

    if not argilla_available:
        print(
            "[push_argilla_queue] WARNING: argilla package not installed. "
            "Printing pending records instead.\n"
            "  Install with: pip install argilla\n"
        )
        for rec in pending:
            print(
                f"  [{rec.get('terminal_state')}] scenario={rec.get('scenario_id')} "
                f"reason={rec.get('failure_reason')}"
            )
        return 0   # graceful degrade

    ok = _push_to_argilla(pending)
    if ok:
        print(f"[push_argilla_queue] ✅ Pushed {len(pending)} record(s) to Argilla "
              f"dataset '{ARGILLA_DATASET}'.")
        return 0
    else:
        print("[push_argilla_queue] Push failed — see errors above.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Push pending Argilla human-review queue records."
    )
    parser.add_argument("--queue-path", default=None, help="Override queue JSONL path.")
    args = parser.parse_args()
    sys.exit(run(args.queue_path))
