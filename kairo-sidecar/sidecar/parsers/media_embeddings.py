"""
Domain 9: Media Embeddings via EmbedAnything
=============================================

Real wrapper for EmbedAnything image embeddings.

If embed-anything is not installed, HAS_EMBED_ANYTHING = False and
MediaEmbeddings raises RuntimeError on init — NEVER mocks.

Usage:
    emb = MediaEmbeddings(model='Qwen/Qwen2.5-VL')
    vec = emb.embed_image('/path/to/image.png')
    sim = emb.cosine_similarity(vec1, vec2)
    indices = emb.find_similar(query_vec, vectors, top_k=5)
"""
from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple

log = logging.getLogger("kairo.media_embeddings")

# ── Availability check ──────────────────────────────────────────────

HAS_EMBED_ANYTHING: bool = False

try:
    from embed_anything import EmbedConfig  # type: ignore
    HAS_EMBED_ANYTHING = True
except ImportError:
    log.info(
        "embed-anything not installed — MediaEmbeddings will raise on init. "
        "Install: pip install embed-anything"
    )
    EmbedConfig = None  # type: ignore


class MediaEmbeddings:
    """
    Real image-embedding wrapper around EmbedAnything.

    Raises RuntimeError if embed-anything is not installed — never mocks.
    """

    def __init__(
        self,
        model: str = "Qwen/Qwen2.5-VL",
        device: str = "cpu",
    ) -> None:
        if not HAS_EMBED_ANYTHING:
            raise RuntimeError(
                "embed-anything not installed. pip install embed-anything"
            )
        self.model_name = model
        self.device = device
        self._config: Optional[object] = None
        self._init_config()

    def _init_config(self) -> None:
        """Build the EmbedConfig for image embeddings."""
        try:
            # EmbedAnything API: build config for image/vision model
            from embed_anything import (  # type: ignore
                EmbedConfig,
                ImageEmbedConfig,
                VisionEncoder,
            )
            self._config = ImageEmbedConfig(
                model=self.model_name,
                device=self.device,
            )
        except Exception:
            # Fallback: try generic EmbedConfig
            try:
                self._config = EmbedConfig(model=self.model_name)
            except Exception as exc:
                log.error("Failed to build EmbedConfig: %s", exc)
                raise RuntimeError(f"Failed to initialise EmbedConfig: {exc}") from exc

    def embed_image(self, image_path: str) -> List[float]:
        """
        Embed a single image and return the embedding vector.

        Raises RuntimeError if the embedding fails.
        """
        if not HAS_EMBED_ANYTHING:
            raise RuntimeError(
                "embed-anything not installed. pip install embed-anything"
            )
        try:
            from embed_anything import embed_image as _embed_image  # type: ignore
            result = _embed_image(image_path, config=self._config)
            # result is typically a list of Embedding objects with .embedding
            if isinstance(result, list) and len(result) > 0:
                emb = result[0]
                if hasattr(emb, "embedding"):
                    return list(map(float, emb.embedding))
                return list(map(float, emb))
            return list(map(float, result))
        except Exception as exc:
            log.error("embed_image failed for %s: %s", image_path, exc)
            raise RuntimeError(f"embed_image failed: {exc}") from exc

    def embed_images(self, image_paths: List[str]) -> List[List[float]]:
        """
        Batch-embed multiple images.

        Returns a list of embedding vectors, one per image.
        """
        if not HAS_EMBED_ANYTHING:
            raise RuntimeError(
                "embed-anything not installed. pip install embed-anything"
            )
        results: List[List[float]] = []
        for path in image_paths:
            results.append(self.embed_image(path))
        return results

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Returns a float in [-1, 1]. Returns 0.0 if either vector is zero-length.
        """
        if not vec1 or not vec2:
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)

    @staticmethod
    def find_similar(
        query_vec: List[float],
        vectors: List[List[float]],
        top_k: int = 5,
    ) -> List[int]:
        """
        KNN search: return indices of the top_k most similar vectors
        to query_vec, ranked by cosine similarity (descending).
        """
        if not vectors:
            return []
        scored: List[Tuple[float, int]] = []
        for idx, vec in enumerate(vectors):
            sim = MediaEmbeddings.cosine_similarity(query_vec, vec)
            scored.append((sim, idx))
        scored.sort(key=lambda x: x[0], reverse=True)
        k = min(top_k, len(scored))
        return [idx for _, idx in scored[:k]]