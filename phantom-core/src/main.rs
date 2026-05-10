mod ai;
mod api;
mod config;
mod crdt;
mod hotkey;
mod injector;
mod uia;
mod context;
mod swarm;
mod platform;
mod document_context;
mod plugin;
mod mcp_client;
mod mcp_bridge;
mod image_pipeline;
mod ghost_session;
mod governance;
mod yjs_peer;
mod identity;
mod wasm_sandbox;
mod extractors;
mod perf_engine;
mod wgpu_effects;
pub mod chaos;
use identity::IdentityManager;
use wasm_sandbox::WasmPluginRegistry;

use ghost_session::ConfidenceBand;
use governance::{AuditLogger, AuditEvent, AuditOutcome};
use tokio_util::sync::CancellationToken;



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

fn main() -> Result<()> {
    // Run everything on the pre-allocated global runtime to avoid guard generation overhead
    crate::perf_engine::global_runtime().block_on(async_main())
}

async fn async_main() -> Result<()> {
    // Initialize logging (use RUST_LOG=debug for verbose output)
    use tracing_subscriber::{fmt, prelude::*, EnvFilter};
    tracing_subscriber::registry()
        .with(if std::env::var("KAIRO_JSON_LOGS").is_ok() {
            fmt::layer().with_target(true).json().boxed()
        } else {
            fmt::layer().with_target(true).boxed()
        })
        .with(EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| EnvFilter::new("kairo_phantom=info,info")))
        .init();

    info!("👻 Kairo Phantom (Production Engine) starting...");

    // --- CLI Subcommand Routing ---
    let args: Vec<String> = std::env::args().collect();

    if args.iter().any(|a| a == "--version" || a == "-V") {
        println!("kairo-phantom v{}", env!("CARGO_PKG_VERSION"));
        return Ok(());
    }

    // kairo export --format revealjs --input <json> --output <path>
    if args.len() >= 2 && args[1] == "export" {
        let format = args.iter().position(|a| a == "--format")
            .and_then(|i| args.get(i + 1))
            .map(|s| s.as_str())
            .unwrap_or("revealjs");
        let output = args.iter().position(|a| a == "--output")
            .and_then(|i| args.get(i + 1))
            .cloned()
            .unwrap_or_else(|| "output.html".to_string());
        match format {
            "revealjs" => {
                println!("🎨 Kairo Export → Reveal.js: {}", output);
                let status = std::process::Command::new("python")
                    .args(["-m", "revealjs_export", "--output", &output])
                    .current_dir("mcp-servers/office-pptx-bridge")
                    .status()
                    .map_err(|e| anyhow::anyhow!("revealjs_export.py error: {}", e))?;
                if !status.success() {
                    println!("❌ Reveal.js export failed. Check Python dependencies.");
                } else {
                    println!("✅ Exported to: {}", output);
                }
            }
            f => println!("❌ Unknown export format: {}. Supported: revealjs", f),
        }
        return Ok(());
    }

    if args.iter().any(|a| a == "--init-config") {
        let _ = PhantomConfig::load_or_default()?;
        println!("✅ Generated default config at: {}", PhantomConfig::config_path().display());
        println!("\nTo run Kairo Phantom offline with Ollama (default):");
        println!("1. Install Ollama: https://ollama.com/download");
        println!("2. Run: ollama pull qwen2.5-coder:14b");
        println!("3. Start Kairo: kairo-phantom");
        return Ok(());
    }

    // kairo plugin list — show registered plugins from config + auto-discovered ones
    if args.len() >= 3 && args[1] == "plugin" && args[2] == "list" {
        let config = PhantomConfig::load_or_default()?;
        println!("📦 Registered plugins (from config.toml):");
        if config.plugins.is_empty() {
            println!("   (none)");
        }
        for p in &config.plugins { println!("   {}", p); }
        println!("\n📂 Auto-discovered plugins (~/.kairo-phantom/plugins/):");
        let plugin_dir = dirs::home_dir()
            .unwrap_or_default()
            .join(".kairo-phantom")
            .join("plugins");
        if plugin_dir.exists() {
            for entry in std::fs::read_dir(&plugin_dir).into_iter().flatten().flatten() {
                if entry.path().extension().and_then(|e| e.to_str()) == Some("toml") {
                    println!("   {}", entry.path().display());
                }
            }
        } else {
            println!("   (directory does not exist — create it to add plugins)");
        }
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
    
    let mut swarm_engine_obj = swarm::SwarmOrchestrator::new(config.swarm.clone(), fallback_backend.clone());
    let injector = Arc::new(Injector::new(config.typing_delay_ms));
    let uia_reader = Arc::new(UiaReader::new());
    let mut context_engine_obj = ContextEngine::new();
    
    // Load plugins from config
    let mut all_plugin_paths: Vec<String> = config.plugins.clone();

    // Auto-discover plugins from ~/.kairo-phantom/plugins/*.toml
    let auto_plugin_dir = dirs::home_dir()
        .unwrap_or_default()
        .join(".kairo-phantom")
        .join("plugins");
    if auto_plugin_dir.exists() {
        if let Ok(entries) = std::fs::read_dir(&auto_plugin_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) == Some("toml") {
                    let path_str = path.to_string_lossy().to_string();
                    if !all_plugin_paths.contains(&path_str) {
                        info!("🔍 Auto-discovered plugin: {}", path_str);
                        all_plugin_paths.push(path_str);
                    }
                }
            }
        }
    }

    for plugin_path in &all_plugin_paths {
        match std::fs::read_to_string(plugin_path) {
            Ok(content) => {
                match toml::from_str::<crate::plugin::PluginConfig>(&content) {
                    Ok(plugin_cfg) => {
                        info!("🔌 Loading plugin: {}", plugin_cfg.name);
                        if let Some(fingerprinters) = plugin_cfg.fingerprinters {
                            for f in fingerprinters {
                                context_engine_obj.registry.register(Box::new(f));
                            }
                        }
                        if let Some(agents) = plugin_cfg.agents {
                            for a in agents {
                                swarm_engine_obj.registry.register(Arc::new(a));
                            }
                        }
                    }
                    Err(e) => warn!("❌ Failed to parse plugin TOML at {}: {}", plugin_path, e),
                }
            }
            Err(e) => warn!("❌ Failed to read plugin file {}: {}", plugin_path, e),
        }
    }


    let swarm_engine = Arc::new(swarm_engine_obj);
    let context_engine = Arc::new(context_engine_obj);
    let extractor_registry = Arc::new(ExtractorRegistry::with_defaults());

    // ── Advancement 6: Enterprise Agent Identity ─────────────────────────────
    let kairo_config_dir = dirs::home_dir().unwrap_or_default().join(".kairo-phantom");
    let identity_manager = IdentityManager::load(&kairo_config_dir);
    info!("🔑 Agent identity loaded: {}", &identity_manager.identity.agent_id[..16]);

    // ── Advancement 7: WASM Plugin Sandbox ───────────────────────────────────
    let wasm_plugin_dir = kairo_config_dir.join("plugins");
    let mut wasm_registry = WasmPluginRegistry::new(wasm_plugin_dir, None);
    wasm_registry.scan_and_load();
    if wasm_registry.plugin_count() > 0 {
        info!("🔌 WASM plugins loaded: {}", wasm_registry.plugin_count());
        for name in wasm_registry.list_plugins() {
            info!("   • {}", name);
        }
    }
    let _wasm_registry = Arc::new(wasm_registry);

    // Create CRDT session (AI peer with fixed clientID 999)
    let crdt_session = Arc::new(CrdtSession::new(999));
    info!("📄 CRDT session initialized (AI clientID: 999)");

    // Phase 4: Initialize enterprise audit logger
    let audit_logger = Arc::new(AuditLogger::from_env());

    // Phase 2: Initialize MCP bridge registry (discovers PPTX/Figma bridges)
    let mcp_bridge_registry = Arc::new(mcp_bridge::McpBridgeRegistry::from_env());
    if mcp_bridge_registry.has_pptx_bridge() {
        info!("📊 PPTX bridge available — PowerPoint generation enabled");
    }
    if mcp_bridge_registry.has_figma_bridge() {
        info!("🎨 Figma bridge available — Figma injection enabled");
    }

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

    // Phase 3: Shared active session cancellation token
    // When the user presses Esc, we cancel the current token and create a new one next session.
    let active_cancel_token: Arc<std::sync::Mutex<Option<CancellationToken>>> =
        Arc::new(std::sync::Mutex::new(None));
    let active_cancel_clone = Arc::clone(&active_cancel_token);

    // Main Orchestration Loop (High-Concurrency with Ghost Session)
    while let Some(event) = rx.recv().await {
        match event {
            PhantomEvent::HotkeyPressed => {
                info!("============= GHOST SESSION TRIGGERED =============");

                // A. Clean up the 'm' typed during Alt+M
                injector.undo_ghost_char();

                // B. Read Text via UIA
                let raw_text = match uia_reader.get_focused_text() {
                    Ok(t) => t,
                    Err(e) => {
                        warn!("⚠️  UIA read failed: {}. Clipboard fallback...", e);
                        uia_reader.get_clipboard_text().unwrap_or_default()
                    }
                };

                if raw_text.trim().is_empty() {
                    warn!("⚠️  No text in focused element. Type a prompt first.");
                    continue;
                }

                // C. Context Engine Analysis
                let app_ctx: AppContext = context_engine.capture(&raw_text);
                if app_ctx.prompt_text.is_empty() {
                    warn!("⚠️  Prompt empty after extraction.");
                    continue;
                }

                let app_label = app_ctx.environment.label().to_string();
                info!("🧠 App: {} | Prompt: {} chars", app_label, app_ctx.prompt_char_count);

                // D. Build DocumentContext
                let doc_ctx: DocumentContext = if let Some(ref file_path) = app_ctx.file_path {
                    extractor_registry
                        .extract(file_path, &app_ctx.prompt_text, app_ctx.active_slide)
                        .unwrap_or_else(|| DocumentContext::from_raw_text(
                            &app_ctx.prompt_text,
                            &app_ctx.document_text,
                            app_ctx.environment.to_doc_kind(),
                        ))
                } else {
                    DocumentContext::from_raw_text(
                        &app_ctx.prompt_text,
                        &app_ctx.document_text,
                        app_ctx.environment.to_doc_kind(),
                    )
                };

                info!("📑 DocKind: {} | outline={} | slides={:?}",
                    doc_ctx.doc_kind.human_name(),
                    doc_ctx.outline.len(),
                    doc_ctx.total_slides
                );

                // E. Swarm Brain Routing
                let (target_backend, agent_profile) = swarm_engine.route(&doc_ctx).await;
                let _agent_id = agent_profile.agent_type.clone();

                // Advancement 6: RBAC check — verify this agent is allowed on this document
                let kairo_agent_id = &identity_manager.identity.agent_id;
                let doc_path_str = doc_ctx.file_path.as_ref()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default();
                if !identity_manager.check_permission(kairo_agent_id, &doc_path_str) {
                    warn!("⚠️  RBAC: agent '{}' denied access to '{}'", &kairo_agent_id[..8], doc_path_str);
                    continue;
                }
                let system_prompt = agent_profile.system_directive;
                let prompt_text = doc_ctx.prompt_text.clone();
                let prompt_char_count = doc_ctx.prompt_char_count;
                let _original_prompt = prompt_text.clone();

                // F. Phase 3: Create Ghost Session with CancellationToken
                let confidence = ConfidenceBand::compute(
                    &prompt_text,
                    doc_ctx.doc_kind.human_name()
                );
                info!("👻 Ghost Session starting | Confidence: {}", confidence.label());

                // Phase 4: Audit log — session started (now with agent identity)
                let kairo_agent_id_for_log = identity_manager.identity.agent_id.clone();
                audit_logger.log_ghost_session(
                    AuditEvent::GhostSessionStarted,
                    AuditOutcome::Pending,
                    &app_label,
                    &kairo_agent_id_for_log,
                    &config.model.model_name.as_deref().unwrap_or("default"),
                    prompt_char_count,
                );

                let cancel_token = CancellationToken::new();
                let child_token = cancel_token.child_token();

                // Store cancel token so Esc can cancel it
                {
                    let mut lock = active_cancel_clone.lock().unwrap();
                    if let Some(old_token) = lock.take() {
                        old_token.cancel(); // cancel any previous session
                    }
                    *lock = Some(cancel_token.clone());
                }

                // G. Spawn AI Streaming Task (cancellable)
                let (token_tx, mut token_rx) = mpsc::channel::<String>(200);
                let prompt_clone = prompt_text.clone();
                let cloud_fallback_clone = cloud_fallback.clone();
                let child_token_clone = child_token.clone();

                tokio::spawn(async move {
                    tokio::select! {
                        result = target_backend.stream_complete(&system_prompt, &prompt_clone, token_tx.clone()) => {
                            if let Err(e) = result {
                                warn!("🤖 Streaming error: {}", e);
                                if let Some(fallback) = cloud_fallback_clone {
                                    warn!("🔄 Cloud fallback...");
                                    let _ = fallback.stream_complete(&system_prompt, &prompt_clone, token_tx).await;
                                }
                            }
                        }
                        _ = child_token_clone.cancelled() => {
                            info!("🛑 Stream cancelled by user (Esc)");
                        }
                    }
                });

                // H. Process Stream — inject tokens as they arrive
                let injector_clone = Arc::clone(&injector);
                let mut first_token = true;
                let mut full_response = String::new();
                let mut buffer = String::new();
                let mut replaced = false;
                let mut was_cancelled = false;

                loop {
                    tokio::select! {
                        maybe_token = token_rx.recv() => {
                            match maybe_token {
                                None => break, // stream ended
                                Some(token) => {
                                    buffer.push_str(&token);

                                    if first_token {
                                        if buffer.len() > 15 || buffer.contains("[REPLACE]") {
                                            first_token = false;
                                            let clean_buf = buffer.replace("[REPLACE]", "").trim_start().to_string();

                                            info!("♻️  Erasing prompt ({} chars)...", prompt_char_count);
                                            injector_clone.erase_prompt(prompt_char_count);
                                            tokio::time::sleep(std::time::Duration::from_millis(50)).await;

                                            if !clean_buf.is_empty() {
                                                if !injector_clone.inject_via_clipboard(&clean_buf) {
                                                    injector_clone.type_text(&clean_buf);
                                                }
                                                full_response.push_str(&clean_buf);
                                            }
                                            replaced = true;
                                        }
                                    } else {
                                        injector_clone.type_text(&token);
                                        full_response.push_str(&token);
                                    }
                                }
                            }
                        }
                        _ = child_token.cancelled() => {
                            info!("🛑 Ghost session cancelled mid-stream");
                            was_cancelled = true;
                            break;
                        }
                    }
                }

                // Fallback: small buffer never triggered
                if !replaced && !buffer.is_empty() && !was_cancelled {
                    let clean_buf = buffer.replace("[REPLACE]", "").trim_start().to_string();
                    injector_clone.erase_prompt(prompt_char_count);
                    tokio::time::sleep(std::time::Duration::from_millis(50)).await;
                    if !injector_clone.inject_via_clipboard(&clean_buf) {
                        injector_clone.type_text(&clean_buf);
                    }
                    full_response.push_str(&clean_buf);
                }

                // I. Phase 3: Record undo history
                if !full_response.is_empty() && !was_cancelled {
                    // Store history for Ctrl+Z (agent-aware undo)
                    // In a full implementation the overlay frontend reads this
                    info!("📝 Ghost session complete: {} chars injected", full_response.len());
                }

                // J. Sync to CRDT
                if !full_response.is_empty() {
                    crdt_session.insert_ai_text(&full_response);
                }

                // K. Phase 4: Audit log outcome
                let outcome = if was_cancelled {
                    AuditOutcome::Cancelled
                } else {
                    AuditOutcome::Success
                };
                audit_logger.log_ghost_session(
                    if was_cancelled { AuditEvent::GhostSessionCancelled } else { AuditEvent::GhostSessionAccepted },
                    outcome,
                    &app_label,
                    "auto",
                    &config.model.model_name.as_deref().unwrap_or("default"),
                    full_response.len(),
                );
            }
            PhantomEvent::UserTyping => {
                info!("🛑 User typing — cancelling active ghost session");
                let lock = active_cancel_token.lock().unwrap();
                if let Some(ref token) = *lock {
                    token.cancel();
                }
            }
            _ => {}
        }
    }

    Ok(())
}
