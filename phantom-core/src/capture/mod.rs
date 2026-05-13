pub mod pii;
pub mod fallback;
#[cfg(target_os = "windows")]
pub mod windows;
#[cfg(target_os = "macos")]
pub mod macos;

#[derive(Debug, Clone)]
pub struct CapturedContext {
    pub user_prompt: String,
    pub document_context: String,
    pub app_name: String,
    pub section_title: Option<String>,
}

pub struct SmartContextCapture;

impl SmartContextCapture {
    pub fn capture() -> Result<CapturedContext, String> {
        // 1. Platform specific raw capture
        #[cfg(target_os = "windows")]
        let (app_name, raw_text) = windows::capture_active_window()?;
        #[cfg(target_os = "macos")]
        let (app_name, raw_text) = macos::capture_active_window()?;
        #[cfg(not(any(target_os = "windows", target_os = "macos")))]
        let (app_name, raw_text) = ("UnknownApp".to_string(), "Mock raw text...".to_string());

        // 2. Semantic windowing (Structural fallback)
        let windowed_text = fallback::semantic_window(&raw_text);

        // 3. Prompt extraction
        let (prompt, mut context) = fallback::extract_prompt(&windowed_text);

        // 4. PII masking inline
        context = pii::mask_pii(&context);

        Ok(CapturedContext {
            user_prompt: prompt,
            document_context: context,
            app_name,
            section_title: None, // Requires full UIA TextPattern implementation
        })
    }
}
