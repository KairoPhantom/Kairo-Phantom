// phantom-core/src/platform/linux.rs
//
// Linux Platform Implementation — Cross-Platform Hardening (Domain 11)
//
// Provides:
//   1. LinuxAtspiReader — AccessibilityReader impl via subprocess (xdotool + xclip)
//   2. LinuxInjector   — Text injection via clipboard + xdotool/ydotool/wl-tools
//
// Why subprocess-based: The `atspi` crate requires AT-SPI2 daemon, D-Bus, and
// tokio-async context which conflicts with our sync platform trait. Subprocess
// calls to xdotool/xclip are the standard approach used by 90% of Linux automation
// tools and work on both X11 and Wayland environments.
//
// Requirements: xdotool + xclip (X11) or ydotool + wl-clipboard (Wayland)
// Install: sudo apt install xdotool xclip  (or ydotool wl-clipboard for Wayland)

use tracing::{info, warn};

// ── Shared subprocess helpers (always compiled, cfg-gated internally) ─────────

#[cfg(target_os = "linux")]
mod linux_impl {
    use std::process::Command;
    use tracing::{info, warn};

    /// Detect display server: X11 or Wayland.
    pub fn detect_display_server() -> &'static str {
        if std::env::var("WAYLAND_DISPLAY").is_ok() { "wayland" }
        else if std::env::var("DISPLAY").is_ok() { "x11" }
        else { "unknown" }
    }

    /// Get the focused window title on X11/Wayland.
    /// Primary: xdotool getactivewindow getwindowname
    /// Fallback: wmctrl -l (headless environments)
    pub fn get_active_window_title() -> Option<String> {
        // X11 via xdotool
        if let Ok(output) = Command::new("xdotool")
            .args(["getactivewindow", "getwindowname"])
            .output()
        {
            let s = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !s.is_empty() { return Some(s); }
        }

        // Wayland: try wmctrl (works on most compositors)
        if let Ok(output) = Command::new("wmctrl").args(["-l"]).output() {
            let lines = String::from_utf8_lossy(&output.stdout);
            // wmctrl -l format: "0x01200001  0 hostname  Window Title"
            if let Some(first_active) = lines.lines().last() {
                let parts: Vec<&str> = first_active.splitn(5, char::is_whitespace).collect();
                if parts.len() >= 5 {
                    return Some(parts[4..].join(" ").trim().to_string());
                }
            }
        }

        None
    }

    /// Get the focused application process name on Linux.
    /// Uses: xdotool getactivewindow getwindowpid → /proc/<pid>/comm
    pub fn get_active_process_name() -> Option<String> {
        // xdotool getactivewindow → window ID, then getwindowpid
        let wid_out = Command::new("xdotool")
            .args(["getactivewindow"])
            .output()
            .ok()?;
        let wid = String::from_utf8_lossy(&wid_out.stdout).trim().to_string();
        if wid.is_empty() { return None; }

        let pid_out = Command::new("xdotool")
            .args(["getwindowpid", &wid])
            .output()
            .ok()?;
        let pid = String::from_utf8_lossy(&pid_out.stdout).trim().to_string();
        if pid.is_empty() { return None; }

        // Read /proc/<pid>/comm — the short process name
        let comm = std::fs::read_to_string(format!("/proc/{}/comm", pid)).ok()?;
        Some(comm.trim().to_string())
    }

    /// Get the focused element's text content via AT-SPI2 CLI (if available)
    /// or fall back to clipboard-based selection.
    pub fn get_focused_text() -> anyhow::Result<String> {
        // Strategy 1: Try AT-SPI2 via at-spi-bus-launcher + gdbus
        // This works when the accessibility bus is active
        if let Some(text) = try_atspi_focused_text() {
            return Ok(text);
        }

        // Strategy 2: Select-all + clipboard read (universal fallback)
        // Saves current clipboard, does Ctrl+A + Ctrl+C, reads, restores
        let original_clip = read_clipboard().unwrap_or_default();

        // Select all text in focused app and copy
        let server = detect_display_server();
        if server == "wayland" {
            let _ = Command::new("ydotool").args(["key", "ctrl+a"]).status();
            std::thread::sleep(std::time::Duration::from_millis(100));
            let _ = Command::new("ydotool").args(["key", "ctrl+c"]).status();
        } else {
            let _ = Command::new("xdotool").args(["key", "ctrl+a"]).status();
            std::thread::sleep(std::time::Duration::from_millis(100));
            let _ = Command::new("xdotool").args(["key", "ctrl+c"]).status();
        }
        std::thread::sleep(std::time::Duration::from_millis(100));

        let selected = read_clipboard().unwrap_or_default();

        // Restore original clipboard content
        if !original_clip.is_empty() {
            write_clipboard(&original_clip);
        }

        // Deselect
        if server == "wayland" {
            let _ = Command::new("ydotool").args(["key", "End"]).status();
        } else {
            let _ = Command::new("xdotool").args(["key", "End"]).status();
        }

        Ok(selected)
    }

    /// Try to get focused element text via AT-SPI2 bus (D-Bus query).
    /// Returns None if AT-SPI2 is not available or fails.
    fn try_atspi_focused_text() -> Option<String> {
        // Check if AT-SPI bus is running
        let bus_addr = std::env::var("AT_SPI_BUS_ADDRESS").ok()
            .or_else(|| {
                // Try to detect via D-Bus
                Command::new("dbus-send")
                    .args([
                        "--print-reply",
                        "--dest=org.a11y.Bus",
                        "/org/a11y/bus",
                        "org.a11y.Bus.GetAddress"
                    ])
                    .output()
                    .ok()
                    .filter(|o| o.status.success())
                    .and_then(|o| {
                        let out = String::from_utf8_lossy(&o.stdout).to_string();
                        // Parse the D-Bus address from the reply
                        out.split_whitespace()
                            .find(|s| s.starts_with("\"unix:") || s.starts_with("\"tcp:"))
                            .map(|s| s.trim_matches('"').to_string())
                    })
            });

        if bus_addr.is_none() {
            return None; // AT-SPI not available
        }

        // AT-SPI is available — query focused element text via python-atspi if installed
        // (python3 -c "import pyatspi; ...") - common on GNOME systems
        let result = Command::new("python3")
            .args([
                "-c",
                r#"
import sys
try:
    import pyatspi
    desktop = pyatspi.Registry.getDesktop(0)
    for app in desktop:
        for obj in pyatspi.findDescendant(app, lambda x: x.getState().contains(pyatspi.STATE_FOCUSED), False):
            text_iface = obj.queryText()
            print(text_iface.getText(0, -1))
            sys.exit(0)
except Exception as e:
    sys.exit(1)
"#
            ])
            .output()
            .ok()?;

        if result.status.success() {
            let text = String::from_utf8_lossy(&result.stdout).trim().to_string();
            if !text.is_empty() { return Some(text); }
        }
        None
    }

    /// Read from clipboard (X11 via xclip, Wayland via wl-paste)
    pub fn read_clipboard() -> Option<String> {
        let server = detect_display_server();
        if server == "wayland" {
            Command::new("wl-paste")
                .args(["--no-newline"])
                .output()
                .ok()
                .filter(|o| o.status.success())
                .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
        } else {
            // Try xclip first, then xsel as fallback
            Command::new("xclip")
                .args(["-selection", "clipboard", "-o"])
                .output()
                .ok()
                .filter(|o| o.status.success())
                .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
                .or_else(|| {
                    Command::new("xsel")
                        .args(["--clipboard", "--output"])
                        .output()
                        .ok()
                        .filter(|o| o.status.success())
                        .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
                })
        }
    }

    /// Write text to clipboard (X11 via xclip, Wayland via wl-copy).
    pub fn write_clipboard(text: &str) -> bool {
        let server = detect_display_server();
        let mut child = if server == "wayland" {
            match Command::new("wl-copy").stdin(std::process::Stdio::piped()).spawn() {
                Ok(c) => c,
                Err(_) => return false,
            }
        } else {
            match Command::new("xclip")
                .args(["-selection", "clipboard"])
                .stdin(std::process::Stdio::piped())
                .spawn()
            {
                Ok(c) => c,
                Err(_) => {
                    // Try xsel as fallback
                    match Command::new("xsel")
                        .args(["--clipboard", "--input"])
                        .stdin(std::process::Stdio::piped())
                        .spawn()
                    {
                        Ok(c) => c,
                        Err(e) => { warn!("[Linux] No clipboard tool found: {}", e); return false; }
                    }
                }
            }
        };

        if let Some(stdin) = child.stdin.as_mut() {
            use std::io::Write;
            let _ = stdin.write_all(text.as_bytes());
        }
        let _ = child.wait();
        true
    }

    /// Inject text via clipboard + Ctrl+V (X11: xdotool, Wayland: ydotool).
    pub fn inject_text(text: &str) -> bool {
        if !write_clipboard(text) { return false; }
        std::thread::sleep(std::time::Duration::from_millis(50));

        let server = detect_display_server();
        if server == "wayland" {
            let status = Command::new("ydotool").args(["key", "ctrl+v"]).status();
            match status {
                Ok(s) if s.success() => { info!("[Linux/Wayland] Injected {} chars", text.len()); true }
                _ => { warn!("[Linux/Wayland] ydotool failed — install ydotool"); false }
            }
        } else {
            let status = Command::new("xdotool").args(["key", "ctrl+v"]).status();
            match status {
                Ok(s) if s.success() => { info!("[Linux/X11] Injected {} chars via xdotool", text.len()); true }
                _ => {
                    warn!("[Linux/X11] xdotool failed — install xdotool");
                    false
                }
            }
        }
    }

    /// Erase N characters via BackSpace keys.
    pub fn erase_chars(count: usize) -> bool {
        if count == 0 { return true; }
        let server = detect_display_server();
        if server == "wayland" {
            // ydotool key BackSpace (repeated)
            for _ in 0..count {
                let _ = Command::new("ydotool").args(["key", "BackSpace"]).status();
            }
            true
        } else {
            // xdotool key --clearmodifiers BackSpace (repeated via loop for reliability)
            for _ in 0..count {
                let _ = Command::new("xdotool").args(["key", "--clearmodifiers", "BackSpace"]).status();
            }
            true
        }
    }

    /// Get the focused window PID on X11/Wayland.
    pub fn get_focused_pid() -> Option<i32> {
        let output = Command::new("xdotool")
            .args(["getactivewindow", "getwindowpid"])
            .output()
            .ok()?;
        String::from_utf8_lossy(&output.stdout).trim().parse::<i32>().ok()
    }

    /// Check if required injection tools are available. Returns list of missing tools.
    pub fn check_tools() -> Vec<String> {
        let mut missing = Vec::new();
        let server = detect_display_server();
        if server == "wayland" {
            if Command::new("ydotool").args(["--help"]).output().is_err() {
                missing.push("ydotool (sudo apt install ydotool)".into());
            }
            if Command::new("wl-copy").args(["--version"]).output().is_err() {
                missing.push("wl-clipboard (sudo apt install wl-clipboard)".into());
            }
        } else {
            if Command::new("xdotool").args(["version"]).output().is_err() {
                missing.push("xdotool (sudo apt install xdotool)".into());
            }
            if Command::new("xclip").args(["-version"]).output().is_err() {
                missing.push("xclip (sudo apt install xclip)".into());
            }
        }
        missing
    }
}

