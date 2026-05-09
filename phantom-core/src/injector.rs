/// Injector v2 — Production-grade ghost typing engine.
/// Uses clipboard injection (Ctrl+V) as the PRIMARY method for reliable,
/// high-speed text insertion across ALL applications (Word, VS Code, Terminals, etc.)
/// Falls back to char-by-char enigo for apps that don't support clipboard paste.

use anyhow::Result;
use enigo::{Enigo, Keyboard, Settings, Key, Direction};
use std::time::Duration;
use tracing::{debug, info, warn};

#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::GetForegroundWindow;

#[derive(Clone)]
pub struct Injector {
    /// Milliseconds between each character (0 = max speed, used for fallback)
    typing_delay_ms: u64,
}

impl Injector {
    pub fn new(typing_delay_ms: u64) -> Self {
        Injector { typing_delay_ms }
    }

    /// Capture the currently focused window handle.
    #[cfg(windows)]
    fn get_foreground_hwnd() -> isize {
        unsafe { GetForegroundWindow().0 as isize }
    }

    #[cfg(not(windows))]
    fn get_foreground_hwnd() -> isize { 0 }

    /// PRIMARY INJECTION METHOD: Clipboard-based paste.
    /// This is the fastest, most reliable method across all applications.
    /// Word, VS Code, Notepad, Google Docs, Terminals — all support Ctrl+V.
    pub fn inject_via_clipboard(&self, text: &str) -> bool {
        match self.write_to_clipboard(text) {
            Ok(_) => {
                // Small delay to let clipboard settle
                std::thread::sleep(Duration::from_millis(30));
                
                let hwnd_before = Self::get_foreground_hwnd();
                
                let mut enigo = match Enigo::new(&Settings::default()) {
                    Ok(e) => e,
                    Err(e) => {
                        warn!("Injector: failed to create enigo for paste: {}", e);
                        return false;
                    }
                };
                
                // Check window hasn't changed
                if hwnd_before != 0 && Self::get_foreground_hwnd() != hwnd_before {
                    warn!("⚠️  Window changed before paste — aborting");
                    return false;
                }
                
                let _ = enigo.key(Key::Control, Direction::Press);
                let _ = enigo.key(Key::Unicode('v'), Direction::Click);
                let _ = enigo.key(Key::Control, Direction::Release);
                
                info!("⚡ Clipboard inject complete ({} chars)", text.len());
                true
            }
            Err(e) => {
                warn!("Clipboard write failed: {} — falling back to key typing", e);
                false
            }
        }
    }

    /// FALLBACK INJECTION: Type text character by character.
    /// Used when clipboard injection fails or for streaming tokens.
    pub fn type_text(&self, text: &str) {
        let origin_hwnd = Self::get_foreground_hwnd();

        let mut enigo = match Enigo::new(&Settings::default()) {
            Ok(e) => e,
            Err(e) => {
                warn!("Injector: failed to create enigo: {}", e);
                return;
            }
        };

        debug!("Injector: typing {} chars", text.len());

        for (i, ch) in text.chars().enumerate() {
            // Window-lock check every 20 characters
            if i % 20 == 0 {
                let current = Self::get_foreground_hwnd();
                if origin_hwnd != 0 && current != origin_hwnd {
                    warn!("⚠️  Window changed during injection — aborting at char {}", i);
                    return;
                }
            }

            if let Err(e) = enigo.text(&ch.to_string()) {
                warn!("Injector: failed to type char '{}': {}", ch, e);
            }
        }

        info!("✅ Injector: typing complete ({} chars)", text.len());
    }

    /// ERASE PROMPT: Select-all-via-clipboard, then replace.
    /// Works by: selecting the exact prompt text backwards, then deleting.
    /// Uses Win32 SendInput for precision timing.
    pub fn erase_prompt(&self, char_count: usize) {
        if char_count == 0 { return; }
        
        let mut enigo = match Enigo::new(&Settings::default()) {
            Ok(e) => e,
            Err(_) => return,
        };

        info!("🗑️  Erasing {} chars (prompt)", char_count);

        // Strategy: Shift+Left select the exact character count, then Delete
        // This works across ALL apps including Word with wrapped lines
        let _ = enigo.key(Key::Shift, Direction::Press);
        for _ in 0..char_count {
            let _ = enigo.key(Key::LeftArrow, Direction::Click);
        }
        let _ = enigo.key(Key::Shift, Direction::Release);
        
        // Single delete to remove entire selection
        std::thread::sleep(Duration::from_millis(15));
        let _ = enigo.key(Key::Delete, Direction::Click);
        
        std::thread::sleep(Duration::from_millis(15));
    }

    /// Simple backspace N times (for minor corrections)
    pub fn backspace_n(&self, n: usize) {
        let mut enigo = match Enigo::new(&Settings::default()) {
            Ok(e) => e,
            Err(_) => return,
        };
        for _ in 0..n {
            let _ = enigo.key(Key::Backspace, Direction::Click);
        }
    }

    /// Remove the last typed character (cleans up 'm' from Alt+M)
    pub fn undo_ghost_char(&self) {
        self.backspace_n(1);
    }

    /// Write text to the Windows clipboard using Unicode format.
    #[cfg(windows)]
    pub fn write_to_clipboard(&self, text: &str) -> Result<()> {
        use windows::Win32::System::DataExchange::{
            SetClipboardData, OpenClipboard, EmptyClipboard, CloseClipboard,
        };
        use windows::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GMEM_MOVEABLE};

        let wide: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        let byte_size = wide.len() * 2;

        unsafe {
            let h_mem = GlobalAlloc(GMEM_MOVEABLE, byte_size)?;
            let ptr = GlobalLock(h_mem) as *mut u16;
            if !ptr.is_null() {
                std::ptr::copy_nonoverlapping(wide.as_ptr(), ptr, wide.len());
            }
            let _ = GlobalUnlock(h_mem);

            OpenClipboard(None)?;
            EmptyClipboard()?;
            SetClipboardData(13u32, windows::Win32::Foundation::HANDLE(h_mem.0 as _))?;
            CloseClipboard()?;
        }

        Ok(())
    }

    #[cfg(not(windows))]
    pub fn write_to_clipboard(&self, _text: &str) -> Result<()> {
        anyhow::bail!("Clipboard injection only supported on Windows")
    }
}
