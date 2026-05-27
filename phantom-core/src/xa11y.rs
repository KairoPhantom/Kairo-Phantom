// phantom-core/src/xa11y.rs
//!
//! xa11y — Unified Accessibility API for Kairo Phantom
//! ====================================================
//!
//! Domain 11: Cross-Platform Hardening
//!
//! Provides a single `Xa11yContext` struct that reads the focused element's
//! text content and application identity on Windows, macOS, and Linux.
//!
//! Architecture:
//!   - Windows: delegates to `platform::windows::WindowsUiaReader` (uiautomation)
//!   - macOS:   delegates to `platform::macos::MacOsAccessibilityReader`
//!   - Linux:   delegates to `platform::linux::LinuxAtspiReader`
//!
//! All three backends implement `platform::AccessibilityReader`, so
//! `Xa11yContext` just calls `platform::new_reader()` uniformly.

use crate::platform;

/// A single accessible UI node returned from the platform accessibility API.
#[derive(Debug, Clone)]
pub struct AccessibleNode {
    /// Human-readable name/label of the element
    pub name: String,
    /// Accessibility role (e.g., "document", "text", "AXTextField", "Edit")
    pub role: String,
    /// Text value / content of the element
    pub value: String,
    /// Bounding box: (x, y, width, height) in screen coordinates
    pub bounds: (f64, f64, f64, f64),
}

/// Cross-platform accessibility context.
///
/// Wraps the platform-specific `AccessibilityReader` implementation
/// behind a uniform interface. Replaces direct `uiautomation` calls that
/// were Windows-only before Domain 11.
///
/// # Example
/// ```rust,no_run
/// use phantom_core::xa11y::Xa11yContext;
/// let ctx = Xa11yContext::new();
/// match ctx.get_focused_node() {
///     Ok(node) => println!("Focused: {} ({})", node.name, node.role),
///     Err(e) => eprintln!("Accessibility error: {}", e),
/// }
/// ```
pub struct Xa11yContext {
    reader: Box<dyn platform::AccessibilityReader>,
}

impl Xa11yContext {
    /// Create a new `Xa11yContext` with the appropriate platform backend.
    /// On Windows → `WindowsUiaReader`, macOS → `MacOsAccessibilityReader`,
    /// Linux → `LinuxAtspiReader`.
    pub fn new() -> Self {
        Xa11yContext {
            reader: platform::new_reader(),
        }
    }

    /// Retrieve the focused element's text across all platforms.
    ///
    /// Implementation per platform:
    /// - **Windows**: UITextPattern → UIValuePattern → clipboard fallback
    /// - **macOS**:   AXUIElement via macos-accessibility-client → pbpaste fallback
    /// - **Linux**:   AT-SPI2 via pyatspi (if available) → clipboard select-all fallback
    pub fn get_focused_node(&self) -> Result<AccessibleNode, Box<dyn std::error::Error>> {
        let text = self.reader.get_focused_text()?;
        let platform_role = Self::platform_role_name();

        Ok(AccessibleNode {
            name: Self::extract_element_name(&text),
            role: platform_role.to_string(),
            value: text,
            bounds: (0.0, 0.0, 0.0, 0.0), // Bounds not available via text-only API
        })
    }

    /// Read clipboard content (cross-platform fallback for context capture).
    pub fn get_clipboard_text(&self) -> Result<String, Box<dyn std::error::Error>> {
        Ok(self.reader.get_clipboard_text()?)
    }

    /// Detect the active application and return (process_name, window_title).
    /// Delegates to the context engine's cross-platform implementation.
    pub fn detect_active_application(&self) -> (String, String) {
        // Re-use the ContextEngine's cross-platform detection
        let engine = crate::context::ContextEngine::new();
        // Capture a dummy context to get process/title info
        let ctx = engine.capture("");
        (ctx.process_name, ctx.window_title)
    }

    /// Returns the platform-appropriate accessibility role name for the
    /// focused document/text element.
    pub fn platform_role_name() -> &'static str {
        #[cfg(windows)]        { "Edit" }      // Windows UIA ControlType
        #[cfg(target_os = "macos")] { "AXTextArea" } // macOS AX role
        #[cfg(target_os = "linux")] { "text" }       // AT-SPI2 role
        #[cfg(not(any(windows, target_os = "macos", target_os = "linux")))]
        { "unknown" }
    }

    /// Extract a short element name from the full document text.
    /// Returns the first non-empty line (truncated to 80 chars) as the name.
    pub fn extract_element_name(text: &str) -> String {
        text.lines()
            .find(|l| !l.trim().is_empty())
            .map(|l| {
                let trimmed = l.trim();
                if trimmed.len() > 80 {
                    format!("{}…", &trimmed[..77])
                } else {
                    trimmed.to_string()
                }
            })
            .unwrap_or_else(|| "<empty document>".to_string())
    }
}

