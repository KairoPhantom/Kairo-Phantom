/// Real Windows keyboard injector — uses SendInput + clipboard for actual text injection.
/// Previously this was stub-only (println!). Now it actually types into the focused window.

use std::thread;
use std::time::Duration;

#[cfg(windows)]
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE,
    VK_BACK, VK_ESCAPE, VK_RETURN, VK_CONTROL, VK_END,
};
#[cfg(windows)]
use windows::Win32::Foundation::LPARAM;
#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{
    PostMessageW, SetForegroundWindow, GetForegroundWindow,
};

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SpeedProfile {
    Ghost,
    FastHuman,
    Natural,
    Readable,
}

pub struct HumanizedInjector {
    pub profile: SpeedProfile,
    delay_ms: u64,
}

impl HumanizedInjector {
    pub fn new(delay_ms: u64) -> Self {
        let profile = if delay_ms == 0 {
            SpeedProfile::Ghost
        } else if delay_ms < 30 {
            SpeedProfile::FastHuman
        } else if delay_ms < 100 {
            SpeedProfile::Natural
        } else {
            SpeedProfile::Readable
        };
        Self { profile, delay_ms }
    }

    // ─── Core: Send a single Unicode character via SendInput ─────────────────

    #[cfg(windows)]
    fn send_char(c: char) {
        let code = c as u16;
        let inputs = [
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: windows::Win32::UI::Input::KeyboardAndMouse::VIRTUAL_KEY(0),
                        wScan: code,
                        dwFlags: KEYEVENTF_UNICODE,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: windows::Win32::UI::Input::KeyboardAndMouse::VIRTUAL_KEY(0),
                        wScan: code,
                        dwFlags: KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
        ];
        unsafe { SendInput(&inputs, std::mem::size_of::<INPUT>() as i32); }
    }

    #[cfg(not(windows))]
    fn send_char(_c: char) {}

    // ─── Core: Send a virtual key down+up ────────────────────────────────────

    #[cfg(windows)]
    fn send_vk(vk: windows::Win32::UI::Input::KeyboardAndMouse::VIRTUAL_KEY) {
        let inputs = [
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: vk,
                        wScan: 0,
                        dwFlags: windows::Win32::UI::Input::KeyboardAndMouse::KEYBD_EVENT_FLAGS(0),
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: vk,
                        wScan: 0,
                        dwFlags: KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
        ];
        unsafe { SendInput(&inputs, std::mem::size_of::<INPUT>() as i32); }
    }

    #[cfg(not(windows))]
    fn send_vk(_vk: u16) {}

    // ─── Public API ───────────────────────────────────────────────────────────

    /// Erase `count` characters by sending Backspace repeatedly.
    pub fn erase_prompt(&self, count: usize) {
        if count == 0 { return; }
        tracing::info!("♻️  Erasing {} characters...", count);
        #[cfg(windows)]
        for _ in 0..count {
            Self::send_vk(VK_BACK);
            thread::sleep(Duration::from_millis(8));
        }
    }

    /// Type text by pasting via clipboard (fast, reliable, works in Word).
    pub fn type_text(&self, text: &str) {
        if text.is_empty() { return; }
        tracing::info!("⌨️  Injecting {} chars via clipboard...", text.len());
        self.inject_via_clipboard(text);
    }

    /// Inject text via clipboard paste (Ctrl+V) — most reliable for Office apps.
    pub fn inject_via_clipboard(&self, text: &str) -> bool {
        if text.is_empty() { return true; }
        
        #[cfg(windows)]
        {
            // Write to clipboard
            if !Self::set_clipboard(text) {
                tracing::warn!("⚠️  Clipboard set failed, falling back to SendInput char-by-char");
                self.type_text_sendinput(text);
                return true;
            }
            
            // Small delay for clipboard to settle
            thread::sleep(Duration::from_millis(50));
            
            // Send Ctrl+V
            Self::send_ctrl_v();
            
            // Log word by word for visibility
            for word in text.split_whitespace().take(5) {
                tracing::debug!("Pasted: {}", word);
            }
            tracing::info!("✅ Clipboard paste complete ({} chars)", text.len());
        }
        true
    }

