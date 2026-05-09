mod ai;
mod api;
mod config;
mod crdt;
mod hotkey;
mod injector;
mod uia;
mod context;
mod swarm;
mod platform; // Cross-platform accessibility layer (v3.0)


use anyhow::Result;
use std::sync::Arc;
use tokio::sync::mpsc;
use tracing::{info, warn};
use tracing_subscriber::EnvFilter;

use api::ApiState;
use config::PhantomConfig;
use crdt::CrdtSession;
use hotkey::HotkeyWatcher;
use injector::Injector;
use uia::UiaReader;
use context::ContextEngine;
use ai::build_backend;
use platform::AccessibilityReader; // trait must be in scope to call methods


/// Message bus between all threads
#[derive(Debug, Clone)]
pub enum PhantomEvent {
    /// User triggered the hotkey — materialize AI suggestion
    HotkeyPressed,
    /// UIA reader captured the current focused element text
    ContextCaptured(String),
    /// AI returned a suggestion
    SuggestionReady(String),
    /// User started typing — abort current AI stream
    UserTyping,
    /// Shutdown signal
    Shutdown,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging (use RUST_LOG=debug for verbose output)
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("kairo_phantom=info".parse()?))
        .init();

    info!("👻 Kairo Phantom (Production Engine) starting...");

    // Load config from ~/.kairo-phantom/config.toml
    let config = PhantomConfig::load_or_default()?;
    info!("⚙️  Config loaded: provider={} model={}", config.model.provider, config.model.model_name.as_deref().unwrap_or("default"));

    // Initialize Core Components
    let fallback_backend = build_backend(&config.model)?;
    let swarm_engine = Arc::new(swarm::SwarmOrchestrator::new(config.swarm.clone(), fallback_backend.clone()));
    let injector = Arc::new(Injector::new(config.typing_delay_ms));
    let uia_reader = Arc::new(UiaReader::new());
    let context_engine = Arc::new(ContextEngine::new());
    
    // Create CRDT session (AI peer with fixed clientID 999)
    let crdt_session = Arc::new(CrdtSession::new(999));
    info!("📄 CRDT session initialized (AI clientID: 999)");

    // Main event channel — all threads talk through this
    let (tx, mut rx) = mpsc::channel::<PhantomEvent>(64);

    // Spawn hotkey listener thread
    let hotkey_tx = tx.clone();
    let hotkey_combo = config.hotkey.clone();
    tokio::task::spawn_blocking(move || {
        let watcher = HotkeyWatcher::new(hotkey_combo, hotkey_tx);
        watcher.run();
    });

    info!("👀 Kairo Phantom ready — press configured hotkey to materialize");

    // Start background HTTP API (for visual overlay)
    let api_state = ApiState {
        crdt: Arc::clone(&crdt_session),
        uia: Arc::clone(&uia_reader),
        injector: Arc::clone(&injector),
        ai: Arc::clone(&fallback_backend),
    };
    tokio::spawn(async move {
        api::start_api_server(api_state).await;
    });

    // Main Orchestration Loop (High-Concurrency)
    while let Some(event) = rx.recv().await {
        match event {
            PhantomEvent::HotkeyPressed => {
                info!("============= MATERIALIZE TRIGGERED =============");
                
                // A. Clean up the 'm' typed during Alt+M (before anything else)
                injector.undo_ghost_char();
                
                // B. Read Text via UIA
                let raw_text = match uia_reader.get_focused_text() {
                    Ok(t) => t,
                    Err(e) => {
                        warn!("⚠️  Failed to read text via UIA: {}. Trying clipboard fallback...", e);
                        uia_reader.get_clipboard_text().unwrap_or_default()
                    }
                };

                if raw_text.trim().is_empty() {
                    warn!("⚠️  No text found in focused element. Type a prompt first.");
                    continue;
                }

                // C. Context Engine Analysis
                let ctx = context_engine.capture(&raw_text);
                
                if ctx.prompt_text.is_empty() {
                    warn!("⚠️  Prompt empty after extraction.");
                    continue;
                }

                info!("🧠 Env detected: {} | Prompt: {} chars", ctx.environment.label(), ctx.prompt_char_count);

                // D. Swarm Brain Routing
                // The Brain analyzes the context and prompt, then delegates to a specialized Agent
                let (target_backend, agent_profile) = swarm_engine.route(&ctx).await;
                let system_prompt = agent_profile.system_directive;

                // E. Stream & Inject

                let (token_tx, mut token_rx) = mpsc::channel::<String>(100);
                
                let prompt_clone = ctx.prompt_text.clone();
                
                // Spawn AI Request using the dynamically routed backend
                tokio::spawn(async move {
                    if let Err(e) = target_backend.stream_complete(&system_prompt, &prompt_clone, token_tx).await {
                        warn!("🤖 Streaming error: {}", e);
                    }
                });

                // Process Stream
                let injector_clone = Arc::clone(&injector);
                let mut first_token = true;
                let mut full_response = String::new();
                let mut buffer = String::new();
                let mut replaced = false;

                while let Some(token) = token_rx.recv().await {
                    buffer.push_str(&token);
                    
                    // Wait for enough tokens to check for [REPLACE] tag
                    if first_token {
                        if buffer.len() > 15 || buffer.contains("[REPLACE]") {
                            first_token = false;
                            
                            let clean_buffer = if buffer.contains("[REPLACE]") {
                                buffer.replace("[REPLACE]", "").trim_start().to_string()
                            } else {
                                buffer.clone()
                            };

                            info!("♻️  Erasing prompt...");
                            injector_clone.erase_prompt(ctx.prompt_char_count);
                            
                            // Small delay to ensure erasure completes
                            tokio::time::sleep(std::time::Duration::from_millis(50)).await;
                            
                            // Inject initial buffer
                            if !clean_buffer.is_empty() {
                                // Try fast clipboard paste first
                                if !injector_clone.inject_via_clipboard(&clean_buffer) {
                                    injector_clone.type_text(&clean_buffer);
                                }
                                full_response.push_str(&clean_buffer);
                            }
                            replaced = true;
                        }
                    } else {
                        // Not first token, just stream immediately char by char
                        injector_clone.type_text(&token);
                        full_response.push_str(&token);
                    }
                }
                
                // Fallback if the model never output enough tokens to trigger first_token block
                if !replaced && !buffer.is_empty() {
                     let clean_buffer = buffer.replace("[REPLACE]", "").trim_start().to_string();
                     injector_clone.erase_prompt(ctx.prompt_char_count);
                     tokio::time::sleep(std::time::Duration::from_millis(50)).await;
                     
                     if !injector_clone.inject_via_clipboard(&clean_buffer) {
                         injector_clone.type_text(&clean_buffer);
                     }
                     full_response.push_str(&clean_buffer);
                }

                // F. Sync to CRDT
                crdt_session.insert_ai_text(&full_response);
                info!("💾 Synced {} chars to CRDT", full_response.len());
            }
            PhantomEvent::UserTyping => {
                info!("🛑 User started typing — aborting current stream");
                // The actual abort logic would require cancellation tokens
                // passed to the AI backend and tokio task
            }
            _ => {}
        }
    }

    Ok(())
}
