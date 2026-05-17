//! Document-aware prompt builder
//! ================================
//! Builds rich, structured LLM prompts based on parsed document context
//! (from sidecar) and the user's // command. The prompt includes:
//!   - Document structure (headings, active section, surrounding paragraphs)
//!   - Format-specific schema instructions (DocxOperation, ExcelOperation, etc.)
//!   - Operation constraints (no freeform prose, JSON output only)
//!
//! The LLM is forced to output ONLY valid typed operations — never raw prose.

use crate::sidecar_client::{DocFormat, DocxContext, ExcelContext};
use serde_json::Value;

// ─── System prompts per document format ──────────────────────────────────────

const DOCX_SYSTEM: &str = r#"You are Kairo Document Engine. You modify Microsoft Word documents by outputting ONLY valid JSON DocxOperation arrays.

## OUTPUT CONTRACT
You MUST output a JSON array of DocxOperation objects. No preamble. No prose. No markdown. Just valid JSON.

```typescript
type DocxOperation = {
  action: "insert_after_heading" | "insert_paragraph" | "replace_paragraph" | "append" | "insert_table";
  heading_text?: string;   // for insert_after_heading: heading to find
  style: string;           // Word style: "Normal" | "Heading1" | "Heading2" | "ListBullet" | "ListNumber" | "Quote"
  content: string | string[]; // text to insert (string or array of strings)
  index?: number;          // for insert_paragraph/replace_paragraph: paragraph index
  rows?: string[][];       // for insert_table: [[col1, col2], [val1, val2]]
};
```

## RULES
- Use "ListBullet" style for bullet points, never "- text" in Normal style
- Use "Heading1"/"Heading2" for section titles, never bold Normal
- For summaries: use multiple "append" operations with "ListBullet" style
- Preserve existing content — only generate content for the requested action
- NEVER include [MCP:...] or any non-JSON in your output

## EXAMPLE
User: "// write a 3-point executive summary after the Introduction"
Output: [
  {"action":"insert_after_heading","heading_text":"Introduction","style":"Heading2","content":"Executive Summary"},
  {"action":"insert_after_heading","heading_text":"Executive Summary","style":"ListBullet","content":["Point one about the topic","Point two with key insight","Point three with recommendation"]}
]"#;

const XLSX_SYSTEM: &str = r#"You are Kairo Spreadsheet Engine. You write Excel formulas and values by outputting ONLY valid JSON ExcelOperation arrays.

## OUTPUT CONTRACT
You MUST output a JSON array of ExcelOperation objects. No preamble. No prose. No markdown. Just valid JSON.

```typescript
type ExcelOperation = {
  cell: string;     // Cell reference, e.g. "G5"
  formula: string;  // Excel formula starting with "=" (use this for calculations)
  value: string;    // Plain text/number value (use when formula not needed)
};
```

## RULES
- Formulas MUST start with "="
- Reference nearby cells based on the provided grid context
- Never write to cells that already have data unless replacing is explicitly requested
- NEVER include prose or explanations — JSON only

## EXAMPLE
User: "// calculate 5% commission on sales in column C, put result in G5"
Output: [{"cell":"G5","formula":"=C5*0.05","value":""}]"#;

const PPTX_SYSTEM: &str = r#"You are Kairo Presentation Engine. You edit PowerPoint slides by outputting ONLY valid JSON SlideOperation arrays.

## OUTPUT CONTRACT
You MUST output a JSON array of SlideOperation objects. No preamble. No prose. No markdown. Just valid JSON.

```typescript
type SlideOperation = {
  slide_index: number;   // Zero-based slide index
  shape_id?: number;     // Shape ID (from slide inventory)
  bullets: string[];     // Bullet text — MAX 7 WORDS EACH, enforced
};
```

## RULES
- MAXIMUM 7 words per bullet — cut mercilessly, every word must earn its place
- Never touch slides not in the operation list
- Use active voice. Use concrete nouns. Avoid "very", "really", "that is"
- NEVER include prose or explanations — JSON only

