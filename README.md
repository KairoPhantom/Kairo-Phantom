# 👻 Kairo Phantom

**Intelligence is currently trapped in chat boxes. Kairo Phantom liberates it into your operating system.**

Kairo Phantom is a professional-grade, high-performance native engine (written in Rust) that enables AI to "haunt" your OS—reading document structure across any application (Word, PowerPoint, VS Code, Canva, Notion) and materializing intelligence exactly where you type.

> [!IMPORTANT]
> **Ghost Writing vs. Copilots**: Unlike typical AI copilots that live in sidebars, Kairo operates directly on your document surface. It reads your intent, analyzes the document structure, and "ghost-types" the response into your editor via a high-speed injection bridge.

---

## 🚀 Key Features

- **Structured Document Awareness**: Not just raw text. Kairo understands Word headings, PowerPoint slide positions, Excel tables, and Markdown hierarchies.
- **The Swarm Brain**: A multi-agent orchestrator that routes your requests to specialized agents (Design, Reasoning, or Content) based on the application environment.
- **MCP Integration**: Fully compliant with the Model Context Protocol (MCP). Use Kairo as a local intelligence server for **Claude Code**, **Cursor**, or **Goose**.
- **Offline-First**: Default support for **Ollama** (Qwen2.5-Coder/Llama3). Cloud fallbacks available for OpenAI/Anthropic.
- **Glassmorphic Overlay**: A minimalist, non-intrusive Tauri-based UI that provides real-time status feedback.
- **Atomic Injection**: Uses a "Clipboard-First" strategy to atomically substitute your prompt with AI output, preserving your flow.

---

## 🛠️ Project Structure

| Component | Description |
| :--- | :--- |
| `phantom-core` | The Rust heart. Handles Win32 hooks, UIA reading, document extraction, and the Swarm Brain. |
| `kairo-mcp` | The MCP Server bridge. Exposes Kairo's "Ghost Writing" tools to external AI assistants. |
| `phantom-overlay` | A glassmorphic Tauri interface for visual feedback and state management. |

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- **Rust** (stable)
- **Ollama** (optional, for offline mode): `ollama pull qwen2.5-coder:14b`
- **Windows** (Win32/UIA support required)

### 2. Build from Source
```bash
# Clone the repository
git clone https://github.com/Kartik24Hulmukh/KairoPhantom.git
cd KairoPhantom

# Build the core engine
cargo build --release
```

### 3. Usage
1. Run `kairo-phantom.exe`.
2. Open any document (Word, Notion, VS Code).
3. Type a prompt (e.g., "Write a professional summary of this report").
4. Press `Alt + M`.
5. Watch the AI "materialize" the text directly into your document.

---

## 🔌 MCP Integration (Claude Code / Cursor)

Add Kairo as an MCP server to your favorite tool to give it "OS Hands":

**Claude Code:**
```bash
claude mcp add kairo -- cargo run --bin kairo-mcp
```

**Cursor / Custom Config:**
```json
{
  "mcpServers": {
    "kairo": {
      "command": "cargo",
      "args": ["run", "--bin", "kairo-mcp", "--manifest-path", "C:/path/to/KairoPhantom/Cargo.toml"]
    }
  }
}
```

### Available Tools:
- `kairo_read_context`: Fetches rich document structure (headings, tables, slides).
- `kairo_ghost_write`: Injects text directly into the focused application.
- `kairo_ask`: Runs a prompt through the Swarm Brain.
- `kairo_detect_app`: Identifies the current environment.

---

## 🧠 Swarm Configuration
Customize your agents in `~/.kairo-phantom/config.toml`:

```toml
[swarm]
enabled = true

[swarm.brain]
provider = "ollama"
model_name = "qwen2.5-coder:14b"

[swarm.agents.design]
system_directive = "You are a world-class designer. Focus on visual copy and layout..."
```

---

## 🔌 Plugin System
Kairo Phantom v3.0 introduces a powerful plugin architecture. You can extend the engine with custom application fingerprinters and specialized AI agents without recompiling.

### 1. Add plugins to `config.toml`
```toml
plugins = ["C:/path/to/finance_plugin.toml"]
```

### 2. Define your plugin (`plugin.toml`)
```toml
name = "Finance Specialist"

[[fingerprinters]]
process = "calc.exe"
env_label = "Calculator"

[[agents]]
id = "finance"
name = "Finance Expert"
system_prompt = "You are a senior accounting specialist..."
match_pattern = "invoice|billing|tax"
default_score = 5
```

---

## 📜 License
Distributed under the **MIT License**. Built for the open-source community by **Kartik Hulmukh**.

---
*"The best interface is the one that disappears."*
