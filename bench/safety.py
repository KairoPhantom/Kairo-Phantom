"""
Kairo Phantom — Safety Verification Suite (SPEC §S9, §S5)

Runs safety audits to verify the system guards are active and unbypassable:
1. Air-gap egress test (cloud tier raises error when OFF).
2. Injection corpus scan (verifies that all prompt injection payloads block).
3. Ingestor fuzz / robustness tests (ensures graceful handling, no crashes).
4. Gate-bypass defense (ensures ungrounded extractions are blocked).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from kernel.core.contracts import InferenceTier, GateVerdict
from kernel.core.data_model import Extraction
from kernel.sidecar.inference_gateway import (
    TieredInferenceGateway,
    AirGapViolationError,
)
from kernel.sidecar.security_filter import LocalSecurityFilter
from kernel.sidecar.ingestor import IngestorImpl
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.sidecar.memory_store import MemoryStoreImpl


def parse_args():
    parser = argparse.ArgumentParser(description="Kairo Phantom Safety Audits")
    parser.add_argument(
        "--fixtures-dir",
        default="fixtures/wedge",
        help="Directory containing fixtures",
    )
    return parser.parse_args()


def run_air_gap_audit():
    """Verify that cloud tier egress is blocked when tier3_enabled is False."""
    print("  [Audit] Running Air-gap egress audit...")
    gateway = TieredInferenceGateway(tier3_enabled=False)
    
    try:
        gateway.complete(
            role="extractor",
            prompt="Process this classification.",
            tier=InferenceTier.TIER3_CLOUD,
        )
        print("    [FAIL] Air-gap egress audit FAILED: Cloud egress was NOT blocked!")
        return False
    except AirGapViolationError:
        print("    [PASS] Air-gap egress audit PASSED: Cloud egress was successfully blocked.")
        return True
    except Exception as e:
        print(f"    [FAIL] Air-gap egress audit FAILED: Unexpected exception: {e}")
        return False


def run_injection_audit():
    """Verify that all prompt injection payloads in injection_corpus.json block."""
    print("  [Audit] Running prompt injection audit...")
    security = LocalSecurityFilter(enable_pii_scan=False)
    corpus_path = pathlib.Path(__file__).parents[1] / "fixtures" / "injection_corpus.json"

    if not corpus_path.exists():
        print(f"    [FAIL] Prompt injection audit FAILED: corpus file not found at {corpus_path}")
        return False

    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    blocked_count = 0
    total_count = len(corpus)

    for item in corpus:
        res = security.scan(item["payload"])
        if res.blocked:
            blocked_count += 1
        else:
            print(f"    [FAIL] Injection payload {item['id']} was NOT blocked: {item['payload']}")

    print(f"    [PASS] Prompt injection audit: Blocked {blocked_count}/{total_count} payloads.")
    return blocked_count == total_count


def run_ingestor_robustness_audit():
    """Verify ingestor handles invalid/fuzzed inputs gracefully."""
    print("  [Audit] Running Ingestor robustness audit...")
    ingestor = IngestorImpl()

    # 1. Missing file
    try:
        ingestor.ingest("non_existent_file_xyz.txt")
        print("    [FAIL] Ingestor audit FAILED: did not raise FileNotFoundError for missing file")
        return False
    except FileNotFoundError:
        pass

    # 2. Unsupported extension
    try:
        # Create a temp invalid file extension
        temp_file = pathlib.Path("temp_test_file.invalid")
        temp_file.touch()
        try:
            ingestor.ingest(str(temp_file))
            print("    [FAIL] Ingestor audit FAILED: did not raise ValueError for unsupported extension")
            return False
        finally:
            if temp_file.exists():
                temp_file.unlink()
    except ValueError:
        pass

    print("    [PASS] Ingestor robustness audit PASSED: invalid inputs handled gracefully.")
    return True


def run_gate_bypass_audit():
    """Verify that ungrounded extractions are blocked by the QualityGate."""
    print("  [Audit] Running Gate-bypass defense audit...")
    memory_store = MemoryStoreImpl(":memory:")
    gate = LocalQualityGate(memory_store)

    # Extraction with no chunk_id (ungrounded)
    ext = Extraction(
        field_name="author",
        value="Dr. Margaret Chen",
        confidence=0.9,
        chunk_id="",  # Ungrounded!
    )

    res = gate.check(ext)
    if res.verdict == GateVerdict.BLOCK:
        print("    [PASS] Gate-bypass audit PASSED: Ungrounded extraction was successfully BLOCKED.")
        return True
    else:
        print(f"    [FAIL] Gate-bypass audit FAILED: Ungrounded extraction passed with verdict: {res.verdict}")
        return False


def main():
    args = parse_args()
    print("=====================================================================")
    print("Kairo Phantom Safety Audits Suite")
    print("=====================================================================")
    
    results = [
        run_air_gap_audit(),
        run_injection_audit(),
        run_ingestor_robustness_audit(),
        run_gate_bypass_audit(),
    ]

    print("=====================================================================")
    if all(results):
        print("[PASS] SAFETY AUDITS: ALL PASSED")
        sys.exit(0)
    else:
        print("[FAIL] SAFETY AUDITS: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
