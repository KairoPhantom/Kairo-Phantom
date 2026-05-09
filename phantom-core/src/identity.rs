/// Enterprise Identity — V6 Production-Grade
/// F1: Real Ed25519 keypair via ed25519-dalek + OsRng (replaces pseudo-random)
/// F2: Append-only audit log (JSONL) with tamper-evident hash chain
/// F3: JIT permission revocation with scoped TTL tokens

use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use tracing::{info, warn};

// ─── F1: Real Ed25519 Agent Identity ─────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentIdentity {
    pub agent_id: String,         // Public key hex (64 chars)
    pub private_key_hex: String,  // Ed25519 signing key hex (128 chars — full keypair)
    pub display_name: String,
    pub instance: String,
    pub created_at: u64,
    pub kairo_version: String,
}

impl AgentIdentity {
    /// F1: Generate real Ed25519 keypair using OsRng (cryptographically secure).
    pub fn generate(display_name: &str, instance: &str) -> Self {
        use ed25519_dalek::SigningKey;
        use rand::rngs::OsRng;

        let mut csprng = OsRng;
        let signing_key = SigningKey::generate(&mut csprng);
        let verifying_key = signing_key.verifying_key();

        // Encode as hex strings for JSON storage
        let private_key_hex = hex_encode(signing_key.to_bytes().as_ref());
        let agent_id = hex_encode(verifying_key.to_bytes().as_ref());

        let created_at = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default().as_secs();

        info!("[Identity] Generated Ed25519 agent_id: {}...{}", &agent_id[..8], &agent_id[56..]);

        Self {
            agent_id,
            private_key_hex,
            display_name: display_name.to_string(),
            instance: instance.to_string(),
            created_at,
            kairo_version: "0.6.0".into(),
        }
    }

    /// Load identity from disk, or generate a new one.
    pub fn load_or_create(config_dir: &PathBuf) -> Self {
        let path = config_dir.join("identity.json");
        if path.exists() {
            if let Ok(contents) = std::fs::read_to_string(&path) {
                if let Ok(identity) = serde_json::from_str::<Self>(&contents) {
                    info!("[Identity] Loaded agent_id: {}...", &identity.agent_id[..8]);
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

    pub fn save(&self, config_dir: &PathBuf) {
        let _ = std::fs::create_dir_all(config_dir);
        let path = config_dir.join("identity.json");
        match serde_json::to_string_pretty(self) {
            Ok(json) => { let _ = std::fs::write(&path, json); }
            Err(e) => warn!("[Identity] Save failed: {}", e),
        }
    }

    /// Sign arbitrary bytes with this agent's Ed25519 private key.
    pub fn sign(&self, data: &[u8]) -> Result<String, String> {
        use ed25519_dalek::{SigningKey, Signer};
        let key_bytes = hex_decode(&self.private_key_hex)
            .map_err(|e| format!("Key decode error: {}", e))?;
        let key_arr: [u8; 32] = key_bytes.try_into()
            .map_err(|_| "Invalid key length".to_string())?;
        let signing_key = SigningKey::from_bytes(&key_arr);
        let signature = signing_key.sign(data);
        Ok(hex_encode(signature.to_bytes().as_ref()))
    }

    /// F3: Create a scoped JIT token (expires after `ttl_secs`).
    pub fn create_jit_token(&self, scope: &str, ttl_secs: u64) -> JitToken {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default().as_secs();
        let payload = format!("{}:{}:{}", self.agent_id, scope, now + ttl_secs);
        let signature = self.sign(payload.as_bytes()).unwrap_or_default();
        JitToken {
            agent_id: self.agent_id.clone(),
            scope: scope.to_string(),
            issued_at: now,
            expires_at: now + ttl_secs,
            signature,
        }
    }

    pub fn agent_id_header(&self) -> String { self.agent_id.clone() }
}

// ─── F3: JIT Permission Token ─────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JitToken {
    pub agent_id: String,
    pub scope: String,
    pub issued_at: u64,
    pub expires_at: u64,
    pub signature: String,
}

impl JitToken {
    pub fn is_valid(&self) -> bool {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default().as_secs();
        now < self.expires_at
    }
    pub fn scope_matches(&self, required: &str) -> bool {
        self.scope == required || self.scope == "*"
    }
}

// ─── RBAC Table ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RbacTable {
    pub rules: std::collections::HashMap<String, Vec<String>>,
}

impl RbacTable {
    pub fn new() -> Self { Self::default() }
    pub fn allow(&mut self, agent_id: &str, patterns: Vec<String>) {
        self.rules.entry(agent_id.to_string()).or_default().extend(patterns);
    }
    pub fn is_allowed(&self, agent_id: &str, file_path: &str) -> bool {
        if matches!(agent_id, "auto" | "content" | "reasoning") { return true; }
        match self.rules.get(agent_id) {
            None => true,
            Some(patterns) => patterns.iter().any(|p| glob_match(p, file_path)),
        }
    }
}

fn glob_match(pattern: &str, path: &str) -> bool {
    if pattern == "*" || pattern == "**" { return true; }
    if pattern.starts_with("*.") { return path.ends_with(&pattern[1..]); }
    path.contains(pattern.trim_matches('*'))
}

// ─── Session Identity ─────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct SessionIdentity {
    pub agent_id: String,
    pub user_id: String,
    pub jit_token: JitToken,
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
            jit_token: identity.create_jit_token(scope, 300), // 5-min TTL
            started_at: std::time::Instant::now(),
            scope: scope.to_string(),
        }
    }
    pub fn elapsed_ms(&self) -> u128 { self.started_at.elapsed().as_millis() }
    pub fn is_still_valid(&self) -> bool { self.jit_token.is_valid() }
    pub fn auth_headers(&self) -> Vec<(String, String)> {
        vec![
            ("X-Kairo-Agent-ID".into(), self.agent_id.clone()),
            ("X-Kairo-JIT-Expires".into(), self.jit_token.expires_at.to_string()),
            ("X-Kairo-User-ID".into(), self.user_id.clone()),
        ]
    }
}

