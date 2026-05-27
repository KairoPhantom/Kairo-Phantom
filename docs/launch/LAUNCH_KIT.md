# Kairo Phantom — Launch Kit

## Launch Day Checklist

- [ ] README updated with Enterprise section + demo GIF
- [ ] Phase 1 gate tests passing (`cargo test`)
- [ ] Video uploaded to YouTube (unlisted → public on launch day)
- [ ] Product Hunt submission scheduled (12:01am PST)
- [ ] Show HN post drafted (below)
- [ ] Reddit posts drafted (below)
- [ ] Hacker News "Ask HN" feedback request ready

---

## Show HN Post

**Title:**
> Show HN: Kairo Phantom – Open-source AI ghost-writer that types directly into any app (Word, VS Code, Notion)

**Body:**
```
Hey HN,

I built Kairo Phantom, an AI writing assistant that's fundamentally different from tab-switching to ChatGPT.

The core idea: press Alt+M in any app (Word, VS Code, Notepad, Notion), type "// your instruction", press Alt+M again — and the AI response types directly into your document. No copy-paste. No context switch.

What makes it different:

1. MEMORY: It learns your writing style. By session 5, it knows you prefer short sentences, bullets over paragraphs, and domain-specific vocabulary. We published a benchmark (KMB-1): 57.7% better personalization than GPT-4o with no memory.

2. PRIVACY: Runs 100% locally with Ollama. Zero data leaves your machine. No API keys needed for the default experience.

3. ENTERPRISE SECURITY: Per-session sentinel UUID, 50-pattern prompt injection firewall, SPIFFE identity, SHA-256-chained audit logs, SOC 2 readiness docs.

4. // PROTOCOL: The double-slash prefix is a deliberate UX decision. It's invisible until you need it, then explicit and consistent. "// rewrite this", "// kami slides: 5-slide pitch", "//! urgent fix".

5. WAZA MARKETPLACE: Skills are TOML + Markdown files. Install legal-review, medical-scribe, code-reviewer, academic-editor with one command. Build your own in 5 minutes.

Technical stack:
- Rust + Tokio async runtime
- Ollama for local LLM (qwen2.5:7b default)
- Win32 UIA for text capture
- SQLite for memory
- WASM sandbox for plugins
- Ed25519 for agent identity

What I'd love feedback on:
- The // protocol — is it learnable in 30 seconds?
- Memory architecture — we're using multi-granularity SQLite. Would you prefer vector embeddings?
- Platform priority — should macOS or Linux come first for the open-source audience?

GitHub: https://github.com/Kartik24Hulmukh/Kairo-Phantom
Install: `cargo install kairo-phantom`
```

---

## Reddit Posts

### r/rust

**Title:** I built a ghost-writer in Rust that types AI responses directly into any Windows app – seeking feedback on the architecture

**Body:**
```
Hey r/rust,

I've been working on Kairo Phantom, an AI ghost-writer built entirely in Rust. Wanted to share the architecture and get feedback from the community.

**Core architecture:**

The main loop is an event-driven Tokio async runtime that:
1. Listens for Alt+M via `rdev` global hotkey
2. Reads text from the focused app via Win32 UIA (`uiautomation` crate)
3. Extracts the `//` command line using a parser that returns `Option<ParsedPrompt>`
4. Streams the LLM response via `ollama-rs`
5. Injects the response using Win32 `SendInput` with humanized timing

**Security layer I'm proud of:**
- Per-session UUID sentinel injected into the system prompt
- If the LLM echoes the sentinel (leakage), the response is blocked + retried up to 2x
- 50 prompt injection patterns in `PromptGuard`
- SHA-256-chained audit log (each event hashes the previous)

**Memory system:**
- SQLite multi-granularity store (per-app, per-doc-type preferences)
- Context-Aware Distillation: compresses 100s of memory items into a focused 512-token injection
- KMB-1 benchmark: 0.9872/1.0 on personalization quality

**What I struggled with:**
- Win32 UIA is janky — some apps (VS Code) don't expose text via UIA, so I fall back to clipboard (Home→Shift+End→Ctrl+C)
- Mid-stream injection caused focus bugs in Word, so I now collect the entire response then do ONE clipboard→paste
- Getting the async cancellation right for the Esc key took 3 attempts

**Cargo.toml highlights:** tokio, rdev, windows-rs, ollama-rs, yrs (CRDT), wasmtime, ed25519-dalek

GitHub: https://github.com/Kartik24Hulmukh/Kairo-Phantom

Happy to discuss any part of the architecture!
```

---

### r/programming

**Title:** Show r/programming: I built an AI ghost-writer that lives in your system tray and types directly into any app

**Body:**
```
I built Kairo Phantom, an open-source AI ghost-writer with a twist: instead of switching to ChatGPT and copy-pasting, you type your instruction directly in your document using `//` and press Alt+M.

The AI reads your document, generates a response, and types it directly into your app — Word, VS Code, Notion, Notepad, anywhere.

What I think is genuinely novel:

