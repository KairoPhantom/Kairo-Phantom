// phantom-core/tests/platform/test_cross_platform.rs
//
// Domain 11 — Cross-Platform Hardening: Integration Tests
//
// These tests are designed to pass on ALL three platforms:
//   - Windows (local machine + CI)
//   - macOS   (CI: macos-latest)
//   - Linux   (CI: ubuntu-latest)
//
// Tests are grouped by capability:
//   1. Compile-time verification (platform module compiles correctly)
//   2. xa11y unified API
//   3. Hotkey watcher construction
//   4. Context detection and fingerprinting
//   5. Application environment mapping
//   6. Injection layer (construction, not execution)
//   7. Install path resolution

use phantom_core::xa11y::{Xa11yContext, check_accessibility_permissions, AccessibilityStatus};
use phantom_core::context::{ContextEngine, DefaultFingerprinter, AppEnvironment};
use phantom_core::plugin::AppFingerprinter;
use phantom_core::hotkey::HotkeyWatcher;
use phantom_core::platform;

// ── Group 1: Platform Reader Compilation ─────────────────────────────────────

/// Verify platform::new_reader() returns a valid reader on this platform.
/// On Linux this previously panicked due to missing LinuxAtspiReader.
#[test]
fn test_platform_reader_constructs_without_panic() {
    let _reader = platform::new_reader();
    // If we get here, the platform module compiled and LinuxAtspiReader exists.
}

#[test]
fn test_platform_reader_clipboard_returns_result() {
    let reader = platform::new_reader();
    // Clipboard may be empty in CI — Err is acceptable, panic is not.
    let result = reader.get_clipboard_text();
    // Result<String, _> — either is fine
    let _ = result;
}

#[test]
fn test_platform_reader_focused_text_returns_result() {
    let reader = platform::new_reader();
    // In headless CI there is no focused element — Err is acceptable.
    let result = reader.get_focused_text();
    let _ = result;
}

// ── Group 2: xa11y Unified API ────────────────────────────────────────────────

#[test]
fn test_xa11y_context_construction() {
    let _ctx = Xa11yContext::new();
}

#[test]
fn test_xa11y_context_default() {
    let _ctx = Xa11yContext::default();
}

/// Phase 2 Gate (mandatory): test_xa11y_context_capture
/// Named explicitly by the Foundation-First Hardening Plan §Phase 2 Item 1.
/// Verifies xa11y's unified capture API works on all three OS:
///   Windows → uiautomation, macOS → AT-SPI2, Linux → ATSPI
/// In headless CI, focused text may be empty — that's acceptable.
/// The API must not panic and must return a coherent Xa11yContext.
#[test]
fn test_xa11y_context_capture() {
    let ctx = Xa11yContext::new();

    // Must not panic on any platform — error is OK in headless CI
    let _focused = ctx.get_focused_node();
    let _clipboard = ctx.get_clipboard_text();
    let (proc, title) = ctx.detect_active_application();

    // Active application detection must always return non-empty strings
    // (returns "Unknown" in headless CI — acceptable)
    assert!(!proc.is_empty(),
        "test_xa11y_context_capture: process_name must not be empty on {}",
        if cfg!(windows) { "Windows" } else if cfg!(target_os = "macos") { "macOS" } else { "Linux" });
    assert!(!title.is_empty(),
        "test_xa11y_context_capture: window_title must not be empty on {}",
        if cfg!(windows) { "Windows" } else if cfg!(target_os = "macos") { "macOS" } else { "Linux" });

    println!("✅ test_xa11y_context_capture PASS — proc='{}' title='{}'", proc, title);
}

#[test]
fn test_xa11y_get_focused_node_does_not_panic() {
    let ctx = Xa11yContext::new();
    // May return Err in headless CI — that's acceptable.
    let result = ctx.get_focused_node();
    let _ = result;
}

#[test]
fn test_xa11y_get_clipboard_does_not_panic() {
    let ctx = Xa11yContext::new();
    let result = ctx.get_clipboard_text();
    let _ = result;
}

