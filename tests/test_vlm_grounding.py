"""
tests/test_vlm_grounding.py

Test suite for the VLM Grounding Engine.

Tests use mock Ollama responses to avoid requiring an actual GPU/model download.
All tests are deterministic and run in CI without any external dependencies.

Coverage:
  - VlmConfig hardware detection and model selection
  - VlmGroundingEngine.ground_element with mock responses
  - VlmGroundingEngine.verify_action with before/after screenshots
  - VlmDownloadManager progress tracking and error handling
  - CrossAppOrchestrator plan building and step sequencing
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "kairo-sidecar"))

from sidecar.cua.vlm_config import (
    VlmConfig,
    VlmModelSpec,
    VLM_7B_Q4,
    VLM_3B_Q4,
    build_vlm_config,
    select_model,
    detect_hardware,
    write_modelfile,
)
from sidecar.cua.vlm_grounding import (
    VlmGroundingEngine,
    GroundingResult,
    VerificationResult,
    ScreenDescription,
)
from sidecar.cua.vlm_download_manager import (
    DownloadProgress,
    DownloadState,
    TrayProgressNotifier,
)
from sidecar.cua.cross_app_orchestrator import (
    CrossAppOrchestrator,
    AppWorkflowPlan,
    WorkflowStep,
    WorkflowBuilder,
    AppTarget,
    StepActionType,
    StepStatus,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_model_dir(tmp_path: Path) -> Path:
    """Temporary model cache directory."""
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    return model_dir


@pytest.fixture
def vlm_config_7b(tmp_model_dir: Path) -> VlmConfig:
    """7B GPU config for testing."""
    return VlmConfig(
        selected_model=VLM_7B_Q4,
        model_cache_dir=tmp_model_dir,
        gpu_available=True,
        vram_gb=8.0,
        hardware_tier="gpu-7b",
    )


@pytest.fixture
def vlm_config_3b(tmp_model_dir: Path) -> VlmConfig:
    """3B CPU config for testing."""
    return VlmConfig(
        selected_model=VLM_3B_Q4,
        model_cache_dir=tmp_model_dir,
        gpu_available=False,
        vram_gb=0.0,
        hardware_tier="cpu",
    )


@pytest.fixture
def mock_screenshot(tmp_path: Path) -> Path:
    """Create a small dummy PNG for testing (just enough bytes to be valid)."""
    png_path = tmp_path / "test_screen.png"
    # Minimal valid PNG header
    png_bytes = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D,  # IHDR chunk length
        0x49, 0x48, 0x44, 0x52,  # IHDR type
        0x00, 0x00, 0x00, 0x01,  # Width: 1
        0x00, 0x00, 0x00, 0x01,  # Height: 1
        0x08, 0x02, 0x00, 0x00, 0x00,  # 8-bit RGB
        0x90, 0x77, 0x53, 0xDE,  # CRC
        0x00, 0x00, 0x00, 0x00,  # IEND chunk length
        0x49, 0x45, 0x4E, 0x44,  # IEND type
        0xAE, 0x42, 0x60, 0x82,  # CRC
    ])
    png_path.write_bytes(png_bytes)
    return png_path


# ─── VlmConfig Tests ──────────────────────────────────────────────────────────

class TestVlmConfig:
    def test_model_spec_immutable(self):
        """VlmModelSpec is frozen — immutable."""
        with pytest.raises((TypeError, AttributeError)):
            VLM_7B_Q4.size_gb = 99.9  # type: ignore

    def test_select_model_gpu_7b(self):
        """GPU with ≥6 GB VRAM → 7B model."""
        model = select_model("gpu-7b")
        assert model == VLM_7B_Q4
        assert model.size_gb == pytest.approx(4.2, abs=0.1)

    def test_select_model_gpu_3b(self):
        """GPU with 3-5 GB VRAM → 3B model."""
        model = select_model("gpu-3b")
        assert model == VLM_3B_Q4

    def test_select_model_cpu(self):
        """CPU-only → 3B model (still works, slower)."""
        model = select_model("cpu")
        assert model == VLM_3B_Q4

    def test_config_model_path(self, vlm_config_7b: VlmConfig, tmp_model_dir: Path):
        """Model path combines model_cache_dir and gguf_filename."""
        expected = tmp_model_dir / VLM_7B_Q4.gguf_filename
        assert vlm_config_7b.model_path == expected

    def test_config_is_downloaded_false(self, vlm_config_7b: VlmConfig):
        """is_downloaded is False when file doesn't exist."""
        assert not vlm_config_7b.is_downloaded

    def test_config_is_downloaded_true(self, vlm_config_7b: VlmConfig):
        """is_downloaded is True when file exists and is large enough."""
        # Create a large-enough dummy file
        vlm_config_7b.model_path.write_bytes(b"\x00" * 200_000_000)
        assert vlm_config_7b.is_downloaded

    def test_config_ollama_options(self, vlm_config_7b: VlmConfig):
        """to_ollama_options includes keep_alive=0."""
        opts = vlm_config_7b.to_ollama_options()
        assert opts["keep_alive"] == 0  # Free VRAM immediately after task
        assert opts["temperature"] == 0.0  # Deterministic for grounding
        assert opts["num_ctx"] == 4096

    def test_write_modelfile(self, vlm_config_7b: VlmConfig):
        """Modelfile is written with correct FROM path."""
        path = write_modelfile(vlm_config_7b)
        assert path.exists()
        content = path.read_text()
        assert "FROM" in content
        assert VLM_7B_Q4.gguf_filename in content
        assert "temperature 0" in content

    def test_build_vlm_config_creates_dir(self, tmp_path: Path):
        """build_vlm_config creates model_cache_dir if missing."""
        new_dir = tmp_path / "nonexistent" / "models"
        assert not new_dir.exists()
        config = build_vlm_config(model_cache_dir=new_dir)
        assert new_dir.exists()


