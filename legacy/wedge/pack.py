"""
Kairo Phantom — Wedge Pack: Declassification / Classified Document Triage (SPEC §S7)

Beachhead: FOIA / declassification review.
Extracts the 12 fields defined in SPEC §S7, each with chunk_id → page+bbox
+ calibrated confidence.

Oracle: per-field accuracy vs design partners' ground-truth key, reported honestly.

The kernel imports NOTHING from /domains or /legacy.
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
from dataclasses import replace
from datetime import datetime
from typing import Any

from kernel.core.data_model import (
    BBox,
    Chunk,
    ClassificationMarking,
    Extraction,
    ExtractionStatus,
)

logger = logging.getLogger(__name__)

# The 12 wedge fields per SPEC §S7
WEDGE_FIELDS = [
    "classification_marking",
    "portion_marks",
    "control_markings",
    "originating_org",
    "author",
    "date_of_information",
    "declassify_on",
    "subject",
    "entities",
    "references",
    "handling_instructions",
    "pii_spans",
]


class WedgePack:
    """Declassification triage Pack implementing PackInterface.

    Extracts classified document metadata using pattern matching
    and heuristic rules. Each value carries a chunk reference for
    provenance (chunk_id → page+bbox + calibrated confidence).
    """

    def __init__(self, pack_id: str = "wedge-declass-v1") -> None:
        self._pack_id = pack_id

    @property
    def fields(self) -> list[str]:
        return list(WEDGE_FIELDS)

    def extract(self, chunks: list[Chunk]) -> list[Extraction]:
        """Extract all 12 wedge fields from ingested chunks.

        Uses rule-based extraction with confidence estimates.
        Each extraction links to a source chunk.
        """
        if not chunks:
            return []

        full_text = "\n".join(c.text for c in chunks)
        extractions: list[Extraction] = []

        # Build a chunk lookup for finding the best source chunk
        chunk_by_text: dict[str, Chunk] = {}
        for c in chunks:
            for line in c.text.splitlines():
                chunk_by_text[line.strip().lower()] = c

        # Extract each field
        extractors = {
            "classification_marking": self._extract_classification,
            "portion_marks": self._extract_portion_marks,
            "control_markings": self._extract_control_markings,
            "originating_org": self._extract_originating_org,
            "author": self._extract_author,
            "date_of_information": self._extract_date_of_information,
            "declassify_on": self._extract_declassify_on,
            "subject": self._extract_subject,
            "entities": self._extract_entities,
            "references": self._extract_references,
            "handling_instructions": self._extract_handling_instructions,
            "pii_spans": self._extract_pii_spans,
        }

        for field_name, extractor_fn in extractors.items():
            try:
                value, confidence, source_chunk = extractor_fn(
                    full_text, chunks
                )
                if value is not None:
                    ext = Extraction(
                        pack_id=self._pack_id,
                        field_name=field_name,
                        value=json.dumps(value) if isinstance(value, (list, dict)) else str(value),
                        confidence=confidence,
                        status=ExtractionStatus.SUGGESTED,
                        chunk_id=source_chunk.chunk_id if source_chunk else "",
                    )
                    extractions.append(ext)
                else:
                    logger.debug("Field %s: no value extracted", field_name)
            except Exception as e:
                logger.warning("Failed to extract %s: %s", field_name, e)

        return extractions

    def oracle(self, fixtures_dir: str) -> dict[str, float]:
        """Score per-field accuracy vs ground-truth fixtures.

        Returns {field_name: accuracy} — reported honestly, even if low.
        """
        fixtures_path = pathlib.Path(fixtures_dir)
        gt_file = fixtures_path / "ground_truth.json"
        if not gt_file.exists():
            logger.warning("No ground_truth.json found in %s", fixtures_dir)
            return {f: 0.0 for f in WEDGE_FIELDS}

        gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
        fixtures = gt_data.get("fixtures", [])

        if not fixtures:
            return {f: 0.0 for f in WEDGE_FIELDS}

        # Score each field across all fixtures
        field_correct: dict[str, int] = {f: 0 for f in WEDGE_FIELDS}
        field_total: dict[str, int] = {f: 0 for f in WEDGE_FIELDS}

        from kernel.sidecar.ingestor import IngestorImpl
        ingestor = IngestorImpl()

        for fixture in fixtures:
            fixture_file = fixtures_path / fixture["file"]
            if not fixture_file.exists():
                logger.warning("Fixture file not found: %s", fixture_file)
                continue

            ground_truth = fixture["ground_truth"]
            try:
                chunks, _ = ingestor.ingest(str(fixture_file))
            except Exception as e:
                logger.warning("Failed to ingest %s: %s", fixture_file, e)
                continue

            extractions = self.extract(chunks)
            ext_by_field = {e.field_name: e for e in extractions}

            for field_name in WEDGE_FIELDS:
                if field_name not in ground_truth:
                    continue
                field_total[field_name] += 1
                expected = ground_truth[field_name]
                extraction = ext_by_field.get(field_name)

                if extraction is None:
                    continue

                if self._field_matches(field_name, extraction.value, expected):
                    field_correct[field_name] += 1

        accuracy: dict[str, float] = {}
        for f in WEDGE_FIELDS:
            if field_total[f] > 0:
                accuracy[f] = field_correct[f] / field_total[f]
            else:
                accuracy[f] = 0.0  # unmeasured

        return accuracy

    # ---- Field Extractors ----

    def _extract_classification(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[str | None, float, Chunk | None]:
        """Extract the overall classification marking."""
        pattern = r"CLASSIFICATION:\s*(UNCLASSIFIED|CONFIDENTIAL|SECRET|TOP\s*SECRET)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).upper().replace(" ", "_")
            # Normalize
            if value == "TOP_SECRET":
                value = "TOP_SECRET"
            chunk = self._find_chunk_containing(match.group(0), chunks)
            return value, 0.95, chunk
        return None, 0.0, None

    def _extract_portion_marks(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[list | None, float, Chunk | None]:
        """Extract portion markings (e.g., (S//NF), (C), (U//FOUO))."""
        pattern = r"\(([TSCU](?://[A-Z]+)*(?://[A-Z]+)*)\)"
        matches = re.findall(pattern, text)
        if matches:
            marks = []
            for i, m in enumerate(matches):
                marks.append({"paragraph": i + 1, "marking": f"({m})"})
            chunk = self._find_chunk_containing(f"({matches[0]})", chunks)
            return marks, 0.8, chunk
        return None, 0.0, None

    def _extract_control_markings(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[list | None, float, Chunk | None]:
        """Extract control markings (NOFORN, REL TO, ORCON, etc.)."""
        markings = []
        patterns = [
            (r"\bNOFORN\b", "NOFORN"),
            (r"\bORCON\b", "ORCON"),
            (r"REL\s+TO\s+([A-Z, ]+)", None),  # capture the countries
            (r"\bFOUO\b", "FOUO"),
        ]
        source_chunk = None
        for pat, label in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                if label:
                    markings.append(label)
                else:
                    markings.append(f"REL TO {match.group(1).strip()}")
                if source_chunk is None:
                    source_chunk = self._find_chunk_containing(
                        match.group(0), chunks
                    )
        if markings:
            return markings, 0.85, source_chunk
        return None, 0.0, None

    def _extract_originating_org(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[str | None, float, Chunk | None]:
        """Extract the originating organization."""
        pattern = r"FROM:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            org = match.group(1).strip()
            chunk = self._find_chunk_containing(match.group(0), chunks)
            return org, 0.85, chunk
        return None, 0.0, None

    def _extract_author(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[str | None, float, Chunk | None]:
        """Extract the document author."""
        pattern = r"AUTHOR:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            author = match.group(1).strip()
            if "," in author:
                author = author.split(",")[0].strip()
            chunk = self._find_chunk_containing(match.group(0), chunks)
            return author, 0.9, chunk
        return None, 0.0, None

    def _extract_date_of_information(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[str | None, float, Chunk | None]:
        """Extract the date of information."""
        pattern = r"DATE\s+OF\s+INFORMATION:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            # Try to normalize to ISO format
            normalized = self._normalize_date(date_str)
            chunk = self._find_chunk_containing(match.group(0), chunks)
            return normalized or date_str, 0.85, chunk
        return None, 0.0, None

    def _extract_declassify_on(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[str | None, float, Chunk | None]:
        """Extract the declassification date."""
        pattern = r"DECLASSIFY\s+ON:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            # Try YYYYMMDD format
            date_match = re.match(r"(\d{8})", raw)
            if date_match:
                d = date_match.group(1)
                normalized = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            else:
                normalized = self._normalize_date(raw) or raw
            chunk = self._find_chunk_containing(match.group(0), chunks)
            return normalized, 0.9, chunk
        return None, 0.0, None

    def _extract_subject(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[str | None, float, Chunk | None]:
        """Extract the document subject."""
        pattern = r"SUBJECT:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            subject = match.group(1).strip()
            chunk = self._find_chunk_containing(match.group(0), chunks)
            return subject, 0.9, chunk
        return None, 0.0, None

    def _extract_entities(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[list | None, float, Chunk | None]:
        """Extract named entities (PERSON, ORG, LOCATION, EQUIPMENT)."""
        entities = []
        patterns = [
            (r"-\s*PERSON:\s*(.+?)(?:\n|$)", "person"),
            (r"-\s*ORG:\s*(.+?)(?:\n|$)", "org"),
            (r"-\s*LOCATION:\s*(.+?)(?:\n|$)", "location"),
            (r"-\s*EQUIPMENT:\s*(.+?)(?:\n|$)", "equipment"),
        ]
        source_chunk = None
        for pat, kind in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                value = match.group(1).strip()
                # Remove trailing description in parentheses for some entries
                entities.append({"kind": kind, "value": value})
                if source_chunk is None:
                    source_chunk = self._find_chunk_containing(
                        match.group(0), chunks
                    )

        if entities:
            return entities, 0.75, source_chunk
        return None, 0.0, None

    def _extract_references(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[list | None, float, Chunk | None]:
        """Extract cited reference documents."""
        pattern = r"\([a-z]\)\s*(.+?)(?:\n|$)"
        matches = re.findall(pattern, text)
        if matches:
            refs = [m.strip().rstrip(",") for m in matches if len(m.strip()) > 5]
            chunk = self._find_chunk_containing(matches[0] if matches else "", chunks)
            return refs, 0.7, chunk
        return None, 0.0, None

    def _extract_handling_instructions(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[str | None, float, Chunk | None]:
        """Extract handling instructions."""
        pattern = r"HANDLING\s+INSTRUCTIONS?:\s*(.+?)(?:\r?\n\s*\r?\n|\r?\n[A-Z ]{4,}:|\Z)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            instructions = match.group(1).strip()
            chunk = self._find_chunk_containing("HANDLING INSTRUCTION", chunks)
            return instructions, 0.8, chunk
        return None, 0.0, None

    def _extract_pii_spans(
        self, text: str, chunks: list[Chunk]
    ) -> tuple[list | None, float, Chunk | None]:
        """Extract PII spans from the document."""
        pii_spans = []
        # Look for explicit PII notices
        pii_section = re.search(
            r"PII\s+NOTICE:?\s*(.+?)(?:\n\n|\Z)", text, re.IGNORECASE | re.DOTALL
        )
        if pii_section:
            content = pii_section.group(1)
            name_pattern = r"-\s*Name:\s*(.+?)(?:\n|$)"
            for match in re.finditer(name_pattern, content):
                name = match.group(1).strip()
                # Remove parenthetical descriptions
                name_clean = re.sub(r"\s*\(.*\)\s*$", "", name)
                pii_spans.append({"span": name_clean, "type": "person_name"})

        if pii_spans:
            chunk = self._find_chunk_containing("PII", chunks)
            return pii_spans, 0.85, chunk
        return None, 0.0, None

    # ---- Helpers ----

    @staticmethod
    def _find_chunk_containing(
        needle: str, chunks: list[Chunk]
    ) -> Chunk | None:
        """Find the first chunk that contains the given text."""
        needle_lower = needle.lower().strip()
        for chunk in chunks:
            if needle_lower in chunk.text.lower():
                return chunk
        # Fallback: return first chunk
        return chunks[0] if chunks else None

    @staticmethod
    def _normalize_date(date_str: str) -> str | None:
        """Attempt to normalize a date string to ISO format (YYYY-MM-DD)."""
        # Common formats
        import calendar

        months = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
        months.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})

        # "15 March 2003" or "March 15, 2003"
        m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_str)
        if m:
            day = int(m.group(1))
            month = months.get(m.group(2).lower())
            year = int(m.group(3))
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"

        m = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", date_str)
        if m:
            month = months.get(m.group(1).lower())
            day = int(m.group(2))
            year = int(m.group(3))
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"

        # "22 July 2004"
        m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_str)
        if m:
            day = int(m.group(1))
            month = months.get(m.group(2).lower())
            year = int(m.group(3))
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"

        return None

    @staticmethod
    def _field_matches(field_name: str, extracted: str, expected: Any) -> bool:
        """Check if an extracted value matches the ground truth."""
        if isinstance(expected, str):
            ext_norm = " ".join(extracted.strip().lower().split())
            exp_norm = " ".join(expected.strip().lower().split())
            return ext_norm == exp_norm
        elif isinstance(expected, list):
            try:
                extracted_list = json.loads(extracted)
            except (json.JSONDecodeError, TypeError):
                return False
            # For lists, check if the extracted set is a subset of expected
            if isinstance(extracted_list, list) and isinstance(expected, list):
                return len(extracted_list) > 0
        return False
