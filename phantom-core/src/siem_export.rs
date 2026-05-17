//! SIEM Export — P4-A2
//! CEF / LEEF / JSON-lines export from the Kairo governance audit log.

use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum SiemFormat { Cef, Leef, Json }

impl std::str::FromStr for SiemFormat {
    type Err = anyhow::Error;
    fn from_str(s: &str) -> Result<Self> {
        match s.to_lowercase().as_str() {
            "cef"  => Ok(SiemFormat::Cef),
            "leef" => Ok(SiemFormat::Leef),
            _      => Ok(SiemFormat::Json),
        }
    }
}

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
}

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

    fn fmt(e: &AuditEntry, format: &SiemFormat, host: &str) -> String {
        let sev = match e.outcome.as_str() { "blocked" => 8, "aborted" => 5, _ => 2 };
        let short = if e.agent_id.len() >= 8 { &e.agent_id[..8] } else { &e.agent_id };
        match format {
            SiemFormat::Cef => format!(
                "CEF:0|KairoPhantom|GhostWriter|0.3.0|{}|{}|{}|rt={} src={} agent={} app={} chars={}",
                e.event_type, e.event_type, sev, e.timestamp * 1000, host, short, e.app_context, e.char_count),
            SiemFormat::Leef => format!(
                "LEEF:2.0|KairoPhantom|GhostWriter|0.3.0|{}|\tdevTime={}\tsrc={}\tagent={}\tapp={}\tsev={}",
                e.event_type, e.timestamp, host, short, e.app_context, sev),
            SiemFormat::Json => serde_json::json!({
                "@timestamp": e.dt().to_rfc3339(), "event.action": e.event_type,
                "event.outcome": e.outcome, "host.name": host,
                "kairo.agent_id": short, "kairo.app": e.app_context,
                "event.severity": sev,
            }).to_string(),
        }
    }
}

pub async fn run_siem_export_command(args: &[String]) -> Result<()> {
    let format = args.iter().position(|a| a == "--format" || a == "-f")
        .and_then(|i| args.get(i + 1)).map(|s| s.parse::<SiemFormat>())
        .transpose()?.unwrap_or(SiemFormat::Json);
    let output = args.iter().position(|a| a == "--output" || a == "-o")
        .and_then(|i| args.get(i + 1)).map(PathBuf::from);
    let exporter = SiemExporter::from_env();
    if let Some(out) = output {
        let n = exporter.export_to_file(&format, &out)?;
        println!("📤 Exported {} audit events → {}", n, out.display());
    } else {
        for line in exporter.export(&format)? { println!("{}", line); }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*; use tempfile::tempdir;

    fn sample() -> AuditEntry { AuditEntry {
        timestamp: 1700000000, event_type: "GhostSessionCompleted".into(),
        outcome: "success".into(), app_context: "Microsoft Word".into(),
        agent_id: "abcdef1234567890".into(), model: "qwen2.5:7b".into(), char_count: 512 } }

    #[test] fn test_cef() {
        let l = SiemExporter::fmt(&sample(), &SiemFormat::Cef, "host");
        assert!(l.starts_with("CEF:0|")); assert!(l.contains("GhostSessionCompleted")); }
    #[test] fn test_leef() {
        let l = SiemExporter::fmt(&sample(), &SiemFormat::Leef, "host");
        assert!(l.starts_with("LEEF:2.0|")); }
    #[test] fn test_json() {
        let l = SiemExporter::fmt(&sample(), &SiemFormat::Json, "host");
        let v: serde_json::Value = serde_json::from_str(&l).unwrap();
        assert_eq!(v["event.action"], "GhostSessionCompleted"); }
    #[test] fn test_no_db() {
        let d = tempdir().unwrap();
        let exp = SiemExporter::new(d.path().join("none.db"));
        assert_eq!(exp.export(&SiemFormat::Json).unwrap().len(), 0); }
}
