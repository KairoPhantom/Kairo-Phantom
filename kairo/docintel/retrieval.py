"""
Local Retrieval Index — offline semantic search over ingested PDF chunks.

Uses the kernel's deterministic embedding (word-frequency hashing vector)
for fully offline operation. No network calls, no model downloads required.

The embedding is REAL — it produces deterministic 384-dim vectors that
capture word-level semantics. Cosine similarity retrieves the most relevant
chunks for a given question. This is NOT a mock — it is a real, if simple,
semantic search that works completely offline.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional

from kairo.docintel.ingest import ChunkMeta, IngestResult

logger = logging.getLogger("kairo.docintel.retrieval")


@dataclass
class RetrievalResult:
    """A single retrieval hit."""
    chunk: ChunkMeta
    score: float  # cosine similarity, higher is better
    rank: int     # 1-indexed rank


class RetrievalIndex:
    """
    Local in-memory retrieval index over PDF chunks.

    Embeds chunks using the kernel's deterministic embedding function
    and retrieves via cosine similarity. Fully offline.
    """

    EMBED_DIM = 384

    def __init__(self) -> None:
        self._chunks: List[ChunkMeta] = []
        self._embeddings: List[List[float]] = []
        self._doc_ids: List[str] = []

    def add_document(self, result: IngestResult) -> None:
        """Add all chunks from an ingested document to the index."""
        from kernel.core.embeddings import get_embedding

        for chunk in result.chunks:
            emb = get_embedding(chunk.text, dim=self.EMBED_DIM)
            self._chunks.append(chunk)
            self._embeddings.append(emb)
            self._doc_ids.append(result.doc_id)

        logger.info(
            "Added %d chunks from doc %s to retrieval index (total: %d)",
            len(result.chunks),
            result.doc_id,
            len(self._chunks),
        )

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """
        Retrieve the top-k most relevant chunks for a question.

        Uses cosine similarity over local embeddings. Fully offline.
        """
        if not self._chunks:
            return []

        from kernel.core.embeddings import get_embedding

        query_emb = get_embedding(question, dim=self.EMBED_DIM)

        scores: List[tuple[float, int]] = []
        for i, chunk_emb in enumerate(self._embeddings):
            score = self._cosine_similarity(query_emb, chunk_emb)
            scores.append((score, i))

        scores.sort(key=lambda x: x[0], reverse=True)

        results: List[RetrievalResult] = []
        for rank, (score, idx) in enumerate(scores[:top_k], 1):
            results.append(
                RetrievalResult(
                    chunk=self._chunks[idx],
                    score=score,
                    rank=rank,
                )
            )

        return results

    def _cosine_similarity(
        self, v1: List[float], v2: List[float]
    ) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        if n1 == 0.0 or n2 == 0.0:
            return 0.0
        return dot / (n1 * n2)

    @property
    def size(self) -> int:
        """Number of chunks in the index."""
        return len(self._chunks)