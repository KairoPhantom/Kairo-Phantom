"""
Tests for hardware_check.py — P1.1 Hardware matrix + graceful degradation.

These tests simulate low-memory / no-GPU environments using override parameters
(NOT mocks on the production path — the detection logic is real, we just feed
it simulated hardware profiles) and assert that:
1. The fallback path activates when no GPU is detected.
2. The "visual retrieval disabled" message is logged.
3. Insufficient RAM is detected before model load and a precise message is printed.
4. The pre-flight check prevents OOM crashes by blocking model load.
5. The recommended tier enables visual retrieval.
"""
import logging
import sys
import os

import pytest

# Ensure the scripts directory is importable
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from hardware_check import (
    detect_hardware,
    check_model_loadable,
    safe_model_load,
    format_report,
    HardwareProfile,
    TIER_MINIMUM,
    TIER_RECOMMENDED,
    TIER_INSUFFICIENT,
    MIN_RAM_GB,
    RECOMMENDED_VRAM_GB,
    MODEL_VRAM_REQUIREMENTS_GB,
    MODEL_RAM_REQUIREMENTS_GB,
)


# ---------------------------------------------------------------------------
# No-GPU detection tests
# ---------------------------------------------------------------------------

def test_no_gpu_activates_fallback_path():
    """When no GPU is present, the CPU-only fallback path must activate."""
    profile = detect_hardware(override_gpu=False, override_ram=8.0)
    assert profile.has_gpu is False
    assert profile.tier == TIER_MINIMUM
    assert profile.visual_retrieval is False
    assert profile.grounding_mode == "text-only"


def test_no_gpu_logs_visual_retrieval_disabled():
    """When no GPU is present, the 'visual retrieval disabled' message must appear."""
    profile = detect_hardware(override_gpu=False, override_ram=8.0)
    warning_text = " ".join(profile.warnings)
    assert "visual retrieval disabled" in warning_text.lower()
    assert "cpu mode" in warning_text.lower()
    assert "text-only grounding" in warning_text.lower()


def test_no_gpu_disables_visual_retrieval_feature():
    """The features_disabled list must include visual retrieval when no GPU."""
    profile = detect_hardware(override_gpu=False, override_ram=8.0)
    disabled_text = " ".join(profile.features_disabled).lower()
    assert "visual_retrieval" in disabled_text or "visual retrieval" in disabled_text


def test_no_gpu_enables_text_grounding():
    """Text-only grounding features must still be enabled without a GPU."""
    profile = detect_hardware(override_gpu=False, override_ram=8.0)
    enabled_text = " ".join(profile.features_enabled).lower()
    assert "exact_grounding" in enabled_text
    assert "fuzzy_grounding" in enabled_text


# ---------------------------------------------------------------------------
# Insufficient RAM tests
# ---------------------------------------------------------------------------

def test_insufficient_ram_detected():
    """RAM below minimum must be detected and flagged as INSUFFICIENT tier."""
    profile = detect_hardware(override_gpu=False, override_ram=4.0)
    assert profile.tier == TIER_INSUFFICIENT
    assert profile.ram_gb < MIN_RAM_GB


def test_insufficient_ram_logs_warning():
    """Insufficient RAM must produce a precise warning message."""
    profile = detect_hardware(override_gpu=False, override_ram=4.0)
    warning_text = " ".join(profile.warnings)
    assert "INSUFFICIENT RAM" in warning_text
    assert "4.0" in warning_text
    assert str(int(MIN_RAM_GB)) in warning_text


def test_insufficient_ram_disables_llm():
    """Insufficient RAM must disable the local LLM."""
    profile = detect_hardware(override_gpu=False, override_ram=4.0)
    disabled_text = " ".join(profile.features_disabled).lower()
    assert "local_llm" in disabled_text


# ---------------------------------------------------------------------------
# Pre-flight model load guardrail tests
# ---------------------------------------------------------------------------

def test_model_load_blocked_on_insufficient_vram():
    """A 34B model on a GPU with only 8GB VRAM must be blocked, not OOM."""
    profile = detect_hardware(override_gpu=True, override_vram=8.0, override_ram=16.0)
    can_load, message = check_model_loadable("34B", profile)
    assert can_load is False
    assert "INSUFFICIENT VRAM" in message
    assert "34B" in message


def test_model_load_blocked_on_insufficient_ram_cpu():
    """A 13B model on CPU with only 8GB RAM must be blocked."""
    profile = detect_hardware(override_gpu=False, override_ram=8.0)
    can_load, message = check_model_loadable("13B", profile)
    assert can_load is False
    assert "INSUFFICIENT RAM" in message
    assert "13B" in message


def test_model_load_blocked_on_insufficient_ram_below_minimum():
    """Any model on a machine with < 8GB RAM must be blocked."""
    profile = detect_hardware(override_gpu=False, override_ram=4.0)
    can_load, message = check_model_loadable("7B", profile)
    assert can_load is False
    assert "INSUFFICIENT RAM" in message


def test_model_load_approved_when_sufficient():
    """A 7B model on a GPU with 16GB VRAM must be approved."""
    profile = detect_hardware(override_gpu=True, override_vram=16.0, override_ram=16.0)
    can_load, message = check_model_loadable("7B", profile)
    assert can_load is True
    assert "OK" in message


