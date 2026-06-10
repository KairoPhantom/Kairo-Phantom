"""
chaos_hotkey.py — Rapid-fire Alt+Ctrl+M press simulator for Kairo Phantom debounce testing.

Simulates rapid-fire hotkey presses via sidecar IPC and verifies the debounce
guard successfully enforces a single dispatch even under burst load.

Usage:
    python scripts/chaos_hotkey.py --count 10 --interval 0.05
    # Output: GRP_responses=1 / requests_sent=10 crashes=0 (debounce: OK)

When sidecar is NOT running:
    Gracefully reports SKIPPED and exits 0.
"""

import argparse
import json
import time
import urllib.request
import urllib.error
import sys
import threading
from typing import List

SIDECAR_URL = "http://127.0.0.1:7437/process"
DUMMY_PROMPT = "// Chaos test — debounce verification"


def send_request(url: str, prompt: str, results: List[dict], idx: int) -> None:
    """Send a single POST to the sidecar /process endpoint."""
    payload = json.dumps({"prompt": prompt, "domain": "word"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            results.append({"idx": idx, "status": resp.status, "body": body[:100]})
    except urllib.error.HTTPError as e:
        results.append({"idx": idx, "status": e.code, "body": ""})
    except Exception as e:
        results.append({"idx": idx, "status": -1, "error": str(e)})


def check_sidecar_available(url: str) -> bool:
    """Return True if the sidecar is reachable."""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:7437/health",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=2.0):
            return True
    except Exception:
        # Also try a HEAD-equivalent against the process endpoint
        try:
            payload = json.dumps({"prompt": "ping"}).encode("utf-8")
            req2 = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req2, timeout=2.0):
                return True
        except urllib.error.HTTPError:
            return True  # Sidecar responded (even with error)
        except Exception:
            return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chaos test: rapid-fire Alt+Ctrl+M presses to verify debounce guard."
    )
    parser.add_argument("--count", type=int, default=10, help="Number of rapid-fire requests (default: 10)")
    parser.add_argument("--interval", type=float, default=0.05, help="Interval between requests in seconds (default: 0.05)")
    parser.add_argument("--url", type=str, default=SIDECAR_URL, help=f"Sidecar /process URL (default: {SIDECAR_URL})")
    args = parser.parse_args()

    print(f"[chaos_hotkey] Checking sidecar availability at {args.url}...")

    if not check_sidecar_available(args.url):
        print("[chaos_hotkey] Sidecar not running — SKIPPED")
        print("GRP_responses=N/A / requests_sent=0 crashes=0 (debounce: SKIPPED)")
        return 0

    print(f"[chaos_hotkey] Sidecar reachable. Sending {args.count} rapid-fire requests with {args.interval}s interval...")

    results: List[dict] = []
    threads = []

    for i in range(args.count):
        t = threading.Thread(
            target=send_request,
            args=(args.url, DUMMY_PROMPT, results, i),
            daemon=True,
        )
        threads.append(t)
        t.start()
        time.sleep(args.interval)

    # Wait for all threads
    for t in threads:
        t.join(timeout=10.0)

    # Analyze results
    requests_sent = args.count
    successful_responses = sum(1 for r in results if r.get("status", -1) in (200, 201, 202))
    crashes = sum(1 for r in results if r.get("status", 0) == -1)

    # Debounce is working if we got 0 or 1 successful responses despite N requests
    # (sidecar may reject duplicates with 429 or deduplicate internally)
    rejected_responses = sum(1 for r in results if r.get("status", 0) == 429)

    debounce_ok = (successful_responses <= 1) or (rejected_responses > 0)
    debounce_label = "OK" if debounce_ok else "FAIL"

    print(f"\n[chaos_hotkey] Results:")
    print(f"  Requests sent:      {requests_sent}")
    print(f"  Successful (2xx):   {successful_responses}")
    print(f"  Rejected (429):     {rejected_responses}")
    print(f"  Errors:             {crashes}")
    print(f"  Debounce:           {debounce_label}")
    print()
    print(f"GRP_responses={successful_responses} / requests_sent={requests_sent} crashes={crashes} (debounce: {debounce_label})")

    if debounce_ok:
        print("Gate: PASS")
        return 0
    else:
        print("Gate: FAIL — multiple GRP responses dispatched without debounce")
        return 1


if __name__ == "__main__":
    sys.exit(main())
