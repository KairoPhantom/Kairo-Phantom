//! OWASP Agentic Top 10 Compliance Matrix — P2-C1
//! Maps every Kairo Phantom governance feature to the OWASP Agentic AI Top 10.
//! This module generates the compliance matrix as a formatted document.

/// One row in the OWASP compliance matrix
#[derive(Debug, Clone)]
pub struct OwaspControl {
    pub owasp_id: &'static str,
    pub owasp_name: &'static str,
    pub kairo_control: &'static str,
    pub kairo_module: &'static str,
    pub status: ComplianceStatus,
    pub evidence: &'static str,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ComplianceStatus {
    FullyCovered,
    PartiallyCovered,
    NotApplicable,
}

impl ComplianceStatus {
    pub fn label(&self) -> &'static str {
        match self {
            Self::FullyCovered => "✅ COVERED",
            Self::PartiallyCovered => "⚠️  PARTIAL",
            Self::NotApplicable => "N/A",
        }
    }
}

/// Returns the full OWASP Agentic Top 10 compliance matrix for Kairo Phantom.
pub fn kairo_owasp_matrix() -> Vec<OwaspControl> {
    vec![
        OwaspControl {
            owasp_id: "LLM01",
            owasp_name: "Prompt Injection",
            kairo_control: "Sentinel + PromptGuard (27-pattern injection detection)",
            kairo_module: "sentinel.rs + guardrails.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "27 regex patterns detect direct/indirect injection; NFC normalization defeats encoding attacks; hash-signed system prompt detects tampering",
        },
        OwaspControl {
            owasp_id: "LLM02",
            owasp_name: "Insecure Output Handling",
            kairo_control: "ResponseValidator + QualityGate (7-mode output verification)",
            kairo_module: "response_validator.rs + quality_gate.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "AI output is validated before injection; PII Guard strips sensitive data; Sentinel scans for leaked system prompt content",
        },
        OwaspControl {
            owasp_id: "LLM03",
            owasp_name: "Training Data Poisoning",
            kairo_control: "MemMachine ground-truth flags + Alaya forgetting curve",
            kairo_module: "memory/mem_machine.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "User-verified episodes marked is_ground_truth=true; low-confidence memories decay; PRIME meta-ops prevent conflicting preference accumulation",
        },
        OwaspControl {
            owasp_id: "LLM04",
            owasp_name: "Model Denial of Service",
            kairo_control: "Token budget cap + CancellationToken + RetryPolicy with backoff",
            kairo_module: "governance/mod.rs + retry_policy.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "Governance gate enforces max_tokens per request; Esc key cancels via CancellationToken; exponential backoff prevents provider hammering",
        },
        OwaspControl {
            owasp_id: "LLM05",
            owasp_name: "Supply Chain Vulnerabilities",
            kairo_control: "WASM Sandbox + Ed25519 Plugin Signature Verification",
            kairo_module: "wasm_sandbox.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "All plugins run in isolated Wasmtime WASM sandbox; Ed25519 signatures verified before load; unsigned plugins rejected; memory limits enforced",
        },
        OwaspControl {
            owasp_id: "LLM06",
            owasp_name: "Sensitive Information Disclosure",
            kairo_control: "PII Guard (email/phone/SSN/card/API key redaction)",
            kairo_module: "pii_guard.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "5-pattern PII redaction runs on all inputs before LLM; output scanned for leaked identifiers; 100% offline mode means zero network exposure",
        },
        OwaspControl {
            owasp_id: "LLM07",
            owasp_name: "Insecure Plugin Design",
            kairo_control: "WASM sandbox isolation + tool allow-list enforcement",
            kairo_module: "wasm_sandbox.rs + governance/mod.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "Plugins cannot access filesystem/network outside sandbox; tool calls validated against governance allow-list; deterministic tool gate blocks unauthorized actions",
        },
        OwaspControl {
            owasp_id: "LLM08",
            owasp_name: "Excessive Agency",
            kairo_control: "Governance Gate (deterministic tool allow-list + forbidden path blocker)",
            kairo_module: "governance/mod.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "Governance gate validates every tool call against an explicit allow-list; forbidden paths (system files, network) blocked deterministically before LLM runs",
        },
        OwaspControl {
            owasp_id: "LLM09",
            owasp_name: "Overreliance",
            kairo_control: "PAHF Confidence Engine + Context7 ground-truth verification",
            kairo_module: "confidence.rs + context7.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "Confidence <0.4 triggers clarification request instead of output; Context7 verifies factual claims against live docs; ConfidenceBand exposed in output",
        },
        OwaspControl {
            owasp_id: "LLM10",
            owasp_name: "Model Theft",
            kairo_control: "SPIFFE-like Agent Identity + Ed25519 session signing",
            kairo_module: "identity.rs",
            status: ComplianceStatus::FullyCovered,
            evidence: "Each agent session has cryptographically bound identity; audit logs capture every action; local-only inference means model weights never leave the machine",
        },
    ]
}

