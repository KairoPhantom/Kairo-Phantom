//! SIEM Audit Log Export — P4-A2
//! Exports governance audit logs in CEF/LEEF/JSON-lines format for SOC2/ISO27001.
//! Reads from the existing AuditLogger SQLite database.

use anyhow::Result;
use std::path::{Path, PathBuf};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, PartialEq)]
pub enum SiemFormat {
    Cef,       // Common Event Format (ArcSight)
    Leef,      // Log Event Extended Format (IBM QRadar)
    JsonLines, // Newline-delimited JSON (Splunk, Elastic)
}

#[derive(Debug)]
pub struct AuditLogEntry {
    pub timestamp: DateTime<Utc>,
    pub session_id: String,
    pub event_type: String,
    pub outcome: String,
    pub details: String,
    pub machine_id: String,
}

pub struct SiemExporter;

impl SiemExporter {
    /// Export audit logs from AuditLogger SQLite database.
    pub fn export(
        db_path: &Path,
        output_path: &Path,
        format: SiemFormat,
        since_hours: Option<u64>,
    ) -> Result<usize> {
        use rusqlite::Connection;

        let conn = Connection::open(db_path)?;
        let since_ts = since_hours.map(|h| {
            (chrono::Utc::now() - chrono::Duration::hours(h as i64)).timestamp()
        });

        let query = if since_ts.is_some() {
            "SELECT timestamp, session_id, event_type, outcome, details FROM audit_log WHERE timestamp >= ?1 ORDER BY timestamp ASC"
        } else {
            "SELECT timestamp, session_id, event_type, outcome, details FROM audit_log ORDER BY timestamp ASC"
        };

        let mut stmt = conn.prepare(query)?;

        let rows: Vec<AuditLogEntry> = if let Some(ts) = since_ts {
            stmt.query_map([ts], |row| {
                Ok(Self::row_to_entry(row))
            })?.flatten().collect()
        } else {
            stmt.query_map([], |row| {
                Ok(Self::row_to_entry(row))
            })?.flatten().collect()
        };

        let count = rows.len();
        let machine_id = std::env::var("COMPUTERNAME")
            .or_else(|_| std::env::var("HOSTNAME"))
            .unwrap_or_else(|_| "unknown".to_string());


        let output: Vec<String> = rows.iter().map(|entry| {
            Self::format_entry(entry, &format, &machine_id)
        }).collect();

        std::fs::write(output_path, output.join("\n"))?;
        tracing::info!(
            "📤 SIEM export: {} events → {:?} → {}",
            count, format, output_path.display()
        );
        Ok(count)
    }

    fn row_to_entry(row: &rusqlite::Row) -> AuditLogEntry {
        let ts: i64 = row.get(0).unwrap_or(0);
        AuditLogEntry {
            timestamp: DateTime::<Utc>::from_timestamp(ts, 0)
                .unwrap_or_else(|| Utc::now()),
            session_id: row.get(1).unwrap_or_default(),
            event_type: row.get(2).unwrap_or_default(),
            outcome: row.get(3).unwrap_or_default(),
            details: row.get(4).unwrap_or_default(),
            machine_id: String::new(),
        }
    }

    fn format_entry(entry: &AuditLogEntry, format: &SiemFormat, machine_id: &str) -> String {
        match format {
            SiemFormat::Cef => {
                // CEF:Version|Device Vendor|Device Product|Device Version|Event Class ID|Name|Severity|Extension
                format!(
                    "CEF:0|KairoPhantom|KairoPhantom|{}|{}|{}|5|rt={} shost={} outcome={} msg={}",
                    env!("CARGO_PKG_VERSION"),
                    entry.event_type,
                    entry.event_type,
                    entry.timestamp.to_rfc3339(),
                    machine_id,
                    entry.outcome,
                    entry.details.replace('|', "\\|")
                )
            }
            SiemFormat::Leef => {
                // LEEF:Version|Vendor|Product|Version|EventID|Key:Value pairs
                format!(
                    "LEEF:2.0|KairoPhantom|KairoPhantom|{}|{}|\tdevTime={}\tdevTimeFormat=ISO8601\tsrc={}\toutcome={}\tmsg={}",
                    env!("CARGO_PKG_VERSION"),
                    entry.event_type,
                    entry.timestamp.to_rfc3339(),
                    machine_id,
                    entry.outcome,
                    entry.details
                )
            }
            SiemFormat::JsonLines => {
                serde_json::json!({
                    "timestamp": entry.timestamp.to_rfc3339(),
                    "source": "kairo-phantom",
                    "version": env!("CARGO_PKG_VERSION"),
                    "session_id": entry.session_id,
                    "event_type": entry.event_type,
                    "outcome": entry.outcome,
                    "machine_id": machine_id,
                    "details": entry.details,
                }).to_string()
            }
        }
    }
}
