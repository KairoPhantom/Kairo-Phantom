# Kairo Phantom — FAQ

> Honest, specific, anti-bluff answers. Trust the receipts.

## 1. Is this shipped or vaporware?

Shipped — with measured receipts. There is a runnable binary you can download from [releases], and `make bench` produces real, reproducible benchmark output from a clean checkout. The grounding cascade, refusal behavior, and air-gap mode are all exercised by tests that fail when the behavior breaks. If a feature isn't measured by a test, we don't claim it works.

## 2. Isn't this just RAG with bounding boxes?

No — the critical difference is verifier independence. In standard RAG, the model generates an answer and cites a source, but nothing independently verifies that the citation is accurate. The model is both answerer and certifier. Kairo splits these roles: the model proposes, but a separate deterministic Rust verifier re-checks every quote and coordinate against stored document geometry. The ablation ([link to bench/ablation]) shows that with the verifier OFF, ungrounded answers leak through; with it ON, they're blocked. The model can never self-certify a bounding box.

## 3. Hardware requirements / does ColQwen2 need a GPU?

ColQwen2/ColPali visual retrieval benefits from a GPU but degrades gracefully without one. The hardware matrix: GPU (RTX 3060+) → full visual retrieval + fast inference; CPU-only → text-based grounding fallback with higher latency; Apple Silicon (M1+) → MPS acceleration. The Rust core itself is lightweight — it's the Python sidecar (OCR, embeddings, LLM) that determines performance. On a machine with no GPU, you still get grounded answers, just slower. `make bench` reports per-stage timing so you can see the degradation curve for your hardware.

## 4. Will it over-refuse and become useless?

False-refusal is measured and targeted at < 5%. The benchmark suite includes hard cases specifically designed to expose false-refusal regressions: merged-cell invoice totals, partially-scanned invoices, cross-referenced contract clauses, and figure-caption-only facts in papers. When Kairo does refuse, it doesn't just go silent — the refusal panel explains *why* (which cascade stage blocked the answer), so you can rephrase your question or check if the document is incomplete. Refusal is a feature when the alternative is a hallucinated answer.

## 5. Frontier labs will ship this in 6 months.

They structurally can't — not with the same guarantees. Kairo's air-gap mode, MIT license, and deterministic verifier are incompatible with cloud business models. A cloud AI company's revenue depends on your data flowing through their servers; they can't offer provable zero-egress. Their models are proprietary; they can't offer MIT. And their architecture has the model certifying its own citations; they can't offer verifier independence without fundamentally restructuring their stack. Kairo is built for the use case where "trust me, it's offline" isn't good enough — you need to verify it yourself with `strace`.

## 6. How do I know it's actually offline?

Run `strace -f -e trace=network kairo-phantom 2>&1 | grep connect` in air-gap mode — you'll see zero connect() syscalls to external addresses. The CI pipeline includes a packet capture test that fails the build if any network egress occurs during a grounded-answer query. The optional cloud BYO-key proxy runs on a separate port (:4000) and is off by default; no API key material ever hits disk or logs. You don't have to trust our word — the proof is a command you can run yourself.
