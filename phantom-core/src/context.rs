/// Context Engine — The brain of Kairo's document awareness.
/// Extracts the user's EXACT prompt (last paragraph/selection) and
/// identifies the precise application environment for context-aware AI responses.

#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{
    GetForegroundWindow, GetWindowTextW, GetWindowThreadProcessId,
};
#[cfg(windows)]
use windows::Win32::System::Threading::{
    OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION, QueryFullProcessImageNameW, PROCESS_NAME_WIN32,
};

/// Identifies the exact type of application the user is writing in.
// ... (Updating AppEnvironment and classify_environment)
#[derive(Debug, Clone, PartialEq)]
pub enum AppEnvironment {
    // Office Suite
    MicrosoftWord,
    MicrosoftPowerPoint,
    MicrosoftExcel,
    MicrosoftOutlook,
    // Modern Productivity & Design
    Notion,
    Figma,
    Canva,
    // Code / Dev
    VSCode,
    WindowsTerminal,
    PowerShell,
    CommandPrompt,
    Vim,
    Notepad,
    NotepadPlusPlus,
    // Browser / Web Apps
    Chrome,
    Firefox,
    Edge,
    // Communication
    Slack,
    Teams,
    Discord,
    // Other
    Unknown(String),
}

impl AppEnvironment {
    /// Returns the AI formatting directive for this environment.
    pub fn ai_directive(&self) -> &'static str {
        match self {
            AppEnvironment::MicrosoftWord | AppEnvironment::MicrosoftOutlook => {
                "ENVIRONMENT: Microsoft Word (Professional Document). Write in formal, polished prose. Use proper paragraph breaks. No markdown, no asterisks, no code fences. Focus on professional justification and alignment."
            }
            AppEnvironment::MicrosoftPowerPoint => {
                "ENVIRONMENT: Microsoft PowerPoint. Structure output as: **Title:** [slide title] followed by bullet points (one per line, start with -). Suggest image placements using [IMAGE: description] tags."
            }
            AppEnvironment::Notion => {
                "ENVIRONMENT: Notion Workspace. Use rich markdown formatting, headers (##), bold text, bullet points, and callout blocks if necessary. Highly structured, aesthetic documentation."
            }
            AppEnvironment::Figma | AppEnvironment::Canva => {
                "ENVIRONMENT: Design Tool (Figma/Canva). Focus on visual copy, layout structures, short punchy headlines, and image generation prompts [IMAGE: ...]. Do not write long paragraphs."
            }
            AppEnvironment::MicrosoftExcel => {
                "ENVIRONMENT: Microsoft Excel. Provide data-focused, concise responses. Use comma-separated or tab-separated values for tables."
            }
            AppEnvironment::VSCode => {
                "ENVIRONMENT: VS Code (Code Editor). Output ONLY clean, syntactically valid code. NO explanations, NO markdown fences, NO preamble. Raw code only."
            }
            AppEnvironment::WindowsTerminal | AppEnvironment::PowerShell | AppEnvironment::CommandPrompt => {
                "ENVIRONMENT: Terminal / Shell. Output ONLY shell commands or script. No explanations. One command per line."
            }
            AppEnvironment::Vim | AppEnvironment::NotepadPlusPlus => {
                "ENVIRONMENT: Code/Text Editor. Output raw text or code only. No markdown formatting."
            }
            AppEnvironment::Notepad => {
                "ENVIRONMENT: Notepad (Plain Text). Write clean plain text. No markdown. No formatting characters."
            }
            AppEnvironment::Chrome | AppEnvironment::Firefox | AppEnvironment::Edge => {
                "ENVIRONMENT: Web Browser. Adapt to the context. If Notion/Canva detected in title, format accordingly."
            }
            AppEnvironment::Slack | AppEnvironment::Discord => {
                "ENVIRONMENT: Messaging App. Use concise, conversational tone. Short sentences. Emojis where appropriate."
            }
            AppEnvironment::Teams => {
                "ENVIRONMENT: Microsoft Teams. Professional, clear, concise messaging appropriate for workplace communication."
            }
            AppEnvironment::Unknown(_) => {
                "ENVIRONMENT: General purpose. Write in clear, professional prose unless the request implies code."
            }
        }
    }

    /// Returns a short human-readable label for logging.
    pub fn label(&self) -> String {
        match self {
            AppEnvironment::MicrosoftWord => "Microsoft Word".into(),
            AppEnvironment::MicrosoftPowerPoint => "PowerPoint".into(),
            AppEnvironment::MicrosoftExcel => "Excel".into(),
            AppEnvironment::MicrosoftOutlook => "Outlook".into(),
            AppEnvironment::Notion => "Notion".into(),
            AppEnvironment::Figma => "Figma".into(),
            AppEnvironment::Canva => "Canva".into(),
            AppEnvironment::VSCode => "VS Code".into(),
            AppEnvironment::WindowsTerminal => "Windows Terminal".into(),
            AppEnvironment::PowerShell => "PowerShell".into(),
            AppEnvironment::CommandPrompt => "Command Prompt".into(),
            AppEnvironment::Vim => "Vim".into(),
            AppEnvironment::Notepad => "Notepad".into(),
            AppEnvironment::NotepadPlusPlus => "Notepad++".into(),
            AppEnvironment::Chrome => "Chrome".into(),
            AppEnvironment::Firefox => "Firefox".into(),
            AppEnvironment::Edge => "Edge".into(),
            AppEnvironment::Slack => "Slack".into(),
            AppEnvironment::Teams => "Teams".into(),
            AppEnvironment::Discord => "Discord".into(),
            AppEnvironment::Unknown(name) => name.clone(),
        }
    }
}

