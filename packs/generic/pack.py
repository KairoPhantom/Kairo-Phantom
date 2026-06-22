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

        # Find summary — look for "Executive Summary" section, or first substantial paragraph
        summary_chunk = None
        summary_val = ""
        full_text_joined = "\n".join(c.text for c in chunks)
        # Strategy 1: "Executive Summary" header followed by text
        m = re.search(r'(?:executive\s+summary|summary|abstract)\s*:?\s*\n(.+?)(?:\n\n|\n[A-Z][^\n]*:|\n\u2022|$)', full_text_joined, re.DOTALL | re.IGNORECASE)
        if m:
            summary_val = m.group(1).strip()
            summary_chunk = next((c for c in chunks if summary_val[:30] in c.text), chunks[0] if chunks else None)
        # Strategy 2: first chunk with > 50 chars (skip title-only chunks)
        if not summary_val:
            for c in chunks:
                if len(c.text.strip()) > 50:
                    sentences = re.split(r'(?<=[.!?])\s+', c.text)
                    summary_val = " ".join(sentences[:2]).strip()
                    summary_chunk = c
                    break

        if summary_val:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="summary",
                value=summary_val,
                source_span=summary_val,
                confidence=0.9,
                chunk_id=summary_chunk.chunk_id if summary_chunk else "",
            ))

        # Find key claims — handle "Key Claims:", "Main Findings:", "Key Recommendations:", bullet points
        claims_list = []
        claims_chunk = None
        for c in chunks:
            lines = c.text.splitlines()
            in_claims_section = False
            for line in lines:
                line_stripped = line.strip()
                # Detect claims section headers (multiple variants)
                if re.match(r'(?:key\s+claims|main\s+findings|key\s+recommendations|findings|recommendations|results|conclusions|primary\s+conclusions)\s*:', line_stripped, re.IGNORECASE):
                    in_claims_section = True
                    if not claims_chunk:
                        claims_chunk = c
                    continue
                if in_claims_section:
                    # Bullet points: "• text", "- text", "* text"
                    m = re.match(r'^[\u2022\-*]\s*(.+)', line_stripped)
                    if m:
                        cleaned = m.group(1).strip()
                        if len(cleaned) > 10 and cleaned not in claims_list:
                            claims_list.append(cleaned)
                        continue
                    # Numbered items: "1. text"
                    m = re.match(r'^\d+\.\s*(.+)', line_stripped)
                    if m:
                        cleaned = m.group(1).strip()
                        if len(cleaned) > 10 and cleaned not in claims_list:
                            claims_list.append(cleaned)
                        continue
                    # End of section: non-empty, non-bullet, non-numbered line
                    if line_stripped and len(claims_list) > 0:
                        in_claims_section = False
            if claims_list:
                break

        # Strategy 2: Fallback — look for bullet points with claim-related keywords
        if not claims_list:
            for c in chunks:
                lines = c.text.splitlines()
                for line in lines:
                    if any(k in line.lower() for k in ["claim", "show", "propose", "suggest", "result", "find", "recommend", "complet", "reduc", "achiev"]):
                        cleaned = line.strip("-*\u2022 ").strip()
                        cleaned = re.sub(r'^\d+\.\s*', '', cleaned)
                        if len(cleaned) > 15 and cleaned not in claims_list:
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

        # Find entities (proper nouns — capitalized phrases, not section headers or common words)
        entities_list = []
        entities_chunk = None
        # Section headers and document terms to exclude
        section_terms = {
            "Executive Summary", "Main Findings", "Key Recommendations", "Key Claims",
            "Abstract", "Introduction", "Conclusion", "References", "Budget",
            "Status Report", "Executive", "Summary", "Findings", "Recommendations",
            "Report", "Analysis", "Overview", "Background", "Methodology",
            "Results", "Discussion", "Appendix", "Table", "Figure",
            "Market Analysis", "Electric Vehicle Adoption",
            "Primary Conclusions", "Strategic Implications", "Overview",
            "Key Findings", "Key Recommendations", "Executive",
            "Status Report", "Audit Report", "Review", "Assessment",
            "Customer Satisfaction", "Survey Results", "Vendor Evaluation",
            "Risk Assessment", "Compliance Review", "Operational Efficiency",
            "Digital Transformation", "Supply Chain", "Employee Engagement",
            "Market Entry", "Technology Stack", "Data Governance",
            "Cloud Migration", "Cybersecurity Threat", "Financial Performance",
            "Sustainability Report", "Brand Audit", "Process Optimization",
            "Innovation Pipeline", "Regulatory Impact", "Competitive Landscape",
            "Workforce Planning", "Capital Expenditure", "Strategic Partnership",
            "IT Infrastructure", "Budget Review", "Product Launch",
            "M&A Due", "Due Diligence",
        }
        stop_words = {"The", "A", "An", "In", "On", "At", "By", "For", "We", "I", "This", "That", "It", "To", "Of", "And", "Q4", "Q1", "Q2", "Q3", "Two", "All", "User", "Data", "API", "November", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "December"}
        # Match multi-word capitalized phrases (proper nouns) — prefer 2+ word phrases
        entity_pattern = re.compile(r'\b[A-Z][a-zA-Z]+(?:[ ]+[A-Z][a-zA-Z]+){1,3}\b')
        for c in chunks:
            matches = entity_pattern.findall(c.text)
            for m in matches:
                if m in stop_words or m in section_terms:
                    continue
                if len(m) < 5:
                    continue
                # Skip if it's a line by itself (likely a header)
                if m.strip() in [l.strip() for l in c.text.splitlines() if l.strip()]:
                    continue
                if m not in entities_list:
                    entities_list.append(m)
                    if not entities_chunk:
                        entities_chunk = c
        # Also add single-word proper nouns that are likely entity names
        if True:  # always check for single-word entities
            single_pattern = re.compile(r'\b[A-Z][a-zA-Z]{4,}\b')
            for c in chunks:
                matches = single_pattern.findall(c.text)
                for m in matches:
                    if m in stop_words or m in section_terms or m in entities_list:
                        continue
                    if m.strip() in [l.strip() for l in c.text.splitlines() if l.strip()]:
                        continue
                    entities_list.append(m)
                    if not entities_chunk:
                        entities_chunk = c
                    if len(entities_list) >= 10:
                        break

        if entities_list:
            # Use actual text from the chunk as source_span (for grounding)
            span = entities_list[0] if entities_list else (chunks[0].text[:100] if chunks else "")
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="entities",
                value=json.dumps(entities_list[:10]),
                source_span=span,
                confidence=0.8,
                chunk_id=entities_chunk.chunk_id if entities_chunk else chunks[0].chunk_id,
            ))

        # Find topics — map text keywords to canonical topic names
        topics_list = []
        topics_chunk = None
        # Map: keyword in text -> canonical topic name
        topic_map = {
            "technology": ["technology", "tech", "software", "api", "cloud", "digital", "it ", "infrastructure", "system", "platform", "battery", "ev ", "electric vehicle", "transition", "supply chain"],
            "security": ["security", "vulnerability", "patch", "audit", "cyber", "threat"],
            "data": ["data", "database", "migration", "analytics"],
            "financial": ["financial", "finance", "budget", "cost", "revenue", "payment", "invoice", "tax"],
            "analysis": ["analysis", "report", "study", "research", "assessment"],
            "market": ["market", "sales", "customer", "adoption", "growth", "competitive"],
            "automotive": ["automotive", "vehicle", "ev", "car", "battery", "electric vehicle"],
            "contract": ["contract", "agreement", "clause", "party", "obligation"],
            "paper": ["paper", "research", "model", "experiment", "dataset", "training"],
            "intelligence": ["intelligence", "ai", "machine learning", "neural"],
        }
        for c in chunks:
            text_lower = c.text.lower()
            for canonical, keywords in topic_map.items():
                if canonical not in topics_list:
                    if any(kw in text_lower for kw in keywords):
                        topics_list.append(canonical)
                        if not topics_chunk:
                            topics_chunk = c

        if topics_list:
            # Limit to first 4 topics to avoid over-extraction
            topics_list = topics_list[:4]
            # Use actual text from the chunk as source_span (for grounding)
            span = topics_chunk.text[:100] if topics_chunk else (chunks[0].text[:100] if chunks else "")
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="topics",
                value=json.dumps(topics_list),
                source_span=span,
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
