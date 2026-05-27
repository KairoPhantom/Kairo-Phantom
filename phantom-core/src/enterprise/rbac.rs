//! Domain 9 — Capability 5: Role-Based Access Control for Waza Agents
//!
//! Evaluates RBAC policies at agent dispatch time (before LLM call)
//! and at injection time (before output reaches the document).
//! Policy is defined per-agent in the `[rbac]` section of the agent manifest.
//!
//! OWASP Agentic Top 10: AT3 — Tool Abuse (RBAC + PluginPermissionManifest)

use serde::{Deserialize, Serialize};
use tracing::info;

// ── Policy ───────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct RbacPolicy {
    /// Roles allowed to invoke this agent. Empty = all roles permitted.
    #[serde(default)]
    pub allowed_roles: Vec<String>,
    /// Roles explicitly denied, regardless of allowed_roles. Deny wins.
    #[serde(default)]
    pub denied_roles: Vec<String>,
    /// Document types this agent may operate on. Empty = no restriction.
    #[serde(default)]
    pub allowed_document_types: Vec<String>,
    /// Maximum tokens per LLM request (0 = no cap).
    #[serde(default)]
    pub max_tokens_per_request: u32,
    /// If true, requires human approval before dispatch.
    #[serde(default)]
    pub require_approval: bool,
}

impl RbacPolicy {
    /// Permissive default — allows any role.
    pub fn permissive() -> Self {
        Self::default()
    }
}

// ── Decision ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum AccessDecision {
    Allowed,
    Denied(String),
    RequiresApproval(String),
}

impl AccessDecision {
    pub fn is_allowed(&self) -> bool {
        matches!(self, Self::Allowed | Self::RequiresApproval(_))
    }

    pub fn deny_reason(&self) -> Option<&str> {
        match self {
            Self::Denied(r) => Some(r),
            _ => None,
        }
    }
}

// ── Engine ───────────────────────────────────────────────────────────────────

pub struct RbacEngine;

impl RbacEngine {
    /// Evaluate RBAC policy for a given set of user roles.
    ///
    /// Evaluation order (deny wins):
    ///   1. If user has any denied_role → Denied
    ///   2. If allowed_roles non-empty and user has none → Denied
    ///   3. If require_approval → RequiresApproval
    ///   4. Otherwise → Allowed
    ///
    /// OWASP Agentic Top 10: AT3 — Tool Abuse (RBAC gate before dispatch)
    pub fn check_access(policy: &RbacPolicy, user_roles: &[String]) -> AccessDecision {
        // Step 1: Explicit deny check (deny always wins)
        for denied in &policy.denied_roles {
            if user_roles.iter().any(|r| r.eq_ignore_ascii_case(denied)) {
                let reason = format!(
                    "Your role '{}' is explicitly denied from this agent.",
                    denied
                );
                info!("🚫 RBAC: Denied user with role '{}'", denied);
                return AccessDecision::Denied(reason);
            }
        }

        // Step 2: Allowlist check (only if allowlist is non-empty)
        if !policy.allowed_roles.is_empty() {
            let has_allowed = user_roles.iter().any(|ur| {
                policy.allowed_roles.iter().any(|ar| ar.eq_ignore_ascii_case(ur))
            });
            if !has_allowed {
                let reason = format!(
                    "None of your roles ({}) are in the allowed list ({}).",
                    user_roles.join(", "),
                    policy.allowed_roles.join(", ")
                );
                info!("🚫 RBAC: No matching allowed role for {:?}", user_roles);
                return AccessDecision::Denied(reason);
            }
        }

        // Step 3: Approval required
        if policy.require_approval {
            return AccessDecision::RequiresApproval(
                "This agent requires administrator approval before dispatch.".to_string()
            );
        }

        info!("✅ RBAC: Access granted for roles {:?}", user_roles);
        AccessDecision::Allowed
    }

    /// `kairo agent policy-check --agent <id> --user <email>`
    pub fn policy_check_cli(
        agent_id: &str,
        user_email: &str,
        user_roles: &[String],
        policy: &RbacPolicy,
    ) -> String {
        match Self::check_access(policy, user_roles) {
            AccessDecision::Allowed =>
                format!("✅ ALLOWED: '{}' may invoke agent '{}' (roles: {})",
                    user_email, agent_id, user_roles.join(", ")),
            AccessDecision::Denied(reason) =>
                format!("❌ DENIED: '{}' cannot invoke agent '{}' — {}",
                    user_email, agent_id, reason),
            AccessDecision::RequiresApproval(msg) =>
                format!("⚠️  REQUIRES APPROVAL: '{}' for agent '{}' — {}",
                    user_email, agent_id, msg),
        }
    }

