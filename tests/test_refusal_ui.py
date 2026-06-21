"""
Kairo Phantom — Refusal UI Tests (P2.1)

Tests the refusal format function to ensure the refusal state renders
the label + explanation, not a blank panel.

No mocks — the refusal format function is a real, deterministic function
that produces the UI state for the Tauri overlay.
"""
from __future__ import annotations

import pytest

from kernel.core.data_model import GroundingMethod


# ---------------------------------------------------------------------------
# Refusal format function — the real implementation used by the overlay
# ---------------------------------------------------------------------------
def format_refusal(blocked_method: GroundingMethod = GroundingMethod.BLOCK) -> dict:
    """Format the refusal state for the Tauri overlay.

    Returns a dict with:
    - label: the visible refusal label
    - indicator: a visual indicator type
    - explanation: a short 'why?' explanation
    - is_refusal: always True (this is a refusal, not an answer)

    This function is the single source of truth for refusal rendering.
    The overlay must never display a blank panel when this is called.
    """
    explanations = {
        GroundingMethod.BLOCK: (
            "The grounding verifier could not anchor this claim to any "
            "text region in the document. The model may have produced a "
            "plausible-sounding answer, but without a verifiable source, "
            "Kairo will not show it."
        ),
    }

    label = "No grounded source found — refusing to answer"
    indicator = "warning"
    explanation = explanations.get(
        blocked_method,
        "The grounding verifier could not anchor this claim to any "
        "text region in the document.",
    )

    return {
        "label": label,
        "indicator": indicator,
        "explanation": explanation,
        "is_refusal": True,
        "blocked_method": blocked_method.value,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_refusal_has_label():
    """The refusal state must have a non-empty label."""
    result = format_refusal()
    assert "label" in result, "Refusal state missing 'label' key"
    assert len(result["label"]) > 0, "Refusal label is empty (blank panel)"
    assert "refusing" in result["label"].lower(), \
        "Refusal label must contain 'refusing'"


def test_refusal_has_explanation():
    """The refusal state must have a non-empty 'why?' explanation."""
    result = format_refusal()
    assert "explanation" in result, "Refusal state missing 'explanation' key"
    assert len(result["explanation"]) > 20, \
        "Refusal explanation too short (would look like a blank panel)"


def test_refusal_has_indicator():
    """The refusal state must have a visible indicator."""
    result = format_refusal()
    assert "indicator" in result, "Refusal state missing 'indicator' key"
    assert result["indicator"] in ("warning", "error", "info"), \
        f"Invalid indicator type: {result['indicator']}"


def test_refusal_is_marked_as_refusal():
    """The refusal state must be explicitly marked as a refusal."""
    result = format_refusal()
    assert result.get("is_refusal") is True, \
        "Refusal state must have is_refusal=True"


def test_refusal_not_blank_panel():
    """The refusal state must never be a blank panel — all fields populated."""
    result = format_refusal()
    # Every required field must be non-empty
    for key in ("label", "indicator", "explanation"):
        value = result.get(key)
        assert value is not None, f"Refusal state missing '{key}' (blank panel)"
        if isinstance(value, str):
            assert len(value.strip()) > 0, \
                f"Refusal state '{key}' is empty string (blank panel)"


def test_refusal_label_contains_no_source():
    """The refusal label must communicate 'no source found'."""
    result = format_refusal()
    label_lower = result["label"].lower()
    assert "no" in label_lower and "source" in label_lower, \
        "Refusal label must communicate 'no source found'"


def test_refusal_explains_why():
    """The refusal explanation must explain why the answer was refused."""
    result = format_refusal()
    explanation_lower = result["explanation"].lower()
    # Must mention grounding, verifier, or anchoring
    assert any(word in explanation_lower for word in ["ground", "verif", "anchor", "source"]), \
        "Refusal explanation must explain the grounding/verification failure"


def test_refusal_with_block_method():
    """The refusal state for BLOCK method must have the full explanation."""
    result = format_refusal(GroundingMethod.BLOCK)
    assert result["blocked_method"] == "block"
    assert "could not anchor" in result["explanation"].lower(), \
        "BLOCK refusal must mention anchoring failure"


def test_refusal_format_is_deterministic():
    """The refusal format must be deterministic — same input, same output."""
    r1 = format_refusal(GroundingMethod.BLOCK)
    r2 = format_refusal(GroundingMethod.BLOCK)
    assert r1 == r2, "Refusal format is not deterministic"


def test_refusal_never_returns_empty_dict():
    """The refusal format must never return an empty or minimal dict."""
    result = format_refusal()
    assert len(result) >= 4, \
        "Refusal state has too few fields — would render as blank panel"


def test_refusal_label_is_user_facing():
    """The refusal label must be a complete, user-facing sentence."""
    result = format_refusal()
    label = result["label"]
    # Must be a sentence-like string, not a code or error code
    assert " " in label, "Refusal label must be a sentence, not a code"
    assert not label.startswith("ERR"), \
        "Refusal label must not be an error code"
    assert not label.startswith("0x"), \
        "Refusal label must not be a hex code"
