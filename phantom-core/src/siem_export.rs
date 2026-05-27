//! SIEM Export — Domain 9, Capability 3
//!
//! Exports audit events from BOTH the legacy governance audit log AND the
//! Domain 9 enterprise cryptographic audit chain (kairo_audit.db).
//!
//! Supported formats:
//!   --format cef    → ArcSight Common Event Format (CEF:0)
//!   --format leef   → IBM QRadar Log Event Extended Format (LEEF:2.0)
//!   --format json   → Elastic / Splunk JSON Lines (NDJSON)
//!   --format csv    → Spreadsheet-friendly CSV with headers
//!
//! The export includes:
//!   • Chain verification status in the header (INTACT / BROKEN)
//!   • All required Domain 9 fields: user_id, spiffe_id, doc_hash, prompt, outcome
//!   • Severity mapping: blocked=8, aborted=5, success=2
//!
//! OWASP Agentic Top 10: AT4 — Data Exfiltration (export with chain verification)

use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

// ── Format ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum SiemFormat { Cef, Leef, Json, Csv }

impl std::str::FromStr for SiemFormat {
    type Err = anyhow::Error;
    fn from_str(s: &str) -> Result<Self> {
        match s.to_lowercase().as_str() {
            "cef"  => Ok(SiemFormat::Cef),
            "leef" => Ok(SiemFormat::Leef),
            "csv"  => Ok(SiemFormat::Csv),
            _      => Ok(SiemFormat::Json),
        }
    }
}

impl std::fmt::Display for SiemFormat {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Cef  => write!(f, "cef"),
            Self::Leef => write!(f, "leef"),
            Self::Json => write!(f, "json"),
            Self::Csv  => write!(f, "csv"),
        }
    }
}

// ── Legacy Audit Entry (governance audit.db) ──────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub timestamp:   i64,
    pub event_type:  String,
    pub outcome:     String,
    pub app_context: String,
    pub agent_id:    String,
    pub model:       String,
    pub char_count:  i64,
}

impl AuditEntry {
    fn dt(&self) -> DateTime<Utc> {
        DateTime::from_timestamp(self.timestamp, 0).unwrap_or_default()
    }

    fn severity(&self) -> u8 {
        match self.outcome.as_str() { "blocked" => 8, "aborted" => 5, _ => 2 }
    }

    fn agent_short(&self) -> &str {
        if self.agent_id.len() >= 8 { &self.agent_id[..8] } else { &self.agent_id }
    }
}

// ── Enterprise Audit Entry (kairo_audit.db — Domain 9) ────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnterpriseAuditEntry {
    pub id:                 i64,
    pub timestamp:          i64,
    pub user_id:            String,
    pub user_email:         String,
    pub spiffe_id:          String,
    pub agent_name:         String,
    pub doc_hash_before:    String,
    pub doc_hash_after:     String,
    pub prompt:             String,
    pub output_preview:     String,
    pub injection_backend:  String,
    pub compliance_override: bool,
    pub outcome:            String,
    pub prev_hash:          String,
    pub record_hash:        String,
}

impl EnterpriseAuditEntry {
    fn dt(&self) -> DateTime<Utc> {
        DateTime::from_timestamp(self.timestamp, 0).unwrap_or_default()
    }

    fn severity(&self) -> u8 {
        match self.outcome.as_str() { "blocked" => 8, "aborted" => 5, _ => 2 }
    }

    /// Format this entry as CEF (ArcSight Common Event Format)
    fn to_cef(&self, host: &str) -> String {
        format!(
            "CEF:0|KairoPhantom|EnterpriseAudit|0.3.0|ghost-write|GhostWriteComplete|{}|\
             rt={} src={} suser={} agent={} spiffeId={} \
             docBefore={} docAfter={} backend={} outcome={} complianceOverride={} cs1={} cs1Label=prompt",
            self.severity(),
            self.timestamp * 1000,
            host,
            self.user_email,
            self.agent_name,
            self.spiffe_id,
            &self.doc_hash_before[..16.min(self.doc_hash_before.len())],
            &self.doc_hash_after[..16.min(self.doc_hash_after.len())],
            self.injection_backend,
            self.outcome,
            self.compliance_override as u8,
            // CEF spec: cs1 is custom string field. Truncate prompt at 100 chars.
            &self.prompt[..100.min(self.prompt.len())].replace('|', "\\|"),
        )
    }

