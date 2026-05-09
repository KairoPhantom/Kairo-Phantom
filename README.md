# Kairo Phantom

> **The AI ghost-writer that lives inside your apps.**
> Press Alt+M anywhere. Kairo reads your document, routes to the right specialist agent, and types the answer directly into your window.

[![Build](https://github.com/your-org/kairo-phantom/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/kairo-phantom/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.78%2B-orange.svg)](https://www.rust-lang.org)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

---

## ⚡ Quick Install

**Windows (one-liner):**
```powershell
irm https://raw.githubusercontent.com/your-org/kairo-phantom/main/install.ps1 | iex
```

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/your-org/kairo-phantom/main/install.sh | bash
```

Then add your API key to `~/.kairo-phantom/config.toml` and press **Alt+M** in any app.

---

## 🎯 What It Does

| Press | In | Kairo does |
|-------|-----|------------|
| `Alt+M` | Word | Reads your doc → streams AI prose → types it in |
| `Alt+M` | PowerPoint | Detects slide → suggests layout + content → types it |
| `Alt+M` | Excel | Detects data → writes formula → injects it |
| `Alt+M` | VS Code | Reads code → writes completion → types it |
| `Alt+M` | Terminal | Reads command history → suggests next command |
| `Alt+M` | Any app | Clipboard fallback → ghost types the response |

---

## 🤖 Swarm Agents (15 Specialists)

Kairo automatically routes to the best agent based on what you're writing:

| Agent | Triggers On |
|-------|-------------|
| 🎨 Design & Media | PowerPoint, Figma, Canva, visual prompts |
| 🧠 Reasoning & Logic | Code, terminal, calculations |
| ✍️ Content All-Rounder | Word docs, general writing (default) |
| 🖼️ Image Generation | "generate image", "create icon", "diagram" |
| 💰 Finance & Spreadsheet | Excel, Google Sheets, formulas |
| ⚖️ Legal Documents | Contracts, NDAs, agreements |
| 🏥 Medical Documentation | SOAP notes, ICD-10, clinical summaries |
| 🎓 Academic Writing | Research papers, APA/MLA citations |
| 📈 Sales & Marketing | Cold email, proposals, pitch decks |
| 👥 HR & Talent | Job descriptions, performance reviews |
| 📣 Marketing Content | Blog posts, SEO, ad copy, landing pages |
| 📋 Product Management | PRDs, user stories, OKRs, roadmaps |
| 👨‍💻 Engineer | README, commits, architecture docs |
| 📚 Student Tutor | Beginner-friendly explanations |
| 📊 Data Analyst | Pivot tables, data summaries |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kairo Phantom Core                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │  Global  │  │    UIA   │  │  Swarm   │  │   Ghost    │ │
│  │  Hotkey  │→ │  Reader  │→ │  Brain   │→ │  Session   │ │
│  │  Alt+M   │  │ (Win32)  │  │ (Router) │  │  (Stream)  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│                                    ↓              ↓         │
│                              ┌──────────┐  ┌────────────┐ │
│                              │   Image  │  │  Injector  │ │
│                              │ Pipeline │  │  (Enigo)   │ │
│                              └──────────┘  └────────────┘ │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          HTTP API (localhost:7437)                   │   │
│  │  /health /materialize /ask /inject /generate_image  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ↕ JSON-RPC stdio                    ↕ JSON-RPC stdio
┌──────────────────┐              ┌─────────────────────────┐
│ MCP Bridge: PPTX │              │   Kairo MCP Server      │
│  14 tools        │              │   8 tools               │
│  (python-pptx)   │              │   (Claude/Cursor/Wind.) │
└──────────────────┘              └─────────────────────────┘
```

---

## 🖼️ Image Generation

Kairo routes image generation to the best available backend:

| Backend | Quality | Speed | Cost | Setup |
|---------|---------|-------|------|-------|
| OpenAI gpt-image-1 | ⭐⭐⭐⭐⭐ | ~15s | $0.04/img | `openai_api_key` |
| Google Imagen 3 | ⭐⭐⭐⭐⭐ | ~10s | Free tier | `gemini_api_key` |
| Ollama (local) | ⭐⭐⭐ | ~30–120s | FREE | Ollama installed |

Generated images are automatically:
- Copied to clipboard (Ctrl+V in any app)
- Injected directly into PPTX slides (via python-pptx)
- Inserted into Word documents (via python-docx)

---

## 🔌 MCP Integration (Claude Code / Cursor / Windsurf)

Add to your MCP config:

```json
{
  "mcpServers": {
    "kairo": {
      "command": "kairo-mcp",
      "args": []
    }
  }
}
```

Available MCP tools:

| Tool | Description |
|------|-------------|
| `kairo_read_context` | Read focused window text |
| `kairo_ghost_write` | Type text into active window |
| `kairo_ask` | Full AI round-trip (read → route → inject) |
| `kairo_generate_image` | Generate image via image pipeline |
| `kairo_generate_image_inject` | Generate + auto-inject into doc |
| `kairo_generate_slide` | Generate full PPTX from topic |
| `kairo_detect_app` | Detect active application |
| `kairo_list_agents` | List all 15 swarm agents |

---

## ⚙️ Configuration

`~/.kairo-phantom/config.toml`:

```toml
[ai]
# Choose one (or all — Kairo falls back gracefully):
openai_api_key = "sk-..."           # OpenAI GPT-4o
gemini_api_key = "AIza..."          # Google Gemini
ollama_base_url = "http://localhost:11434"  # Offline/local

[image]
openai_api_key = "sk-..."           # gpt-image-1
gemini_api_key = "AIza..."          # Imagen 3
# offline_only = true               # Force local Ollama

[swarm]
enabled = true                      # Multi-agent routing

[mcp]
# canva_access_token = "..."        # Canva Connect API
```

---

## 🧩 Plugin System

Install hero plugins to extend Kairo's capabilities:

```bash
# Copy plugins to installation directory
cp plugins/*.toml ~/.kairo-phantom/plugins/
```

**Available hero plugins** (`plugins/`):
- `finance.toml` — Excel formulas, DCF, financial modeling
- `legal.toml` — Contracts, NDAs, legal drafting  
- `design.toml` — PowerPoint, Figma, visual design
- `dev.toml` — Code, README, git commits, architecture
- `medical.toml` — SOAP notes, ICD-10, clinical docs
- `academic.toml` — Research papers, APA/MLA citations
- `sales.toml` — Cold email, proposals, CRM
- `hr.toml` — Job descriptions, performance reviews
- `marketing.toml` — Blogs, SEO, ad copy
- `product.toml` — PRDs, user stories, OKRs

---

## 🎮 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Alt+M` | Activate Kairo / submit prompt |
| `Esc` | Cancel streaming (immediately) |
| `Tab` | Accept full suggestion |
| `Ctrl+Right` | Accept next word |
| `Alt+1` / `Alt+2` | Switch between alternatives A/B |
| `Ctrl+/` | Re-prompt (inline correction) |
| `Ctrl+Z` | Agent-aware undo (restores pre-Kairo state) |
| `Alt+Shift+M` | Replay last session |

---

## 🔑 API Keys Reference

After installation, you'll need at least one of these:

| Service | Key | Get it at | Used for |
|---------|-----|-----------|----------|
| **OpenAI** | `openai_api_key` | [platform.openai.com](https://platform.openai.com) | GPT-4o text + gpt-image-1 |
| **Google Gemini** | `gemini_api_key` | [aistudio.google.com](https://aistudio.google.com) | Gemini text + Imagen 3 |
| **Anthropic** | `anthropic_api_key` | [console.anthropic.com](https://console.anthropic.com) | Claude Sonnet |
| **Canva** | `canva_access_token` | [canva.com/developers](https://www.canva.com/developers) | Canva Connect API |
| **Ollama** | *(none)* | [ollama.ai](https://ollama.ai) | 100% local/offline |

> **Minimum to start:** Just Ollama (free, local). Add cloud keys for higher quality.

---

## 🏗️ Build from Source

```bash
git clone https://github.com/your-org/kairo-phantom
cd kairo-phantom

# Build core
cd phantom-core && cargo build --release

# Build MCP server  
cd ../mcp-servers/kairo-mcp && cargo build --release

# Install Python bridges
pip install python-pptx pillow requests

# Run
./target/release/kairo-phantom
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 🌟 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit with Conventional Commits: `feat(swarm): add new agent`
4. Open a PR — describe What/Why/How

Hero plugin contributions especially welcome! See `plugins/finance.toml` as a template.
