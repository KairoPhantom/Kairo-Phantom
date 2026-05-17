//! Kairo Sidecar Client
//! ====================
//! Communicates with the Python sidecar process (localhost:7438) using
//! newline-delimited JSON over TCP.
//!
//! The sidecar owns all document I/O (DOCX, XLSX, PPTX, PDF).
//! This module is the Rust bridge to those capabilities.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::TcpStream;
use uuid::Uuid;

const SIDECAR_HOST: &str = "127.0.0.1";
const SIDECAR_PORT: u16 = 7438;

static SIDECAR_AVAILABLE: AtomicBool = AtomicBool::new(false);

// ─── Protocol types ───────────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
pub struct SidecarRequest {
    pub id: String,
    pub action: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub payload: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
pub struct SidecarResponse {
    pub id: String,
    pub ok: bool,
    #[serde(default)]
    pub data: Option<serde_json::Value>,
    #[serde(default)]
    pub error: Option<String>,
}

// ─── DocxOperation schema ─────────────────────────────────────────────────────

/// Typed operations the LLM can request for DOCX files.
/// The LLM is forced to output ONLY valid operations — never freeform prose.
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DocxOperation {
    /// "insert_after_heading" | "insert_paragraph" | "replace_paragraph" | "append" | "insert_table"
    pub action: String,
    /// For insert_after_heading: the heading text to find
    #[serde(skip_serializing_if = "Option::is_none")]
    pub heading_text: Option<String>,
    /// Word paragraph style: "Normal", "Heading1", "ListBullet", "ListNumber", etc.
    pub style: String,
    /// Text content to insert (string or Vec<String> for multiple paragraphs)
    pub content: serde_json::Value,
    /// For insert_paragraph/replace_paragraph: paragraph index
    #[serde(skip_serializing_if = "Option::is_none")]
    pub index: Option<usize>,
    /// For insert_table: row data [[cell, cell], [cell, cell]]
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rows: Option<Vec<Vec<String>>>,
}

/// Typed operations for XLSX cells.
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ExcelOperation {
    /// Cell reference, e.g. "G5"
    pub cell: String,
    /// Formula starting with "=" (takes priority over value)
    #[serde(default)]
    pub formula: String,
    /// Plain value if no formula
    #[serde(default)]
    pub value: String,
}

/// Typed operations for PPTX slides.
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SlideOperation {
    /// Zero-based slide index
    pub slide_index: usize,
    /// Shape ID to write to (None = content placeholder)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub shape_id: Option<i32>,
    /// Bullet points (max 7 words each, enforced by sidecar validator)
    pub bullets: Vec<String>,
}

// ─── Document context returned by sidecar ─────────────────────────────────────

#[derive(Debug, Deserialize, Default)]
pub struct DocxContext {
    pub full_text: String,
    pub headings: Vec<HeadingEntry>,
    pub paragraphs: Vec<ParagraphEntry>,
    pub paragraph_count: usize,
}

#[derive(Debug, Deserialize, Default, Clone)]
pub struct HeadingEntry {
    pub index: usize,
    pub level: i32,
    pub text: String,
}

#[derive(Debug, Deserialize, Default, Clone)]
pub struct ParagraphEntry {
    pub index: usize,
    pub text: String,
    pub style: String,
    pub is_heading: bool,
}

#[derive(Debug, Deserialize, Default)]
pub struct ExcelContext {
    pub active_cell: String,
    pub sheet_name: String,
    pub grid: Vec<Vec<CellEntry>>,
    pub headers: std::collections::HashMap<String, String>,
    pub named_ranges: Vec<String>,
}

#[derive(Debug, Deserialize, Default, Clone)]
pub struct CellEntry {
    pub r#ref: String,
    pub value: String,
    pub formula: String,
    pub is_active: bool,
}

// ─── Core client function ─────────────────────────────────────────────────────

/// Send one request to the sidecar and get the response.
/// Returns Err if the sidecar is down or returns an error response.
async fn call_sidecar(req: SidecarRequest) -> Result<serde_json::Value> {
    let stream = TcpStream::connect((SIDECAR_HOST, SIDECAR_PORT))
        .await
        .context("Sidecar not reachable — is kairo-sidecar/sidecar.py running?")?;

    let (reader, mut writer) = stream.into_split();
    let mut buf_reader = BufReader::new(reader);

    let json_line = serde_json::to_string(&req)? + "\n";
    writer.write_all(json_line.as_bytes()).await?;

    let mut response_line = String::new();
    buf_reader.read_line(&mut response_line).await?;

    let resp: SidecarResponse = serde_json::from_str(response_line.trim())
        .context("Invalid JSON from sidecar")?;

    if !resp.ok {
        bail!(
            "Sidecar error: {}",
            resp.error.unwrap_or_else(|| "unknown error".to_string())
        );
    }

    Ok(resp.data.unwrap_or(serde_json::Value::Null))
}

// ─── Public API ───────────────────────────────────────────────────────────────

/// Check if the sidecar is reachable. Updates SIDECAR_AVAILABLE flag.
pub async fn ping() -> bool {
    let req = SidecarRequest {
        id: Uuid::new_v4().to_string(),
        action: "ping".to_string(),
        path: None,
        payload: None,
    };
    let ok = call_sidecar(req).await.is_ok();
    SIDECAR_AVAILABLE.store(ok, Ordering::Relaxed);
    ok
}

/// Returns true if the sidecar was reachable at last ping.
pub fn is_available() -> bool {
    SIDECAR_AVAILABLE.load(Ordering::Relaxed)
}

/// Extract full structured context from a document file.
/// Returns the full_text + structure (headings, paragraphs, grid, etc.)
pub async fn extract_context(path: &str, active_cell: Option<&str>) -> Result<serde_json::Value> {
    let mut payload = serde_json::json!({});
    if let Some(cell) = active_cell {
        payload["active_cell"] = serde_json::Value::String(cell.to_string());
    }
    call_sidecar(SidecarRequest {
        id: Uuid::new_v4().to_string(),
        action: "extract_context".to_string(),
        path: Some(path.to_string()),
        payload: Some(payload),
    })
    .await
}

/// Read a DOCX file and return structured context.
pub async fn read_docx(path: &str) -> Result<DocxContext> {
    let data = call_sidecar(SidecarRequest {
        id: Uuid::new_v4().to_string(),
        action: "read_docx".to_string(),
        path: Some(path.to_string()),
        payload: None,
    })
    .await?;
    serde_json::from_value(data).context("Failed to parse DOCX context from sidecar")
}

/// Apply DocxOperation list to a .docx file.
pub async fn write_docx(path: &str, operations: Vec<DocxOperation>) -> Result<serde_json::Value> {
    let payload = serde_json::json!({
        "operations": serde_json::to_value(&operations)?
    });
    call_sidecar(SidecarRequest {
        id: Uuid::new_v4().to_string(),
        action: "write_docx".to_string(),
        path: Some(path.to_string()),
        payload: Some(payload),
    })
    .await
}

/// Read an Excel file with context around the active cell.
pub async fn read_xlsx(path: &str, active_cell: Option<&str>) -> Result<ExcelContext> {
    let mut payload = serde_json::json!({});
    if let Some(cell) = active_cell {
        payload["active_cell"] = serde_json::Value::String(cell.to_string());
    }
    let data = call_sidecar(SidecarRequest {
        id: Uuid::new_v4().to_string(),
        action: "read_xlsx".to_string(),
        path: Some(path.to_string()),
        payload: Some(payload),
    })
    .await?;
    serde_json::from_value(data).context("Failed to parse Excel context")
}

/// Apply ExcelOperation list to a .xlsx file.
pub async fn write_xlsx(path: &str, operations: Vec<ExcelOperation>) -> Result<serde_json::Value> {
    let payload = serde_json::json!({
        "operations": serde_json::to_value(&operations)?
    });
    call_sidecar(SidecarRequest {
        id: Uuid::new_v4().to_string(),
        action: "write_xlsx".to_string(),
        path: Some(path.to_string()),
        payload: Some(payload),
    })
    .await
}

/// Read a PPTX file and return slide inventory.
pub async fn read_pptx(path: &str) -> Result<serde_json::Value> {
    call_sidecar(SidecarRequest {
        id: Uuid::new_v4().to_string(),
        action: "read_pptx".to_string(),
        path: Some(path.to_string()),
        payload: None,
    })
    .await
}

/// Apply SlideOperation list to a .pptx file.
pub async fn write_pptx(path: &str, operations: Vec<SlideOperation>) -> Result<serde_json::Value> {
    let payload = serde_json::json!({
        "operations": serde_json::to_value(&operations)?
    });
    call_sidecar(SidecarRequest {
        id: Uuid::new_v4().to_string(),
        action: "write_pptx".to_string(),
        path: Some(path.to_string()),
        payload: Some(payload),
    })
    .await
}

// ─── Path resolver ────────────────────────────────────────────────────────────

/// Determine the file format from extension.
#[derive(Debug, Clone, PartialEq)]
pub enum DocFormat {
    Docx,
    Xlsx,
    Pptx,
    Pdf,
    Txt,
    Md,
    Code(String), // language name
    Unknown,
}

impl DocFormat {
    pub fn from_path(path: &str) -> Self {
        match Path::new(path).extension().and_then(|e| e.to_str()) {
            Some("docx") => DocFormat::Docx,
            Some("xlsx") | Some("xlsm") => DocFormat::Xlsx,
            Some("pptx") => DocFormat::Pptx,
            Some("pdf") => DocFormat::Pdf,
            Some("txt") => DocFormat::Txt,
            Some("md") | Some("markdown") => DocFormat::Md,
            Some(ext) if matches!(ext, "rs"|"py"|"js"|"ts"|"cpp"|"c"|"go"|"java"|"cs") => {
                DocFormat::Code(ext.to_string())
            }
            _ => DocFormat::Unknown,
        }
    }

