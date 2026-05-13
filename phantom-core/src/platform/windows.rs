/// Windows UIAutomation implementation of the AccessibilityReader trait.
/// Uses UIAutomation TextPattern (primary) and ValuePattern (fallback)
/// to read text from the focused application element.
///
/// This is the production-ready Windows implementation.
/// For cross-platform support, see platform/mod.rs.

use anyhow::{Context, Result};
use uiautomation::core::UIAutomation;

use super::AccessibilityReader;

pub struct WindowsUiaReader;

impl Default for WindowsUiaReader {
    fn default() -> Self {
        Self::new()
    }
}

impl WindowsUiaReader {
    pub fn new() -> Self {
        WindowsUiaReader
    }
}

impl AccessibilityReader for WindowsUiaReader {
    /// Get the full text of the currently focused UI element via UIAutomation.
    ///
    /// Strategy:
    /// 1. TextPattern → works for Word, VS Code, Notepad, browsers, terminals
    /// 2. ValuePattern → works for form fields, simple inputs
    /// 3. Returns empty string if neither pattern is available
    fn get_focused_text(&self) -> Result<String> {
        let automation = UIAutomation::new()
            .context("Failed to initialize Windows UIAutomation")?;

        let focused = automation
            .get_focused_element()
            .context("No focused element found — click on a text field first")?;

        // Primary: TextPattern — works for rich text editors
        if let Ok(pat) = focused.get_pattern::<uiautomation::patterns::UITextPattern>() {
            if let Ok(range) = pat.get_document_range() {
                if let Ok(text) = range.get_text(-1) {
                    if !text.is_empty() {
                        return Ok(text);
                    }
                }
            }
        }

        // Secondary: ValuePattern — works for simple inputs
        if let Ok(pat) = focused.get_pattern::<uiautomation::patterns::UIValuePattern>() {
            if let Ok(val) = pat.get_value() {
                if !val.is_empty() {
                    return Ok(val);
                }
            }
        }

        // Both patterns empty — return empty string (caller handles gracefully)
        Ok(String::new())
    }

    /// Read text from the Windows clipboard using Win32 API.
    /// CF_UNICODETEXT (format 13) for Unicode content.
    fn get_clipboard_text(&self) -> Result<String> {
        unsafe {
            use windows::Win32::System::DataExchange::{
                GetClipboardData, OpenClipboard, CloseClipboard,
            };
            use windows::Win32::System::Memory::{GlobalLock, GlobalUnlock};

            OpenClipboard(None)?;
            let handle = GetClipboardData(13u32)?; // CF_UNICODETEXT
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
    }
}
