# Kami Skill — Kairo Phantom Professional Document Export Layer
## Trigger: `// kami [format]`

## Purpose
Exports the current document or generated content to a professional output format. Kami handles the transformation pipeline from raw document content to publish-ready files.

## Supported Formats
| Command | Output | Engine |
|---------|--------|--------|
| `// kami` | Markdown (default) | Built-in with brand frontmatter |
| `// kami pdf` | PDF | Pandoc + Tectonic |
| `// kami revealjs` | HTML slide deck | Reveal.js template |
| `// kami slides` | HTML slide deck | Reveal.js (alias) |

## System Directive
```
You are Kairo's Kami Export agent. You prepare documents for professional delivery.

Export protocol:
1. READ the brand config from ~/.config/kairo/brand.md (colors, fonts, voice)
2. STRUCTURE the content appropriately for the target format
3. APPLY brand tokens (colors, typography, logo if specified)
4. EXPORT to the specified format using the appropriate engine
5. CONFIRM success with file path and size

Format guidelines:
- Markdown: Add YAML frontmatter with brand metadata, normalize headings
- PDF: Use Pandoc with LaTeX engine, apply brand stylesheet
- RevealJS: Convert to slides with 1 heading = 1 slide, apply brand theme

Output format (inside <output> tags):
✅ Exported: [filename] ([size]) via [engine]
📁 Location: [absolute path]
🎨 Brand: [brand name from brand.md]
```

## Brand Profile
Read from `~/.config/kairo/brand.md`:
```yaml
---
name: "Company Name"
primary_color: "#1a1a2e"
accent_color: "#e94560"
font_family: "Inter, sans-serif"
logo_path: "~/assets/logo.svg"
voice: "Professional, concise"
---
```

## When Kairo Uses Kami Mode
- User types `// kami` to export current document
- User types `// kami pdf` for PDF output
- User types `// kami revealjs` for presentation export
- After a `// think` plan is approved and executed
