#!/usr/bin/env python3
"""
kairo-effects CLI entry point — can also be used standalone.
Usage: python effects_engine.py --effect cloth_tear --output out.mp4 --from a.png --to b.png --duration 1200
"""
import sys
import argparse
import os
import subprocess
import json
from pathlib import Path

EFFECTS = [
    "cloth_tear", "glitch_reveal", "gl_wipe_left", "crosszoom",
    "gl_cube", "gl_ripple", "particle_disintegrate", "cinema_fade", "ascii_dissolve"
]

GL_TRANSITIONS_MAP = {
    "gl_wipe_left": "wipeLeft",
    "crosszoom": "crosszoom",
    "gl_cube": "cube",
    "gl_ripple": "ripple",
}


def render_ffmpeg_xfade(from_image: str, to_image: str, output: str, effect: str, duration_ms: int):
    """FFmpeg xfade-based transition (no Puppeteer required)."""
    dur = duration_ms / 1000.0
    xfade_map = {
        "cinema_fade": "fade",
        "glitch_reveal": "pixelize",
        "cloth_tear": "wipeleft",
        "gl_wipe_left": "wipeleft",
        "crosszoom": "zoomin",
        "gl_cube": "cube",
        "gl_ripple": "radial",
        "particle_disintegrate": "dissolve",
        "ascii_dissolve": "fadeblack",
    }
    xfade = xfade_map.get(effect, "fade")

    # Create 2-second still images then xfade
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", from_image or "black.png", "-t", "2",
        "-loop", "1", "-i", to_image or "white.png", "-t", "2",
        "-filter_complex",
        f"[0][1]xfade=transition={xfade}:duration={dur}:offset=1,format=yuv420p",
        "-c:v", "libx264", "-r", "30",
        output
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ Rendered {effect} → {output}")
            return True
        else:
            print(f"❌ FFmpeg error: {result.stderr[:300]}", file=sys.stderr)
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found. Install: https://ffmpeg.org/download.html", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg timeout", file=sys.stderr)
        return False


def render_puppeteer(from_image: str, to_image: str, output: str, effect: str, duration_ms: int):
    """Puppeteer-based WebGL transition rendering."""
    script_dir = Path(__file__).parent
    node_script = script_dir / "render_transition.js"

    if not node_script.exists():
        return False

    try:
        result = subprocess.run(
            ["node", str(node_script),
             "--effect", effect,
             "--from", from_image,
             "--to", to_image,
             "--output", output,
             "--duration", str(duration_ms)],
            capture_output=True, text=True, timeout=60,
            cwd=str(script_dir)
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def render_effect(effect: str, from_image: str, to_image: str, output: str, duration_ms: int = 1200) -> bool:
    """Render a transition effect. Tries Puppeteer first, falls back to FFmpeg xfade."""
    if effect not in EFFECTS:
        print(f"❌ Unknown effect: {effect}. Available: {', '.join(EFFECTS)}", file=sys.stderr)
        return False

    print(f"🎬 Rendering: {effect} ({duration_ms}ms) → {output}")

    # Try Puppeteer WebGL first
    if render_puppeteer(from_image, to_image, output, effect, duration_ms):
        return True

    print("⚠️  Puppeteer unavailable, falling back to FFmpeg xfade...")
    return render_ffmpeg_xfade(from_image, to_image, output, effect, duration_ms)


def list_effects() -> list:
    return EFFECTS


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kairo Cinematic Effects Engine")
    parser.add_argument("--effect", choices=EFFECTS, default="cinema_fade")
    parser.add_argument("--from", dest="from_image", default="")
    parser.add_argument("--to", dest="to_image", default="")
    parser.add_argument("--output", default="transition.mp4")
    parser.add_argument("--duration", type=int, default=1200)
    parser.add_argument("--list", action="store_true", help="List available effects")

    args = parser.parse_args()

    if args.list:
        print(json.dumps({"effects": list_effects()}, indent=2))
        sys.exit(0)

    success = render_effect(args.effect, args.from_image, args.to_image, args.output, args.duration)
    sys.exit(0 if success else 1)
