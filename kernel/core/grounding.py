"""
Kairo Phantom — Grounding Verifier (SPEC §S3)

Implements the deterministic cascade to refuse-or-cite:
NORMALIZE → EXACT → FUZZY(≥0.92) → SEMANTIC(≥0.86, with re-verify) → BLOCK.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from kernel.core.data_model import (
    Anchor,
    BBox,
    Chunk,
    Extraction,
    ExtractionStatus,
    GroundingMethod,
)
from kernel.core.embeddings import get_embedding, cosine_similarity

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """NORMALIZE step: strip whitespace/case/punctuation/number-format variants."""
    text = text.lower().strip()
    # Remove punctuation
    text = re.sub(r'[^\w\s\-\.]', '', text)
    # Normalize multiple whitespaces to single space
    text = " ".join(text.split())
    # Strip currency symbols if any left
    text = re.sub(r'[\$\€\£\¥]', '', text)
    return text

def levenshtein_ratio(s1: str, s2: str) -> float:
    """Calculate Levenshtein similarity ratio between two strings."""
    s1 = s1.lower()
    s2 = s2.lower()
    if s1 == s2:
        return 1.0
    if len(s1) == 0 or len(s2) == 0:
        return 0.0

    rows = len(s1) + 1
    cols = len(s2) + 1
    dist = [[0 for _ in range(cols)] for _ in range(rows)]

    for i in range(1, rows):
        dist[i][0] = i
    for j in range(1, cols):
        dist[0][j] = j

    for col in range(1, cols):
        for row in range(1, rows):
            if s1[row-1] == s2[col-1]:
                cost = 0
            else:
                cost = 1
            dist[row][col] = min(dist[row-1][col] + 1,
                                 dist[row][col-1] + 1,
                                 dist[row-1][col-1] + cost)

    return 1.0 - (dist[rows-1][cols-1] / max(len(s1), len(s2)))

def best_fuzzy_match(value: str, text: str) -> tuple[float, tuple[int, int]]:
    """Scan windows of words in text to find best fuzzy substring match.
    Returns (best_ratio, (start_char, end_char)).
    """
    val_norm = normalize_text(value)
    if not val_norm:
        return 0.0, (0, 0)

    val_words = val_norm.split()
    n = len(val_words)

    # We want to find exact positions in the original text, so we'll tokenize with spans
    words_spans = []
    for m in re.finditer(r'\S+', text):
        words_spans.append((m.group(0), m.start(), m.end()))

    if not words_spans:
        return 0.0, (0, 0)

    best_ratio = 0.0
    best_span = (0, 0)

    # Scan windows of size from n-1 to n+2
    for length in range(max(1, n-1), min(len(words_spans) + 1, n+3)):
        for i in range(len(words_spans) - length + 1):
            window = words_spans[i:i+length]
            sub_text = text[window[0][1]:window[-1][2]]
            sub_norm = normalize_text(sub_text)
            
            ratio = levenshtein_ratio(val_norm, sub_norm)
            if ratio > best_ratio:
                best_ratio = ratio
                best_span = (window[0][1], window[-1][2])

    return best_ratio, best_span


class GroundingVerifierImpl:
    """Grounding verifier cascade implementation."""

    def __init__(self, fuzzy_threshold: float = 0.92, semantic_threshold: float = 0.86) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self.semantic_threshold = semantic_threshold

    def verify(self, value: str, source_span: str, chunks: list[Chunk]) -> tuple[GroundingMethod, tuple[Anchor, ...]]:
        """Verify the value/source_span against all chunks in the document.
        Returns (method, tuple of anchors).
        """
        if not chunks:
            return GroundingMethod.BLOCK, ()

        # 1. Normalize target text
        target = source_span if source_span else value
        if not target.strip():
            return GroundingMethod.BLOCK, ()

        norm_target = normalize_text(target)

        # 2. EXACT match
        for chunk in chunks:
            if target.lower() in chunk.text.lower():
                # Find start and end offset
                start = chunk.text.lower().find(target.lower())
                end = start + len(target)
                anchor = Anchor(
                    chunk_id=chunk.chunk_id,
                    char_span=(start, end),
                    page=chunk.page,
                    bbox=chunk.bbox,
                )
                return GroundingMethod.EXACT, (anchor,)

        # 3. FUZZY match (Levenshtein token ratio >= 0.92)
        best_ratio = 0.0
        best_anchor = None
        for chunk in chunks:
            ratio, span = best_fuzzy_match(target, chunk.text)
            if ratio >= self.fuzzy_threshold and ratio > best_ratio:
                best_ratio = ratio
                best_anchor = Anchor(
                    chunk_id=chunk.chunk_id,
                    char_span=span,
                    page=chunk.page,
                    bbox=chunk.bbox,
                )

        if best_anchor:
            return GroundingMethod.FUZZY, (best_anchor,)

        # 4. SEMANTIC match (Cosine similarity >= 0.86 + re-verify)
        # Compute embedding of the value
        target_emb = get_embedding(target)
        best_cosine = 0.0
        best_sem_chunk = None

        for chunk in chunks:
            if not chunk.embedding:
                # compute embedding on demand if missing
                # (usually populated at index time)
                from dataclasses import replace
                chunk_emb = get_embedding(chunk.text)
            else:
                chunk_emb = chunk.embedding

            sim = cosine_similarity(target_emb, chunk_emb)
            if sim >= self.semantic_threshold and sim > best_cosine:
                best_cosine = sim
                best_sem_chunk = chunk

        # Re-verify step: check if there's any word intersection/meaning overlap
        if best_sem_chunk:
            chunk_words = set(normalize_text(best_sem_chunk.text).split())
            target_words = set(norm_target.split())
            # Require at least 25% or 1 word of target words to be present in chunk for re-verification
            intersection = chunk_words.intersection(target_words)
            if len(intersection) > 0 or len(target_words) == 0:
                anchor = Anchor(
                    chunk_id=best_sem_chunk.chunk_id,
                    char_span=(0, len(best_sem_chunk.text)),
                    page=best_sem_chunk.page,
                    bbox=best_sem_chunk.bbox,
                )
                return GroundingMethod.SEMANTIC, (anchor,)

        # 5. BLOCK if none of the above pass
        return GroundingMethod.BLOCK, ()
