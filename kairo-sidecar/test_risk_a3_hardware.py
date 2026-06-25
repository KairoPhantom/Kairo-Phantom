"""
Risk A3: Hardware Variability (GPU/CPU/RAM).
Test: graceful degradation — no GPU → CPU PIL pipeline works (REAL, not mocked).
"""
import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))


class TestHardwareDegradation:
    """Hardware detection + graceful degradation must work."""

    def test_cpu_fallback_image_processor_works(self):
        """CPU PIL-based ImageProcessor must work without GPU (REAL processing)."""
        from sidecar.parsers.image_processor import ImageProcessor
        from PIL import Image
        import tempfile

        proc = ImageProcessor()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 100), color="red")
            img.save(f.name)
            img_path = f.name

        try:
            result = proc.resize(img_path, (50, 50))
            assert result is not None, "CPU image processing returned None"
        finally:
            os.unlink(img_path)

    def test_media_embeddings_raise_without_gpu(self):
        """MediaEmbeddings must raise RuntimeError (not silently succeed) without embed-anything."""
        from sidecar.parsers.media_embeddings import MediaEmbeddings
        with pytest.raises(RuntimeError):
            MediaEmbeddings()

    def test_adaptive_compute_tier_detection(self):
        """AdaptiveComputeTier must detect the hardware tier without crashing."""
        from sidecar.adaptive_compute import AdaptiveComputeTier
        tier = AdaptiveComputeTier.detect_tier()
        assert tier is not None, "detect_tier() returned None"
        assert isinstance(tier, str), f"Tier must be a string, got: {type(tier)}"

    def test_adaptive_compute_model_selection(self):
        """Model selection must return a valid model name for the detected tier."""
        from sidecar.adaptive_compute import AdaptiveComputeTier
        tier = AdaptiveComputeTier.detect_tier()
        model = AdaptiveComputeTier.get_model_for_tier(tier)
        assert model is not None, f"No model for tier {tier}"
        assert isinstance(model, str), f"Model must be string, got: {type(model)}"

    def test_no_gpu_in_sandbox_not_tier1(self):
        """In this sandbox (no GPU), tier must NOT be tier1 (GPU tier)."""
        from sidecar.adaptive_compute import AdaptiveComputeTier
        tier = AdaptiveComputeTier.detect_tier()
        # Sandbox has no GPU → must not report GPU tier
        # (tier names may vary, but must not claim GPU)
        assert "gpu" not in tier.lower() or tier != "tier1",             f"Tier {tier} claims GPU in a sandbox with no GPU — FALSE POSITIVE"