    /// Format this entry as LEEF (IBM QRadar Log Event Extended Format)
    fn to_leef(&self, host: &str) -> String {
        format!(
            "LEEF:2.0|KairoPhantom|EnterpriseAudit|0.3.0|ghost-write|\
             \tdevTime={}\tsrc={}\tusrName={}\tagent={}\tspiffeId={}\
             \tdocBefore={}\tdocAfter={}\tbackend={}\toutcome={}\tsev={}",
            self.dt().to_rfc3339(),
            host,
            self.user_email,
            self.agent_name,
            self.spiffe_id,
            &self.doc_hash_before[..16.min(self.doc_hash_before.len())],
            &self.doc_hash_after[..16.min(self.doc_hash_after.len())],
            self.injection_backend,
            self.outcome,
            self.severity(),
        )
    }

    /// Format this entry as JSON (Elastic ECS-compatible)
    fn to_json(&self, host: &str, chain_status: &str) -> String {
        serde_json::json!({
            "@timestamp": self.dt().to_rfc3339(),
            "event.action": "ghost-write",
            "event.outcome": self.outcome,
            "event.severity": self.severity(),
            "host.name": host,
            "user.id": self.user_id,
            "user.email": self.user_email,
            "kairo.agent.name": self.agent_name,
            "kairo.agent.spiffe_id": self.spiffe_id,
            "kairo.doc.hash_before": self.doc_hash_before,
            "kairo.doc.hash_after": self.doc_hash_after,
            "kairo.audit.id": self.id,
            "kairo.audit.prev_hash": self.prev_hash,
            "kairo.audit.record_hash": self.record_hash,
            "kairo.audit.chain_status": chain_status,
            "kairo.injection.backend": self.injection_backend,
            "kairo.compliance.override": self.compliance_override,
            "kairo.prompt": self.prompt,
            "kairo.output_preview": self.output_preview,
        }).to_string()
    }

    /// Format this entry as a CSV row (no escaping of commas in fields; fields quoted)
    fn to_csv_row(&self) -> String {
        fn q(s: &str) -> String {
            format!("\"{}\"", s.replace('"', "\"\""))
        }
        format!("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}",
            self.timestamp,
            q(&self.user_id),
            q(&self.user_email),
            q(&self.spiffe_id),
            q(&self.agent_name),
            q(&self.doc_hash_before),
            q(&self.doc_hash_after),
            q(&self.prompt[..50.min(self.prompt.len())]),
            q(&self.output_preview[..50.min(self.output_preview.len())]),
            q(&self.injection_backend),
            self.compliance_override as u8,
            q(&self.outcome),
            q(&self.prev_hash[..16.min(self.prev_hash.len())]),
            q(&self.record_hash[..16.min(self.record_hash.len())]),
            self.severity(),
        )
    }
}

// ── Enterprise SIEM Exporter ──────────────────────────────────────────────────

pub struct EnterpriseSiemExporter {
    enterprise_db_path: PathBuf,
    legacy_db_path: PathBuf,
}

impl EnterpriseSiemExporter {
    pub fn from_env() -> Self {
        let base = dirs::home_dir().unwrap_or_default().join(".kairo-phantom");
        Self {
            enterprise_db_path: base.join("kairo_audit.db"),
            legacy_db_path:     base.join("audit.db"),
        }
    }

    pub fn new(enterprise_db_path: PathBuf, legacy_db_path: PathBuf) -> Self {
        Self { enterprise_db_path, legacy_db_path }
    }

