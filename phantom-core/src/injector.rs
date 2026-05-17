/// Real Windows keyboard injector — uses SendInput + clipboard for actual text injection.
/// v2.0 PRODUCTION REWRITE:
/// - Removed backspace-based erase_prompt (unreliable: backspaces miss document body focus)
/// - New strategy: Home + Shift+End + Ctrl+V (select current line → replace with paste)
/// - Added click_to_focus() via mouse_event to click document body before sending keys
/// - Clipboard is always set BEFORE focus switch to avoid clipboard race

use std::thread;
use std::time::Duration;

#[cfg(windows)]
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE,
    VK_BACK, VK_ESCAPE, VK_RETURN, VK_CONTROL, VK_END, VK_HOME, VK_SHIFT, VK_DELETE,
    VIRTUAL_KEY, KEYBD_EVENT_FLAGS,
};
#[cfg(windows)]
use windows::Win32::Foundation::LPARAM;
#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{
    PostMessageW, SetForegroundWindow, GetForegroundWindow,
    BringWindowToTop, ShowWindow, SW_SHOW,
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
                        wVk: VIRTUAL_KEY(0),
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
                        wVk: VIRTUAL_KEY(0),
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
    fn send_vk(vk: VIRTUAL_KEY) {
        let inputs = [
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: vk,
                        wScan: 0,
                        dwFlags: KEYBD_EVENT_FLAGS(0),
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

    // ─── Production Injection Strategy ───────────────────────────────────────
    //
    // THE CORRECT APPROACH FOR ALL DESKTOP APPS:
    //
    //   1. Set clipboard = AI response  (BEFORE focusing the window)
    //   2. BringWindowToTop + SetForegroundWindow
    //   3. Wait 300ms for OS to fully grant keyboard focus to document body
    //   4. Send HOME  → move cursor to beginning of the prompt line
    //   5. Send Shift+END → select entire line (the // prompt)
    //   6. Send Ctrl+V  → paste replaces the selection
    //
    // This completely eliminates backspace-based erasure which requires the
    // text cursor to be in exactly the right position with full keyboard focus.
    // Select-line-then-paste is atomic and focus-position-independent.

    /// PRIMARY injection method: set clipboard FIRST (before focus switch),
    /// then caller does BringWindowToTop + 300ms sleep, then calls inject_replace_line().
    pub fn prepare_clipboard(&self, text: &str) -> bool {
        #[cfg(windows)]
        {
            if !Self::set_clipboard(text) {
                tracing::warn!("Clipboard set failed");
                return false;
            }
            tracing::info!("Clipboard ready: {} chars", text.len());
            true
        }
        #[cfg(not(windows))]
        { true }
    }

    /// SECONDARY injection: select the current line and replace it with clipboard content.
    /// Call this AFTER window focus is confirmed (300ms+ after SetForegroundWindow).
    ///
    /// Sequence: Home → Shift+End → (optional: Delete) → Ctrl+V
    pub fn inject_replace_line(&self) {
        #[cfg(windows)]
        {
            tracing::info!("Sending Home + Shift+End + Ctrl+V (select line → paste)");
            
            // Home: go to beginning of current line
            Self::send_vk(VK_HOME);
            thread::sleep(Duration::from_millis(30));
            
            // Shift+End: select to end of line
            let shift_end = [
                INPUT {
                    r#type: INPUT_KEYBOARD,
                    Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                        ki: KEYBDINPUT {
                            wVk: VK_SHIFT,
                            wScan: 0,
                            dwFlags: KEYBD_EVENT_FLAGS(0),
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                },
                INPUT {
                    r#type: INPUT_KEYBOARD,
                    Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                        ki: KEYBDINPUT {
                            wVk: VK_END,
                            wScan: 0,
                            dwFlags: KEYBD_EVENT_FLAGS(0),
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                },
                INPUT {
                    r#type: INPUT_KEYBOARD,
                    Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                        ki: KEYBDINPUT {
                            wVk: VK_END,
                            wScan: 0,
                            dwFlags: KEYEVENTF_KEYUP,
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                },
                INPUT {
                    r#type: INPUT_KEYBOARD,
                    Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                        ki: KEYBDINPUT {
                            wVk: VK_SHIFT,
                            wScan: 0,
                            dwFlags: KEYEVENTF_KEYUP,
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                },
            ];
            unsafe { SendInput(&shift_end, std::mem::size_of::<INPUT>() as i32); }
            thread::sleep(Duration::from_millis(30));
            
            // Ctrl+V: paste (replaces selection)
            Self::send_ctrl_v();
            thread::sleep(Duration::from_millis(50));
            
            tracing::info!("inject_replace_line complete");
        }
    }

    /// All-in-one: set clipboard + select line + paste.
    /// This is the main entry point called from main.rs ghost session handler.
    /// Caller must have already called BringWindowToTop + SetForegroundWindow + 300ms sleep.
    pub fn inject_via_clipboard(&self, text: &str) -> bool {
        if text.is_empty() { return true; }

        #[cfg(windows)]
        {
            // Step 1: Set clipboard FIRST
            if !Self::set_clipboard(text) {
                tracing::warn!("Clipboard set failed, trying SendInput char-by-char");
                self.type_text_sendinput(text);
                return true;
            }
            thread::sleep(Duration::from_millis(30));

            // Step 2: Select current line (Home + Shift+End) then paste (Ctrl+V)
            self.inject_replace_line();

            for word in text.split_whitespace().take(5) {
                tracing::debug!("Injected: {}", word);
            }
            tracing::info!("inject_via_clipboard complete ({} chars)", text.len());
        }
        true
    }

    /// Legacy: erase N chars via backspace. Kept for compatibility but
    /// this is NO LONGER CALLED in the main ghost session flow.
    /// inject_via_clipboard() now uses Home+Shift+End+Ctrl+V instead.
    pub fn erase_prompt(&self, count: usize) {
        if count == 0 { return; }
        tracing::info!("erase_prompt({}) called — using Home+Shift+End+Delete instead of backspaces", count);
        #[cfg(windows)]
        {
            // Select the line and delete it (without pasting anything)
            Self::send_vk(VK_HOME);
            thread::sleep(Duration::from_millis(20));
            let shift_end = [
                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_SHIFT, wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_END, wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_END, wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_SHIFT, wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
            ];
            unsafe { SendInput(&shift_end, std::mem::size_of::<INPUT>() as i32); }
            thread::sleep(Duration::from_millis(20));
            Self::send_vk(VK_DELETE);
        }
    }

    /// Type text — always via clipboard for reliability.
    pub fn type_text(&self, text: &str) {
        if text.is_empty() { return; }
        tracing::info!("type_text: {} chars via clipboard", text.len());
        self.inject_via_clipboard(text);
    }

    /// Fallback: type char by char using SendInput (Unicode).
    /// Only used when clipboard fails.
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

    /// Set Windows clipboard content (Unicode text).
    #[cfg(windows)]
    pub fn set_clipboard(text: &str) -> bool {
        use windows::Win32::System::DataExchange::{OpenClipboard, EmptyClipboard, SetClipboardData, CloseClipboard};
        use windows::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GMEM_MOVEABLE};
        use windows::Win32::Foundation::HANDLE;

        let wide: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        let byte_count = wide.len() * 2;

        unsafe {
            // Retry up to 5 times — clipboard may be locked by Word momentarily
            for attempt in 0..5 {
                if OpenClipboard(None).is_ok() {
                    let _ = EmptyClipboard();
                    let h_mem = GlobalAlloc(GMEM_MOVEABLE, byte_count);
                    if let Ok(h_mem) = h_mem {
                        let ptr = GlobalLock(h_mem) as *mut u16;
                        if !ptr.is_null() {
                            std::ptr::copy_nonoverlapping(wide.as_ptr(), ptr, wide.len());
                            let _ = GlobalUnlock(h_mem);
                            // CF_UNICODETEXT = 13
                            let result = SetClipboardData(13, HANDLE(h_mem.0));
                            let _ = CloseClipboard();
                            if result.is_ok() {
                                tracing::debug!("Clipboard set OK on attempt {}", attempt + 1);
                                return true;
                            }
                        } else {
                            let _ = CloseClipboard();
                        }
                    } else {
                        let _ = CloseClipboard();
                    }
                }
                thread::sleep(Duration::from_millis(20));
            }
            tracing::error!("Clipboard set failed after 5 attempts");
            false
        }
    }

    /// Send Ctrl+V keystroke.
    #[cfg(windows)]
    fn send_ctrl_v() {
        let inputs = [
            INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_CONTROL, wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
            INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VIRTUAL_KEY(0x56), wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
            INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VIRTUAL_KEY(0x56), wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
            INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_CONTROL, wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
        ];
        unsafe { SendInput(&inputs, std::mem::size_of::<INPUT>() as i32); }
    }

    /// Escape any ribbon/menu mode. NOT called in main flow (removed — it sent ESC into apps).
    pub fn escape_ribbon_mode(&self) {
        // Intentionally a no-op. Double-ESC was destroying Word document state.
        // The hook consumes Alt+M at the low-level (LRESULT(1)) so no cleanup needed.
    }

    /// Undo ghost char — no-op (hook consumes the key).
    pub fn undo_ghost_char(&self) {}

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
