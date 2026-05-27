//! Domain 9 — Capability 3: Cryptographic Audit Logging
//!
//! Append-only SQLite audit database with SHA-256 chain linking.
//! Each record stores prev_hash = SHA-256 of previous record.
//! Hourly HMAC-SHA256 sealing using a configurable key.
//! Tampering with any record breaks the chain — detected by `kairo audit-verify`.
//!
//! OWASP Agentic Top 10: AT4 — Data Exfiltration (immutable audit trail)

use anyhow::Result;
use chrono::Utc;
use hmac::{Hmac, Mac};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::PathBuf;
use tracing::info;

type HmacSha256 = Hmac<sha2::Sha256>;

// ── Event ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnterpriseAuditEvent {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<i64>,
    pub timestamp: i64,
    /// User ID from SSO JWT (or "local-user" when SSO disabled)
    pub user_id: String,
    /// User email
    pub user_email: String,
    /// SPIFFE ID of the agent that performed this action
    pub spiffe_id: String,
    /// Waza agent name
    pub agent_name: String,
    /// SHA-256 of doc content BEFORE the edit
    pub doc_hash_before: String,
    /// SHA-256 of doc content AFTER the edit
    pub doc_hash_after: String,
    /// User prompt (truncated to 500 chars)
    pub prompt: String,
    /// First 200 chars of AI output
    pub output_preview: String,
    /// Injection backend (Adeu, ExcelMcp, sidecar-docx, etc.)
    pub injection_backend: String,
    /// Was a compliance override applied?
    pub compliance_override: bool,
    /// "success" | "blocked" | "aborted"
    pub outcome: String,
    /// SHA-256 of previous record's canonical JSON (chain link)
    pub prev_hash: String,
    /// SHA-256 of this record's canonical JSON (computed on write)
    pub record_hash: String,
}

impl EnterpriseAuditEvent {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        user_id: impl Into<String>,
        user_email: impl Into<String>,
        spiffe_id: impl Into<String>,
        agent_name: impl Into<String>,
        doc_hash_before: impl Into<String>,
        doc_hash_after: impl Into<String>,
        prompt: impl Into<String>,
        output_preview: impl Into<String>,
        injection_backend: impl Into<String>,
        outcome: impl Into<String>,
        prev_hash: impl Into<String>,
    ) -> Self {
        let p: String = prompt.into();
        let o: String = output_preview.into();
        Self {
            id: None,
            timestamp: Utc::now().timestamp(),
            user_id: user_id.into(),
            user_email: user_email.into(),
            spiffe_id: spiffe_id.into(),
            agent_name: agent_name.into(),
            doc_hash_before: doc_hash_before.into(),
            doc_hash_after: doc_hash_after.into(),
            prompt: if p.len() > 500 { p[..500].to_string() } else { p },
            output_preview: if o.len() > 200 { o[..200].to_string() } else { o },
            injection_backend: injection_backend.into(),
            compliance_override: false,
            outcome: outcome.into(),
            prev_hash: prev_hash.into(),
            record_hash: String::new(),
        }
    }

    /// Canonical JSON for hashing — excludes `id` and `record_hash`.
    pub fn canonical_json(&self) -> String {
        serde_json::json!({
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "spiffe_id": self.spiffe_id,
            "agent_name": self.agent_name,
            "doc_hash_before": self.doc_hash_before,
            "doc_hash_after": self.doc_hash_after,
            "prompt": self.prompt,
            "output_preview": self.output_preview,
            "injection_backend": self.injection_backend,
            "compliance_override": self.compliance_override,
            "outcome": self.outcome,
            "prev_hash": self.prev_hash,
        }).to_string()
    }

    /// SHA-256 of the canonical JSON.
    pub fn compute_hash(&self) -> String {
        sha256_hex(self.canonical_json().as_bytes())
    }
}

/// SHA-256 of arbitrary bytes → lowercase hex string.
pub fn sha256_hex(data: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(data);
    hex::encode(h.finalize())
}

/// SHA-256 of a file's contents. Returns "(unreadable)" on error.
pub fn file_hash(path: &std::path::Path) -> String {
    match std::fs::read(path) {
        Ok(b) => sha256_hex(&b),
        Err(_) => "(unreadable)".to_string(),
    }
}

// ── Chain Verification Result ────────────────────────────────────────────────

#[derive(Debug)]
pub enum ChainVerificationResult {
    Intact { record_count: usize },
    Broken { at_record: i64, expected_hash: String, found_hash: String },
    Empty,
}

