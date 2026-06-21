# Kairo Phantom — Hardware Matrix & Graceful Degradation

**Last updated:** 2026-06-22

This document specifies exactly what hardware is required to run Kairo Phantom
and how the tool degrades gracefully on weaker setups. Every claim here is
backed by `scripts/hardware_check.py`, which probes real system resources.

---

## Hardware Tiers

### Tier 1: Minimum (CPU-only)

| Requirement | Value |
|:---|:---|
| CPU | Any x86_64 or ARM64, 4+ cores |
| RAM | **8 GB** minimum |
| GPU | Not required |
| VRAM | N/A |
| Disk | 10 GB free (models + LanceDB index) |
| OS | macOS 12+, Windows 10+, Linux (Ubuntu 20.04+) |

**What this tier enables:**
- Exact grounding (NORMALIZE → EXACT)
- Fuzzy grounding (Levenshtein ≥ 0.92)
- Semantic grounding (degraded — bag-of-words hash embeddings, no neural model)
- Local LLM: 7B model only (Q4_K_M quantization, CPU inference via llama.cpp)
- OCR/layout: Docling (CPU mode, slower)
- Embeddings: fastembed (CPU mode)

**What this tier disables:**
- ❌ Visual retrieval (ColQwen2/ColPali) — requires GPU with ≥16 GB VRAM
- ❌ Local LLM 13B — requires GPU with ≥10 GB VRAM
- ❌ Local LLM 34B — requires GPU with ≥24 GB VRAM
- ❌ DeepSeek-OCR2 — requires GPU

**Degradation message when no GPU is detected:**
> `visual retrieval disabled — CPU mode, text-only grounding`

### Tier 2: Recommended (GPU)

| Requirement | Value |
|:---|:---|
| CPU | Any x86_64 or ARM64, 8+ cores |
| RAM | **16 GB** minimum |
| GPU | NVIDIA with CUDA, AMD with ROCm, or Apple Silicon |
| VRAM | **16 GB** minimum |
| Disk | 20 GB free (larger models + visual retrieval index) |
| OS | macOS 12+, Windows 10+, Linux (Ubuntu 20.04+) |

**What this tier enables:**
- ✅ Visual retrieval (ColQwen2/ColPali) — bounding-box-level visual grounding
- ✅ Semantic grounding (neural embeddings via fastembed/model2vec)
- ✅ Fuzzy grounding (Levenshtein ≥ 0.92)
- ✅ Exact grounding (NORMALIZE → EXACT)
- ✅ Local LLM: up to 34B model (GPU inference)
- ✅ OCR/layout: Docling + DeepSeek-OCR2 (GPU accelerated)
- ✅ Embeddings: fastembed + model2vec (GPU accelerated)

**What this tier disables:**
- Nothing — all features available.

### Tier 3: Insufficient (below minimum)

| Condition | Behavior |
|:---|:---|
| RAM < 8 GB | Kairo refuses to load any local model. Prints precise message. |
| No GPU + RAM < 8 GB | Only exact + fuzzy grounding available. No LLM, no OCR. |

**Guardrail message:**
> `INSUFFICIENT RAM: X GB detected, minimum 8 GB required. Kairo cannot run the local LLM. Upgrade RAM or use BYO-key cloud mode.`

---

## Graceful Degradation Model

Kairo never crashes with an OOM. Before loading any model, `scripts/hardware_check.py`
runs a pre-flight check:

```
check_model_loadable(model_size, profile) → (can_load, message)
```

If the check fails, Kairo prints a precise diagnostic and falls back to a
smaller model or text-only grounding. The user is never left with a crash.

### Degradation Cascade

```
GPU + 16GB VRAM → visual retrieval + 34B LLM + neural embeddings
     ↓ (no GPU or < 16GB VRAM)
CPU + 8GB RAM → text-only grounding + 7B LLM + hash embeddings
     ↓ (RAM < 8GB)
INSUFFICIENT → exact + fuzzy grounding only, no LLM, precise error message
```

---

## Degradation Accuracy Table

The following table shows **target** grounded-answer and false-refusal rates
at different model sizes. These are labeled **target (not yet measured)**
because we cannot run the full benchmark suite in the current environment.
They will be replaced with live `make bench` numbers when measured.

| Model Size | Hardware | Grounding Mode | Grounded-Answer Rate | False-Refusal Rate | Status |
|:---|:---|:---|:---|:---|:---|
| 7B (Q4_K_M) | CPU, 8 GB RAM | text-only | ≥ 85% (target) | < 10% (target) | target (not yet measured) |
| 7B (Q4_K_M) | GPU, 16 GB VRAM | text-only | ≥ 90% (target) | < 7% (target) | target (not yet measured) |
| 13B (Q4_K_M) | GPU, 16 GB VRAM | text-only | ≥ 93% (target) | < 6% (target) | target (not yet measured) |
| 34B (Q4_K_M) | GPU, 16 GB VRAM | visual + text | ≥ 95% (target) | < 5% (target) | target (not yet measured) |
| 34B (Q4_K_M) | GPU, 24+ GB VRAM | visual + text | ≥ 97% (target) | < 3% (target) | target (not yet measured) |

**Note:** The production-ready target is grounded-answer ≥ 95% and false-refusal < 5%.
The 34B + GPU tier is expected to meet this. Smaller models and CPU-only mode
will have lower accuracy — this is honest degradation, not a failure.

---

## Model VRAM/RAM Requirements

| Model | VRAM (GPU) | RAM (CPU fallback) | Notes |
|:---|:---|:---|:---|
| 7B (Q4_K_M) | 6 GB | 8 GB | Minimum viable model |
| 13B (Q4_K_M) | 10 GB | 14 GB | Better extraction quality |
| 34B (Q4_K_M) | 24 GB | 36 GB | Production-grade, visual retrieval |

These are approximate. `scripts/hardware_check.py` uses these values in its
pre-flight check to prevent OOM crashes.

---

## How to Check Your Hardware

```bash
python3 scripts/hardware_check.py
```

Output includes:
- Detected GPU name and VRAM
- Detected RAM
- Assigned tier (minimum / recommended / insufficient)
- Enabled and disabled features
- Per-model load checks (7B / 13B / 34B)
- JSON profile for programmatic use

Exit code: 0 if sufficient, 1 if insufficient.

---

## Testing

```bash
python3 -m pytest tests/test_hardware_check.py -v
```

Tests simulate low-memory and no-GPU environments using override parameters
(not mocks) and assert that:
1. The fallback path activates when no GPU is detected.
2. The "visual retrieval disabled" message is logged.
3. Insufficient RAM is detected before model load and a precise message is printed.
4. The pre-flight check prevents OOM crashes by blocking model load.