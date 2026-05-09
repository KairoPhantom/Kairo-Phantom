# Phase 2 Plan: Deep Document Understanding
# Kairo Phantom v3.0

## Objective
Wire structured document understanding into the Swarm Brain. When a user presses Alt+M in Word, the AI receives the document's heading hierarchy, table count, and slide position — not just raw selected text.

## Context
- **newfeature.md** contains the complete `DocumentContext` struct spec and `OfficeOxideExtractor` implementation blueprint — use it as the design reference.
- **We build an original implementation** inspired by office_oxide's API patterns. We reference the crate's API surface and write our own integration layer.
- The `DocumentContext` struct becomes the canonical context type used by ALL agents in the Swarm.
- This is an **additive phase** — zero changes to the existing Alt+M flow for apps without office files.

## Files to Create/Modify

### New: `phantom-core/src/document_context.rs`
The complete implementation with:
- `DocumentContext` struct (per `newfeature.md` spec)
- `DocKind` enum (WordDocument, PowerPoint, Excel, ODT, PDF, Markdown, CodeFile, Canva, Notion, Figma, Terminal, UnknownApp)
- `OutlineItem` and `TableData` structs
- `FormatMetadata` struct
- `DocumentContextExtractor` async trait
- `OfficeOxideExtractor` implementing the trait for DOCX/PPTX/XLSX
- `PlainTextFallbackExtractor` for all other apps
- `ExtractorRegistry` (plugin-ready)
- `DocumentContext::plain_text_fallback()` static method
- `DocumentContext::to_system_prompt_fragment()` — injects into Swarm Brain

### Modified: `phantom-core/src/context.rs`
Add file path resolution:
```rust
// After getting AppEnvironment, try to resolve the document file path
fn resolve_file_path(window_title: &str, process_name: &str) -> Option<PathBuf> {
    // Strategy 1: Parse file name from window title
    // Word: "Document.docx - Microsoft Word" → extract "Document.docx"
    // VS Code: "main.rs - kairo-phantom" → extract "main.rs"  
    // Strategy 2: Query process open file handles (Windows: NtQueryInformationProcess)
    // Strategy 3: Return None if path cannot be determined
}
```

### Modified: `phantom-core/src/swarm.rs`
Replace `ctx.prompt_text` string with full `DocumentContext`:
- `SwarmOrchestrator::route()` now receives `&DocumentContext`  
- `build_agent_prompt()` calls `doc_ctx.to_system_prompt_fragment()` and prepends to agent system prompt

### Modified: `phantom-core/Cargo.toml`
```toml
[features]
office = ["office_oxide"]

[dependencies]
office_oxide = { version = "0.1", optional = true }
```

### Modified: `phantom-core/src/main.rs`
Wire `ExtractorRegistry` into the main event loop:
```rust
let extractor_registry = document_context::ExtractorRegistry::with_defaults();
// In the HotkeyPressed handler, after context capture:
let doc_ctx = if let Some(file_path) = ctx.resolve_file_path() {
    extractor_registry
        .find_for_extension(file_path.extension()...)
        .extract(&file_path).await
        .unwrap_or_else(|_| DocumentContext::plain_text_fallback(...))
} else {
    DocumentContext::from_raw_text(&ctx.prompt_text, &ctx.environment)
};
let (backend, profile) = swarm_engine.route(&doc_ctx).await;
```

## Key Implementation Notes

### Window Title Parsing (Word)
```
"Q3 Report.docx - Word" → extract "Q3 Report.docx" → look in recent files
"Q3 Report [Read-Only] - Word" → strip "[Read-Only]"
"Untitled - Word" → no file path (use UIA text only)
```

### Window Title Parsing (PowerPoint)
```
"Pitch Deck.pptx - PowerPoint [Slide 3 of 12]" → extract slide number from title
```

### Graceful Degradation
- If `office_oxide` feature is disabled: `ExtractorRegistry` only has `PlainTextFallbackExtractor`
- If file path cannot be resolved: `DocumentContext::from_raw_text()` preserves existing behavior
- If `office_oxide::Document::open()` fails: log warning, fall back to UIA raw text

### `DocumentContext::from_raw_text()` 
A constructor that creates a minimal `DocumentContext` from the UIA text for non-file-based apps:
```rust
pub fn from_raw_text(text: &str, env: &AppEnvironment) -> Self {
    DocumentContext {
        doc_kind: env.to_doc_kind(),
        file_path: None,
        full_text: text.to_string(),
        outline: vec![],
        tables: vec![],
        active_slide: None,
        total_slides: None,
        has_tracked_changes: false,
        format_metadata: FormatMetadata::default(),
    }
}
```

## Verification Checklist
- [ ] `cargo build --release --features office` compiles
- [ ] `cargo build --release` (no features) compiles with PlainTextFallback only
- [ ] Alt+M in Notepad: system prompt contains "You are assisting inside a plain text editor"
- [ ] Alt+M in VS Code: system prompt contains "You are assisting inside a code file"
- [ ] Alt+M in Word (with .docx): system prompt contains heading outline (if headings exist)
- [ ] Alt+M in PowerPoint: system prompt contains "Currently on slide X/Y"
- [ ] Window without a file (browser, Notepad): falls back to `from_raw_text()` gracefully
- [ ] Swarm Brain receives `DocumentContext` not raw string

## Files Modified Summary
- `phantom-core/src/document_context.rs` (new)
- `phantom-core/src/context.rs` (add file path resolution + `resolve_file_path()`)
- `phantom-core/src/swarm.rs` (route() takes `&DocumentContext`)
- `phantom-core/src/main.rs` (wire ExtractorRegistry)
- `phantom-core/Cargo.toml` (office feature flag)
