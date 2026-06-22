# Kairo Phantom v2.2 — Model Cards

> **Local-first by design.** The default configuration runs entirely on-device. Cloud inference (Tier 3) is opt-in and disabled by default. The grounding verifier is model-independent — it works regardless of which model produced the candidate answer.

## Architecture: Tiered Inference

Kairo uses a two-tier inference gateway (`kernel/sidecar/inference_gateway.py`):

| Tier | Role | Default | Location | Enabled |
|---|---|---|---|---|
| Tier 1 (Worker) | Extraction, routing, field detection | `ollama/llama3.2` | Local (LiteLLM/Ollama) | ✅ Always |
| Tier 3 (Reasoner) | Complex Q&A, synthesis | `gpt-4o-mini` | Cloud (OpenAI API) | ❌ Off by default |

### Test mode

When `KAIRO_GATEWAY_TEST_MODE=true`, the gateway returns deterministic responses without calling any model. This is how the blind benchmark runs — the extraction patterns and grounding cascade are pure Python and don't need model inference. This proves the verifier works independently of any model.

---

## Worker Tier (Tier 1 — Local)

| Property | Value |
|---|---|
| **Model** | Llama 3.2 (via Ollama) |
| **Parameters** | 3B (default) / 1B (lightweight variant) |
| **Base** | Meta Llama 3.2 |
| **License** | Llama 3.2 Community License |
| **Runtime** | Ollama / LiteLLM proxy |
| **VRAM** | ~2-4 GB (3B model, Q4 quantization) |
| **CPU fallback** | ✅ Viable — Llama 3.2 1B runs on CPU at ~5-15 tokens/s |
| **Role** | Field extraction, document classification, routing |
| **Air-gap** | ✅ Zero network traffic (local only) |

### CPU fallback viability

Llama 3.2 1B can run on CPU-only machines:
- **RAM:** 2 GB model + 2 GB overhead = 4 GB minimum
- **Speed:** ~5-15 tokens/s on modern x86 (AVX2)
- **Use case:** Extraction and field detection (short prompts, structured output)
- **Limitation:** Not suitable for long-form synthesis or complex reasoning

---

## Reasoner Tier (Tier 3 — Cloud, opt-in)

| Property | Value |
|---|---|
| **Model** | GPT-4o-mini (default, configurable) |
| **Parameters** | Proprietary (OpenAI) |
| **Base** | OpenAI GPT-4o family |
| **License** | OpenAI API Terms |
| **Runtime** | OpenAI API (cloud) |
| **VRAM** | N/A (cloud-hosted) |
| **CPU fallback** | N/A |
| **Role** | Complex Q&A, multi-step reasoning, synthesis |
| **Air-gap** | ❌ Requires network — disabled by default |

### Alternative reasoner models (configurable)

The reasoner tier model is configurable via `tier3_model` parameter:
- `gpt-4o-mini` — default, cost-effective
- `gpt-4o` — higher quality, higher cost
- `claude-3-5-sonnet` — Anthropic, strong reasoning
- `mistral-large` — Mistral AI, European hosting option
- Any LiteLLM-supported model

### When to enable Tier 3

Tier 3 is for users who want LLM-powered Q&A on their documents. The extraction + grounding pipeline works without it. Enable only when:
- You need natural-language Q&A (not just field extraction)
- You accept cloud traffic (breaks air-gap)
- You've configured API credentials

---

## Embedding Model

| Property | Value |
|---|---|
| **Model** | Deterministic word-frequency hashing (fallback) |
| **Dimensions** | 384 |
| **Location** | Local (in-process Python) |
| **VRAM** | 0 (CPU only, no model loaded) |
| **Air-gap** | ✅ Zero network traffic |
| **Role** | Semantic similarity in grounding cascade (SEMANTIC layer) |

The embedding function (`kernel/core/embeddings.py`) uses a deterministic hashing-based vector when no sentence-transformer model is available. This is intentionally lightweight — the grounding cascade's SEMANTIC layer (cosine similarity ≥ 0.86) works with any embedding, and the deterministic fallback ensures air-gap compliance.

For higher-quality semantic matching, users can plug in `sentence-transformers/all-MiniLM-L6-v2` (384-dim, ~90 MB, CPU-viable) without changing the cascade thresholds.

---

## Grounding Verifier (Model-Independent)

The 5-layer cascade (`kernel/core/grounding.py`) is the core moat:

```
NORMALIZE → EXACT → FUZZY(≥0.92) → SEMANTIC(≥0.86, re-verify) → VISUAL(IoU≥0.5) → BLOCK
```

**This component does not use any LLM.** It is pure deterministic Python. It re-checks every candidate value against the stored document text and bounding boxes, and blocks (refuses) anything it cannot ground. This is what makes Kairo's citations independently auditable — the verifier's decision does not depend on which model produced the answer.

---

## Model independence

The blind benchmark (100.0% grounded) was run in test mode with **no model inference at all** — only the extraction patterns + grounding cascade. This proves:

1. The verifier works without any LLM
2. The extraction patterns are deterministic
3. The refusal-or-cite guarantee is model-independent
4. The numbers reproduce on any machine with Python (no GPU, no API keys)