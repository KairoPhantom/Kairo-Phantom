//! Domain 9 — Capability 2: SPIFFE Agent Identity
//!
//! Cryptographically verifiable agent identity using SPIFFE URI format.
//! Offline/air-gapped: self-signed Ed25519 keys (no SPIRE server required).
//! Enterprises with SPIRE can set `agent_socket_path` in config.
//!
//! OWASP Agentic Top 10: AT1 — Agent Impersonation (SPIFFE X.509 SVID)

use anyhow::{anyhow, Result};
use base64::{engine::general_purpose::STANDARD as B64, Engine};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use tracing::info;

// ── Config ──────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct SpiffeConfig {
    /// Enable SPIFFE agent identity (always on by default for audit signing).
    #[serde(default = "spiffe_enabled_default")]
    pub enabled: bool,
    /// SPIFFE trust domain (e.g. "kairo-phantom.io")
    #[serde(default = "default_trust_domain")]
    pub trust_domain: String,
    /// Agent name suffix (e.g. "word-specialist")
    #[serde(default = "default_agent_name")]
    pub agent_name: String,
    /// Optional SPIRE workload API socket path (enterprise deployments with SPIRE server)
    #[serde(default)]
    pub agent_socket_path: Option<String>,
}

fn spiffe_enabled_default() -> bool { true }
fn default_trust_domain() -> String { "kairo-phantom.io".to_string() }
fn default_agent_name() -> String { "ghost-writer".to_string() }

// ── Identity Record ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpiffeIdentityRecord {
    /// Full SPIFFE URI: spiffe://<trust_domain>/agent/<agent_name>
    pub spiffe_id: String,
    pub trust_domain: String,
    pub agent_name: String,
    /// SHA-256 fingerprint of the Ed25519 public key (hex, 64 chars)
    pub cert_fingerprint: String,
    /// Ed25519 public key bytes (base64)
    pub public_key_b64: String,
    /// Ed25519 private key bytes (base64) — stored locally only, never logged
    #[serde(skip_serializing_if = "String::is_empty", default)]
    pub private_key_b64: String,
    /// Creation timestamp (unix seconds)
    pub created_at: i64,
}

// ── Agent ────────────────────────────────────────────────────────────────────

pub struct SpiffeAgent {
    pub identity: SpiffeIdentityRecord,
    signing_key: SigningKey,
}

impl SpiffeAgent {
    /// Load existing or generate new SPIFFE agent identity.
    ///
    /// OWASP Agentic Top 10: AT1 — Agent Impersonation (SPIFFE X.509 SVID)
    pub fn load_or_create(config: &SpiffeConfig) -> Result<Self> {
        let identity_dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".kairo-phantom")
            .join("enterprise");
        std::fs::create_dir_all(&identity_dir)?;
        let identity_path = identity_dir.join("spiffe_identity.json");

