//! Domain 9 — Capability 4: Enhanced Compliance Scanner
//!
//! Extends phrase-based ComplianceScanner with regex PAN/SSN/CVV detection.
//! Three-way decision: Block (error), WarnWithOverride (warning), or Allow.
//! Pre-injection scan ensures prohibited content never reaches the document.
//!
//! OWASP Agentic Top 10: AT4 — Data Exfiltration (ComplianceScanner + 100% offline)

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;
use tracing::warn;

// ── Pattern Set ──────────────────────────────────────────────────────────────

struct PatternSet {
    ssn: Regex,
    pan_visa: Regex,
    pan_mc: Regex,
    pan_amex: Regex,
    pan_generic: Regex,
    cvv: Regex,
    iban: Regex,
    uk_nino: Regex,
}

static PATTERNS: OnceLock<PatternSet> = OnceLock::new();

fn patterns() -> &'static PatternSet {
    PATTERNS.get_or_init(|| PatternSet {
        // US SSN with separators: 123-45-6789 or 123 45 6789
        ssn: Regex::new(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b").unwrap(),
        // Visa: 4xxxxxxxxxxxxxx (13 or 16 digits)
        pan_visa: Regex::new(r"\b4[0-9]{12}(?:[0-9]{3})?\b").unwrap(),
        // Mastercard: 5[1-5] or 2[2-7] prefix, 16 digits
        pan_mc: Regex::new(r"\b(?:5[1-5][0-9]{14}|2[2-7][0-9]{14})\b").unwrap(),
        // Amex: 3[47] prefix, 15 digits
        pan_amex: Regex::new(r"\b3[47][0-9]{13}\b").unwrap(),
        // Generic 16-digit card with separators (1234 5678 9012 3456)
        pan_generic: Regex::new(r"\b(?:\d{4}[-\s]){3}\d{4}\b").unwrap(),
        // CVV/CVC near keyword
        cvv: Regex::new(r"(?i)(?:cvv|cvc|cvv2|security\s+code)[:=\s]+\d{3,4}").unwrap(),
        // IBAN (simplified; matches well-formed EU/UK IBANs)
        iban: Regex::new(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}[0-9]{7}(?:[A-Z0-9]{0,16})?\b").unwrap(),
        // UK NI Number (e.g. AB123456C)
        uk_nino: Regex::new(r"\b[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b").unwrap(),
    })
}

// ── Violation ────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegexViolation {
    pub pattern_id: String,
    pub regulation: String,
    pub description: String,
    /// "error" → Block | "warning" → WarnWithOverride
    pub severity: String,
    pub matched_at: usize,
    pub matched_len: usize,
}

// ── Decision ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum ComplianceDecision {
    /// No violations detected — proceed.
    Allow,
    /// Error-level violations — ghost-write BLOCKED until override.
    Block(Vec<String>),
    /// Warning-level violations only — proceed but log override.
    WarnWithOverride(Vec<String>),
}

impl ComplianceDecision {
    pub fn is_blocked(&self) -> bool {
        matches!(self, Self::Block(_))
    }

    pub fn violations(&self) -> &[String] {
        match self {
            Self::Allow => &[],
            Self::Block(v) | Self::WarnWithOverride(v) => v.as_slice(),
        }
    }

    /// User-visible overlay message for the PAHF toast.
    pub fn overlay_message(&self) -> Option<String> {
        match self {
            Self::Allow => None,
            Self::Block(violations) => Some(format!(
                "⛔ Compliance Block: {} violation(s) detected.\n{}\n\nPress Esc to cancel, or //! compliance-override to proceed (audited).",
                violations.len(),
                violations.iter().take(3).cloned().collect::<Vec<_>>().join("\n")
            )),
            Self::WarnWithOverride(violations) => Some(format!(
                "⚠️  Compliance Warning: {} potential violation(s).\n{}\n\nProceeding — override logged to audit.",
                violations.len(),
                violations.iter().take(3).cloned().collect::<Vec<_>>().join("\n")
            )),
        }
    }
}

// ── Scanner ──────────────────────────────────────────────────────────────────

pub struct EnterpriseComplianceScanner;

