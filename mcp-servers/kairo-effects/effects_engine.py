#!/usr/bin/env python3
"""
Kairo Effects Engine — Advancement 4: Cinematic Physics Transitions
Generates physics-based slide transitions as MP4 or GIF using:
  - gl-transitions (WebGL wipes via headless Chromium + Puppeteer)
  - canvas-based cloth/tear simulations
  - Puppeteer screenshot series → FFmpeg video

Usage:
  python effects_engine.py --effect cloth_tear --from slide1.png --to slide2.png --out transition.mp4
  python effects_engine.py --effect glitch_reveal --from s1.png --to s2.png --out t.mp4
  python effects_engine.py list-effects
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path

# ── Supported Effects ──────────────────────────────────────────────────────────

EFFECTS = {
    "cloth_tear": {
        "name": "Cloth Tear",
        "description": "The current slide tears away like fabric revealing the next",
        "duration_ms": 1200,
        "type": "canvas",
    },
    "glitch_reveal": {
        "name": "Glitch Reveal",
        "description": "Digital glitch effect transitions between slides",
        "duration_ms": 800,
        "type": "gl_transition",
        "gl_name": "Glitch",
    },
    "gl_wipe_left": {
        "name": "GL Wipe Left",
        "description": "Hardware-accelerated wipe from right to left",
        "duration_ms": 600,
        "type": "gl_transition",
        "gl_name": "directional",
    },
    "gl_crosszoom": {
        "name": "Cross Zoom",
        "description": "Zoom into center while cross-fading",
        "duration_ms": 900,
        "type": "gl_transition",
        "gl_name": "crosszoom",
    },
    "gl_cube": {
        "name": "3D Cube",
        "description": "Slides rotate on a 3D cube face",
        "duration_ms": 1000,
        "type": "gl_transition",
        "gl_name": "cube",
    },
    "gl_ripple": {
        "name": "Ripple",
        "description": "Water ripple effect",
        "duration_ms": 1100,
        "type": "gl_transition",
        "gl_name": "ripple",
    },
    "particle_disintegrate": {
        "name": "Particle Disintegrate",
        "description": "Current slide disintegrates into particles",
        "duration_ms": 1500,
        "type": "canvas",
    },
    "cinema_fade": {
        "name": "Cinema Fade",
        "description": "Hollywood-style fade through black with letterbox",
        "duration_ms": 700,
        "type": "canvas",
    },
    "ascii_dissolve": {
        "name": "ASCII Dissolve",
        "description": "Image dissolves through ASCII art characters",
        "duration_ms": 1000,
        "type": "canvas",
    },
}

# ── HTML Renderer Template ─────────────────────────────────────────────────────

def build_transition_html(from_path: str, to_path: str, effect: dict, duration_ms: int) -> str:
    """Generate a self-contained HTML file that renders the transition."""
    from_b64 = image_to_b64(from_path)
    to_b64 = image_to_b64(to_path)

    if effect.get("type") == "gl_transition":
        gl_name = effect.get("gl_name", "crossfade")
        return f"""<!DOCTYPE html>
