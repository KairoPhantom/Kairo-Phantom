// tests/security/test_audit_chain.rs
//
// Domain 10 — Security Regression Test: Cryptographic Audit Chain
//
// Gate Condition:
//   • Cryptographic chain integrity verified → must pass
//   • Tamper detection → must detect any modification to audit entries
//   • cargo test --test test_audit_chain exits 0

use phantom_core::enterprise::audit::{
    EnterpriseAuditLogger, EnterpriseAuditEvent, ChainVerificationResult,
};
use tempfile::tempdir;

fn make_logger() -> (EnterpriseAuditLogger, tempfile::TempDir) {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("audit_security_test.db");
    let logger = EnterpriseAuditLogger::new(db_path)
        .expect("EnterpriseAuditLogger creation must not fail");
    (logger, dir)
}

fn sample_event(user: &str, action: &str) -> EnterpriseAuditEvent {
    EnterpriseAuditEvent::new(
        user,
        &format!("{}@test.kairo.ai", user),
        &format!("spiffe://kairo.io/agent/{}", action),
        action,
        "before_hash_abc123",
        "after_hash_def456",
        &format!("Write a {} summary", action),
        "AI output preview here...",
        "Adeu",
        "success",
        "", // prev_hash computed by logger
    )
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 1 — Chain Integrity
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn audit_chain_empty_log_is_valid() {
    let (logger, _dir) = make_logger();
    let result = logger.verify_chain().expect("verify_chain must not error on empty log");
    assert!(
        matches!(result, ChainVerificationResult::Empty),
        "Empty audit log must return Empty, got: {:?}", result
    );
}

#[test]
fn audit_chain_single_entry_is_valid() {
    let (logger, _dir) = make_logger();
    logger.log_event(sample_event("agent-1", "write_suggestion"))
        .expect("Logging must not fail");

    let result = logger.verify_chain().expect("verify_chain must succeed");
    assert!(
        matches!(result, ChainVerificationResult::Intact { record_count: 1 }),
        "Single-entry audit chain must be Intact with 1 record, got: {:?}", result
    );
}

#[test]
fn audit_chain_10_entries_is_valid() {
    let (logger, _dir) = make_logger();

    for i in 0..10 {
        logger.log_event(sample_event(&format!("agent-{}", i), "write_suggestion"))
            .expect("Log entry must succeed");
    }

    let result = logger.verify_chain().expect("verify_chain must succeed");
    assert!(
        matches!(result, ChainVerificationResult::Intact { record_count: 10 }),
        "10-entry audit chain must be cryptographically Intact, got: {:?}", result
    );
}

#[test]
fn audit_chain_50_entries_is_valid() {
    let (logger, _dir) = make_logger();

    for i in 0..50 {
        logger.log_event(sample_event(
            &format!("agent-{}", i % 5),
            if i % 2 == 0 { "read_document" } else { "write_suggestion" },
        )).expect("Log entry must succeed");
    }

    let result = logger.verify_chain().expect("verify_chain must succeed after 50 entries");
    assert!(
        matches!(result, ChainVerificationResult::Intact { record_count: 50 }),
        "50-entry chain must be Intact, got: {:?}", result
    );
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 2 — Tamper Detection
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn audit_chain_detects_tampered_record_hash() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("audit_tamper_test.db");

    {
        let logger = EnterpriseAuditLogger::new(db_path.clone()).unwrap();
        for _ in 0..5 {
            logger.log_event(sample_event("agent", "write")).unwrap();
        }
        // Verify chain is intact before tampering
        assert!(matches!(
            logger.verify_chain().unwrap(),
            ChainVerificationResult::Intact { .. }
        ), "Chain must be intact before tampering");
    }

    // TAMPER: Directly modify record 2's record_hash in SQLite
    {
        use rusqlite::Connection;
        let conn = Connection::open(&db_path).unwrap();
        let modified = conn.execute(
            "UPDATE enterprise_audit SET record_hash = 'TAMPERED0000000000000000000000000000000000000000000000000000000A' WHERE id = 2",
            [],
        ).unwrap();
        assert_eq!(modified, 1, "Must have modified exactly 1 row");
    }

    // Verify tamper is detected
    let logger = EnterpriseAuditLogger::new(db_path).unwrap();
    let result = logger.verify_chain().unwrap();
    assert!(
        matches!(result, ChainVerificationResult::Broken { .. }),
        "SECURITY FAILURE: Audit chain did not detect tampering!\nResult: {:?}", result
    );
}

#[test]
fn audit_chain_detects_tampered_payload() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("audit_payload_tamper.db");

    {
        let logger = EnterpriseAuditLogger::new(db_path.clone()).unwrap();
        for _ in 0..3 {
            logger.log_event(sample_event("agent", "write")).unwrap();
        }
    }

    // TAMPER: Modify the prompt of record 2 — this changes canonical_json
    // and breaks the record_hash integrity
    {
        use rusqlite::Connection;
        let conn = Connection::open(&db_path).unwrap();
        conn.execute(
            "UPDATE enterprise_audit SET prompt = 'INJECTED MALICIOUS CONTENT' WHERE id = 2",
            [],
        ).unwrap();
    }

    let logger = EnterpriseAuditLogger::new(db_path).unwrap();
    let result = logger.verify_chain().unwrap();
    // Either the record_hash no longer matches canonical JSON, OR the chain breaks
    // at the next record whose prev_hash references the tampered hash
    assert!(
        matches!(result, ChainVerificationResult::Broken { .. }),
        "Payload tampering must break the audit chain: {:?}", result
    );
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 3 — Chain Continuity
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn audit_chain_prev_hash_links_correctly() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("audit_link_test.db");
    let logger = EnterpriseAuditLogger::new(db_path.clone()).unwrap();

    // Log 3 events
    let id1 = logger.log_event(sample_event("alice", "write")).unwrap();
    let id2 = logger.log_event(sample_event("bob", "read")).unwrap();
    let id3 = logger.log_event(sample_event("carol", "write")).unwrap();
    assert!(id1 < id2 && id2 < id3, "IDs must be sequential");

    // Export and verify prev_hash chaining
    let lines = logger.export_json(None, None).unwrap();
    assert_eq!(lines.len(), 3);

    let e1: serde_json::Value = serde_json::from_str(&lines[0]).unwrap();
    let e2: serde_json::Value = serde_json::from_str(&lines[1]).unwrap();
    let e3: serde_json::Value = serde_json::from_str(&lines[2]).unwrap();

    // Record 1: prev_hash should be "genesis"
    assert_eq!(e1["prev_hash"], "genesis", "First record must link to genesis");
    // Record 2: prev_hash should equal record 1's record_hash
    assert_eq!(e2["prev_hash"], e1["record_hash"], "Record 2 must link to record 1's hash");
    // Record 3: prev_hash should equal record 2's record_hash
    assert_eq!(e3["prev_hash"], e2["record_hash"], "Record 3 must link to record 2's hash");
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 4 — HMAC Seal Integrity
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn audit_hmac_seal_100_entries_verifiable() {
    let (logger, _dir) = make_logger();

    for i in 0..100 {
        logger.log_event(sample_event(
            &format!("agent-{}", i % 10),
            "read_document",
        )).expect("Log entry must succeed");
    }

    // Seal the chain
    logger.seal_hourly(b"kairo-enterprise-hmac-key-32bytX")
        .expect("Sealing must succeed");

    // Chain must still be verifiable after sealing
    let result = logger.verify_chain().expect("verify_chain after seal must succeed");
    assert!(
        matches!(result, ChainVerificationResult::Intact { record_count: 100 }),
        "100-entry sealed chain must be Intact: {:?}", result
    );
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 5 — Audit Log Required Fields
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn audit_log_entry_has_all_required_security_fields() {
    let (logger, _dir) = make_logger();
    logger.log_event(sample_event("agent-1", "write_suggestion")).unwrap();

    let lines = logger.export_json(None, None).unwrap();
    assert!(!lines.is_empty(), "Must retrieve logged entries");

    let entry: serde_json::Value = serde_json::from_str(&lines[0]).unwrap();
    // All these fields are required for forensic audit
    for field in &["user_id", "user_email", "spiffe_id", "agent_name",
                   "doc_hash_before", "doc_hash_after", "prompt",
                   "outcome", "prev_hash", "record_hash", "timestamp"] {
        assert!(entry.get(field).is_some(),
            "Audit entry missing required security field: {}", field);
    }
}

#[test]
fn audit_log_handles_unicode_payload_with_intact_chain() {
    let (logger, _dir) = make_logger();

    // Unicode content including emoji, multi-byte chars, and security-relevant unicode
    let mut event = sample_event("agent-1", "write");
    event.prompt = "Content: 你好世界 🦀 мир αβγ — security test".into();
    event.output_preview = "Formatted: 日本語テスト".into();

    logger.log_event(event).expect("Unicode audit event must be stored");

    let result = logger.verify_chain().expect("verify_chain must succeed");
    assert!(
        matches!(result, ChainVerificationResult::Intact { .. }),
        "Chain must be valid after Unicode entry: {:?}", result
    );
}

#[test]
fn audit_log_large_payload_does_not_break_chain() {
    let (logger, _dir) = make_logger();

    // Create event using new() with 600-char prompt (will be truncated to 500 at construction)
    let large_prompt = "x".repeat(600);
    let event = EnterpriseAuditEvent::new(
        "agent-large", "large@test.kairo.ai",
        "spiffe://kairo.io/agent/large",
        "large-agent",
        "before", "after",
        &large_prompt, // 600 chars → truncated to 500 by new()
        "test output", "Adeu", "success", "",
    );
    logger.log_event(event).expect("Large payload must be stored");
    assert_eq!(logger.count(), 1);

    // Verify prompt was truncated at 500 chars (EnterpriseAuditEvent::new truncates)
    let lines = logger.export_json(None, None).unwrap();
    let entry: serde_json::Value = serde_json::from_str(&lines[0]).unwrap();
    let prompt_len = entry["prompt"].as_str().unwrap().len();
    assert!(prompt_len <= 500, "Prompt must be truncated at 500 chars, got {}", prompt_len);

    // Chain must still be valid
    let result = logger.verify_chain().expect("verify_chain must succeed");
    assert!(matches!(result, ChainVerificationResult::Intact { .. }));
}

#[test]
fn audit_log_count_is_accurate() {
    let (logger, _dir) = make_logger();
    assert_eq!(logger.count(), 0, "Empty logger must have count 0");

    for i in 1..=5 {
        logger.log_event(sample_event("agent", "write")).unwrap();
        assert_eq!(logger.count(), i, "Count must be accurate after {} entries", i);
    }
}
