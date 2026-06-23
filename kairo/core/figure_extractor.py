"""
Kairo Figure Extractor — Paper Pack Figure Detection via PyMuPDF.

Uses PyMuPDF's page.get_images() and page.get_image_info() for figure
detection. Adds caption association and classification heuristics (no ML).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Figure:
    """A detected figure in a document page."""
    page: int
    bbox: list[float]  # [x0, y0, x1, y1] in PDF points
    caption: str = ""
    classification: str = "unknown"  # photo, chart, table_image, diagram
    image_bytes: bytes | None = None
    confidence: float = 0.7

    def to_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "bbox": self.bbox,
            "caption": self.caption,
            "classification": self.classification,
            "confidence": self.confidence,
            "has_image": self.image_bytes is not None,
        }


def extract_figures_from_pdf(pdf_path: str) -> list[Figure]:
    """Extract figures from a PDF document using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of Figure objects with bbox, caption, and classification.
    """
    try:
        import fitz
    except ImportError:
        logger.warning("PyMuPDF not available, cannot extract figures")
        return []

    figures: list[Figure] = []

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Failed to open PDF {pdf_path}: {e}")
        return []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_number = page_num + 1  # 1-indexed

        # Get image info (bbox + metadata)
        image_list = page.get_image_info(xrefs=True)
        for img_info in image_list:
            bbox = img_info.get("bbox", [0, 0, 0, 0])
            if len(bbox) == 4 and (bbox[2] - bbox[0]) > 20 and (bbox[3] - bbox[1]) > 20:
                # Skip tiny images (likely icons/bullets)
                figure = Figure(
                    page=page_number,
                    bbox=[bbox[0], bbox[1], bbox[2], bbox[3]],
                )

                # Extract image bytes
                xref = img_info.get("xref", 0)
                if xref:
                    try:
                        figure.image_bytes = doc.extract_image(xref)["image"]
                    except Exception:
                        pass

                # Classify figure
                figure.classification = _classify_figure(figure, page)

                # Find caption
                figure.caption = _find_caption(page, bbox, page_number)

                figures.append(figure)

    doc.close()
    return figures


def _find_caption(page, figure_bbox: list, page_num: int) -> str:
    """Find caption text near a figure (within 50px below/above).

    Looks for text blocks starting with "Figure N" or "Fig. N".
    """
    try:
        import fitz
    except ImportError:
        return ""

    blocks = page.get_text("blocks")
    fig_y_center = (figure_bbox[1] + figure_bbox[3]) / 2

    for block in blocks:
        if len(block) < 5:
            continue
        x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
        block_y_center = (y0 + y1) / 2

        # Check if block is within 50px of figure (above or below)
        distance = abs(block_y_center - fig_y_center)
        if distance > 50:
            continue

        # Check if text starts with "Figure N" or "Fig. N"
        text_stripped = text.strip()
        if re.match(r'(?:Figure|Fig\.?)\s*\d+', text_stripped, re.IGNORECASE):
            return text_stripped

    return ""


def _classify_figure(figure: Figure, page) -> str:
    """Classify a figure using heuristics (no ML).

    - high color variance -> photo
    - axis-like lines -> chart
    - grid -> table_image
    - vector -> diagram
    """
    if figure.image_bytes is None:
        return "diagram"  # no image bytes, likely vector

    try:
        from PIL import Image
        import io
        import numpy as np

        img = Image.open(io.BytesIO(figure.image_bytes))
        img_array = np.array(img)

        # Check color variance
        if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
            # Color image — check variance
            color_std = np.std(img_array[:, :, :3], axis=(0, 1)).mean()
            if color_std > 50:
                return "photo"

        # Check for grid patterns (table_image)
        if len(img_array.shape) == 2:
            # Grayscale — check for regular line patterns
            row_vars = np.var(img_array, axis=1)
            col_vars = np.var(img_array, axis=0)
            if np.mean(row_vars) > 100 and np.mean(col_vars) > 100:
                return "table_image"

        # Check for axis-like lines (chart)
        if len(img_array.shape) >= 2:
            # Look for long horizontal/vertical lines
            edges = np.diff(img_array.mean(axis=0) if len(img_array.shape) == 2 else img_array.mean(axis=2))
            if np.sum(np.abs(edges) > 50) > 5:
                return "chart"

        return "diagram"

    except Exception:
        return "unknown"


def extract_figures_from_text(text: str) -> list[Figure]:
    """Extract figure references from text (for text-only documents).

    Finds "Figure N" and "Table N" references in text.
    """
    figures: list[Figure] = []
    # Find "Figure N: caption" or "Fig. N: caption" patterns
    for match in re.finditer(r'(?:Figure|Fig\.?)\s*(\d+)\s*[:.]\s*(.+?)(?:\n|$)', text, re.IGNORECASE):
        fig_num = match.group(1)
        caption = match.group(2).strip()
        figures.append(Figure(
            page=1,  # text docs are single-page
            bbox=[0, 0, 0, 0],  # no bbox for text
            caption=f"Figure {fig_num}: {caption}",
            classification="unknown",
            confidence=0.6,
        ))
    # Find "Table N" references
    for match in re.finditer(r'Table\s*(\d+)\s*[:.]\s*(.+?)(?:\n|$)', text, re.IGNORECASE):
        tab_num = match.group(1)
        caption = match.group(2).strip()
        figures.append(Figure(
            page=1,
            bbox=[0, 0, 0, 0],
            caption=f"Table {tab_num}: {caption}",
            classification="table_image",
            confidence=0.6,
        ))
    return figures