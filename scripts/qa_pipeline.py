"""
Kairo Phantom — Q&A Pipeline (P0.1)

The runnable artifact: ingest a document, answer a question with a grounded
citation (exact bounding-box region), or refuse when the answer cannot be
grounded in the source.

Core promise: "No source → no answer."

This module is the engine behind `make run DOC=... Q=...` and
`scripts/first_run.py`. It uses:
  - IngestorImpl to produce Chunks with page + bbox
  - GroundingVerifierImpl to independently verify every answer against
    stored document geometry (the model can never self-certify)
  - A retrieval step (embedding similarity) to find candidate chunks,
    then the deterministic grounding cascade to verify the answer

No mocks, no stubs. If the pipeline breaks, this produces a real error.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import textwrap
from datetime import datetime, timezone
from typing import Any

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.core.data_model import (
    Answer,
    Anchor,
    BBox,
    Chunk,
    Document,
    Extraction,
    ExtractionStatus,
    GroundingMethod,
)
from kernel.core.embeddings import get_embedding, cosine_similarity
from kernel.core.grounding import (
    GroundingVerifierImpl,
    normalize_text,
    best_fuzzy_match,
)
from kernel.sidecar.ingestor import IngestorImpl


# ---------------------------------------------------------------------------
# Dependency check — precise, actionable errors (not stack traces)
# ---------------------------------------------------------------------------

def _check_dependencies() -> None:
    """Verify required dependencies are importable. Print actionable errors.

    numpy is optional — the embeddings module has a pure-Python fallback.
    We only check for things that have no fallback and would produce a
    confusing stack trace.
    """
    # Currently all core deps are stdlib or have fallbacks.
    # This function is the hook for future hard-required deps.
    pass


# ---------------------------------------------------------------------------
# Retrieval — find the most relevant chunk(s) for a query
# ---------------------------------------------------------------------------

def _retrieve_chunks(
    query: str, chunks: list[Chunk], top_k: int = 3
) -> list[tuple[Chunk, float]]:
    """Return the top-k chunks most relevant to the query.

    Uses keyword overlap as the primary signal (more reliable than hash-based
    embeddings for short documents), with embedding cosine similarity as a
    tiebreaker.
    """
    if not chunks:
        return []

    query_kw = _query_keywords(query)
    if not query_kw:
        query_kw = set(normalize_text(query).split())

    query_emb = get_embedding(query)
    scored: list[tuple[Chunk, float]] = []

    for chunk in chunks:
        # Primary signal: keyword overlap
        chunk_words = set(normalize_text(chunk.text).split())
        kw_overlap = len(query_kw & chunk_words) if query_kw else 0

        # Secondary signal: embedding similarity
        chunk_emb = chunk.embedding if chunk.embedding else get_embedding(chunk.text)
        emb_sim = cosine_similarity(query_emb, chunk_emb)

        # Combined score: keyword overlap weighted 10x over embedding sim
        combined = kw_overlap * 10.0 + emb_sim
        scored.append((chunk, combined))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [(c, s) for c, s in scored[:top_k]]


# ---------------------------------------------------------------------------
# Answer extraction — pull the answer sentence/phrase from a chunk
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


_STOP_WORDS = {
    "what", "is", "the", "who", "when", "where", "why", "how",
    "are", "was", "were", "do", "does", "did", "can", "could",
    "will", "would", "should", "of", "in", "on", "at", "to",
    "for", "and", "or", "a", "an", "this", "that", "which",
    "whose", "whom", "list", "name", "tell", "me", "give",
    "show", "find", "get", "please", "s", "t",
}


def _query_keywords(query: str) -> set[str]:
    """Extract content keywords from a query (stop words removed)."""
    words = set(normalize_text(query).split())
    return words - _STOP_WORDS


def _chunk_relevance_score(query_kw: set[str], chunk: Chunk) -> int:
    """Count how many query keywords appear in the chunk text."""
    if not query_kw:
        return 0
    chunk_words = set(normalize_text(chunk.text).split())
    return len(query_kw & chunk_words)


def _extract_answer_text(query: str, chunk: Chunk) -> str:
    """Extract the most relevant sentence or phrase from a chunk for the query.

    Strategy:
    1. Find the sentence with the highest keyword overlap with the query.
    2. Fall back to the full chunk text if no good sentence is found.
    """
    sentences = _split_sentences(chunk.text)
    if not sentences:
        return chunk.text.strip()

    query_kw = _query_keywords(query)
    if not query_kw:
        query_kw = set(normalize_text(query).split())

    best_sentence = ""
    best_score = -1
    for sent in sentences:
        sent_words = set(normalize_text(sent).split())
        overlap = len(query_kw & sent_words)
        if overlap > best_score:
            best_score = overlap
            best_sentence = sent

    if best_score <= 0:
        return chunk.text.strip()

    return best_sentence


# ---------------------------------------------------------------------------
# Main Q&A function
# ---------------------------------------------------------------------------

def answer_question(
    doc_path: str,
    query: str,
    verifier: GroundingVerifierImpl | None = None,
) -> Answer:
    """Answer a question about a document with a grounded citation or refusal.

    Returns an Answer object:
      - grounded=True, refused=False  → answer with citations (page, bbox)
      - grounded=False, refused=True  → refusal (could not ground in source)

    No mocks: uses the real ingestor + real grounding verifier.
    """
    _check_dependencies()

    filepath = pathlib.Path(doc_path)
    if not filepath.exists():
        raise FileNotFoundError(f"Document not found: {doc_path}")

    if not query or not query.strip():
        raise ValueError("Query must not be empty")

    # 1. Ingest the document → chunks with page + bbox
    ingestor = IngestorImpl()
    chunks, doc, pages = ingestor.ingest(doc_path)

    if not chunks:
        return Answer(
            query=query,
            text="I cannot answer this question because the document could not be parsed.",
            grounded=False,
            refused=True,
        )

    # 2. Retrieve the most relevant chunks
    retrieved = _retrieve_chunks(query, chunks, top_k=3)

    if not retrieved:
        return Answer(
            query=query,
            text="I cannot answer this question because no relevant content was found in the document.",
            grounded=False,
            refused=True,
        )

    # 2b. Relevance gate: if fewer than 50% of the query's content keywords
    #     appear in ANY chunk, the question is likely unanswerable → REFUSE.
    #     This is stricter than just "any keyword" — it prevents grounding
    #     irrelevant text just because one word coincidentally matches.
    query_kw = _query_keywords(query)
    if query_kw:
        max_relevance = max(_chunk_relevance_score(query_kw, c) for c in chunks)
        # Require at least half of query keywords to appear in some chunk.
        # This prevents grounding irrelevant text when only one word matches.
        min_required = max(1, (len(query_kw) + 1) // 2)
        if max_relevance < min_required:
            return Answer(
                query=query,
                text=(
                    "I cannot answer this question because the document does not "
                    "contain sufficient information relevant to this query. "
                    "No source → no answer."
                ),
                grounded=False,
                refused=True,
            )

    # 2c. Verify the best retrieved chunk actually contains query keywords.
    #     If the best chunk has zero keyword overlap, the retrieval is not
    #     relevant enough → refuse (avoid grounding irrelevant text).
    best_chunk, best_score = retrieved[0]
    best_chunk_kw_overlap = _chunk_relevance_score(query_kw, best_chunk) if query_kw else 0
    if best_chunk_kw_overlap == 0:
        return Answer(
            query=query,
            text=(
                "I cannot answer this question because no relevant content was "
                "found in the document. No source → no answer."
            ),
            grounded=False,
            refused=True,
        )

    # 3. Extract candidate answer text from ALL retrieved chunks
    #    Search across all retrieved chunks for the best sentence, not just
    #    the top one — this handles cases where the right answer is in a
    #    lower-ranked chunk.
    query_kw = _query_keywords(query)
    if not query_kw:
        query_kw = set(normalize_text(query).split())

    best_answer_text = ""
    best_sentence_score = -1

    for chunk, _score in retrieved:
        candidate = _extract_answer_text(query, chunk)
        # Score the candidate by keyword overlap
        candidate_words = set(normalize_text(candidate).split())
        candidate_score = len(query_kw & candidate_words) if query_kw else 0
        if candidate_score > best_sentence_score:
            best_sentence_score = candidate_score
            best_answer_text = candidate

    answer_text = best_answer_text

    # 4. Verify the answer using the grounding cascade
    #    The verifier independently re-checks the answer against stored geometry.
    #    The model can never self-certify a bounding box.
    if verifier is None:
        verifier = GroundingVerifierImpl()

    method, anchors = verifier.verify(answer_text, answer_text, chunks)

    if method == GroundingMethod.BLOCK or not anchors:
        # Could not ground → REFUSE (core promise: "No source → no answer")
        return Answer(
            query=query,
            text=(
                "I cannot answer this question because I could not ground the "
                "answer in the source document. No source → no answer."
            ),
            grounded=False,
            refused=True,
        )

    # 5. Build the grounded answer with citations
    citation_strs: list[str] = []
    for anchor in anchors:
        bbox = anchor.bbox
        if bbox:
            citation_strs.append(
                f"page {anchor.page}, "
                f"bbox=[{bbox.x0:.3f}, {bbox.y0:.3f}, {bbox.x1:.3f}, {bbox.y1:.3f}]"
            )
        else:
            citation_strs.append(f"page {anchor.page}")

    citation_summary = "; ".join(citation_strs)
    full_answer = f"{answer_text}\n  [Source: {citation_summary} | Method: {method.value}]"

    return Answer(
        query=query,
        text=full_answer,
        citations=anchors,
        grounded=True,
        refused=False,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _format_answer(answer: Answer, doc_path: str) -> str:
    """Format an Answer for terminal output."""
    lines = [
        "=" * 70,
        f"Kairo Phantom — Grounded Q&A",
        "=" * 70,
        f"Document: {doc_path}",
        f"Question: {answer.query}",
        "-" * 70,
    ]

    if answer.refused and not answer.grounded:
        lines.append(f"ANSWER: [REFUSED] {answer.text}")
    elif answer.grounded:
        lines.append(f"ANSWER: {answer.text}")
        if answer.citations:
            lines.append("")
            lines.append("Citations (verified by independent grounding checker):")
            for i, anchor in enumerate(answer.citations, 1):
                bbox = anchor.bbox
                if bbox:
                    lines.append(
                        f"  [{i}] page {anchor.page}, "
                        f"bbox=({bbox.x0:.3f}, {bbox.y0:.3f}, {bbox.x1:.3f}, {bbox.y1:.3f}), "
                        f"char_span=({anchor.char_span[0]}, {anchor.char_span[1]})"
                    )
                else:
                    lines.append(f"  [{i}] page {anchor.page}")
    else:
        lines.append(f"ANSWER: {answer.text}")

    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Kairo Phantom — Grounded Q&A (No source → no answer)"
    )
    parser.add_argument(
        "--doc", required=True,
        help="Path to the document to query",
    )
    parser.add_argument(
        "--question", "-q", required=True,
        help="The question to answer",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON instead of human-readable text",
    )
    args = parser.parse_args()

    try:
        answer = answer_question(args.doc, args.question)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        output = {
            "query": answer.query,
            "text": answer.text,
            "grounded": answer.grounded,
            "refused": answer.refused,
            "citations": [
                {
                    "page": a.page,
                    "bbox": [a.bbox.x0, a.bbox.y0, a.bbox.x1, a.bbox.y1]
                    if a.bbox else None,
                    "char_span": list(a.char_span),
                }
                for a in answer.citations
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(_format_answer(answer, args.doc))

    # Exit code: 0 = grounded answer, 1 = refusal (still a valid result)
    sys.exit(0 if answer.grounded else 1)


if __name__ == "__main__":
    main()