    pub fn is_sidecar_supported(&self) -> bool {
        matches!(self, DocFormat::Docx | DocFormat::Xlsx | DocFormat::Pptx | DocFormat::Pdf | DocFormat::Txt | DocFormat::Md)
    }
}

/// Try to resolve the active document path from the window title.
/// Word titles look like: "Document1 - Microsoft Word" or "report.docx - Word"
/// VS Code titles look like: "main.rs - MyProject - Visual Studio Code"
pub fn resolve_document_path(window_title: &str, process_name: &str) -> Option<String> {
    let process_lower = process_name.to_lowercase();
    let home = dirs::home_dir().unwrap_or_default();

    // Microsoft Word: title often contains the filename
    if process_lower.contains("winword") {
        if let Some(fname) = window_title.split(" - ").next() {
            let fname = fname.trim();
            for dir in &[
                home.join("Documents"),
                home.join("Desktop"),
                std::env::current_dir().unwrap_or_default(),
            ] {
                let candidate = dir.join(fname);
                if candidate.exists() {
                    return Some(candidate.to_string_lossy().to_string());
                }
                let with_ext = dir.join(format!("{}.docx", fname));
                if with_ext.exists() {
                    return Some(with_ext.to_string_lossy().to_string());
                }
            }
        }
    }

    // VS Code: title has "filename - folder - Visual Studio Code"
    if process_lower.contains("code") && !process_lower.contains("discord") {
        if let Some(fname) = window_title.split(" - ").next() {
            let fname = fname.trim().trim_start_matches('●').trim();
            for dir in &[
                home.clone(),
                std::env::current_dir().unwrap_or_default(),
            ] {
                let candidate = dir.join(fname);
                if candidate.exists() {
                    return Some(candidate.to_string_lossy().to_string());
                }
            }
        }
    }

    // Excel: "Book1 - Excel" or "data.xlsx - Microsoft Excel"
    if process_lower.contains("excel") {
        if let Some(fname) = window_title.split(" - ").next() {
            let fname = fname.trim();
            for dir in &[
                home.join("Documents"),
                home.join("Desktop"),
            ] {
                let candidate = dir.join(fname);
                if candidate.exists() {
                    return Some(candidate.to_string_lossy().to_string());
                }
                let with_ext = dir.join(format!("{}.xlsx", fname));
                if with_ext.exists() {
                    return Some(with_ext.to_string_lossy().to_string());
                }
            }
        }
    }

    None
}

// ─── Sidecar launcher ─────────────────────────────────────────────────────────

/// Launch the Python sidecar as a background process.
/// Called once at daemon startup. Monitors and auto-restarts on crash.
pub async fn launch_sidecar() {
    use std::process::Stdio;
    use tokio::process::Command;

    // Search multiple locations for sidecar.py
    let exe = std::env::current_exe().unwrap_or_default();
    let cwd = std::env::current_dir().unwrap_or_default();

    let candidates = vec![
        // Relative to EXE: target/release/ → ../../kairo-sidecar/sidecar.py
        exe.parent().and_then(|p| p.parent()).and_then(|p| p.parent())
            .map(|p| p.join("kairo-sidecar").join("sidecar.py"))
            .unwrap_or_default(),
        // Relative to EXE: target/release/ → ../../../kairo-sidecar/sidecar.py (if in phantom-core/target/release)
        exe.parent().and_then(|p| p.parent()).and_then(|p| p.parent()).and_then(|p| p.parent())
            .map(|p| p.join("kairo-sidecar").join("sidecar.py"))
            .unwrap_or_default(),
        // Relative to current working directory
        cwd.join("kairo-sidecar").join("sidecar.py"),
        // Explicit known location based on project structure
        dirs::home_dir().unwrap_or_default()
            .join("Desktop").join("Memory").join("KairoPhantom")
            .join("kairo-sidecar").join("sidecar.py"),
    ];

    let sidecar_path = candidates.into_iter().find(|p| p.exists());

    let sidecar_path = match sidecar_path {
        Some(p) => {
            tracing::info!("🐍 Found sidecar at: {:?}", p);
            p
        }
        None => {
            tracing::warn!("⚠️  Sidecar not found in any candidate path — document-native mode disabled");
            tracing::warn!("   To enable: place sidecar.py at <project_root>/kairo-sidecar/sidecar.py");
            return;
        }
    };

    tokio::spawn(async move {
        let mut backoff_secs = 2u64;
        loop {
            tracing::info!("🐍 Launching Python sidecar: {:?}", sidecar_path);
            match Command::new("python")
                .arg(&sidecar_path)
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
            {
                Ok(mut child) => {
                    // Wait for sidecar to start
                    tokio::time::sleep(std::time::Duration::from_secs(3)).await;
                    // Ping to confirm it's up
                    if ping().await {
                        tracing::info!("✅ Sidecar ready on port {}", SIDECAR_PORT);
                        backoff_secs = 2;
                    }
                    // Wait for child to exit
                    let _ = child.wait().await;
                    tracing::warn!("⚠️  Sidecar process exited — restarting in {}s", backoff_secs);
                }
                Err(e) => {
                    tracing::warn!("⚠️  Failed to spawn sidecar: {} — retrying in {}s", e, backoff_secs);
                }
            }
            tokio::time::sleep(std::time::Duration::from_secs(backoff_secs)).await;
            backoff_secs = (backoff_secs * 2).min(60);
        }
    });
}
