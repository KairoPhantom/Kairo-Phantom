"""
Opt-in anonymous telemetry for Kairo Phantom.
Collects ONLY: operation counts, latency percentiles, error counts.
NEVER collects: document content, user text, filenames, or any PII.
Opt-in: disabled by default.
"""
import json
import time
import logging
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

log = logging.getLogger("kairo.telemetry")

TELEMETRY_FILE = Path.home() / ".kairo-phantom" / "telemetry.jsonl"
CONFIG_FILE = Path.home() / ".kairo-phantom" / "config.json"


def is_opted_in() -> bool:
    """Check if user has opted into telemetry. Default: False."""
    try:
        config = json.loads(CONFIG_FILE.read_text())
        return config.get("telemetry_enabled", False)
    except Exception:
        return False


def record_operation(domain: str, latency_ms: float, success: bool = True) -> None:
    """
    Record an anonymized operation metric.
    Only fires if user has opted in.
    NON-BLOCKING: writes to local JSONL file only (no network).
    """
    if not is_opted_in():
        return
    entry = {
        "ts": int(time.time()),
        "domain": domain,
        "latency_ms": round(latency_ms, 1),
        "success": success,
    }
    try:
        TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.debug(f"[Telemetry] Write failed: {e}")


def get_summary() -> Dict:
    """Read telemetry file and return summary statistics."""
    if not TELEMETRY_FILE.exists():
        return {"operations": 0, "domains": {}, "avg_latency_ms": 0}
    domain_counts: Dict[str, int] = defaultdict(int)
    latencies: List[float] = []
    try:
        for line in TELEMETRY_FILE.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            domain_counts[entry["domain"]] += 1
            latencies.append(entry["latency_ms"])
    except Exception:
        pass
    return {
        "operations": sum(domain_counts.values()),
        "domains": dict(domain_counts),
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 1),
    }
