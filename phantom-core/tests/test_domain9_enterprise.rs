//! Domain 9 — Enterprise Governance & Compliance Integration Tests
//!
//! Gate Conditions (all must pass):
//!   GC1: SsoGate blocks unauthenticated requests when SSO enabled
//!   GC2: SpiffeAgent sign/verify roundtrip is deterministic
//!   GC3: AuditLogger chain integrity maintained across 50 events
//!   GC4: ComplianceScanner blocks PAN + SSN, warns on IBAN
//!   GC5: RbacEngine: deny wins over allow; permissive allows all
//!   GC6: Full 12-step pipeline: SSO→RBAC→Compliance→SPIFFE-sign→Audit

use phantom_core::enterprise::{
    sso::{SsoConfig, SsoGate, SsoGateResult, SsoSession},
    spiffe_identity::{SpiffeAgent, SpiffeConfig},
    audit::{EnterpriseAuditEvent, EnterpriseAuditLogger, ChainVerificationResult, sha256_hex},
    compliance::{EnterpriseComplianceScanner, ComplianceDecision},
    rbac::{AccessDecision, RbacEngine, RbacPolicy},
};
use tempfile::tempdir;

// ── Helper Factories ──────────────────────────────────────────────────────────

fn make_spiffe_config() -> SpiffeConfig {
    SpiffeConfig {
        enabled: true,
        trust_domain: "test.kairo-phantom.io".to_string(),
        agent_name: "integration-test-agent".to_string(),
        agent_socket_path: None,
    }
}

fn make_logger(tmp_dir: &std::path::Path) -> EnterpriseAuditLogger {
    EnterpriseAuditLogger::new(tmp_dir.join("test_audit.db")).unwrap()
}

fn sample_event(spiffe_id: &str) -> EnterpriseAuditEvent {
    EnterpriseAuditEvent::new(
        "test-user-123",
        "lawyer@bigfirm.com",
        spiffe_id,
        "legal-review-specialist",
        sha256_hex(b"original contract text"),
        sha256_hex(b"edited contract text"),
        "Draft a professional summary of this M&A agreement for the client.",
        "This M&A agreement summary provides...",
        "Adeu",
        "success",
        "",
    )
}

// ── GC1: SSO Gate Blocks Unauthenticated Requests ────────────────────────────

#[test]
fn gc1_sso_gate_blocks_no_token_when_enabled() {
    let config = SsoConfig {
        enabled: true,
        jwt_secret: "test-secret-key".to_string(),
        ..Default::default()
    };
    let gate = SsoGate::new(config);
    let result = gate.check(None);
    assert!(
        matches!(result, SsoGateResult::Blocked(_)),
        "Gate must block when SSO is enabled and no token is provided"
    );
}

#[test]
fn gc1_sso_gate_passes_through_when_disabled() {
    let config = SsoConfig { enabled: false, ..Default::default() };
    let gate = SsoGate::new(config);
    assert_eq!(gate.check(None), SsoGateResult::Disabled);
    assert_eq!(gate.check(Some("any_token")), SsoGateResult::Disabled);
}

#[test]
fn gc1_sso_anonymous_session_has_admin_role() {
    let s = SsoSession::anonymous();
    assert!(!s.is_expired());
    assert!(s.has_role("admin"));
    assert!(s.has_role("ADMIN")); // case-insensitive
    assert!(!s.has_role("intern"));
}

#[test]
fn gc1_sso_expired_session_detected() {
    let s = SsoSession {
        user_id: "u".to_string(),
        email: "u@u.com".to_string(),
        roles: vec![],
        jwt_exp: 1_000_000, // long past epoch
        access_token: String::new(),
        authenticated_at: 0,
    };
    assert!(s.is_expired());
}

// ── GC2: SPIFFE Sign/Verify Roundtrip ────────────────────────────────────────

#[test]
fn gc2_spiffe_sign_verify_roundtrip() {
    let tmp = tempdir().unwrap();
    let config = make_spiffe_config();
    let agent = SpiffeAgent::generate(&config, &tmp.path().join("id.json")).unwrap();
    let data = b"contract_hash_abc123def456";
    let signature = agent.sign_payload(data);
    assert!(
        agent.verify_signature(data, &signature),
        "Signature verification must succeed for original data"
    );
}

