//! Compliance Scanner — P2-A3
//! Loads prohibited phrase rules from ~/.kairo-phantom/compliance/*.toml
//! Scans document text in real-time for HIPAA/GDPR/custom rule violations.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ComplianceRule {
    pub id: String,
    pub description: String,
    pub phrases: Vec<String>,
    pub severity: String, // "error" | "warning" | "info"
    pub regulation: String, // "HIPAA" | "GDPR" | "custom"
    #[serde(default)]
    pub suggestion: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ComplianceRuleFile {
    rules: Vec<ComplianceRule>,
}

#[derive(Debug, Clone)]
pub struct ComplianceViolation {
    pub rule_id: String,
    pub matched_phrase: String,
    pub severity: String,
    pub regulation: String,
    pub description: String,
    pub suggestion: Option<String>,
    pub position: usize,
}

pub struct ComplianceScanner {
    rules: Vec<ComplianceRule>,
}

impl ComplianceScanner {
    /// Load all compliance rules from ~/.kairo-phantom/compliance/*.toml
    pub fn load() -> Self {
        let mut rules = Vec::new();

        // Built-in HIPAA rules
        rules.extend(Self::builtin_hipaa_rules());
        // Built-in GDPR rules
        rules.extend(Self::builtin_gdpr_rules());

        // Load user-defined rules from compliance dir
        let compliance_dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".kairo-phantom")
            .join("compliance");

        if compliance_dir.exists() {
            if let Ok(entries) = std::fs::read_dir(&compliance_dir) {
                for entry in entries.flatten() {
                    if entry.path().extension().and_then(|e| e.to_str()) == Some("toml") {
                        if let Ok(content) = std::fs::read_to_string(entry.path()) {
                            if let Ok(file) = toml::from_str::<ComplianceRuleFile>(&content) {
                                rules.extend(file.rules);
                            }
                        }
                    }
                }
            }
        }

        tracing::info!("📋 ComplianceScanner: {} rules loaded", rules.len());
        Self { rules }
    }

    /// Scan document text for compliance violations. Returns list of violations.
    pub fn scan(&self, text: &str) -> Vec<ComplianceViolation> {
        let text_lower = text.to_lowercase();
        let mut violations = Vec::new();

        for rule in &self.rules {
            for phrase in &rule.phrases {
                let phrase_lower = phrase.to_lowercase();
                if let Some(pos) = text_lower.find(&phrase_lower) {
                    violations.push(ComplianceViolation {
                        rule_id: rule.id.clone(),
                        matched_phrase: phrase.clone(),
                        severity: rule.severity.clone(),
                        regulation: rule.regulation.clone(),
                        description: rule.description.clone(),
                        suggestion: rule.suggestion.clone(),
                        position: pos,
                    });
                }
            }
        }

        violations
    }

    /// Format violations as a concise report string for injection/logging.
    pub fn format_report(&self, violations: &[ComplianceViolation]) -> String {
        if violations.is_empty() {
            return "✅ Compliance scan: No violations found.".to_string();
        }
        let mut report = format!("⚠️  Compliance Scan — {} violation(s) found:\n\n", violations.len());
        for v in violations {
            report.push_str(&format!(
                "  [{} {}] '{}' — {}\n",
                v.severity.to_uppercase(), v.regulation, v.matched_phrase, v.description
            ));
            if let Some(s) = &v.suggestion {
                report.push_str(&format!("    💡 Suggestion: {}\n", s));
            }
        }
        report
    }

    fn builtin_hipaa_rules() -> Vec<ComplianceRule> {
        vec![
            ComplianceRule {
                id: "HIPAA-001".to_string(),
                description: "Social Security Number exposure risk".to_string(),
                phrases: vec!["ssn".to_string(), "social security".to_string()],
                severity: "error".to_string(),
                regulation: "HIPAA".to_string(),
                suggestion: Some("Redact or use de-identified identifiers".to_string()),
            },
            ComplianceRule {
                id: "HIPAA-002".to_string(),
                description: "Medical Record Number (MRN) should not appear in unstructured text".to_string(),
                phrases: vec!["mrn".to_string(), "medical record number".to_string()],
                severity: "warning".to_string(),
                regulation: "HIPAA".to_string(),
                suggestion: Some("Use de-identified patient identifiers".to_string()),
            },
            ComplianceRule {
                id: "HIPAA-003".to_string(),
                description: "Date of birth is a HIPAA identifier".to_string(),
                phrases: vec!["date of birth".to_string(), "dob".to_string(), "birthdate".to_string()],
                severity: "warning".to_string(),
                regulation: "HIPAA".to_string(),
                suggestion: Some("Use age ranges instead of exact dates".to_string()),
            },
        ]
    }

    fn builtin_gdpr_rules() -> Vec<ComplianceRule> {
        vec![
            ComplianceRule {
                id: "GDPR-001".to_string(),
                description: "Personal data processing requires explicit consent documentation".to_string(),
                phrases: vec!["personal data".to_string(), "personal information".to_string()],
                severity: "info".to_string(),
                regulation: "GDPR".to_string(),
                suggestion: Some("Ensure consent basis is documented under GDPR Art. 6".to_string()),
            },
            ComplianceRule {
                id: "GDPR-002".to_string(),
                description: "Right to erasure — ensure deletion mechanisms are documented".to_string(),
                phrases: vec!["right to be forgotten".to_string(), "data deletion".to_string()],
                severity: "info".to_string(),
                regulation: "GDPR".to_string(),
                suggestion: Some("Confirm GDPR Art. 17 erasure mechanism is in place".to_string()),
            },
        ]
    }
}

/// Example compliance rules TOML file template
pub const EXAMPLE_RULES_TOML: &str = r#"# ~/.kairo-phantom/compliance/custom_rules.toml
# Kairo Phantom Compliance Scanner — Custom Rules

[[rules]]
id = "CUSTOM-001"
description = "Confidential project codename must not appear in external docs"
phrases = ["project phoenix", "operation midnight"]
severity = "error"
regulation = "custom"
suggestion = "Use the public product name instead"

[[rules]]
id = "CUSTOM-002"
description = "Internal pricing must not be disclosed"
phrases = ["internal price", "cost price", "margin"]
severity = "warning"
regulation = "custom"
"#;