impl EnterpriseComplianceScanner {
    /// Scan text and return a three-way compliance decision.
    ///
    /// Called twice in the 12-step pipeline:
    ///   Step 3: scan user prompt (before LLM)
    ///   Step 9: scan AI output (before injection)
    ///
    /// OWASP Agentic Top 10: AT4 — Data Exfiltration (pre-injection scan)
    pub fn scan_with_decision(text: &str) -> ComplianceDecision {
        let violations = Self::detect_violations(text);
        if violations.is_empty() {
            return ComplianceDecision::Allow;
        }

        let errors: Vec<String> = violations.iter()
            .filter(|v| v.severity == "error")
            .map(|v| format!("[ERROR {}] {} — {}",
                v.regulation, v.pattern_id, v.description))
            .collect();

        let warnings: Vec<String> = violations.iter()
            .filter(|v| v.severity == "warning")
            .map(|v| format!("[WARNING {}] {}", v.regulation, v.description))
            .collect();

        if !errors.is_empty() {
            warn!("🚫 Compliance: BLOCKED — {} error violation(s)", errors.len());
            ComplianceDecision::Block(errors)
        } else {
            warn!("⚠️  Compliance: WARNING — {} warning violation(s)", warnings.len());
            ComplianceDecision::WarnWithOverride(warnings)
        }
    }

    /// Detect all regex violations in text. Returns all matches.
    pub fn detect_violations(text: &str) -> Vec<RegexViolation> {
        let p = patterns();
        let mut v = Vec::new();

        // HIPAA: US SSN
        for m in p.ssn.find_iter(text) {
            v.push(RegexViolation {
                pattern_id: "HIPAA-SSN-001".into(),
                regulation: "HIPAA".into(),
                description: format!("US Social Security Number detected: {}", &text[m.start()..m.end()]),
                severity: "error".into(),
                matched_at: m.start(),
                matched_len: m.len(),
            });
        }

        // PCI: Visa PAN
        for m in p.pan_visa.find_iter(text) {
            v.push(RegexViolation {
                pattern_id: "PCI-PAN-VISA".into(),
                regulation: "PCI-DSS".into(),
                description: "Visa card number (PAN) detected".into(),
                severity: "error".into(),
                matched_at: m.start(),
                matched_len: m.len(),
            });
        }

        // PCI: Mastercard PAN
        for m in p.pan_mc.find_iter(text) {
            v.push(RegexViolation {
                pattern_id: "PCI-PAN-MC".into(),
                regulation: "PCI-DSS".into(),
                description: "Mastercard number (PAN) detected".into(),
                severity: "error".into(),
                matched_at: m.start(),
                matched_len: m.len(),
            });
        }

        // PCI: Amex PAN
        for m in p.pan_amex.find_iter(text) {
            v.push(RegexViolation {
                pattern_id: "PCI-PAN-AMEX".into(),
                regulation: "PCI-DSS".into(),
                description: "American Express card number (PAN) detected".into(),
                severity: "error".into(),
                matched_at: m.start(),
                matched_len: m.len(),
            });
        }

        // PCI: Generic card with separators
        for m in p.pan_generic.find_iter(text) {
            v.push(RegexViolation {
                pattern_id: "PCI-PAN-GENERIC".into(),
                regulation: "PCI-DSS".into(),
                description: "Generic card number pattern (PAN) detected".into(),
                severity: "error".into(),
                matched_at: m.start(),
                matched_len: m.len(),
            });
        }

        // PCI: CVV
        for m in p.cvv.find_iter(text) {
            v.push(RegexViolation {
                pattern_id: "PCI-CVV-001".into(),
                regulation: "PCI-DSS".into(),
                description: "CVV/CVC security code detected".into(),
                severity: "error".into(),
                matched_at: m.start(),
                matched_len: m.len(),
            });
        }

        // GDPR: IBAN (warning — may be legitimate in financial docs)
        for m in p.iban.find_iter(text) {
            v.push(RegexViolation {
                pattern_id: "GDPR-IBAN-001".into(),
                regulation: "GDPR".into(),
                description: "IBAN bank account number detected (financial personal data)".into(),
                severity: "warning".into(),
                matched_at: m.start(),
                matched_len: m.len(),
            });
        }

        // GDPR: UK NI Number (warning)
        for m in p.uk_nino.find_iter(text) {
            v.push(RegexViolation {
                pattern_id: "GDPR-NINO-001".into(),
                regulation: "GDPR".into(),
                description: "UK National Insurance Number detected (personal data under GDPR)".into(),
                severity: "warning".into(),
                matched_at: m.start(),
                matched_len: m.len(),
            });
        }

        v
    }

