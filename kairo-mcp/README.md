# Kairo MCP Server (`kairo-mcp`)

The Model Context Protocol (MCP) server for Kairo Phantom.

This enables AI developer agents like **Claude Code**, **Cursor**, and **Goose** to directly control Kairo Phantom, allowing them to:
- Read your exact document context (what app you are in, what you are looking at)
- Request Kairo to ghost-type generated code/text directly into your focused app
- Leverage Kairo's local or swarm-based agent intelligence seamlessly.

## Tools Exposed

1. `kairo_read_context`: Returns process name, window title, and exact text under cursor/focus.
2. `kairo_ghost_write`: Inject text into the focused window.
3. `kairo_ask`: Forward a prompt to Kairo's internal context-aware swarm (Design, Reasoning, Content) and auto-inject the response.
4. `kairo_detect_app`: Fast check for which app is currently focused (Word, VS Code, Browser, etc).
5. `kairo_switch_agent`: Override the swarm orchestrator's agent selection for the next request.

## Installation for Claude Code

In your terminal, configure Claude Code to use this local server:
```bash
claude mcp add kairo -- cargo run --bin kairo-mcp --manifest-path "C:/Users/SANDIP/Desktop/Memory/KairoPhantom/Cargo.toml"
```

*Note: Ensure `kairo-phantom` (the core engine) is running in the background for the MCP server to successfully execute actions.*
