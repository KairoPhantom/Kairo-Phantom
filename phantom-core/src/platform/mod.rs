/// Kairo Phantom — Cross-Platform Accessibility Layer
/// 
/// Provides a unified trait for reading text from the focused UI element
/// across Windows (UIAutomation), macOS (AXUIElement), and Linux (AT-SPI2).
/// Each platform has its own implementation module, selected at compile time.
///
/// Architecture inspired by xa11y's unified API design, but implemented
/// natively using each platform's official accessibility APIs.

/// The canonical accessibility reader trait.
/// Every platform implements this to extract text from the focused UI element.
pub trait AccessibilityReader: Send + Sync {
    /// Read the full text content of the currently focused UI element.
    /// Returns the text or an error if the element is not accessible.
    fn get_focused_text(&self) -> anyhow::Result<String>;

    /// Read text from the system clipboard as a fallback.
    fn get_clipboard_text(&self) -> anyhow::Result<String>;
}

/// Construct the platform-appropriate AccessibilityReader at runtime.
pub fn new_reader() -> Box<dyn AccessibilityReader> {
    #[cfg(target_os = "windows")]
    {
        Box::new(windows::WindowsUiaReader::new())
    }
    #[cfg(target_os = "macos")]
    {
        Box::new(macos::MacOsAccessibilityReader::new())
    }
    #[cfg(target_os = "linux")]
    {
        Box::new(linux::LinuxAtspiReader::new())
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        compile_error!("Kairo Phantom requires Windows, macOS, or Linux.")
    }
}

// ─── Platform Modules ─────────────────────────────────────────────────────────

#[cfg(target_os = "windows")]
pub mod windows;

#[cfg(target_os = "macos")]
pub mod macos;

#[cfg(target_os = "linux")]
pub mod linux;