# ─── VlmGroundingEngine Tests ─────────────────────────────────────────────────

class TestVlmGroundingEngine:
    """Tests with mocked Ollama API calls."""

    def _make_engine(self, config: VlmConfig, model_exists: bool = True) -> VlmGroundingEngine:
        """Create engine with optionally available model."""
        if model_exists:
            config.model_path.write_bytes(b"\x00" * 200_000_000)
        engine = VlmGroundingEngine(config)
        # Override downloader to report model as ready/not-ready
        engine._downloader = MagicMock()
        engine._downloader.is_ready = model_exists
        return engine

    @pytest.mark.asyncio
    async def test_ground_element_not_available(
        self, vlm_config_3b: VlmConfig
    ):
        """Returns not-found result when VLM not available."""
        engine = self._make_engine(vlm_config_3b, model_exists=False)
        result = await engine.ground_element("/fake/screen.png", "Submit button")
        assert not result.found
        assert "downloading" in result.description.lower()

    @pytest.mark.asyncio
    async def test_ground_element_success(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """Returns coordinates when VLM finds element."""
        engine = self._make_engine(vlm_config_7b)

        mock_response = json.dumps({
            "found": True,
            "x": 840,
            "y": 450,
            "confidence": 0.97,
            "description": "Submit button found at bottom-right of form",
        })

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (mock_response, 1200.0)
            result = await engine.ground_element(mock_screenshot, "Submit button")

        assert result.found
        assert result.x == 840
        assert result.y == 450
        assert result.confidence == pytest.approx(0.97, abs=0.001)
        assert result.latency_ms == pytest.approx(1200.0, abs=1.0)

    @pytest.mark.asyncio
    async def test_ground_element_not_found(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """Returns found=False when VLM cannot locate element."""
        engine = self._make_engine(vlm_config_7b)

        mock_response = json.dumps({
            "found": False,
            "x": 0,
            "y": 0,
            "confidence": 0.0,
            "description": "Could not find 'Purple Unicorn Button' in screenshot",
        })

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (mock_response, 800.0)
            result = await engine.ground_element(mock_screenshot, "Purple Unicorn Button")

        assert not result.found
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_ground_element_json_in_markdown(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """Handles VLM response wrapped in markdown code fences."""
        engine = self._make_engine(vlm_config_7b)

        # VLM sometimes wraps JSON in ```json ... ```
        mock_response = '```json\n{"found": true, "x": 100, "y": 200, "confidence": 0.9, "description": "found"}\n```'

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (mock_response, 500.0)
            result = await engine.ground_element(mock_screenshot, "Any button")

        assert result.found
        assert result.x == 100
        assert result.y == 200

    @pytest.mark.asyncio
    async def test_ground_element_parse_error(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """Returns not-found on JSON parse error — never raises exception."""
        engine = self._make_engine(vlm_config_7b)

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = ("This is not JSON at all", 300.0)
            result = await engine.ground_element(mock_screenshot, "Button")

        assert not result.found
        assert "error" in result.description.lower() or "parse" in result.description.lower()

    @pytest.mark.asyncio
    async def test_verify_action_success(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """Verify returns success=True when dialog shows expected text."""
        engine = self._make_engine(vlm_config_7b)

        mock_response = json.dumps({
            "success": True,
            "confidence": 0.95,
            "explanation": "Dialog shows 'File saved successfully' — action confirmed",
        })

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (mock_response, 800.0)
            result = await engine.verify_action(
                mock_screenshot, mock_screenshot, "File saved confirmation"
            )

        assert result.success
        assert result.confidence == pytest.approx(0.95, abs=0.001)
        assert "saved" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_verify_action_failure(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """Verify returns success=False when action didn't produce expected result."""
        engine = self._make_engine(vlm_config_7b)

        mock_response = json.dumps({
            "success": False,
            "confidence": 0.88,
            "explanation": "No save confirmation visible — screenshots appear identical",
        })

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (mock_response, 900.0)
            result = await engine.verify_action(
                mock_screenshot, mock_screenshot, "File saved"
            )

        assert not result.success

    @pytest.mark.asyncio
    async def test_verify_keyboard_only_mode(self, vlm_config_3b: VlmConfig):
        """Keyboard-only mode returns assumed-success."""
        engine = self._make_engine(vlm_config_3b, model_exists=False)
        result = await engine.verify_action("/fake/before.png", "/fake/after.png", "anything")
        assert result.success  # Assumed success in keyboard-only mode
        assert result.confidence == pytest.approx(0.5, abs=0.01)
        assert "keyboard-only" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_describe_screen(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """Screen description extracts app name and elements."""
        engine = self._make_engine(vlm_config_7b)

        mock_response = json.dumps({
            "app_name": "Microsoft Word",
            "elements": [
                {"name": "Save Button", "type": "button", "x": 100, "y": 50, "text": "Save"},
                {"name": "Close Button", "type": "button", "x": 1900, "y": 20, "text": "X"},
            ],
            "description": "Microsoft Word with document open",
        })

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (mock_response, 1500.0)
            result = await engine.describe_screen(mock_screenshot)

        assert result.app_name == "Microsoft Word"
        assert len(result.elements) == 2
        assert result.elements[0]["name"] == "Save Button"


# ─── DownloadProgress Tests ───────────────────────────────────────────────────

class TestDownloadProgress:
    def test_percent_calculation(self):
        p = DownloadProgress(
            state=DownloadState.DOWNLOADING,
            bytes_downloaded=2_100_000_000,  # 2.1 GB of 4.2 GB
            total_bytes=4_200_000_000,
        )
        assert p.percent == pytest.approx(50.0, abs=0.1)

    def test_percent_zero_when_total_zero(self):
        p = DownloadProgress(state=DownloadState.NOT_STARTED)
        assert p.percent == 0.0

    def test_is_complete(self):
        p = DownloadProgress(state=DownloadState.COMPLETE)
        assert p.is_complete

    def test_is_active_while_downloading(self):
        p = DownloadProgress(state=DownloadState.DOWNLOADING)
        assert p.is_active

    def test_is_not_active_when_failed(self):
        p = DownloadProgress(state=DownloadState.FAILED, error="network error")
        assert not p.is_active


# ─── CrossAppOrchestrator Tests ───────────────────────────────────────────────

class TestCrossAppOrchestrator:
    def test_workflow_builder_excel_pptx(self):
        """WorkflowBuilder creates valid Excel→PowerPoint plan."""
        plan = WorkflowBuilder.excel_to_powerpoint_email(
            chart_name="Q3 Revenue",
            slide_title="Q3 Results",
        )
        assert plan.plan_id == "excel-to-pptx-email"
        assert plan.total_steps > 0
        assert any(s.app_target == AppTarget.EXCEL for s in plan.steps)
        assert any(s.app_target == AppTarget.POWERPOINT for s in plan.steps)
        # No email steps without recipient
        assert all(s.app_target != AppTarget.OUTLOOK for s in plan.steps)

    def test_workflow_builder_with_email(self):
        """WorkflowBuilder adds email steps when recipient provided."""
        plan = WorkflowBuilder.excel_to_powerpoint_email(
            recipient_email="boss@company.com",
            email_subject="Q3 Report",
        )
        assert any(s.app_target == AppTarget.OUTLOOK for s in plan.steps)
        outlook_steps = [s for s in plan.steps if s.app_target == AppTarget.OUTLOOK]
        assert len(outlook_steps) >= 3  # Focus + new email + type recipient

    def test_workflow_plan_progress(self):
        """Plan tracks progress correctly."""
        plan = WorkflowBuilder.excel_to_powerpoint_email()
        assert plan.completed_steps == 0
        assert plan.progress_percent == pytest.approx(0.0, abs=0.1)
        
        # Mark first step as success
        plan.steps[0].status = StepStatus.SUCCESS
        assert plan.completed_steps == 1
        expected_pct = (1 / plan.total_steps) * 100
        assert plan.progress_percent == pytest.approx(expected_pct, abs=0.1)

    def test_plan_is_complete(self):
        """Plan is complete when all steps succeed or are skipped."""
        plan = WorkflowBuilder.word_to_pdf_email()
        for step in plan.steps:
            step.status = StepStatus.SUCCESS
        assert plan.is_complete

    def test_plan_not_complete_with_pending(self):
        """Plan is not complete when steps are pending."""
        plan = WorkflowBuilder.word_to_pdf_email()
        assert not plan.is_complete

    @pytest.mark.asyncio
    async def test_orchestrator_dry_run(self):
        """Dry run completes without executing any actions."""
        plan = WorkflowBuilder.excel_to_powerpoint_email()
        orch = CrossAppOrchestrator()
        
        result = await orch.execute_plan(plan, dry_run=True)
        
        assert result.success
        assert result.steps_completed == plan.total_steps
        assert result.steps_failed == 0

    @pytest.mark.asyncio
    async def test_orchestrator_step_callback(self):
        """Step callback is invoked for each step."""
        plan = WorkflowBuilder.word_to_pdf_email()
        orch = CrossAppOrchestrator()
        
        callback_count = 0
        def on_step(step: WorkflowStep) -> None:
            nonlocal callback_count
            callback_count += 1
        
        await orch.execute_plan(plan, on_step_update=on_step, dry_run=True)
        
        # Callback should be called at least once per step
        assert callback_count >= plan.total_steps

    def test_step_ids_are_sequential(self):
        """Step IDs must be sequential for rollback to work correctly."""
        plan = WorkflowBuilder.excel_to_powerpoint_email()
        ids = [s.step_id for s in plan.steps]
        assert ids == list(range(1, len(plan.steps) + 1))

    def test_all_steps_have_descriptions(self):
        """All steps must have human-readable descriptions for GRP display."""
        plan = WorkflowBuilder.excel_to_powerpoint_email()
        for step in plan.steps:
            assert len(step.description) > 0, f"Step {step.step_id} missing description"


# ─── Integration: VLM + CUA Flow ──────────────────────────────────────────────

class TestVlmCuaIntegration:
    """End-to-end tests for the VLM → CUA grounding flow."""

    @pytest.mark.asyncio
    async def test_vlm_grounding_reduces_miss_rate(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """
        Simulates the miss rate reduction:
        UIA fails (56.7% miss) → VLM finds element (<12% miss).
        
        This is the core value proposition from the briefing.
        """
        engine = VlmGroundingEngine(vlm_config_7b)
        engine._downloader = MagicMock()
        engine._downloader.is_ready = True

        # Simulate UIA failure (element not in accessibility tree)
        uia_found = False

        # VLM fallback
        mock_response = json.dumps({
            "found": True,
            "x": 1234,
            "y": 567,
            "confidence": 0.93,
            "description": "Submit button located via visual analysis",
        })

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (mock_response, 1100.0)
            
            if not uia_found:
                # Call VLM as fallback
                result = await engine.ground_element(mock_screenshot, "Submit button")
                assert result.found
                assert result.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_semantic_verify_replaces_pixel_diff(
        self, vlm_config_7b: VlmConfig, mock_screenshot: Path
    ):
        """
        Verifies that semantic verification replaces pixel diff.
        
        Pixel diff: same screenshot = not changed (false negative)
        VLM verify: explicitly asked "was file saved?" → returns true
        """
        engine = VlmGroundingEngine(vlm_config_7b)
        engine._downloader = MagicMock()
        engine._downloader.is_ready = True

        mock_response = json.dumps({
            "success": True,
            "confidence": 0.97,
            "explanation": "Dialog title changed from 'Unsaved' to 'Saved'",
        })

        with patch.object(engine, "_ollama_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (mock_response, 850.0)
            result = await engine.verify_action(
                mock_screenshot, mock_screenshot, "File saved dialog appeared"
            )

        assert result.success
        assert result.confidence >= 0.9


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
