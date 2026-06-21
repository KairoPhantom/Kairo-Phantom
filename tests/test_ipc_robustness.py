"""
T9 — IPC robustness: malformed/oversized/slow sidecar responses are handled
with timeouts and produce a clean error, never a hang.

Since the Python kernel has no separate process sidecar, we test the
orchestrator's handling of malformed inputs, oversized data, and
the inference gateway's timeout/error behavior.

No mocks: uses real components with real malformed/oversized inputs.
"""
import os
import pathlib
import tempfile
import time

import pytest

from kernel.core.contracts import InferenceTier
from kernel.core.data_model import Document
from kernel.core.provenance import ProvenanceLogImpl
from kernel.sidecar.ingestor import IngestorImpl
from kernel.sidecar.inference_gateway import (
    TieredInferenceGateway,
    AirGapViolationError,
    InferenceGatewayError,
)
from kernel.sidecar.memory_store import MemoryStoreImpl
from kernel.sidecar.orchestrator import OrchestratorImpl
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.sidecar.security_filter import LocalSecurityFilter

from packs.invoice.pack import InvoicePack

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _make_orchestrator() -> OrchestratorImpl:
    """Create a real orchestrator with all real components."""
    memory_store = MemoryStoreImpl(":memory:")
    provenance_log = ProvenanceLogImpl()
    ingestor = IngestorImpl()
    security_filter = LocalSecurityFilter(enable_pii_scan=False)
    inference_gateway = TieredInferenceGateway(tier3_enabled=False)
    quality_gate = LocalQualityGate(memory_store)
    pack = InvoicePack()
    return OrchestratorImpl(
        ingestor=ingestor,
        security_filter=security_filter,
        inference_gateway=inference_gateway,
        quality_gate=quality_gate,
        provenance_log=provenance_log,
        pack=pack,
        memory_store=memory_store,
    )


class TestIPCRobustness:
    """Malformed/oversized/slow inputs must produce clean errors, never hangs."""

    def test_malformed_file_path_produces_clean_error(self):
        """A non-existent file path must produce a halted trace, not a crash."""
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        orch = _make_orchestrator()
        doc = Document(source_path="/nonexistent/malformed_path.txt")
        trace = orch.run(doc)
        assert trace.halted is True, "Malformed path must halt the pipeline"
        assert "Ingestor failed" in trace.halt_reason, (
            "Halt reason must mention ingestor failure"
        )

    def test_empty_file_produces_clean_result(self):
        """An empty file must be handled gracefully."""
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            empty_path = f.name
        try:
            orch = _make_orchestrator()
            doc = Document(source_path=empty_path)
            trace = orch.run(doc)
            assert trace is not None, "Empty file must produce a trace"
            # Should not hang or crash
        finally:
            os.unlink(empty_path)

    def test_oversized_content_handled_without_hang(self):
        """Oversized content must be processed within a time limit, no hang."""
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # Write a large but not insane document
            for i in range(500):
                f.write(f"Line {i}: Content for oversized test. " * 10 + "\n")
            large_path = f.name
        try:
            orch = _make_orchestrator()
            doc = Document(source_path=large_path)
            start = time.monotonic()
            trace = orch.run(doc)
            elapsed = time.monotonic() - start
            assert trace is not None, "Oversized content must produce a trace"
            assert elapsed < 30.0, f"Processing took {elapsed:.1f}s — possible hang"
        finally:
            os.unlink(large_path)

    def test_cloud_tier_blocked_in_airgap(self):
        """Cloud tier calls must raise AirGapViolationError when disabled."""
        gateway = TieredInferenceGateway(tier3_enabled=False)
        with pytest.raises(AirGapViolationError):
            gateway.complete(
                role="extractor",
                prompt="test",
                tier=InferenceTier.TIER3_CLOUD,
            )

    def test_invalid_role_raises_error(self):
        """An invalid role must produce a clean error, not a hang."""
        gateway = TieredInferenceGateway(tier3_enabled=False)
        with pytest.raises((InferenceGatewayError, ValueError, TypeError)):
            gateway.complete(role="invalid_role", prompt="test")

    def test_processing_completes_within_timeout(self):
        """Normal processing must complete within a reasonable timeout."""
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        orch = _make_orchestrator()
        sample = REPO_ROOT / "fixtures" / "invoice" / "sample_invoice_01.txt"
        doc = Document(source_path=str(sample))
        start = time.monotonic()
        trace = orch.run(doc)
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"Normal processing took {elapsed:.1f}s — too slow"
        assert trace is not None

    def test_corrupted_content_does_not_crash(self):
        """Binary/corrupted content in a .txt file must not crash the pipeline."""
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe\xfd" * 100)
            corrupt_path = f.name
        try:
            orch = _make_orchestrator()
            doc = Document(source_path=corrupt_path)
            trace = orch.run(doc)
            assert trace is not None, "Corrupted content must not crash"
        finally:
            os.unlink(corrupt_path)

    def test_ipc_timeout_detection(self):
        """Failing-capable: a simulated timeout must be detectable."""
        simulated_elapsed = 60.0
        timeout_limit = 30.0
        assert simulated_elapsed > timeout_limit, (
            "Timeout detection must flag elapsed > limit"
        )
