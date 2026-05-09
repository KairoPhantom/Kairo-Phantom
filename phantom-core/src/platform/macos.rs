/// macOS Accessibility implementation of the AccessibilityReader trait.
/// 
/// Phase 1: Stub implementation — clipboard reads work via pbpaste.
/// Phase 2 (future): Full AXUIElement implementation for reading focused element text
/// using the macOS Accessibility API (kAXFocusedUIElementAttribute).
///
/// To use this on macOS, the app must be granted Accessibility permissions
/// in System Preferences → Privacy & Security → Accessibility.

use anyhow::Result;
use super::AccessibilityReader;

pub struct MacOsAccessibilityReader;

impl MacOsAccessibilityReader {
    pub fn new() -> Self {
        MacOsAccessibilityReader
    }
}

impl AccessibilityReader for MacOsAccessibilityReader {
    /// Read text from the focused UI element via AXUIElement.
    ///
    /// Phase 1 stub: Returns an error with a clear message.
    /// TODO Phase 2: Implement using core-foundation + AXUIElement:
    ///   AXUIElementCreateSystemWide() → kAXFocusedUIElementAttribute
    ///   → kAXValueAttribute / kAXSelectedTextAttribute
    fn get_focused_text(&self) -> Result<String> {
        // Phase 1 stub: macOS UIA reading is planned for Phase 2.
        // For now, users on macOS can use the clipboard fallback path.
        anyhow::bail!(
            "macOS focused text reading not yet implemented (Phase 2). \
             Trigger via clipboard: copy your text first, then press Alt+M."
        )
    }

    /// Read from macOS clipboard via pbpaste command.
    /// This works immediately on macOS without Accessibility permissions.
    fn get_clipboard_text(&self) -> Result<String> {
        let output = std::process::Command::new("pbpaste")
            .output()
            .map_err(|e| anyhow::anyhow!("pbpaste failed: {}", e))?;
        Ok(String::from_utf8_lossy(&output.stdout).into_owned())
    }
}
