"""
T9 — Sidecar lifecycle robustness: test the orchestrator lifecycle —
initialization, processing, cleanup, and re-initialization.
Since there's no separate process sidecar, we test the in-process orchestrator.

No mocks: uses the real OrchestratorImpl with real ingestor, memory store, etc.
"""
import pathlib

import pytest

from kernel.core.data_model import Document
from kernel.core.provenance import ProvenanceLogImpl
from kernel.core.grounding import GroundingVerifierImpl
from kernel.sidecar.ingestor import IngestorImpl
from kernel.sidecar.inference_gateway import TieredInferenceGateway
from kernel.sidecar.memory_store import MemoryStoreImpl
from kernel.sidecar.orchestrator import OrchestratorImpl
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.sidecar.security_filter import LocalSecurityFilter

from packs.invoice.pack import InvoicePack

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLE_INVOICE = REPO_ROOT / "fixtures" / "invoice" / "sample_invoice_01.txt"


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


class TestSidecarLifecycle:
    """Test orchestrator lifecycle: init, process, cleanup, re-init."""

    def test_clean_startup_and_initialization(self):
        """Orchestrator must initialize cleanly with all components."""
        orch = _make_orchestrator()
        assert orch is not None, "Orchestrator must initialize"
        assert orch._ingestor is not None, "Ingestor must be set"
        assert orch._security is not None, "Security filter must be set"
        assert orch._gateway is not None, "Gateway must be set"
        assert orch._quality is not None, "Quality gate must be set"
        assert orch._provenance is not None, "Provenance log must be set"
        assert orch._pack is not None, "Pack must be set"
        assert orch._memory is not None, "Memory store must be set"

    def test_processing_produces_trace(self):
        """Processing a document must produce a complete Trace."""
        import os
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        orch = _make_orchestrator()
        doc = Document(source_path=str(SAMPLE_INVOICE))
        trace = orch.run(doc)
        assert trace is not None, "Trace must not be None"
        assert len(trace.stages) > 0, "Trace must have stages"
        assert trace.is_complete, "Trace must be complete (non-empty IO)"

    def test_cleanup_and_reinitialization(self):
        """After cleanup, a new orchestrator must work from scratch."""
        import os
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        # First orchestrator
        orch1 = _make_orchestrator()
        doc = Document(source_path=str(SAMPLE_INVOICE))
        trace1 = orch1.run(doc)
        assert len(trace1.stages) > 0

        # Simulate cleanup by dropping references
        del orch1

        # Re-initialize a fresh orchestrator
        orch2 = _make_orchestrator()
        trace2 = orch2.run(doc)
        assert len(trace2.stages) > 0, "Re-initialized orchestrator must process documents"
        assert trace2.is_complete, "Re-initialized orchestrator trace must be complete"

    def test_multiple_documents_sequential(self):
        """Processing multiple documents sequentially must not fail."""
        import os
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        orch = _make_orchestrator()
        invoice_dir = REPO_ROOT / "fixtures" / "invoice"
        for gt_file in invoice_dir.glob("sample_invoice_*.txt"):
            doc = Document(source_path=str(gt_file))
            trace = orch.run(doc)
            assert trace is not None, f"Trace for {gt_file.name} must not be None"
            assert len(trace.stages) > 0, f"Trace for {gt_file.name} must have stages"

    def test_restart_on_simulated_crash(self):
        """If processing fails, a new orchestrator must recover."""
        import os
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        orch = _make_orchestrator()
        # Simulate a crash by passing a non-existent file
        bad_doc = Document(source_path="/nonexistent/crash_test.txt")
        trace = orch.run(bad_doc)
        assert trace.halted is True, "Crash must produce a halted trace"
        assert "Ingestor failed" in trace.halt_reason, "Halt reason must mention ingestor failure"

        # New orchestrator must work after the crash
        orch2 = _make_orchestrator()
        doc = Document(source_path=str(SAMPLE_INVOICE))
        trace2 = orch2.run(doc)
        assert len(trace2.stages) > 0, "New orchestrator must recover after crash"

    def test_no_orphaned_state_after_processing(self):
        """Memory store must be scoped — no cross-contamination between runs."""
        import os
        os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
        orch = _make_orchestrator()
        doc = Document(source_path=str(SAMPLE_INVOICE))
        orch.run(doc)
        # The memory store should have data from this run
        stats = orch._memory.stats
        assert stats["documents"] >= 1, "Memory store should have at least 1 document"
        # New orchestrator has its own memory store (no orphans)
        orch2 = _make_orchestrator()
        stats2 = orch2._memory.stats
        assert stats2["documents"] == 0, "New orchestrator must start with empty memory"