#[test]
fn gc2_spiffe_verify_fails_on_tampered_data() {
    let tmp = tempdir().unwrap();
    let agent = SpiffeAgent::generate(&make_spiffe_config(), &tmp.path().join("id.json")).unwrap();
    let sig = agent.sign_payload(b"original");
    assert!(
        !agent.verify_signature(b"tampered", &sig),
        "Verification must fail when data is tampered"
    );
}

#[test]
fn gc2_spiffe_uri_format_correct() {
    let tmp = tempdir().unwrap();
    let agent = SpiffeAgent::generate(&make_spiffe_config(), &tmp.path().join("id.json")).unwrap();
    assert_eq!(
        agent.identity.spiffe_id,
        "spiffe://test.kairo-phantom.io/agent/integration-test-agent"
    );
}

#[test]
fn gc2_spiffe_fingerprint_is_64_hex() {
    let tmp = tempdir().unwrap();
    let agent = SpiffeAgent::generate(&make_spiffe_config(), &tmp.path().join("id.json")).unwrap();
    assert_eq!(agent.identity.cert_fingerprint.len(), 64);
    assert!(
        agent.identity.cert_fingerprint.chars().all(|c| c.is_ascii_hexdigit()),
        "Fingerprint must be lowercase hex"
    );
}

// ── GC3: Audit Chain Integrity ────────────────────────────────────────────────

#[test]
fn gc3_audit_chain_intact_after_50_events() {
    let tmp = tempdir().unwrap();
    let logger = make_logger(tmp.path());
    let spiffe_id = "spiffe://test.kairo-phantom.io/agent/test";

    for i in 0..50 {
        let mut e = sample_event(spiffe_id);
        e.prompt = format!("Prompt number {}", i);
        logger.log_event(e).unwrap();
    }

    assert_eq!(logger.count(), 50);
    let result = logger.verify_chain().unwrap();
    assert!(
        matches!(result, ChainVerificationResult::Intact { record_count: 50 }),
        "Chain must be intact after 50 events, got: {:?}", result
    );
}

#[test]
fn gc3_audit_chain_broken_on_tampering() {
    let tmp = tempdir().unwrap();
    let logger = make_logger(tmp.path());
    let spiffe_id = "spiffe://test.kairo-phantom.io/agent/test";

    // Log 5 events
    for _ in 0..5 {
        logger.log_event(sample_event(spiffe_id)).unwrap();
    }

    // Tamper with record 3's record_hash
    let conn = rusqlite::Connection::open(tmp.path().join("test_audit.db")).unwrap();
    conn.execute(
        "UPDATE enterprise_audit SET record_hash = 'deadbeef0000000000000000000000000000000000000000000000000000DEAD' WHERE id = 3",
        [],
    ).unwrap();
    drop(conn);

    let result = logger.verify_chain().unwrap();
    assert!(
        matches!(result, ChainVerificationResult::Broken { .. }),
        "Chain must be broken when a record_hash is tampered"
    );
}

#[test]
fn gc3_audit_export_json_has_all_required_fields() {
    let tmp = tempdir().unwrap();
    let logger = make_logger(tmp.path());
    logger.log_event(sample_event("spiffe://x/a")).unwrap();

    let lines = logger.export_json(None, None).unwrap();
    assert_eq!(lines.len(), 1);
    let v: serde_json::Value = serde_json::from_str(&lines[0]).unwrap();

    for field in &["user_id", "user_email", "spiffe_id", "agent_name",
                    "doc_hash_before", "doc_hash_after", "outcome",
                    "prev_hash", "record_hash"] {
        assert!(v.get(field).is_some(), "Missing required field: {}", field);
    }
}

#[test]
fn gc3_audit_seal_writes_hmac_record() {
    let tmp = tempdir().unwrap();
    let logger = make_logger(tmp.path());
    logger.log_event(sample_event("spiffe://x/a")).unwrap();
    logger.seal_hourly(b"test-hmac-key-32-bytes-exactly!!").unwrap();

    let conn = rusqlite::Connection::open(tmp.path().join("test_audit.db")).unwrap();
    let count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM audit_chain_seals", [], |r| r.get(0)
    ).unwrap();
    assert_eq!(count, 1, "Seal must create exactly one seal record");
}