/// Generate the compliance matrix as a markdown document.
pub fn generate_markdown_report() -> String {
    let matrix = kairo_owasp_matrix();
    let covered = matrix.iter().filter(|c| c.status == ComplianceStatus::FullyCovered).count();

    let mut md = String::new();
    md.push_str("# Kairo Phantom — OWASP Agentic AI Top 10 Compliance Matrix\n\n");
    md.push_str(&format!(
        "> **Compliance Score: {}/{} controls fully covered**  \n",
        covered, matrix.len()
    ));
    md.push_str("> Kairo Phantom is the only document AI co-pilot with a deterministic governance layer  \n");
    md.push_str("> mapping directly to every OWASP Agentic AI security control.\n\n");
    md.push_str("---\n\n");
    md.push_str("| OWASP ID | Threat | Kairo Control | Module | Status |\n");
    md.push_str("|----------|--------|---------------|--------|--------|\n");

    for ctrl in &matrix {
        md.push_str(&format!(
            "| {} | {} | {} | `{}` | {} |\n",
            ctrl.owasp_id, ctrl.owasp_name, ctrl.kairo_control,
            ctrl.kairo_module, ctrl.status.label()
        ));
    }

    md.push_str("\n---\n\n## Evidence Details\n\n");
    for ctrl in &matrix {
        md.push_str(&format!(
            "### {} — {}\n**Kairo Control:** {}  \n**Module:** `{}`  \n**Evidence:** {}  \n\n",
            ctrl.owasp_id, ctrl.owasp_name,
            ctrl.kairo_control, ctrl.kairo_module, ctrl.evidence
        ));
    }

    md.push_str("---\n\n");
    md.push_str("*Generated by Kairo Phantom. For enterprise compliance inquiries: enterprise@kairo.ai*\n");
    md
}

/// Generate the compliance matrix as plain text for a CISO one-pager.
pub fn generate_ciso_summary() -> String {
    let matrix = kairo_owasp_matrix();
    let covered = matrix.iter().filter(|c| c.status == ComplianceStatus::FullyCovered).count();

    format!(
        "KAIRO PHANTOM — OWASP AGENTIC AI TOP 10 COMPLIANCE SUMMARY\n\
         ============================================================\n\
         Compliance Coverage: {}/{} controls\n\
         Architecture: 100% local inference — zero external API calls\n\
         Audit: Cryptographically signed session logs\n\n\
         CONTROLS:\n\
         LLM01 Prompt Injection    ✅ 27-pattern PromptGuard + Sentinel\n\
         LLM02 Output Handling     ✅ 7-mode QualityGate + PII scan\n\
         LLM03 Data Poisoning      ✅ Ground-truth flags + Alaya decay\n\
         LLM04 DoS                 ✅ Token cap + CancellationToken\n\
         LLM05 Supply Chain        ✅ WASM sandbox + Ed25519 signatures\n\
         LLM06 Info Disclosure     ✅ PII Guard + offline-only mode\n\
         LLM07 Plugin Design       ✅ WASM isolation + tool allow-list\n\
         LLM08 Excessive Agency    ✅ Deterministic governance gate\n\
         LLM09 Overreliance        ✅ PAHF confidence engine + Context7\n\
         LLM10 Model Theft         ✅ SPIFFE identity + Ed25519 signing\n\n\
         For full evidence: kairo-phantom --owasp-report\n",
        covered, matrix.len()
    )
}