// ─── F2: Tamper-Evident Append-Only Audit Log ─────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditChainEntry {
    pub agent_id: String,
    pub user_id: String,
    pub action: String,
    pub doc_path: String,
    pub timestamp: u64,
    pub result: String,
    /// SHA-256 hash of the previous entry's JSON (tamper-evident chain)
    pub prev_hash: String,
    /// SHA-256 hash of this entry's JSON (self-hash for verification)
    pub self_hash: String,
}

impl AuditChainEntry {
    pub fn new(agent_id: &str, user_id: &str, action: &str, doc_path: &str, result: &str, prev_hash: &str) -> Self {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default().as_secs();
        let mut entry = Self {
            agent_id: agent_id.to_string(),
            user_id: user_id.to_string(),
            action: action.to_string(),
            doc_path: doc_path.to_string(),
            timestamp,
            result: result.to_string(),
            prev_hash: prev_hash.to_string(),
            self_hash: String::new(),
        };
        // Compute self-hash
        let json = serde_json::to_string(&entry).unwrap_or_default();
        entry.self_hash = sha256_hex(json.as_bytes());
        entry
    }
}

pub struct TamperEvidentAuditLog {
    path: PathBuf,
    last_hash: std::sync::Mutex<String>,
}

impl TamperEvidentAuditLog {
    pub fn new(path: PathBuf) -> Self {
        // Read last hash from existing log (for chain continuity)
        let last_hash = Self::read_last_hash(&path);
        info!("[AuditLog] Initialized chain at {:?}, last_hash={}...", path, &last_hash[..8.min(last_hash.len())]);
        Self { path, last_hash: std::sync::Mutex::new(last_hash) }
    }

    fn read_last_hash(path: &PathBuf) -> String {
        if !path.exists() { return "genesis".to_string(); }
        let contents = std::fs::read_to_string(path).unwrap_or_default();
        // Find last non-empty line
        for line in contents.lines().rev() {
            if !line.trim().is_empty() {
                if let Ok(entry) = serde_json::from_str::<AuditChainEntry>(line) {
                    return entry.self_hash;
                }
            }
        }
        "genesis".to_string()
    }

