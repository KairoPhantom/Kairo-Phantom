/// ============================================================
/// LAYER 1: Unit Tests — Core Module Isolation
///
/// Tests each internal function in isolation without 
/// external dependencies (Ollama, UIA, clipboard)
/// ============================================================
use phantom_core::ghost_session::{GhostSession, ConfidenceBand, SessionState};
use phantom_core::config::PhantomConfig;
use std::sync::atomic::Ordering;

// ─── ConfidenceBand ───────────────────────────────────────────

#[test]
fn unit_confidence_low_for_vague_unknown() {
    let band = ConfidenceBand::compute("ok", "Unknown");
    assert!(matches!(band, ConfidenceBand::Low));
}

#[test]
fn unit_confidence_medium_for_vague_known() {
    let band = ConfidenceBand::compute("write", "Word");
    assert!(matches!(band, ConfidenceBand::Medium));
}

#[test]
fn unit_confidence_medium_for_clear_unknown() {
    let band = ConfidenceBand::compute(
        "rewrite this paragraph in a professional tone for a board meeting", "Unknown"
    );
    assert!(matches!(band, ConfidenceBand::Medium));
}

#[test]
fn unit_confidence_high_for_clear_known() {
    let band = ConfidenceBand::compute(
        "add three bullet points summarizing the key risks identified in this document",
        "Word"
    );
    assert!(matches!(band, ConfidenceBand::High));
}

// ─── GhostSession ─────────────────────────────────────────────

#[test]
fn unit_ghost_session_starts_streaming() {
    let s = GhostSession::new("test prompt", 11, ConfidenceBand::High);
    assert!(matches!(s.state, SessionState::Streaming));
}

#[test]
fn unit_ghost_session_preserves_prompt() {
    let prompt = "write a haiku about Rust";
    let s = GhostSession::new(prompt, prompt.len(), ConfidenceBand::High);
    assert_eq!(s.original_prompt, prompt);
    assert_eq!(s.prompt_char_count, prompt.len());
}

#[test]
fn unit_ghost_session_cancellation_token_works() {
    let s = GhostSession::new("test", 4, ConfidenceBand::Low);
    assert!(!s.cancel_token.is_cancelled());
    s.cancel_token.cancel();
    assert!(s.cancel_token.is_cancelled());
}

#[test]
fn unit_ghost_session_empty_prompt() {
    // Edge case: empty prompt must not panic
    let s = GhostSession::new("", 0, ConfidenceBand::Low);
    assert_eq!(s.prompt_char_count, 0);
    assert_eq!(s.original_prompt, "");
}

#[test]
fn unit_ghost_session_unicode_prompt() {
    let prompt = "写一首关于编程的诗 🦀🔥";
    let s = GhostSession::new(prompt, prompt.len(), ConfidenceBand::High);
    assert_eq!(s.original_prompt, prompt);
}

#[test]
fn unit_ghost_session_very_long_prompt() {
    let prompt = "a".repeat(100_000);
    let s = GhostSession::new(&prompt, prompt.len(), ConfidenceBand::High);
    assert_eq!(s.prompt_char_count, 100_000);
}

// ─── Config ───────────────────────────────────────────────────

#[test]
fn unit_config_default_is_ollama() {
    let cfg = PhantomConfig::default();
    assert_eq!(cfg.model.provider, "ollama");
}

#[test]
fn unit_config_default_has_model_name() {
    let cfg = PhantomConfig::default();
    assert!(cfg.model.model_name.is_some());
}

#[test]
fn unit_config_swarm_disabled_by_default() {
    let cfg = PhantomConfig::default();
    assert!(!cfg.swarm.enabled, "Swarm must be opt-in, not default");
}

#[test]
fn unit_config_serialization_no_panic() {
    let cfg = PhantomConfig::default();
    let result = toml::to_string_pretty(&cfg);
    assert!(result.is_ok(), "Default config must serialize without error");
}