impl std::fmt::Display for ChainVerificationResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Intact { record_count } =>
                write!(f, "✅ AUDIT CHAIN INTACT: {} records verified", record_count),
            Self::Broken { at_record, expected_hash, found_hash } =>
                write!(f, "❌ CHAIN BROKEN at record {} — expected {}... but found {}...",
                    at_record,
                    &expected_hash[..16.min(expected_hash.len())],
                    &found_hash[..16.min(found_hash.len())]),
            Self::Empty =>
                write!(f, "ℹ️  Audit log is empty"),
        }
    }
}

// ── Logger ───────────────────────────────────────────────────────────────────

pub struct EnterpriseAuditLogger {
    db_path: PathBuf,
}

impl EnterpriseAuditLogger {
    pub fn new(db_path: PathBuf) -> Result<Self> {
        let l = Self { db_path };
        l.init_db()?;
        Ok(l)
    }

    pub fn from_env() -> Result<Self> {
        let db_path = dirs::home_dir()
            .unwrap_or_default()
            .join(".kairo-phantom")
            .join("kairo_audit.db");
        Self::new(db_path)
    }

    fn open(&self) -> Result<Connection> {
        Ok(Connection::open(&self.db_path)?)
    }

    fn init_db(&self) -> Result<()> {
        let conn = self.open()?;
        conn.execute_batch("
            CREATE TABLE IF NOT EXISTS enterprise_audit (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp           INTEGER NOT NULL,
                user_id             TEXT NOT NULL,
                user_email          TEXT NOT NULL,
                spiffe_id           TEXT NOT NULL,
                agent_name          TEXT NOT NULL,
                doc_hash_before     TEXT NOT NULL,
                doc_hash_after      TEXT NOT NULL,
                prompt              TEXT NOT NULL,
                output_preview      TEXT NOT NULL,
                injection_backend   TEXT NOT NULL,
                compliance_override INTEGER NOT NULL DEFAULT 0,
                outcome             TEXT NOT NULL,
                prev_hash           TEXT NOT NULL,
                record_hash         TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_chain_seals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sealed_at   INTEGER NOT NULL,
                from_id     INTEGER NOT NULL,
                to_id       INTEGER NOT NULL,
                hmac_hex    TEXT NOT NULL
            );
        ")?;
        Ok(())
    }

    fn latest_record_hash(&self) -> Result<String> {
        let conn = self.open()?;
        let hash: Option<String> = conn.query_row(
            "SELECT record_hash FROM enterprise_audit ORDER BY id DESC LIMIT 1",
            [],
            |row| row.get(0),
        ).ok();
        Ok(hash.unwrap_or_else(|| "genesis".to_string()))
    }

    /// Append one audit event, computing chain hash automatically.
    ///
    /// OWASP Agentic Top 10: AT4 — Data Exfiltration (immutable audit trail)
    pub fn log_event(&self, mut event: EnterpriseAuditEvent) -> Result<i64> {
        event.prev_hash = self.latest_record_hash()?;
        event.record_hash = event.compute_hash();

        let conn = self.open()?;
        conn.execute(
            "INSERT INTO enterprise_audit
             (timestamp, user_id, user_email, spiffe_id, agent_name,
              doc_hash_before, doc_hash_after, prompt, output_preview,
              injection_backend, compliance_override, outcome, prev_hash, record_hash)
             VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14)",
            params![
                event.timestamp, event.user_id, event.user_email,
                event.spiffe_id, event.agent_name,
                event.doc_hash_before, event.doc_hash_after,
                event.prompt, event.output_preview, event.injection_backend,
                event.compliance_override as i32, event.outcome,
                event.prev_hash, event.record_hash
            ],
        )?;
        let id = conn.last_insert_rowid();
        info!("📜 Audit #{}: user='{}' agent='{}' outcome='{}' chain={}...",
            id, event.user_id, event.agent_name, event.outcome, &event.record_hash[..8]);
        Ok(id)
    }

    /// Scan every record and verify the SHA-256 chain is unbroken.
    ///
    /// OWASP Agentic Top 10: AT4 — Data Exfiltration (tamper detection)
    pub fn verify_chain(&self) -> Result<ChainVerificationResult> {
        let conn = self.open()?;
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM enterprise_audit", [], |r| r.get(0)
        ).unwrap_or(0);

        if count == 0 {
            return Ok(ChainVerificationResult::Empty);
        }

        let mut stmt = conn.prepare(
            "SELECT id, timestamp, user_id, user_email, spiffe_id, agent_name,
                    doc_hash_before, doc_hash_after, prompt, output_preview,
                    injection_backend, compliance_override, outcome, prev_hash, record_hash
             FROM enterprise_audit ORDER BY id ASC"
        )?;

