#!/usr/bin/env python3
"""
Reveal.js Export Module — Advancement 5
Generates interactive HTML5 presentations from Kairo slide data.
Supports: base64 images, GL transitions, speaker notes, and speaker view.

Usage (as MCP tool):
  Called by office-pptx-bridge export_revealjs tool.

CLI:
  python revealjs_export.py --slides slides.json --out presentation.html
"""

import json
import os
import sys
import base64
import argparse
from pathlib import Path
from typing import Any

# ── Slide Schema ───────────────────────────────────────────────────────────────

def load_image_b64(path_or_url: str) -> str:
    """Load an image from file or return URL as-is."""
    if not path_or_url:
        return ""
    if path_or_url.startswith("http"):
        return path_or_url
    if os.path.exists(path_or_url):
        ext = Path(path_or_url).suffix.lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}.get(ext, "png")
        with open(path_or_url, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/{mime};base64,{b64}"
    return path_or_url


def build_slide_html(slide: dict, index: int) -> str:
    """Convert a slide dict to a Reveal.js <section> element."""
    title = slide.get("title", "")
    content = slide.get("content", "")
    image = slide.get("image", "")
    notes = slide.get("speaker_notes", slide.get("notes", ""))
    bg_color = slide.get("bg_color", "")
    layout = slide.get("layout", "default")
    transition = slide.get("transition", "fade")

    # Build section attributes
    attrs = []
    if bg_color:
        attrs.append(f'data-background-color="{bg_color}"')
    if transition:
        attrs.append(f'data-transition="{transition}"')

    attrs_str = " ".join(attrs)

    # Build content elements
    content_html = ""

    if layout == "title-only":
        content_html = f'<h1>{title}</h1>'
    elif layout == "two-column":
        parts = content.split("||") if "||" in content else [content, ""]
        content_html = f"""
        <div class="r-hstack">
          <div class="r-stack">
            <h2>{title}</h2>
            <div class="slide-content">{parts[0]}</div>
          </div>
          <div class="r-stack">
            <div class="slide-content">{parts[1]}</div>
          </div>
        </div>"""
    elif layout == "image-right" and image:
        img_src = load_image_b64(image)
        content_html = f"""
        <div class="r-hstack">
          <div style="flex:1">
            <h2>{title}</h2>
            <div class="slide-content">{content}</div>
          </div>
          <div style="flex:1">
            <img src="{img_src}" style="max-height:400px;border-radius:8px"/>
          </div>
        </div>"""
    elif layout == "full-image" and image:
        img_src = load_image_b64(image)
        content_html = f'<div data-background-image="{img_src}"><h1 class="slide-overlay-title">{title}</h1></div>'
        attrs_str += f' data-background-image="{img_src}" data-background-opacity="0.6"'
    else:
        # Default layout
        title_tag = f"<h2>{title}</h2>" if title else ""
        image_tag = ""
        if image:
            img_src = load_image_b64(image)
            image_tag = f'<img src="{img_src}" style="max-height:320px;border-radius:8px;margin:16px 0"/>'

        # Format content as bullet list if it contains newlines
        if "\n" in content:
            bullets = "".join(f"<li>{line.strip('- •').strip()}</li>"
                              for line in content.splitlines() if line.strip())
            content_body = f"<ul>{bullets}</ul>"
        else:
            content_body = f"<p>{content}</p>" if content else ""

        content_html = f"{title_tag}{image_tag}{content_body}"

    # Speaker notes
    notes_html = f"<aside class='notes'>{notes}</aside>" if notes else ""

    return f"""
    <section {attrs_str}>
      {content_html}
      {notes_html}
    </section>"""


# ── Full Reveal.js Template ────────────────────────────────────────────────────

def build_presentation(slides: list[dict], title: str = "Kairo Presentation",
                        theme: str = "black", transition: str = "fade",
                        enable_gl: bool = False) -> str:
    """Build a complete Reveal.js HTML file from slide data."""

    slides_html = "\n".join(build_slide_html(s, i) for i, s in enumerate(slides))

    gl_plugin = """
    <!-- GL Transitions plugin -->
    <script>
    // GL Transitions can be added here via reveal.js-gl plugin
    // or custom GLSL shader integration
    </script>
    """ if enable_gl else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reset.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/{theme}.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/highlight/monokai.css">
  <style>
    :root {{
      --r-main-font: 'Inter', 'Segoe UI', system-ui, sans-serif;
      --r-heading-font: var(--r-main-font);
      --r-link-color: #7c3aed;
    }}
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    .reveal .slides section {{
      text-align: left;
    }}
    .reveal h1, .reveal h2, .reveal h3 {{
      font-weight: 700;
      text-align: left;
    }}
    .slide-content {{
      font-size: 0.85em;
      line-height: 1.6;
    }}
    .slide-overlay-title {{
      background: rgba(0,0,0,0.6);
      padding: 16px 24px;
      border-radius: 8px;
    }}
    .kairo-badge {{
      position: fixed;
      bottom: 12px;
      right: 16px;
      font-size: 11px;
      opacity: 0.5;
      color: #fff;
      z-index: 1000;
    }}
    .reveal ul {{
      margin-left: 1em;
    }}
    .reveal ul li {{
      margin-bottom: 0.4em;
    }}
  </style>
</head>
<body>

<div class="reveal">
  <div class="slides">
{slides_html}
  </div>
</div>

<div class="kairo-badge">Built with Kairo Phantom</div>

<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/notes/notes.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/highlight/highlight.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/zoom/zoom.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/markdown/markdown.js"></script>
{gl_plugin}
<script>
  Reveal.initialize({{
    hash: true,
    transition: '{transition}',
    transitionSpeed: 'default',
    backgroundTransition: 'fade',
    controls: true,
    controlsTutorial: true,
    progress: true,
    slideNumber: 'c/t',
    showSlideNumber: 'speaker',
    overview: true,
    center: false,
    touch: true,
    loop: false,
    shuffle: false,
    fragments: true,
    fragmentInURL: true,
    embedded: false,
    help: true,
    autoSlide: 0,
    autoSlideStoppable: true,
    mouseWheel: false,
    previewLinks: false,
    width: 1280,
    height: 720,
    margin: 0.04,
    minScale: 0.2,
    maxScale: 2.0,
    plugins: [ RevealNotes, RevealHighlight, RevealZoom, RevealMarkdown ]
  }});
</script>
</body>
</html>"""


# ── Export Function (called by PPTX bridge as MCP tool) ───────────────────────

def export_revealjs(slide_data: list[dict], output_path: str,
                    title: str = "Kairo Presentation",
                    theme: str = "black",
                    transition: str = "fade") -> dict:
    """
    Main export function — called by office-pptx-bridge export_revealjs tool.

    Args:
        slide_data: List of slide dicts with title/content/image/notes/layout
        output_path: Where to write the HTML file
        title: Presentation title
        theme: Reveal.js theme (black, white, moon, sky, beige, etc.)
        transition: Default transition (fade, slide, convex, zoom, none)

    Returns:
        {"success": True, "output": output_path, "slides": N}
    """
    try:
        html = build_presentation(slide_data, title=title, theme=theme, transition=transition)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return {
            "success": True,
            "output": output_path,
            "slides": len(slide_data),
            "size_kb": round(len(html) / 1024, 1)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Kairo Reveal.js Exporter")
    parser.add_argument("--slides", required=True, help="JSON file with slide data")
    parser.add_argument("--out", required=True, help="Output HTML path")
    parser.add_argument("--title", default="Kairo Presentation")
    parser.add_argument("--theme", default="black",
                        choices=["black", "white", "league", "beige", "sky", "night", "serif", "simple", "solarized", "moon"])
    parser.add_argument("--transition", default="fade",
                        choices=["none", "fade", "slide", "convex", "concave", "zoom"])
    args = parser.parse_args()

    with open(args.slides, encoding="utf-8") as f:
        slides = json.load(f)

    result = export_revealjs(slides, args.out, title=args.title,
                             theme=args.theme, transition=args.transition)
    if result["success"]:
        print(f"[OK] Exported {result['slides']} slides → {result['output']} ({result['size_kb']} KB)")
    else:
        print(f"[ERROR] {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
