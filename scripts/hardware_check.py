#!/usr/bin/env python3
"""
Kairo Phantom — Hardware Check & Graceful Degradation (P1.1)

Detects available hardware (GPU presence, VRAM, RAM) and reports which tier
the user is in and what features are enabled/disabled.

When no GPU is present, it reports:
  'visual retrieval disabled — CPU mode, text-only grounding'

Hard guardrails: detects insufficient VRAM/RAM before loading a model and
prints a precise message instead of OOM-crashing.

No mocks on the production path. The detection logic probes real system
resources via stdlib (psutil when available, /proc fallback on Linux).
"""
from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------
TIER_MINIMUM = "minimum"
TIER_RECOMMENDED = "recommended"
TIER_INSUFFICIENT = "insufficient"

MIN_RAM_GB = 8.0
RECOMMENDED_VRAM_GB = 16.0
RECOMMENDED_RAM_GB = 16.0

# Model VRAM requirements (approximate, Q4_K_M quantization)
MODEL_VRAM_REQUIREMENTS_GB = {
    "7B": 6.0,
    "13B": 10.0,
    "34B": 24.0,
}

# Model RAM requirements (CPU-only fallback, approximate)
MODEL_RAM_REQUIREMENTS_GB = {
    "7B": 8.0,
    "13B": 14.0,
    "34B": 36.0,
}


@dataclass
class HardwareProfile:
    """Detected hardware profile."""
    has_gpu: bool = False
    gpu_name: str = ""
    vram_gb: float = 0.0
    ram_gb: float = 0.0
    os_name: str = ""
    tier: str = TIER_INSUFFICIENT
    features_enabled: list[str] = field(default_factory=list)
    features_disabled: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    visual_retrieval: bool = False
    grounding_mode: str = "text-only"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Detection functions — real system probes, no mocks
# ---------------------------------------------------------------------------

def _detect_ram_gb() -> float:
    """Detect total system RAM in GB. Returns 0.0 if unknown."""
    # Try psutil first (most reliable cross-platform)
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024**3), 1)
    except ImportError:
        pass

    # Linux /proc/meminfo fallback
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024**2), 1)
        except (IOError, ValueError, IndexError):
            pass

    # macOS sysctl fallback
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return round(int(result.stdout.strip()) / (1024**3), 1)
        except (subprocess.SubprocessError, ValueError):
            pass

    # Windows WMI fallback
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
                if len(lines) >= 2:
                    return round(int(lines[1]) / (1024**3), 1)
        except (subprocess.SubprocessError, ValueError):
            pass

    return 0.0


