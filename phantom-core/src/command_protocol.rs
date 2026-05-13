// phantom-core/src/command_protocol.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Hash)]
pub enum CommandMode {
    /// // Direct ghost-write
    GhostWrite,
    /// //! Critical / urgent
    Urgent,
    /// //? Query mode (read-only)
    Query,
    /// // think
    Think,
    /// // design
    Design,
    /// // check
    Check,
    /// // write
    Write,
    /// // learn
    Learn,
    /// // read
    Read,
    /// // explain
    Explain,
    /// // health
    Health,
    /// // kami pdf
    KamiPdf,
    /// // kami revealjs
    KamiRevealJs,
    /// // kami email
    KamiEmail,
    /// // kami linkedin
    KamiLinkedin,
    /// // kami press-release
    KamiPressRelease,
    /// // kami (generic)
    Kami,
    /// No delimiter (content only)
    None,
}

impl CommandMode {
    pub fn from_prompt(prompt: &str) -> (Self, String) {
        let p = prompt.trim();
        if p.starts_with("//!") {
            (Self::Urgent,      p.strip_prefix("//!").unwrap_or("").trim().to_string())
        } else if p.starts_with("//?") {
            (Self::Query,       p.strip_prefix("//?").unwrap_or("").trim().to_string())
        } else if p.starts_with("// think") {
            (Self::Think,       p.strip_prefix("// think").unwrap_or("").trim().to_string())
        } else if p.starts_with("// design") {
            (Self::Design,      p.strip_prefix("// design").unwrap_or("").trim().to_string())
        } else if p.starts_with("// check") {
            (Self::Check,       p.strip_prefix("// check").unwrap_or("").trim().to_string())
        } else if p.starts_with("// write") {
            (Self::Write,       p.strip_prefix("// write").unwrap_or("").trim().to_string())
        } else if p.starts_with("// learn") {
            (Self::Learn,       p.strip_prefix("// learn").unwrap_or("").trim().to_string())
        } else if p.starts_with("// read") {
            (Self::Read,        p.strip_prefix("// read").unwrap_or("").trim().to_string())
        } else if p.starts_with("// explain") {
            (Self::Explain,     p.strip_prefix("// explain").unwrap_or("").trim().to_string())
        } else if p.starts_with("// health") {
            (Self::Health,      p.strip_prefix("// health").unwrap_or("").trim().to_string())
        } else if p.starts_with("// kami pdf") {
            (Self::KamiPdf,     p.strip_prefix("// kami pdf").unwrap_or("").trim().to_string())
        } else if p.starts_with("// kami revealjs") {
            (Self::KamiRevealJs, p.strip_prefix("// kami revealjs").unwrap_or("").trim().to_string())
        } else if p.starts_with("// kami email") {
            (Self::KamiEmail,   p.strip_prefix("// kami email").unwrap_or("").trim().to_string())
        } else if p.starts_with("// kami linkedin") {
            (Self::KamiLinkedin, p.strip_prefix("// kami linkedin").unwrap_or("").trim().to_string())
        } else if p.starts_with("// kami press-release") {
            (Self::KamiPressRelease, p.strip_prefix("// kami press-release").unwrap_or("").trim().to_string())
        } else if p.starts_with("// kami") {
            (Self::Kami,        p.strip_prefix("// kami").unwrap_or("").trim().to_string())
        } else if p.starts_with("//") {
            (Self::GhostWrite,  p.strip_prefix("//").unwrap_or("").trim().to_string())
        } else {
            (Self::None, p.to_string())
        }
    }

    pub fn is_command(&self) -> bool {
        !matches!(self, Self::None)
    }

    pub fn system_hint(&self) -> &'static str {
        match self {
            Self::GhostWrite => "MODE: GHOST-WRITE. Output the replacement text only.",
            Self::Urgent => "MODE: URGENT. Perform the action immediately.",
            Self::Query => "MODE: QUERY. Answer based on document context. Do NOT modify the document.",
            Self::Think => "MODE: THINK. Analyze, challenge, and plan. Output a structured plan.",
            Self::Design => "MODE: DESIGN. Focus on distinctive visual/structural direction.",
            Self::Check => "MODE: CHECK. Review output, verify constraints, find flaws.",
            Self::Write => "MODE: WRITE. Natural prose matching document style.",
            Self::Learn => "MODE: LEARN. 6-phase research: collect, digest, outline, fill, refine, review.",
            Self::Read => "MODE: READ. Extract clean Markdown from provided URL/PDF context.",
            Self::Explain => "MODE: EXPLAIN. Do not generate new text. Instead, annotate and explain the existing context inline. Use blockquotes or bold to clarify the concepts.",
            Self::Health => "MODE: HEALTH. System self-audit report.",
            Self::KamiPdf => "MODE: KAMI. Exporting document to PDF format.",
            Self::KamiRevealJs => "MODE: KAMI. Exporting document to RevealJS presentation.",
            Self::KamiEmail => "MODE: KAMI. Exporting document as a professional email. Format with subject line and body.",
            Self::KamiLinkedin => "MODE: KAMI. Exporting document as a LinkedIn post. Make it engaging, use appropriate hashtags.",
            Self::KamiPressRelease => "MODE: KAMI. Exporting document as a formal press release. Include FOR IMMEDIATE RELEASE, dateline, and boilerplate.",
            Self::Kami => "MODE: KAMI. Exporting document to professional format.",
            Self::None => "MODE: CONTENT. Observe context and wait for command.",
        }
    }
}