    /// Check if a document type is permitted by policy.
    pub fn check_document_type(policy: &RbacPolicy, doc_type: &str) -> bool {
        if policy.allowed_document_types.is_empty() {
            return true; // No restriction
        }
        policy.allowed_document_types.iter()
            .any(|t| t.eq_ignore_ascii_case(doc_type))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn r(roles: &[&str]) -> Vec<String> {
        roles.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn test_intern_denied() {
        let policy = RbacPolicy {
            allowed_roles: r(&["legal", "partner"]),
            denied_roles: r(&["intern"]),
            ..Default::default()
        };
        assert!(matches!(RbacEngine::check_access(&policy, &r(&["intern"])), AccessDecision::Denied(_)));
    }

    #[test]
    fn test_partner_allowed() {
        let policy = RbacPolicy {
            allowed_roles: r(&["legal", "partner"]),
            denied_roles: r(&["intern"]),
            ..Default::default()
        };
        assert_eq!(RbacEngine::check_access(&policy, &r(&["partner"])), AccessDecision::Allowed);
    }

    #[test]
    fn test_no_matching_allowed_role_denied() {
        let policy = RbacPolicy {
            allowed_roles: r(&["admin"]),
            ..Default::default()
        };
        assert!(matches!(RbacEngine::check_access(&policy, &r(&["user"])), AccessDecision::Denied(_)));
    }

    #[test]
    fn test_permissive_allows_everyone() {
        let policy = RbacPolicy::permissive();
        assert_eq!(RbacEngine::check_access(&policy, &r(&["intern"])), AccessDecision::Allowed);
        assert_eq!(RbacEngine::check_access(&policy, &r(&[])), AccessDecision::Allowed);
    }

    #[test]
    fn test_deny_wins_over_allowed_role() {
        let policy = RbacPolicy {
            allowed_roles: r(&["legal"]),
            denied_roles: r(&["intern"]),
            ..Default::default()
        };
        // User has both legal (allowed) and intern (denied) — deny wins
        assert!(matches!(RbacEngine::check_access(&policy, &r(&["legal", "intern"])), AccessDecision::Denied(_)));
    }

    #[test]
    fn test_require_approval() {
        let policy = RbacPolicy {
            require_approval: true,
            ..Default::default()
        };
        assert!(matches!(RbacEngine::check_access(&policy, &r(&["admin"])), AccessDecision::RequiresApproval(_)));
    }

    #[test]
    fn test_policy_check_cli_allowed_output() {
        let policy = RbacPolicy::permissive();
        let out = RbacEngine::policy_check_cli("legal-review", "alice@firm.com", &r(&["partner"]), &policy);
        assert!(out.contains("ALLOWED"));
        assert!(out.contains("alice@firm.com"));
        assert!(out.contains("legal-review"));
    }

    #[test]
    fn test_policy_check_cli_denied_output() {
        let policy = RbacPolicy { denied_roles: r(&["intern"]), ..Default::default() };
        let out = RbacEngine::policy_check_cli("legal-review", "bob@firm.com", &r(&["intern"]), &policy);
        assert!(out.contains("DENIED"));
        assert!(out.contains("bob@firm.com"));
    }

    #[test]
    fn test_doc_type_restriction() {
        let policy = RbacPolicy {
            allowed_document_types: r(&["DOCX", "PDF"]),
            ..Default::default()
        };
        assert!(RbacEngine::check_document_type(&policy, "docx"));
        assert!(RbacEngine::check_document_type(&policy, "PDF"));
        assert!(!RbacEngine::check_document_type(&policy, "XLSX"));
    }

    #[test]
    fn test_doc_type_unrestricted_when_empty() {
        let policy = RbacPolicy::permissive();
        assert!(RbacEngine::check_document_type(&policy, "ANYTHING"));
    }

    #[test]
    fn test_is_allowed_helper() {
        assert!(AccessDecision::Allowed.is_allowed());
        assert!(AccessDecision::RequiresApproval("x".into()).is_allowed());
        assert!(!AccessDecision::Denied("x".into()).is_allowed());
    }

    #[test]
    fn test_case_insensitive_role_matching() {
        let policy = RbacPolicy {
            allowed_roles: r(&["Legal"]),
            ..Default::default()
        };
        assert_eq!(RbacEngine::check_access(&policy, &r(&["LEGAL"])), AccessDecision::Allowed);
    }
}