        let rows: Vec<EnterpriseAuditEvent> = stmt.query_map([], |row| {
            Ok(EnterpriseAuditEvent {
                id: Some(row.get::<_, i64>(0)?),
                timestamp: row.get(1)?,
                user_id: row.get(2)?,
                user_email: row.get(3)?,
                spiffe_id: row.get(4)?,
                agent_name: row.get(5)?,
                doc_hash_before: row.get(6)?,
                doc_hash_after: row.get(7)?,
                prompt: row.get(8)?,
                output_preview: row.get(9)?,
                injection_backend: row.get(10)?,
                compliance_override: row.get::<_, i32>(11)? != 0,
                outcome: row.get(12)?,
                prev_hash: row.get(13)?,
                record_hash: row.get(14)?,
            })
        })?.filter_map(|r| r.ok()).collect();

        let mut prev_hash = "genesis".to_string();

        for event in &rows {
            // Verify prev_hash link
            if event.prev_hash != prev_hash {
                return Ok(ChainVerificationResult::Broken {
                    at_record: event.id.unwrap_or(0),
                    expected_hash: prev_hash,
                    found_hash: event.prev_hash.clone(),
                });
            }
            // Verify record_hash integrity
            let computed = event.compute_hash();
            if computed != event.record_hash {
                return Ok(ChainVerificationResult::Broken {
                    at_record: event.id.unwrap_or(0),
                    expected_hash: computed,
                    found_hash: event.record_hash.clone(),
                });
            }
            prev_hash = event.record_hash.clone();
        }

