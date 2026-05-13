/// Context Engine — The brain of Kairo's document awareness.
/// Extracts the user's EXACT prompt (last paragraph/selection) and
/// identifies the precise application environment for context-aware AI responses.
/// v3.0: Also resolves the active document file path and slide number
/// from the window title for structured document extraction.

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
    // Yjs-powered collaborative apps (Advancement 1)
    GoogleDocs,
    GoogleSlides,
    LinearApp,
    TiptapEditor,
    Liveblocks,
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
    /*
    /// Returns the AI formatting directive for this environment.
    pub fn ai_directive(&self) -> &'static str {
        match self {
            // ... (directives)
        }
    }
    */

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
            // Yjs apps
            AppEnvironment::GoogleDocs => "Google Docs".into(),
            AppEnvironment::GoogleSlides => "Google Slides".into(),
            AppEnvironment::LinearApp => "Linear".into(),
            AppEnvironment::TiptapEditor => "Tiptap Editor".into(),
            AppEnvironment::Liveblocks => "Liveblocks".into(),
            AppEnvironment::Unknown(name) => name.clone(),
        }
    }

    /// Returns true if this app is Yjs-powered — triggers CRDT peer injection.
    pub fn is_yjs_app(&self) -> bool {
        matches!(self,
            AppEnvironment::GoogleDocs |
            AppEnvironment::GoogleSlides |
            AppEnvironment::Notion |
            AppEnvironment::LinearApp |
            AppEnvironment::TiptapEditor |
            AppEnvironment::Liveblocks
        )
    }

    /// Convert to the canonical DocKind for structured document context.
    pub fn to_doc_kind(&self) -> crate::document_context::DocKind {
        use crate::document_context::DocKind;
        match self {
            AppEnvironment::MicrosoftWord | AppEnvironment::MicrosoftOutlook => DocKind::WordDocument,
            AppEnvironment::MicrosoftPowerPoint => DocKind::PowerPoint,
            AppEnvironment::MicrosoftExcel => DocKind::ExcelSpreadsheet,
            AppEnvironment::Notion | AppEnvironment::TiptapEditor | AppEnvironment::Liveblocks => DocKind::NotionPage,
            AppEnvironment::GoogleDocs => DocKind::YjsDocument,
            AppEnvironment::GoogleSlides => DocKind::YjsDocument,
            AppEnvironment::LinearApp => DocKind::YjsDocument,
            AppEnvironment::Figma => DocKind::FigmaDesign,
            AppEnvironment::Canva => DocKind::CanvaDesign,
            AppEnvironment::VSCode | AppEnvironment::Vim | AppEnvironment::NotepadPlusPlus => DocKind::CodeFile,
            AppEnvironment::WindowsTerminal | AppEnvironment::PowerShell | AppEnvironment::CommandPrompt => DocKind::Terminal,
            AppEnvironment::Notepad => DocKind::PlainText,
            _ => DocKind::UnknownApp,
        }
    }
}

/// Raw capture snapshot from the hotkey moment.
/// This is the intermediate struct before DocumentContext enrichment.
/// v3.0: Renamed from DocumentContext to AppContext to avoid collision
/// with the canonical document_context::DocumentContext.
#[derive(Debug, Clone)]
pub struct AppContext {
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
    /// Full document text from UIA
    pub document_text: String,
    /// Resolved file path (from window title parsing)
    pub file_path: Option<std::path::PathBuf>,
    /// Active slide number (parsed from PowerPoint window title)
    pub active_slide: Option<usize>,
}

use crate::plugin::{AppFingerprinter, FingerprinterRegistry};

pub struct DefaultFingerprinter;

impl AppFingerprinter for DefaultFingerprinter {
    fn fingerprint(&self, process_name: &str, window_title: &str) -> Option<AppEnvironment> {
        let proc = process_name.to_lowercase();
        let title = window_title.to_lowercase();

        // Office Suite
        if proc.contains("winword") { return Some(AppEnvironment::MicrosoftWord); }
        if proc.contains("powerpnt") { return Some(AppEnvironment::MicrosoftPowerPoint); }
        if proc.contains("excel") { return Some(AppEnvironment::MicrosoftExcel); }
        if proc.contains("outlook") { return Some(AppEnvironment::MicrosoftOutlook); }

        // Code Editors
        if proc.contains("code") && !proc.contains("discord") { return Some(AppEnvironment::VSCode); }
        if proc.contains("notepad++") || proc.contains("notepadplusplus") { return Some(AppEnvironment::NotepadPlusPlus); }
        if proc.contains("notepad") { return Some(AppEnvironment::Notepad); }
        if proc.contains("vim") || proc.contains("nvim") { return Some(AppEnvironment::Vim); }

        // Terminals
        if proc.contains("windowsterminal") { return Some(AppEnvironment::WindowsTerminal); }
        if proc.contains("powershell") || title.contains("powershell") { return Some(AppEnvironment::PowerShell); }
        if proc.contains("cmd") || title.contains("command prompt") { return Some(AppEnvironment::CommandPrompt); }

        // Browsers & Web Apps — check title for Yjs apps FIRST (before generic browser)
        if title.contains("notion") || proc.contains("notion") { return Some(AppEnvironment::Notion); }
        if title.contains("figma") || proc.contains("figma") { return Some(AppEnvironment::Figma); }
        if title.contains("canva") || proc.contains("canva") { return Some(AppEnvironment::Canva); }

        // Yjs-powered collaborative apps (Advancement 1)
        if title.contains("google docs") || title.contains("docs.google.com") {
            return Some(AppEnvironment::GoogleDocs);
        }
        if title.contains("google slides") || title.contains("slides.google.com") {
            return Some(AppEnvironment::GoogleSlides);
        }
        if title.contains("linear") && (proc.contains("linear") || title.contains("linear.app")) {
            return Some(AppEnvironment::LinearApp);
        }
        if title.contains("tiptap") { return Some(AppEnvironment::TiptapEditor); }
        if title.contains("liveblocks") { return Some(AppEnvironment::Liveblocks); }

        if proc.contains("chrome") || proc.contains("chromium") { return Some(AppEnvironment::Chrome); }
        if proc.contains("firefox") { return Some(AppEnvironment::Firefox); }
        if proc.contains("msedge") { return Some(AppEnvironment::Edge); }

        // Communication
        if proc.contains("slack") { return Some(AppEnvironment::Slack); }
        if proc.contains("teams") { return Some(AppEnvironment::Teams); }
        if proc.contains("discord") { return Some(AppEnvironment::Discord); }

        None
    }
}

