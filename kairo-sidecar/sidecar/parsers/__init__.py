# kairo-sidecar/sidecar/parsers/__init__.py
"""
Kairo Sidecar – Parsers Package
================================
Exposes structured document parsing functions for DOCX, PDF, PPTX, and XLSX
documents, using Docling (primary) and MinerU / PyMuPDF (PDF fallback).

Quick reference
---------------
parse_docx_structured(path)   → {paragraphs, tables, metadata}  [docling_parser]
parse_pdf_structured(path)    → {paragraphs, tables, metadata}  [mineru_parser]
"""

from .docling_parser import parse_docx_structured, DoclingParser  # noqa: F401
from .mineru_parser import parse_pdf_structured, parse_with_mineru, MineruParser  # noqa: F401

__all__ = [
    # DOCX / general structured parsing (Docling primary)
    "DoclingParser",
    "parse_docx_structured",
    # PDF parsing (MinerU primary, PyMuPDF fallback)
    "MineruParser",
    "parse_pdf_structured",
    "parse_with_mineru",
]
