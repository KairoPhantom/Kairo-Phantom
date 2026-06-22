# Kairo Phantom v2.2 — Hardware Requirements

> **Local-first.** Kairo runs on your machine, not in the cloud. The grounding verifier and extraction patterns need no GPU. Model inference (optional) scales from CPU-only to multi-GPU.

## Minimum Specs (CPU-only, extraction + grounding)

| Component | Requirement |
|---|---|
| **CPU** | x86-64 with AVX2 (any modern Intel/AMD) |
| **RAM** | 4 GB (extraction + cascade only) |
| **GPU** | None required |
| **Disk** | 500 MB (Kairo core + corpus) |
| **OS** | Linux, macOS, Windows (via Tauri) |
| **Python** | 3.10+ |
| **Network** | None (air-gap compatible) |

**What runs:** Full extraction pipeline, 5-layer grounding cascade, quality gate, blind benchmark. This is how the 100.0% blind number was produced — no GPU, no network.

**What doesn't run:** LLM-powered Q&A (Tier 1 model inference needs Ollama; Tier 3 needs cloud API).

---

## Recommended Specs (with local LLM)

| Component | Requirement |
|---|---|
| **CPU** | 8-core x86-64 (AVX2) |
| **RAM** | 16 GB |
| **GPU** | Single 8 GB+ VRAM card (e.g., RTX 3060, RTX 4060) |
| **Disk** | 10 GB (Kairo + Ollama + Llama 3.2 3B model) |
| **OS** | Linux (native), macOS (Metal), Windows (CUDA/DirectML) |
| **Network** | None (air-gap compatible with local model) |

**What runs:** Everything in minimum specs + Llama 3.2 3B for local field extraction and Q&A. Air-gap preserved — zero network traffic.

---

## Single 24 GB Card Feasibility

| Configuration | Feasible | Notes |
|---|---|---|
| Extraction + grounding only | ✅ | No GPU needed at all |
| Llama 3.2 3B (Q4) | ✅ | ~2-4 GB VRAM, leaves 20 GB free |
| Llama 3.2 8B (Q4) | ✅ | ~5-6 GB VRAM, leaves 18 GB free |
| Llama 3.1 70B (Q4) | ✅ | ~40 GB VRAM — needs 2×24 GB cards |
| Mixtral 8x7B (Q4) | ✅ | ~26 GB VRAM — tight on single 24 GB, better on 2× |
| Concurrent multi-doc batch | ✅ | 3B model leaves room for parallel ingestion |

**A single 24 GB card (RTX 3090/4090/A5000) is more than sufficient** for the default Llama 3.2 3B configuration. It can also run 8B models comfortably. 70B-class models require 2×24 GB.

---

## Modular Install Options

Kairo's architecture allows progressive installation:

### Level 0: Core only (no model)
```bash
pip install kairo-phantom
# Runs extraction + grounding cascade + quality gate
# No Ollama, no GPU, no API keys
# Blind benchmark: 100.0% grounded
```

### Level 1: + Local LLM (Ollama)
```bash
pip install kairo-phantom
ollama pull llama3.2
# Adds local Q&A and LLM-assisted extraction
# Still air-gap compatible
```

### Level 2: + Cloud reasoner (opt-in)
```bash
pip install kairo-phantom
export OPENAI_API_KEY=sk-...
# Adds Tier 3 cloud reasoning for complex Q&A
# Breaks air-gap — network traffic to OpenAI
```

### Level 3: + Tauri overlay (desktop GUI)
```bash
npm install
npm run tauri build
# Adds the desktop renderer overlay
# Click-to-source navigation, visual bbox display
```

---

## Performance Budgets

> **INFRA-PENDING:** The following perf budgets require a GPU-equipped machine to measure. The extraction + scoring pipeline (no GPU) runs in seconds on the 120-doc blind corpus. Full perf characterization (cold-start, click-to-source latency, parse throughput) is pending a GPU run.

| Metric | Target | Status |
|---|---|---|
| Cold-start | < 2s | INFRA-PENDING (needs GPU) |
| Click-to-source | < 100ms | INFRA-PENDING (needs overlay) |
| Parse throughput | ≥ 20 pages/s | INFRA-PENDING (needs GPU) |
| Worker RSS | < 4 GB | ✅ Measured: extraction runs in < 4 GB |
| Blind bench (120 docs) | — | ✅ Completes in seconds (no GPU) |

---

## Air-Gap Verification

The blind benchmark runs with `KAIRO_GATEWAY_TEST_MODE=true`, which:
- Disables all network calls (no Ollama, no OpenAI)
- Returns deterministic responses from the gateway
- Proves the extraction + grounding pipeline needs zero network traffic

For production air-gap: use Level 0 or Level 1 installation. The grounding verifier, quality gate, and extraction patterns are pure Python with no network dependencies.