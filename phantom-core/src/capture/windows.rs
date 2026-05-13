// phantom-core/src/capture/windows.rs
// Stubs for Windows UI Automation

pub fn capture_active_window() -> Result<(String, String), String> {
    // In real app, uses `windows` crate UIAutomation APIs
    // Returns (AppName, RawText)
    Ok(("Word.exe".to_string(), "Extracted text via UIA text pattern...".to_string()))
}
