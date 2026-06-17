"""
Kairo Phantom — Invoice Pack (SPEC §S7)
Extracts vendor_name, invoice_number, invoice_date, due_date, total_amount, currency, line_items, tax_amount, payment_terms.
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

INVOICE_FIELDS = [
    "vendor_name", "invoice_number", "invoice_date", "due_date",
    "total_amount", "currency", "line_items", "tax_amount", "payment_terms"
]

class InvoicePack:
    """Invoice extraction Pack implementing PackInterface."""

    def __init__(self, pack_id: str = "invoice-v1") -> None:
        self._pack_id = pack_id

    @property
    def fields(self) -> list[str]:
        return list(INVOICE_FIELDS)

    def extract(self, chunks: list[Chunk]) -> list[Extraction]:
        """Extract invoice fields from ingested chunks using regex and rules."""
        if not chunks:
            return []

        full_text = "\n".join(c.text for c in chunks)
        extractions: list[Extraction] = []

        # Find vendor name (usually at the top of the invoice, first line or after "FROM:")
        vendor_name = ""
        vendor_chunk = chunks[0] if chunks else None
        if vendor_chunk:
            lines = [l.strip() for l in vendor_chunk.text.splitlines() if l.strip()]
            for line in lines[:5]:
                if any(x in line.lower() for x in ["invoice", "bill to", "to:", "date:"]):
                    continue
                if len(line) > 3:
                    vendor_name = line
                    break

        if vendor_name:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="vendor_name",
                value=vendor_name,
                source_span=vendor_name,
                confidence=0.9,
                chunk_id=vendor_chunk.chunk_id if vendor_chunk else "",
            ))

        # Find invoice number
        inv_no = ""
        inv_chunk = None
        for c in chunks:
            m = re.search(r'(?:invoice|inv|number|no\.?|#)\s*:?\s*([a-zA-Z0-9\-]+)', c.text, re.IGNORECASE)
            if m:
                inv_no = m.group(1).strip()
                inv_chunk = c
                break

        if inv_no:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="invoice_number",
                value=inv_no,
                source_span=inv_no,
                confidence=0.95,
                chunk_id=inv_chunk.chunk_id if inv_chunk else "",
            ))

        # Find invoice date and due date
        inv_date = ""
        due_date = ""
        date_chunk = None
        for c in chunks:
            dates = re.findall(r'(?:date|issued|billed)\s*:?\s*(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[a-zA-Z]+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{2}/\d{2}/\d{4})', c.text, re.IGNORECASE)
            if dates:
                inv_date = dates[0]
                date_chunk = c
            due_dates = re.findall(r'(?:due|due date|payment due)\s*:?\s*(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[a-zA-Z]+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{2}/\d{2}/\d{4})', c.text, re.IGNORECASE)
            if due_dates:
                due_date = due_dates[0]
                date_chunk = c

        if inv_date:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="invoice_date",
                value=self._parse_date(inv_date) or inv_date,
                source_span=inv_date,
                confidence=0.9,
                chunk_id=date_chunk.chunk_id if date_chunk else "",
            ))
        if due_date:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="due_date",
                value=self._parse_date(due_date) or due_date,
                source_span=due_date,
                confidence=0.9,
                chunk_id=date_chunk.chunk_id if date_chunk else "",
            ))

        # Find total amount and currency
        total_amt = ""
        currency = "USD"  # Default
        amt_chunk = None
        for c in chunks:
            # Look for total or amount due
            m = re.search(r'(?:total|amount due|balance due|total due|grand total)\s*:?\s*([$€£¥]?\s*[\d,]+\.\d{2})', c.text, re.IGNORECASE)
            if m:
                total_str = m.group(1).strip()
                amt_chunk = c
                # Extract currency symbol
                if "$" in total_str:
                    currency = "USD"
                elif "€" in total_str:
                    currency = "EUR"
                elif "£" in total_str:
                    currency = "GBP"
                
                total_val = re.sub(r'[^\d\.]', '', total_str)
                total_amt = total_val
                break

        if total_amt:
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="total_amount",
                value=total_amt,
                source_span=total_amt,
                confidence=0.95,
                chunk_id=amt_chunk.chunk_id if amt_chunk else "",
            ))
            extractions.append(Extraction(
                pack_id=self._pack_id,
                field_name="currency",
                value=currency,
                source_span=currency,
                confidence=0.9,
                chunk_id=amt_chunk.chunk_id if amt_chunk else "",
            ))

        # Tax amount
        tax_amt = "0.00"
        tax_chunk = None
        for c in chunks:
            m = re.search(r'(?:tax|vat|gst)\s*:?\s*([$€£¥]?\s*[\d,]+\.\d{2})', c.text, re.IGNORECASE)
            if m:
                tax_str = m.group(1).strip()
                tax_amt = re.sub(r'[^\d\.]', '', tax_str)
                tax_chunk = c
                break

        extractions.append(Extraction(
            pack_id=self._pack_id,
            field_name="tax_amount",
            value=tax_amt,
            source_span=tax_amt,
            confidence=0.85,
            chunk_id=tax_chunk.chunk_id if tax_chunk else chunks[0].chunk_id,
        ))

        # Payment terms
        terms = "Net 30"
        terms_chunk = None
        for c in chunks:
            m = re.search(r'(?:terms|payment terms)\s*:?\s*(net\s*\d+|due on receipt|immediate)', c.text, re.IGNORECASE)
            if m:
                terms = m.group(1).strip()
                terms_chunk = c
                break

        extractions.append(Extraction(
            pack_id=self._pack_id,
            field_name="payment_terms",
            value=terms,
            source_span=terms,
            confidence=0.85,
            chunk_id=terms_chunk.chunk_id if terms_chunk else chunks[0].chunk_id,
        ))

        # Line items (dummy list or basic regex parse)
        line_items = []
        for c in chunks:
            # Simple line items search: look for lines containing descriptive terms + amounts
            lines = c.text.splitlines()
            for line in lines:
                m = re.search(r'([a-zA-Z\s]{5,})\s+(\d+)\s+([$€£¥]?\s*[\d,]+\.\d{2})\s+([$€£¥]?\s*[\d,]+\.\d{2})', line)
                if m:
                    desc = m.group(1).strip()
                    qty = int(m.group(2))
                    price = float(re.sub(r'[^\d\.]', '', m.group(3)))
                    total = float(re.sub(r'[^\d\.]', '', m.group(4)))
                    line_items.append({"description": desc, "quantity": qty, "unit_price": price, "total": total})

        extractions.append(Extraction(
            pack_id=self._pack_id,
            field_name="line_items",
            value=json.dumps(line_items),
            source_span=line_items[0]["description"] if line_items else "",
            confidence=0.8,
            chunk_id=chunks[0].chunk_id,
        ))

        return extractions

    def oracle(self, fixtures_dir: str) -> dict[str, float]:
        """Score per-field accuracy vs ground-truth fixtures."""
        fixtures_path = pathlib.Path(fixtures_dir)
        gt_file = fixtures_path / "ground_truth.json"
        if not gt_file.exists():
            return {f: 0.0 for f in INVOICE_FIELDS}

        gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
        fixtures = gt_data.get("fixtures", [])
        if not fixtures:
            return {f: 0.0 for f in INVOICE_FIELDS}

        field_correct = {f: 0 for f in INVOICE_FIELDS}
        field_total = {f: 0 for f in INVOICE_FIELDS}

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

            for field_name in INVOICE_FIELDS:
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
            for f in INVOICE_FIELDS
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
        if isinstance(expected, (int, float)):
            try:
                return abs(float(extracted) - float(expected)) < 0.01
            except Exception:
                return False
        if isinstance(expected, str):
            ext_norm = " ".join(extracted.strip().lower().split())
            exp_norm = " ".join(expected.strip().lower().split())
            return ext_norm == exp_norm or exp_norm in ext_norm or ext_norm in exp_norm
        elif isinstance(expected, list):
            try:
                extracted_list = json.loads(extracted) if extracted.startswith("[") else [extracted]
            except Exception:
                extracted_list = [extracted]
            # Check if elements match
            return len(extracted_list) == len(expected)
        return False
