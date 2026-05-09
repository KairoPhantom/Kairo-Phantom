# Kairo Phantom — Production Overhaul Roadmap
# Version 2.0 — Launch-Ready

## Milestone 1: Production-Grade Engine

### Phase 1: Clipboard-First Injection (CRITICAL — fixes garbled text)
- Replace Shift+Left character selection with Win32 clipboard injection
- Word/Notepad/VS Code all accept Ctrl+A + Ctrl+V
- Remove slow Shift+Left loop (causes garbled chars at high speed)

### Phase 2: Smart Prompt Extraction (Context Engine)
- Extract ONLY the user's last line/paragraph (not entire document)
- Use cursor position via UIA CaretRange to find exact prompt
- Erase ONLY the prompt, not surrounding text

### Phase 3: Application Context Detection (App-Aware AI)
- Full process fingerprinting: WinWord.exe → Word, Code.exe → VSCode, powershell.exe → Terminal
- Inject doc-type as structured metadata into AI prompt
- AI adapts: code for terminals, prose for Word, bullets for PPT

### Phase 4: Production-Grade Streaming (Like Claude.ai)
- Clipboard-blast first paragraph, stream remainder via keystrokes
- Handle SSE reconnection and error recovery gracefully
- Show per-token latency metrics in kairo.log

Status: PLANNED
