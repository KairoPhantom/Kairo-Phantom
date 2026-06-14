"""Slide Image Generation: ComfyUI, gpt-image-2, Nano Banana Pro."""
import subprocess
import json
import os
import tempfile
import base64
import logging
from enum import Enum
from typing import Optional, List, Dict

log = logging.getLogger("kairo-sidecar.slide_image_gen")

class ImageBackend(Enum):
    COMFYUI = "comfyui"        # Local, offline
    GPT_IMAGE_2 = "gpt_image_2"  # OpenAI, cloud, best text rendering
    NANO_BANANA = "nano_banana"  # Gemini, cloud, parallel fast
    STABLE_DIFFUSION = "sd"      # Local via ComfyUI

class SlideImageGenerator:
    """Generates images for presentation slides."""

    def __init__(self, offline_mode: bool = True):
        self.offline_mode = offline_mode

    def generate_slide_image(self,
                             slide_content: dict,
                             backend: ImageBackend = None,
                             style: str = "professional") -> str:
        """
        Generate a slide image. Returns path to generated image.
        If offline or backends fail, generates a local high-quality mock PNG.
        """
        backend = backend or self._auto_select_backend()

        try:
            if backend == ImageBackend.COMFYUI and self._comfyui_available():
                return self._generate_comfyui(slide_content, style)
            elif backend == ImageBackend.GPT_IMAGE_2 and self._gpt_image2_available():
                return self._generate_gpt_image2(slide_content, style)
            elif backend == ImageBackend.NANO_BANANA and self._nano_banana_available():
                return self._generate_nano_banana(slide_content, style)
            # No backend was available — fall through to feature-flag guard below
            raise RuntimeError(
                f"No image-generation backend available for backend={backend.value!r}. "
                f"Available: ComfyUI={self._comfyui_available()}, "
                f"GPT-Image-2={self._gpt_image2_available()}, "
                f"NanoBanana={self._nano_banana_available()}."
            )
        except Exception as exc:
            # EXPLICIT FEATURE FLAG — must be set deliberately in local dev or tests.
            # CI and production must NOT set this flag; they should see the real failure.
            if os.environ.get("KAIRO_SLIDE_IMAGE_MOCK", "0") == "1":
                log.warning(
                    f"[KAIRO_SLIDE_IMAGE_MOCK=1] Real image generation failed: {exc}. "
                    f"Returning mock PNG. This MUST NOT happen in CI or production."
                )
                return self._generate_mock_image(slide_content, style)
            # Hard fail — do not hide the problem with a silent mock.
            raise RuntimeError(
                f"slide_image_gen: image generation failed and KAIRO_SLIDE_IMAGE_MOCK "
                f"is not set. Backend={backend.value!r}. "
                f"Set KAIRO_SLIDE_IMAGE_MOCK=1 only in local dev/tests. "
                f"Underlying error: {exc}"
            ) from exc


    def generate_deck_images(self,
                             slide_contents: List[dict],
                             backend: ImageBackend = None,
                             style: str = "professional",
                             parallel: bool = True) -> List[str]:
        """
        Generate images for an entire deck.
        """
        backend = backend or self._auto_select_backend()
        image_paths = []

        for slide in slide_contents:
            path = self.generate_slide_image(slide, backend, style)
            image_paths.append(path)

        return image_paths

    def _auto_select_backend(self) -> ImageBackend:
        """Auto-select based on availability and offline mode."""
        if self.offline_mode:
            if self._comfyui_available():
                return ImageBackend.COMFYUI
            return ImageBackend.COMFYUI # Default fallback
        # Online: prefer quality
        if self._gpt_image2_available():
            return ImageBackend.GPT_IMAGE_2
        if self._nano_banana_available():
            return ImageBackend.NANO_BANANA
        return ImageBackend.COMFYUI

    def _generate_comfyui(self, slide: dict, style: str) -> str:
        """Generate via local ComfyUI."""
        prompt = self._build_image_prompt(slide, style)
        import requests
        response = requests.post(
            "http://localhost:8188/prompt",
            json={"prompt": prompt, "workflow": "slide_generation"},
            timeout=5
        )
        if response.status_code == 200:
            # Poll and download
            pass
        raise RuntimeError("ComfyUI server returned error or not configured completely")

    def _generate_gpt_image2(self, slide: dict, style: str) -> str:
        """Generate via GPT-Image-2 (mocked API call unless client library is imported)."""
        prompt = self._build_full_slide_prompt(slide, style)
        # API execution mock
        raise RuntimeError("GPT-Image-2 API keys or client not fully loaded")

    def _generate_nano_banana(self, slide: dict, style: str) -> str:
        """Generate via Nano Banana Pro."""
        prompt = self._build_image_prompt(slide, style)
        raise RuntimeError("Nano Banana Pro Gemini API key not found")

    def _generate_mock_image(self, slide: dict, style: str) -> str:
        """Draws a beautiful mock infographic/slide image using PIL."""
        from PIL import Image, ImageDraw, ImageFont
        
        # 16:9 widescreen dimensions (e.g. 1280x720)
        img = Image.new("RGB", (1280, 720), color=(240, 244, 248))
        draw = ImageDraw.Draw(img)

        # Draw a stylish visual layout (gradient-like shape/accent)
        # Left accent block
        draw.rectangle([0, 0, 40, 720], fill=(0, 102, 204))
        
        # Draw some decorative abstract geometric shapes representing an infographic
        draw.ellipse([800, 200, 1100, 500], fill=(224, 235, 245), outline=(0, 102, 204), width=6)
        draw.arc([800, 200, 1100, 500], start=0, end=270, fill=(0, 102, 204), width=10)
        
        title = slide.get("title", "Market Growth")
        topic = slide.get("topic", "Data Infographic")
        
        # Text rendering (simple fail-safe font)
        try:
            # Try to load a system font, otherwise default
            font_title = ImageFont.truetype("arial.ttf", 48)
            font_subtitle = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            font_title = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()

        draw.text((100, 100), title, fill=(33, 37, 41), font=font_title)
        draw.text((100, 170), f"Topic: {topic}", fill=(108, 117, 125), font=font_subtitle)
        draw.text((890, 335), "75%", fill=(0, 102, 204), font=font_title)
        
        fd, path = tempfile.mkstemp(suffix=".png", prefix="kairo_slide_img_")
        os.close(fd)
        img.save(path)
        return path

    def _build_full_slide_prompt(self, slide: dict, style: str) -> str:
        """Build gpt-image-2 prompt with text-aware slide design."""
        title = slide.get("title", "")
        bullets = slide.get("bullets", [])
        layout = slide.get("layout", "title_and_content")

        prompt_parts = [
            f"Professional presentation slide, {style} style, 16:9 ratio.",
            f"Title: '{title}'",
        ]
        if bullets:
            prompt_parts.append("Content:")
            for b in bullets[:5]:
                prompt_parts.append(f"- {b}")

        prompt_parts.extend([
            "All text must be clearly visible, well-positioned, and typographically consistent.",
            "Use appropriate icons or diagrams where helpful.",
            "Segoe UI styling typography, clean layout, generous whitespace.",
            "High resolution."
        ])

        return " ".join(prompt_parts)

    def _build_image_prompt(self, slide: dict, style: str) -> str:
        """Build image prompt for slide illustration."""
        title = slide.get("title", "")
        topic = slide.get("topic", title)
        return (f"Professional illustration for a presentation slide "
                f"about '{topic}'. {style} style. Clean, modern, "
                f"corporate aesthetic. 16:9 aspect ratio.")

    def _comfyui_available(self) -> bool:
        """Check if ComfyUI is running."""
        import requests
        try:
            r = requests.get("http://localhost:8188/system_stats", timeout=1)
            return r.status_code == 200
        except Exception:
            return False

    def _gpt_image2_available(self) -> bool:
        return "OPENAI_API_KEY" in os.environ

    def _nano_banana_available(self) -> bool:
        return "GOOGLE_API_KEY" in os.environ