// ── GC4: Compliance Scanner ───────────────────────────────────────────────────

#[test]
fn gc4_ssn_with_dashes_blocked() {
    let prompt = "Patient John Doe SSN 123-45-6789 requires urgent care.";
    let decision = EnterpriseComplianceScanner::scan_with_decision(prompt);
    assert!(decision.is_blocked(), "SSN must trigger BLOCK decision");
    assert!(decision.violations().iter().any(|v| v.contains("HIPAA")));
}

#[test]
fn gc4_visa_pan_blocked() {
    let text = "Please charge 4532015112830366 for the service.";
    let decision = EnterpriseComplianceScanner::scan_with_decision(text);
    assert!(decision.is_blocked(), "Visa PAN must trigger BLOCK decision");
}

#[test]
fn gc4_generic_card_with_spaces_blocked() {
    let text = "Card number: 1234 5678 9012 3456 — process immediately.";
    let decision = EnterpriseComplianceScanner::scan_with_decision(text);
    assert!(decision.is_blocked(), "Generic card pattern must be blocked");
}

#[test]
fn gc4_cvv_blocked() {
    let text = "Security code CVV: 123 for card 4532015112830366";
    let v = EnterpriseComplianceScanner::detect_violations(text);
    assert!(v.iter().any(|x| x.pattern_id == "PCI-CVV-001"), "CVV must be detected");
}

#[test]
fn gc4_iban_warns_not_blocks() {
    let text = "Transfer funds to GB82WEST12345698765432 by Friday.";
    let decision = EnterpriseComplianceScanner::scan_with_decision(text);
    assert!(
        matches!(decision, ComplianceDecision::WarnWithOverride(_)),
        "IBAN alone must produce WarnWithOverride, not Block"
    );
}

#[test]
fn gc4_clean_text_allowed() {
    let text = "Please draft a professional summary of the Q3 earnings report for the board.";
    let decision = EnterpriseComplianceScanner::scan_with_decision(text);
    assert_eq!(decision, ComplianceDecision::Allow, "Clean text must be Allowed");
}

#[test]
fn gc4_ssn_redacted() {
    let text = "ID: 123-45-6789 in this document";
    let redacted = EnterpriseComplianceScanner::redact(text);
    assert!(!redacted.contains("123-45-6789"));
    assert!(redacted.contains("[REDACTED]"));
}

// ── GC5: RBAC Engine ─────────────────────────────────────────────────────────

#[test]
fn gc5_intern_denied_by_denied_roles() {
    let policy = RbacPolicy {
        allowed_roles: vec!["legal".into(), "partner".into()],
        denied_roles: vec!["intern".into()],
        ..Default::default()
    };
    assert!(matches!(
        RbacEngine::check_access(&policy, &["intern".to_string()]),
        AccessDecision::Denied(_)
    ));
}

#[test]
fn gc5_partner_allowed() {
    let policy = RbacPolicy {
        allowed_roles: vec!["legal".into(), "partner".into()],
        denied_roles: vec!["intern".into()],
        ..Default::default()
    };
    assert_eq!(
        RbacEngine::check_access(&policy, &["partner".to_string()]),
        AccessDecision::Allowed
    );
}

#[test]
fn gc5_deny_wins_over_allowed_role() {
    let policy = RbacPolicy {
        allowed_roles: vec!["legal".into()],
        denied_roles: vec!["intern".into()],
        ..Default::default()
    };
    // User has both allowed (legal) and denied (intern) — deny wins
    assert!(matches!(
        RbacEngine::check_access(&policy, &["legal".to_string(), "intern".to_string()]),
        AccessDecision::Denied(_)
    ));
}

#[test]
fn gc5_permissive_allows_all_roles() {
    let policy = RbacPolicy::permissive();
    assert_eq!(RbacEngine::check_access(&policy, &["intern".to_string()]), AccessDecision::Allowed);
    assert_eq!(RbacEngine::check_access(&policy, &[]), AccessDecision::Allowed);
    assert_eq!(RbacEngine::check_access(&policy, &["anyone".to_string()]), AccessDecision::Allowed);
}