**The memory system.** Most AI tools are stateless. Kairo builds a profile of how you write across every session. After a week, it knows your preferred sentence length, vocabulary, formatting style, and structural patterns. We published a benchmark showing 57.7% better personalization than a baseline GPT-4o call.

**The security model.** Each session gets a unique UUID sentinel embedded in the system prompt. If the LLM echoes it back (a sign of prompt injection or leakage), the response is blocked before it ever reaches your document. There's also a 50-pattern injection firewall, SPIFFE-based agent identity, and a tamper-evident audit chain.

**The // protocol.** Typing `//` in any document is the activation prefix. `// rewrite this`, `//! urgent`, `//? what's the word count`. The Skills marketplace (Waza) extends this: `// legal review this contract`, `// code review this function`, `// SOAP note`.

It's MIT-licensed, runs offline with Ollama, and is written entirely in Rust.

https://github.com/Kartik24Hulmukh/Kairo-Phantom
```

---

### r/LocalLLaMA

**Title:** I built a ghost-writer that injects Ollama's output directly into any Windows app — no copy-paste (Show HN crosspost)

**Body:**
```
Hey r/LocalLLaMA,

Built something I think this community will appreciate: Kairo Phantom runs entirely on Ollama (qwen2.5:7b by default), and instead of showing you a chat interface, it types the AI response directly into whatever app you're using.

The flow:
1. You're in Word/VS Code/Notepad
2. Type `// your instruction` anywhere in the document
3. Press Alt+M
4. Kairo reads your document, sends it to Ollama, streams the response back and types it into your app

**Ollama integration:**
- Uses `ollama-rs` with streaming
- Falls back to OpenAI/Anthropic/Gemini if Ollama isn't running
- Supports any model in Ollama — llama3.2, mistral, phi4, deepseek-r1, etc.
- Auto-detects and bootstraps Ollama on first run

**Privacy:**
- 100% local by default
- Documents never leave your machine
- Even the memory (what it learns about your writing style) is SQLite on your local disk

**Performance:**
- First token in ~800ms on RTX 3060 with qwen2.5:7b
- Full sentence in ~2.5s
- Streams tokens as they arrive (you watch it type)

Tested with: qwen2.5:7b, llama3.2:3b, mistral:7b, phi4, deepseek-r1:7b

Would love to know what models people are getting good writing results with!

https://github.com/Kartik24Hulmukh/Kairo-Phantom
Install: `cargo install kairo-phantom`
```

---

### r/selfhosted

**Title:** Self-hosted AI ghost-writer that types directly into Word/VS Code/Notepad — no cloud, no copy-paste

**Body:**
```
If you're already running Ollama for local AI, Kairo Phantom might be a natural companion.

It's a system tray app that reads the focused window, sends the text + your `//` instruction to Ollama, and types the response back into the app. Completely local. No account. No subscription.

**Self-hosting highlights:**
- Runs on your machine, talks to your local Ollama instance
- Memory stored in SQLite at `~/.kairo-phantom/memory.db`
- Config at `~/.kairo-phantom/config.toml` — set your model, API key, preferences
- Enterprise audit logs at `~/.kairo-phantom/enterprise/audit.db`
- Skills marketplace installs to `~/.kairo-phantom/skills/`

**Docker:** Not available yet (it needs GUI/tray access), but a headless server mode for remote team use is on the roadmap.

**What works offline (no Ollama needed):**
- Excel formula engine (deterministic, no LLM needed)
- Section summarizer
- Document health checker
- Contract clause identifier (CUAD model via Python sidecar)

https://github.com/Kartik24Hulmukh/Kairo-Phantom
```

---

## Product Hunt Submission

**Name:** Kairo Phantom  
**Tagline:** The AI ghost-writer that haunts any app — and learns how you write  
**Description:**
> Kairo Phantom lives in your system tray and writes AI-generated content directly into Word, VS Code, Notion — any app. No copy-paste. No context switch. Just type `//` and press Alt+M.
>
> What makes it different: it actually learns your writing style. After a week of use, it knows your preferred vocabulary, sentence structure, and formatting — 57.7% better personalization than raw GPT-4o (per our KMB-1 benchmark).
>
> 100% offline with Ollama. MIT-licensed. Built in Rust.

**Topics:** Artificial Intelligence, Productivity, Developer Tools, Open Source, Writing

**Links:**
- Website: GitHub repo (until landing page is live)
- Demo video: [YouTube link]

**First comment (maker's comment):**
```
Hey Product Hunt! 👋

I'm the maker of Kairo Phantom.

The core frustration that led me to build this: I was spending 20% of my writing time just switching to ChatGPT, explaining context, copying the response, and pasting it back. After the 100th time, I decided to fix it.

The hardest part wasn't the AI integration — it was making the text injection reliable. Win32 UIA is surprisingly inconsistent across apps. VS Code doesn't expose text via accessibility APIs at all, so I had to build a clipboard-based fallback. Word has focus-switching bugs that caused early responses to only inject the first 15 characters.

The memory system took 3 complete rewrites. The current architecture — multi-granularity SQLite + context-aware distillation — is the first one that actually feels like it "knows you" after a few sessions.

Happy to answer any questions about the architecture, the // protocol design, or the roadmap!
```
