# Kairo Phantom v3.0 — Requirements

## Milestone Goal
Transform Kairo Phantom from a Windows-only ghost-typing engine into the **universal, offline-capable, cross-platform, MCP-distributed document AI peer** that no other open-source project delivers.

## Context for Agents
All agents implementing these requirements MUST follow:
1. **Build original code** — reference external crate APIs for integration patterns, never copy implementations verbatim
2. **Compile on stable Rust** — no nightly features unless gated behind `#[cfg(feature)]`
3. **Every phase must build cleanly** — `cargo build --release` must succeed before a phase is considered done
4. **Backwards compatible** — existing config.toml files must continue to work

---

## Requirement 1: Cross-Platform Accessibility Layer (Pillar 1)
**Priority:** High | **Week:** 1-2

### Current State
- `uia.rs` uses `uiautomation-rs` which is Windows-only
- Kairo cannot run on macOS or Linux

### Required
- Create a new `phantom-core/src/platform/` module with platform-specific implementations
- `platform/windows.rs` — wraps `uiautomation-rs` (current implementation)
- `platform/macos.rs` — uses `accessibility-rs` or `core-foundation` + AXUIElement for macOS text extraction
- `platform/linux.rs` — uses AT-SPI2 via `atspi` crate for Linux text extraction
- Common trait: `pub trait AccessibilityReader: Send + Sync { fn get_focused_text(&self) -> Result<String>; fn get_clipboard_text(&self) -> Result<String>; }`
- Compile-time platform selection via `#[cfg(target_os)]`
- **DO NOT** depend on xa11y as a direct dependency; implement the trait natively using each platform's official APIs
- The `AppEnvironment` detection in `context.rs` must also work cross-platform (use process name matching for all platforms)

### Acceptance Criteria
- `cargo build --release` passes on Windows
- `cargo build --release` passes on macOS (CI check)
- `cargo build --release` passes on Linux (CI check)
- All existing `AppEnvironment` detection works unchanged

---

## Requirement 2: Deep Document Understanding (Pillar 2)
**Priority:** High | **Week:** 3-4

### Current State
- `context.rs` extracts raw text only from the focused UI element
- No awareness of document structure (headings, tables, slide numbers)

### Required
- Create `phantom-core/src/document_context.rs` implementing the trait architecture from `newfeature.md`
- `DocumentContext` struct with: `doc_kind`, `full_text`, `outline: Vec<OutlineItem>`, `tables: Vec<TableData>`, `active_slide`, `total_slides`, `has_tracked_changes`, `format_metadata`
- `DocumentContextExtractor` async trait with `handles()`, `extract()`, `can_handle_extension()`
- `ExtractorRegistry` for plugin registration
- Add `office_oxide` as optional dependency (feature flag: `feature = "office"`)
  - DOCX extractor: heading outline from paragraph styles, table extraction, tracked-change detection
  - PPTX extractor: slide count, per-slide text, active_slide inference from window title
  - XLSX extractor: sheet names, CSV extraction per sheet
- Fallback: when file path is unavailable, fall back to UIA raw text (current behavior)
- Wire `DocumentContext::to_system_prompt_fragment()` into the Swarm Brain system prompt
- `context.rs` must attempt to resolve the active file path from: window title → process args → recent files registry

### Acceptance Criteria
- Opening Word with a .docx file and pressing Alt+M sends the heading outline to the LLM
- Opening PowerPoint and pressing Alt+M includes "Currently on slide X/Y" in the system prompt
- For apps without a file path (browser, Notepad), graceful fallback to current UIA-only behavior
- Feature compiles cleanly with and without `--features office`

---

## Requirement 3: Offline Mode — Ollama First (Pillar 3)
**Priority:** High | **Week:** 5-6

### Current State
- Config defaults to `provider = "openai"` 
- No offline detection or user-facing guidance

### Required
- Change default `provider` to `"ollama"` in `config.rs`
- Change default `model_name` to `"qwen2.5-coder:14b"` for the reasoning agent, `"llama3.2"` for content/design
- On startup: detect if Ollama is running (GET `http://localhost:11434/api/tags`)
- If Ollama not found: print a clear one-liner setup prompt (no panic)
  ```
  ⚠ Ollama not detected. Get offline AI in 2 commands:
    winget install Ollama.Ollama
    ollama pull qwen2.5-coder:14b
  Kairo will retry Ollama every 30s, or add an API key to config.toml for cloud mode.
  ```
