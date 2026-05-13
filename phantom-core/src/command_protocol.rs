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
    /// // health
    Health,
    /// // kami
    Kami,
    /// No delimiter (content only)
    None,
}

impl CommandMode {
    pub fn from_prompt(prompt: &str) -> (Self, String) {
        let p = prompt.trim();
        if p.starts_with("//!") {
            (Self::Urgent, p[3..].trim().to_string())
        } else if p.starts_with("//?") {
            (Self::Query, p[3..].trim().to_string())
        } else if p.starts_with("// think") {
            (Self::Think, p[8..].trim().to_string())
        } else if p.starts_with("// design") {
            (Self::Design, p[9..].trim().to_string())
        } else if p.starts_with("// check") {
            (Self::Check, p[8..].trim().to_string())
        } else if p.starts_with("// write") {
            (Self::Write, p[8..].trim().to_string())
        } else if p.starts_with("// learn") {
            (Self::Learn, p[8..].trim().to_string())
        } else if p.starts_with("// read") {
            (Self::Read, p[7..].trim().to_string())
        } else if p.starts_with("// health") {
            (Self::Health, p[9..].trim().to_string())
        } else if p.starts_with("// kami") {
            (Self::Kami, p[7..].trim().to_string())
        } else if p.starts_with("//") {
            (Self::GhostWrite, p[2..].trim().to_string())
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
            Self::Query => "MODE: QUERY. Answer based on document context.",
            Self::Think => "MODE: THINK. Analyze, challenge, and plan. Output a structured plan.",
            Self::Design => "MODE: DESIGN. Focus on distinctive visual/structural direction.",
            Self::Check => "MODE: CHECK. Review output, verify constraints, find flaws.",
            Self::Write => "MODE: WRITE. Natural prose matching document style.",
            Self::Learn => "MODE: LEARN. 6-phase research: collect, digest, outline, fill, refine, review.",
            Self::Read => "MODE: READ. Extract clean Markdown from provided URL/PDF context.",
            Self::Health => "MODE: HEALTH. System self-audit report.",
            Self::Kami => "MODE: KAMI. Exporting document to professional format.",
            Self::None => "MODE: CONTENT. Observe context and wait for command.",
        }
    }
}
