# Kairo Phantom — Show HN Submission

**Title:** Show HN: Kairo Phantom – an AI ghost-writer that works inside Word, PowerPoint, Figma and any other app (Rust, local-first)

---

## Post Body

I spent the last few months building something I kept wishing existed: an AI writing assistant that doesn't require me to switch apps.

**Kairo Phantom** sits as a background Rust process. Press **Alt+M** anywhere — Word, Notion, Google Docs, VS Code, a terminal, PowerPoint, Figma — type your request, and it reads the focused window's text via the Windows Accessibility API, routes to the right specialized agent (Design, Code, Medical, Legal, Sales, etc.), streams the response, and ghost-types the result directly into your document. No copy-paste.

### What makes it different

- **Zero context-switch**: stays in your app. No browser tab to Alt+Tab to.
- **Document-aware**: reads the actual content of what you're editing. The AI knows you're on slide 3 of a Q3 earnings deck, not just responding to a generic prompt.
- **Swarm routing**: 15 specialized agents. Detects "you're writing in Word + the prompt is about indemnification" → routes to the Legal agent automatically.
- **Image pipeline**: generates images (OpenAI/Gemini Imagen 3/Ollama SD) and copies them to clipboard OR injects directly into the PPTX file via python-pptx.
- **MCP server**: exposes all capabilities to Claude Code, Cursor, Windsurf as `kairo_ghost_write`, `kairo_generate_slide`, `kairo_generate_image`, etc.
- **Local-first**: works 100% offline with Ollama. No data leaves your machine unless you configure a cloud API.
- **Ghost Session UX**: streaming + Esc to cancel + Tab to accept + Alt+1/Alt+2 to switch between two alternatives + Ctrl+Right to word-by-word accept + confidence bands (green/yellow/red glow).
- **Plugin system**: TOML-based hero plugins for Finance, Legal, Medical, Academic, Sales, HR, Marketing, Product, Dev.

### Stack

- **Core**: Rust (tokio, axum, enigo, uiautomation, ollama-rs, reqwest, yrs CRDT)
- **MCP bridges**: Python (python-pptx, Figma API)
- **MCP server**: Rust (JSON-RPC stdio, connects to Claude Code/Cursor/Windsurf)
- **Overlay**: Tauri (planned for v0.4 — currently hotkey-driven)

### Install (Windows, one line)

```powershell
irm https://raw.githubusercontent.com/your-org/kairo-phantom/main/install.ps1 | iex
```

macOS/Linux:
```bash
curl -sSL https://raw.githubusercontent.com/your-org/kairo-phantom/main/install.sh | bash
```

### Open questions I'd love feedback on

1. The Windows accessibility (UIA) layer is tight but brittle for some Electron apps. Anyone have experience with `IUIAutomation` in non-standard window hierarchies?
2. Ghost-typing speed vs. typing simulation detection in apps like Notion (which uses slate.js). I'm currently using `enigo` at ~20ms per char.
3. The swarm routing uses keyword + doc-kind scoring. Would a small embedding model be worth the latency trade-off for more accurate routing?

GitHub: [https://github.com/your-org/kairo-phantom](https://github.com/your-org/kairo-phantom)

---

## Tags
`show-hn` `rust` `ai` `productivity` `local-first` `llm` `mcp` `windows` `macos`
