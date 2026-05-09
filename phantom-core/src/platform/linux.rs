/// Linux AT-SPI2 implementation of the AccessibilityReader trait.
///
/// Phase 1: Stub implementation — clipboard reads work via xclip or wl-paste.
/// Phase 2 (future): Full AT-SPI2 implementation using the `atspi` crate
/// for reading focused element text via D-Bus.
///
/// Requires: xclip (X11) or wl-clipboard (Wayland) for clipboard operations.
/// Install: sudo apt install xclip   OR   sudo apt install wl-clipboard

use anyhow::Result;
use super::AccessibilityReader;

pub struct LinuxAtspiReader;

impl LinuxAtspiReader {
    pub fn new() -> Self {
        LinuxAtspiReader
    }
}

impl AccessibilityReader for LinuxAtspiReader {
    /// Read text from the focused UI element via AT-SPI2.
    ///
    /// Phase 1 stub: Returns an error with a clear message.
    /// TODO Phase 2: Implement using the `atspi` crate:
    ///   atspi::AccessibilityConnection::open()
    ///   → get_focused_object() → get_text(0, -1)
    fn get_focused_text(&self) -> Result<String> {
        anyhow::bail!(
            "Linux AT-SPI2 focused text reading not yet implemented (Phase 2). \
             Trigger via clipboard: copy your text first, then press Alt+M."
        )
    }

    /// Read from Linux clipboard via xclip (X11) or wl-paste (Wayland).
    /// Tries xclip first, falls back to wl-paste for Wayland sessions.
    fn get_clipboard_text(&self) -> Result<String> {
        // Try X11 clipboard first
        if let Ok(output) = std::process::Command::new("xclip")
            .args(["-selection", "clipboard", "-o"])
            .output()
        {
            if output.status.success() {
                return Ok(String::from_utf8_lossy(&output.stdout).into_owned());
            }
        }

        // Fallback: Wayland clipboard
        let output = std::process::Command::new("wl-paste")
            .output()
            .map_err(|_| anyhow::anyhow!(
                "Clipboard read failed. Install xclip (X11) or wl-clipboard (Wayland): \
                 sudo apt install xclip"
            ))?;
        Ok(String::from_utf8_lossy(&output.stdout).into_owned())
    }
}
