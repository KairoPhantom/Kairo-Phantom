/// Fuzz target: UIA text parser
/// Attack surface: arbitrary Unicode text from any application window
/// 
/// Validates: DocumentContext::from_raw_text() never panics on any input,
/// including 100KB of zero-width joiners, RTL text, null bytes, surrogates
#![no_main]
use libfuzzer_sys::fuzz_target;
use phantom_core::document_context::{DocumentContext, DocKind};

fuzz_target!(|data: &[u8]| {
    // Convert arbitrary bytes to a UTF-8 string (lossy — exactly what UIA does)
    let text = String::from_utf8_lossy(data);
    
    // Must NEVER panic on any input — this is the UIA contract
    let _ctx = DocumentContext::from_raw_text(&text, &text, DocKind::PlainText);
    
    // Also test the system prompt fragment — must not panic
    let ctx = DocumentContext::from_raw_text("test", &text, DocKind::WordDocument);
    let _fragment = ctx.to_system_prompt_fragment();
});
