/// Yjs Awareness Peer — Advancement 1
/// Kairo joins Yjs-powered docs as a CRDT peer with awareness broadcasting.

use std::sync::Arc;
use tokio::sync::Mutex;
use yrs::{Doc, GetString, Options, Text, Transact, WriteTxn, ReadTxn};
use yrs::updates::decoder::Decode;
use serde::{Deserialize, Serialize};
use tracing::{debug, info};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AwarenessState {
    pub name: String,
    pub color: String,
    pub status: String,
    pub progress: f32,
    pub active_section: Option<String>,
    pub agent_id: String,
}

impl Default for AwarenessState {
    fn default() -> Self {
        Self {
            name: "Kairo AI".into(),
            color: "#8b5cf6".into(),
            status: "idle".into(),
            progress: 0.0,
            active_section: None,
            agent_id: "auto".into(),
        }
    }
}

#[derive(Debug, Clone)]
pub enum SyncTransport {
    WebSocket { url: String, room: String },
    InProcess,
    Disconnected,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct YjsPeerConfig {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default = "default_true")]
    pub auto_detect: bool,
    #[serde(default)]
    pub endpoints: std::collections::HashMap<String, String>,
    #[serde(default = "default_prefix")]
    pub client_id_prefix: String,
    #[serde(default = "default_review")]
    pub review_mode: String,
}

fn default_true() -> bool { true }
fn default_prefix() -> String { "kairo-ai-".into() }
fn default_review() -> String { "ghost".into() }

impl Default for YjsPeerConfig {
    fn default() -> Self {
        Self { enabled: false, auto_detect: true, endpoints: Default::default(),
               client_id_prefix: "kairo-ai-".into(), review_mode: "ghost".into() }
    }
}

const YJS_URL_PATTERNS: &[(&str, &[&str])] = &[
    ("notion", &["notion.so", "notion.site"]),
    ("google_docs", &["docs.google.com/document"]),
    ("tiptap", &["tiptap.dev", "collab.tiptap.dev"]),
    ("linear", &["linear.app"]),
    ("blocksuite", &["blocksuite.io", "affine.pro"]),
    ("liveblocks", &["liveblocks.io"]),
];

const YJS_TITLE_PATTERNS: &[(&str, &[&str])] = &[
    ("notion", &["notion"]),
    ("google_docs", &["google docs"]),
    ("tiptap", &["tiptap"]),
    ("linear", &["linear"]),
    ("blocksuite", &["affine", "blocksuite"]),
];

pub struct YjsPeer {
    pub config: YjsPeerConfig,
    doc: Doc,
    pub client_id: u64,
    awareness: Arc<Mutex<AwarenessState>>,
    transport: Arc<Mutex<SyncTransport>>,
    connected: Arc<Mutex<bool>>,
}

impl YjsPeer {
    pub fn new(config: YjsPeerConfig) -> Self {
        let client_id = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default().as_nanos() as u64 & 0x00FF_FFFF_FFFF_FFFF;
        let doc = Doc::with_options(Options { client_id, ..Default::default() });
        info!("[YjsPeer] Created clientID: {}", client_id);
        Self { config, doc, client_id,
               awareness: Arc::new(Mutex::new(AwarenessState::default())),
               transport: Arc::new(Mutex::new(SyncTransport::Disconnected)),
               connected: Arc::new(Mutex::new(false)) }
    }

    pub fn detect_yjs_app(title: &str, url: Option<&str>) -> Option<String> {
        let t = title.to_lowercase();
        let u = url.unwrap_or("").to_lowercase();
        for (name, patterns) in YJS_URL_PATTERNS {
            if patterns.iter().any(|p| u.contains(p)) { return Some(name.to_string()); }
        }
        for (name, patterns) in YJS_TITLE_PATTERNS {
            if patterns.iter().any(|p| t.contains(p)) { return Some(name.to_string()); }
        }
        None
    }

