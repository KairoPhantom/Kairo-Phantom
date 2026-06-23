"""
Kairo Phantom — Overlay Server (SPEC §S8)

FastAPI service serving the premium glass-chrome UX for de-identification triage.
Allows viewing source documents, highlights bbox, and accept/edit/reject.
"""

from __future__ import annotations

import os
import pathlib
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from kernel.core.contracts import GateVerdict, InferenceTier
from kernel.core.data_model import (
    Action,
    ActionKind,
    ActionStatus,
    Correction,
    Document,
    ExtractionStatus,
)
from kernel.core.provenance import ProvenanceLogImpl
from kernel.sidecar.action_executor import ActionExecutorImpl
from kernel.sidecar.ingestor import IngestorImpl
from kernel.sidecar.inference_gateway import TieredInferenceGateway
from kernel.sidecar.memory_store import MemoryStoreImpl
from kernel.sidecar.orchestrator import OrchestratorImpl
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.sidecar.security_filter import LocalSecurityFilter
from packs.generic.pack import GenericPack

# Initialize FastAPI
app = FastAPI(title="Kairo Phantom Web Overlay")

# Paths
BASE_DIR = pathlib.Path(__file__).parents[1]
FIXTURES_DIR = BASE_DIR / "fixtures" / "wedge"
TEMPLATES_DIR = BASE_DIR / "overlay" / "templates"

# Initialize Core Services
provenance_log = ProvenanceLogImpl()
memory_store = MemoryStoreImpl(BASE_DIR / ".kairo" / "overlay_store.db")
ingestor = IngestorImpl()
security_filter = LocalSecurityFilter(enable_pii_scan=False)

# Gateway in test mode (no LiteLLM/Ollama needed for overlay demonstration)
os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
inference_gateway = TieredInferenceGateway(tier3_enabled=False)

quality_gate = LocalQualityGate(memory_store)
wedge_pack = GenericPack()

orchestrator = OrchestratorImpl(
    ingestor=ingestor,
    security_filter=security_filter,
    inference_gateway=inference_gateway,
    quality_gate=quality_gate,
    provenance_log=provenance_log,
    pack=wedge_pack,
    memory_store=memory_store,
)

action_executor = ActionExecutorImpl(provenance_log)


class DemoRequest(BaseModel):
    file: str


class ApplyRequest(BaseModel):
    ext_id: str
    accept: bool