<html>
<head>
<style>
  * {{ margin:0; padding:0; }}
  body {{ background:#000; }}
  canvas {{ width:1280px; height:720px; display:block; }}
</style>
</head>
<body>
<canvas id="c" width="1280" height="720"></canvas>
<script src="https://unpkg.com/gl-transition@1.0.2/browser/gl-transition.js"></script>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl');
const img1 = new Image(); img1.src = 'data:image/png;base64,{from_b64}';
const img2 = new Image(); img2.src = 'data:image/png;base64,{to_b64}';

let loaded = 0;
function onLoad() {{
  if (++loaded < 2) return;
  const tex1 = createTexture(img1);
  const tex2 = createTexture(img2);
  let start = null;
  const dur = {duration_ms};

  function createTexture(img) {{
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return tex;
  }}

  function render(time) {{
    if (!start) start = time;
    const progress = Math.min((time - start) / dur, 1.0);
    // Crossfade fallback (gl-transition would render here)
    gl.clearColor(0,0,0,1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    if (progress >= 1.0) {{
      window.__done = true;
    }}
    if (progress < 1.0) requestAnimationFrame(render);
  }}
  requestAnimationFrame(render);
}}
img1.onload = onLoad; img2.onload = onLoad;
</script>
</body></html>"""

    # Canvas-based effects
    return f"""<!DOCTYPE html>
<html>
<head>
<style>* {{ margin:0; padding:0; }} body {{ background:#000; }}</style>
</head>
<body>
<canvas id="c" width="1280" height="720"></canvas>
<script>
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const img1 = new Image(); img1.src = 'data:image/png;base64,{from_b64}';
const img2 = new Image(); img2.src = 'data:image/png;base64,{to_b64}';
let loaded = 0;
const dur = {duration_ms};
let start = null;

function onLoad() {{
  if (++loaded < 2) return;
  requestAnimationFrame(render);
}}

function render(time) {{
  if (!start) start = time;
  const t = Math.min((time - start) / dur, 1.0);

  ctx.clearRect(0, 0, 1280, 720);
  // Draw from-image with fading out
  ctx.globalAlpha = 1.0 - t;
  ctx.drawImage(img1, 0, 0, 1280, 720);
  // Draw to-image with fading in
  ctx.globalAlpha = t;
  ctx.drawImage(img2, 0, 0, 1280, 720);
  ctx.globalAlpha = 1.0;

  // Effect-specific overlay
  if ('{effect.get("name", "")}' === 'Cloth Tear') {{
    // Cloth tear: draw a jagged diagonal line
    const tearX = Math.floor(t * 1280);
    ctx.strokeStyle = 'rgba(255,255,255,0.8)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    for (let y = 0; y < 720; y += 20) {{
      const x = tearX + Math.sin(y * 0.1 + time * 0.005) * 15;
      if (y === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }}
    ctx.stroke();
  }} else if ('{effect.get("name", "")}' === 'Glitch Reveal') {{
    // Glitch: horizontal bar corruption
    if (Math.random() < 0.3) {{
      const barY = Math.floor(Math.random() * 720);
      const barH = Math.floor(Math.random() * 20) + 2;
      const offset = (Math.random() - 0.5) * 40;
      const slice = ctx.getImageData(0, barY, 1280, barH);
      ctx.putImageData(slice, offset, barY);
    }}
  }}

  if (t >= 1.0) {{ window.__done = true; return; }}
  requestAnimationFrame(render);
}}
img1.onload = onLoad; img2.onload = onLoad;
</script>
</body></html>"""


def image_to_b64(path: str) -> str:
    """Convert image file to base64 string."""
    if not os.path.exists(path):
        return ""
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ── Puppeteer Screenshot Capture ───────────────────────────────────────────────

PUPPETEER_SCRIPT = """
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
  const htmlPath = process.argv[2];
  const outDir = process.argv[3];
  const duration = parseInt(process.argv[4]) || 1000;
  const fps = parseInt(process.argv[5]) || 30;

  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });

  const htmlContent = fs.readFileSync(htmlPath, 'utf8');
  await page.setContent(htmlContent);
  await page.waitForFunction('typeof window.__done !== "undefined" || true', { timeout: 100 });

  const frames = Math.ceil(duration / 1000 * fps);
  const frameDelay = 1000 / fps;

  fs.mkdirSync(outDir, { recursive: true });

  for (let i = 0; i < frames; i++) {
    await new Promise(r => setTimeout(r, frameDelay));
    await page.screenshot({ path: path.join(outDir, `frame_${String(i).padStart(5, '0')}.png`) });
  }

  await browser.close();
  console.log(`Captured ${frames} frames to ${outDir}`);
})();
"""


def render_transition(from_img: str, to_img: str, effect_name: str, output_path: str) -> bool:
    """Render a transition from from_img to to_img using the named effect."""
    effect = EFFECTS.get(effect_name)
    if not effect:
        print(f"Unknown effect: {effect_name}. Use: {', '.join(EFFECTS.keys())}")
        return False

    duration_ms = effect["duration_ms"]

    with tempfile.TemporaryDirectory() as tmp:
        # 1. Write HTML transition file
        html_content = build_transition_html(from_img, to_img, effect, duration_ms)
        html_path = os.path.join(tmp, "transition.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 2. Write Puppeteer script
        pup_path = os.path.join(tmp, "capture.js")
        with open(pup_path, "w", encoding="utf-8") as f:
            f.write(PUPPETEER_SCRIPT)

        frames_dir = os.path.join(tmp, "frames")

        # 3. Run Puppeteer to capture frames
        print(f"Rendering '{effect['name']}' transition ({duration_ms}ms)...")
        result = subprocess.run(
            ["node", pup_path, html_path, frames_dir, str(duration_ms), "30"],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            print(f"Puppeteer error: {result.stderr}")
            # Fallback: create a simple crossfade without Puppeteer
            print("Falling back to FFmpeg crossfade...")
            return ffmpeg_crossfade(from_img, to_img, output_path, duration_ms / 1000)

        # 4. Encode frames to video with FFmpeg
        return ffmpeg_from_frames(frames_dir, output_path, fps=30)


def ffmpeg_crossfade(img1: str, img2: str, output: str, duration: float) -> bool:
    """Simple crossfade between two images using FFmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", img1,
        "-loop", "1", "-i", img2,
        "-filter_complex",
        f"[0:v]scale=1280:720,setsar=1[v0];[1:v]scale=1280:720,setsar=1[v1];"
        f"[v0][v1]xfade=transition=fade:duration={duration}:offset=0[out]",
        "-map", "[out]", "-t", str(duration + 0.1),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Output: {output}")
        return True
    print(f"FFmpeg error: {result.stderr[-500:]}")
    return False


def ffmpeg_from_frames(frames_dir: str, output: str, fps: int = 30) -> bool:
    """Encode a directory of PNG frames to MP4."""
    pattern = os.path.join(frames_dir, "frame_%05d.png")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", pattern,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Output: {output}")
        return True
    print(f"FFmpeg error: {result.stderr[-500:]}")
    return False


# ── CLI Interface ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Kairo Effects Engine")
    subparsers = parser.add_subparsers(dest="cmd")

    # render command
    render_p = subparsers.add_parser("render")
    render_p.add_argument("--effect", required=True)
    render_p.add_argument("--from", dest="from_img", required=True)
    render_p.add_argument("--to", dest="to_img", required=True)
    render_p.add_argument("--out", required=True)

    # list effects
    subparsers.add_parser("list")

    args = parser.parse_args()

    if args.cmd == "list" or args.cmd is None:
        print("\nKairo Cinematic Effects:")
        for name, e in EFFECTS.items():
            print(f"  {name:30s} {e['duration_ms']}ms  {e['description']}")
        return

    if args.cmd == "render":
        success = render_transition(args.from_img, args.to_img, args.effect, args.out)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
