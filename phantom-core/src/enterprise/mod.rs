//! Domain 9 — Enterprise Governance & Compliance (module root)
//!
//! Provides the Trust & Revenue Layer for regulated enterprise deployments.
//!
//! ## Six Capabilities
//!
//!   1. [`sso`] — SSO & Identity (Logto/OIDC JWT validation, MIT)
//!   2. [`spiffe_identity`] — SPIFFE Agent Identity (Ed25519 X.509-equivalent)
//!   3. [`audit`] — Cryptographic Audit Logging (SHA-256 chain + HMAC sealing)
//!   4. [`compliance`] — Enhanced Compliance Scanning (HIPAA/GDPR/PCI regex)
//!   5. [`rbac`] — Role-Based Access Control (Waza agent dispatch + injection gates)
//!
//! ## 12-Step Ghost-Write Pipeline (Domain 9 additions in bold)
//! ```text
//! 1.  **SSO Gate**          → identity verified (Logto JWT)
//! 2.  **RBAC Check**        → authorized? (roles → Waza agent permissions)
//! 3.  **Compliance Scan**   → prompt contains PII/PCI? (Block or Warn)
//! 4.   PromptShield         → 27-detector injection guard
//! 5.   Waza Agent Dispatch  → specialist routing
//! 6.   LLM Generation       → AI output
//! 7.   Sentinel Sanitizer   → system-prompt leakage scan
//! 8.   Quality Gate         → Devil's Advocate + Style Reviewer
//! 9.  **Compliance Scan**   → output contains PII? (Block or Warn)
//! 10. **SPIFFE Sign**       → output cryptographically signed by agent
//! 11.  Ghost-Inject         → domain-specific backend (Adeu/ExcelMcp/sidecar)
//! 12. **Audit Log**         → immutable, cryptographically chained record
//! ```
//!
//! Every step is deterministic Rust. Nothing is bypassable by the LLM.

pub mod sso;
pub mod spiffe_identity;
pub mod audit;
pub mod compliance;
pub mod rbac;

pub use sso::{JwtValidator, SsoConfig, SsoGate, SsoGateResult, SsoSession};
pub use spiffe_identity::{SpiffeAgent, SpiffeConfig, SpiffeIdentityRecord};
pub use audit::{
    ChainVerificationResult, EnterpriseAuditEvent, EnterpriseAuditLogger,
    file_hash, sha256_hex,
};
pub use compliance::{ComplianceDecision, EnterpriseComplianceScanner, RegexViolation};
pub use rbac::{AccessDecision, RbacEngine, RbacPolicy};

use anyhow::Result;

/// Unified enterprise runtime — holds all Domain 9 subsystems.
///
/// Instantiate once at startup; pass a reference into the ghost-write pipeline.
pub struct Enterprise {
    pub sso_gate: SsoGate,
    pub spiffe: Option<SpiffeAgent>,
    pub audit: EnterpriseAuditLogger,
    pub current_session: Option<SsoSession>,
}

impl Enterprise {
    /// Initialise the enterprise runtime.
    pub fn init(sso_config: SsoConfig, spiffe_config: SpiffeConfig) -> Result<Self> {
        let sso_gate = SsoGate::new(sso_config);
        let spiffe = match SpiffeAgent::load_or_create(&spiffe_config) {
            Ok(agent) => {
                tracing::info!("🔐 Enterprise: SPIFFE identity loaded: {}",
                    agent.identity.spiffe_id);
                Some(agent)
            }
            Err(e) => {
                tracing::warn!("⚠️  Enterprise: SPIFFE init failed (audit signing disabled): {}", e);
                None
            }
        };
        let audit = EnterpriseAuditLogger::from_env()?;
        Ok(Self { sso_gate, spiffe, audit, current_session: None })
    }

    /// SPIFFE ID of this agent instance.
    pub fn spiffe_id(&self) -> String {
        self.spiffe.as_ref()
            .map(|s| s.identity.spiffe_id.clone())
            .unwrap_or_else(|| "spiffe://kairo-phantom.io/agent/local".to_string())
    }

    /// Current user ID (from SSO JWT or "local-user" when SSO disabled).
    pub fn user_id(&self) -> String {
        self.current_session.as_ref()
            .map(|s| s.user_id.clone())
            .unwrap_or_else(|| "local-user".to_string())
    }

    /// Current user email.
    pub fn user_email(&self) -> String {
        self.current_session.as_ref()
            .map(|s| s.email.clone())
            .unwrap_or_else(|| "local@kairo.local".to_string())
    }

    /// Current user roles.
    pub fn user_roles(&self) -> Vec<String> {
        self.current_session.as_ref()
            .map(|s| s.roles.clone())
            .unwrap_or_else(|| vec!["admin".to_string()])
    }
}
