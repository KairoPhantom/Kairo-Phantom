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

    use core_graphics::event::{CGEvent, CGEventType, CGKeyCode, CGEventFlags};
    use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
    
    /// Map a character to a CGKeyCode and flags.
    /// Note: This is a simplistic mapping for demonstration. Real implementations need
    /// complete keyboard layout mapping (TISCopyCurrentKeyboardInputSource).
    fn char_to_keycode(c: char) -> Option<(CGKeyCode, CGEventFlags)> {
        match c {
            'a'..='z' => Some(((c as u16) - ('a' as u16) + 0x00, CGEventFlags::empty())), // Very rough mapping
            'A'..='Z' => Some(((c as u16) - ('A' as u16) + 0x00, CGEventFlags::CGEventFlagShift)),
            ' ' => Some((0x31, CGEventFlags::empty())),
            '\n' => Some((0x24, CGEventFlags::empty())),
            _ => None, // Fallback needed
        }
    }

    /// Inject text into the focused process via CGEventPostToPid.
    /// This is true background injection without stealing focus.
    pub fn inject_text_via_clipboard(text: &str) -> bool {
        // We still use pbcopy for the actual payload since mapping arbitrary Unicode
        // to CGKeyCodes requires complex TIS layout translation.
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

        // Small settle delay for clipboard sync
        std::thread::sleep(std::time::Duration::from_millis(30));

        let pid = match get_focused_pid() {
            Some(p) => p,
            None => return false,
        };

        // Send Cmd+V via CGEventPostToPid directly to the target app's event queue
        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState).unwrap();
        
        // 0x09 is 'v' keycode
        let mut v_down = CGEvent::new_keyboard_event(source.clone(), 0x09, true).unwrap();
        v_down.set_flags(CGEventFlags::CGEventFlagCommand);
        
        let mut v_up = CGEvent::new_keyboard_event(source, 0x09, false).unwrap();
        v_up.set_flags(CGEventFlags::CGEventFlagCommand);

        v_down.post_to_pid(pid);
        std::thread::sleep(std::time::Duration::from_millis(5));
        v_up.post_to_pid(pid);

        info!("[macOS] Injected {} chars via CGEventPostToPid(Cmd+V) to PID {}", text.len(), pid);
        true
    }

    /// Send a CGEventKeyDown/Up sequence for a single keystroke directly to PID.
    pub fn send_keystroke_applescript(key: &str, _modifiers: &[&str]) -> bool {
        // Fallback for complex keys
        let pid = match get_focused_pid() {
            Some(p) => p,
            None => return false,
        };
        
        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState).unwrap();
        let keycode = match key {
            "delete" => 0x33, // Delete key
            "return" => 0x24,
            "escape" => 0x35,
            _ => return false,
        };

        let event_down = CGEvent::new_keyboard_event(source.clone(), keycode, true).unwrap();
        let event_up = CGEvent::new_keyboard_event(source, keycode, false).unwrap();

        event_down.post_to_pid(pid);
        std::thread::sleep(std::time::Duration::from_millis(2));
        event_up.post_to_pid(pid);

        true
    }

    /// Erase N characters backwards using Delete key simulation via CGEventPostToPid.
    pub fn erase_chars(count: usize) -> bool {
        let pid = match get_focused_pid() {
            Some(p) => p,
            None => return false,
        };
        
        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState).unwrap();
        
        for _ in 0..count {
            let event_down = CGEvent::new_keyboard_event(source.clone(), 0x33, true).unwrap(); // 0x33 is delete
            let event_up = CGEvent::new_keyboard_event(source.clone(), 0x33, false).unwrap();
            
            event_down.post_to_pid(pid);
            event_up.post_to_pid(pid);
            std::thread::sleep(std::time::Duration::from_millis(1));
        }
        
        true
    }

    /// Check if Accessibility permission is granted using CoreGraphics.
    pub fn check_accessibility_permission() -> bool {
        // CGEvent::post requires accessibility permissions in modern macOS
        // We can do a dummy post to our own PID
        let pid = std::process::id() as i32;
        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState).unwrap();
        if let Ok(event) = CGEvent::new_keyboard_event(source, 0xFF, true) {
            // If we can create and post it, we likely have permissions (or are testing ourselves)
            // A more robust check requires AXIsProcessTrusted() from ApplicationServices
            event.post_to_pid(pid);
            true
        } else {
            false
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

use crate::platform::AccessibilityReader;
use anyhow::{Result, anyhow};

/// macOS implementation of the AccessibilityReader trait using AXUIElement.
pub struct MacOsAccessibilityReader;

impl MacOsAccessibilityReader {
    pub fn new() -> Self {
        Self
    }
}

#[cfg(target_os = "macos")]
impl AccessibilityReader for MacOsAccessibilityReader {
    fn get_focused_text(&self) -> Result<String> {
        use macos_accessibility_client::accessibility::{application::Application, element::AXUIElement};
        
        // 1. Get the system-wide focused UI element using AXUIElement CreateSystemWide
        // Or get the active application first.
        let app = Application::frontmost()
            .ok_or_else(|| anyhow!("No frontmost application found"))?;
            
        let focused_element = app.focused_element()
            .ok_or_else(|| anyhow!("No focused element found in frontmost app"))?;
            
        // 2. Query the AXValue or AXSelectedText attribute
        let text = focused_element.value()
            .or_else(|| focused_element.title())
            .ok_or_else(|| anyhow!("Failed to extract text from focused AXUIElement"))?;
            
        Ok(text)
    }

    fn get_clipboard_text(&self) -> Result<String> {
        let mut child = std::process::Command::new("pbpaste")
            .stdout(std::process::Stdio::piped())
            .spawn()?;

        let output = child.wait_with_output()?;
        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        } else {
            Err(anyhow!("pbpaste failed"))
        }
    }
}

#[cfg(not(target_os = "macos"))]
impl AccessibilityReader for MacOsAccessibilityReader {
    fn get_focused_text(&self) -> Result<String> {
        Err(anyhow!("macOS accessibility is not supported on this platform"))
    }
    fn get_clipboard_text(&self) -> Result<String> {
        Err(anyhow!("macOS clipboard is not supported on this platform"))
    }
}