class CorrectionRequest(BaseModel):
    ext_id: str
    field_name: str
    original: str
    corrected: str
    reason: str


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the primary HTML overlay template."""
    template_path = TEMPLATES_DIR / "index.html"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))


@app.post("/demo")
async def run_demo(req: DemoRequest):
    """Run the pipeline on a document and return data for the overlay."""
    p = pathlib.Path(req.file)
    if p.exists():
        file_path = p
    else:
        file_path = FIXTURES_DIR / req.file
        if not file_path.exists():
            file_path = BASE_DIR / req.file
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"File {req.file} not found")

    try:
        # 1. Create target document
        doc = Document(
            source_path=str(file_path),
            sha256="mock-sha256",
        )

        # 2. Run Orchestrator
        trace = orchestrator.run(doc)

        # 3. Read raw file contents to return to UI
        if file_path.suffix.lower() in (".txt", ".md"):
            document_text = file_path.read_text(encoding="utf-8", errors="replace")
        else:
            # Reconstruct document text from the registered chunks
            doc_chunks = [c for c in provenance_log._chunks.values() if c.doc_id == doc.doc_id]
            if not doc_chunks:
                doc_chunks = list(provenance_log._chunks.values())
            document_chunks = sorted(
                doc_chunks,
                key=lambda c: (c.page, c.bbox.y0 if c.bbox else 0)
            )
            document_text = "\n\n".join(chunk.text for chunk in document_chunks)

        # 4. Format suggestions with bbox + page mapping
        suggestions = []
        for ext in trace.extractions:
            if ext.status == ExtractionStatus.BLOCKED:
                continue
            
            chain = provenance_log.get_provenance(ext.ext_id)
            if not chain.is_complete:
                continue

            suggestions.append({
                "ext_id": ext.ext_id,
                "field_name": ext.field_name,
                "value": ext.value,
                "confidence": ext.confidence,
                "page": chain.chunk.page if chain.chunk else 1,
                "chunk_id": chain.chunk.chunk_id if chain.chunk else "",
                "bbox": {
                    "x0": chain.chunk.bbox.x0 if chain.chunk and chain.chunk.bbox else 0,
                    "y0": chain.chunk.bbox.y0 if chain.chunk and chain.chunk.bbox else 0,
                    "x1": chain.chunk.bbox.x1 if chain.chunk and chain.chunk.bbox else 1,
                    "y1": chain.chunk.bbox.y1 if chain.chunk and chain.chunk.bbox else 1,
                }
            })

            # Register proposed action for each suggestion
            action = Action(
                ext_id=ext.ext_id,
                kind=ActionKind.SUGGEST,
                target_app="notepad",
                payload={"value": ext.value},
                confidence=ext.confidence,
                status=ActionStatus.PENDING,
            )
            provenance_log.register_action(action)

        # 5. Format trace details
        formatted_trace = {
            "halted": trace.halted,
            "halt_reason": trace.halt_reason,
            "stages": [
                {
                    "name": s.name,
                    "input_data": s.input_data,
                    "output_data": s.output_data,
                    "duration_ms": s.duration_ms,
                    "status": s.status,
                }
                for s in trace.stages
            ]
        }

        return {
            "success": True,
            "document_text": document_text,
            "suggestions": suggestions,
            "trace": formatted_trace,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/apply")
async def apply_cua(req: ApplyRequest):
    """Execute a confirmed CUA action and verify post-state."""
    # Retrieve action from provenance log
    action_id = None
    for act_id, act in provenance_log._actions.items():
        if act.ext_id == req.ext_id:
            action_id = act_id
            break

    if not action_id:
        return {"success": False, "error": "No pending action found for this extraction"}

    action = provenance_log._actions[action_id]
    
    # Kairo ActionExecutor requires human_confirm=True
    result = action_executor.apply(action, human_confirm=req.accept)
    return {
        "success": result.success,
        "error": result.error,
        "post_state": result.post_state,
    }


@app.post("/correct")
async def record_flywheel_correction(req: CorrectionRequest):
    """Record a correction to memory store, triggering the local flywheel."""
    try:
        corr = Correction(
            ext_id=req.ext_id,
            original=req.original,
            corrected=req.corrected,
            reason=req.reason,
            by="overlay-user",
        )
        memory_store.record_correction(corr)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Mount static directory for serving page images
if pathlib.Path(".kairo").exists():
    app.mount("/static", StaticFiles(directory=".kairo"), name="static")


@app.get("/api/compression/stats")
async def get_compression_stats():
    """Return aggregate context compression statistics."""
    try:
        from kairo.context.compressor import get_compression_stats
        return get_compression_stats()
    except ImportError:
        return {"error": "Context compressor not available", "total_runs": 0}


@app.get("/source/{extraction_id}")
async def get_source_provenance(extraction_id: str):
    """Retrieve bounding box and page reference for click-to-source verification."""
    ext = memory_store.get_extraction(extraction_id)
    if not ext:
        ext = provenance_log.get_provenance(extraction_id).extraction
        if not ext:
            raise HTTPException(status_code=404, detail="Extraction not found")

    chain = provenance_log.get_provenance(ext.ext_id)
    if not chain.is_complete or not chain.chunk:
        if ext.anchors:
            anchor = ext.anchors[0]
            bbox = {
                "x0": anchor.bbox.x0 if anchor.bbox else 0,
                "y0": anchor.bbox.y0 if anchor.bbox else 0,
                "x1": anchor.bbox.x1 if anchor.bbox else 1,
                "y1": anchor.bbox.y1 if anchor.bbox else 1,
            }
            page = anchor.page
            doc_id = ext.pack_id
        else:
            raise HTTPException(status_code=404, detail="Provenance chain is incomplete")
    else:
        page = chain.chunk.page
        bbox = {
            "x0": chain.chunk.bbox.x0 if chain.chunk.bbox else 0,
            "y0": chain.chunk.bbox.y0 if chain.chunk.bbox else 0,
            "x1": chain.chunk.bbox.x1 if chain.chunk.bbox else 1,
            "y1": chain.chunk.bbox.y1 if chain.chunk.bbox else 1,
        }
        doc_id = chain.document.doc_id if chain.document else ""

    pages = memory_store.get_pages(doc_id)
    image_ref = ""
    for p in pages:
        if p.index == page:
            image_ref = f"/static/page_images/{p.image_sha256}.png" if p.image_sha256 else ""
            break

    return {
        "page": page,
        "bbox": bbox,
        "image_ref": image_ref,
    }