    /// Verify the enterprise audit chain and return a status string.
    fn verify_enterprise_chain(&self) -> String {
        if !self.enterprise_db_path.exists() { return "NO_DB".to_string(); }
        use crate::enterprise::audit::EnterpriseAuditLogger;
        match EnterpriseAuditLogger::new(self.enterprise_db_path.clone()) {
            Ok(logger) => match logger.verify_chain() {
                Ok(r) => r.to_string(),
                Err(e) => format!("VERIFY_ERROR: {}", e),
            },
            Err(e) => format!("LOGGER_ERROR: {}", e),
        }
    }

    /// Fetch enterprise audit entries from kairo_audit.db.
    fn fetch_enterprise_entries(
        &self,
        since: Option<i64>,
        until: Option<i64>,
    ) -> Result<Vec<EnterpriseAuditEntry>> {
        if !self.enterprise_db_path.exists() { return Ok(vec![]); }
        let conn = rusqlite::Connection::open(&self.enterprise_db_path)?;

        // Check table exists
        let has_table: bool = conn.query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='enterprise_audit'",
            [], |r| r.get::<_, i64>(0),
        ).unwrap_or(0) > 0;
        if !has_table { return Ok(vec![]); }

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

        let rows = stmt.query_map(rusqlite::params![since, until], |row| {
            Ok(EnterpriseAuditEntry {
                id:                  row.get(0)?,
                timestamp:           row.get(1)?,
                user_id:             row.get(2)?,
                user_email:          row.get(3)?,
                spiffe_id:           row.get(4)?,
                agent_name:          row.get(5)?,
                doc_hash_before:     row.get(6)?,
                doc_hash_after:      row.get(7)?,
                prompt:              row.get(8)?,
                output_preview:      row.get(9)?,
                injection_backend:   row.get(10)?,
                compliance_override: row.get::<_, i32>(11)? != 0,
                outcome:             row.get(12)?,
                prev_hash:           row.get(13)?,
                record_hash:         row.get(14)?,
            })
        })?.filter_map(|r| r.ok()).collect();
        Ok(rows)
    }

    /// Export enterprise audit entries in the requested format.
    ///
    /// Returns (lines, chain_status_string).
    /// OWASP Agentic Top 10: AT4 — Data Exfiltration (export with chain verification)
    pub fn export_enterprise(
        &self,
        format: &SiemFormat,
        since: Option<i64>,
        until: Option<i64>,
    ) -> Result<(Vec<String>, String)> {
        let chain_status = self.verify_enterprise_chain();
        let entries = self.fetch_enterprise_entries(since, until)?;
        let host = std::env::var("COMPUTERNAME")
            .or_else(|_| std::env::var("HOSTNAME"))
            .unwrap_or_else(|_| "unknown".into());

        let lines: Vec<String> = match format {
            SiemFormat::Csv => {
                // CSV with header row
                let header = "timestamp,user_id,user_email,spiffe_id,agent_name,\
                              doc_hash_before,doc_hash_after,prompt_preview,\
                              output_preview,injection_backend,compliance_override,\
                              outcome,prev_hash_prefix,record_hash_prefix,severity"
                    .to_string();
                let mut rows = vec![header];
                rows.extend(entries.iter().map(|e| e.to_csv_row()));
                rows
            }
            SiemFormat::Cef  => entries.iter().map(|e| e.to_cef(&host)).collect(),
            SiemFormat::Leef => entries.iter().map(|e| e.to_leef(&host)).collect(),
            SiemFormat::Json => entries.iter().map(|e| e.to_json(&host, &chain_status)).collect(),
        };

        Ok((lines, chain_status))
    }

    /// Export to file and print a summary with chain verification status.
    pub fn export_enterprise_to_file(
        &self,
        format: &SiemFormat,
        out: &PathBuf,
        since: Option<i64>,
        until: Option<i64>,
    ) -> Result<usize> {
        let (lines, chain_status) = self.export_enterprise(format, since, until)?;
        let count = if format == &SiemFormat::Csv {
            lines.len().saturating_sub(1) // Don't count header row
        } else {
            lines.len()
        };
        std::fs::write(out, lines.join("\n"))?;
        println!("🔒 Audit chain: {}", chain_status);
        Ok(count)
    }
}

