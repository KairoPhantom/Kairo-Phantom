#!/usr/bin/env python3
"""
Kairo Phantom — First-Run Flow (P0.1)

Detects whether the Python kernel is set up, builds the index for a sample
document, answers one bundled question with a grounded highlight, and prints
where the answer came from.

Usage:
    python3 scripts/first_run.py
    python3 scripts/first_run.py --doc samples/contract/sample_contract_01.txt --question "What is the effective date?"
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def _check_kernel_setup() -> bool:
    """Detect whether the Python kernel is importable and functional."""
    try:
        import kernel  # noqa: F401
        import kernel.core.data_model  # noqa: F401
        import kernel.core.grounding  # noqa: F401
        import kernel.sidecar.ingestor  # noqa: F401
        return True
    except ImportError as e:
        print(f"  [FAIL] Kernel import failed: {e}")
        print()
        print("  The Python kernel is not set up. Install dependencies:")
        print("    pip install numpy")
        print("  Then from the repo root:")
        print("    python3 -c 'import kernel; print(\"kernel OK\")'")
        return False


def _build_index(doc_path: str) -> tuple:
    """Build the index (ingest + chunk) for a sample document."""
    from kernel.sidecar.ingestor import IngestorImpl
    ingestor = IngestorImpl()
    chunks, doc, pages = ingestor.ingest(doc_path)
    return chunks, doc, pages


def _answer(doc_path: str, question: str):
    """Answer a question with grounded citation or refusal."""
    from scripts.qa_pipeline import answer_question
    return answer_question(doc_path, question)


def main():
    parser = argparse.ArgumentParser(
        description="Kairo Phantom — First-Run Flow"
    )
    parser.add_argument(
        "--doc", default="samples/invoice/sample_invoice_01.txt",
        help="Path to the sample document (default: bundled invoice sample)",
    )
    parser.add_argument(
        "--question", default="What is the invoice number?",
        help="Question to answer (default: bundled invoice question)",
    )
    args = parser.parse_args()

    doc_path = args.doc
    if not pathlib.Path(doc_path).is_absolute():
        doc_path = str(_REPO_ROOT / doc_path)

    _print_header("Kairo Phantom — First-Run Flow")

    # Step 1: Check kernel setup
    print("\n  Step 1: Checking Python kernel setup...")
    if not _check_kernel_setup():
        sys.exit(1)
    print("  [OK] Python kernel is importable and functional.")

    # Step 2: Build index for sample document
    print(f"\n  Step 2: Building index for {pathlib.Path(doc_path).name}...")
    t0 = time.monotonic()
    try:
        chunks, doc, pages = _build_index(doc_path)
    except FileNotFoundError as e:
        print(f"  [FAIL] {e}")
        print(f"  Sample document not found at: {doc_path}")
        sys.exit(1)
    except Exception as e:
        print(f"  [FAIL] Index build failed: {e}")
        sys.exit(1)
    elapsed = time.monotonic() - t0
    print(f"  [OK] Indexed {len(chunks)} chunks across {len(pages)} page(s) in {elapsed:.2f}s.")

    # Step 3: Answer the bundled question
    print(f"\n  Step 3: Answering question: \"{args.question}\"")
    t0 = time.monotonic()
    answer = _answer(doc_path, args.question)
    elapsed = time.monotonic() - t0

    print(f"  [OK] Answer produced in {elapsed:.2f}s.")
    print()
    print(f"  Question: {answer.query}")
    print()

    if answer.grounded:
        print("  ✓ GROUNDED ANSWER:")
        print(f"    {answer.text}")
        print()
        if answer.citations:
            print("  Source region (verified by independent grounding checker):")
            for i, anchor in enumerate(answer.citations, 1):
                bbox = anchor.bbox
                if bbox:
                    print(
                        f"    [{i}] Page {anchor.page}, "
                        f"bounding box: ({bbox.x0:.3f}, {bbox.y0:.3f}) → "
                        f"({bbox.x1:.3f}, {bbox.y1:.3f})"
                    )
                    print(f"        Character span: {anchor.char_span[0]}–{anchor.char_span[1]}")
        print()
        print("  The answer was independently verified against the document's")
        print("  stored geometry. The model cannot self-certify this bounding box.")
    else:
        print("  ✗ REFUSED (no source → no answer):")
        print(f"    {answer.text}")
        print()
        print("  Kairo declined to answer because it could not ground the")
        print("  answer in the source document. This is the core promise:")
        print("  'No source → no answer.'")

    _print_header("First-Run Complete")
    print()
    print("  Try more questions:")
    print(f"    make run DOC={args.doc} Q=\"What is the total amount due?\"")
    print()
    print("  Try all bundled samples:")
    print("    make samples")
    print()

    sys.exit(0 if answer.grounded else 1)


if __name__ == "__main__":
    main()