/// Full context snapshot captured at the moment Alt+M is pressed.
#[derive(Debug, Clone)]
pub struct DocumentContext {
    /// The process name (e.g., "WINWORD.EXE")
    pub process_name: String,
    /// The window title (e.g., "Document1 - Microsoft Word")
    pub window_title: String,
    /// The detected application environment
    pub environment: AppEnvironment,
    /// The exact user prompt (last paragraph only — what to replace)
    pub prompt_text: String,
    /// Character count of prompt (used for exact erasure)
    pub prompt_char_count: usize,
    /// Full document context (for AI understanding — not erased)
    pub document_text: String,
}

pub struct ContextEngine;

impl ContextEngine {
    pub fn new() -> Self {
        ContextEngine
    }

    /// Captures the complete document context at hotkey press time.
    pub fn capture(&self, full_text: &str) -> DocumentContext {
        let (process_name, window_title) = self.get_active_app_info();
        let environment = Self::classify_environment(&process_name, &window_title);

        // Extract just the last paragraph (user's actual prompt)
        // This is the segment we'll erase and replace
        let prompt_text = Self::extract_last_paragraph(full_text);
        let prompt_char_count = prompt_text.chars().count();

        tracing::info!(
            "📍 Context: env={} | prompt='{}...' ({} chars)",
            environment.label(),
            &prompt_text.chars().take(30).collect::<String>(),
            prompt_char_count
        );

        DocumentContext {
            process_name,
            window_title,
            environment,
            prompt_char_count,
            document_text: full_text.to_string(),
            prompt_text,
        }
    }

    /// Classify the app environment from process name and window title.
    pub fn classify_environment(process_name: &str, window_title: &str) -> AppEnvironment {
        let proc = process_name.to_lowercase();
        let title = window_title.to_lowercase();

        // Office Suite
        if proc.contains("winword") { return AppEnvironment::MicrosoftWord; }
        if proc.contains("powerpnt") { return AppEnvironment::MicrosoftPowerPoint; }
        if proc.contains("excel") { return AppEnvironment::MicrosoftExcel; }
        if proc.contains("outlook") { return AppEnvironment::MicrosoftOutlook; }

        // Code Editors
        if proc.contains("code") && !proc.contains("discord") { return AppEnvironment::VSCode; }
        if proc.contains("notepad++") || proc.contains("notepadplusplus") { return AppEnvironment::NotepadPlusPlus; }
        if proc.contains("notepad") { return AppEnvironment::Notepad; }
        if proc.contains("vim") || proc.contains("nvim") { return AppEnvironment::Vim; }

        // Terminals
        if proc.contains("windowsterminal") { return AppEnvironment::WindowsTerminal; }
        if proc.contains("powershell") || title.contains("powershell") { return AppEnvironment::PowerShell; }
        if proc.contains("cmd") || title.contains("command prompt") { return AppEnvironment::CommandPrompt; }

        // Browsers & Web Apps
        if title.contains("notion") || proc.contains("notion") { return AppEnvironment::Notion; }
        if title.contains("figma") || proc.contains("figma") { return AppEnvironment::Figma; }
        if title.contains("canva") || proc.contains("canva") { return AppEnvironment::Canva; }

        if proc.contains("chrome") || proc.contains("chromium") { return AppEnvironment::Chrome; }
        if proc.contains("firefox") { return AppEnvironment::Firefox; }
        if proc.contains("msedge") { return AppEnvironment::Edge; }

        // Communication
        if proc.contains("slack") { return AppEnvironment::Slack; }
        if proc.contains("teams") { return AppEnvironment::Teams; }
        if proc.contains("discord") { return AppEnvironment::Discord; }

        AppEnvironment::Unknown(process_name.to_string())
    }

    /// Extract the last non-empty paragraph (the user's actual prompt).
    /// This is what Kairo will erase and replace with AI output.
    pub fn extract_last_paragraph(text: &str) -> String {
        // Split by paragraph breaks and take the last non-empty one
        let paragraphs: Vec<&str> = text
            .split(|c| c == '\n' || c == '\r')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .collect();

        paragraphs.last().unwrap_or(&"").to_string()
    }

    /// Get the active foreground process name and window title.
    fn get_active_app_info(&self) -> (String, String) {
        #[cfg(windows)]
        unsafe {
            let hwnd = GetForegroundWindow();
            if hwnd.is_invalid() {
                return ("Unknown".into(), "Unknown".into());
            }

            // Window title
            let mut title_buf = [0u16; 512];
            let title_len = GetWindowTextW(hwnd, &mut title_buf);
            let title = String::from_utf16_lossy(&title_buf[..title_len as usize]);

            // Process name
            let mut pid = 0u32;
            GetWindowThreadProcessId(hwnd, Some(&mut pid));

            if let Ok(handle) = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) {
                let mut path_buf = [0u16; 1024];
                let mut path_len = path_buf.len() as u32;
                if QueryFullProcessImageNameW(
                    handle,
                    PROCESS_NAME_WIN32,
                    windows::core::PWSTR(path_buf.as_mut_ptr()),
                    &mut path_len,
                )
                .is_ok()
                {
                    let full_path = String::from_utf16_lossy(&path_buf[..path_len as usize]);
                    let proc_name = std::path::Path::new(&full_path)
                        .file_name()
                        .and_then(|n| n.to_str())
                        .unwrap_or("Unknown")
                        .to_string();
                    return (proc_name, title);
                }
            }
            ("Unknown".into(), title)
        }

        #[cfg(not(windows))]
        ("Unknown".into(), "Unknown".into())
    }
}
