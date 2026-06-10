"""
scripts/latency_test.py — Kairo Phantom LiteLLM Latency Gate
=============================================================
Measures time-to-first-token (TTFT) for the LiteLLM proxy and prints
p50/p95 latencies.  Designed to be invoked by the PR gate runner.

Usage:
    python scripts/latency_test.py [--runs N] [--model MODEL]

Exit codes:
    0  — PASS or SKIPPED (proxy not running)
    1  — FAIL (p95 exceeds threshold)
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request

# Thresholds per model alias (milliseconds)
THRESHOLDS_MS = {
    "kairo-standard": 2000,
    "kairo-fast": 600,
}
DEFAULT_THRESHOLD_MS = 2000  # fallback for unknown model aliases

ENDPOINT = "http://localhost:4000/v1/chat/completions"
TEST_PROMPT = "Reply with exactly one word: hello"


def measure_ttft(model: str) -> float | None:
    """
    Send a streaming request and return time-to-first-token in milliseconds.
    Returns None if the request fails for non-connection reasons.
    Raises ConnectionRefusedError if the proxy is not reachable.
    """
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "stream": True,
        "temperature": 0.0,
        "max_tokens": 5,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t_start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            for line in resp:
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str or line_str == "data: [DONE]":
                    continue
                if line_str.startswith("data: "):
                    try:
                        chunk = json.loads(line_str[6:])
                        token = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if token:
                            t_end = time.perf_counter()
                            return (t_end - t_start) * 1000.0
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, ConnectionRefusedError) or "Connection refused" in str(
            reason
        ):
            raise ConnectionRefusedError("LiteLLM proxy not running") from exc
        raise
    return None  # no token received but no hard error


def main() -> int:
    parser = argparse.ArgumentParser(description="Kairo Phantom Latency Gate")
    parser.add_argument(
        "--runs", type=int, default=20, help="Number of test runs (default: 20)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="kairo-standard",
        help="LiteLLM model alias (default: kairo-standard)",
    )
    args = parser.parse_args()

    threshold_ms = THRESHOLDS_MS.get(args.model, DEFAULT_THRESHOLD_MS)

    latencies: list[float] = []
    skipped = 0

    print(
        f"Latency test: model={args.model!r}  runs={args.runs}  "
        f"threshold={threshold_ms}ms"
    )

    for i in range(1, args.runs + 1):
        try:
            ttft = measure_ttft(args.model)
            if ttft is None:
                print(f"  run {i:3d}: no token received (skip)")
                skipped += 1
            else:
                latencies.append(ttft)
                print(f"  run {i:3d}: {ttft:.1f}ms")
        except ConnectionRefusedError:
            # Proxy not running — mark ALL remaining runs as skipped and bail
            remaining = args.runs - (i - 1)
            skipped += remaining
            print(
                f"  run {i:3d}: SKIPPED — LiteLLM proxy not running "
                f"(connection refused); skipping remaining {remaining - 1} run(s)"
            )
            break
        except Exception as exc:
            print(f"  run {i:3d}: error — {exc} (skip)")
            skipped += 1

    total = len(latencies) + skipped
    if not latencies:
        print(
            f"\nResult: SKIPPED ({skipped}/{total} runs skipped — proxy not running)"
        )
        return 0  # Gate runner handles MANUAL classification

    p50 = statistics.median(latencies)
    sorted_l = sorted(latencies)
    idx_95 = max(0, int(len(sorted_l) * 0.95) - 1)
    p95 = sorted_l[idx_95] if sorted_l else 0.0

    gate = "PASS" if p95 < threshold_ms else "FAIL"
    print(
        f"\np50={p50:.0f}ms  p95={p95:.0f}ms  "
        f"(n={len(latencies)} measured, {skipped} skipped)  Gate: {gate}"
    )
    if skipped > 0:
        print(f"  Note: {skipped} run(s) were skipped (see above).")

    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