def test_safe_model_load_returns_blocked_not_crash():
    """safe_model_load must return a BLOCKED message, not raise an OOM exception."""
    profile = detect_hardware(override_gpu=False, override_ram=4.0)
    result = safe_model_load("7B", profile)
    assert result.startswith("BLOCKED:")
    assert "INSUFFICIENT" in result


def test_safe_model_load_returns_approved_when_ok():
    """safe_model_load must return APPROVED when hardware is sufficient."""
    profile = detect_hardware(override_gpu=True, override_vram=16.0, override_ram=16.0)
    result = safe_model_load("7B", profile)
    assert result.startswith("APPROVED:")


def test_unknown_model_size_rejected():
    """An unknown model size must be rejected with a clear message."""
    profile = detect_hardware(override_gpu=True, override_vram=16.0, override_ram=16.0)
    can_load, message = check_model_loadable("99B", profile)
    assert can_load is False
    assert "Unknown model size" in message


# ---------------------------------------------------------------------------
# Recommended tier tests
# ---------------------------------------------------------------------------

def test_recommended_tier_enables_visual_retrieval():
    """A GPU with ≥16GB VRAM and ≥16GB RAM must enable visual retrieval."""
    profile = detect_hardware(override_gpu=True, override_vram=16.0, override_ram=16.0)
    assert profile.tier == TIER_RECOMMENDED
    assert profile.visual_retrieval is True
    assert profile.grounding_mode == "visual+text"


def test_recommended_tier_no_disabled_features():
    """The recommended tier should have no disabled features."""
    profile = detect_hardware(override_gpu=True, override_vram=16.0, override_ram=16.0)
    assert len(profile.features_disabled) == 0


def test_recommended_tier_enables_all_grounding():
    """The recommended tier must enable all grounding methods."""
    profile = detect_hardware(override_gpu=True, override_vram=16.0, override_ram=16.0)
    enabled_text = " ".join(profile.features_enabled).lower()
    assert "exact_grounding" in enabled_text
    assert "fuzzy_grounding" in enabled_text
    assert "semantic_grounding" in enabled_text
    assert "visual_retrieval" in enabled_text


# ---------------------------------------------------------------------------
# Degradation cascade tests
# ---------------------------------------------------------------------------

def test_degradation_from_recommended_to_minimum():
    """Removing GPU should degrade from recommended to minimum tier."""
    profile_gpu = detect_hardware(override_gpu=True, override_vram=16.0, override_ram=16.0)
    profile_cpu = detect_hardware(override_gpu=False, override_ram=16.0)
    assert profile_gpu.tier == TIER_RECOMMENDED
    assert profile_cpu.tier == TIER_MINIMUM
    assert profile_gpu.visual_retrieval is True
    assert profile_cpu.visual_retrieval is False


def test_degradation_from_minimum_to_insufficient():
    """Reducing RAM below minimum should degrade from minimum to insufficient."""
    profile_ok = detect_hardware(override_gpu=False, override_ram=8.0)
    profile_low = detect_hardware(override_gpu=False, override_ram=4.0)
    assert profile_ok.tier == TIER_MINIMUM
    assert profile_low.tier == TIER_INSUFFICIENT


# ---------------------------------------------------------------------------
# Report formatting test
# ---------------------------------------------------------------------------

def test_format_report_contains_tier_and_features():
    """The formatted report must contain tier, features, and warnings."""
    profile = detect_hardware(override_gpu=False, override_ram=8.0)
    report = format_report(profile)
    assert "Hardware Check" in report
    assert TIER_MINIMUM in report
    assert "visual retrieval" in report.lower()
    assert "text-only" in report


def test_profile_json_serializable():
    """The hardware profile must be JSON serializable."""
    profile = detect_hardware(override_gpu=False, override_ram=8.0)
    json_str = profile.to_json()
    import json
    data = json.loads(json_str)
    assert data["tier"] == TIER_MINIMUM
    assert data["has_gpu"] is False


# ---------------------------------------------------------------------------
# Failing-capable test: break the behavior and verify the test catches it
# ---------------------------------------------------------------------------

def test_failing_capable_no_gpu_message():
    """This test FAILS if the 'visual retrieval disabled' message is removed.

    To verify this is failing-capable: remove the warning from detect_hardware()
    and this test will go RED.
    """
    profile = detect_hardware(override_gpu=False, override_ram=8.0)
    # This must be present — if someone removes the degradation message,
    # this test catches the regression.
    assert any("visual retrieval disabled" in w.lower() for w in profile.warnings), \
        "Regression: 'visual retrieval disabled' message was removed from no-GPU path"


def test_failing_capable_oom_guard():
    """This test FAILS if the pre-flight OOM guard is removed.

    To verify: remove the VRAM check from check_model_loadable() and this
    test will go RED because the model would be approved instead of blocked.
    """
    profile = detect_hardware(override_gpu=True, override_vram=2.0, override_ram=16.0)
    # 34B requires 24GB VRAM — with only 2GB, this MUST be blocked
    can_load, message = check_model_loadable("34B", profile)
    assert can_load is False, \
        "Regression: OOM guard removed — 34B model approved with only 2GB VRAM"
    assert "INSUFFICIENT VRAM" in message