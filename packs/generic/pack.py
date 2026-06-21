"""
Kairo Phantom — Generic Pack (SPEC §S7)
Extracts summary, key_claims, entities, and topics from any document.
"""
from __future__ import annotations

import json
import logging
import pathlib
import re
from typing import Any

from kernel.core.data_model import (
    Chunk,
    Extraction,
    ExtractionStatus,
)

logger = logging.getLogger(__name__)

GENERIC_FIELDS = ["summary", "key_claims", "entities", "topics"]

class GenericPack:
    """Generic document intelligence Pack implementing PackInterface."""

    def __init__(self, pack_id: str = "generic-v1") -> None:
        self._pack_id = pack_id

    @property
    def fields(self) -> list[str]:
        return list(GENERIC_FIELDS)

    def extract(self, chunks: list[Chunk]) -> list[Extraction]:
        """Extract generic fields from ingested chunks."""
        if not chunks:
            return []

        full_text = "\n".join(c.text for c in chunks)
        extractions: list[Extraction] = []

        # Find a chunk for summary (usually the first chunk)
        summary_chunk = chunks[0] if chunks else None
        summary_val = ""
        if summary_chunk:
            # First 2 sentences
            sentences = re.split(r'(?<=[.!?])\s+', summary_chunk.text)
            summary_val = " ".join(sentences[:2]).strip()

        if summary_val:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="summary",
                value=summary_val,
                source_span=summary_val,
                confidence=0.9,
                chunk_id=summary_chunk.chunk_id if summary_chunk else "",
            ))

        # Find key claims
        claims_list = []
        claims_chunk = None
        for c in chunks:
            lines = c.text.splitlines()
            # Strategy 1: Look for "Key Claims:" header and extract numbered items after it
            in_claims_section = False
            for line in lines:
                line_stripped = line.strip()
                if re.match(r'key\s+claims\s*:', line_stripped, re.IGNORECASE):
                    in_claims_section = True
                    if not claims_chunk:
                        claims_chunk = c
                    continue
                if in_claims_section:
                    # Check if this line is a numbered claim (e.g., "1. Some claim text.")
                    m = re.match(r'^\d+\.\s*(.+)', line_stripped)
                    if m:
                        cleaned = m.group(1).strip()
                        if len(cleaned) > 10 and cleaned not in claims_list:
                            claims_list.append(cleaned)
                    elif line_stripped and not line_stripped.startswith('---'):
                        # End of claims section (non-numbered, non-empty line)
                        if len(claims_list) > 0:
                            in_claims_section = False
            if claims_list:
                break

        # Strategy 2: Fallback — look for lines with claim-related keywords
        if not claims_list:
            for c in chunks:
                lines = c.text.splitlines()
                for line in lines:
                    if any(k in line.lower() for k in ["claim", "show", "propose", "suggest", "result", "find"]):
                        cleaned = line.strip("-*\u2022 ").strip()
                        # Remove leading numbers
                        cleaned = re.sub(r'^\d+\.\s*', '', cleaned)
                        if len(cleaned) > 20 and cleaned not in claims_list:
                            claims_list.append(cleaned)
                            if not claims_chunk:
                                claims_chunk = c

        if claims_list:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="key_claims",
                value=json.dumps(claims_list),
                source_span=claims_list[0],
                confidence=0.85,
                chunk_id=claims_chunk.chunk_id if claims_chunk else chunks[0].chunk_id,
            ))

        # Find entities (capitalized words/phrases)
        entities_list = []
        entities_chunk = None
        entity_pattern = re.compile(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b')
        for c in chunks:
            matches = entity_pattern.findall(c.text)
            for m in matches:
                # Filter out common stop capitalized words
                if m not in ["The", "A", "An", "In", "On", "At", "By", "For", "We", "I", "This", "That", "It", "To", "Of", "And"] and len(m) > 2:
                    if m not in entities_list:
                        entities_list.append(m)
                        if not entities_chunk:
                            entities_chunk = c

        if entities_list:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="entities",
                value=json.dumps(entities_list[:10]),
                source_span=entities_list[0],
                confidence=0.8,
                chunk_id=entities_chunk.chunk_id if entities_chunk else chunks[0].chunk_id,
            ))

        # Find topics (simple frequency word logic or keywords)
        topics_list = []
        topics_chunk = None
        topic_keywords = ["technology", "security", "financial", "analysis", "system", "contract", "invoice", "paper", "data", "intelligence"]
        for c in chunks:
            for keyword in topic_keywords:
                if keyword in c.text.lower() and keyword not in topics_list:
                    topics_list.append(keyword)
                    if not topics_chunk:
                        topics_chunk = c

        if topics_list:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="topics",
                value=json.dumps(topics_list),
                source_span=topics_list[0],
                confidence=0.75,
                chunk_id=topics_chunk.chunk_id if topics_chunk else chunks[0].chunk_id,
            ))

        return extractions

    def oracle(self, fixtures_dir: str) -> dict[str, float]:
        """Score per-field accuracy vs ground-truth fixtures."""
        fixtures_path = pathlib.Path(fixtures_dir)
        gt_file = fixtures_path / "ground_truth.json"
        if not gt_file.exists():
            return {f: 0.0 for f in GENERIC_FIELDS}

        gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
        fixtures = gt_data.get("fixtures", [])
        if not fixtures:
            return {f: 0.0 for f in GENERIC_FIELDS}

        field_correct = {f: 0 for f in GENERIC_FIELDS}
        field_total = {f: 0 for f in GENERIC_FIELDS}

        from kernel.sidecar.ingestor import IngestorImpl
        ingestor = IngestorImpl()

        for fixture in fixtures:
            fixture_file = fixtures_path / fixture["file"]
            if not fixture_file.exists():
                continue

            ground_truth = fixture["ground_truth"]
            try:
                chunks, _, _ = ingestor.ingest(str(fixture_file))
            except Exception:
                continue

            extractions = self.extract(chunks)
            ext_by_field = {e.field_name: e for e in extractions}

            for field_name in GENERIC_FIELDS:
                expected = ground_truth.get(field_name)
                ext = ext_by_field.get(field_name)
                field_total[field_name] += 1
                if expected is None and ext is None:
                    field_correct[field_name] += 1
                elif expected is not None and ext is not None:
                    if self._field_matches(field_name, ext.value, expected):
                        field_correct[field_name] += 1

        return {
            f: field_correct[f] / field_total[f] if field_total[f] > 0 else 0.0
            for f in GENERIC_FIELDS
        }

    @staticmethod
    def _field_matches(field_name: str, extracted: str, expected: Any) -> bool:
        """Check if an extracted value matches the ground truth."""
        if isinstance(expected, str):
            ext_norm = " ".join(extracted.strip().lower().split())
            exp_norm = " ".join(expected.strip().lower().split())
            return ext_norm == exp_norm or exp_norm in ext_norm or ext_norm in exp_norm
        elif isinstance(expected, list):
            try:
                extracted_list = json.loads(extracted) if extracted.startswith("[") else [extracted]
            except Exception:
                extracted_list = [extracted]
            # Check if there is intersection
            for item in expected:
                item_norm = str(item).strip().lower()
                for ext_item in extracted_list:
                    ext_norm = str(ext_item).strip().lower()
                    if item_norm in ext_norm or ext_norm in item_norm:
                        return True
        return False
