# Kairo Phantom

> **An AI ghost-writer that haunts any app and learns how you write.**

```bash
cargo install kairo-phantom
```

Press `Alt+M` anywhere. Ghost-text appears in 2 seconds.

---

`Works in any app` &nbsp;|&nbsp; `Learns your style` &nbsp;|&nbsp; `100% offline via Ollama`

---

## What it does

Kairo Phantom is a system-wide AI writing assistant for Windows. It lives at the OS level — no browser extension, no plugin, no copy-paste. Press `Alt+M` in **any** text field (Word, Outlook, Slack, VS Code, your browser, your terminal), and Kairo reads your context, routes your prompt to the best specialist agent, and types the AI response directly into the window — character by character, as if a skilled colleague is typing beside you.

**Who it's for:** Knowledge workers who type for a living and are tired of switching windows to an AI chat interface.

---

## Quickstart

```bash
# 1. Install Ollama (offline AI engine)
#    → https://ollama.ai

# 2. Pull a model
ollama pull qwen2.5-coder:7b

# 3. Install Kairo Phantom
cargo install kairo-phantom

# 4. Launch
kairo-phantom

# 5. Open any app, click a text field, press Alt+M
```

That's it. No accounts. No API keys. No data leaving your machine.

---

## How it works

- **Press `Alt+M`** — hotkey is intercepted at the OS level via native accessibility APIs.
- **Context is captured** — Kairo reads the active window title, selected text, and surrounding document content.
- **Prompt is routed** — the 8-agent Waza swarm selects the specialist best suited to your context.
- **Memory is recalled** — your formatting preferences (bullets vs. prose, formal vs. casual, length) are loaded from local SQLite.
- **Ghost-text appears** — the response streams directly into your active window, character by character.

---

## Does Kairo actually learn?

**Yes — and we've measured it.**

The `MemMachine` intelligence engine is validated against a 30-session production benchmark. All scores are computed from live system output — not simulations.

### Memory Intelligence Benchmark — v0.3.0

| Metric | Score |
|--------|-------|
| **Final Composite Score** | **0.9872** |
| **Learning Convergence** | Session 2 (from cold start) |
| **Format Match (sessions 2–30)** | 1.000 |
| **Tone Consistency (sessions 2–30)** | 1.000 |
| **Length Accuracy (sessions 2–30)** | 1.000 |
| **Sessions tested** | 30 |

**Learning curve:**

| Session | Composite |
|---------|-----------|
| 1 | 0.617 |
| 2 | **1.000** |
| 3–30 | **1.000** |

Score curve: `▂████████████████████████████` — converges after **one correction**.

Reproduce it yourself:
```bash
cargo run --release --bin memory_benchmark
```

### Five architectural upgrades behind the score

| Upgrade | Technique | Impact |
|---------|-----------|--------|
| **Ground-Truth Store** | Raw episode preservation | Eliminates LLM summary drift |
| **PRIME Meta-Operations** | Merge/Split/Generalize policies | Self-improving learning |
| **Alaya Cognitive Decay** | Ebbinghaus curves in SQLite | Prunes noise, preserves signal |
| **Multi-Granularity Routing** | Entropy-based context_key | Sub-app preference precision |
| **PAHF Dual-Channel Feedback** | Format + tone + length signals | 3× faster preference learning |

---

## Waza Agents

Kairo ships with 8 specialist agents. The router selects the best one automatically.

| Agent | Best for | Example prompt |
|---|---|---|
| **Corporate Strategist** | Pitch decks, exec summaries | *"Draft a Q3 migration memo for the board."* |
| **Creative Writer** | Blog posts, marketing copy | *"Write a compelling hook about our new launch."* |
| **Developer** | Code docs, technical writing | *"Document this Python class and its methods."* |
| **Academic Researcher** | Literature reviews, citations | *"Summarize the findings on quantum decoherence."* |
| **Medical Reviewer** | Clinical notes, patient comms | *"Plain-English explanation of this diagnosis."* |
| **Legal Writer** | Contracts, briefs, compliance | *"Write a boilerplate non-disclosure clause."* |
| **Marketing Copywriter** | SEO, ad copy, social media | *"Generate 3 tweet variants for this feature."* |
| **Executive Communicator** | Slack, email, status updates | *"Politely decline this meeting request."* |

---

## Keyboard Reference

| Shortcut | Action |
|---|---|
| `Alt+M` | Trigger ghost-write at cursor |
| `Esc` | Cancel streaming mid-generation |
| `Alt+Z` | Undo last ghost-write |
| `Alt+Shift+M` | Re-run with different agent |

---

## Install community agents

The Waza architecture is fully open. Install third-party agents from the community:

```bash
kairo agent install github.com/community/legal-brief-agent
```

Build your own: see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Privacy

**Zero telemetry. Your data never leaves your machine** unless you explicitly configure a cloud LLM provider.

- Default provider: **Ollama** (100% local inference)
- Memory store: local SQLite at `~/.kairo-phantom/memory/`
- No usage analytics, crash reporting, or network calls from the core engine

Cloud providers (OpenAI, Anthropic, Gemini) are opt-in and require you to add your own API key to `~/.kairo-phantom/config.toml`.

---

## Security

- **WASM sandbox** — third-party plugins run in Wasmtime with Ed25519 signature verification
- **ToolGate** — explicit allowlist for all file access and tool calls
- **Sentinel sanitizer** — prompt injection detection and PII redaction on all AI output
- **SPIFFE identity** — cryptographically signed agent identity at every inter-agent boundary

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

---

## Contributing

We welcome community agents, bug fixes, and platform ports.

→ [Build your own Waza agent in 10 minutes](CONTRIBUTING.md)

---

## License

MIT — see [LICENSE](LICENSE).