#[test]
fn gc5_require_approval_returns_approval_decision() {
    let policy = RbacPolicy {
        require_approval: true,
        ..Default::default()
    };
    assert!(matches!(
        RbacEngine::check_access(&policy, &["admin".to_string()]),
        AccessDecision::RequiresApproval(_)
    ));
}

// ── GC6: Full 12-Step Pipeline Simulation ────────────────────────────────────

#[test]
fn gc6_full_pipeline_compliant_request_succeeds() {
    let tmp = tempdir().unwrap();

    // Step 1: SSO disabled → anonymous session
    let sso_config = SsoConfig { enabled: false, ..Default::default() };
    let gate = SsoGate::new(sso_config);
    let sso_result = gate.check(None);
    assert_eq!(sso_result, SsoGateResult::Disabled);
    let session = SsoSession::anonymous();

    // Step 2: RBAC check — permissive policy
    let rbac_policy = RbacPolicy::permissive();
    let rbac_decision = RbacEngine::check_access(&rbac_policy, &session.roles);
    assert_eq!(rbac_decision, AccessDecision::Allowed);

    // Step 3: Compliance scan on clean prompt
    let prompt = "Draft a professional cover letter for the merger agreement.";
    let scan_result = EnterpriseComplianceScanner::scan_with_decision(prompt);
    assert_eq!(scan_result, ComplianceDecision::Allow);

    // Steps 4-8: Simulated (prompt shield, dispatch, LLM, sentinel, QA gate)
    let doc_before = sha256_hex(b"original document content");
    let doc_after = sha256_hex(b"edited document content with cover letter");
    let ai_output = "This professional cover letter provides a comprehensive overview...";

    // Step 9: Compliance scan on output
    let output_scan = EnterpriseComplianceScanner::scan_with_decision(ai_output);
    assert_eq!(output_scan, ComplianceDecision::Allow);

    // Step 10: SPIFFE sign
    let spiffe_config = make_spiffe_config();
    let agent = SpiffeAgent::generate(&spiffe_config, &tmp.path().join("id.json")).unwrap();
    let payload = format!("{}:{}", doc_before, doc_after);
    let signature = agent.sign_payload(payload.as_bytes());
    assert!(agent.verify_signature(payload.as_bytes(), &signature));

    // Steps 11: Ghost-inject (simulated)

    // Step 12: Audit log
    let logger = make_logger(tmp.path());
    let event = EnterpriseAuditEvent::new(
        &session.user_id,
        &session.email,
        &agent.identity.spiffe_id,
        "legal-review-specialist",
        &doc_before,
        &doc_after,
        prompt,
        ai_output,
        "Adeu",
        "success",
        "",
    );
    let audit_id = logger.log_event(event).unwrap();
    assert!(audit_id > 0);

    // Verify chain integrity
    let chain_result = logger.verify_chain().unwrap();
    assert!(
        matches!(chain_result, ChainVerificationResult::Intact { record_count: 1 }),
        "Full pipeline audit chain must be intact after one compliant ghost-write"
    );
}

#[test]
fn gc6_pipeline_blocked_when_ssn_in_prompt() {
    // Demonstrates that step 3 (compliance scan) blocks before LLM ever runs
    let prompt = "Write a letter for patient SSN 987-65-4321 regarding their treatment.";
    let decision = EnterpriseComplianceScanner::scan_with_decision(prompt);
    assert!(
        decision.is_blocked(),
        "Pipeline step 3 must block SSN-containing prompts before LLM"
    );
    assert!(
        decision.violations().iter().any(|v| v.contains("HIPAA")),
        "Block violation must cite HIPAA regulation"
    );
}

#[test]
fn gc6_rbac_blocks_unauthorized_role_before_dispatch() {
    let policy = RbacPolicy {
        allowed_roles: vec!["partner".into(), "associate".into()],
        denied_roles: vec!["intern".into()],
        ..Default::default()
    };
    // Intern user attempts to invoke the legal-review agent
    let decision = RbacEngine::check_access(&policy, &["intern".to_string()]);
    assert!(
        matches!(decision, AccessDecision::Denied(_)),
        "RBAC gate must deny intern role before agent dispatch"
    );
}
