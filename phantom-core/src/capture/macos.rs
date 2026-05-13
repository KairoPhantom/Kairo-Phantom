// phantom-core/src/capture/macos.rs
// Stubs for macOS Accessibility API

pub fn capture_active_window() -> Result<(String, String), String> {
    // In real app, uses AX UI Element APIs
    // Returns (AppName, RawText)
    Ok(("Pages.app".to_string(), "Extracted text via AX...".to_string()))
}
