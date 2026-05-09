# Phase 4 Plan: MCP Server — kairo-mcp
# Kairo Phantom v3.0

## Objective
Make every Claude Code, Cursor, and Goose user a Kairo user by distributing as an MCP server. This is the distribution flywheel: MCP is the emerging standard, and Kairo exposing its ghost-writing capabilities as MCP tools gives us instant distribution to every AI developer.

## What MCP Is
The Model Context Protocol (MCP) is a JSON-RPC 2.0 standard over stdio (or HTTP) that lets AI coding assistants (Claude Code, Cursor, Goose) connect to external tools. When `kairo-phantom-mcp` is added to a user's MCP config, Claude Code can call `kairo_ask("write a professional email")` and the text appears in Word.

**We build an original MCP stdio implementation** — we reference the MCP specification and mouseless's server structure for design inspiration, but every line of our protocol handling is original.

## New Crate Structure

```
KairoPhantom/
├── phantom-core/       (existing)
├── phantom-overlay/    (existing)
└── kairo-mcp/          (NEW)
    ├── Cargo.toml
    ├── src/
    │   ├── main.rs     ← stdio transport, MCP dispatcher
    │   ├── protocol.rs ← JSON-RPC types (Request, Response, Error)
    │   ├── tools.rs    ← 5 tool implementations
    │   └── client.rs   ← HTTP client to phantom-core API (port 7437)
    └── README.md
```

## MCP Protocol Implementation

### `protocol.rs` — JSON-RPC 2.0 Types
```rust
#[derive(Deserialize)]
pub struct McpRequest {
    pub jsonrpc: String,
    pub id: Option<serde_json::Value>,
    pub method: String,
    pub params: Option<serde_json::Value>,
}

#[derive(Serialize)]
pub struct McpResponse {
    pub jsonrpc: String,
    pub id: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<McpError>,
}

#[derive(Serialize)]
pub struct McpError {
    pub code: i32,
    pub message: String,
}
```

### `main.rs` — stdio Transport Loop
```rust
fn main() {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let mut stdout = stdout.lock();
    
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        if line.trim().is_empty() { continue; }
        
        let request: McpRequest = serde_json::from_str(&line)
            .expect("Invalid JSON-RPC request");
        
        let response = dispatch(request);
        let json = serde_json::to_string(&response).unwrap();
        writeln!(stdout, "{}", json).unwrap();
        stdout.flush().unwrap();
    }
}
```

### `tools.rs` — 5 Tool Definitions + Implementations

#### Tool 1: `kairo_read_context`
```json
{
  "name": "kairo_read_context",
  "description": "Read the current text content and application context from the focused window on the user's desktop.",
  "inputSchema": { "type": "object", "properties": {} }
}
```
Implementation: `GET http://127.0.0.1:7437/context` → return JSON

#### Tool 2: `kairo_ghost_write`
```json
{
  "name": "kairo_ghost_write",
  "description": "Inject the given text into the currently focused window using clipboard-first injection (Ctrl+V).",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": { "type": "string", "description": "Text to inject into the focused window" }
    },
    "required": ["text"]
  }
}
```
Implementation: `POST http://127.0.0.1:7437/inject { "text": "..." }` → return success/error

#### Tool 3: `kairo_ask`
```json
{
  "name": "kairo_ask",
  "description": "Run a full ghost-writing round-trip: reads context, sends prompt to the AI swarm, and injects the response into the focused window.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": { "type": "string", "description": "The instruction for the AI agent" }
    },
    "required": ["prompt"]
  }
}
```
Implementation: `POST http://127.0.0.1:7437/ask { "prompt": "..." }` → streams response → return full text

#### Tool 4: `kairo_detect_app`
```json
{
  "name": "kairo_detect_app",
  "description": "Identify the currently active application and its type (Word, VS Code, Browser, etc.).",
  "inputSchema": { "type": "object", "properties": {} }
}
```
Implementation: `GET http://127.0.0.1:7437/app` → return `{ "process": "WINWORD.EXE", "environment": "MicrosoftWord" }`

#### Tool 5: `kairo_switch_agent`
```json
{
  "name": "kairo_switch_agent",
  "description": "Override the Swarm Brain's agent routing for the next request.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agent": { "type": "string", "enum": ["design", "reasoning", "content", "auto"] }
    },
    "required": ["agent"]
  }
}
```
Implementation: `POST http://127.0.0.1:7437/agent { "type": "design" }`

## Required Additions to `phantom-core/src/api.rs`
The existing HTTP API needs these new endpoints to support the MCP server:
- `GET /context` — returns `AppEnvironment` + focused text
- `POST /inject` — accepts `{ "text": "..." }` → injects via clipboard
- `POST /ask` — accepts `{ "prompt": "..." }` → full round-trip → returns response text
- `GET /app` — returns process name + AppEnvironment
- `POST /agent` — sets agent override for next request

## MCP Manifest JSON
`kairo-mcp/mcp-manifest.json`:
```json
{
  "name": "kairo-phantom",
  "version": "0.3.0",
  "description": "Ghost-write AI text into any desktop application",
  "tools": [
    { "name": "kairo_read_context", "...": "..." },
    ...
  ]
}
```

## User Integration Guide (README.md)

### Claude Code
```bash
claude mcp add kairo-phantom-mcp -- kairo-phantom-mcp
```

### Cursor
Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "kairo": {
      "command": "kairo-phantom-mcp",
      "args": []
    }
  }
}
```

### Goose
```yaml
# .goose/config.yaml
extensions:
  - type: stdio
    name: kairo
    cmd: kairo-phantom-mcp
```

## `kairo-mcp/Cargo.toml`
```toml
[package]
name = "kairo-phantom-mcp"
version = "0.3.0"

[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
reqwest = { version = "0.12", features = ["json", "blocking"] }
```

## Verification Checklist
- [ ] `echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' | kairo-phantom-mcp` returns valid response
- [ ] `echo '{"jsonrpc":"2.0","method":"tools/list","id":2}' | kairo-phantom-mcp` returns all 5 tools
- [ ] `kairo_ghost_write` with `"text": "Hello World"` injects into focused Notepad
- [ ] `kairo_ask` with `"prompt": "write a haiku"` replaces prompt in Notepad
- [ ] Claude Code integration works end-to-end with `claude mcp add`
- [ ] `kairo-phantom-mcp` exits cleanly when stdin closes

## Files Created/Modified
- `kairo-mcp/` (new crate)
- `phantom-core/src/api.rs` (5 new endpoints)
- `Cargo.toml` (workspace: add kairo-mcp member)