def _detect_gpu() -> tuple[bool, str, float]:
    """Detect GPU presence, name, and VRAM in GB.
    Returns (has_gpu, gpu_name, vram_gb).
    Uses nvidia-smi for NVIDIA GPUs. No mock — probes real hardware.
    """
    # Try nvidia-smi (NVIDIA GPUs)
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            result = subprocess.run(
                [nvidia_smi,
                 "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().split("\n")[0]
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    name = parts[0]
                    vram_mb = float(parts[1])
                    vram_gb = round(vram_mb / 1024.0, 1)
                    return True, name, vram_gb
        except (subprocess.SubprocessError, ValueError, IndexError):
            pass

    # Try ROCM/SMI for AMD GPUs
    rocm_smi = shutil.which("rocm-smi")
    if rocm_smi:
        try:
            result = subprocess.run(
                [rocm_smi, "--showmeminfo", "vram", "--json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                for key, val in data.items():
                    if "VRAM" in key and isinstance(val, dict):
                        vram_bytes = int(val.get("VRAM Total Memory (B)", 0))
                        if vram_bytes > 0:
                            return True, "AMD GPU", round(vram_bytes / (1024**3), 1)
        except (subprocess.SubprocessError, ValueError, json.JSONDecodeError):
            pass

    # macOS: check for Metal/MPS via system_profiler
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                displays = data.get("SPDisplaysDataType", [])
                for gpu_info in displays:
                    name = gpu_info.get("sppci_model", "")
                    if name and "Apple" in name:
                        # Apple Silicon unified memory — report as GPU
                        vram = _detect_ram_gb()  # unified memory
                        return True, name, vram
        except (subprocess.SubprocessError, ValueError, json.JSONDecodeError):
            pass

    return False, "", 0.0


def detect_hardware(
    override_gpu: Optional[bool] = None,
    override_vram: Optional[float] = None,
    override_ram: Optional[float] = None,
) -> HardwareProfile:
    """Detect hardware and determine tier + feature flags.

    Override parameters are for TESTING ONLY — they let tests simulate
    different hardware environments without mocking the detection functions.
    In production, these are None and real hardware is probed.
    """
    has_gpu, gpu_name, vram_gb = _detect_gpu()
    ram_gb = _detect_ram_gb()

    # Apply test overrides if provided
    if override_gpu is not None:
        has_gpu = override_gpu
        if not has_gpu:
            gpu_name = ""
            vram_gb = 0.0
    if override_vram is not None:
        vram_gb = override_vram
        if vram_gb > 0:
            has_gpu = True
    if override_ram is not None:
        ram_gb = override_ram

    profile = HardwareProfile(
        has_gpu=has_gpu,
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        ram_gb=ram_gb,
        os_name=platform.system(),
    )

    # Determine tier
    if has_gpu and vram_gb >= RECOMMENDED_VRAM_GB and ram_gb >= RECOMMENDED_RAM_GB:
        profile.tier = TIER_RECOMMENDED
    elif ram_gb >= MIN_RAM_GB:
        profile.tier = TIER_MINIMUM
    else:
        profile.tier = TIER_INSUFFICIENT

    # Feature flags based on tier
    if profile.tier == TIER_RECOMMENDED:
        profile.features_enabled = [
            "visual_retrieval (ColQwen2/ColPali)",
            "semantic_grounding",
            "fuzzy_grounding",
            "exact_grounding",
            "local_llm_34B",
            "ocr_layout (Docling/DeepSeek-OCR2)",
            "embeddings (fastembed/model2vec)",
        ]
        profile.features_disabled = []
        profile.visual_retrieval = True
        profile.grounding_mode = "visual+text"
    elif profile.tier == TIER_MINIMUM:
        profile.features_enabled = [
            "exact_grounding",
            "fuzzy_grounding",
            "semantic_grounding (degraded)",
            "local_llm_7B",
            "ocr_layout (Docling)",
            "embeddings (fastembed)",
        ]
        profile.features_disabled = [
            "visual_retrieval (ColQwen2/ColPali) — requires GPU with ≥16GB VRAM",
            "local_llm_34B — requires GPU with ≥24GB VRAM",
            "local_llm_13B — requires GPU with ≥10GB VRAM",
        ]
        profile.visual_retrieval = False
        profile.grounding_mode = "text-only"
        profile.warnings.append(
            "visual retrieval disabled — CPU mode, text-only grounding"
        )
    else:  # INSUFFICIENT
        profile.features_enabled = [
            "exact_grounding",
            "fuzzy_grounding",
        ]
        profile.features_disabled = [
            "visual_retrieval — no GPU",
            "semantic_grounding — insufficient RAM for embedding model",
            "local_llm — insufficient RAM for any model size",
            "ocr_layout — insufficient RAM",
        ]
        profile.visual_retrieval = False
        profile.grounding_mode = "text-only"
        profile.warnings.append(
            "visual retrieval disabled — CPU mode, text-only grounding"
        )
        profile.warnings.append(
            f"INSUFFICIENT RAM: {ram_gb}GB detected, minimum {MIN_RAM_GB}GB required. "
            f"Kairo cannot run the local LLM. Upgrade RAM or use BYO-key cloud mode."
        )

    return profile


# ---------------------------------------------------------------------------
# Pre-load guardrail — check before loading a model
# ---------------------------------------------------------------------------

class InsufficientResourceError(Exception):
    """Raised when hardware is insufficient to load a model.
    In production, this is caught and a precise message is printed
    instead of allowing an OOM crash.
    """
    pass


def check_model_loadable(
    model_size: str,
    profile: Optional[HardwareProfile] = None,
) -> tuple[bool, str]:
    """Check if a model of given size can be loaded on current hardware.

    Returns (can_load, message). If can_load is False, message explains
    exactly what is insufficient. This is called BEFORE attempting to load
    a model, preventing OOM crashes.

    Args:
        model_size: One of "7B", "13B", "34B"
        profile: Optional pre-detected profile. If None, detects fresh.
    """
    if profile is None:
        profile = detect_hardware()

    model_size = model_size.upper().strip()
    if model_size not in MODEL_VRAM_REQUIREMENTS_GB:
        return False, f"Unknown model size '{model_size}'. Supported: {list(MODEL_VRAM_REQUIREMENTS_GB.keys())}"

    if profile.has_gpu:
        required_vram = MODEL_VRAM_REQUIREMENTS_GB[model_size]
        if profile.vram_gb < required_vram:
            return False, (
                f"INSUFFICIENT VRAM: model '{model_size}' requires {required_vram}GB VRAM, "
                f"but only {profile.vram_gb}GB available on GPU '{profile.gpu_name}'. "
                f"Use a smaller model or switch to CPU-only mode."
            )
        return True, f"OK: model '{model_size}' fits in {profile.vram_gb}GB VRAM"
    else:
        # CPU-only path
        required_ram = MODEL_RAM_REQUIREMENTS_GB.get(model_size, 999.0)
        if profile.ram_gb < required_ram:
            return False, (
                f"INSUFFICIENT RAM (CPU mode): model '{model_size}' requires {required_ram}GB RAM, "
                f"but only {profile.ram_gb}GB available. "
                f"No GPU detected — visual retrieval disabled, text-only grounding. "
                f"Use a smaller model (7B) or add a GPU."
            )
        if profile.ram_gb < MIN_RAM_GB:
            return False, (
                f"INSUFFICIENT RAM: {profile.ram_gb}GB detected, minimum {MIN_RAM_GB}GB required. "
                f"Kairo cannot run any local model. Consider BYO-key cloud mode (off by default)."
            )
        return True, f"OK: model '{model_size}' fits in {profile.ram_gb}GB RAM (CPU mode)"


def safe_model_load(model_size: str, profile: Optional[HardwareProfile] = None) -> str:
    """Attempt to load a model with pre-flight resource check.

    Instead of OOM-crashing, this checks resources first and returns
    a precise diagnostic message if insufficient.

    Returns a status string. In production, the caller uses this to decide
    whether to proceed with model loading or fall back gracefully.
    """
    can_load, message = check_model_loadable(model_size, profile)
    if not can_load:
        logger.warning("Model load blocked by hardware check: %s", message)
        return f"BLOCKED: {message}"
    logger.info("Model load approved: %s", message)
    return f"APPROVED: {message}"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def format_report(profile: HardwareProfile) -> str:
    """Format a human-readable hardware report."""
    lines = []
    lines.append("=" * 60)
    lines.append("Kairo Phantom — Hardware Check")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"OS:              {profile.os_name}")
    lines.append(f"GPU:             {profile.gpu_name if profile.has_gpu else 'Not detected'}")
    lines.append(f"VRAM:            {profile.vram_gb}GB" if profile.has_gpu else "VRAM:            N/A (no GPU)")
    lines.append(f"RAM:             {profile.ram_gb}GB")
    lines.append(f"Tier:            {profile.tier}")
    lines.append(f"Grounding mode:  {profile.grounding_mode}")
    lines.append(f"Visual retrieval: {'ENABLED' if profile.visual_retrieval else 'DISABLED'}")
    lines.append("")
    lines.append("Features enabled:")
    for f in profile.features_enabled:
        lines.append(f"  ✓ {f}")
    lines.append("")
    if profile.features_disabled:
        lines.append("Features disabled:")
        for f in profile.features_disabled:
            lines.append(f"  ✗ {f}")
        lines.append("")
    if profile.warnings:
        lines.append("Warnings:")
        for w in profile.warnings:
            lines.append(f"  ⚠ {w}")
        lines.append("")
    lines.append("Model load checks:")
    for size in ["7B", "13B", "34B"]:
        status = safe_model_load(size, profile)
        lines.append(f"  {size}: {status}")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    """CLI entry point: detect hardware and print report."""
    profile = detect_hardware()
    report = format_report(profile)
    print(report)
    print()
    print("JSON profile:")
    print(profile.to_json())

    # Exit code: 0 if sufficient, 1 if insufficient
    if profile.tier == TIER_INSUFFICIENT:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()