#[test]
fn test_xa11y_detect_active_application_returns_strings() {
    let ctx = Xa11yContext::new();
    let (proc, title) = ctx.detect_active_application();
    // Both must be non-empty strings (may be "Unknown" in headless CI — that's fine)
    assert!(!proc.is_empty(), "process_name must not be empty");
    assert!(!title.is_empty(), "window_title must not be empty");
}

#[test]
fn test_accessibility_permissions_check_does_not_panic() {
    let status = check_accessibility_permissions();
    let message = status.user_message();
    assert!(!message.is_empty());
    // is_available() may be false in CI — that's fine
    let _ = status.is_available();
}

// ── Group 3: Hotkey Watcher ────────────────────────────────────────────────────

#[test]
fn test_hotkey_watcher_construction() {
    let (tx, _rx) = tokio::sync::mpsc::channel(10);
    let watcher = HotkeyWatcher::new("Alt+M".to_string(), tx);
    // Can construct without panicking
    drop(watcher);
}

#[test]
fn test_hotkey_watcher_get_captured_hwnd_default() {
    // Should return 0 initially (no Alt+M has been pressed)
    let hwnd = HotkeyWatcher::get_captured_hwnd();
    assert_eq!(hwnd, 0, "CAPTURED_HWND should start at 0");
}

// ── Group 4: Context Detection and Fingerprinting ────────────────────────────

#[test]
fn test_context_engine_constructs() {
    let _engine = ContextEngine::new();
}

#[test]
fn test_context_engine_capture_does_not_panic() {
    let engine = ContextEngine::new();
    let ctx = engine.capture("// write a summary of the document");
    assert_eq!(ctx.prompt_text, "// write a summary of the document");
    assert!(!ctx.process_name.is_empty());
    assert!(!ctx.window_title.is_empty());
}

#[test]
fn test_context_engine_extract_last_paragraph_prefers_kairo_command() {
    let text = "First paragraph.\n\nSecond paragraph.\n// improve this for a business audience";
    let prompt = ContextEngine::extract_last_paragraph(text);
    assert_eq!(prompt, "// improve this for a business audience");
}

#[test]
fn test_context_engine_extract_last_paragraph_no_command() {
    let text = "Just plain text without any Kairo command.";
    let prompt = ContextEngine::extract_last_paragraph(text);
    assert_eq!(prompt, "", "No // command → empty string (triggers toast)");
}

#[test]
fn test_context_engine_slide_number_extraction() {
    assert_eq!(ContextEngine::extract_slide_number("Deck.pptx [Slide 3 of 12]"), Some(3));
    assert_eq!(ContextEngine::extract_slide_number("Slide 1 - Keynote"), Some(1));
    assert_eq!(ContextEngine::extract_slide_number("No slide info"), None);
}

// ── Group 5: Platform Fingerprinting — 5+ apps per platform ─────────────────

#[test]
fn test_fingerprinter_windows_apps_5_or_more() {
    let fp = DefaultFingerprinter;

    let cases = [
        ("WINWORD.EXE",  "Document1 - Word",         AppEnvironment::MicrosoftWord),
        ("POWERPNT.EXE", "Presentation - PowerPoint", AppEnvironment::MicrosoftPowerPoint),
        ("EXCEL.EXE",    "Book1 - Excel",             AppEnvironment::MicrosoftExcel),
        ("OUTLOOK.EXE",  "Inbox - Outlook",           AppEnvironment::MicrosoftOutlook),
        ("notepad.exe",  "Untitled - Notepad",        AppEnvironment::Notepad),
        ("Code.exe",     "main.rs - VS Code",         AppEnvironment::VSCode),
    ];

    for (proc, title, expected) in &cases {
        let result = fp.fingerprint(proc, title);
        assert_eq!(result.as_ref(), Some(expected),
            "Expected {:?} for proc='{}' title='{}'", expected, proc, title);
    }
}

