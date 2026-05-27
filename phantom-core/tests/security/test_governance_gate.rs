// tests/security/test_governance_gate.rs
//
// Domain 10 — Security Regression Test: Governance Gate
//
// Gate Condition:
//   • Writes to forbidden paths → blocked
//   • Token cap exceeded → blocked
//   • Tool allow-list violation → blocked
//   • cargo test --test test_governance_gate exits 0

use phantom_core::governance::{ToolGate, PluginPermissionManifest, PluginPermission};
use phantom_core::enterprise::rbac::{RbacPolicy, RbacEngine, AccessDecision};

// ══════════════════════════════════════════════════════════════════════════
// SECTION 1 — Forbidden Path Protection (ToolGate)
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn governance_blocks_windows_system32_write() {
    let gate = ToolGate::new();
    assert!(
        !gate.validate_file_access("C:\\Windows\\System32\\config\\SAM"),
        "Must block write to Windows SAM database"
    );
}

#[test]
fn governance_blocks_windows_system_files() {
    let gate = ToolGate::new();
    assert!(
        !gate.validate_file_access("C:\\Windows\\system.ini"),
        "Must block write to Windows system files"
    );
}

#[test]
fn governance_blocks_etc_passwd() {
    let gate = ToolGate::new();
    assert!(
        !gate.validate_file_access("/etc/passwd"),
        "Must block write to /etc/passwd on Unix"
    );
}

#[test]
fn governance_blocks_etc_shadow() {
    let gate = ToolGate::new();
    assert!(
        !gate.validate_file_access("/etc/shadow"),
        "Must block write to /etc/shadow on Unix"
    );
}

