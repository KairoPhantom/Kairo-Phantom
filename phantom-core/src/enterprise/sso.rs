//! Domain 9 — Capability 1: Enterprise SSO & Identity
//!
//! Validates JWTs issued by Logto (MIT), Okta, Entra ID, or any OIDC provider.
//! Uses the `jsonwebtoken` crate (MIT) for RS256/HS256 verification.
//!
//! OWASP Agentic Top 10: AT1 — Agent Impersonation (SsoGate JWT validation)

use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use tracing::{info, warn};

// ── Config ─────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct SsoConfig {
    /// Enable SSO gate. Default false (single-user mode, no breaking change).
    #[serde(default)]
    pub enabled: bool,
    /// OIDC discovery URL (e.g. https://your-logto.example.com/oidc)
    #[serde(default)]
    pub discovery_url: String,
    /// OAuth2 client_id
    #[serde(default)]
    pub client_id: String,
    /// Expected JWT issuer (validated against `iss` claim)
    #[serde(default)]
    pub issuer: String,
    /// JWT audience to validate (`aud` claim)
    #[serde(default)]
    pub audience: String,
    /// Shared secret for HS256 (Logto local/dev mode). Leave blank for RS256.
    #[serde(default)]
    pub jwt_secret: String,
    /// Idle session timeout in seconds (default 3600)
    #[serde(default = "default_idle_timeout")]
    pub idle_timeout_secs: u64,
}

fn default_idle_timeout() -> u64 { 3600 }

// ── Session ─────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct SsoSession {
    pub user_id: String,
    pub email: String,
    pub roles: Vec<String>,
    pub jwt_exp: u64,
    pub access_token: String,
    pub authenticated_at: u64,
}

impl SsoSession {
    pub fn is_expired(&self) -> bool {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        now >= self.jwt_exp
    }

    pub fn has_role(&self, role: &str) -> bool {
        self.roles.iter().any(|r| r.eq_ignore_ascii_case(role))
    }

    /// Anonymous guest session used when SSO is disabled.
    pub fn anonymous() -> Self {
        Self {
            user_id: "local-user".to_string(),
            email: "local@kairo.local".to_string(),
            roles: vec!["admin".to_string()],
            jwt_exp: u64::MAX,
            access_token: String::new(),
            authenticated_at: 0,
        }
    }
}

// ── JWT Claims ──────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
struct JwtClaims {
    sub: String,
    #[serde(default)]
    email: Option<String>,
    #[serde(default)]
    roles: Option<Vec<String>>,
    exp: u64,
    #[serde(default)]
    iss: Option<String>,
}

// ── Gate Decision ───────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum SsoGateResult {
    /// SSO disabled — pass through with anonymous session.
    Disabled,
    /// Valid token, session attached.
    Allowed(SsoSession),
    /// Rejected: expired, invalid signature, or missing.
    Blocked(String),
}

// ── Validator ───────────────────────────────────────────────────────────────

pub struct JwtValidator {
    config: SsoConfig,
}

impl JwtValidator {
    pub fn new(config: SsoConfig) -> Self {
        Self { config }
    }

    /// Validate a raw JWT string. Returns SsoSession on success.
    ///
    /// OWASP Agentic Top 10: AT1 — Agent Impersonation (JWT signature verification)
    pub fn validate(&self, token: &str) -> Result<SsoSession> {
        use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};

        if token.is_empty() {
            return Err(anyhow!("JWT token is empty"));
        }

        let mut validation = Validation::new(Algorithm::HS256);

        if !self.config.audience.is_empty() {
            validation.set_audience(&[&self.config.audience]);
        } else {
            validation.validate_aud = false;
        }
        if !self.config.issuer.is_empty() {
            validation.set_issuer(&[&self.config.issuer]);
        }

        let decoding_key = if !self.config.jwt_secret.is_empty() {
            DecodingKey::from_secret(self.config.jwt_secret.as_bytes())
        } else {
            // RS256 — read enterprise PEM from config dir
            let pubkey_path = dirs::home_dir()
                .unwrap_or_default()
                .join(".kairo-phantom")
                .join("enterprise")
                .join("sso_public_key.pem");

            if pubkey_path.exists() {
                let pem = std::fs::read_to_string(&pubkey_path)
                    .map_err(|e| anyhow!("Failed to read SSO public key: {}", e))?;
                validation = Validation::new(Algorithm::RS256);
                if !self.config.audience.is_empty() {
                    validation.set_audience(&[&self.config.audience]);
                } else {
                    validation.validate_aud = false;
                }
                DecodingKey::from_rsa_pem(pem.as_bytes())
                    .map_err(|e| anyhow!("Invalid RSA public key PEM: {}", e))?
            } else {
                warn!("🔐 SSO: No public key at {:?} — dev mode (no-verify)", pubkey_path);
                validation.insecure_disable_signature_validation();
                DecodingKey::from_secret(b"")
            }
        };

