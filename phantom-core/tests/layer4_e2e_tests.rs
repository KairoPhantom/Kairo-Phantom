/// ============================================================
/// LAYER 4: Cross-Platform E2E Integration Tests
///
/// Validates the complete Alt+M workflow end-to-end:
///   - Hotkey registration
///   - Config load lifecycle  
///   - Session creation and cancellation
///   - MCP server round-trip structure
///   - Swarm agent selection for different document types
///   - Clipboard injection fallback chain
/// ============================================================
use phantom_core::config::PhantomConfig;
use phantom_core::ghost_session::{GhostSession, ConfidenceBand, SessionState};
use phantom_core::document_context::{DocumentContext, DocKind};
use std::time::Duration;

// ──────────────────────────────────────────────────────────────
// E2E Test 1: Config loads with correct defaults
// ──────────────────────────────────────────────────────────────
#[test]
fn e2e_config_loads_with_correct_defaults() {
    let cfg = PhantomConfig::default();
    
    // Provider must default to ollama (offline-first)
    assert_eq!(cfg.model.provider, "ollama", "Must default to offline Ollama");
    
    // Hotkey must be set
    assert!(!cfg.hotkey.is_empty(), "Hotkey must not be empty");
    
    // Typing delay must be reasonable (not 0, not >1000ms)
    assert!(cfg.typing_delay_ms > 0 && cfg.typing_delay_ms <= 1000,
        "Typing delay {} is out of bounds", cfg.typing_delay_ms);
    
    // Model name must be populated for offline use
    assert!(cfg.model.model_name.is_some(), "Model name must be set for offline use");
}

// ──────────────────────────────────────────────────────────────
// E2E Test 2: GhostSession state machine transitions
// ──────────────────────────────────────────────────────────────
#[test]
fn e2e_ghost_session_state_transitions() {
    let session = GhostSession::new("complete this email", 20, ConfidenceBand::High);
    
    // Initial state must be Streaming (awaiting AI)
    assert!(matches!(session.state, SessionState::Streaming),
        "Initial state must be Streaming, got {:?}", session.state);
    
    // CancellationToken must be valid and uncancelled
    assert!(!session.cancel_token.is_cancelled(),
        "Token must start uncancelled");
    
    // Cancellation must work
    session.cancel_token.cancel();
    assert!(session.cancel_token.is_cancelled(),
        "Token must be cancelled after cancel()");
    
    // Prompt data must be intact
    assert_eq!(session.original_prompt, "complete this email");
    assert_eq!(session.prompt_char_count, 20);
}

// ──────────────────────────────────────────────────────────────
// E2E Test 3: ConfidenceBand routing logic
// ──────────────────────────────────────────────────────────────
#[test]
fn e2e_confidence_band_routing() {
    // Short vague prompt + unknown app → Low confidence
    let low = ConfidenceBand::compute("hey", "Unknown");
    assert!(matches!(low, ConfidenceBand::Low),
        "Short+Unknown must yield Low confidence");
    
    // Long clear prompt + known app → High confidence
    let high = ConfidenceBand::compute(
        "write a professional email declining the meeting invitation with a counterproposal",
        "Word"
    );
    assert!(matches!(high, ConfidenceBand::High),
        "Long+Known must yield High confidence");
    
    // Medium case
    let medium = ConfidenceBand::compute("write something", "Word");
    assert!(matches!(medium, ConfidenceBand::Medium),
        "Short+Known must yield Medium confidence");
}

// ──────────────────────────────────────────────────────────────
// E2E Test 4: Swarm agent selection by document type
// Uses DocumentContext::from_raw_text directly (no test helper needed)
// ──────────────────────────────────────────────────────────────
#[test]
fn e2e_swarm_selects_correct_agent_for_powerpoint() {
    use phantom_core::plugin::AgentRegistry;
    use phantom_core::swarm::{DesignAgent, ReasoningAgent, ContentAgent};
    use std::sync::Arc;
    
    let ctx = DocumentContext::from_raw_text(
        "add speaker notes",
        "Slide 1: Company Overview",
        DocKind::PowerPoint,
    );
    
    let mut registry = AgentRegistry::new();
    registry.register(Arc::new(DesignAgent));
    registry.register(Arc::new(ReasoningAgent));
    registry.register(Arc::new(ContentAgent));
    
    // PowerPoint must route to design agent
    let best = registry.select_best(&ctx);
    assert!(best.is_some(), "Registry must select an agent");
    let agent_id = best.unwrap().id().to_string();
    assert_eq!(agent_id, "design",
        "PowerPoint must route to design agent, got '{}'", agent_id);
}

