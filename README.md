# Kairo Phantom v2.2

### The document AI with a conscience you can audit.

A local-first, MIT open-core layer that answers questions about your documents and extracts fields, where **every value is anchored to a page + bounding box, or it refuses**.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Blind: 100% grounded](https://img.shields.io/badge/blind-100%25%20grounded-brightgreen)](BENCHMARKS.md)
[![Tests: 167 passing](https://img.shields.io/badge/tests-167%20passing-brightgreen)]()
[![Local-first](https://img.shields.io/badge/architecture-local--first-blueviolet)]()

---

## What it does

Kairo Phantom reads your documents (PDFs, invoices, contracts, papers, memos) and extracts fields with **pixel-level provenance**. Every extracted value comes with:

- A **bounding box** on the source page
- A **cascade method** (EXACT → FUZZY → SEMANTIC → VISUAL → BLOCK)
- A **confidence score**
- A **source link** (`kairo://doc/{id}?page=N&x=X&y=Y&w=W&h=H`)

If it can't ground a value to the document, it **refuses** — and tells you why.

## Why it's different

Your competitors generate fluent text and occasionally lie. Kairo's entire franchise is the one thing they structurally cannot do: **refuse-or-cite**. A model-independent verifier re-checks every quote against stored bboxes and blocks anything it can't ground. The model can never self-certify a bounding box.

## Quick start

```bash
git clone https://github.com/KairoPhantom/Kairo-Phantom.git
cd Kairo-Phantom
pip install -r requirements.lock  # includes numpy, PyMuPDF, openpyxl, and more
python -m bench.blind_bench  # verify 100% blind grounded
```

See [QUICKSTART.md](QUICKSTART.md) for the 5-step integration guide.

## Key features

- **5-layer grounding cascade**: NORMALIZE → EXACT → FUZZY → SEMANTIC → VISUAL → BLOCK
- **4 document packs**: generic, invoice, contract, paper
- **Context compression**: 84% token reduction on boilerplate (Kairo Context Compressor)
- **Grounding trace dashboard**: live cascade visualization at `/dashboard`
- **Connector protocol**: `POST /api/extract-document`, `POST /api/ask-document`
- **Knowledge graph**: grounded entity graph with bbox-anchored nodes
- **Figure extraction**: PyMuPDF-based figure detection + caption association
- **Eval + monitoring**: regression detection, drift alerts, live metrics
- **Injection guard**: 200+ payload corpus, multi-language, NFKC + zero-width
- **P2P sync**: zero-cloud document sync between devices (stretch goal)

## Architecture

```
Document → Ingestor → Security Filter → Context Compression → Pack Extractor
    → Grounding Verifier (5-layer cascade) → Quality Gate → Output
```

The grounding verifier is **model-independent** — it works regardless of which model produced the candidate answer. The 100% blind number was achieved with **no LLM at all** (test mode).

## Benchmarks

| Metric | Blind (120 docs) | Gate |
|---|---|---|
| Grounded Rate | **100.0%** | ≥ 95% |
| False-Refusal Rate | **0.0%** | < 5% |
| Refusal-Correct Rate | **100.0%** | = 100% |
| Hallucinated-Bbox Blocked | **100.0%** | = 100% |

See [BENCHMARKS.md](BENCHMARKS.md) for full details and [FAILURE_TAXONOMY.md](FAILURE_TAXONOMY.md) for the honest failure breakdown.

## Security

- **Air-gap verified**: zero network traffic in default config
- **25/25 prompt injection payloads blocked** (expanded to 200+)
- **RAGShield**: poisoning neutralized by grounding verifier
- **Secret scan**: no key leakage in config files

See [NETWORK_AUDIT.md](NETWORK_AUDIT.md) for the full security audit.

## Development

```bash
make run          # start the sidecar + kernel together
make test         # run the full test suite
cargo build       # build the Rust core
```

The Python sidecar exists because OCR, layout analysis, and document parsing
engines (Docling, PyMuPDF, pdfplumber) are Python-native — reimplementing them
in Rust would be a massive undertaking with no marginal benefit.

## License

MIT — open core with paid Packs. See [LICENSE](LICENSE).