        let token_data = decode::<JwtClaims>(token, &decoding_key, &validation)
            .map_err(|e| anyhow!("JWT validation failed: {}", e))?;

        let claims = token_data.claims;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        if claims.exp < now {
            return Err(anyhow!("JWT token has expired (exp={}, now={})", claims.exp, now));
        }

        info!("🔐 SSO: Authenticated '{}'", claims.sub);

        Ok(SsoSession {
            user_id: claims.sub.clone(),
            email: claims.email.unwrap_or_else(|| claims.sub.clone()),
            roles: claims.roles.unwrap_or_else(|| vec!["user".to_string()]),
            jwt_exp: claims.exp,
            access_token: token.to_string(),
            authenticated_at: now,
        })
    }
}

// ── Gate ────────────────────────────────────────────────────────────────────

pub struct SsoGate {
    config: SsoConfig,
    validator: JwtValidator,
}

impl SsoGate {
    pub fn new(config: SsoConfig) -> Self {
        let validator = JwtValidator::new(config.clone());
        Self { config, validator }
    }

    /// Evaluate the SSO gate for a given JWT token.
    ///
    /// OWASP Agentic Top 10: AT1 — Agent Impersonation (SsoGate JWT validation)
    pub fn check(&self, token: Option<&str>) -> SsoGateResult {
        if !self.config.enabled {
            return SsoGateResult::Disabled;
        }
        match token {
            None => {
                warn!("🔐 SSO: No token provided — blocking ghost-write");
                SsoGateResult::Blocked("Authentication required. Sign in via your Logto instance.".to_string())
            }
            Some(tok) => match self.validator.validate(tok) {
                Ok(session) => SsoGateResult::Allowed(session),
                Err(e) => {
                    warn!("🔐 SSO: JWT rejected — {}", e);
                    SsoGateResult::Blocked(format!("Authentication failed: {}", e))
                }
            },
        }
    }
}

// ── CLI ──────────────────────────────────────────────────────────────────────

pub fn run_sso_status(session: Option<&SsoSession>) {
    match session {
        None => println!("🔐 SSO: Not authenticated"),
        Some(s) => {
            println!("🔐 SSO Status:");
            println!("   User ID:  {}", s.user_id);
            println!("   Email:    {}", s.email);
            println!("   Roles:    {}", s.roles.join(", "));
            println!("   Expires:  {} ({})", s.jwt_exp,
                if s.is_expired() { "EXPIRED" } else { "valid" });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_anonymous_session_never_expires() {
        let anon = SsoSession::anonymous();
        assert!(!anon.is_expired());
    }

    #[test]
    fn test_anonymous_has_admin_role_case_insensitive() {
        let anon = SsoSession::anonymous();
        assert!(anon.has_role("admin"));
        assert!(anon.has_role("ADMIN"));
        assert!(!anon.has_role("intern"));
    }

    #[test]
    fn test_sso_disabled_returns_disabled_regardless_of_token() {
        let config = SsoConfig { enabled: false, ..Default::default() };
        let gate = SsoGate::new(config);
        assert_eq!(gate.check(None), SsoGateResult::Disabled);
        assert_eq!(gate.check(Some("any_token")), SsoGateResult::Disabled);
    }

    #[test]
    fn test_sso_enabled_no_token_blocks() {
        let config = SsoConfig {
            enabled: true,
            jwt_secret: "testsecret".to_string(),
            ..Default::default()
        };
        let gate = SsoGate::new(config);
        assert!(matches!(gate.check(None), SsoGateResult::Blocked(_)));
    }

    #[test]
    fn test_jwt_validator_rejects_empty_token() {
        let config = SsoConfig {
            jwt_secret: "testsecret".to_string(),
            ..Default::default()
        };
        let v = JwtValidator::new(config);
        assert!(v.validate("").is_err());
    }

    #[test]
    fn test_expired_session_detected() {
        let s = SsoSession {
            user_id: "u1".into(),
            email: "u1@test.com".into(),
            roles: vec![],
            jwt_exp: 1000, // ancient timestamp
            access_token: String::new(),
            authenticated_at: 0,
        };
        assert!(s.is_expired());
    }
}