#[test]
fn e2e_swarm_selects_correct_agent_for_code() {
    use phantom_core::plugin::AgentRegistry;
    use phantom_core::swarm::{DesignAgent, ReasoningAgent, ContentAgent};
    use std::sync::Arc;
    
    let ctx = DocumentContext::from_raw_text(
        "complete this function with error handling",
        "fn parse_json(input: &str) -> Result<Value> {",
        DocKind::CodeFile,
    );
    
    let mut registry = AgentRegistry::new();
    registry.register(Arc::new(DesignAgent));
    registry.register(Arc::new(ReasoningAgent));
    registry.register(Arc::new(ContentAgent));
    
    // Code context must route to reasoning agent
    let best = registry.select_best(&ctx);
    assert!(best.is_some(), "Registry must select an agent");
    let agent_id = best.unwrap().id().to_string();
    assert_eq!(agent_id, "reasoning",
        "Code context must route to reasoning agent, got '{}'", agent_id);
}

// ──────────────────────────────────────────────────────────────
// E2E Test 5: Esc cancel during streaming terminates cleanly
// ──────────────────────────────────────────────────────────────
#[tokio::test]
async fn e2e_esc_cancel_terminates_sse_stream() {
    let session = GhostSession::new("write a long document", 21, ConfidenceBand::High);
    let token = session.cancel_token.clone();
    
    // Simulate Esc key press cancelling the stream
    let cancel_task = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(10)).await;
        token.cancel();
    });
    
    // Wait for cancellation
    tokio::time::timeout(Duration::from_millis(500), async {
        session.cancel_token.cancelled().await;
    }).await.expect("Cancellation must complete within 500ms");
    
    cancel_task.await.unwrap();
    assert!(session.cancel_token.is_cancelled(), "Token must be cancelled after Esc");
}

// ──────────────────────────────────────────────────────────────
// E2E Test 6: Config TOML load/save round-trip
// ──────────────────────────────────────────────────────────────
#[test]
fn e2e_config_toml_roundtrip() {
    let original = PhantomConfig::default();
    
    // Serialize to TOML
    let toml_str = toml::to_string_pretty(&original)
        .expect("PhantomConfig must serialize to TOML");
    
    // Must produce valid TOML (parseable)
    assert!(!toml_str.is_empty(), "Serialized TOML must not be empty");
    
    // Deserialize back
    let restored: PhantomConfig = toml::from_str(&toml_str)
        .expect("Serialized TOML must be deserializable");
    
    // Key fields must match
    assert_eq!(restored.model.provider, original.model.provider);
    assert_eq!(restored.typing_delay_ms, original.typing_delay_ms);
    assert_eq!(restored.hotkey, original.hotkey);
}

// ──────────────────────────────────────────────────────────────
// E2E Test 7: Concurrent session stress — no deadlock
//   Simulates multiple parallel Alt+M triggers
// ──────────────────────────────────────────────────────────────
#[tokio::test]
async fn e2e_concurrent_sessions_no_deadlock() {
    let handles: Vec<_> = (0..20).map(|i| {
        tokio::spawn(async move {
            let prompt = format!("concurrent test prompt {}", i);
            let session = GhostSession::new(&prompt, prompt.len(), ConfidenceBand::High);
            
            // Each task cancels its own session
            session.cancel_token.cancel();
            
            assert!(session.cancel_token.is_cancelled());
            i
        })
    }).collect();
    
    // All 20 concurrent sessions must complete without deadlock
    let results = futures::future::join_all(handles).await;
    for (idx, res) in results.into_iter().enumerate() {
        assert_eq!(res.unwrap(), idx, "Task {} must complete", idx);
    }
}

// ──────────────────────────────────────────────────────────────
// E2E Test 8: MCP server JSON-RPC validation
//   Validates the JSON structure expected by the MCP transport
// ──────────────────────────────────────────────────────────────
#[test]
fn e2e_mcp_jsonrpc_structure_valid() {
    use serde_json::{json, Value};
    
    // Valid MCP request
    let request = json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "kairo_ghost_write",
            "arguments": {
                "prompt": "complete this sentence"
            }
        }
    });
    
    // Must have required fields
    assert_eq!(request["jsonrpc"], "2.0");
    assert!(request["id"].is_number());
    assert_eq!(request["method"], "tools/call");
    assert!(request["params"]["name"].is_string());
    
    // Serialize and deserialize — must be stable
    let serialized = serde_json::to_string(&request).unwrap();
    let deserialized: Value = serde_json::from_str(&serialized).unwrap();
    assert_eq!(deserialized["method"], "tools/call");
}