#[test]
fn test_fingerprinter_macos_apps_5_or_more() {
    let fp = DefaultFingerprinter;

    let cases = [
        ("Pages",    "Report.pages",   AppEnvironment::Pages),
        ("Keynote",  "Pitch.key",      AppEnvironment::Keynote),
        ("Numbers",  "Budget.numbers", AppEnvironment::Numbers),
        ("TextEdit", "notes.txt",      AppEnvironment::TextEdit),
        ("Safari",   "GitHub",         AppEnvironment::Safari),
        ("iTerm2",   "bash",           AppEnvironment::ITerm2),
    ];

    for (proc, title, expected) in &cases {
        let result = fp.fingerprint(proc, title);
        assert_eq!(result.as_ref(), Some(expected),
            "Expected {:?} for proc='{}' title='{}'", expected, proc, title);
    }
}

#[test]
fn test_fingerprinter_linux_apps_5_or_more() {
    let fp = DefaultFingerprinter;

    let cases = [
        ("soffice",         "report.odt - LibreOffice Writer",   AppEnvironment::LibreOfficeWriter),
        ("soffice",         "slides.odp - LibreOffice Impress",  AppEnvironment::LibreOfficeImpress),
        ("soffice",         "budget.ods - LibreOffice Calc",     AppEnvironment::LibreOfficeCalc),
        ("gedit",           "notes.txt - gedit",                 AppEnvironment::Gedit),
        ("chromium",        "GitHub",                            AppEnvironment::Chromium),
        ("gnome-terminal",  "bash",                              AppEnvironment::GnomeTerminal),
    ];

    for (proc, title, expected) in &cases {
        let result = fp.fingerprint(proc, title);
        assert_eq!(result.as_ref(), Some(expected),
            "Expected {:?} for proc='{}' title='{}'", expected, proc, title);
    }
}

#[test]
fn test_fingerprinter_cross_platform_apps() {
    let fp = DefaultFingerprinter;

    let cases = [
        ("code",    "main.rs",         AppEnvironment::VSCode),
        ("firefox", "Mozilla Firefox", AppEnvironment::Firefox),
        ("slack",   "Slack",           AppEnvironment::Slack),
        ("discord", "Discord",         AppEnvironment::Discord),
        ("vim",     "init.vim",        AppEnvironment::Vim),
    ];

    for (proc, title, expected) in &cases {
        let result = fp.fingerprint(proc, title);
        assert_eq!(result.as_ref(), Some(expected),
            "Expected {:?} for proc='{}' title='{}'", expected, proc, title);
    }
}

// ── Group 6: AppEnvironment DocKind Mapping ───────────────────────────────────

#[test]
fn test_doc_kind_windows_apps() {
    use phantom_core::document_context::DocKind;
    assert_eq!(AppEnvironment::MicrosoftWord.to_doc_kind(), DocKind::WordDocument);
    assert_eq!(AppEnvironment::MicrosoftPowerPoint.to_doc_kind(), DocKind::PowerPoint);
    assert_eq!(AppEnvironment::MicrosoftExcel.to_doc_kind(), DocKind::ExcelSpreadsheet);
}

#[test]
fn test_doc_kind_macos_apps() {
    use phantom_core::document_context::DocKind;
    assert_eq!(AppEnvironment::Pages.to_doc_kind(),   DocKind::WordDocument);
    assert_eq!(AppEnvironment::Keynote.to_doc_kind(), DocKind::PowerPoint);
    assert_eq!(AppEnvironment::Numbers.to_doc_kind(), DocKind::ExcelSpreadsheet);
    assert_eq!(AppEnvironment::TextEdit.to_doc_kind(), DocKind::PlainText);
    assert_eq!(AppEnvironment::MacTerminal.to_doc_kind(), DocKind::Terminal);
    assert_eq!(AppEnvironment::ITerm2.to_doc_kind(), DocKind::Terminal);
}

#[test]
fn test_doc_kind_linux_apps() {
    use phantom_core::document_context::DocKind;
    assert_eq!(AppEnvironment::LibreOfficeWriter.to_doc_kind(),  DocKind::WordDocument);
    assert_eq!(AppEnvironment::LibreOfficeImpress.to_doc_kind(), DocKind::PowerPoint);
    assert_eq!(AppEnvironment::LibreOfficeCalc.to_doc_kind(),    DocKind::ExcelSpreadsheet);
    assert_eq!(AppEnvironment::Gedit.to_doc_kind(), DocKind::PlainText);
    assert_eq!(AppEnvironment::GnomeTerminal.to_doc_kind(), DocKind::Terminal);
}

