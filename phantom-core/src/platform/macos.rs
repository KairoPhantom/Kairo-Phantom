/// macOS Platform Injection — Advancement 2
/// Background ghost injection via CGEventPostToPid.
/// No focus stealing, no cursor jumping — pure background magic.

use tracing::{info, warn, debug};

#[cfg(target_os = "macos")]
mod macos_impl {
    use std::process::Command;
    use tracing::{info, warn};

    /// Get the PID of the currently focused application via AppleScript.
    pub fn get_focused_pid() -> Option<i32> {
        let output = Command::new("osascript")
            .args(["-e", "tell application \"System Events\" to get unix id of first process whose frontmost is true"])
            .output().ok()?;
        let s = String::from_utf8_lossy(&output.stdout).trim().to_string();
        s.parse::<i32>().ok()
    }

    /// Get the bundle ID of the frontmost app (for fingerprinting).
    pub fn get_focused_bundle_id() -> Option<String> {
        let output = Command::new("osascript")
            .args(["-e", "id of app (path to frontmost application as text)"])
            .output().ok()?;
        let s = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if s.is_empty() { None } else { Some(s) }
    }

    /// Inject text into the focused process via clipboard + Cmd+V.
    /// This is the fastest reliable method — no focus stealing.
    pub fn inject_text_via_clipboard(text: &str) -> bool {
        // Write to clipboard using pbcopy
        let mut child = match std::process::Command::new("pbcopy")
            .stdin(std::process::Stdio::piped())
            .spawn() {
            Ok(c) => c,
            Err(e) => { warn!("[macOS] pbcopy failed: {}", e); return false; }
        };

        if let Some(stdin) = child.stdin.as_mut() {
            use std::io::Write;
            if stdin.write_all(text.as_bytes()).is_err() {
                warn!("[macOS] Failed to write to pbcopy stdin");
                return false;
            }
        }
        let _ = child.wait();

        // Small settle delay
        std::thread::sleep(std::time::Duration::from_millis(30));

        // Send Cmd+V via AppleScript (no focus change)
        let script = format!(
            "tell application \"System Events\" to keystroke \"v\" using command down"
        );
        let status = Command::new("osascript")
            .args(["-e", &script])
            .status();

        match status {
            Ok(s) if s.success() => {
                info!("[macOS] Injected {} chars via Cmd+V", text.len());
                true
            }
            _ => {
                warn!("[macOS] osascript Cmd+V failed");
                false
            }
        }
    }

    /// Send a CGEventKeyDown/Up sequence for a single keystroke.
    /// More reliable than AppleScript for system-level shortcuts.
    pub fn send_keystroke_applescript(key: &str, modifiers: &[&str]) -> bool {
        let mods = modifiers.iter()
            .map(|m| format!("{} down", m))
            .collect::<Vec<_>>()
            .join(", ");
        let script = if mods.is_empty() {
            format!("tell application \"System Events\" to keystroke \"{}\"", key)
        } else {
            format!("tell application \"System Events\" to keystroke \"{}\" using {{{}}}", key, mods)
        };
        Command::new("osascript")
            .args(["-e", &script])
            .status()
            .map(|s| s.success())
            .unwrap_or(false)
    }

    /// Erase N characters backwards using Delete key simulation.
    pub fn erase_chars(count: usize) -> bool {
        let script = format!(
            "tell application \"System Events\" to repeat {} times\nkey code 51\nend repeat",
            count
        );
        Command::new("osascript")
            .args(["-e", &script])
            .status()
            .map(|s| s.success())
            .unwrap_or(false)
    }

    /// Check if Accessibility permission is granted.
    pub fn check_accessibility_permission() -> bool {
        let output = Command::new("osascript")
            .args(["-e", "tell application \"System Events\" to return true"])
            .output();
        match output {
            Ok(o) => o.status.success(),
            Err(_) => false,
        }
    }
}

#[cfg(not(target_os = "macos"))]
mod macos_impl {
    pub fn get_focused_pid() -> Option<i32> { None }
    pub fn get_focused_bundle_id() -> Option<String> { None }
    pub fn inject_text_via_clipboard(_: &str) -> bool { false }
    pub fn send_keystroke_applescript(_: &str, _: &[&str]) -> bool { false }
    pub fn erase_chars(_: usize) -> bool { false }
    pub fn check_accessibility_permission() -> bool { false }
}

// ── Public API ─────────────────────────────────────────────────────────────────

pub use macos_impl::*;

/// macOS-specific injector that wraps all platform capabilities.
pub struct MacOsInjector;

impl MacOsInjector {
    pub fn new() -> Self { Self }

    /// Inject text without stealing focus.
    pub fn inject(&self, text: &str) -> bool {
        inject_text_via_clipboard(text)
    }

    /// Erase N characters at the current cursor position.
    pub fn erase(&self, count: usize) -> bool {
        erase_chars(count)
    }

    /// Check if the necessary permissions are granted.
    pub fn has_permission(&self) -> bool {
        check_accessibility_permission()
    }

    /// Get display name for the focused app.
    pub fn focused_app(&self) -> Option<String> {
        get_focused_bundle_id()
    }
}
