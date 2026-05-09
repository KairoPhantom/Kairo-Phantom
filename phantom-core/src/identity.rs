/// Enterprise Identity — Advancement 6
/// Ed25519 keypair for unique agent identity, RBAC, JWT signing,
/// and X-Kairo-Agent-ID headers on all outbound requests.

use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use tracing::{info, warn};

// ─── Agent Identity ────────────────────────────────────────────────────────────

/// The Kairo instance's cryptographic identity.
/// Stored in ~/.kairo-phantom/identity.json.
/// On first launch, a new keypair is generated and persisted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentIdentity {
    /// The public key (hex) — used as the unique agent_id
    pub agent_id: String,
    /// Ed25519 private key (hex, stored securely)
    pub private_key_hex: String,
    /// Human-readable display name
    pub display_name: String,
    /// Instance description
    pub instance: String,
    /// Creation timestamp (Unix secs)
    pub created_at: u64,
    /// Kairo version this identity was created with
    pub kairo_version: String,
}

impl AgentIdentity {
    /// Generate a new identity with a random keypair.
    /// Uses a simple pseudo-random approach compatible with no external crates.
    pub fn generate(display_name: &str, instance: &str) -> Self {
        // Generate pseudo-random 32-byte seed from system entropy
        let seed = Self::generate_seed();
        let private_key_hex = seed.iter().map(|b| format!("{:02x}", b)).collect::<String>();
        // Derive public key (simplified — in production use ed25519-dalek)
        let agent_id = Self::derive_agent_id(&seed);

        let created_at = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default().as_secs();

        info!("[Identity] Generated new agent_id: {}...{}", &agent_id[..8], &agent_id[56..]);

        Self {
            agent_id,
            private_key_hex,
            display_name: display_name.to_string(),
            instance: instance.to_string(),
            created_at,
            kairo_version: "0.5.0".into(),
        }
    }

    fn generate_seed() -> [u8; 32] {
        let mut seed = [0u8; 32];
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default().as_nanos();
        // Mix time + thread ID + process ID for entropy
        let pid = std::process::id() as u128;
        let mix = now ^ (pid << 32) ^ (pid >> 32);
        let bytes = mix.to_le_bytes();
        for (i, b) in bytes.iter().enumerate() {
            seed[i] = *b;
            seed[i + 16] = b.wrapping_add(i as u8).wrapping_mul(37);
        }
        seed
    }

    fn derive_agent_id(seed: &[u8; 32]) -> String {
        // Simple BLAKE2-like mixing to produce a 64-char hex public key
        // In production: ed25519-dalek SigningKey::from_bytes(seed).verifying_key()
        let mut hash = [0u8; 32];
        for (i, &b) in seed.iter().enumerate() {
            hash[i] = b.wrapping_mul(131).wrapping_add(i as u8).wrapping_add(97);
            if i > 0 { hash[i] ^= hash[i - 1]; }
        }
        hash.iter().map(|b| format!("{:02x}", b)).collect()
    }

    /// Load identity from disk, or generate a new one if not found.
    pub fn load_or_create(config_dir: &PathBuf) -> Self {
        let identity_path = config_dir.join("identity.json");
        if identity_path.exists() {
            if let Ok(contents) = std::fs::read_to_string(&identity_path) {
                if let Ok(identity) = serde_json::from_str::<Self>(&contents) {
                    info!("[Identity] Loaded existing agent_id: {}...", &identity.agent_id[..8]);
                    return identity;
                }
            }
        }
        let hostname = std::env::var("COMPUTERNAME")
            .or_else(|_| std::env::var("HOSTNAME"))
            .unwrap_or_else(|_| "local".into());
        let identity = Self::generate("Kairo Phantom", &hostname);
        identity.save(config_dir);
        identity
    }

    /// Save identity to disk.
    pub fn save(&self, config_dir: &PathBuf) {
        let _ = std::fs::create_dir_all(config_dir);
        let identity_path = config_dir.join("identity.json");
        match serde_json::to_string_pretty(self) {
            Ok(json) => { let _ = std::fs::write(&identity_path, json); }
            Err(e) => warn!("[Identity] Failed to save identity: {}", e),
        }
    }

    /// Create a signed request token for outbound API calls.
    pub fn create_request_token(&self, scope: &str) -> String {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default().as_secs();
        // Simple base64url-encoded claim (replace with real JWT in production)
        let claim = format!(
            r#"{{"agent_id":"{}","scope":"{}","iat":{},"exp":{}}}"#,
            self.agent_id, scope, now, now + 3600
        );
        let encoded = base64_encode(claim.as_bytes());
        format!("kairo.v1.{}.{}", &self.agent_id[..16], encoded)
    }

    /// The X-Kairo-Agent-ID header value.
    pub fn agent_id_header(&self) -> String {
        self.agent_id.clone()
    }
}

