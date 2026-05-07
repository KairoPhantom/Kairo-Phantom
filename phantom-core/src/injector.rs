/// Injector — ghost types AI suggestion into the active application
/// using enigo keyboard simulation at human-like typing speed.

use anyhow::Result;
use enigo::{Enigo, Keyboard, Settings};
use std::time::Duration;
use tracing::debug;

#[derive(Clone)]
pub struct Injector {
    /// Milliseconds between each character (15ms = realistic human typing)
    typing_delay_ms: u64,
}

impl Injector {
    pub fn new(typing_delay_ms: u64) -> Self {
        Injector { typing_delay_ms }
    }

    /// Ghost-type text into the currently focused application.
    /// Types character by character at human-like speed.
    pub fn type_text(&self, text: &str) {
        // We must create enigo on the thread that calls it
        let mut enigo = match Enigo::new(&Settings::default()) {
            Ok(e) => e,
            Err(e) => {
                tracing::warn!("Injector: failed to create enigo: {}", e);
                return;
            }
        };

        debug!("Injector: typing {} chars at {}ms delay", text.len(), self.typing_delay_ms);

        for ch in text.chars() {
            // enigo.text() handles Unicode correctly via scancode mapping on Windows
            if let Err(e) = enigo.text(&ch.to_string()) {
                tracing::warn!("Injector: failed to type char '{}': {}", ch, e);
            }
            if self.typing_delay_ms > 0 {
                std::thread::sleep(Duration::from_millis(self.typing_delay_ms));
            }
        }

        debug!("Injector: typing complete");
    }

    /// Fast inject via clipboard paste — used for large blocks of text
    /// where character-by-character would be too slow.
    pub fn paste_text(&self, text: &str) -> Result<()> {
        use enigo::{Key, Direction};

        let mut enigo = Enigo::new(&Settings::default())?;

        // Write to clipboard
        self.write_to_clipboard(text)?;

        // Small delay to let clipboard settle
        std::thread::sleep(Duration::from_millis(50));

        // Ctrl+V to paste
        enigo.key(Key::Control, Direction::Press)?;
        enigo.key(Key::Unicode('v'), Direction::Click)?;
        enigo.key(Key::Control, Direction::Release)?;

        Ok(())
    }

    #[cfg(windows)]
    fn write_to_clipboard(&self, text: &str) -> Result<()> {
        use windows::Win32::System::DataExchange::{SetClipboardData, OpenClipboard, EmptyClipboard, CloseClipboard};
        use windows::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GMEM_MOVEABLE};
        use windows::core::PWSTR;

        let wide: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        let byte_size = wide.len() * 2;

        unsafe {
            let h_mem = GlobalAlloc(GMEM_MOVEABLE, byte_size)?;
            let ptr = GlobalLock(h_mem) as *mut u16;
            std::ptr::copy_nonoverlapping(wide.as_ptr(), ptr, wide.len());
            GlobalUnlock(h_mem);

            OpenClipboard(None)?;
            EmptyClipboard()?;
            SetClipboardData(13u32, windows::Win32::Foundation::HANDLE(h_mem.0 as _))?; // CF_UNICODETEXT
            CloseClipboard()?;
        }

        Ok(())
    }

    #[cfg(not(windows))]
    fn write_to_clipboard(&self, _text: &str) -> Result<()> {
        anyhow::bail!("Clipboard injection only supported on Windows")
    }
}
