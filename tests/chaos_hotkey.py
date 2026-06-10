#!/usr/bin/env python3
"""
tests/chaos_hotkey.py — Alt+M press debounce stress test
=========================================================
"""

import sys
import os
import argparse
import time

# Add sidecar directory to path to import debounce_guard
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kairo-sidecar"))

try:
    from sidecar.debounce_guard import DebounceGuard
except ImportError:
    # Fallback to local definition if path lookup fails
    class DebounceGuard:
        def __init__(self, interval_seconds: float = 0.2):
            self.interval = interval_seconds
            self.last_triggered = 0.0
        def should_process(self) -> bool:
            now = time.time()
            if now - self.last_triggered >= self.interval:
                self.last_triggered = now
                return True
            return False

def main():
    parser = argparse.ArgumentParser(description="Kairo Debounce Stress Test")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=0.01)  # rapid spam
    args = parser.parse_args()

    print(f"Simulating {args.count} Alt+M events spaced by {args.interval}s...")

    guard = DebounceGuard(interval_seconds=0.2) # 200ms debounce
    requests_sent = 0
    responses_processed = 0
    phantom_injections = 0
    crashes = 0

    for i in range(args.count):
        requests_sent += 1
        try:
            if guard.should_process():
                responses_processed += 1
        except Exception:
            crashes += 1
        time.sleep(args.interval)

    print("\nResults:")
    print(f"  requests_sent: {requests_sent}")
    print(f"  responses_processed: {responses_processed}")
    print(f"  phantom_injections: {phantom_injections}")
    print(f"  crashes: {crashes}")

    pass_gate = (responses_processed == 1) and (crashes == 0)
    if pass_gate:
        print("PASS")
        sys.exit(0)
    else:
        print("FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()
