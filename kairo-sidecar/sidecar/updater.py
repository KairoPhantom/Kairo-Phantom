"""
Auto-update checker for Kairo Phantom.
Checks GitHub releases API on startup (non-blocking).
Never downloads automatically — only prompts user.
"""
import json
import threading
import logging
from typing import Optional, Tuple
from urllib import request, error

log = logging.getLogger("kairo.updater")

CURRENT_VERSION = "3.9.0"
GITHUB_RELEASES_API = "https://api.github.com/repos/Kartik24Hulmukh/Kairo-Phantom/releases/latest"


def check_for_update() -> Optional[Tuple[str, str]]:
    """
    Check GitHub releases for a newer version.
    Returns (latest_version, download_url) if newer available, else None.
    Times out in 5 seconds.
    """
    try:
        req = request.Request(
            GITHUB_RELEASES_API,
            headers={"User-Agent": f"KairoPhantom/{CURRENT_VERSION}"},
        )
        with request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        latest = data.get("tag_name", "").lstrip("v")
        download_url = data.get("html_url", "")
        if latest and latest != CURRENT_VERSION and _is_newer(latest, CURRENT_VERSION):
            log.info(f"[Updater] New version available: {latest}")
            return (latest, download_url)
        return None
    except (error.URLError, json.JSONDecodeError, Exception) as e:
        log.debug(f"[Updater] Update check failed (offline or error): {e}")
        return None


def _is_newer(a: str, b: str) -> bool:
    """Return True if version a > version b."""
    try:
        return tuple(int(x) for x in a.split(".")) > tuple(int(x) for x in b.split("."))
    except ValueError:
        return False


def check_for_update_async(callback) -> None:
    """Run update check in background thread, call callback with result."""
    def _run():
        result = check_for_update()
        if result:
            callback(result)
    threading.Thread(target=_run, daemon=True, name="kairo-updater").start()