        Ok(ChainVerificationResult::Intact { record_count: rows.len() })
    }

    /// Seal the chain with HMAC-SHA256. Called hourly via background worker.
    pub fn seal_hourly(&self, hmac_key: &[u8]) -> Result<()> {
        let conn = self.open()?;
        let mut stmt = conn.prepare(
            "SELECT id, record_hash FROM enterprise_audit ORDER BY id ASC"
        )?;
        let rows: Vec<(i64, String)> = stmt.query_map([], |row| {
            Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?))
        })?.filter_map(|r| r.ok()).collect();

        if rows.is_empty() { return Ok(()); }

        let from_id = rows.first().map(|(id, _)| *id).unwrap_or(0);
        let to_id   = rows.last().map(|(id, _)| *id).unwrap_or(0);
        let hashes: String = rows.iter().map(|(_, h)| h.as_str()).collect::<Vec<_>>().join(",");

        let mut mac = HmacSha256::new_from_slice(hmac_key)
            .map_err(|e| anyhow::anyhow!("HMAC key error: {}", e))?;
        mac.update(hashes.as_bytes());
        let hmac_hex = hex::encode(mac.finalize().into_bytes());

        conn.execute(
            "INSERT INTO audit_chain_seals (sealed_at, from_id, to_id, hmac_hex) VALUES (?1,?2,?3,?4)",
            params![Utc::now().timestamp(), from_id, to_id, hmac_hex],
        )?;

        info!("🔒 Audit chain sealed: records {}-{} (HMAC: {}...)", from_id, to_id, &hmac_hex[..8]);
        Ok(())
    }

    /// Export events as JSON lines, optionally filtered by time range.
    pub fn export_json(&self, since: Option<i64>, until: Option<i64>) -> Result<Vec<String>> {
        let conn = self.open()?;
        let since = since.unwrap_or(0);
        let until = until.unwrap_or(i64::MAX);

        let mut stmt = conn.prepare(
            "SELECT id, timestamp, user_id, user_email, spiffe_id, agent_name,
                    doc_hash_before, doc_hash_after, prompt, output_preview,
                    injection_backend, compliance_override, outcome, prev_hash, record_hash
             FROM enterprise_audit
             WHERE timestamp >= ?1 AND timestamp <= ?2
             ORDER BY id ASC"
        )?;

        let rows: Vec<EnterpriseAuditEvent> = stmt.query_map(params![since, until], |row| {
            Ok(EnterpriseAuditEvent {
                id: Some(row.get::<_, i64>(0)?),
                timestamp: row.get(1)?,
                user_id: row.get(2)?,
                user_email: row.get(3)?,
                spiffe_id: row.get(4)?,
                agent_name: row.get(5)?,
                doc_hash_before: row.get(6)?,
                doc_hash_after: row.get(7)?,
                prompt: row.get(8)?,
                output_preview: row.get(9)?,
                injection_backend: row.get(10)?,
                compliance_override: row.get::<_, i32>(11)? != 0,
                outcome: row.get(12)?,
                prev_hash: row.get(13)?,
                record_hash: row.get(14)?,
            })
        })?.filter_map(|r| r.ok()).collect();

        Ok(rows.iter().map(|e| serde_json::to_string(e).unwrap_or_default()).collect())
    }

    pub fn count(&self) -> usize {
        let Ok(conn) = self.open() else { return 0; };
        conn.query_row("SELECT COUNT(*) FROM enterprise_audit", [], |r| r.get::<_, i64>(0))
            .unwrap_or(0) as usize
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn make_logger() -> (EnterpriseAuditLogger, tempfile::TempDir) {
        let tmp = tempdir().unwrap();
        let logger = EnterpriseAuditLogger::new(tmp.path().join("audit.db")).unwrap();
        (logger, tmp)
    }

    fn sample_event() -> EnterpriseAuditEvent {
        EnterpriseAuditEvent::new(
            "user-123", "alice@firm.com",
            "spiffe://kairo.io/agent/word-specialist",
            "word-specialist",
            "abc123", "def456",
            "Write a summary of the contract.", "Here is the summary...",
            "Adeu", "success", "",
        )
    }

    #[test]
    fn test_log_and_count() {
        let (logger, _tmp) = make_logger();
        logger.log_event(sample_event()).unwrap();
        assert_eq!(logger.count(), 1);
    }

    #[test]
    fn test_chain_intact_after_10_events() {
        let (logger, _tmp) = make_logger();
        for _ in 0..10 {
            logger.log_event(sample_event()).unwrap();
        }
        let result = logger.verify_chain().unwrap();
        assert!(matches!(result, ChainVerificationResult::Intact { record_count: 10 }));
    }

    #[test]
    fn test_chain_broken_on_record_hash_tamper() {
        let (logger, tmp) = make_logger();
        logger.log_event(sample_event()).unwrap();
        logger.log_event(sample_event()).unwrap();
        logger.log_event(sample_event()).unwrap();

        // Tamper: overwrite record_hash of record 2
        let conn = Connection::open(tmp.path().join("audit.db")).unwrap();
        conn.execute(
            "UPDATE enterprise_audit SET record_hash = 'TAMPERED0000000000000000000000000000000000000000000000000000000A' WHERE id = 2",
            [],
        ).unwrap();

        let result = logger.verify_chain().unwrap();
        assert!(matches!(result,
            ChainVerificationResult::Broken { at_record: 2, .. } |
            ChainVerificationResult::Broken { at_record: 3, .. }
        ));
    }

    #[test]
    fn test_chain_empty_db() {
        let (logger, _tmp) = make_logger();
        assert!(matches!(logger.verify_chain().unwrap(), ChainVerificationResult::Empty));
    }

    #[test]
    fn test_export_json_has_required_fields() {
        let (logger, _tmp) = make_logger();
        logger.log_event(sample_event()).unwrap();
        let lines = logger.export_json(None, None).unwrap();
        assert_eq!(lines.len(), 1);
        let v: serde_json::Value = serde_json::from_str(&lines[0]).unwrap();
        assert!(v.get("user_id").is_some(), "missing user_id");
        assert!(v.get("spiffe_id").is_some(), "missing spiffe_id");
        assert!(v.get("doc_hash_before").is_some(), "missing doc_hash_before");
        assert!(v.get("prev_hash").is_some(), "missing prev_hash");
        assert!(v.get("record_hash").is_some(), "missing record_hash");
    }

    #[test]
    fn test_seal_creates_seal_record() {
        let (logger, tmp) = make_logger();
        logger.log_event(sample_event()).unwrap();
        logger.seal_hourly(b"enterprise-hmac-key-32bytes!!!!X").unwrap();
        let conn = Connection::open(tmp.path().join("audit.db")).unwrap();
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM audit_chain_seals", [], |r| r.get(0)
        ).unwrap();
        assert_eq!(count, 1);
    }

    #[test]
    fn test_sha256_utility_is_64_hex() {
        let h = sha256_hex(b"hello world");
        assert_eq!(h.len(), 64);
    }

    #[test]
    fn test_prompt_truncated_at_500_chars() {
        let event = EnterpriseAuditEvent::new(
            "u", "e@e.com", "spiffe://x/a", "a",
            "b", "c", &"x".repeat(600), "out", "backend", "success", ""
        );
        assert_eq!(event.prompt.len(), 500);
    }

    #[test]
    fn test_output_preview_truncated_at_200_chars() {
        let event = EnterpriseAuditEvent::new(
            "u", "e@e.com", "spiffe://x/a", "a",
            "b", "c", "prompt", &"y".repeat(300), "backend", "success", ""
        );
        assert_eq!(event.output_preview.len(), 200);
    }
}