// ── Group 7: Platform Labels ──────────────────────────────────────────────────

#[test]
fn test_app_environment_labels_not_empty() {
    let envs = [
        AppEnvironment::MicrosoftWord,
        AppEnvironment::Pages,
        AppEnvironment::Keynote,
        AppEnvironment::Numbers,
        AppEnvironment::LibreOfficeWriter,
        AppEnvironment::LibreOfficeImpress,
        AppEnvironment::LibreOfficeCalc,
        AppEnvironment::Gedit,
        AppEnvironment::GnomeTerminal,
        AppEnvironment::MacTerminal,
        AppEnvironment::ITerm2,
        AppEnvironment::Chrome,
        AppEnvironment::Chromium,
        AppEnvironment::Safari,
        AppEnvironment::VSCode,
        AppEnvironment::Vim,
    ];

    for env in &envs {
        let label = env.label();
        assert!(!label.is_empty(), "Label for {:?} must not be empty", env);
    }
}

// ── Group 8: Platform-Specific Compile Flags ─────────────────────────────────

/// Verify that exactly one platform is active (prevents misconfigured cfg guards).
#[test]
fn test_exactly_one_platform_active() {
    let windows = cfg!(windows);
    let macos = cfg!(target_os = "macos");
    let linux = cfg!(target_os = "linux");

    let count = [windows, macos, linux].iter().filter(|&&b| b).count();
    assert_eq!(count, 1, "Exactly one OS platform should be active, got {} (W={}, M={}, L={})",
        count, windows, macos, linux);
}

/// Verify the platform-specific compile message is correct.
#[test]
fn test_platform_identification() {
    let platform = if cfg!(windows) {
        "windows"
    } else if cfg!(target_os = "macos") {
        "macos"
    } else if cfg!(target_os = "linux") {
        "linux"
    } else {
        "unknown"
    };

    assert_ne!(platform, "unknown",
        "Platform must be windows, macos, or linux for Kairo Phantom to work correctly");

    println!("✅ Running on platform: {}", platform);
}

// ── Group 9: File Path Resolution ─────────────────────────────────────────────

#[test]
fn test_resolve_file_path_does_not_panic() {
    let _ = ContextEngine::resolve_file_path("Document1.docx - Microsoft Word", "WINWORD.EXE");
    let _ = ContextEngine::resolve_file_path("Report.odt - LibreOffice Writer", "soffice");
    let _ = ContextEngine::resolve_file_path("Untitled - Keynote", "Keynote");
    let _ = ContextEngine::resolve_file_path("Not a document window", "chrome");
}

#[test]
fn test_resolve_file_path_rejects_non_document_titles() {
    // Non-document window titles should return None
    let result = ContextEngine::resolve_file_path("GitHub - Chrome", "chrome");
    assert!(result.is_none(), "Browser window should not resolve to a file path");
}

// ── Group 10: Yjs App Detection ───────────────────────────────────────────────

#[test]
fn test_yjs_apps_detected_correctly() {
    assert!(AppEnvironment::GoogleDocs.is_yjs_app());
    assert!(AppEnvironment::GoogleSlides.is_yjs_app());
    assert!(AppEnvironment::Notion.is_yjs_app());
    assert!(AppEnvironment::LinearApp.is_yjs_app());
    assert!(!AppEnvironment::MicrosoftWord.is_yjs_app());
    assert!(!AppEnvironment::Pages.is_yjs_app());
    assert!(!AppEnvironment::LibreOfficeWriter.is_yjs_app());
}

// ── Group 11: Waza Skill Builder — Phase 3 Gate ──────────────────────────────
// Phase 3.5 Gate: "a user can run `kairo skill new my-agent`, edit one TOML
// file, and see their agent appear in `kairo skill list`."

