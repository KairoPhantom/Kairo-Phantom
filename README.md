# Kairo Phantom

LLMs are currently trapped in chat boxes. Kairo Phantom liberates them into your operating system.

Kairo Phantom is a lightweight, high-performance native engine (written in Rust) that enables AI to "haunt" your OS—reading your intent across any application (Word, VS Code, Canva, Browser) and materializing intelligence exactly where you type.

### How it works

The engine operates on a few simple, deterministic primitives:

1. **Global Hooking**: We use a low-level Win32 keyboard hook (`WH_KEYBOARD_LL`) to listen for a specific hotkey (`Alt + M`).
2. **Context Fingerprinting**: Upon trigger, we use UI Automation (UIA) to extract the text from the currently focused element. We don't just read the text; we fingerprint the process (`WINWORD.EXE`, `Code.exe`) to understand the user's environment.
3. **The Swarm Brain**: We don't send a raw prompt to a single LLM. A "Brain" orchestrator first analyzes the context and prompt to delegate the task to a specialized agent (Design, Reasoning, or Content).
4. **SSE Streaming**: Responses are streamed via Server-Sent Events for real-time responsiveness.
5. **Atomic Injection**: Instead of slow character simulation, we use a "Clipboard-First" strategy to atomically substitute the user's prompt with the AI's response via `Ctrl+V`.

### Project Structure

- `phantom-core/`: The Rust backend responsible for OS hooks, UIA reading, and AI orchestration.
- `phantom-overlay/`: A glassmorphic Tauri-based UI that provides visual feedback on AI status.
- `src/swarm.rs`: The multi-agent routing logic.
- `src/context.rs`: Environmental awareness and app fingerprinting.

### Setup

Prerequisites: Rust, Admin privileges (for hooks).

```bash
# Clone the repository
git clone https://github.com/Kartik24Hulmukh/KairoPhantom.git
cd KairoPhantom/phantom-core

# Build and run
cargo run --release
```

Configure your agents in `~/.kairo-phantom/config.toml`:

```toml
[swarm]
enabled = true

[swarm.brain]
provider = "openai"
model_name = "gpt-4o-mini"
api_key = "..."
```

### Philosophy

No bloat. No complex abstractions. Just a direct pipe between LLM intelligence and your keyboard.

### License
MIT