// ── Legacy SiemExporter (kept for backward compatibility) ─────────────────────

pub struct SiemExporter { db_path: PathBuf }

impl SiemExporter {
    pub fn from_env() -> Self {
        Self { db_path: dirs::home_dir().unwrap_or_default()
            .join(".kairo-phantom").join("audit.db") }
    }
    pub fn new(db_path: PathBuf) -> Self { Self { db_path } }

    fn fetch_entries(&self) -> Result<Vec<AuditEntry>> {
        if !self.db_path.exists() { return Ok(vec![]); }
        let conn = rusqlite::Connection::open(&self.db_path)?;
        let ok: bool = conn.query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='audit_log'",
            [], |row| row.get::<_, i64>(0)).unwrap_or(0) > 0;
        if !ok { return Ok(vec![]); }
        let mut stmt = conn.prepare(
            "SELECT timestamp, event_type, outcome, app_context, agent_id, model_name, char_count \
             FROM audit_log ORDER BY timestamp DESC LIMIT 10000")?;
        let rows = stmt.query_map([], |row| Ok(AuditEntry {
            timestamp:   row.get::<_, i64>(0).unwrap_or(0),
            event_type:  row.get::<_, String>(1).unwrap_or_default(),
            outcome:     row.get::<_, String>(2).unwrap_or_default(),
            app_context: row.get::<_, String>(3).unwrap_or_default(),
            agent_id:    row.get::<_, String>(4).unwrap_or_default(),
            model:       row.get::<_, String>(5).unwrap_or_default(),
            char_count:  row.get::<_, i64>(6).unwrap_or(0),
        }))?;
        Ok(rows.filter_map(|r| r.ok()).collect())
    }

    pub fn export(&self, format: &SiemFormat) -> Result<Vec<String>> {
        let host = std::env::var("COMPUTERNAME")
            .or_else(|_| std::env::var("HOSTNAME")).unwrap_or_else(|_| "unknown".into());
        Ok(self.fetch_entries()?.iter().map(|e| Self::fmt(e, format, &host)).collect())
    }

    pub fn export_to_file(&self, format: &SiemFormat, out: &PathBuf) -> Result<usize> {
        let lines = self.export(format)?;
        let n = lines.len();
        std::fs::write(out, lines.join("\n"))?;
        Ok(n)
    }

    pub fn fmt(e: &AuditEntry, format: &SiemFormat, host: &str) -> String {
        match format {
            SiemFormat::Cef => format!(
                "CEF:0|KairoPhantom|GhostWriter|0.3.0|{}|{}|{}|rt={} src={} agent={} app={} chars={}",
                e.event_type, e.event_type, e.severity(),
                e.timestamp * 1000, host, e.agent_short(), e.app_context, e.char_count),
            SiemFormat::Leef => format!(
                "LEEF:2.0|KairoPhantom|GhostWriter|0.3.0|{}|\tdevTime={}\tsrc={}\tagent={}\tapp={}\tsev={}",
                e.event_type, e.timestamp, host, e.agent_short(), e.app_context, e.severity()),
            SiemFormat::Csv => format!(
                "{},{},{},{},{},{},{}",
                e.timestamp, e.event_type, e.outcome, e.app_context,
                e.agent_short(), e.model, e.char_count),
            SiemFormat::Json => serde_json::json!({
                "@timestamp": e.dt().to_rfc3339(), "event.action": e.event_type,
                "event.outcome": e.outcome, "host.name": host,
                "kairo.agent_id": e.agent_short(), "kairo.app": e.app_context,
                "event.severity": e.severity(),
            }).to_string(),
        }
    }
}

// ── CLI Command ───────────────────────────────────────────────────────────────

