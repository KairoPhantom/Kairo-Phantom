"""
kairo-sidecar/sidecar/cua/__init__.py

CUA — Computer Use Agent package.

This package implements Tier 3 (last-resort) GUI automation for Kairo Phantom.

Tier hierarchy:
  Tier 0: File API (python-docx, openpyxl, python-pptx)  — 95% of tasks
  Tier 1: UIA SetValue (accessibility write)              — browser fields, etc.
  Tier 2: MCP server (figma-mcp, excel-mcp, etc.)        — when API available
  Tier 3: CUA (this package)                             — only when 0-2 all fail

Primary use case: Canva (no API of any kind — CUA is the only path).

Architecture:
  - UIA-first targeting (eliminates 56.7% coordinate miss rate of generic CUA)
  - VLM grounding via Qwen2.5-VL-7B (reduces miss rate to <12%)
  - farscry OCR fallback when UIA can't find the element
  - Clipboard fallback when both fail
  - User approval required before ANY action (Tab in GRP)
  - Esc cancels all pending actions within 100ms
"""

from .canva_cua import CanvaCUAAgent, ExecutionResult
from .driver_service import CuaDriverService
from .vlm_config import VlmConfig, VlmModelSpec, get_vlm_config, build_vlm_config
from .vlm_download_manager import (
    VlmDownloadManager,
    BackgroundVlmDownloader,
    DownloadState,
    DownloadProgress,
    get_background_downloader,
)
from .vlm_grounding import (
    VlmGroundingEngine,
    GroundingResult,
    VerificationResult,
    ScreenDescription,
    get_vlm_engine,
)
from .cross_app_orchestrator import (
    CrossAppOrchestrator,
    AppWorkflowPlan,
    WorkflowStep,
    WorkflowBuilder,
    OrchestrationResult,
    AppTarget,
    StepActionType,
    get_cross_app_orchestrator,
)

__all__ = [
    # Canva CUA (Tier 3 core)
    "CanvaCUAAgent",
    "ExecutionResult",
    "CuaDriverService",
    # VLM Config
    "VlmConfig",
    "VlmModelSpec",
    "get_vlm_config",
    "build_vlm_config",
    # VLM Download
    "VlmDownloadManager",
    "BackgroundVlmDownloader",
    "DownloadState",
    "DownloadProgress",
    "get_background_downloader",
    # VLM Grounding Engine
    "VlmGroundingEngine",
    "GroundingResult",
    "VerificationResult",
    "ScreenDescription",
    "get_vlm_engine",
    # Cross-App Orchestrator
    "CrossAppOrchestrator",
    "AppWorkflowPlan",
    "WorkflowStep",
    "WorkflowBuilder",
    "OrchestrationResult",
    "AppTarget",
    "StepActionType",
    "get_cross_app_orchestrator",
]