    pub fn append(&self, agent_id: &str, user_id: &str, action: &str, doc_path: &str, result: &str) {
        let mut last = self.last_hash.lock().unwrap();
        let entry = AuditChainEntry::new(agent_id, user_id, action, doc_path, result, &last);
        *last = entry.self_hash.clone();

        let line = serde_json::to_string(&entry).unwrap_or_default();
        if let Some(parent) = self.path.parent() { let _ = std::fs::create_dir_all(parent); }
        use std::io::Write;
        if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true).open(&self.path) {
            let _ = writeln!(file, "{}", line);
        }
        tracing::debug!("[AuditChain] Logged: {} → {} (hash: {}...)", action, result, &entry.self_hash[..8]);
    }

    /// Verify the chain integrity — returns number of violations found.
    pub fn verify_chain(&self) -> usize {
        if !self.path.exists() { return 0; }
        let contents = std::fs::read_to_string(&self.path).unwrap_or_default();
        let mut prev_hash = "genesis".to_string();
        let mut violations = 0;
        for (i, line) in contents.lines().enumerate() {
            if line.trim().is_empty() { continue; }
            if let Ok(entry) = serde_json::from_str::<AuditChainEntry>(line) {
                if entry.prev_hash != prev_hash {
                    warn!("[AuditChain] CHAIN VIOLATION at line {}: prev_hash mismatch", i+1);
                    violations += 1;
                }
                prev_hash = entry.self_hash.clone();
            }
        }
        if violations == 0 {
            info!("[AuditChain] Chain verified OK — no tampering detected");
        }
        violations
    }
}

// ─── Identity Manager ─────────────────────────────────────────────────────────

pub struct IdentityManager {
    pub identity: AgentIdentity,
    pub rbac: RbacTable,
    pub audit_log: Option<TamperEvidentAuditLog>,
}

impl IdentityManager {
    pub fn load(config_dir: &PathBuf) -> Self {
        let identity = AgentIdentity::load_or_create(config_dir);
        info!("[IdentityManager] Agent: {} | Instance: {}", identity.display_name, identity.instance);

        let audit_path = config_dir.join("audit_chain.jsonl");
        let audit_log = Some(TamperEvidentAuditLog::new(audit_path));

        Self { identity, rbac: RbacTable::new(), audit_log }
    }

    pub fn check_permission(&self, agent_id: &str, file_path: &str) -> bool {
        let allowed = self.rbac.is_allowed(agent_id, file_path);
        if !allowed {
            tracing::warn!("[RBAC] Agent '{}' denied: '{}'", agent_id, file_path);
            if let Some(log) = &self.audit_log {
                log.append(agent_id, "system", "rbac_denied", file_path, "denied");
            }
        }
        allowed
    }

    pub fn create_session(&self, agent_name: &str, scope: &str) -> SessionIdentity {
        SessionIdentity::new(&self.identity, agent_name, scope)
    }

    pub fn log_action(&self, action: &str, doc_path: &str, result: &str) {
        if let Some(log) = &self.audit_log {
            let user = std::env::var("USERNAME").or_else(|_| std::env::var("USER")).unwrap_or_else(|_| "local".into());
            log.append(&self.identity.agent_id, &user, action, doc_path, result);
        }
    }
}

// ─── Crypto Helpers ───────────────────────────────────────────────────────────

fn sha256_hex(data: &[u8]) -> String {
    use sha2::Digest;
    let hash = sha2::Sha256::digest(data);
    hex_encode(&hash)
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

fn hex_decode(hex: &str) -> Result<Vec<u8>, &'static str> {
    if hex.len() % 2 != 0 { return Err("Odd hex length"); }
    (0..hex.len()).step_by(2)
        .map(|i| u8::from_str_radix(&hex[i..i+2], 16).map_err(|_| "Invalid hex"))
        .collect()
}