    /// Redact all detected PII from text (replaces with [REDACTED]).
    pub fn redact(text: &str) -> String {
        let p = patterns();
        let mut ranges: Vec<(usize, usize)> = Vec::new();
        for m in p.ssn.find_iter(text) { ranges.push((m.start(), m.end())); }
        for m in p.pan_visa.find_iter(text) { ranges.push((m.start(), m.end())); }
        for m in p.pan_mc.find_iter(text) { ranges.push((m.start(), m.end())); }
        for m in p.pan_amex.find_iter(text) { ranges.push((m.start(), m.end())); }
        for m in p.pan_generic.find_iter(text) { ranges.push((m.start(), m.end())); }
        for m in p.cvv.find_iter(text) { ranges.push((m.start(), m.end())); }

        // Sort descending to preserve indices when replacing
        ranges.sort_by(|a, b| b.0.cmp(&a.0));
        ranges.dedup();

        let mut result = text.to_string();
        for (start, end) in ranges {
            result.replace_range(start..end, "[REDACTED]");
        }
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ssn_with_dashes_blocks() {
        let text = "Patient John Doe, SSN 123-45-6789, needs a prescription";
        assert!(EnterpriseComplianceScanner::scan_with_decision(text).is_blocked());
    }

    #[test]
    fn test_clean_text_allowed() {
        let text = "Please write a summary of the Q3 earnings report.";
        assert_eq!(EnterpriseComplianceScanner::scan_with_decision(text), ComplianceDecision::Allow);
    }

    #[test]
    fn test_visa_pan_blocks() {
        let text = "Charge card 4532015112830366 for the purchase";
        assert!(EnterpriseComplianceScanner::scan_with_decision(text).is_blocked());
    }

    #[test]
    fn test_generic_card_with_spaces_blocks() {
        let text = "Card: 1234 5678 9012 3456";
        assert!(EnterpriseComplianceScanner::scan_with_decision(text).is_blocked());
    }

    #[test]
    fn test_cvv_blocks() {
        let text = "CVV: 123";
        let v = EnterpriseComplianceScanner::detect_violations(text);
        assert!(v.iter().any(|x| x.pattern_id == "PCI-CVV-001"));
    }

    #[test]
    fn test_iban_warns_not_blocks() {
        let text = "Transfer to GB82WEST12345698765432 please";
        let d = EnterpriseComplianceScanner::scan_with_decision(text);
        assert!(matches!(d, ComplianceDecision::WarnWithOverride(_)));
    }

    #[test]
    fn test_ssn_redacted() {
        let text = "SSN: 123-45-6789 in letter";
        let r = EnterpriseComplianceScanner::redact(text);
        assert!(!r.contains("123-45-6789"));
        assert!(r.contains("[REDACTED]"));
    }

    #[test]
    fn test_block_overlay_contains_override_instruction() {
        let d = ComplianceDecision::Block(vec!["[ERROR HIPAA] SSN detected".into()]);
        let msg = d.overlay_message().unwrap();
        assert!(msg.contains("compliance-override"));
        assert!(msg.contains("Esc"));
    }

    #[test]
    fn test_allow_no_overlay() {
        assert!(ComplianceDecision::Allow.overlay_message().is_none());
    }

    #[test]
    fn test_plain_9digit_no_ssn_match() {
        // Intentional: no separators = not caught (avoids false positives on zip/phone)
        let text = "Reference number 123456789 for your order";
        let v = EnterpriseComplianceScanner::detect_violations(text);
        assert!(v.iter().all(|x| x.pattern_id != "HIPAA-SSN-001"));
    }
}