impl Default for Xa11yContext {
    fn default() -> Self {
        Self::new()
    }
}

/// Convenience: get the focused text directly without constructing Xa11yContext.
pub fn get_focused_text() -> anyhow::Result<String> {
    let reader = platform::new_reader();
    reader.get_focused_text()
}

/// Convenience: check platform accessibility permissions.
pub fn check_accessibility_permissions() -> AccessibilityStatus {
    #[cfg(windows)]
    { AccessibilityStatus::Available } // Windows: no explicit permission needed for UIAutomation

    #[cfg(target_os = "macos")]
    {
        // Check if the process has accessibility access
        use std::process::Command;
        let out = Command::new("osascript")
            .args(["-e", r#"tell application "System Events" to get name of first process whose frontmost is true"#])
            .output();
        match out {
            Ok(o) if o.status.success() => AccessibilityStatus::Available,
            _ => AccessibilityStatus::PermissionRequired {
                message: "Grant Accessibility access in System Preferences → Privacy & Security → Accessibility".into(),
            },
        }
    }

    #[cfg(target_os = "linux")]
    {
        // Check if xdotool is available
        use std::process::Command;
        match Command::new("xdotool").args(["version"]).output() {
            Ok(o) if o.status.success() => AccessibilityStatus::Available,
            _ => AccessibilityStatus::ToolsMissing {
                tools: vec![
                    "xdotool (sudo apt install xdotool)".into(),
                    "xclip (sudo apt install xclip)".into(),
                ],
            },
        }
    }

    #[cfg(not(any(windows, target_os = "macos", target_os = "linux")))]
    { AccessibilityStatus::Unsupported }
}

/// Result of an accessibility permission check.
#[derive(Debug, Clone)]
pub enum AccessibilityStatus {
    /// Accessibility API is available and permissions are granted.
    Available,
    /// macOS: The user must grant permission in System Preferences.
    PermissionRequired { message: String },
    /// Linux: Required command-line tools are missing.
    ToolsMissing { tools: Vec<String> },
    /// The current OS is not supported.
    Unsupported,
}

impl AccessibilityStatus {
    pub fn is_available(&self) -> bool {
        matches!(self, AccessibilityStatus::Available)
    }

    pub fn user_message(&self) -> String {
        match self {
            AccessibilityStatus::Available => "✅ Accessibility available".into(),
            AccessibilityStatus::PermissionRequired { message } =>
                format!("⚠️  Permission required: {}", message),
            AccessibilityStatus::ToolsMissing { tools } =>
                format!("⚠️  Missing tools: {}", tools.join(", ")),
            AccessibilityStatus::Unsupported =>
                "❌ Accessibility not supported on this platform".into(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_xa11y_context_construction() {
        // Must not panic on any platform
        let _ctx = Xa11yContext::new();
    }

    #[test]
    fn test_xa11y_default() {
        let _ctx = Xa11yContext::default();
    }

    #[test]
    fn test_extract_element_name_empty() {
        let name = Xa11yContext::extract_element_name("");
        assert_eq!(name, "<empty document>");
    }

    #[test]
    fn test_extract_element_name_normal() {
        let name = Xa11yContext::extract_element_name("Hello world\nMore text");
        assert_eq!(name, "Hello world");
    }

    #[test]
    fn test_extract_element_name_truncates_long_line() {
        let long = "a".repeat(100);
        let name = Xa11yContext::extract_element_name(&long);
        assert!(name.len() <= 81); // 77 chars + "…"
    }

    #[test]
    fn test_accessibility_status_is_available() {
        let status = check_accessibility_permissions();
        // We can't guarantee Available in all CI environments,
        // but the function must not panic
        let _ = status.user_message();
    }

    #[test]
    fn test_platform_role_name_not_empty() {
        let role = Xa11yContext::platform_role_name();
        assert!(!role.is_empty());
    }

    #[test]
    fn test_get_focused_text_does_not_panic() {
        // get_focused_text() may return Err in headless CI — that's fine.
        // The critical thing is it compiles and doesn't panic.
        let result = get_focused_text();
        // Result may be Ok or Err depending on environment
        let _ = result;
    }
}