- If model not pulled: use `ollama pull <model>` automatically (with user consent prompt via overlay/log)
- `config.toml` `fallback` field: if Ollama fails on a request, retry once with the fallback provider
- The existing `OllamaBackend` in `ai.rs` must be refactored to use the official Ollama HTTP API properly (streaming, model selection, context length)

### Acceptance Criteria
- A user with Ollama + qwen2.5-coder:14b and NO API keys can use Kairo fully offline
- Clear log messages at startup indicating which provider is active
- Cloud fallback works transparently when Ollama fails

---

## Requirement 4: MCP Server (Pillar 4)
**Priority:** High | **Week:** 7-8

### Current State
- Kairo exposes an HTTP API on port 7437 (internal only)
- No MCP protocol support

### Required
- Create new crate `kairo-mcp/` (sibling to `phantom-core/`)
- Implement MCP server over **stdio transport** (compatible with Claude Code, Cursor, Goose without config)
- Expose exactly these 5 tools:
  ```
  kairo_read_context  → reads text + AppEnvironment from focused window → returns JSON
  kairo_ghost_write   → accepts text string → injects via Clipboard-First → returns success/error
  kairo_ask           → accepts prompt string → runs full Alt+M round-trip → returns AI response text
  kairo_detect_app    → returns active process name + AppEnvironment enum → returns JSON
  kairo_switch_agent  → accepts agent_type string → overrides Swarm Brain routing for next request
  ```
- MCP server communicates with `phantom-core` via the existing HTTP API on port 7437
- `kairo-mcp` is a thin adapter; all logic stays in `phantom-core`
- Ship as a separate binary: `cargo install kairo-phantom-mcp`
- MCP manifest JSON for tool definitions
- README with Claude Code integration instructions (`claude mcp add kairo-phantom-mcp`)
- **DO NOT** copy mouseless or other MCP server implementations; implement MCP stdio protocol from the official spec

### Acceptance Criteria
- `echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | kairo-phantom-mcp` returns the 5 tool definitions
- `kairo_ask` tool works end-to-end with Claude Code
- `kairo_ghost_write` injects text into the focused window correctly

---

## Requirement 5: Plugin System + Trait Extraction (Pillar 5)
**Priority:** Medium | **Week:** 9-10

### Required
- Extract `AppContext` trait from `context.rs`:
  ```rust
  pub trait AppFingerprinter: Send + Sync {
      fn detect(&self, process_name: &str, window_title: &str) -> Option<AppEnvironment>;
      fn directive(&self, env: &AppEnvironment) -> Option<&'static str>;
  }
  ```
- Extract `SwarmAgent` trait from `swarm.rs`:
  ```rust
  pub trait SwarmAgent: Send + Sync {
      fn name(&self) -> &str;
      fn agent_type(&self) -> AgentType;
      fn system_prompt(&self, ctx: &DocumentContext) -> String;
      fn model_preference(&self) -> Option<ModelConfig>;
      fn should_handle(&self, ctx: &DocumentContext) -> bool;
  }
  ```
- `AgentRegistry` and `FingerprinterRegistry` (mirrors `ExtractorRegistry` pattern)
- Config: `[plugins]` section in config.toml pointing to plugin TOML files
- Plugin TOML format for community plugins:
  ```toml
  [plugin]
  name = "autocad-fingerprinter"
  fingerprinter = { process = "acad.exe", environment = "AutoCAD" }
  agent_prompt = "You are writing inside AutoCAD..."
  ```
- `kairo-plugin init <name>` CLI command scaffolds a new plugin TOML

### Acceptance Criteria
- Built-in agents refactored to implement `SwarmAgent` trait
- A third-party plugin TOML file can add a new `AppEnvironment` without recompiling Kairo
- `kairo-plugin init` generates a valid plugin template

---

## Requirement 6: One-Liner Install + Distribution
**Priority:** Medium | **Week:** 11-12

### Required
- `cargo install kairo-phantom` must work from crates.io
- `winget install kairo-phantom` manifest submitted
- `brew install kairo-phantom` Homebrew formula for macOS
- GitHub Actions CI: build on Ubuntu, macOS, Windows → upload artifacts
- Version bumped to `0.3.0` in all Cargo.toml files
- `CHANGELOG.md` following Keep a Changelog format
- Updated `README.md` with the full v3.0 architecture diagram (ASCII art from roadmap)

### Acceptance Criteria
- Fresh machine with only Rust installed can `cargo install kairo-phantom` and have it working
- GitHub Actions passes on all three platforms
- `kairo-phantom --version` prints `0.3.0`
