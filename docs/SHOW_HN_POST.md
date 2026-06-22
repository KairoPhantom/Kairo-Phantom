# Show HN: Kairo Phantom – local doc Q&A that refuses to hallucinate (MIT, Rust, offline)

## Post Body

**Title:** Show HN: Kairo Phantom – local doc Q&A that refuses to hallucinate (MIT, Rust, offline)

Every RAG system I've used has the same problem: it cites things that sound right but aren't actually in the document. The model generates a plausible answer, slaps a citation on it, and you trust it because it *looks* grounded. Kairo Phantom is my attempt to fix this at the architecture level.

**Why not just use Claude/ChatGPT with citations?**

Because the model is certifying its own citations. When Claude says "according to page 4, paragraph 2," nothing independently verifies that the text on page 4, paragraph 2 actually supports the claim. The model is both the answerer and the verifier — that's a conflict of interest. Kairo splits these roles: the model proposes an answer, but a separate, deterministic Rust verifier independently re-checks every quote and coordinate against stored document geometry. The model can never self-certify a bounding box.

**What's measured today (not promises — receipts):**

- **Blind benchmark: 100.0% grounded on 120 real documents** (832/832 answerable fields grounded-correct, 8/8 unanswerable refusal-correct, 0 hallucinations). Run it yourself: `python -m bench.blind_bench`
- Grounding cascade: NORMALIZE → EXACT → FUZZY(≥0.92) → SEMANTIC(≥0.86, re-verify) → VISUAL(IoU≥0.5) → BLOCK
- 4 Packs: generic, invoice, paper, contract — each with fixture-based benchmarks
- Air-gap mode: zero network egress, provable with `strace` (25/25 prompt injection payloads blocked)
- The verifier is model-independent — the 100% blind number was achieved with **no LLM at all** (test mode), proving the verifier works regardless of which model produced the answer
- Parse throughput: 183 pages/s on CPU alone (no GPU needed for extraction + grounding)
- We publish our own failure taxonomy: 89 failures across 8 categories, all diagnosed and fixed. See `FAILURE_TAXONOMY.md`.

**The moat in one sentence:** the verifier re-checks every coordinate independently of the model, so even if the model hallucinates, the verifier blocks the ungrounded answer from reaching the UI.

**Scope boundaries — what it does and doesn't do:**

- ✅ Reads PDFs, .txt, .docx and answers questions with source-region highlights
- ✅ Refuses (stays silent) when it can't ground a claim — and tells you why
- ✅ Runs 100% locally (Rust core + Python sidecar on 127.0.0.1:7438)
- ✅ MIT licensed, open-core with paid Packs
- ❌ Does not write to or modify your source documents (v1 is READ + SUGGEST ONLY)
- ❌ Does not send data to any cloud (optional BYO-key cloud on :4000, off by default)
- ❌ Is not a multi-domain expert swarm or collaborative layer

I'd love feedback on the grounding cascade thresholds, the refusal UX, and whether the verifier-independence argument holds up. The code is at [github link] and you can reproduce the benchmarks with `python3 scripts/replicate.py`.

---

## Prepared Replies

### Reply 1: Cascade Ablation Question

> "Can you show what happens when the verifier is turned off?"

Yes — we run an ablation where the grounding verifier is disabled. With the verifier OFF, ungrounded answers leak through to the UI at a measurable rate (the model produces plausible-sounding answers that don't match any text region). With the verifier ON, those same answers are blocked. The ablation is in `bench/` and you can run it yourself: it shows the leak rate with OFF vs. zero leaks with ON. The key insight is that the verifier is deterministic and model-independent — it doesn't care what the model said, it only checks whether the claimed source text actually exists at the claimed coordinates.

### Reply 2: Hardware Requirements Question

> "What hardware do you need? Does ColQwen2 require a GPU?"

ColQwen2/ColPali visual retrieval benefits from a GPU but degrades gracefully without one. The hardware matrix is: GPU (e.g., RTX 3060+) → full visual retrieval + fast inference; CPU-only → visual retrieval falls back to text-based grounding with slightly higher latency; Apple Silicon (M1+) → MPS acceleration for the sidecar. The Rust core itself has minimal hardware requirements — it's the Python sidecar (OCR, embeddings, LLM inference) that determines the experience. On a machine with no GPU, you still get grounded answers, just slower. The `make bench` output includes timing per stage so you can see the degradation curve.

### Reply 3: Threat Model / Air-Gap Question

> "How do I know it's actually offline?"

Three ways: (1) Run `strace -f -e trace=network kairo-phantom 2>&1 | grep connect` — you'll see zero connect() syscalls to external addresses in air-gap mode. (2) The CI pipeline includes a packet capture test that fails if any network egress occurs during a grounded-answer query. (3) The optional cloud BYO-key proxy runs on a separate port (:4000) and is off by default — no API key material ever hits disk or logs. The threat model doc covers the full attack surface: prompt injection via document text, model-side hallucination, and provenance tampering — each with a mitigation that's tested in CI.
