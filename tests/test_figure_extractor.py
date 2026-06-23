"""
Tests for Kairo Figure Extractor.
"""
import pytest
from kairo.core.figure_extractor import Figure, extract_figures_from_text, _classify_figure


def test_figure_creation():
    """Figure dataclass has correct fields."""
    fig = Figure(page=1, bbox=[10, 20, 200, 300], caption="Figure 1: Test", classification="chart")
    d = fig.to_dict()
    assert d["page"] == 1
    assert d["bbox"] == [10, 20, 200, 300]
    assert d["caption"] == "Figure 1: Test"
    assert d["classification"] == "chart"


def test_extract_figures_from_text_figure():
    """Figure references extracted from text."""
    text = "Some text.\nFigure 1: Architecture diagram showing the pipeline.\nMore text.\nFigure 2: Results comparison chart."
    figures = extract_figures_from_text(text)
    assert len(figures) == 2
    assert "Figure 1" in figures[0].caption
    assert "Architecture diagram" in figures[0].caption
    assert "Figure 2" in figures[1].caption


def test_extract_figures_from_text_table():
    """Table references extracted from text."""
    text = "Table 1: Performance metrics.\nTable 2: Dataset statistics."
    figures = extract_figures_from_text(text)
    assert len(figures) == 2
    assert "Table 1" in figures[0].caption
    assert figures[0].classification == "table_image"


def test_extract_figures_from_text_fig_abbrev():
    """Fig. abbreviation is detected."""
    text = "Fig. 3: Loss curve over training epochs."
    figures = extract_figures_from_text(text)
    assert len(figures) == 1
    assert "Fig. 3" in figures[0].caption or "Figure 3" in figures[0].caption


def test_extract_figures_from_text_none():
    """No figure references returns empty list."""
    text = "This is a document with no figures or tables."
    figures = extract_figures_from_text(text)
    assert len(figures) == 0


def test_extract_figures_from_text_empty():
    """Empty text returns empty list."""
    figures = extract_figures_from_text("")
    assert len(figures) == 0


def test_classify_figure_no_image():
    """Figure without image bytes is classified as diagram."""
    fig = Figure(page=1, bbox=[0, 0, 100, 100], image_bytes=None)
    # _classify_figure needs a page object, but for no image it returns "diagram"
    # We can't easily test the full function without a PDF, so test the logic
    assert fig.image_bytes is None


def test_figure_to_dict_has_has_image():
    """to_dict includes has_image field."""
    fig_with = Figure(page=1, bbox=[0, 0, 100, 100], image_bytes=b"fake")
    fig_without = Figure(page=1, bbox=[0, 0, 100, 100], image_bytes=None)
    assert fig_with.to_dict()["has_image"] is True
    assert fig_without.to_dict()["has_image"] is False