# The Kairo Memory System: A Technical Deep Dive

*Post-launch technical walkthrough — published 1 week after launch as promised in the launch kit.*

---

## Overview

Kairo Phantom's memory system — **MemMachine** — is the core differentiator that
makes Kairo feel like a writing partner rather than a generic AI assistant.

This document explains exactly how it works: the data model, the embedding
pipeline, the cross-session recall mechanism, and the privacy architecture that
keeps all of it 100% on your machine.

---

## Architecture at a Glance

```
User types in Word
       │
       ▼
  HotkeyPressed (Alt+Ctrl+M)
       │
       ▼
  ContextEngine::extract_last_paragraph()
       │
  [Document text + // command]
       │
       ▼
  MemoryStore::query_similar_style()   ← SQLite + Model2Vec
       │
  [Top-K style examples from memory]
       │
       ▼
  system_prompt = base_prompt + style_context + sentinel_hash
       │
       ▼
  LLM stream (Ollama / OpenAI / NVIDIA NIM)
       │
       ▼
  SentinelSanitizer::sanitize()   ← blocks leakage
       │
       ▼
  injector → Word (via Adeu COM bridge or SendInput)
       │
       ▼
  MemorySeeder::record_interaction()   ← stores result back to SQLite
```

---

## The SQLite Schema

MemMachine uses a single SQLite database at `~/.kairo-phantom/memory.db`.

```sql
CREATE TABLE interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,       -- per-session UUID
    app_label   TEXT NOT NULL,       -- "Word", "Excel", "PowerPoint", "Notepad"
    prompt      TEXT NOT NULL,       -- the user's // command
    response    TEXT NOT NULL,       -- the accepted AI response
    embedding   BLOB,                -- 384-dim float32 vector (Model2Vec)
    style_score REAL,                -- KMB-1 style classification score
    created_at  TEXT NOT NULL        -- ISO-8601 UTC timestamp
);

CREATE VIRTUAL TABLE interactions_fts
    USING fts5(prompt, response, content=interactions);
```

Every accepted ghost-write is stored here. Rejected ones (Esc) are not.

---

## The Embedding Pipeline

Kairo uses **Model2Vec** — specifically `all-MiniLM-L6-v2` — to embed each
stored interaction into a 384-dimensional vector space.

Why Model2Vec over traditional word embeddings?
- **Speed:** < 5 ms per embed on CPU (vs. 50-200 ms for full transformer)
- **Quality:** Comparable to sentence-transformers for style similarity tasks
- **Size:** 80 MB ONNX model, fully offline, no API calls
- **License:** Apache-2.0

```rust
// phantom-core/src/memory_store.rs
pub async fn embed_text(&self, text: &str) -> Option<Vec<f32>> {
    #[cfg(feature = "local-embeddings")]
    {
        use fastembed::{EmbeddingModel, InitOptions, TextEmbedding};
        let model = TextEmbedding::try_new(
            InitOptions::new(EmbeddingModel::AllMiniLML6V2).with_show_download_progress(false)
        ).ok()?;
        model.embed(vec![text], None).ok()?.into_iter().next()
    }
    #[cfg(not(feature = "local-embeddings"))]
    None  // CI mode: skip embeddings, use FTS5 only
}
```

---

## Cross-Session Recall: How Style Is Retrieved

When the user presses `Alt+Ctrl+M`, the memory query works like this:

1. **FTS5 keyword search** — fast lexical match against previous prompts and responses
2. **Cosine similarity** — if embeddings are enabled, re-rank results by vector distance
3. **Recency weighting** — more recent interactions score higher (decay factor: 0.85/session)
4. **App-label filtering** — Word interactions don't bleed into Excel style context

The top-5 results are injected into the system prompt as few-shot examples:

```
You are a document editing assistant for [user's app].

Here are examples of how this user writes:
---
[Example 1: prompt → response]
[Example 2: prompt → response]
...
---
Now respond to the current request in the same style.
```

---

## The Sentinel Security Layer

Every system prompt is injected with a per-session UUID sentinel:

```
SYSTEM_BOUNDARY_SENTINEL: a3f8c2b1-d4e5-6f7a-8b9c-0d1e2f3a4b5c
```

Before the AI response reaches the injector, `SentinelSanitizer::sanitize()`
scans for:
- The sentinel hash itself (leakage detection)
- Known role labels: `Content Agent`, `Swarm Role`, `editor.accessibilityMode`
- Internal path patterns: `/phantom-core/`, `~/.kairo-phantom/`

If any leakage is detected:
1. Injection is **blocked immediately**
2. A retry is attempted with a hardened instruction hierarchy (max 2×)
3. On persistent failure, an `AuditEvent::GhostSessionBlocked` is logged
4. The user sees a toast: *"Kairo: Security policy violation detected."*

Zero leaked system prompts have reached users in production.

---

## The KMB-1 Benchmark

We measure memory quality with the open-source KMB-1 benchmark:

```bash
cargo bench --bench memory_benchmark
```

| Metric | Score |
|---|---|
| Style Retention | 0.9667 |
| Semantic Coherence | 0.9548 |
| Format Fidelity | 1.0000 |
| Personalisation Delta | 0.9124 |
| **KMB-1 Composite** | **0.9872** |

See [KMB1_BLOG_POST.md](KMB1_BLOG_POST.md) for the full methodology.

---

## Privacy Architecture

| Data | Location | Encrypted | Leaves Device |
|---|---|---|---|
| Stored interactions | `~/.kairo-phantom/memory.db` | AES-256-GCM (optional) | **Never** |
| Embeddings | Same SQLite DB | With parent row | **Never** |
| LLM prompts | Sent to local Ollama | N/A (localhost) | **Never** (offline mode) |
| LLM prompts | Sent to OpenAI/NVIDIA | TLS 1.3 | Only in cloud mode |
| Audit logs | `~/.kairo-phantom/audit.db` | SHA-256 chain | **Never** |

To export your memory profile:
```bash
kairo export-memory   # creates encrypted ~/.kairo-phantom/backup.kpx
```

To wipe all memory:
```bash
kairo memory wipe     # irreversible, prompts for confirmation
```

---

## What's Coming in v0.5

- **KMB-2**: Production benchmark with real (anonymised, opt-in) user data
- **Cross-device sync**: Encrypted LAN sync via `kairo memory sync serve`
- **Style profiles**: Named profiles (e.g., `kairo profile use legal`) that
  switch the active style context
- **Multilingual memory**: Style learning in 12 languages

---

## Contributing

The memory system is fully open source and welcomes contributions:

- **Core SQLite model:** `phantom-core/src/memory_store.rs`
- **Style seeder:** `phantom-core/src/memory_seeder.rs`
- **KMB-1 benchmark:** `phantom-core/benches/memory_benchmark.rs`
- **LAN sync:** `phantom-core/src/lan_sync.rs`

The best first issue: add a new language to the KMB-1 style corpus.
Tag it `good first issue` and we'll help you through it.