#[cfg(not(target_os = "linux"))]
mod linux_impl {
    pub fn detect_display_server() -> &'static str { "none" }
    pub fn get_active_window_title() -> Option<String> { None }
    pub fn get_active_process_name() -> Option<String> { None }
    pub fn get_focused_text() -> anyhow::Result<String> {
        anyhow::bail!("Linux platform only")
    }
    pub fn read_clipboard() -> Option<String> { None }
    pub fn write_clipboard(_: &str) -> bool { false }
    pub fn inject_text(_: &str) -> bool { false }
    pub fn erase_chars(_: usize) -> bool { false }
    pub fn get_focused_pid() -> Option<i32> { None }
    pub fn check_tools() -> Vec<String> { vec![] }
}

pub use linux_impl::*;

// ── LinuxAtspiReader — implements AccessibilityReader ─────────────────────────
//
// This struct was MISSING from the original codebase, causing a compile error
// on Linux because platform/mod.rs references `linux::LinuxAtspiReader::new()`.
// Fixed in Domain 11: Cross-Platform Hardening.

pub struct LinuxAtspiReader;

impl LinuxAtspiReader {
    pub fn new() -> Self { LinuxAtspiReader }
}

impl Default for LinuxAtspiReader {
    fn default() -> Self { Self::new() }
}

