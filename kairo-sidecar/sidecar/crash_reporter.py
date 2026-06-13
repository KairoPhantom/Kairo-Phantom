"""
Crash reporter for Kairo Phantom Python sidecar.
On unhandled exception: writes structured JSON to ~/.kairo-phantom/crashes/
NEVER sends data externally.
"""
import sys
import json
import traceback
import platform
import time
import logging
from pathlib import Path

log = logging.getLogger("kairo.crash-reporter")

CRASH_DIR = Path.home() / ".kairo-phantom" / "crashes"


def install_crash_handler() -> None:
    """Install as sys.excepthook to catch all unhandled exceptions."""
    sys.excepthook = _crash_handler
    log.debug("[CrashReporter] Crash handler installed")


def _crash_handler(exc_type, exc_value, exc_tb) -> None:
    """Write crash report and print user-friendly message."""
    crash_path = _write_crash_report(exc_type, exc_value, exc_tb)
    print(f"\n[Kairo Phantom] An unexpected error occurred.", file=sys.stderr)
    print(f"Crash report saved to: {crash_path}", file=sys.stderr)
    print("Please report this at: https://github.com/KairoPhantom/Kairo-Phantom/issues", file=sys.stderr)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


import re

def scrub_pii(text: str) -> str:
    """Scrub common PII patterns (email, phone, SSN) from a string."""
    # Scrub email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
    # Scrub phone numbers (simple pattern)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    # Scrub typical SSN
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    return text


def _write_crash_report(exc_type, exc_value, exc_tb) -> Path:
    """Write structured JSON crash report with PII scrubbed."""
    CRASH_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    crash_file = CRASH_DIR / f"crash_{timestamp}.json"
    
    msg = scrub_pii(str(exc_value))
    tb_list = traceback.format_exception(exc_type, exc_value, exc_tb)
    tb_scrubbed = [scrub_pii(line) for line in tb_list]
    
    report = {
        "timestamp": timestamp,
        "version": "3.9.0",
        "platform": {
            "os": platform.system(),
            "os_version": platform.version(),
            "python": platform.python_version(),
            "machine": platform.machine(),
        },
        "exception": {
            "type": exc_type.__name__ if exc_type else "Unknown",
            "message": msg,
            "traceback": tb_scrubbed,
        },
    }
    try:
        crash_file.write_text(json.dumps(report, indent=2, default=str))
        log.info(f"[CrashReporter] Crash report written to {crash_file}")
    except Exception as e:
        log.error(f"[CrashReporter] Failed to write crash report: {e}")
    return crash_file


def write_manual_crash(message: str, extra: dict = None) -> Path:
    """Manually record a non-fatal error as a crash report."""
    report = {
        "timestamp": int(time.time()),
        "version": "3.9.0",
        "type": "manual",
        "message": message,
        "extra": extra or {},
    }
    CRASH_DIR.mkdir(parents=True, exist_ok=True)
    crash_file = CRASH_DIR / f"crash_{int(time.time())}.json"
    crash_file.write_text(json.dumps(report, indent=2))
    return crash_file