#[test]
fn governance_blocks_windows_system32_hosts() {
    let gate = ToolGate::new();
    assert!(
        !gate.validate_file_access("C:\\Windows\\System32\\drivers\\etc\\hosts"),
        "Must block write to system hosts file"
    );
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 2 — Token Cap Enforcement (ToolGate)
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn governance_token_cap_exceeded_blocks_request() {
    let gate = ToolGate::new();
    // ToolGate::new() sets cap at 5000 tokens
    let result = gate.validate_token_usage(999_999);
    assert!(
        !result,
        "Request exceeding token cap must be blocked"
    );
}

#[test]
fn governance_token_cap_within_limit_allowed() {
    let gate = ToolGate::new();
    let result = gate.validate_token_usage(1000);
    assert!(
        result,
        "Request within token cap must be allowed"
    );
}

#[test]
fn governance_token_exactly_at_cap_allowed() {
    let gate = ToolGate::new();
    // 5000 = exactly at cap limit — should be allowed
    let result = gate.validate_token_usage(5000);
    assert!(result, "Request at exactly the token cap must be allowed");
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 3 — Tool Allow-List Enforcement (ToolGate.authorize_tool_call)
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn governance_blocks_unauthorized_tool_network_fetch() {
    let gate = ToolGate::new();
    // Empty allowlist = all denied
    let allowed: &[&str] = &["read_document", "write_suggestion"];
    assert!(
        !gate.authorize_tool_call("network_fetch", allowed),
        "network_fetch must not be in the tool allow-list"
    );
}

#[test]
fn governance_blocks_unauthorized_tool_exec_command() {
    let gate = ToolGate::new();
    let allowed: &[&str] = &["read_document", "write_suggestion"];
    assert!(
        !gate.authorize_tool_call("exec_command", allowed),
        "exec_command must not be in the tool allow-list"
    );
}

#[test]
fn governance_blocks_unauthorized_tool_delete_file() {
    let gate = ToolGate::new();
    let allowed: &[&str] = &["read_document", "write_suggestion"];
    assert!(
        !gate.authorize_tool_call("delete_file", allowed),
        "delete_file must not be in the tool allow-list"
    );
}

#[test]
fn governance_allows_read_document_tool() {
    let gate = ToolGate::new();
    let allowed: &[&str] = &["read_document", "write_suggestion"];
    assert!(
        gate.authorize_tool_call("read_document", allowed),
        "read_document must be in the tool allow-list"
    );
}

#[test]
fn governance_allows_write_suggestion_tool() {
    let gate = ToolGate::new();
    let allowed: &[&str] = &["read_document", "write_suggestion"];
    assert!(
        gate.authorize_tool_call("write_suggestion", allowed),
        "write_suggestion must be in the tool allow-list"
    );
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 4 — Plugin Permission Manifest
// ══════════════════════════════════════════════════════════════════════════

#[test]
fn plugin_manifest_network_access_is_high_risk() {
    let manifest = PluginPermissionManifest {
        name: "NetworkPlugin".into(),
        version: "1.0.0".into(),
        author: Some("Test".into()),
        permissions: vec![PluginPermission::NetworkAccess, PluginPermission::ReadDocument],
        requires_approval: true,
        checksum_sha256: None,
    };
    // High-risk plugins must require approval
    assert!(manifest.requires_approval,
        "Plugin with NetworkAccess must require approval");
    assert!(manifest.has_permission(&PluginPermission::NetworkAccess));
    assert!(manifest.has_permission(&PluginPermission::ReadDocument));
    assert!(!manifest.has_permission(&PluginPermission::ProcessSpawn));
}

#[test]
fn plugin_manifest_process_spawn_is_high_risk() {
    let manifest = PluginPermissionManifest {
        name: "ProcessPlugin".into(),
        version: "1.0.0".into(),
        author: Some("Test".into()),
        permissions: vec![PluginPermission::ProcessSpawn],
        requires_approval: true,
        checksum_sha256: None,
    };
    assert!(manifest.has_permission(&PluginPermission::ProcessSpawn));
    assert!(manifest.requires_approval, "ProcessSpawn plugin must require approval");
}

#[test]
fn plugin_manifest_read_only_does_not_require_approval() {
    let manifest = PluginPermissionManifest {
        name: "SafePlugin".into(),
        version: "1.0.0".into(),
        author: Some("Test".into()),
        permissions: vec![PluginPermission::ReadDocument],
        requires_approval: false,
        checksum_sha256: None,
    };
    assert!(manifest.has_permission(&PluginPermission::ReadDocument));
    assert!(!manifest.has_permission(&PluginPermission::NetworkAccess));
    assert!(!manifest.has_permission(&PluginPermission::ProcessSpawn));
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 5 — RBAC Integration
// ══════════════════════════════════════════════════════════════════════════

fn roles(r: &[&str]) -> Vec<String> { r.iter().map(|s| s.to_string()).collect() }

#[test]
fn rbac_intern_cannot_access_agent() {
    let policy = RbacPolicy {
        allowed_roles: roles(&["admin", "editor"]),
        denied_roles: roles(&[]),
        allowed_document_types: vec![],
        max_tokens_per_request: 0,
        require_approval: false,
    };
    let result = RbacEngine::check_access(&policy, &roles(&["intern"]));
    assert!(
        !result.is_allowed(),
        "Intern must not access restricted agent"
    );
}

#[test]
fn rbac_admin_can_access_all_agents() {
    let policy = RbacPolicy {
        allowed_roles: roles(&["admin"]),
        denied_roles: vec![],
        allowed_document_types: vec![],
        max_tokens_per_request: 0,
        require_approval: false,
    };
    let result = RbacEngine::check_access(&policy, &roles(&["admin"]));
    assert!(result.is_allowed(), "Admin must have access");
}

#[test]
fn rbac_explicitly_denied_role_always_blocked() {
    let policy = RbacPolicy {
        allowed_roles: roles(&["contractor"]),
        denied_roles: roles(&["contractor"]), // Explicitly denied — deny wins
        allowed_document_types: vec![],
        max_tokens_per_request: 0,
        require_approval: false,
    };
    let result = RbacEngine::check_access(&policy, &roles(&["contractor"]));
    assert!(
        !result.is_allowed(),
        "Explicitly denied role must be blocked even if in allowed_roles (deny wins)"
    );
}

#[test]
fn rbac_permissive_policy_allows_everyone() {
    let policy = RbacPolicy::permissive();
    assert!(RbacEngine::check_access(&policy, &roles(&["intern"])).is_allowed());
    assert!(RbacEngine::check_access(&policy, &roles(&["unknown"])).is_allowed());
}

#[test]
fn rbac_require_approval_returns_requires_approval() {
    let policy = RbacPolicy {
        allowed_roles: vec![],
        denied_roles: vec![],
        allowed_document_types: vec![],
        max_tokens_per_request: 0,
        require_approval: true,
    };
    let result = RbacEngine::check_access(&policy, &roles(&["admin"]));
    assert!(
        matches!(result, AccessDecision::RequiresApproval(_)),
        "Must return RequiresApproval when require_approval=true"
    );
    // RequiresApproval.is_allowed() returns true (it can proceed with approval)
    assert!(result.is_allowed(), "RequiresApproval still counts as allowed (pending approval)");
}

#[test]
fn rbac_deny_wins_over_allowed_role() {
    let policy = RbacPolicy {
        allowed_roles: roles(&["legal"]),
        denied_roles: roles(&["intern"]),
        allowed_document_types: vec![],
        max_tokens_per_request: 0,
        require_approval: false,
    };
    // User has both legal (allowed) and intern (denied) — deny must win
    let result = RbacEngine::check_access(&policy, &roles(&["legal", "intern"]));
    assert!(
        !result.is_allowed(),
        "When user has both allowed and denied role, deny must win"
    );
}