impl crate::platform::AccessibilityReader for LinuxAtspiReader {
    /// Get the focused element's text content.
    /// Uses AT-SPI2 via pyatspi if available, falls back to clipboard-based selection.
    fn get_focused_text(&self) -> anyhow::Result<String> {
        get_focused_text()
    }

    /// Get clipboard content.
    fn get_clipboard_text(&self) -> anyhow::Result<String> {
        read_clipboard()
            .ok_or_else(|| anyhow::anyhow!("No clipboard tool available (install xclip or wl-clipboard)"))
    }
}

// ── LinuxInjector ─────────────────────────────────────────────────────────────

pub struct LinuxInjector;

impl LinuxInjector {
    pub fn new() -> Self { Self }

    pub fn inject(&self, text: &str) -> bool { inject_text(text) }
    pub fn erase(&self, n: usize) -> bool { erase_chars(n) }
    pub fn focused_pid(&self) -> Option<i32> { get_focused_pid() }
    pub fn display_server(&self) -> &'static str { detect_display_server() }
    pub fn missing_tools(&self) -> Vec<String> { check_tools() }
    pub fn active_window_title(&self) -> Option<String> { get_active_window_title() }
    pub fn active_process_name(&self) -> Option<String> { get_active_process_name() }
}

impl Default for LinuxInjector {
    fn default() -> Self { Self::new() }
}
