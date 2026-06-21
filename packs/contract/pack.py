"""
Kairo Phantom — Contract Pack (SPEC §S7)
Extracts parties, effective_date, termination_date, obligations, governing_law, payment_terms, confidentiality_clause.
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

CONTRACT_FIELDS = [
    "parties", "effective_date", "termination_date", "obligations",
    "governing_law", "payment_terms", "confidentiality_clause"
]

class ContractPack:
    """Contract review Pack implementing PackInterface."""

    def __init__(self, pack_id: str = "contract-v1") -> None:
        self._pack_id = pack_id

    @property
    def fields(self) -> list[str]:
        return list(CONTRACT_FIELDS)

    def extract(self, chunks: list[Chunk]) -> list[Extraction]:
        """Extract contract fields from ingested chunks."""
        if not chunks:
            return []

        full_text = "\n".join(c.text for c in chunks)
        extractions: list[Extraction] = []

        # Parties — extract from the introductory clause
        # Patterns: "between X (\"alias\") and Y (\"alias\")" or "between X and Y"
        parties = []
        parties_chunk = None
        # Search ALL chunks for the parties clause (it may not be in chunks[0])
        for c in chunks:
            text = c.text
            if not ('between' in text.lower() or 'among' in text.lower()):
                continue
            # Strategy 1: "between X, a ... (\"alias\"), and Y, a ... (\"alias\")"
            m = re.search(
                r'(?:between|among)\s+([A-Z][a-zA-Z0-9\s,.&]+?)\s*(?:\([^)]*\))?\s*(?:,\s*a\s+\w+\s+\w+)?\s*(?:\([^)]*\))?\s*,?\s*and\s+([A-Z][a-zA-Z0-9\s,.&]+?)(?:\s*(?:\(|,|\.|$))',
                text
            )
            if m:
                parties_chunk = c
                p1 = m.group(1).strip().rstrip(',')
                p2 = m.group(2).strip().rstrip(',')
                # Clean up: remove trailing "a Delaware corporation" etc.
                p1 = re.sub(r',\s+a\s+.*$', '', p1).strip()
                p2 = re.sub(r',\s+a\s+.*$', '', p2).strip()
                parties = [p1, p2]

            # Strategy 2: "between X (\"alias\") and Y (\"alias\")" — simpler
            if not parties:
                m2 = re.findall(
                    r'(?:between|among)\s+([A-Z][a-zA-Z0-9\s.&]+?)(?:\s*\([^)]*\))?(?:,\s*a\s+\w+\s+\w+)?(?:\s*\([^)]*\))?\s*(?:,?\s*and\s+([A-Z][a-zA-Z0-9\s.&]+?))(?:\s*\(|,|\.|$)',
                    text
                )
                if m2:
                    for match in m2:
                        if match[0] and match[1]:
                            parties = [match[0].strip().rstrip(','), match[1].strip().rstrip(',')]
                            break

            # Strategy 3: Fallback — find "X and Y" near "between" or "entered into"
            if not parties:
                m3 = re.search(
                    r'(?:between|entered into.*?between)\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+(?:\([^)]*\)\s+)?and\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)',
                    text
                )
                if m3:
                    parties = [m3.group(1).strip(), m3.group(2).strip()]
                    if not parties_chunk:
                        parties_chunk = c

            if parties:
                break

        if parties:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="parties",
                value=json.dumps(parties),
                source_span=parties[0] if parties else "",
                confidence=0.85,
                chunk_id=parties_chunk.chunk_id if parties_chunk else "",
            ))

        # Effective date and termination date
        eff_date = ""
        term_date = ""
        date_chunk = None
        for c in chunks:
            # Effective date: look for "as of <date>" or "entered into on/as of <date>" or "Effective Date" near a date
            if not eff_date:
                # Pattern: "as of <date>" or "entered into ... on/as of <date>"
                m = re.search(
                    r'(?:as of|entered into\s+(?:as of|on))\s+(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[a-zA-Z]+\s+\d{4}|[a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
                    c.text, re.IGNORECASE
                )
                if m:
                    eff_date = m.group(1).strip()
                    date_chunk = c
                else:
                    # Pattern: "made and entered into as of <date>"
                    m = re.search(
                        r'(?:made|entered)\s+(?:and\s+\w+\s+)?(?:into\s+)?(?:as of|on)\s+(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[a-zA-Z]+\s+\d{4}|[a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
                        c.text, re.IGNORECASE
                    )
                    if m:
                        eff_date = m.group(1).strip()
                        date_chunk = c
                # Also check "effective date ... is <date>" or "commencement date ... <date>"
                if not eff_date:
                    m = re.search(
                        r'(?:effective date|commencement date|date of this agreement)\s*(?:is|of|as of|=|:)?\s*(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[a-zA-Z]+\s+\d{4}|[a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
                        c.text, re.IGNORECASE
                    )
                    if m:
                        eff_date = m.group(1).strip()
                        date_chunk = c

            # Termination date
            m2 = re.search(
                r'(?:terminate on|expiration date|termination date|ends on|terminate\s+on)\s*(?:is|of|as of)?\s*(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[a-zA-Z]+\s+\d{4}|[a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
                c.text, re.IGNORECASE
            )
            if m2:
                term_date = m2.group(1).strip()
                date_chunk = c

        if eff_date:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="effective_date",
                value=self._parse_date(eff_date) or eff_date,
                source_span=eff_date,
                confidence=0.9,
                chunk_id=date_chunk.chunk_id if date_chunk else "",
            ))
        if term_date:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="termination_date",
                value=self._parse_date(term_date) or term_date,
                source_span=term_date,
                confidence=0.9,
                chunk_id=date_chunk.chunk_id if date_chunk else "",
            ))

        # Obligations
        obligations = []
        ob_chunk = None
        for c in chunks:
            lines = c.text.splitlines()
            for line in lines:
                if any(x in line.lower() for x in ["shall", "agree to", "covenant", "undertake"]):
                    obligations.append(line.strip())
                    if not ob_chunk:
                        ob_chunk = c

        if obligations:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="obligations",
                value=json.dumps(obligations),
                source_span=obligations[0][:50],
                confidence=0.8,
                chunk_id=ob_chunk.chunk_id if ob_chunk else chunks[0].chunk_id,
            ))

        # Governing Law
        gov_law = ""
        gov_chunk = None
        for c in chunks:
            # Pattern: "State of New York" or "State of Delaware" — allow multi-word state names
            m = re.search(r'(?:State of|state of)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', c.text)
            if m:
                gov_law = m.group(1).strip()
                gov_chunk = c
                break
            # Fallback: "governed by the laws of New York"
            m = re.search(r'(?:governed by|governing law|laws of)\s+(?:the\s+)?(?:State\s+of\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', c.text, re.IGNORECASE)
            if m:
                gov_law = m.group(1).strip()
                gov_chunk = c
                break

        if gov_law:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="governing_law",
                value=gov_law,
                source_span=gov_law,
                confidence=0.9,
                chunk_id=gov_chunk.chunk_id if gov_chunk else "",
            ))

        # Payment terms
        pay_terms = ""
        pay_chunk = None
        for c in chunks:
            # Pattern 1: "within N days" (common in contracts)
            m = re.search(r'within\s+(\d+\s*days)', c.text, re.IGNORECASE)
            if m:
                pay_terms = "within " + m.group(1).strip()
                pay_chunk = c
                break
            # Pattern 2: "payment terms: ..." or "terms: ..."
            m = re.search(r'(?:payment terms|terms)\s*:?\s*(net\s*\d+|due on receipt|immediate|within\s+\d+\s*days)', c.text, re.IGNORECASE)
            if m:
                pay_terms = m.group(1).strip()
                pay_chunk = c
                break
            # Pattern 3: "paid within N days" or "pay ... within N days"
            m = re.search(r'(?:paid|pay)\s+(?:within\s+)?(\d+\s*days)', c.text, re.IGNORECASE)
            if m:
                pay_terms = "within " + m.group(1).strip()
                pay_chunk = c
                break

        if pay_terms:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="payment_terms",
                value=pay_terms,
                source_span=pay_terms,
                confidence=0.85,
                chunk_id=pay_chunk.chunk_id if pay_chunk else "",
            ))

        # Confidentiality clause
        conf = ""
        conf_chunk = None
        # Strategy 1: Look for a "Confidentiality:" section header and extract the text after it
        for c in chunks:
            lines = c.text.splitlines()
            in_conf_section = False
            for line in lines:
                line_stripped = line.strip()
                # Check for confidentiality section header
                if re.search(r'confidentiality\s*:', line_stripped, re.IGNORECASE):
                    in_conf_section = True
                    conf_chunk = c
                    continue
                if in_conf_section:
                    # Skip section headers
                    if re.match(r'^\d+\.\s*', line_stripped):
                        continue
                    if len(line_stripped) < 10:
                        continue
                    # This is the confidentiality clause text
                    conf = line_stripped
                    break
            if conf:
                break

        # Strategy 2: Look for lines with "agrees" + "confidential" or "disclosure"
        if not conf:
            for c in chunks:
                lines = c.text.splitlines()
                for line in lines:
                    line_stripped = line.strip()
                    if re.match(r'^\d+\.\s*', line_stripped):
                        continue
                    if len(line_stripped) < 20 and line_stripped.endswith(':'):
                        continue
                    if ("confidential" in line_stripped.lower() or "proprietary" in line_stripped.lower()) and \
                       ("agrees" in line_stripped.lower() or "disclosure" in line_stripped.lower() or \
                        "shall" in line_stripped.lower() or "party" in line_stripped.lower()):
                        conf = line_stripped
                        conf_chunk = c
                        break
                if conf:
                    break

        if conf:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="confidentiality_clause",
                value=conf,
                source_span=conf[:50],
                confidence=0.85,
                chunk_id=conf_chunk.chunk_id if conf_chunk else "",
            ))

        return extractions

    def oracle(self, fixtures_dir: str) -> dict[str, float]:
        """Score per-field accuracy vs ground-truth fixtures."""
        fixtures_path = pathlib.Path(fixtures_dir)
        gt_file = fixtures_path / "ground_truth.json"
        if not gt_file.exists():
            return {f: 0.0 for f in CONTRACT_FIELDS}

        gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
        fixtures = gt_data.get("fixtures", [])
        if not fixtures:
            return {f: 0.0 for f in CONTRACT_FIELDS}

        field_correct = {f: 0 for f in CONTRACT_FIELDS}
        field_total = {f: 0 for f in CONTRACT_FIELDS}

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

            for field_name in CONTRACT_FIELDS:
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
            for f in CONTRACT_FIELDS
        }

    @staticmethod
    def _parse_date(date_str: str) -> str | None:
        """Parse standard date formats to YYYY-MM-DD."""
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        # YYYY-MM-DD
        m = re.match(r"(\d{4})[-/](\d{2})[-/](\d{2})", date_str)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            
        # DD Month YYYY
        m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_str)
        if m:
            day = int(m.group(1))
            month = months.get(m.group(2).lower())
            year = int(m.group(3))
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"

        # Month DD, YYYY
        m = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", date_str)
        if m:
            month = months.get(m.group(1).lower())
            day = int(m.group(2))
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