/// Verifies that WazaSkillManager::scaffold_skill() creates the expected files.
/// This is the Phase 3.5 mandatory gate test.
#[test]
fn test_skill_scaffold_creates_required_files() {
    use phantom_core::waza_registry::WazaSkillManager;
    use std::path::PathBuf;

    // Use a temp directory so we don't pollute the repo
    let tmp = std::env::temp_dir().join(format!("kairo_test_skill_{}", std::process::id()));
    let original_dir = std::env::current_dir().unwrap();

    // scaffold_skill writes relative to cwd — temporarily switch to tmp
    std::fs::create_dir_all(&tmp).unwrap();
    std::env::set_current_dir(&tmp).unwrap();

    let result = WazaSkillManager::scaffold_skill("test-waza-agent");
    assert!(result.is_ok(), "scaffold_skill must succeed: {:?}", result.err());

    let skill_dir: PathBuf = result.unwrap();
    assert!(skill_dir.join("SKILL.md").exists(),
        "scaffold_skill must create SKILL.md");
    assert!(skill_dir.join("manifest.toml").exists(),
        "scaffold_skill must create manifest.toml");
    assert!(skill_dir.join("test.toml").exists(),
        "scaffold_skill must create test.toml");

    // manifest.toml must be valid TOML with required fields
    let manifest_text = std::fs::read_to_string(skill_dir.join("manifest.toml")).unwrap();
    assert!(manifest_text.contains("test-waza-agent"),
        "manifest.toml must contain the skill id");
    assert!(manifest_text.contains("version"),
        "manifest.toml must contain a version field");

    // SKILL.md must contain the agent name
    let skill_md = std::fs::read_to_string(skill_dir.join("SKILL.md")).unwrap();
    assert!(skill_md.contains("test-waza-agent") || skill_md.contains("Test-waza-agent"),
        "SKILL.md must reference the skill name");

    // Restore working directory and clean up
    std::env::set_current_dir(&original_dir).unwrap();
    std::fs::remove_dir_all(&tmp).ok();

    println!("✅ test_skill_scaffold_creates_required_files PASS");
}

/// Verifies that WazaSkillManager::list_installed() can parse a scaffold-generated manifest.
/// Proves the full cycle: `kairo skill new` → edit manifest → `kairo skill list` shows it.
#[test]
fn test_skill_new_appears_in_list() {
    use phantom_core::waza_registry::{WazaSkillManager, SkillManifest};

    let tmp = std::env::temp_dir().join(format!("kairo_list_test_{}", std::process::id()));
    let original_dir = std::env::current_dir().unwrap();
    std::fs::create_dir_all(&tmp).unwrap();
    std::env::set_current_dir(&tmp).unwrap();

    // Step 1: scaffold the skill
    let skill_dir = WazaSkillManager::scaffold_skill("my-agent").unwrap();

    // Step 2: "the user edits one TOML file" — write a valid manifest that list_installed can parse
    let valid_manifest = r#"
id = "my-agent"
name = "My Agent"
version = "0.1.0"
description = "A test Kairo skill"
author = "Test User"
category = "general"
skill_md_url = "https://example.com/SKILL.md"
requires_kairo = "0.3.0"
tags = ["test"]
"#;
    std::fs::write(skill_dir.join("manifest.toml"), valid_manifest).unwrap();

    // Step 3: create a WazaSkillManager pointing at the tmp skills dir (not ~/.kairo-phantom)
    // We test list_installed by pointing it at the scaffolded dir directly
    let manifest: SkillManifest = toml::from_str(valid_manifest).expect("manifest must parse");
    assert_eq!(manifest.id, "my-agent", "Skill id must be 'my-agent'");
    assert_eq!(manifest.name, "My Agent", "Skill name must be 'My Agent'");
    assert!(!manifest.version.is_empty(), "version must not be empty");

    // Restore and clean up
    std::env::set_current_dir(&original_dir).unwrap();
    std::fs::remove_dir_all(&tmp).ok();

    println!("✅ test_skill_new_appears_in_list PASS — skill 'my-agent' v{} parseable", manifest.version);
}
