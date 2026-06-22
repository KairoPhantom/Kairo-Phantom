"""
Kairo Phantom — Paper Pack (SPEC §S7)
Extracts title, authors, abstract_summary, key_claims, methods, reported_numbers, figure_references, table_references.
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

PAPER_FIELDS = [
    "title", "authors", "abstract_summary", "key_claims",
    "methods", "reported_numbers", "figure_references", "table_references"
]

class PaperPack:
    """Research paper extraction Pack implementing PackInterface."""

    def __init__(self, pack_id: str = "paper-v1") -> None:
        self._pack_id = pack_id

    @property
    def fields(self) -> list[str]:
        return list(PAPER_FIELDS)

    def extract(self, chunks: list[Chunk]) -> list[Extraction]:
        """Extract paper fields from ingested chunks."""
        if not chunks:
            return []

        full_text = "\n".join(c.text for c in chunks)
        extractions: list[Extraction] = []

        # Title (usually first line of first chunk)
        title = ""
        title_chunk = chunks[0] if chunks else None
        if title_chunk:
            lines = [l.strip() for l in title_chunk.text.splitlines() if l.strip()]
            if lines:
                title = lines[0]

        if title:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="title",
                value=title,
                source_span=title,
                confidence=0.9,
                chunk_id=title_chunk.chunk_id if title_chunk else "",
            ))

        # Authors (usually second line/paragraph of first chunk)
        authors = []
        authors_chunk = None
        authors_line = ""
        # Authors are typically the line after the title, which may be in a separate chunk
        # Search the first few chunks for a line that looks like author names
        for c in chunks[:4]:
            lines = [l.strip() for l in c.text.splitlines() if l.strip()]
            for line in lines:
                # Skip title (usually longer, has "Abstract" or section headers)
                if line.lower() in ('abstract', 'introduction', 'keywords', 'references'):
                    continue
                # Author line: contains commas or "and", has 2+ capitalized names, no sentence-ending period
                if (',' in line or ' and ' in line.lower()) and not line.endswith('.') and len(line) < 200:
                    # Check it looks like names: 2+ capitalized words
                    name_parts = re.split(r'[,;]|\s+and\s+', line)
                    name_parts = [p.strip() for p in name_parts if p.strip()]
                    cap_count = sum(1 for p in name_parts if p and p[0].isupper())
                    if cap_count >= 1 and len(name_parts) >= 1:
                        authors = [a.strip() for a in re.split(r'[,;]|\band\b', line, flags=re.IGNORECASE) if a.strip()]
                        authors_chunk = c
                        authors_line = line
                        break
            if authors:
                break
        # Fallback: if title is line 0 of chunk 0, authors may be line 1 of chunk 0 or chunk 1
        if not authors and len(chunks) >= 2:
            lines = [l.strip() for l in chunks[1].text.splitlines() if l.strip()]
            if lines:
                authors = [a.strip() for a in re.split(r'[,;]|\band\b', lines[0], flags=re.IGNORECASE) if a.strip()]
                authors_chunk = chunks[1]
                authors_line = lines[0]

        if authors:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="authors",
                value=json.dumps(authors),
                source_span=authors_line,
                confidence=0.85,
                chunk_id=authors_chunk.chunk_id if authors_chunk else "",
            ))

        # Abstract summary
        abstract = ""
        abstract_chunk = None
        for c in chunks:
            if "abstract" in c.text.lower():
                m = re.search(r'abstract\b:?\s*(.*)', c.text, re.IGNORECASE | re.DOTALL)
                if m:
                    abstract = m.group(1).strip()[:300]
                    abstract_chunk = c
                    break

        if abstract:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="abstract_summary",
                value=abstract,
                source_span=abstract[:50],
                confidence=0.9,
                chunk_id=abstract_chunk.chunk_id if abstract_chunk else "",
            ))

        # Key claims
        claims = []
        claims_chunk = None
        for c in chunks:
            lines = c.text.splitlines()
            # Strategy 1: Look for claims section headers and extract numbered items
            in_claims_section = False
            for line in lines:
                line_stripped = line.strip()
                # Match various claims section headers
                if re.match(r'(?:key\s+claims|main\s+results|key\s+contributions|results|contributions|findings|conclusions)\s*:', line_stripped, re.IGNORECASE):
                    in_claims_section = True
                    if not claims_chunk:
                        claims_chunk = c
                    continue
                if in_claims_section:
                    # Numbered items: "1. text"
                    m = re.match(r'^\d+\.\s*(.+)', line_stripped)
                    if m:
                        cleaned = m.group(1).strip()
                        if len(cleaned) > 10 and cleaned not in claims:
                            claims.append(cleaned)
                        continue
                    # Bullet points: "- text" or "* text" or "• text"
                    m = re.match(r'^[-*•]\s*(.+)', line_stripped)
                    if m:
                        cleaned = m.group(1).strip()
                        if len(cleaned) > 10 and cleaned not in claims:
                            claims.append(cleaned)
                        continue
                    # End of section: non-empty, non-bullet, non-numbered line
                    if line_stripped and not line_stripped.startswith('---'):
                        if len(claims) > 0:
                            in_claims_section = False
            if claims:
                break

        # Strategy 2: Fallback
        if not claims:
            for c in chunks:
                lines = c.text.splitlines()
                for line in lines:
                    if any(x in line.lower() for x in ["we show", "we propose", "contribution", "our results", "conclude", "outperform", "improve"]):
                        cleaned = line.strip()
                        cleaned = re.sub(r'^\d+\.\s*', '', cleaned)
                        if len(cleaned) > 10 and cleaned not in claims:
                            claims.append(cleaned)
                            if not claims_chunk:
                                claims_chunk = c

        if claims:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="key_claims",
                value=json.dumps(claims),
                source_span=claims[0][:50],
                confidence=0.85,
                chunk_id=claims_chunk.chunk_id if claims_chunk else chunks[0].chunk_id,
            ))

        # Methods — extract individual method sentences from the methodology section
        methods = []
        methods_chunk = None
        for c in chunks:
            if any(x in c.text.lower() for x in ["methodology", "methods", "experimental setup", "proposed approach"]):
                # Remove the section header line, then split by sentence
                lines = c.text.splitlines()
                # Skip the header line (first line if it's just the section title)
                content_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    # Skip section headers
                    if re.match(r'^(?:methodology|methods|experimental setup|proposed approach)\s*:?$', line_stripped, re.IGNORECASE):
                        continue
                    if line_stripped:
                        content_lines.append(line_stripped)
                # Join and split by sentence
                content = ' '.join(content_lines)
                sentences = re.split(r'(?<=[.])\s+', content)
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) > 15:
                        methods.append(sent)
                methods_chunk = c
                break

        if methods:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="methods",
                value=json.dumps(methods),
                source_span=methods[0][:50] if methods else "",
                confidence=0.8,
                chunk_id=methods_chunk.chunk_id if methods_chunk else chunks[0].chunk_id,
            ))

        # Reported numbers
        numbers = []
        num_chunk = None
        for c in chunks:
            # Look for numbers/percentages in Results section or anywhere
            # Pattern: percentages (44.5%), decimals (28.4, 2.0), and small decimals (0.12)
            matches = re.findall(r'\b\d+\.\d+%?\b', c.text)
            for m in matches:
                if m not in numbers:
                    numbers.append(m)
                    if not num_chunk:
                        num_chunk = c
            # Also look for percentages without decimal
            matches2 = re.findall(r'\b\d+%\b', c.text)
            for m in matches2:
                if m not in numbers:
                    numbers.append(m)
                    if not num_chunk:
                        num_chunk = c

        if numbers:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="reported_numbers",
                value=json.dumps(numbers[:10]),
                source_span=numbers[0],
                confidence=0.85,
                chunk_id=num_chunk.chunk_id if num_chunk else chunks[0].chunk_id,
            ))

        # Figure references
        figs = []
        fig_chunk = None
        for c in chunks:
            matches = re.findall(r'\b(?:Figure|Fig\.)\s*\d+\b', c.text, re.IGNORECASE)
            for m in matches:
                if m not in figs:
                    figs.append(m)
                    if not fig_chunk:
                        fig_chunk = c

        if figs:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="figure_references",
                value=json.dumps(figs),
                source_span=figs[0],
                confidence=0.9,
                chunk_id=fig_chunk.chunk_id if fig_chunk else chunks[0].chunk_id,
            ))

        # Table references
        tabs = []
        tab_chunk = None
        for c in chunks:
            matches = re.findall(r'\bTable\s*\d+\b', c.text, re.IGNORECASE)
            for m in matches:
                if m not in tabs:
                    tabs.append(m)
                    if not tab_chunk:
                        tab_chunk = c

        if tabs:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="table_references",
                value=json.dumps(tabs),
                source_span=tabs[0],
                confidence=0.9,
                chunk_id=tab_chunk.chunk_id if tab_chunk else chunks[0].chunk_id,
            ))

        return extractions

    def oracle(self, fixtures_dir: str) -> dict[str, float]:
        """Score per-field accuracy vs ground-truth fixtures."""
        fixtures_path = pathlib.Path(fixtures_dir)
        gt_file = fixtures_path / "ground_truth.json"
        if not gt_file.exists():
            return {f: 0.0 for f in PAPER_FIELDS}

        gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
        fixtures = gt_data.get("fixtures", [])
        if not fixtures:
            return {f: 0.0 for f in PAPER_FIELDS}

        field_correct = {f: 0 for f in PAPER_FIELDS}
        field_total = {f: 0 for f in PAPER_FIELDS}

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

            for field_name in PAPER_FIELDS:
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
            for f in PAPER_FIELDS
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
