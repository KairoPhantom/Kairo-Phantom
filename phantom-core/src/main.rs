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
mod document_context; // Structured document understanding (v3.0)


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
use context::{ContextEngine, AppContext};
use ai::build_backend;
use platform::AccessibilityReader; // trait must be in scope to call methods
use document_context::{DocumentContext, ExtractorRegistry};

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

/// Checks if Ollama is running at the given base URL.
async fn check_ollama_health(base_url: &str) -> bool {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .unwrap_or_default();
    client.get(&format!("{}/api/tags", base_url))
        .send().await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging (use RUST_LOG=debug for verbose output)
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("kairo_phantom=info".parse()?))
        .init();

    info!("👻 Kairo Phantom (Production Engine) starting...");

    // Check for --init-config flag
    if std::env::args().any(|arg| arg == "--init-config") {
        let _ = PhantomConfig::load_or_default()?;
        println!("✅ Generated default config at: {}", PhantomConfig::config_path().display());
        println!("\nTo run Kairo Phantom offline with Ollama (default):");
        println!("1. Install Ollama: https://ollama.com/download");
        println!("2. Run: ollama pull qwen2.5-coder:14b");
        println!("3. Start Kairo: kairo-phantom");
        return Ok(());
    }

    // Load config from ~/.kairo-phantom/config.toml
    let config = PhantomConfig::load_or_default()?;
    info!("⚙️  Config loaded: provider={} model={}", config.model.provider, config.model.model_name.as_deref().unwrap_or("default"));

    // Phase 3: Ollama Health Check
    if config.model.provider == "ollama" {
        let base_url = config.model.base_url.as_deref().unwrap_or("http://localhost:11434");
        if !check_ollama_health(base_url).await {
            println!("⚠  Ollama not detected. Get offline AI in 2 commands:");
            println!("   winget install Ollama.Ollama   (Windows)");
            println!("   brew install ollama            (macOS)");
            println!("   curl -fsSL https://ollama.ai/install.sh | sh  (Linux)");
            println!("   Then: ollama pull qwen2.5-coder:14b");
            println!();
            println!("   Or add an API key to ~/.kairo-phantom/config.toml for cloud mode.");
            println!("   Kairo will retry Ollama every 30s...");
        } else {
            info!("✅ Ollama running at {}. Offline mode active.", base_url);
        }
    }

    // Initialize Core Components
    let fallback_backend = build_backend(&config.model)?;
    
    // Build optional cloud fallback
    let cloud_fallback = if let Some(ref fb_conf) = config.fallback {
        build_backend(fb_conf).ok()
    } else {
        None
    };
    
    let swarm_engine = Arc::new(swarm::SwarmOrchestrator::new(config.swarm.clone(), fallback_backend.clone()));
    let injector = Arc::new(Injector::new(config.typing_delay_ms));
    let uia_reader = Arc::new(UiaReader::new());
    let context_engine = Arc::new(ContextEngine::new());
    let extractor_registry = Arc::new(ExtractorRegistry::with_defaults());
    
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

    // Start background HTTP API (for visual overlay and MCP tools)
    let mcp_agent_override = Arc::new(std::sync::Mutex::new(None));
    
    let api_state = ApiState {
        crdt: Arc::clone(&crdt_session),
        uia: Arc::clone(&uia_reader),
        injector: Arc::clone(&injector),
        ai: Arc::clone(&fallback_backend),
        context_engine: Arc::clone(&context_engine),
        extractor_registry: Arc::clone(&extractor_registry),
        swarm_engine: Arc::clone(&swarm_engine),
        mcp_agent_override: Arc::clone(&mcp_agent_override),
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
                let app_ctx: AppContext = context_engine.capture(&raw_text);
                
                if app_ctx.prompt_text.is_empty() {
                    warn!("⚠️  Prompt empty after extraction.");
                    continue;
                }

                info!("🧠 Env detected: {} | Prompt: {} chars", app_ctx.environment.label(), app_ctx.prompt_char_count);

                // D. v3.0: Build rich DocumentContext via ExtractorRegistry
                // If we resolved a file path from the window title, try to extract
                // structured content (headings, tables, slide count). If that fails
                // or no file path was found, fall back to plain UIA text.
                let doc_ctx: DocumentContext = if let Some(ref file_path) = app_ctx.file_path {
                    extractor_registry
                        .extract(file_path, &app_ctx.prompt_text, app_ctx.active_slide)
                        .unwrap_or_else(|| {
                            tracing::debug!("📄 Extraction failed for {:?}, using raw text fallback", file_path);
                            DocumentContext::from_raw_text(
                                &app_ctx.prompt_text,
                                &app_ctx.document_text,
                                app_ctx.environment.to_doc_kind(),
                            )
                        })
                } else {
                    DocumentContext::from_raw_text(
                        &app_ctx.prompt_text,
                        &app_ctx.document_text,
                        app_ctx.environment.to_doc_kind(),
                    )
                };

                info!("📑 DocKind: {} | outline={} items | slides={:?}",
                    doc_ctx.doc_kind.human_name(),
                    doc_ctx.outline.len(),
                    doc_ctx.total_slides
                );

                // E. Swarm Brain Routing
                // Brain analyzes DocumentContext (not just raw text), routes to specialized Agent
                let (target_backend, agent_profile) = swarm_engine.route(&doc_ctx).await;
                let system_prompt = agent_profile.system_directive;
                let prompt_text = doc_ctx.prompt_text.clone();
                let prompt_char_count = doc_ctx.prompt_char_count;

                // F. Stream & Inject
                let (token_tx, mut token_rx) = mpsc::channel::<String>(100);
                
                let prompt_clone = prompt_text.clone();
                let cloud_fallback_clone = cloud_fallback.clone();
                
                // Spawn AI Request using the dynamically routed backend
                tokio::spawn(async move {
                    if let Err(e) = target_backend.stream_complete(&system_prompt, &prompt_clone, token_tx.clone()).await {
                        warn!("🤖 Streaming error: {}", e);
                        
                        if let Some(fallback) = cloud_fallback_clone {
                            warn!("🔄 Retrying with fallback provider...");
                            if let Err(e2) = fallback.stream_complete(&system_prompt, &prompt_clone, token_tx).await {
                                warn!("🤖 Fallback streaming error: {}", e2);
                            }
                        }
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
                            injector_clone.erase_prompt(prompt_char_count);
                            
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
                     injector_clone.erase_prompt(prompt_char_count);
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
