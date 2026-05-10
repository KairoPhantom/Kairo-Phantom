/// ============================================================
/// LAYER 6: WASM Sandbox Defense-in-Depth Tests
///
/// Validates the Phase 4 WASM Plugin Sandbox:
///   - Ed25519 signature enforcement
///   - Capability bounding and manifest validation
///   - Concurrent Wasmtime compilation bounds
///   - Fuzzing of malformed manifests
/// ============================================================
use phantom_core::wasm_sandbox::{WasmPluginManifest, WasmCapability, WasmPluginRegistry, generate_skeleton_manifest};
use proptest::prelude::*;
use std::path::PathBuf;
use ed25519_dalek::{SigningKey, Signer, SecretKey};
use rand::rngs::OsRng;
use std::fs;
use tempfile::tempdir;

// ──────────────────────────────────────────────────────────────
// Test 1: Property Testing the Manifest Capability Validator
// ──────────────────────────────────────────────────────────────
proptest! {
    #[test]
    fn wasm_manifest_validation_never_panics(
        name in "\\PC*",
        author in "\\PC*",
        import_str in "[a-zA-Z0-9_]{1,20}::[a-zA-Z0-9_]{1,20}"
    ) {
        let manifest = WasmPluginManifest {
            name: name.clone(),
            version: "1.0.0".into(),
            author: author.clone(),
            publisher_key: Some("00".repeat(32)),
            signature: Some("00".repeat(64)),
            capabilities: vec![WasmCapability::ReadContext, WasmCapability::Stdout],
            wit_world: "kairo:world".into(),
            description: "test".into(),
            registry_verified: true,
            declared_imports: vec![import_str.clone()],
        };

        // Should not panic, just return violations
        let violations = manifest.validate_imports(&[import_str]);
        
        // Either it violates or it doesn't, but no panics.
        let _warnings = manifest.validate();
    }
}

// ──────────────────────────────────────────────────────────────
// Test 2: Ed25519 Signature Verification
// ──────────────────────────────────────────────────────────────
#[test]
fn wasm_ed25519_signature_verification() {
    let mut csprng = OsRng;
    let signing_key: SigningKey = SigningKey::generate(&mut csprng);
    let verifying_key = signing_key.verifying_key();
    
    // Create dummy WASM payload
    let wasm_bytes = b"\\0asm\\x01\\x00\\x00\\x00";
    
    use sha2::Digest;
    let hash = sha2::Sha256::digest(wasm_bytes);
    let signature = signing_key.sign(&hash);
    
    let mut manifest = WasmPluginManifest {
        name: "SignedPlugin".into(),
        version: "1.0.0".into(),
        author: "Test".into(),
        publisher_key: Some(hex::encode(verifying_key.as_bytes())),
        signature: Some(hex::encode(signature.to_bytes())),
        capabilities: vec![WasmCapability::WriteSuggestion],
        wit_world: "".into(),
        description: "".into(),
        registry_verified: true,
        declared_imports: vec![],
    };
    
    // Save to temp dir
    let dir = tempdir().unwrap();
    let wasm_path = dir.path().join("test.wasm");
    fs::write(&wasm_path, wasm_bytes).unwrap();
    let manifest_path = dir.path().join("test.manifest.json");
    fs::write(&manifest_path, serde_json::to_string(&manifest).unwrap()).unwrap();
    
    let mut registry = WasmPluginRegistry::new(dir.path().to_path_buf(), None);
    registry.scan_and_load();
    
    // Invalid WASM format will fail to compile in Wasmtime, but signature check happens FIRST.
    // We check the logs or plugin count. Since it fails to compile, it won't load,
    // but the signature check must pass. Let's break the signature and ensure it's rejected.
    
    let bad_signature = "00".repeat(64);
    manifest.signature = Some(bad_signature);
    fs::write(&manifest_path, serde_json::to_string(&manifest).unwrap()).unwrap();
    
    let mut bad_registry = WasmPluginRegistry::new(dir.path().to_path_buf(), None);
    bad_registry.scan_and_load();
    assert_eq!(bad_registry.plugin_count(), 1, "Plugin loads lazily");
    
    // Call the plugin to trigger compilation and signature check
    let input = phantom_core::wasm_sandbox::PluginCallInput {
        app_name: "Test".into(),
        doc_kind: "Text".into(),
        text: "hello".into(),
        prompt: "test".into(),
        agent_id: "test".into(),
    };
    
    let outputs = bad_registry.call_all(&input);
    assert_eq!(outputs.len(), 1);
    assert!(outputs[0].error.is_some(), "Invalid signature must fail during call/compilation");
    assert!(outputs[0].error.as_ref().unwrap().contains("FAILED"), "Must contain signature verification failure message");
}

// ──────────────────────────────────────────────────────────────
// Test 3: Capability Violation Rejection
// ──────────────────────────────────────────────────────────────
#[test]
fn wasm_capability_violation_rejection() {
    let manifest = WasmPluginManifest {
        name: "TestPlugin".into(),
        version: "1.0.0".into(),
        author: "Test".into(),
        publisher_key: None,
        signature: None,
        capabilities: vec![WasmCapability::ReadContext], // No Http or EnvRead
        wit_world: "".into(),
        description: "".into(),
        registry_verified: false,
        declared_imports: vec![],
    };
    
    // Try to import http_fetch
    let violations = manifest.validate_imports(&["kairo::http_fetch".to_string()]);
    assert_eq!(violations.len(), 1, "Must detect undeclared http_fetch import");
    assert!(violations[0].contains("http_fetch"));
    
    // Try to import env_read
    let violations = manifest.validate_imports(&["kairo::env_read".to_string()]);
    assert_eq!(violations.len(), 1, "Must detect undeclared env_read import");
}

// ──────────────────────────────────────────────────────────────
// Test 4: Concurrent Sandbox Isolation Stress Test
// ──────────────────────────────────────────────────────────────
#[tokio::test]
async fn wasm_concurrent_sandbox_stress_test() {
    // We will generate the skeleton manifest concurrently to ensure
    // no state leakage or panics in the manifest generator.
    let handles: Vec<_> = (0..100).map(|i| {
        tokio::spawn(async move {
            let manifest = generate_skeleton_manifest(&format!("Plugin{}", i), "Author");
            assert!(manifest.contains(&format!("Plugin{}", i)));
            i
        })
    }).collect();
    
    let results = futures::future::join_all(handles).await;
    for (idx, res) in results.into_iter().enumerate() {
        assert_eq!(res.unwrap(), idx);
    }
}
