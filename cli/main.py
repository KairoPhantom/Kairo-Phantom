"""
Kairo Phantom — Headless CLI (SPEC §S1, §S8)
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

from kernel.core.data_model import Document, Extraction, Correction, Anchor, GroundingMethod
from kernel.sidecar.ingestor import IngestorImpl
from kernel.sidecar.security_filter import LocalSecurityFilter
from kernel.sidecar.inference_gateway import TieredInferenceGateway
from kernel.sidecar.quality_gate import LocalQualityGate
from kernel.core.provenance import ProvenanceLogImpl
from kernel.sidecar.memory_store import MemoryStoreImpl
from kernel.sidecar.orchestrator import OrchestratorImpl

# Import packs
from packs.generic.pack import GenericPack
from packs.invoice.pack import InvoicePack
from packs.paper.pack import PaperPack
from packs.contract.pack import ContractPack


def get_db_path() -> pathlib.Path:
    db_dir = pathlib.Path(".kairo")
    db_dir.mkdir(exist_ok=True)
    return db_dir / "kairo.db"


def cmd_index(args):
    file_path = pathlib.Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found {file_path}", file=sys.stderr)
        sys.exit(1)

    ingestor = IngestorImpl()
    try:
        chunks, doc, pages = ingestor.ingest(str(file_path))
    except Exception as e:
        print(f"Error indexing file: {e}", file=sys.stderr)
        sys.exit(1)

    db_path = get_db_path()
    store = MemoryStoreImpl(db_path)
    store.upsert_document(doc)
    for page in pages:
        store.upsert_page(page)
    for chunk in chunks:
        store.upsert_chunk(chunk)

    print(f"Indexed {len(chunks)} chunks across {doc.page_count} pages.")


def cmd_run(args):
    file_path = pathlib.Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found {file_path}", file=sys.stderr)
        sys.exit(1)

    # Instantiate pack
    pack_name = args.pack.lower()
    if pack_name == "generic":
        pack = GenericPack()
    elif pack_name == "invoice":
        pack = InvoicePack()
    elif pack_name == "paper":
        pack = PaperPack()
    elif pack_name == "contract":
        pack = ContractPack()
    else:
        print(f"Error: unknown pack {args.pack}", file=sys.stderr)
        sys.exit(1)

    # Setup orchestrator
    os.environ["KAIRO_GATEWAY_TEST_MODE"] = "true"
    db_path = get_db_path()
    store = MemoryStoreImpl(db_path)
    ingestor = IngestorImpl()
    security_filter = LocalSecurityFilter(enable_pii_scan=False)
    inference_gateway = TieredInferenceGateway(tier3_enabled=False)
    quality_gate = LocalQualityGate(store)
    provenance_log = ProvenanceLogImpl()

    orchestrator = OrchestratorImpl(
        ingestor=ingestor,
        security_filter=security_filter,
        inference_gateway=inference_gateway,
        quality_gate=quality_gate,
        provenance_log=provenance_log,
        pack=pack,
        memory_store=store,
    )

    doc = Document(source_path=str(file_path))
    trace = orchestrator.run(doc)

    # Format output
    output_list = []
    for ext in trace.extractions:
        # Get first anchor if available
        page = None
        bbox = None
        if ext.anchors:
            anchor = ext.anchors[0]
            page = anchor.page
            if anchor.bbox:
                bbox = [anchor.bbox.x0, anchor.bbox.y0, anchor.bbox.x1, anchor.bbox.y1]

        output_list.append({
            "id": ext.ext_id,
            "field": ext.field_name,
            "value": ext.value,
            "confidence": ext.confidence,
            "page": page,
            "bbox": bbox,
            "method": ext.method.value if hasattr(ext.method, "value") else str(ext.method),
            "status": ext.status.value,
        })

    print(json.dumps(output_list, indent=2))


def cmd_ask(args):
    file_path = pathlib.Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found {file_path}", file=sys.stderr)
        sys.exit(1)

    ingestor = IngestorImpl()
    try:
        chunks, doc, pages = ingestor.ingest(str(file_path))
    except Exception as e:
        print(f"Error: failed to ingest file: {e}", file=sys.stderr)
        sys.exit(1)

    if not chunks:
        print("Refused to answer: not verifiable in source text")
        sys.exit(0)

    query = args.query
    # Find best chunk by word overlap/semantic similarity
    from kernel.core.embeddings import get_embedding, cosine_similarity
    from kernel.core.grounding import normalize_text
    query_emb = get_embedding(query)
    best_chunk = None
    best_score = 0.0

    for chunk in chunks:
        chunk_emb = get_embedding(chunk.text)
        sim = cosine_similarity(query_emb, chunk_emb)
        if sim > best_score:
            best_score = sim
            best_chunk = chunk

    # Fallback to simple keyword check if best score is low
    q_words = set(normalize_text(query).split())
    if best_score < 0.3 or not best_chunk:
        # check if any chunk has keyword overlap
        best_overlap = 0
        for chunk in chunks:
            c_words = set(normalize_text(chunk.text).split())
            overlap = q_words.intersection(c_words)
            if len(overlap) > best_overlap:
                best_overlap = len(overlap)
                best_chunk = chunk

        if best_overlap == 0 or not best_chunk:
            print("Refused to answer: not verifiable in source text")
            sys.exit(0)

    # Find the sentence in the best_chunk that has the highest overlap with the query
    import re
    sentences = re.split(r'(?<=[.!?])\s+', best_chunk.text)
    best_sentence = ""
    best_sent_score = -1

    for sent in sentences:
        s_words = set(normalize_text(sent).split())
        overlap = q_words.intersection(s_words)
        if len(overlap) > best_sent_score:
            best_sent_score = len(overlap)
            best_sentence = sent

    if not best_sentence or best_sent_score == 0:
        print("Refused to answer: not verifiable in source text")
        sys.exit(0)

    # Ground the best_sentence
    from kernel.core.grounding import GroundingVerifierImpl
    verifier = GroundingVerifierImpl()
    method, anchors = verifier.verify(best_sentence, best_sentence, chunks)
    if method == GroundingMethod.BLOCK or not anchors:
        print("Refused to answer: not verifiable in source text")
        sys.exit(0)

    # Format output as requested
    citation = anchors[0]
    bbox_str = f"[{citation.bbox.x0:.3f}, {citation.bbox.y0:.3f}, {citation.bbox.x1:.3f}, {citation.bbox.y1:.3f}]" if citation.bbox else "None"
    print(f"Answer: {best_sentence.strip()}")
    print(f"Citation: page {citation.page}, bbox {bbox_str}, method {method.value}")


def cmd_correct(args):
    db_path = get_db_path()
    store = MemoryStoreImpl(db_path)
    ext = store.get_extraction(args.extraction_id)
    if not ext:
        print(f"Error: extraction not found: {args.extraction_id}", file=sys.stderr)
        sys.exit(1)

    correction = Correction(
        ext_id=ext.ext_id,
        original=ext.value,
        corrected=args.new_value,
        reason="Manual CLI correction",
        by="cli-user",
    )
    store.record_correction(correction)
    print(f"Recorded correction: {ext.value} -> {args.new_value}")


def main():
    parser = argparse.ArgumentParser(description="Kairo Headless CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # index
    parser_index = subparsers.add_parser("index", help="Index a document")
    parser_index.add_argument("file", help="Path to file")

    # run
    parser_run = subparsers.add_parser("run", help="Run domain-specific extraction pack")
    parser_run.add_argument("file", help="Path to file")
    parser_run.add_argument("--pack", required=True, help="Pack name: generic, invoice, paper, contract")

    # ask
    parser_ask = subparsers.add_parser("ask", help="Query the document")
    parser_ask.add_argument("file", help="Path to file")
    parser_ask.add_argument("query", help="Question to ask")

    # correct
    parser_correct = subparsers.add_parser("correct", help="Record human correction")
    parser_correct.add_argument("extraction_id", help="ID of extraction to correct")
    parser_correct.add_argument("new_value", help="New corrected value")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "correct":
        cmd_correct(args)


if __name__ == "__main__":
    main()