    /// Fallback: type char by char using SendInput (Unicode)
    fn type_text_sendinput(&self, text: &str) {
        let delay = match self.profile {
            SpeedProfile::Ghost => 0,
            SpeedProfile::FastHuman => 15,
            _ => 25,
        };
        for c in text.chars() {
            Self::send_char(c);
            if delay > 0 {
                thread::sleep(Duration::from_millis(delay));
            }
        }
    }

    /// Set Windows clipboard content.
    #[cfg(windows)]
    fn set_clipboard(text: &str) -> bool {
        use windows::Win32::System::DataExchange::{OpenClipboard, EmptyClipboard, SetClipboardData, CloseClipboard};
        use windows::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GMEM_MOVEABLE};
        use windows::Win32::Foundation::HANDLE;
        use windows::core::PCWSTR;

        let wide: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        let byte_count = wide.len() * 2;

        unsafe {
            if OpenClipboard(None).is_err() { return false; }
            let _ = EmptyClipboard();
            
            let h_mem = GlobalAlloc(GMEM_MOVEABLE, byte_count);
            if h_mem.is_err() { let _ = CloseClipboard(); return false; }
            let h_mem = h_mem.unwrap();
            
            let ptr = GlobalLock(h_mem) as *mut u16;
            if ptr.is_null() { let _ = CloseClipboard(); return false; }
            std::ptr::copy_nonoverlapping(wide.as_ptr(), ptr, wide.len());
            let _ = GlobalUnlock(h_mem);
            
            // CF_UNICODETEXT = 13
            let result = SetClipboardData(13, HANDLE(h_mem.0));
            let _ = CloseClipboard();
            result.is_ok()
        }
    }

    /// Send Ctrl+V keystroke.
    #[cfg(windows)]
    fn send_ctrl_v() {
        use windows::Win32::UI::Input::KeyboardAndMouse::{VIRTUAL_KEY, KEYBD_EVENT_FLAGS};
        let inputs = [
            // Ctrl down
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_CONTROL,
                        wScan: 0,
                        dwFlags: KEYBD_EVENT_FLAGS(0),
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
            // V down
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VIRTUAL_KEY(0x56), // 'V'
                        wScan: 0,
                        dwFlags: KEYBD_EVENT_FLAGS(0),
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
            // V up
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VIRTUAL_KEY(0x56),
                        wScan: 0,
                        dwFlags: KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
            // Ctrl up
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_CONTROL,
                        wScan: 0,
                        dwFlags: KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
        ];
        unsafe { SendInput(&inputs, std::mem::size_of::<INPUT>() as i32); }
    }

    /// Escape any ribbon/menu mode (send Escape key twice to be safe).
    pub fn escape_ribbon_mode(&self) {
        #[cfg(windows)]
        {
            Self::send_vk(VK_ESCAPE);
            thread::sleep(Duration::from_millis(30));
            Self::send_vk(VK_ESCAPE);
        }
    }

    /// Undo the 'm' character that may have been typed before the hook consumed it.
    pub fn undo_ghost_char(&self) {
        // The hook now consumes the key (LRESULT(1)), so no ghost char appears.
        // This is a no-op for safety.
    }

    // Legacy async API (kept for compatibility)
    pub async fn inject_char(&mut self, c: char, cancel: &tokio_util::sync::CancellationToken) -> bool {
        if cancel.is_cancelled() { return false; }
        Self::send_char(c);
        true
    }

    pub async fn inject_stream(&mut self, text: &str, cancel: &tokio_util::sync::CancellationToken) {
        for c in text.chars() {
            if !self.inject_char(c, cancel).await { break; }
        }
    }
}