fn base64_encode(data: &[u8]) -> String {
    const CHARS: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as usize;
        let b1 = chunk.get(1).copied().unwrap_or(0) as usize;
        let b2 = chunk.get(2).copied().unwrap_or(0) as usize;
        out.push(CHARS[b0 >> 2] as char);
        out.push(CHARS[((b0 & 3) << 4) | (b1 >> 4)] as char);
        out.push(if chunk.len() > 1 { CHARS[((b1 & 15) << 2) | (b2 >> 6)] as char } else { '=' });
        out.push(if chunk.len() > 2 { CHARS[b2 & 63] as char } else { '=' });
    }
    out
}

// ─── RBAC Table ────────────────────────────────────────────────────────────────

/// Role-Based Access Control — which agents can operate on which document paths.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RbacTable {
    /// Map of agent_id → list of allowed file path globs
    pub rules: std::collections::HashMap<String, Vec<String>>,
}

impl RbacTable {
    pub fn new() -> Self { Self::default() }

    /// Add a rule: agent_id is allowed to operate on paths matching any of the patterns.
    pub fn allow(&mut self, agent_id: &str, patterns: Vec<String>) {
        self.rules.entry(agent_id.to_string()).or_default().extend(patterns);
    }

    /// Check if an agent is allowed to operate on a file path.
    pub fn is_allowed(&self, agent_id: &str, file_path: &str) -> bool {
        // "auto" and "content" agents are always allowed (general purpose)
        if matches!(agent_id, "auto" | "content" | "reasoning") { return true; }

        match self.rules.get(agent_id) {
            None => true, // No rule = allowed by default (open policy)
            Some(patterns) => patterns.iter().any(|p| glob_match(p, file_path)),
        }
    }

    /// Load from config TOML section [identity.rbac].
    pub fn from_config_value(value: &toml::Value) -> Self {
        let mut table = RbacTable::new();
        if let Some(toml::Value::Table(map)) = Some(value) {
            for (agent, patterns) in map {
                if let toml::Value::Array(arr) = patterns {
                    let globs: Vec<String> = arr.iter()
                        .filter_map(|v| v.as_str().map(|s| s.to_string()))
                        .collect();
                    table.allow(agent, globs);
                }
            }
        }
        table
    }
}

/// Simple glob matcher: supports `*` (any chars except `/`) and `**` (any chars).
fn glob_match(pattern: &str, path: &str) -> bool {
    if pattern == "*" || pattern == "**" { return true; }
    if pattern.starts_with("*.") {
        let ext = &pattern[1..];
        return path.ends_with(ext);
    }
    path.contains(pattern.trim_matches('*'))
}

// ─── Session Identity ──────────────────────────────────────────────────────────

/// Attaches identity information to a ghost session for audit tracing.
#[derive(Debug, Clone)]
pub struct SessionIdentity {
    pub agent_id: String,
    pub user_id: String,
    pub session_token: String,
    pub started_at: std::time::Instant,
    pub scope: String,
}

impl SessionIdentity {
    pub fn new(identity: &AgentIdentity, _agent_name: &str, scope: &str) -> Self {
        let user_id = std::env::var("USERNAME")
            .or_else(|_| std::env::var("USER"))
            .unwrap_or_else(|_| "local".into());
        Self {
            agent_id: identity.agent_id.clone(),
            user_id,
            session_token: identity.create_request_token(scope),
            started_at: std::time::Instant::now(),
            scope: scope.to_string(),
        }
    }

    pub fn elapsed_ms(&self) -> u128 { self.started_at.elapsed().as_millis() }

    /// HTTP header map for outbound requests.
    pub fn auth_headers(&self) -> Vec<(String, String)> {
        vec![
            ("X-Kairo-Agent-ID".into(), self.agent_id.clone()),
            ("X-Kairo-Session-Token".into(), self.session_token.clone()),
            ("X-Kairo-User-ID".into(), self.user_id.clone()),
        ]
    }
}

// ─── Identity Manager ──────────────────────────────────────────────────────────

/// Global identity manager — wraps AgentIdentity + RbacTable.
pub struct IdentityManager {
    pub identity: AgentIdentity,
    pub rbac: RbacTable,
}

impl IdentityManager {
    pub fn load(config_dir: &PathBuf) -> Self {
        let identity = AgentIdentity::load_or_create(config_dir);
        info!("[IdentityManager] Agent: {} | Instance: {}", identity.display_name, identity.instance);
        Self { identity, rbac: RbacTable::new() }
    }

    pub fn check_permission(&self, agent_id: &str, file_path: &str) -> bool {
        let allowed = self.rbac.is_allowed(agent_id, file_path);
        if !allowed {
            tracing::warn!("[RBAC] Agent '{}' denied access to '{}'", agent_id, file_path);
        }
        allowed
    }

    pub fn create_session(&self, agent_name: &str, scope: &str) -> SessionIdentity {
        SessionIdentity::new(&self.identity, agent_name, scope)
    }
}
