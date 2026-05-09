# Changelog — Kairo Phantom

## [0.3.0] — 2026-05-09
### Added
- **Plugin System:** Support for custom `AppFingerprinter` and `SwarmAgent` via TOML configuration.
- **MCP Server:** Integrated `kairo-mcp` for seamless use with Claude Code, Cursor, and Goose.
- **Deep Document Understanding:** Zip+XML extraction for Word (.docx), PowerPoint (.pptx), and Excel (.xlsx).
- **Multi-Agent Swarm:** Specialized agents for Design, Reasoning, and Content with intelligent routing.
- **Offline-First:** Default Ollama support with Qwen 2.5 Coder.
- **Context Engine:** Automatic file path and slide number resolution from active windows.

### Changed
- Refactored `ContextEngine` and `SwarmOrchestrator` to use trait-based registries.
- Improved Win32 ghost-writing speed and reliability.
- Updated README with professional documentation and architectural diagrams.

### Fixed
- Resolved multiple build warnings and unused import issues.
- Fixed must_use warnings for Win32 API calls.

## [0.2.0] — 2026-04-15
- Core ghost-typing loop in Rust.
- Initial UIAutomation (UIA) support for Windows.
- Basic Ollama integration.

## [0.1.0] — 2026-03-01
- Project inception.
