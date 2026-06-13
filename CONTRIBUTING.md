# Contributing to Kairo Phantom

Thank you for your interest in contributing! Kairo Phantom is a Rust-native AI ghost-writer that works across every app on your OS. This guide gets you from zero to a working development environment.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Building a Release Binary](#building-a-release-binary)
- [Adding a Waza Agent Plugin](#adding-a-waza-agent-plugin)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Code Style](#code-style)

---

## Development Setup

### Prerequisites

| Requirement | Version | Install |
|---|---|---|
| Rust | stable (≥ 1.78) | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| Ollama | latest | https://ollama.ai |
| Qwen 2.5 model | any | `ollama pull qwen2.5-coder:7b` |

### Clone and build

```bash
git clone https://github.com/KairoPhantom/Kairo-Phantom.git
cd Kairo-Phantom/phantom-core
cargo build
```

### First run

```bash
cargo run --bin kairo-phantom
```

Press `Alt+M` in any focused text field. The first-run wizard will guide you through Ollama configuration.

---

## Running Tests

### Unit + integration tests (all platforms)

```bash
cargo test --workspace
```

### E2E Gauntlet (39 real-world scenarios)

```bash
cargo test --test e2e_memory_gauntlet
```

Expected output: `test result: ok. 3 passed; 0 failed`

### Memory intelligence benchmark

```bash
cargo run --release --bin memory_benchmark
```

Expected: `Final Average Composite Score (30 sessions): ≥ 0.95`

### Strict lint gate (must pass before PR)

```bash
cargo clippy --all-targets -- -D warnings
```

Expected: zero errors, zero warnings.

---

## Building a Release Binary

```bash
cargo build --release
# Binary at: target/release/kairo-phantom
```

---

## Adding a Waza Agent Plugin

Kairo's routing system is driven by TOML agent definitions in `plugins/`.

1. Create `plugins/my-agent.toml`:

```toml
[agent]
id = "my-agent"
display_name = "My Custom Agent"
description = "Specialized for legal contract summarization."

[routing]
# App names that trigger this agent (case-insensitive substring match)
preferred_apps = ["Word", "Chrome", "Adobe"]
# Keyword signals in the prompt that increase this agent's score
keywords = ["contract", "clause", "liability", "indemnify"]

[persona]
system_prompt = """
You are a legal writing specialist. You produce concise, precise legal summaries.
Always use plain English. Never hallucinate case citations.
"""
```

2. Test it:

```bash
cargo test --test e2e_memory_gauntlet
```

3. Submit a PR — include the TOML file and a short description of the use case.

### Publishing a community agent

You can publish your agent as a GitHub repository. Users install it with:

```bash
kairo agent install github.com/your-org/your-agent
```

The agent must contain a valid `agent.toml` at the repo root.

---

## Pull Request Guidelines

- **One concern per PR.** Bug fixes and features in separate PRs.
- **All tests must pass.** `cargo test --workspace` and `cargo clippy --all-targets -- -D warnings`.
- **No new `unsafe` blocks** without a documented safety comment.
- **New public APIs require documentation.** Add `///` doc comments.
- **Link to the issue** your PR addresses, if applicable.

---

## Code Style

Kairo Phantom follows standard Rust idioms:

```bash
cargo fmt --all
cargo clippy --all-targets -- -D warnings
```

Both must pass cleanly before a PR is merged.

---

## Questions?

Open a [GitHub Discussion](https://github.com/KairoPhantom/Kairo-Phantom/discussions) or file an issue. We're a friendly community.