## EXAMPLE
User: "// rewrite slide 2 to focus on cost savings, 4 bullets"
Output: [{"slide_index":1,"bullets":["Cut infrastructure costs by 40%","Eliminate redundant toolchain overhead","Automate deployment saves 20 hours","ROI positive within 6 months"]}]"#;

// ─── Context formatters ───────────────────────────────────────────────────────

/// Format DOCX context for LLM prompt
pub fn format_docx_context(ctx: &DocxContext, command: &str) -> String {
    let mut parts = vec![];

    // Heading structure
    if !ctx.headings.is_empty() {
        parts.push("## Document Structure".to_string());
        for h in &ctx.headings {
            let indent = "  ".repeat((h.level as usize).saturating_sub(1));
            parts.push(format!("{}{} H{}: {}", indent, "→", h.level, h.text));
        }
    }

    // First 2000 chars of document text for context
    let text_preview = if ctx.full_text.len() > 2000 {
        format!("{}...[truncated]", &ctx.full_text[..2000])
    } else {
        ctx.full_text.clone()
    };
    parts.push("\n## Document Content (preview)".to_string());
    parts.push(text_preview);

    parts.push(format!("\n## User Command\n{}", command));
    parts.join("\n")
}

/// Format Excel context for LLM prompt
pub fn format_xlsx_context(ctx: &ExcelContext, command: &str) -> String {
    let mut parts = vec![];

    parts.push(format!("## Active Cell: {}", ctx.active_cell));
    parts.push(format!("## Sheet: {}", ctx.sheet_name));

    // Headers
    if !ctx.headers.is_empty() {
        let header_str = ctx.headers
            .iter()
            .map(|(col, name)| format!("{}={}", col, name))
            .collect::<Vec<_>>()
            .join(", ");
        parts.push(format!("## Column Headers: {}", header_str));
    }

    // Grid (show surrounding cells)
    parts.push("## Surrounding Data (10x10 grid)".to_string());
    for row in &ctx.grid {
        let row_str = row
            .iter()
            .map(|c| {
                if c.is_active {
                    format!("[{}:ACTIVE]", c.r#ref)
                } else if !c.formula.is_empty() {
                    format!("{}:{}", c.r#ref, c.formula)
                } else if !c.value.is_empty() {
                    format!("{}:{}", c.r#ref, c.value)
                } else {
                    format!("{}:empty", c.r#ref)
                }
            })
            .collect::<Vec<_>>()
            .join(" | ");
        parts.push(row_str);
    }

    parts.push(format!("\n## User Command\n{}", command));
    parts.join("\n")
}

/// Format generic document context (for PDF, TXT, MD)
pub fn format_generic_context(data: &Value, command: &str) -> String {
    let full_text = data["full_text"].as_str().unwrap_or("");
    let preview = if full_text.len() > 3000 {
        format!("{}...[truncated]", &full_text[..3000])
    } else {
        full_text.to_string()
    };

    format!(
        "## Document Content\n{}\n\n## User Command\n{}",
        preview, command
    )
}

// ─── Prompt builder ───────────────────────────────────────────────────────────

pub struct DocumentPrompt {
    pub system: String,
    pub user: String,
    pub is_structured: bool, // true = LLM must output JSON operations, false = prose
}

impl DocumentPrompt {
    /// Build a structured prompt for DOCX manipulation.
    pub fn for_docx(ctx: &DocxContext, command: &str) -> Self {
        DocumentPrompt {
            system: DOCX_SYSTEM.to_string(),
            user: format_docx_context(ctx, command),
            is_structured: true,
        }
    }

    /// Build a structured prompt for Excel manipulation.
    pub fn for_xlsx(ctx: &ExcelContext, command: &str) -> Self {
        DocumentPrompt {
            system: XLSX_SYSTEM.to_string(),
            user: format_xlsx_context(ctx, command),
            is_structured: true,
        }
    }

    /// Build a structured prompt for PowerPoint manipulation.
    pub fn for_pptx(data: &Value, command: &str) -> Self {
        let slide_info = serde_json::to_string_pretty(data).unwrap_or_default();
        DocumentPrompt {
            system: PPTX_SYSTEM.to_string(),
            user: format!(
                "## Slide Inventory\n{}\n\n## User Command\n{}",
                slide_info, command
            ),
            is_structured: true,
        }
    }

    /// Build a prose prompt for PDF/TXT/MD (fallback — no structured schema).
    pub fn for_prose(data: &Value, command: &str, format: &DocFormat) -> Self {
        let format_hint = match format {
            DocFormat::Pdf => "The document is a PDF. Write a well-structured analysis or summary.",
            DocFormat::Md => "The document is Markdown. Respond in valid Markdown with proper heading hierarchy.",
            DocFormat::Txt => "The document is plain text. Respond in clean plain text, no formatting.",
            _ => "Respond clearly and accurately based on the document context.",
        };

        DocumentPrompt {
            system: format!(
                "You are Kairo Document Engine. {}\n\nRULES:\n- NEVER invent facts not in the document\n- NEVER fabricate statistics or quotes\n- Use hedging language for uncertain specifics",
                format_hint
            ),
            user: format_generic_context(data, command),
            is_structured: false,
        }
    }
}

// ─── Response parser ──────────────────────────────────────────────────────────

/// Parse structured LLM output (JSON operations array) from a potentially
/// messy LLM response that might have some prose around the JSON.
pub fn extract_json_array(response: &str) -> Option<Value> {
    // Clean response: remove [REPLACE] tag if present
    let cleaned = response.trim().trim_start_matches("[REPLACE]").trim();

    // Try parsing directly first
    if let Ok(v) = serde_json::from_str::<Value>(cleaned) {
        if v.is_array() {
            return Some(v);
        }
    }

    // Find JSON array in response (LLM might add prose around it)
    if let Some(start) = cleaned.find('[') {
        let slice = &cleaned[start..];
        // Find matching closing bracket
        let mut depth = 0i32;
        let mut end = 0;
        for (i, ch) in slice.char_indices() {
            match ch {
                '[' | '{' => depth += 1,
                ']' | '}' => {
                    depth -= 1;
                    if depth == 0 {
                        end = i + 1;
                        break;
                    }
                }
                _ => {}
            }
        }
        if end > 0 {
            if let Ok(v) = serde_json::from_str::<Value>(&slice[..end]) {
                if v.is_array() {
                    return Some(v);
                }
            }
        }
    }

    None
}

/// Parse DocxOperation array from LLM response.
pub fn parse_docx_operations(response: &str) -> Vec<crate::sidecar_client::DocxOperation> {
    let Some(arr) = extract_json_array(response) else {
        tracing::warn!("⚠️  Could not parse DocxOperation JSON from LLM response");
        return vec![];
    };
    match serde_json::from_value::<Vec<crate::sidecar_client::DocxOperation>>(arr) {
        Ok(ops) => {
            tracing::info!("✅ Parsed {} DocxOperations", ops.len());
            ops
        }
        Err(e) => {
            tracing::warn!("⚠️  DocxOperation parse error: {}", e);
            vec![]
        }
    }
}

/// Parse ExcelOperation array from LLM response.
pub fn parse_excel_operations(response: &str) -> Vec<crate::sidecar_client::ExcelOperation> {
    let Some(arr) = extract_json_array(response) else {
        return vec![];
    };
    match serde_json::from_value::<Vec<crate::sidecar_client::ExcelOperation>>(arr) {
        Ok(ops) => ops,
        Err(e) => {
            tracing::warn!("⚠️  ExcelOperation parse error: {}", e);
            vec![]
        }
    }
}

/// Parse SlideOperation array from LLM response.
pub fn parse_slide_operations(response: &str) -> Vec<crate::sidecar_client::SlideOperation> {
    let Some(arr) = extract_json_array(response) else {
        return vec![];
    };
    match serde_json::from_value::<Vec<crate::sidecar_client::SlideOperation>>(arr) {
        Ok(ops) => ops,
        Err(e) => {
            tracing::warn!("⚠️  SlideOperation parse error: {}", e);
            vec![]
        }
    }
}