pub struct ContextEngine {
    pub registry: FingerprinterRegistry,
}


impl Default for ContextEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl ContextEngine {
    pub fn new() -> Self {
        let mut registry = FingerprinterRegistry::new();
        registry.register(Box::new(DefaultFingerprinter));
        
        ContextEngine { registry }
    }


    /// Captures the complete application context at hotkey press time.
    pub fn capture(&self, full_text: &str) -> AppContext {
        let (process_name, window_title) = self.get_active_app_info();
        let environment = self.registry.identify(&process_name, &window_title)
            .unwrap_or(AppEnvironment::Unknown(process_name.clone()));


        // Extract just the last paragraph (user's actual prompt — what gets erased)
        let prompt_text = Self::extract_last_paragraph(full_text);
        let prompt_char_count = prompt_text.chars().count();

        // v3.0: Resolve file path + slide number from window title
        let file_path = Self::resolve_file_path(&window_title, &process_name);
        let active_slide = Self::extract_slide_number(&window_title);

        tracing::info!(
            "📍 Context: env={} | file={:?} | slide={:?} | prompt='{}...' ({} chars)",
            environment.label(),
            file_path.as_ref().and_then(|p| p.file_name()).and_then(|n| n.to_str()),
            active_slide,
            &prompt_text.chars().take(30).collect::<String>(),
            prompt_char_count
        );

        AppContext {
            process_name,
            window_title,
            environment,
            prompt_char_count,
            document_text: full_text.to_string(),
            prompt_text,
            file_path,
            active_slide,
        }
    }

    /// Resolve the document file path from the window title.
    ///
    /// Strategies:
    /// 1. Parse "filename.ext - App Name" pattern from window title
    /// 2. Check if parsed filename exists in common document locations
    /// 3. Return None if unresolvable (graceful fallback to UIA text)
    pub fn resolve_file_path(window_title: &str, _process_name: &str) -> Option<std::path::PathBuf> {
        // Pattern: "Document.docx - Microsoft Word" or "Report.pptx - PowerPoint"
        // Split on " - " and take the first segment
        let parts: Vec<&str> = window_title.splitn(2, " - ").collect();
        let candidate = parts.first()?.trim();

        // Strip common suffixes like "[Read-Only]", "[Compatibility Mode]"
        let clean = candidate
            .trim_end_matches(']')
            .rsplitn(2, '[')
            .last()
            .unwrap_or(candidate)
            .trim();

        // Must have a recognized office extension
        let ext = std::path::Path::new(clean)
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| e.to_lowercase());

        let known_ext = matches!(
            ext.as_deref(),
            Some("docx") | Some("doc") | Some("pptx") | Some("ppt")
            | Some("xlsx") | Some("xls") | Some("odt") | Some("odp")
            | Some("pdf") | Some("md") | Some("txt")
        );

        if !known_ext {
            return None;
        }

        // Search common document locations
        let search_dirs = [
            dirs::document_dir(),
            dirs::desktop_dir(),
            dirs::download_dir(),
        ];

        for dir in search_dirs.iter().flatten() {
            let candidate_path = dir.join(clean);
            if candidate_path.exists() {
                return Some(candidate_path);
            }
        }

        // Return a relative path as a hint even if not yet located on disk
        // (the extractor will return None if the file doesn't exist)
        Some(std::path::PathBuf::from(clean))
    }

    /// Extract the current slide number from a PowerPoint window title.
    /// Handles: "Deck.pptx - PowerPoint [Slide 3 of 12]"
    pub fn extract_slide_number(window_title: &str) -> Option<usize> {
        let title_lower = window_title.to_lowercase();
        if let Some(slide_pos) = title_lower.find("slide ") {
            let after = &window_title[slide_pos + 6..];
            let num_str: String = after.chars().take_while(|c| c.is_ascii_digit()).collect();
            num_str.parse().ok()
        } else {
            None
        }
    }

    // classify_environment removed in favor of FingerprinterRegistry


    /// Extract the last non-empty paragraph (the user's actual prompt).
    /// This is what Kairo will erase and replace with AI output.
    pub fn extract_last_paragraph(text: &str) -> String {
        // Split by paragraph breaks and take the last non-empty one
        let paragraphs: Vec<&str> = text
            .split(['\n', '\r'])
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
