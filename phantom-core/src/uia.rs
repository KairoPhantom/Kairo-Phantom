/// UIA Reader v2 — Reads text from the focused application element.
/// Uses Windows UI Automation TextPattern as primary.
/// Falls back to clipboard for elevated processes.

use anyhow::{Context, Result};

#[cfg(windows)]
use uiautomation::core::UIAutomation;

pub struct UiaReader;

impl UiaReader {
    pub fn new() -> Self {
        UiaReader
    }

    /// Get the full text of the currently focused element.
    pub fn get_focused_text(&self) -> Result<String> {
        #[cfg(windows)]
        {
            let automation = UIAutomation::new()
                .context("Failed to initialize UIAutomation")?;

            let focused = automation
                .get_focused_element()
                .context("No focused element")?;

            // TextPattern — works for Word, VS Code, Notepad, browsers
            if let Ok(pat) = focused.get_pattern::<uiautomation::patterns::UITextPattern>() {
                if let Ok(range) = pat.get_document_range() {
                    if let Ok(text) = range.get_text(-1) {
                        if !text.is_empty() {
                            return Ok(text);
                        }
                    }
                }
            }

            // ValuePattern — works for simple inputs, text fields
            if let Ok(pat) = focused.get_pattern::<uiautomation::patterns::UIValuePattern>() {
                if let Ok(val) = pat.get_value() {
                    if !val.is_empty() {
                        return Ok(val);
                    }
                }
            }

            Ok(String::new())
        }

        #[cfg(not(windows))]
        Ok(String::new())
    }

    /// Fallback: read clipboard content (only what's already there)
    pub fn get_clipboard_text(&self) -> Result<String> {
        #[cfg(windows)]
        unsafe {
            use windows::Win32::System::DataExchange::{
                GetClipboardData, OpenClipboard, CloseClipboard,
            };
            use windows::Win32::System::Memory::{GlobalLock, GlobalUnlock};

            OpenClipboard(None)?;
            let handle = GetClipboardData(13u32)?;
            let hglobal = windows::Win32::Foundation::HGLOBAL(handle.0 as _);
            let ptr = GlobalLock(hglobal) as *const u16;
            if ptr.is_null() {
                let _ = CloseClipboard();
                return Ok(String::new());
            }
            let mut len = 0;
            while *ptr.add(len) != 0 {
                len += 1;
            }
            let slice = std::slice::from_raw_parts(ptr, len);
            let text = String::from_utf16_lossy(slice);
            let _ = GlobalUnlock(hglobal);
            let _ = CloseClipboard();
            Ok(text)
        }

        #[cfg(not(windows))]
        Ok(String::new())
    }
}