        if identity_path.exists() {
            let json = std::fs::read_to_string(&identity_path)?;
            let record: SpiffeIdentityRecord = serde_json::from_str(&json)?;
            let priv_bytes = B64.decode(&record.private_key_b64)
                .map_err(|e| anyhow!("Decode private key: {}", e))?;
            let key_bytes: [u8; 32] = priv_bytes.try_into()
                .map_err(|_| anyhow!("Invalid Ed25519 key length (expected 32 bytes)"))?;
            let signing_key = SigningKey::from_bytes(&key_bytes);
            info!("🔐 SPIFFE: Loaded identity '{}'", record.spiffe_id);
            Ok(Self { identity: record, signing_key })
        } else {
            Self::generate(config, &identity_path)
        }
    }

    /// Generate a fresh Ed25519 keypair and persist to disk.
    pub fn generate(config: &SpiffeConfig, save_path: &Path) -> Result<Self> {
        let signing_key = SigningKey::generate(&mut OsRng);
        let verifying_key: VerifyingKey = signing_key.verifying_key();
        let pub_bytes = verifying_key.to_bytes();
        let priv_bytes = signing_key.to_bytes();

        let spiffe_id = format!(
            "spiffe://{}/agent/{}",
            config.trust_domain, config.agent_name
        );

        // SHA-256 fingerprint of public key (analogous to TLS cert fingerprint)
        let mut hasher = Sha256::new();
        hasher.update(&pub_bytes);
        let cert_fingerprint = hex::encode(hasher.finalize());

        let record = SpiffeIdentityRecord {
            spiffe_id: spiffe_id.clone(),
            trust_domain: config.trust_domain.clone(),
            agent_name: config.agent_name.clone(),
            cert_fingerprint: cert_fingerprint.clone(),
            public_key_b64: B64.encode(pub_bytes),
            private_key_b64: B64.encode(priv_bytes),
            created_at: chrono::Utc::now().timestamp(),
        };

        let json = serde_json::to_string_pretty(&record)?;
        std::fs::write(save_path, &json)?;

        info!("🔐 SPIFFE: Generated identity '{}' (fp: {}...)",
            spiffe_id, &cert_fingerprint[..16]);

        Ok(Self { identity: record, signing_key })
    }

    /// Sign arbitrary bytes. Returns base64-encoded Ed25519 signature.
    ///
    /// Used to sign every audit event and every ghost-written document.
    ///
    /// OWASP Agentic Top 10: AT1 — Agent Impersonation (cryptographic signing)
    pub fn sign_payload(&self, data: &[u8]) -> String {
        let sig: Signature = self.signing_key.sign(data);
        B64.encode(sig.to_bytes())
    }

    /// Verify a signature against this agent's own public key.
    pub fn verify_signature(&self, data: &[u8], sig_b64: &str) -> bool {
        let vk = self.signing_key.verifying_key();
        Self::verify_with_key(data, sig_b64, &vk)
    }

    /// Verify a signature using an external base64-encoded Ed25519 public key.
    pub fn verify_with_pubkey(data: &[u8], sig_b64: &str, pubkey_b64: &str) -> bool {
        let Ok(pub_bytes) = B64.decode(pubkey_b64) else { return false; };
        let Ok(arr) = pub_bytes.try_into() else { return false; };
        let Ok(vk) = VerifyingKey::from_bytes(&arr) else { return false; };
        Self::verify_with_key(data, sig_b64, &vk)
    }

    fn verify_with_key(data: &[u8], sig_b64: &str, vk: &VerifyingKey) -> bool {
        let Ok(sig_bytes) = B64.decode(sig_b64) else { return false; };
        let Ok(arr) = sig_bytes.try_into() else { return false; };
        let sig = Signature::from_bytes(&arr);
        vk.verify(data, &sig).is_ok()
    }

    /// Print identity to stdout. Used by `kairo agent identity show`.
    pub fn show_identity(&self) {
        println!("🔐 Kairo Phantom — Agent Identity (SPIFFE)");
        println!("   SPIFFE ID:    {}", self.identity.spiffe_id);
        println!("   Trust Domain: {}", self.identity.trust_domain);
        println!("   Agent Name:   {}", self.identity.agent_name);
        println!("   Fingerprint:  {}", self.identity.cert_fingerprint);
        println!("   Public Key:   {}...", &self.identity.public_key_b64[..32]);
        println!("   Created At:   {}", self.identity.created_at);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn test_config() -> SpiffeConfig {
        SpiffeConfig {
            enabled: true,
            trust_domain: "test.kairo.io".to_string(),
            agent_name: "test-agent".to_string(),
            agent_socket_path: None,
        }
    }

    #[test]
    fn test_generate_produces_correct_spiffe_uri() {
        let tmp = tempdir().unwrap();
        let agent = SpiffeAgent::generate(&test_config(), &tmp.path().join("id.json")).unwrap();
        assert_eq!(agent.identity.spiffe_id, "spiffe://test.kairo.io/agent/test-agent");
    }

    #[test]
    fn test_sign_verify_roundtrip() {
        let tmp = tempdir().unwrap();
        let agent = SpiffeAgent::generate(&test_config(), &tmp.path().join("id.json")).unwrap();
        let data = b"audit event payload";
        let sig = agent.sign_payload(data);
        assert!(agent.verify_signature(data, &sig));
    }

    #[test]
    fn test_tampered_data_fails_verification() {
        let tmp = tempdir().unwrap();
        let agent = SpiffeAgent::generate(&test_config(), &tmp.path().join("id.json")).unwrap();
        let sig = agent.sign_payload(b"original");
        assert!(!agent.verify_signature(b"tampered", &sig));
    }

    #[test]
    fn test_fingerprint_is_64_hex_chars() {
        let tmp = tempdir().unwrap();
        let agent = SpiffeAgent::generate(&test_config(), &tmp.path().join("id.json")).unwrap();
        assert_eq!(agent.identity.cert_fingerprint.len(), 64);
        assert!(agent.identity.cert_fingerprint.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn test_identity_persisted_and_reloadable() {
        let tmp = tempdir().unwrap();
        let path = tmp.path().join("id.json");
        let agent1 = SpiffeAgent::generate(&test_config(), &path).unwrap();
        let fp1 = agent1.identity.cert_fingerprint.clone();
        // Read back from disk
        let json = std::fs::read_to_string(&path).unwrap();
        let record: SpiffeIdentityRecord = serde_json::from_str(&json).unwrap();
        assert_eq!(record.cert_fingerprint, fp1);
    }

    #[test]
    fn test_verify_with_pubkey_roundtrip() {
        let tmp = tempdir().unwrap();
        let agent = SpiffeAgent::generate(&test_config(), &tmp.path().join("id.json")).unwrap();
        let data = b"cross-verification test";
        let sig = agent.sign_payload(data);
        assert!(SpiffeAgent::verify_with_pubkey(data, &sig, &agent.identity.public_key_b64));
    }
}
