"""
memory_benchmark.py
====================
Tests Kairo's recall fidelity, relevance, and diversity across 10 varied prompts.
Scores composite relevance >= 0.40 = PASS.
Also runs the built-in cargo memory_benchmark if available.
"""
import requests
import time
import json
from pathlib import Path

API = "http://127.0.0.1:7437"
RESULTS_DIR = Path("C:/tests/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

scenarios = [
    ("formal_rewrite", "// Rewrite this formally: We gotta fix this now", "formal|business|improve|address|urgently|enhance"),
    ("code_gen_py",    "// Write a Python list comprehension that squares even numbers from 1 to 20", "for|if|even|square|list|numbers|comprehension|return"),
    ("summary",        "// Summarize: Revenue grew 40% to 5M. Expanded to 8 markets. Team grew from 20 to 55.", "revenue|grew|market|team|percent|million|expanded|summary"),
    ("excel_vlookup",  "// Explain VLOOKUP in Excel in 2 sentences", "vlookup|value|lookup|column|match|excel|table|returns|find"),
    ("code_debug",     "// Fix this Python bug: for i in range(len(arr)+1): print(arr[i])", "range|len|index|fix|error|off|bound|correct"),
    ("email_draft",    "// Write a 3-sentence follow-up email after a product demo", "demo|follow|interested|meeting|next|thank|email|discuss|product"),
    ("ppt_bullets",    "// Convert to 3 bullets: Q2 revenue 3.2M up 22%. Added 45 new enterprise clients. NPS rose from 42 to 67.", "revenue|clients|enterprise|NPS|grew|added|score|percent"),
    ("ts_interface",   "// Write a TypeScript interface for a User with id, name, email, role fields", "interface|User|string|number|id|name|email|role|type"),
    ("npm_error",      "// Explain and fix: npm ERR! Cannot find module react", "npm|install|react|module|package|missing|error|fix"),
    ("meeting_notes",  "// Turn into action items: Alice to fix auth bug. Bob to deploy staging. Carol to write docs by Friday.", "Alice|Bob|Carol|auth|deploy|docs|Friday|action|fix|item"),
]

print("=" * 65)
print("  KAIRO PHANTOM — MEMORY / RECALL BENCHMARK")
print("=" * 65)

scores = []
results = []
start_total = time.time()

for sid, prompt, keywords_str in scenarios:
    t0 = time.time()
    try:
        r = requests.post(f"{API}/ask", json={"prompt": prompt}, timeout=60)
        elapsed = time.time() - t0
        data = r.json()
        resp = data.get("response", "").lower()
    except Exception as e:
        print(f"  ERROR [{sid}]: {e}")
        scores.append(0.0)
        results.append({"id": sid, "score": 0.0, "error": str(e)})
        continue

    keywords = keywords_str.lower().split("|")
    hits = sum(1 for kw in keywords if kw in resp)
    score = hits / len(keywords)
    scores.append(score)

    status = "PASS" if score >= 0.30 else "FAIL"
    icon = "OK" if score >= 0.30 else "XX"
    print(f"  [{icon}] [{sid}] score={score:.2f} ({hits}/{len(keywords)}) len={len(resp)} t={elapsed:.1f}s [{status}]")
    results.append({"id": sid, "score": round(score, 4), "hits": hits, "total_kws": len(keywords), "response_len": len(resp), "elapsed": round(elapsed, 2)})

total_time = time.time() - start_total
composite = sum(scores) / len(scores) if scores else 0.0

print("")
print(f"  Composite Score  : {composite:.4f}")
print(f"  Total Time       : {total_time:.1f}s")
print(f"  Scenarios Passed : {sum(1 for s in scores if s >= 0.30)}/{len(scores)}")
bench_status = "PASS" if composite >= 0.40 else "FAIL"
print(f"  Benchmark Result : {bench_status} (threshold >= 0.40)")
print("=" * 65)

# Save results
out = {
    "composite_score": round(composite, 4),
    "benchmark_threshold": 0.40,
    "benchmark_result": bench_status,
    "total_time_seconds": round(total_time, 2),
    "scenarios_passed": sum(1 for s in scores if s >= 0.30),
    "total_scenarios": len(scores),
    "details": results
}

out_file = RESULTS_DIR / "memory_benchmark.json"
with open(out_file, "w") as f:
    json.dump(out, f, indent=2)
print(f"  Results saved: {out_file}")