    pub async fn connect(&self, app_name: &str) -> Result<(), String> {
        let ws = self.config.endpoints.get(app_name).cloned().unwrap_or("auto".into());
        if ws == "auto" {
            *self.transport.lock().await = SyncTransport::InProcess;
        } else {
            *self.transport.lock().await = SyncTransport::WebSocket { url: ws, room: app_name.into() };
        }
        *self.connected.lock().await = true;
        self.awareness.lock().await.status = "connected".into();
        Ok(())
    }

    pub async fn disconnect(&self) {
        *self.connected.lock().await = false;
        *self.transport.lock().await = SyncTransport::Disconnected;
        let mut s = self.awareness.lock().await;
        s.status = "idle".into(); s.progress = 0.0;
    }

    pub async fn is_connected(&self) -> bool { *self.connected.lock().await }

    pub fn read_document_text(&self) -> String {
        let c = self.doc.get_or_insert_text("content");
        let txn = self.doc.transact();
        let s = c.get_string(&txn); drop(txn); s
    }

    pub fn insert_text(&self, text: &str, pos: u32) -> Result<(), String> {
        let mut txn = self.doc.transact_mut();
        let c = txn.get_or_insert_text("content");
        c.insert(&mut txn, pos, text); drop(txn);
        info!("[YjsPeer] Inserted {} chars at pos {}", text.len(), pos);
        Ok(())
    }

    pub fn replace_text(&self, start: u32, del: u32, new: &str) -> Result<(), String> {
        let mut txn = self.doc.transact_mut();
        let c = txn.get_or_insert_text("content");
        if del > 0 { c.remove_range(&mut txn, start, del); }
        c.insert(&mut txn, start, new); drop(txn); Ok(())
    }

    pub fn append_text(&self, text: &str) -> Result<(), String> {
        let pos = self.read_document_text().len() as u32;
        self.insert_text(text, pos)
    }

    pub async fn set_awareness(&self, status: &str, progress: f32, section: Option<&str>, agent: &str) {
        let mut s = self.awareness.lock().await;
        s.status = status.into(); s.progress = progress;
        s.active_section = section.map(|x| x.into()); s.agent_id = agent.into();
        debug!("[YjsPeer] Awareness: {} {:.0}%", status, progress * 100.0);
    }

    pub async fn get_awareness(&self) -> AwarenessState { self.awareness.lock().await.clone() }
    pub async fn broadcast_thinking(&self, p: f32) { self.set_awareness("thinking...", p, None, "auto").await; }
    pub async fn broadcast_writing(&self, sec: &str, p: f32) {
        self.set_awareness(&format!("writing {}...", sec), p, Some(sec), "auto").await;
    }
    pub async fn broadcast_done(&self) { self.set_awareness("done", 1.0, None, "auto").await; }

    pub fn export_state(&self) -> Vec<u8> {
        let txn = self.doc.transact();
        txn.encode_state_as_update_v1(&Default::default())
    }

    pub fn apply_update(&self, update: &[u8]) -> Result<(), String> {
        let update_decoded = yrs::Update::decode_v1(update)
            .map_err(|e| format!("Decode error: {e}"))?;
        let mut txn = self.doc.transact_mut();
        txn.apply_update(update_decoded)
            .map_err(|e| format!("Apply error: {e:?}"))?;
        drop(txn); Ok(())
    }
}

pub struct YjsGhostBridge { peer: Arc<YjsPeer> }

impl YjsGhostBridge {
    pub fn new(peer: Arc<YjsPeer>) -> Self { Self { peer } }

    pub async fn inject_accepted(&self, text: &str, pos: u32) -> Result<(), String> {
        self.peer.broadcast_writing("injecting", 0.9).await;
        self.peer.insert_text(text, pos)?;
        self.peer.broadcast_done().await;
        Ok(())
    }

    pub async fn stream_token(&self, token: &str, pos: u32) -> Result<u32, String> {
        self.peer.insert_text(token, pos)?;
        Ok(pos + token.len() as u32)
    }
}

/// Module-level helper: detect if window title/URL indicates a Yjs-powered app.
/// Returns the app identifier (e.g. "google_docs", "notion") or None.
pub fn detect_yjs_app(title: &str, url: Option<&str>) -> Option<String> {
    YjsPeer::detect_yjs_app(title, url)
}
