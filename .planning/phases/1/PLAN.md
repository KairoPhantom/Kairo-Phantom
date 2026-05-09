# Phase 1 Plan: Cross-Platform Accessibility Foundation
# Kairo Phantom v3.0

## Objective
Refactor `uia.rs` into a trait-based, cross-platform platform module that compiles cleanly on Windows, macOS, and Linux. This is the foundational unblocking phase for all subsequent pillars.

## Context Given to Agents
- **Current state:** `uia.rs` uses `uiautomation-rs` (Windows-only). It must be refactored, NOT rewritten from scratch — it already works on Windows.
- **We are NOT using xa11y as a dependency.** We reference xa11y's design (unified trait API) but implement each platform backend using native, platform-specific crates.
- **macOS and Linux are stubs in Phase 1** — they must compile cleanly with `Ok("")` fallbacks and proper `#[cfg(target_os)]` gating.
- **Zero regressions** — all current Alt+M functionality must work identically on Windows after this refactor.

## Architecture Designed by Software Architect Agent

```
phantom-core/src/
├── platform/
│   ├── mod.rs          ← Trait definition + platform selector
│   ├── windows.rs      ← Refactored uia.rs (Windows UIAutomation)
│   ├── macos.rs        ← Stub (accessibility-rs, graceful compile)
│   └── linux.rs        ← Stub (atspi, graceful compile)
└── uia.rs              ← Replaced by: pub use platform::AccessibilityReader;
```

## Implementation Steps

### Step 1.1 — Create `platform/mod.rs` with the `AccessibilityReader` trait
File: `phantom-core/src/platform/mod.rs`

```rust
/// Cross-platform accessibility trait.
/// Each platform implements this for reading focused UI element text.
pub trait AccessibilityReader: Send + Sync {
    /// Read text from the currently focused UI element (UIA, AXUIElement, AT-SPI2).
    fn get_focused_text(&self) -> anyhow::Result<String>;
    /// Fallback: read from system clipboard.
    fn get_clipboard_text(&self) -> anyhow::Result<String>;
}

/// Platform-specific constructor
pub fn new_reader() -> Box<dyn AccessibilityReader> {
    #[cfg(target_os = "windows")]
    { Box::new(windows::WindowsUiaReader::new()) }
    #[cfg(target_os = "macos")]
    { Box::new(macos::MacOsAccessibilityReader::new()) }
    #[cfg(target_os = "linux")]
    { Box::new(linux::LinuxAtspiReader::new()) }
    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    { compile_error!("Unsupported platform") }
}

// Re-exports
#[cfg(target_os = "windows")]
pub mod windows;
#[cfg(target_os = "macos")]
pub mod macos;
#[cfg(target_os = "linux")]
pub mod linux;
```

### Step 1.2 — Move `uia.rs` → `platform/windows.rs`
- The existing `UiaReader` struct becomes `WindowsUiaReader`
- Implement `AccessibilityReader` trait for `WindowsUiaReader`
- Keep all existing Win32 UIA logic unchanged
- Remove `pub use` re-exports from old `uia.rs` — replace with `pub use platform::new_reader`

### Step 1.3 — Create `platform/macos.rs` stub
```rust
pub struct MacOsAccessibilityReader;
impl MacOsAccessibilityReader {
    pub fn new() -> Self { Self }
}
impl super::AccessibilityReader for MacOsAccessibilityReader {
    fn get_focused_text(&self) -> anyhow::Result<String> {
        // Phase 1 stub: macOS AXUIElement implementation in Phase 2
        anyhow::bail!("macOS accessibility not yet implemented")
    }
    fn get_clipboard_text(&self) -> anyhow::Result<String> {
        // Read from pbpaste / NSPasteboard
        let output = std::process::Command::new("pbpaste").output()?;
        Ok(String::from_utf8_lossy(&output.stdout).into_owned())
    }
}
```

### Step 1.4 — Create `platform/linux.rs` stub
```rust
pub struct LinuxAtspiReader;
impl LinuxAtspiReader {
    pub fn new() -> Self { Self }
}
impl super::AccessibilityReader for LinuxAtspiReader {
    fn get_focused_text(&self) -> anyhow::Result<String> {
        anyhow::bail!("Linux AT-SPI2 not yet implemented")
    }
    fn get_clipboard_text(&self) -> anyhow::Result<String> {
        let output = std::process::Command::new("xclip")
            .args(["-selection", "clipboard", "-o"])
            .output()
            .or_else(|_| std::process::Command::new("wl-paste").output())?;
        Ok(String::from_utf8_lossy(&output.stdout).into_owned())
    }
}
```

### Step 1.5 — Update `main.rs` imports
Replace all `use crate::uia::UiaReader` with `use crate::platform;` and `platform::new_reader()`.

### Step 1.6 — Update `Cargo.toml` with platform-specific dependencies
```toml
[target.'cfg(target_os = "windows")'.dependencies]
uiautomation = { version = "0.7", features = ["process"] }

[target.'cfg(target_os = "macos")'.dependencies]
# accessibility-rs or core-foundation for future implementation
# core-foundation = "0.9"

[target.'cfg(target_os = "linux")'.dependencies]
# atspi = "0.22" for future AT-SPI2 implementation
```

### Step 1.7 — GitHub Actions CI
File: `.github/workflows/ci.yml`
```yaml
jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - run: cargo build --release -p phantom-core
```

## Verification Checklist
- [ ] `cargo build --release -p phantom-core` passes on Windows with no regressions
- [ ] `cargo check --target x86_64-apple-darwin` passes (macOS stub)
- [ ] `cargo check --target x86_64-unknown-linux-gnu` passes (Linux stub)
- [ ] Alt+M still works identically on Windows
- [ ] `uia.rs` replaced by `platform/` module (old file deleted)
- [ ] `AppEnvironment` detection in `context.rs` works unchanged
- [ ] CI workflow file added to `.github/workflows/`

## Files Modified
- `phantom-core/src/platform/mod.rs` (new)
- `phantom-core/src/platform/windows.rs` (new, content from uia.rs)
- `phantom-core/src/platform/macos.rs` (new stub)
- `phantom-core/src/platform/linux.rs` (new stub)
- `phantom-core/src/uia.rs` (deleted, replaced)
- `phantom-core/src/main.rs` (updated imports)
- `phantom-core/Cargo.toml` (platform-specific deps)
- `.github/workflows/ci.yml` (new)
