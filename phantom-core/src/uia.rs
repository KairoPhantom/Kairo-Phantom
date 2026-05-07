/// UIA Reader — reads text from the currently focused Windows UI element.
/// Falls back to clipboard paste for elevated processes.

use anyhow::{Context, Result};
use tracing::{debug, warn};

#[cfg(windows)]
use uiautomation::{core::UIAutomation, types::UIProperty};

pub struct UiaReader;

impl UiaReader {
    pub fn new() -> Self {
        UiaReader
    }

    /// Primary: get text from the focused UI element via Windows UI Automation.
    pub fn get_focused_text(&self) -> Result<String> {
        #[cfg(windows)]
        {
            let automation = UIAutomation::new()
                .context("Failed to initialize UIAutomation — are you on Windows?")?;

            let focused = automation
                .get_focused_element()
                .context("No focused element found")?;

            // Try ValuePattern first (works for most text inputs)
            if let Ok(value_pattern) = focused.get_pattern::<uiautomation::patterns::UIValuePattern>() {
                if let Ok(val) = value_pattern.get_value() {
                    if !val.is_empty() {
                        debug!("UIA: got text via ValuePattern ({} chars)", val.len());
                        return Ok(val);
                    }
                }
            }

            // Fallback: try getting element Name property (works for labels, buttons etc)
            if let Ok(name) = focused.get_name() {
                if !name.is_empty() {
                    debug!("UIA: got text via Name property ({} chars)", name.len());
                    return Ok(name);
                }
            }

            // Fallback: TextPattern (works for rich text editors like Word)
            if let Ok(text_pattern) = focused.get_pattern::<uiautomation::patterns::UITextPattern>() {
                if let Ok(range) = text_pattern.document_range() {
                    if let Ok(text) = range.get_text(-1) {
                        if !text.is_empty() {
                            debug!("UIA: got text via TextPattern ({} chars)", text.len());
                            return Ok(text);
                        }
                    }
                }
            }

            warn!("UIA: no text found via any pattern");
            Ok(String::new())
        }

        #[cfg(not(windows))]
        {
            anyhow::bail!("UIA is only available on Windows")
        }
    }

    /// Fallback: read clipboard content when UIA fails (elevated process etc.)
    pub fn get_clipboard_text(&self) -> Result<String> {
        // Select all + copy, then read clipboard
        // This uses enigo to send Ctrl+A, Ctrl+C
        use enigo::{Enigo, Key, Keyboard, Settings};
        use std::time::Duration;

        let mut enigo = Enigo::new(&Settings::default())
            .context("Failed to create enigo instance for clipboard read")?;

        // Ctrl+A to select all
        enigo.key(Key::Control, enigo::Direction::Press)?;
        enigo.key(Key::Unicode('a'), enigo::Direction::Click)?;
        enigo.key(Key::Control, enigo::Direction::Release)?;

        std::thread::sleep(Duration::from_millis(50));

        // Ctrl+C to copy
        enigo.key(Key::Control, enigo::Direction::Press)?;
        enigo.key(Key::Unicode('c'), enigo::Direction::Click)?;
        enigo.key(Key::Control, enigo::Direction::Release)?;

        std::thread::sleep(Duration::from_millis(100));

        // Read clipboard
        #[cfg(windows)]
        {
            use windows::Win32::System::DataExchange::{GetClipboardData, OpenClipboard, CloseClipboard};
            use windows::Win32::System::Memory::{GlobalLock, GlobalUnlock};
            use windows::core::PCWSTR;

            unsafe {
                OpenClipboard(None).ok()?;
                let handle = GetClipboardData(13u32)?; // CF_UNICODETEXT = 13
                let ptr = GlobalLock(handle.0 as _) as *const u16;
                if ptr.is_null() {
                    CloseClipboard().ok();
                    return Ok(String::new());
                }
                let mut len = 0;
                while *ptr.add(len) != 0 { len += 1; }
                let slice = std::slice::from_raw_parts(ptr, len);
                let text = String::from_utf16_lossy(slice);
                GlobalUnlock(handle.0 as _);
                CloseClipboard().ok();
                Ok(text)
            }
        }

        #[cfg(not(windows))]
        Ok(String::new())
    }
}
