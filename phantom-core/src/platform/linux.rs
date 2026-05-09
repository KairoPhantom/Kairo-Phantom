/// Linux Platform Injection — Advancement 2
/// Background ghost injection via xdotool / xdg-clipboard.
/// Works on X11. Wayland support via wl-clipboard + ydotool.

use tracing::{info, warn};

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
                .spawn() {
                Ok(c) => c,
                Err(_) => {
                    // Try xsel as fallback
                    match Command::new("xsel")
                        .args(["--clipboard", "--input"])
                        .stdin(std::process::Stdio::piped())
                        .spawn() {
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
            // ydotool key ctrl+v
            let status = Command::new("ydotool")
                .args(["key", "ctrl+v"])
                .status();
            match status {
                Ok(s) if s.success() => { info!("[Linux/Wayland] Injected {} chars", text.len()); true }
                _ => { warn!("[Linux/Wayland] ydotool failed — install ydotool"); false }
            }
        } else {
            // xdotool key ctrl+v
            let status = Command::new("xdotool")
                .args(["key", "ctrl+v"])
                .status();
            match status {
                Ok(s) if s.success() => { info!("[Linux/X11] Injected {} chars via xdotool", text.len()); true }
                _ => {
                    warn!("[Linux/X11] xdotool failed — install xdotool");
                    // Try xte (xautomation) as fallback
                    let _ = Command::new("xte").args(["key ctrl+v"]).status();
                    false
                }
            }
        }
    }

    /// Erase N characters.
    pub fn erase_chars(count: usize) -> bool {
        let server = detect_display_server();
        let keys = (0..count).map(|_| "BackSpace").collect::<Vec<_>>().join(" ");
        if server == "wayland" {
            let mut args = vec!["key"];
            let parts: Vec<&str> = keys.split_whitespace().collect();
            args.extend(parts);
            Command::new("ydotool").args(&args).status().map(|s| s.success()).unwrap_or(false)
        } else {
            let key_cmds: Vec<String> = (0..count).map(|_| "key BackSpace".to_string()).collect();
            let script = key_cmds.join("\n");
            let mut args = vec![];
            for cmd in key_cmds.iter() {
                args.extend(cmd.split_whitespace());
            }
            Command::new("xdotool").args(["key", "BackSpace"]).status().map(|s| s.success()).unwrap_or(false)
        }
    }

    /// Get the focused window PID on X11.
    pub fn get_focused_pid() -> Option<i32> {
        let output = Command::new("xdotool")
            .args(["getactivewindow", "getwindowpid"])
            .output().ok()?;
        String::from_utf8_lossy(&output.stdout).trim().parse::<i32>().ok()
    }

    /// Check if required injection tools are available.
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
    pub fn inject_text(_: &str) -> bool { false }
    pub fn erase_chars(_: usize) -> bool { false }
    pub fn get_focused_pid() -> Option<i32> { None }
    pub fn check_tools() -> Vec<String> { vec![] }
}

pub use linux_impl::*;

pub struct LinuxInjector;

impl LinuxInjector {
    pub fn new() -> Self { Self }

    pub fn inject(&self, text: &str) -> bool { inject_text(text) }
    pub fn erase(&self, n: usize) -> bool { erase_chars(n) }
    pub fn focused_pid(&self) -> Option<i32> { get_focused_pid() }
    pub fn display_server(&self) -> &'static str { detect_display_server() }
    pub fn missing_tools(&self) -> Vec<String> { check_tools() }
}
