# 🎬 Kairo Phantom — 90-Second Demo Video Script

## Format
- Duration: 90 seconds (60 FPS screen recording)
- Resolution: 2560×1440 (downscale to 1080p for export)
- Audio: Voiceover (no background music until 0:50)
- Tool: OBS Studio or Loom

---

## Scene 1 — Hook (0:00–0:08)

**Visual:** Black screen. Fade in to a Word doc mid-sentence.
> "Sales grew 42% in Q3, driven by—"

**VO:** "You're in the middle of a document. You need AI. But switching to ChatGPT means losing your flow."

**Action:** User opens browser, pastes context, waits... (show the friction)

---

## Scene 2 — Reveal Kairo (0:08–0:18)

**Visual:** Back to Word doc. User presses **Alt+M**. Small prompt bar slides in from bottom.

**VO:** "Kairo Phantom lives inside your apps. Press Alt+M, type your request."

**Action:** User types: `finish this sentence with Q3 product highlights`

**Visual:** Ghost text streams in, word by word, into the document itself.

**VO:** "It reads your document. It types the answer. Right here."

---

## Scene 3 — Swarm Routing (0:18–0:30)

**Visual:** Split-screen — Word → Excel → PowerPoint
- In Excel: User presses Alt+M, types `VLOOKUP formula for this table`
- Formula appears in the cell
- In PowerPoint: types `suggest slide layout for this content`
- Design suggestions stream into speaker notes

**VO:** "Kairo detects what you're writing — spreadsheet, deck, code — and routes to the right specialist agent automatically."

**Overlay text:** "15 specialized agents: Finance | Legal | Medical | Sales | Design | Code | ..."

---

## Scene 4 — Image Generation (0:30–0:42)

**Visual:** PowerPoint open. User presses Alt+M, types `generate hero image for slide 1: cloud infrastructure diagram`

**Visual:** Small spinner. Image appears on slide automatically.

**VO:** "Need an image? Kairo generates it — using OpenAI, Gemini Imagen 3, or local Stable Diffusion — and injects it directly into your slide."

**Action:** Ctrl+V paste also shown — image is in clipboard too.

---

## Scene 5 — MCP + Claude Code (0:42–0:55)

**Visual:** Terminal. Claude Code opens. User runs:
```
> Use kairo to write the executive summary for my earnings report
```

**Visual:** Claude Code calls `kairo_read_context` → `kairo_ghost_write` → text appears in Word in background.

**VO:** "Or use it from Claude Code, Cursor, or Windsurf. Kairo's MCP server exposes ghost-write, slide generation, and image tools directly in your AI coding assistant."

---

## Scene 6 — Ghost Session UX (0:55–1:10)

**Visual:** Zoom in on the ghost text overlay during streaming.

**VO:** "While it's streaming, press Esc to cancel. Tab to accept. Ctrl+Right to accept word by word."

**Action:** Show Alt+1/Alt+2 toggling between two alternative suggestions, confidence band changing green to yellow.

**VO:** "Two alternatives. Confidence bands. Full keyboard control. You're always in charge."

---

## Scene 7 — Install + Call to Action (1:10–1:30)

**Visual:** Terminal window.

```powershell
irm https://raw.githubusercontent.com/your-org/kairo-phantom/main/install.ps1 | iex
```

Progress bar installs. Binary starts. Hotkey registered.

**VO:** "One command installs everything. Works offline with Ollama. No data leaves your machine unless you want it to."

**Text overlay:**
```
🔑 API Keys needed:
• OpenAI (optional) — for gpt-image-1
• Gemini (optional) — for Imagen 3
• Ollama (FREE) — for 100% local, offline
```

**Final shot:** Kairo logo + GitHub URL
**VO:** "Kairo Phantom. The AI that lives in your apps. Open source. Star us on GitHub."

**Music fade in at 1:10**

---

## Recording Checklist
- [ ] 2K monitor, clean desktop, no notifications
- [ ] Increase font size in Word to 18pt for readability
- [ ] Use dark mode apps where possible
- [ ] Record at 60fps, export at 30fps
- [ ] Compress to <100MB MP4 for Twitter, <2GB for YouTube
- [ ] Thumbnail: split-screen of hotkey + ghost text streaming