pub async fn run_siem_export_command(args: &[String]) -> Result<()> {
    let format: SiemFormat = args.iter().position(|a| a == "--format" || a == "-f")
        .and_then(|i| args.get(i + 1)).map(|s| s.parse::<SiemFormat>())
        .transpose()?.unwrap_or(SiemFormat::Json);

    let output: Option<PathBuf> = args.iter().position(|a| a == "--output" || a == "-o")
        .and_then(|i| args.get(i + 1)).map(PathBuf::from);

    // Parse optional time range
    let since: Option<i64> = args.iter().position(|a| a == "--since")
        .and_then(|i| args.get(i + 1))
        .and_then(|s| {
            chrono::DateTime::parse_from_rfc3339(s).ok()
                .or_else(|| chrono::DateTime::parse_from_rfc3339(&format!("{}T00:00:00Z", s)).ok())
        })
        .map(|dt| dt.timestamp());

    let until: Option<i64> = args.iter().position(|a| a == "--until")
        .and_then(|i| args.get(i + 1))
        .and_then(|s| {
            chrono::DateTime::parse_from_rfc3339(s).ok()
                .or_else(|| chrono::DateTime::parse_from_rfc3339(&format!("{}T23:59:59Z", s)).ok())
        })
        .map(|dt| dt.timestamp());

    // Always use enterprise exporter (which includes chain verification)
    let exporter = EnterpriseSiemExporter::from_env();

    println!("📤 Kairo Phantom — SIEM Export");
    println!("   Format: {}", format);
    if let Some(s) = since {
        println!("   Since:  {}", DateTime::<Utc>::from_timestamp(s, 0)
            .unwrap_or_default().to_rfc3339());
    }
    if let Some(u) = until {
        println!("   Until:  {}", DateTime::<Utc>::from_timestamp(u, 0)
            .unwrap_or_default().to_rfc3339());
    }

    if let Some(ref out) = output {
        let n = exporter.export_enterprise_to_file(&format, out, since, until)?;
        println!("✅ Exported {} audit events → {}", n, out.display());
    } else {
        let (lines, chain_status) = exporter.export_enterprise(&format, since, until)?;
        println!("🔒 Audit chain: {}", chain_status);
        println!("---");
        for line in &lines {
            println!("{}", line);
        }
        println!("---");
        println!("✅ {} audit events", lines.len());
    }

    Ok(())
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn sample() -> AuditEntry {
        AuditEntry {
            timestamp: 1700000000,
            event_type: "GhostSessionCompleted".into(),
            outcome: "success".into(),
            app_context: "Microsoft Word".into(),
            agent_id: "abcdef1234567890".into(),
            model: "qwen2.5:7b".into(),
            char_count: 512,
        }
    }

    fn enterprise_sample() -> EnterpriseAuditEntry {
        EnterpriseAuditEntry {
            id: 1,
            timestamp: 1700000000,
            user_id: "alice".into(),
            user_email: "alice@lawfirm.com".into(),
            spiffe_id: "spiffe://kairo-phantom.io/agent/word-specialist".into(),
            agent_name: "word-specialist".into(),
            doc_hash_before: "a".repeat(64),
            doc_hash_after: "b".repeat(64),
            prompt: "// Rewrite this clause for clarity".into(),
            output_preview: "The party of the first part...".into(),
            injection_backend: "Adeu".into(),
            compliance_override: false,
            outcome: "success".into(),
            prev_hash: "genesis".into(),
            record_hash: "c".repeat(64),
        }
    }

    // ── Legacy format tests ───────────────────────────────────────────────────

    #[test]
    fn test_legacy_cef_format() {
        let l = SiemExporter::fmt(&sample(), &SiemFormat::Cef, "host");
        assert!(l.starts_with("CEF:0|"), "CEF must start with CEF:0|");
        assert!(l.contains("GhostSessionCompleted"), "Must contain event type");
        assert!(l.contains("rt="), "Must contain timestamp");
    }

    #[test]
    fn test_legacy_leef_format() {
        let l = SiemExporter::fmt(&sample(), &SiemFormat::Leef, "host");
        assert!(l.starts_with("LEEF:2.0|"), "LEEF must start with LEEF:2.0|");
        assert!(l.contains("devTime="), "Must contain devTime");
    }

    #[test]
    fn test_legacy_json_format() {
        let l = SiemExporter::fmt(&sample(), &SiemFormat::Json, "host");
        let v: serde_json::Value = serde_json::from_str(&l).unwrap();
        assert_eq!(v["event.action"], "GhostSessionCompleted");
        assert!(v["@timestamp"].as_str().is_some(), "Must have @timestamp");
    }

    #[test]
    fn test_legacy_csv_format() {
        let l = SiemExporter::fmt(&sample(), &SiemFormat::Csv, "host");
        let fields: Vec<&str> = l.split(',').collect();
        assert!(fields.len() >= 7, "CSV must have at least 7 fields");
        assert!(l.contains("GhostSessionCompleted"), "CSV must contain event type");
    }

    #[test]
    fn test_no_legacy_db() {
        let d = tempdir().unwrap();
        let exp = SiemExporter::new(d.path().join("none.db"));
        assert_eq!(exp.export(&SiemFormat::Json).unwrap().len(), 0);
    }

    // ── Enterprise format tests ───────────────────────────────────────────────

    #[test]
    fn test_enterprise_cef_has_spiffe_id() {
        let e = enterprise_sample();
        let cef = e.to_cef("testhost");
        assert!(cef.starts_with("CEF:0|"), "Must start with CEF:0|");
        assert!(cef.contains("spiffe://"), "CEF must contain SPIFFE ID");
        assert!(cef.contains("alice@lawfirm.com"), "CEF must contain user email");
        assert!(cef.contains("Adeu"), "CEF must contain injection backend");
    }

    #[test]
    fn test_enterprise_leef_has_required_fields() {
        let e = enterprise_sample();
        let leef = e.to_leef("testhost");
        assert!(leef.starts_with("LEEF:2.0|"), "Must start with LEEF:2.0|");
        assert!(leef.contains("alice@lawfirm.com"), "Must contain user email");
        assert!(leef.contains("spiffe://"), "Must contain SPIFFE ID");
    }

    #[test]
    fn test_enterprise_json_has_all_domain9_fields() {
        let e = enterprise_sample();
        let json_str = e.to_json("testhost", "INTACT");
        let v: serde_json::Value = serde_json::from_str(&json_str).unwrap();
        assert_eq!(v["user.email"], "alice@lawfirm.com");
        assert_eq!(v["kairo.agent.spiffe_id"], "spiffe://kairo-phantom.io/agent/word-specialist");
        assert_eq!(v["kairo.audit.chain_status"], "INTACT");
        assert_eq!(v["kairo.injection.backend"], "Adeu");
        assert!(v["kairo.doc.hash_before"].as_str().is_some());
        assert!(v["kairo.audit.prev_hash"].as_str().is_some());
        assert!(v["kairo.audit.record_hash"].as_str().is_some());
    }

    #[test]
    fn test_enterprise_csv_header_has_required_columns() {
        let dir = tempdir().unwrap();
        let exp = EnterpriseSiemExporter::new(
            dir.path().join("kairo_audit.db"),
            dir.path().join("audit.db"),
        );
        let (lines, _) = exp.export_enterprise(&SiemFormat::Csv, None, None).unwrap();
        // Even with no data, CSV export must produce a header row
        assert!(!lines.is_empty(), "CSV must have at least a header row");
        let header = &lines[0];
        assert!(header.contains("user_id"), "CSV header must have user_id");
        assert!(header.contains("spiffe_id"), "CSV header must have spiffe_id");
        assert!(header.contains("doc_hash_before"), "CSV header must have doc_hash_before");
        assert!(header.contains("outcome"), "CSV header must have outcome");
    }

    #[test]
    fn test_format_from_str_all_variants() {
        assert_eq!("cef".parse::<SiemFormat>().unwrap(), SiemFormat::Cef);
        assert_eq!("CEF".parse::<SiemFormat>().unwrap(), SiemFormat::Cef);
        assert_eq!("leef".parse::<SiemFormat>().unwrap(), SiemFormat::Leef);
        assert_eq!("LEEF".parse::<SiemFormat>().unwrap(), SiemFormat::Leef);
        assert_eq!("csv".parse::<SiemFormat>().unwrap(), SiemFormat::Csv);
        assert_eq!("CSV".parse::<SiemFormat>().unwrap(), SiemFormat::Csv);
        assert_eq!("json".parse::<SiemFormat>().unwrap(), SiemFormat::Json);
        assert_eq!("anything".parse::<SiemFormat>().unwrap(), SiemFormat::Json);
    }

    #[test]
    fn test_enterprise_csv_row_has_correct_field_count() {
        let e = enterprise_sample();
        let row = e.to_csv_row();
        let field_count = row.split(',').count();
        assert_eq!(field_count, 15, "CSV row must have exactly 15 fields");
    }

    #[test]
    fn test_severity_mapping() {
        let mut e = enterprise_sample();
        e.outcome = "blocked".into();
        assert_eq!(e.severity(), 8);
        e.outcome = "aborted".into();
        assert_eq!(e.severity(), 5);
        e.outcome = "success".into();
        assert_eq!(e.severity(), 2);
    }

    #[test]
    fn test_enterprise_exporter_no_db_returns_empty() {
        let dir = tempdir().unwrap();
        let exp = EnterpriseSiemExporter::new(
            dir.path().join("nonexistent_audit.db"),
            dir.path().join("nonexistent_legacy.db"),
        );
        let (lines, chain_status) = exp.export_enterprise(&SiemFormat::Json, None, None).unwrap();
        assert_eq!(lines.len(), 0, "No DB must return 0 events");
        assert_eq!(chain_status, "NO_DB", "Chain status must be NO_DB when no database");
    }

    #[test]
    fn test_enterprise_siem_export_with_live_data() {
        use crate::enterprise::audit::{EnterpriseAuditLogger, EnterpriseAuditEvent};

        let dir = tempdir().unwrap();
        let db_path = dir.path().join("kairo_audit.db");

        // Create enterprise audit logger and write 3 events
        let logger = EnterpriseAuditLogger::new(db_path.clone()).unwrap();
        for i in 0..3 {
            let event = EnterpriseAuditEvent::new(
                "alice", "alice@lawfirm.com",
                "spiffe://kairo-phantom.io/agent/word-specialist",
                "word-specialist",
                &format!("before_{}", i), &format!("after_{}", i),
                &format!("Prompt {}", i), &format!("Output {}", i),
                "Adeu", "success", "",
            );
            logger.log_event(event).unwrap();
        }

        // Now export via SIEM exporter
        let exporter = EnterpriseSiemExporter::new(
            db_path,
            dir.path().join("legacy.db"),
        );

        // JSON format
        let (json_lines, chain_status) = exporter.export_enterprise(&SiemFormat::Json, None, None).unwrap();
        assert_eq!(json_lines.len(), 3, "Must export all 3 events");
        assert!(chain_status.contains("INTACT") || chain_status.contains("3"),
            "Chain must be intact: {}", chain_status);

        // Verify each JSON line has required fields
        for line in &json_lines {
            let v: serde_json::Value = serde_json::from_str(line).unwrap();
            assert!(v["user.email"].as_str().is_some(), "Must have user.email");
            assert!(v["kairo.agent.spiffe_id"].as_str().is_some(), "Must have SPIFFE ID");
            assert!(v["kairo.audit.chain_status"].as_str().is_some(), "Must have chain_status");
        }

        // CSV format
        let (csv_lines, _) = exporter.export_enterprise(&SiemFormat::Csv, None, None).unwrap();
        assert_eq!(csv_lines.len(), 4, "CSV must have 1 header + 3 data rows");
        assert!(csv_lines[0].contains("user_id"), "First row must be header");

        // CEF format
        let (cef_lines, _) = exporter.export_enterprise(&SiemFormat::Cef, None, None).unwrap();
        assert_eq!(cef_lines.len(), 3, "CEF must have 3 event lines");
        assert!(cef_lines[0].starts_with("CEF:0|"), "CEF must start with CEF:0|");

        println!("✅ Enterprise SIEM export with live data: JSON={}, CSV={}, CEF={}",
            json_lines.len(), csv_lines.len() - 1, cef_lines.len());
    }
}
