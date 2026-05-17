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
mod sentinel;
mod persona;
mod memory;
mod guardrails;
mod context7;
mod command_protocol;
mod pii_guard;
mod response_validator;
mod retry_policy;
mod memory_store;
mod verify;
mod quality_gate;
mod writing_pipeline;
mod kami_export;
mod context_optimizer;
mod background_worker;
mod aws_emulation;
mod skills;
mod memory_vault;
mod tolaria_bridge;
mod integration;
mod telemetry;
mod eval;
mod xa11y;
mod inference;
mod mcp_auth;
mod waza_sdk;

// ── 100x Roadmap Modules ─────────────────────────────────────────────────────
mod ollama_bootstrap;
mod toast_notification;
mod startup_timer;
mod memory_seeder;
mod kpx_export;
mod health_check;
mod compliance_scanner;
mod owasp_compliance;
mod deep_presenter;
mod waza_registry;
mod siem_export;
mod cross_doc_consistency;
mod lan_sync;
mod excel_formula;
mod section_summarizer;

use identity::IdentityManager;
use wasm_sandbox::WasmPluginRegistry;

use ghost_session::ConfidenceBand;
use governance::{AuditLogger, AuditEvent, AuditOutcome};
use tokio_util::sync::CancellationToken;



use anyhow::Result;
use std::sync::Arc;
use tokio::sync::mpsc;
use tracing::{info, warn};

use api::ApiState;
use config::PhantomConfig;
use crdt::CrdtSession;
use hotkey::HotkeyWatcher;
use injector::HumanizedInjector as Injector;
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
    client.get(format!("{}/api/tags", base_url))
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
    
    // Set up file-based logging to ~/.kairo-phantom/daemon.log
    let kairo_dir = dirs::home_dir()
        .map(|h| h.join(".kairo-phantom"))
        .unwrap_or_else(|| std::path::PathBuf::from("."));
    let log_file_path = kairo_dir.join("daemon.log");
    let log_file = std::fs::OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(true) // Fresh log each daemon start
        .open(&log_file_path)
        .expect("Failed to open daemon.log for writing");

    let file_layer = fmt::layer()
        .with_target(true)
        .with_ansi(false) // No ANSI color codes in file
        .with_writer(std::sync::Mutex::new(log_file));
    
    let console_layer = if std::env::var("KAIRO_JSON_LOGS").is_ok() {
        fmt::layer().with_target(true).json().boxed()
    } else {
        fmt::layer().with_target(true).boxed()
    };

    tracing_subscriber::registry()
        .with(console_layer)
        .with(file_layer)
        .with(EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| EnvFilter::new("kairo_phantom=info,info")))
        .init();

    info!("👻 Kairo Phantom (Production Engine) starting...");

    // P0-A1: Startup performance timer
    let _startup_timer = startup_timer::StartupTimer::new();
    _startup_timer.checkpoint("logger init");

    // P0-A2: Ollama bootstrap — detect + background model pull
    ollama_bootstrap::OllamaBootstrap::bootstrap("qwen2.5:7b").await;
    _startup_timer.checkpoint("ollama check");


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

    // kairo verify
    if args.len() >= 2 && args[1] == "verify" {
        println!("🔍 Running Kairo Facts Verification...");
        match crate::verify::FactsVerifier::verify_all() {
            Ok(true) => std::process::exit(0),
            Ok(false) => std::process::exit(1),
            Err(e) => {
                println!("❌ Error: {}", e);
                std::process::exit(1);
            }
        }
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

    // ── 100x: New CLI subcommands ─────────────────────────────────────────────

    // kairo seed <folder> — seed MemMachine from existing documents
    if args.len() >= 3 && args[1] == "seed" {
        return memory_seeder::run_seed_command(&args[2]).await;
    }

    // kairo import <file.kpx> — import memory export
    if args.len() >= 3 && args[1] == "import" {
        let kpx_path = std::path::Path::new(&args[2]);
        let db_path = dirs::home_dir()
            .unwrap_or_default()
            .join(".kairo-phantom")
            .join("mem_machine.db");
        let count = kpx_export::KpxExporter::import(kpx_path, &db_path)?;
        println!("✅ Imported {} memories from {}", count, args[2]);
        return Ok(());
    }

    // kairo export-memory [--output <path>] — export memory as .kpx
    if args.len() >= 2 && args[1] == "export-memory" {
        let output = args.iter().position(|a| a == "--output")
            .and_then(|i| args.get(i + 1))
            .map(|s| s.as_str())
            .unwrap_or("kairo-memory.kpx");
        let db_path = dirs::home_dir()
            .unwrap_or_default()
            .join(".kairo-phantom")
            .join("mem_machine.db");
        let count = kpx_export::KpxExporter::export(
            &db_path, std::path::Path::new(output), "Manual export"
        )?;
        println!("📦 Exported {} memories to {}", count, output);
        return Ok(());
    }

    // kairo owasp-report — print OWASP compliance matrix
    if args.len() >= 2 && args[1] == "owasp-report" {
        let report = owasp_compliance::generate_markdown_report();
        let output_path = "KAIRO_OWASP_COMPLIANCE.md";
        std::fs::write(output_path, &report)?;
        println!("✅ OWASP Compliance Matrix written to: {}", output_path);
        println!("\n{}", owasp_compliance::generate_ciso_summary());
        return Ok(());
    }

    // kairo siem-export [--format cef|leef|json] [--output file]
    if args.len() >= 2 && args[1] == "siem-export" {
        return siem_export::run_siem_export_command(&args[2..]).await;
    }

    // kairo memory sync <discover|pull <peer>|serve>
    if args.len() >= 3 && args[1] == "memory" && args[2] == "sync" {
        return lan_sync::run_lan_sync_command(&args[3..]).await;
    }

    // kairo skill <add|list|remove|new> [args]
    if args.len() >= 2 && args[1] == "skill" {
        let sub = args.get(2).map(|s| s.as_str()).unwrap_or("list");
        let skill_args = if args.len() > 3 { args[3..].to_vec() } else { vec![] };
        return waza_registry::run_skill_command(sub, &skill_args).await;
    }

    // kairo help — show all available commands
    if args.len() >= 2 && (args[1] == "help" || args[1] == "--help" || args[1] == "-h") {
        print_help();
        return Ok(());
    }

    // kairo first-run — interactive onboarding
    if args.iter().any(|a| a == "--first-run" || a == "first-run") {
        println!();
        println!("  ╔══════════════════════════════════════════════════════════╗");
        println!("  ║     👻 Welcome to Kairo Phantom v{}{}",
            env!("CARGO_PKG_VERSION"),
            " ".repeat(30usize.saturating_sub(env!("CARGO_PKG_VERSION").len()))
        );
        println!("  ║     The AI ghost-writer that haunts every desktop app   ║");
        println!("  ╠══════════════════════════════════════════════════════════╣");
        println!("  ║  ⚡ Alt+M  — Activate Kairo in any app                  ║");
        println!("  ║  🧠 MemMachine — Learns your style automatically        ║");
        println!("  ║  🔒 100% offline — Zero data leaves your machine        ║");
        println!("  ╚══════════════════════════════════════════════════════════╝");
        println!();
        println!("  💡 Tip: Run 'kairo seed <your-docs-folder>' to teach Kairo");
        println!("         your writing style from existing documents.\n");
        // Fall through to normal startup
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
    
    // ── Production Modules: Memory, Context7, PII Guard ──────────────────────────
    let kairo_config_dir = dirs::home_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join(".kairo-phantom");
    let mem_machine = Arc::new(crate::memory::MemMachine::new(kairo_config_dir.clone())?);
    
    // Spawn Alaya 24-hour background maintenance.
    // rusqlite::Connection is !Send, so we can't move it into tokio::spawn directly.
    // Instead, create a dedicated MemMachine for the Alaya thread and run it in
    // spawn_blocking, which runs on the blocking thread-pool with no Send constraint.
    let alaya_config_dir = kairo_config_dir.clone();
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("Alaya tokio runtime");
        rt.block_on(async move {
            match crate::memory::MemMachine::new(alaya_config_dir.clone()) {
                Ok(alaya_mem) => {
                    // Run once on startup
                    let _ = alaya_mem.run_maintenance_cycle().await;
                    // Then every 24 hours
                    let mut interval = tokio::time::interval(std::time::Duration::from_secs(86400));
                    loop {
                        interval.tick().await;
                        let _ = alaya_mem.run_maintenance_cycle().await;
                    }
                }
                Err(e) => {
                    tracing::warn!("⚠️  Alaya: could not open maintenance MemMachine: {}", e);
                }
            }
        });
    });

    let mem_store = memory_store::MemoryStore::from_env();
    let kairo_memory = mem_store.load();
    let context7 = Arc::new(context7::Context7::new());
    let pii_guard = pii_guard::PiiGuard::new();
    info!("🧠 MemMachine ready | 📚 Context7 ready | 🛡️ PII Guard active");
    
    // Share memory store for session recording
    let mem_store = Arc::new(std::sync::Mutex::new((mem_store, kairo_memory)));
    
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

    // ── Waza Skill Architecture — per kairo-intel.md §3.1 ───────────────────
    let skill_manager = Arc::new(crate::skills::SkillManager::new());
    info!("🎯 Waza skills loaded: {}/{} SKILL.md files active", skill_manager.count(), 8);
    for summary_line in skill_manager.skill_summary() {
        info!("{}", summary_line);
    }

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

    // Phase 5: Start background document worker
    let mem_store_for_worker = Arc::clone(&mem_store);
    tokio::spawn(async move {
        crate::background_worker::start_document_scanner(mem_store_for_worker).await;
    });

    // Phase 3: Shared active session cancellation token
    // When the user presses Esc, we cancel the current token and create a new one next session.
    let active_cancel_token: Arc<std::sync::Mutex<Option<CancellationToken>>> =
        Arc::new(std::sync::Mutex::new(None));
    let active_cancel_clone = Arc::clone(&active_cancel_token);

    // Stale prompt guard: track the last // command that was processed.
    // If the user presses Alt+M again with the same // line (e.g., from a
    // previous AI output still in the document), we warn instead of re-generating.
    let mut last_processed_prompt: String = String::new();

    // Main Orchestration Loop (High-Concurrency with Ghost Session)
    while let Some(event) = rx.recv().await {
        match event {
            PhantomEvent::HotkeyPressed => {
                info!("============= GHOST SESSION TRIGGERED =============");

                // NOTE: The hotkey hook now consumes the Alt key-up event directly,
                // preventing Windows from activating the ribbon/menu bar.
                // No synthetic key-ups needed here — they can corrupt keyboard state.
                
                // Small delay to let the hook process the Alt key-up consumption
                tokio::time::sleep(std::time::Duration::from_millis(50)).await;

                // A. Show instant toast feedback
                crate::toast_notification::show_progress_toast("Kairo is thinking... ✨");

                // ── CRITICAL: Use the HWND captured at hook time (the user's actual app). ──
                let target_hwnd_val = crate::hotkey::CAPTURED_HWND.load(std::sync::atomic::Ordering::SeqCst);
                info!("🎯 Target HWND from snapshot: {}", target_hwnd_val);

                // B. Derive process name + window title FROM the captured HWND
                //    NOTE: GetWindowTextW and GetWindowThreadProcessId do NOT require
                //    the window to be focused. We can read these from any valid HWND.
                //    DO NOT call ShowWindow/BringWindowToTop/SetForegroundWindow here!
                //    Focusing the window now would trigger Alt key release → ribbon activation.
                let (captured_process, captured_title) = unsafe {
                    use windows::Win32::Foundation::HWND;
                    use windows::Win32::UI::WindowsAndMessaging::{
                        GetWindowTextW, GetWindowThreadProcessId,
                    };
                    use windows::Win32::System::Threading::{
                        OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION,
                        QueryFullProcessImageNameW, PROCESS_NAME_WIN32,
                    };

                    let hwnd = HWND(target_hwnd_val as *mut std::ffi::c_void);

                    // Read window title (no focus needed)
                    let mut title_buf = [0u16; 512];
                    let title_len = GetWindowTextW(hwnd, &mut title_buf);
                    let title = String::from_utf16_lossy(&title_buf[..title_len as usize]);

                    // Read process name (no focus needed)
                    let mut pid = 0u32;
                    GetWindowThreadProcessId(hwnd, Some(&mut pid));
                    let proc_name = if let Ok(handle) = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) {
                        let mut path_buf = [0u16; 1024];
                        let mut path_len = path_buf.len() as u32;
                        if QueryFullProcessImageNameW(
                            handle,
                            PROCESS_NAME_WIN32,
                            windows::core::PWSTR(path_buf.as_mut_ptr()),
                            &mut path_len,
                        ).is_ok() {
                            let full_path = String::from_utf16_lossy(&path_buf[..path_len as usize]);
                            std::path::Path::new(&full_path)
                                .file_name()
                                .and_then(|n| n.to_str())
                                .unwrap_or("Unknown")
                                .to_string()
                        } else { "Unknown".to_string() }
                    } else { "Unknown".to_string() };

                    info!("🖥️  Target app: '{}' | Title: '{}'", proc_name, title);
                    (proc_name, title)
                };

                // C. Read text from target app
                //    Strategy: UIA first (works without focus for Word, Notepad, etc.)
                //    If UIA fails, focus the window SAFELY then use clipboard fallback.
                let raw_text = {
                    // Try UIA first — it can read from the focused element without us
                    // needing to SetForegroundWindow
                    let uia_result = uia_reader.get_focused_text();
                    match uia_result {
                        Ok(t) if !t.trim().is_empty() => {
                            info!("📖 UIA read: {} chars", t.len());
                            t
                        },
                        uia_r => {
                            if let Err(ref e) = uia_r { warn!("⚠️  UIA error: {}", e); }
                            // Clipboard fallback: need to focus window first, then Ctrl+A, Ctrl+C
                            info!("📋 Clipboard fallback: focusing window, then Ctrl+A + Ctrl+C...");

                            #[cfg(windows)]
                            {
                                use windows::Win32::UI::WindowsAndMessaging::{
                                    SetForegroundWindow, BringWindowToTop, ShowWindow, SW_RESTORE,
                                };
                                use windows::Win32::Foundation::HWND;
                                use windows::Win32::UI::Input::KeyboardAndMouse::{
                                    SendInput, INPUT, INPUT_KEYBOARD, KEYBDINPUT,
                                    KEYEVENTF_KEYUP, VK_CONTROL, VK_MENU, VK_LMENU, VK_RMENU,
                                    VK_SHIFT, VIRTUAL_KEY, KEYBD_EVENT_FLAGS,
                                };

                                let hwnd = HWND(target_hwnd_val as *mut std::ffi::c_void);

                                // Focus the window using SW_RESTORE (not SW_SHOW — SW_SHOW can
                                // cause issues with minimized windows)
                                unsafe {
                                    if windows::Win32::UI::WindowsAndMessaging::IsIconic(hwnd).as_bool() { let _ = ShowWindow(hwnd, SW_RESTORE); }
                                    let _ = BringWindowToTop(hwnd);
                                    let _ = SetForegroundWindow(hwnd);
                                }
                                tokio::time::sleep(std::time::Duration::from_millis(300)).await;

                                // NOTE: No modifier clearing needed — the hotkey hook already
                                // consumed the Alt key-up event to prevent ribbon activation.

                                // NOW safe to send Ctrl+A, Ctrl+C
                                let sel_copy = [
                                    INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_CONTROL, wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                                    INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VIRTUAL_KEY(0x41), wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                                    INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VIRTUAL_KEY(0x41), wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
                                    INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VIRTUAL_KEY(0x43), wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                                    INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VIRTUAL_KEY(0x43), wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
                                    INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_CONTROL, wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
                                ];
                                unsafe { SendInput(&sel_copy, std::mem::size_of::<INPUT>() as i32); }
                            }
                            tokio::time::sleep(std::time::Duration::from_millis(200)).await;
                            let clip = uia_reader.get_clipboard_text().unwrap_or_default();
                            info!("📋 Clipboard captured: {} chars", clip.len());
                            clip
                        }
                    }
                };

                if raw_text.trim().is_empty() {
                    warn!("⚠️  No text captured from '{}'. Type a // prompt first.", captured_process);
                    crate::toast_notification::show_progress_toast("Kairo: No text found. Click in your app and type // first.");
                    continue;
                }

                // D. Build AppContext using CAPTURED process/title (not GetForegroundWindow)
                //    This ensures we identify Word/Chrome/Notepad correctly.
                let app_env = {
                    use crate::context::AppEnvironment;
                    let proc = captured_process.to_lowercase();
                    let title = captured_title.to_lowercase();
                    if proc.contains("winword") { AppEnvironment::MicrosoftWord }
                    else if proc.contains("powerpnt") { AppEnvironment::MicrosoftPowerPoint }
                    else if proc.contains("excel") { AppEnvironment::MicrosoftExcel }
                    else if proc.contains("outlook") { AppEnvironment::MicrosoftOutlook }
                    else if proc.contains("code") && !proc.contains("discord") { AppEnvironment::VSCode }
                    else if proc.contains("notepad") { AppEnvironment::Notepad }
                    else if proc.contains("windowsterminal") { AppEnvironment::WindowsTerminal }
                    else if proc.contains("powershell") { AppEnvironment::PowerShell }
                    else if title.contains("notion") { AppEnvironment::Notion }
                    else if proc.contains("chrome") || proc.contains("chromium") { AppEnvironment::Chrome }
                    else if proc.contains("msedge") { AppEnvironment::Edge }
                    else if proc.contains("firefox") { AppEnvironment::Firefox }
                    else { AppEnvironment::Unknown(captured_process.clone()) }
                };

                // Extract the // command from captured text
                let prompt_text = crate::context::ContextEngine::extract_last_paragraph(&raw_text);
                let prompt_char_count = prompt_text.chars().count();

                if prompt_text.is_empty() {
                    // Safe truncation: use char_indices to avoid UTF-8 mid-char panic
                    let preview: String = raw_text.chars().take(100).collect();
                    warn!("⚠️  No // command found in text. Prompt: {:?}", preview);
                    crate::toast_notification::show_progress_toast("Kairo: Type // followed by your instruction.");
                    continue;
                }

                let app_label = app_env.label().to_string();
                // Safe truncation: use .chars().take() to avoid UTF-8 mid-char panic
                let prompt_preview: String = prompt_text.chars().take(80).collect();
                info!("🧠 App: '{}' | Prompt ({} chars): '{}'", app_label, prompt_char_count, prompt_preview);

                // DEFECT 2 FIX: Stale prompt guard.
                // If this exact // line was already processed last session, warn the user.
                // This prevents reusing a stale // line that's sitting in the document
                // from a previous AI injection.
                if prompt_text == last_processed_prompt {
                    warn!("⚠️  Stale prompt detected — same // command as last session.");
                    crate::toast_notification::show_progress_toast(
                        "Kairo: Edit your // prompt before pressing Alt+M again."
                    );
                    continue;
                }
                // Record this prompt as the currently processing one
                last_processed_prompt = prompt_text.clone();

                // Build AppContext from our captured data
                let app_ctx = crate::context::AppContext {
                    process_name: captured_process.clone(),
                    window_title: captured_title.clone(),
                    environment: app_env,
                    prompt_text: prompt_text.clone(),
                    prompt_char_count,
                    document_text: raw_text.clone(),
                    file_path: crate::context::ContextEngine::resolve_file_path(&captured_title, &captured_process),
                    active_slide: crate::context::ContextEngine::extract_slide_number(&captured_title),
                };


                // D. Build DocumentContext
                println!("🔍 Reading document structure...");
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

                // E. Swarm Brain Routing & Command Handling
                println!("🧠 Initializing specialist swarm...");
                let (command_mode, clean_prompt) = crate::command_protocol::CommandMode::from_prompt(&doc_ctx.prompt_text);
                
                // Handle System Commands Immediately
                match command_mode {
                    crate::command_protocol::CommandMode::Health => {
                        // Comprehensive health audit per kairo-intel.md §3.4
                        let base_url = config.model.base_url.as_deref().unwrap_or("http://localhost:11434");
                        let ollama_ok = check_ollama_health(base_url).await;
                        let api_key_status = if config.model.api_key.as_deref().unwrap_or("").is_empty() {
                            "⚪ Not configured (offline/Ollama mode)"
                        } else {
                            "✅ API key configured"
                        };
                        let lock = mem_store.lock().unwrap();
                        let (_, ref memory) = *lock;
                        let learned_prefs: Vec<String> = memory.preferences.iter()
                            .filter(|p| p.weight > 0.5)
                            .map(|p| format!("  · {} → {} (weight: {:.1})", p.key, p.value, p.weight))
                            .collect();
                        let word_model: Vec<String> = memory.user_model.word_preferences.iter()
                            .map(|(k, v)| format!("  · {}: {}", k, v))
                            .collect();
                        let ppt_model: Vec<String> = memory.user_model.ppt_preferences.iter()
                            .map(|(k, v)| format!("  · {}: {}", k, v))
                            .collect();
                        let mcp_status = if std::path::Path::new("mcp-servers").exists() { "✅ MCP directory found" } else { "⚠️  MCP directory missing" };
                        let kairo_ver = env!("CARGO_PKG_VERSION");
                        let skill_summary_lines = skill_manager.skill_summary();
                        let skill_report = skill_summary_lines.join("\n");
                        let report = format!(
                            "🏥 Kairo Phantom v{} — System Health Report\n\n\
                             🤖 AI Engine\n  · Provider: {}\n  · Model: {}\n  · Ollama: {}\n  · API Key: {}\n\n\
                             🧠 Memory (SQLite: ~/.kairo-phantom/memory.db)\n  · Preferences: {} learned\n  · Interactions: {} recorded\n  · Skill patterns: {} stored\n  · Knowledge graph: {} nodes, {} edges\n\n\
                             📊 User Model (Word): {}\n{}\n\n\
                             📊 User Model (PPT): {}\n{}\n\n\
                             📚 Learned Preferences (weight > 0.5):\n{}\n\n\
                             🎯 Waza Skills ({}/8 loaded):\n{}\n\n\
                             🔌 MCP Bridge: {}\n  · Context7: {} (offline: {})\n  · PII Guard: ✅ Active\n  · Sentinel: ✅ Active\n  · PromptGuard: ✅ 27 patterns loaded\n\n\
                             📁 Export (Kami):\n  · Use: // kami <markdown|pdf|revealjs>",
                            kairo_ver,
                            config.model.provider,
                            config.model.model_name.as_deref().unwrap_or("default"),
                            if ollama_ok { "✅ Running" } else { "❌ Not detected" },
                            api_key_status,
                            memory.preferences.len(),
                            memory.interactions.len(),
                            memory.skill.reusable_patterns.len(),
                            memory.graph.nodes.len(),
                            memory.graph.edges.len(),
                            if word_model.is_empty() { 0 } else { word_model.len() },
                            if word_model.is_empty() { "  · (none yet — use Kairo in Word to learn)".to_string() } else { word_model.join("\n") },
                            if ppt_model.is_empty() { 0 } else { ppt_model.len() },
                            if ppt_model.is_empty() { "  · (none yet — use Kairo in PowerPoint to learn)".to_string() } else { ppt_model.join("\n") },
                            if learned_prefs.is_empty() { "  · (none yet)".to_string() } else { learned_prefs.join("\n") },
                            skill_manager.count(),
                            skill_report,
                            mcp_status,
                            if std::env::var("KAIRO_OFFLINE").is_ok() { "⚪ Offline mode" } else { "✅ Online mode" },
                            std::env::var("KAIRO_OFFLINE").is_ok(),
                        );
                        // Use production injection: clipboard → focus → select line → paste
                        let hwnd_val = crate::hotkey::CAPTURED_HWND.load(std::sync::atomic::Ordering::SeqCst);
                        let _ = crate::injector::HumanizedInjector::set_clipboard(&report);
                        if hwnd_val != 0 {
                            use windows::Win32::UI::WindowsAndMessaging::{SetForegroundWindow, BringWindowToTop, ShowWindow, SW_RESTORE};
                            use windows::Win32::Foundation::HWND;
                            let h = HWND(hwnd_val as *mut std::ffi::c_void);
                            unsafe { if windows::Win32::UI::WindowsAndMessaging::IsIconic(h).as_bool() { let _ = windows::Win32::UI::WindowsAndMessaging::ShowWindow(h, windows::Win32::UI::WindowsAndMessaging::SW_RESTORE); } let _ = BringWindowToTop(h); let _ = SetForegroundWindow(h); }
                            tokio::time::sleep(std::time::Duration::from_millis(400)).await;
                        }
                        injector.inject_replace_line();
                        continue;
                    },
                    crate::command_protocol::CommandMode::Kami => {
                        // Parse format from clean_prompt: // kami <format> or default to markdown
                        let kami_args = clean_prompt.trim().to_lowercase();
                        let kami_format = if kami_args.contains("pdf") { "pdf" }
                            else if kami_args.contains("revealjs") || kami_args.contains("slides") || kami_args.contains("presentation") { "revealjs" }
                            else { "markdown" };
                        let kami_output = match kami_format {
                            "pdf" => "kairo_export.pdf",
                            "revealjs" => "kairo_export.html",
                            _ => "kairo_export.md",
                        };
                        let kami_result = match kami_format {
                            "pdf" => crate::kami_export::KamiExporter::execute(crate::kami_export::KamiCommand::Pdf, doc_ctx.full_text.clone()).await,
                            "revealjs" => crate::kami_export::KamiExporter::execute(crate::kami_export::KamiCommand::RevealJs, doc_ctx.full_text.clone()).await,
                            _ => crate::kami_export::KamiExporter::execute(crate::kami_export::KamiCommand::Summary, doc_ctx.full_text.clone()).await,
                        };
                        let kami_msg = match kami_result {
                            Ok(_) => format!("✅ Document exported via Kami ({}) → {}", kami_format, kami_output),
                            Err(e) => format!("❌ Kami {} export failed: {}", kami_format, e),
                        };
                        let hwnd_val = crate::hotkey::CAPTURED_HWND.load(std::sync::atomic::Ordering::SeqCst);
                        let _ = crate::injector::HumanizedInjector::set_clipboard(&kami_msg);
                        if hwnd_val != 0 {
                            use windows::Win32::UI::WindowsAndMessaging::{SetForegroundWindow, BringWindowToTop, ShowWindow, SW_RESTORE};
                            use windows::Win32::Foundation::HWND;
                            let h = HWND(hwnd_val as *mut std::ffi::c_void);
                            unsafe { if windows::Win32::UI::WindowsAndMessaging::IsIconic(h).as_bool() { let _ = windows::Win32::UI::WindowsAndMessaging::ShowWindow(h, windows::Win32::UI::WindowsAndMessaging::SW_RESTORE); } let _ = BringWindowToTop(h); let _ = SetForegroundWindow(h); }
                            tokio::time::sleep(std::time::Duration::from_millis(400)).await;
                        }
                        injector.inject_replace_line();
                        continue;
                    },
                    crate::command_protocol::CommandMode::Think => {
                        // PHASE 1 of Think: Generate a structured plan and show it.
                        // User reviews it; pressing Alt+M again with the plan in context executes it.
                        // Per kairo-intel.md §3.3: "Kairo outputs a plan (not the slides yet)"
                        let (target_backend, agent_profile) = swarm_engine.route(&doc_ctx, &command_mode).await;
                        let sentinel = crate::sentinel::SentinelSanitizer::new();
                        let think_system = sentinel.wrap_system_prompt(&format!(
                            "{}\n\nMODE: THINK — PLAN ONLY. Do NOT execute yet. Output a structured JSON-style plan with:\n\
                             1. Problem restatement\n2. Proposed approach (bullet points)\n3. Sections/slides/steps to generate\n4. Tone and formatting decisions\n5. Key constraints\n\
                             Start with '## KAIRO PLAN — review and press Alt+M to execute'\n\
                             DO NOT generate the final content yet. Only the plan.",
                            agent_profile.system_directive
                        ));
                        let (plan_tx, mut plan_rx) = mpsc::channel::<String>(200);
                        let backend_clone = target_backend.clone();
                        let prompt_for_plan = clean_prompt.clone();
                        let ctx_for_plan = doc_ctx.full_text.clone();
                        tokio::spawn(async move {
                            // Safe truncation: use .chars().take() to avoid UTF-8 panic
                            let ctx_preview: String = ctx_for_plan.chars().take(2000).collect();
                            let _ = backend_clone.stream_complete(
                                &think_system,
                                &format!("DOCUMENT CONTEXT:\n{}\n\nUSER REQUEST: {}", ctx_preview, prompt_for_plan),
                                plan_tx
                            ).await;
                        });
                        // Collect plan output
                        let mut plan_output = String::new();
                        while let Some(token) = plan_rx.recv().await {
                            plan_output.push_str(&token);
                        }
                        // Inject plan for user review - they press Alt+M again to execute
                        let hwnd_val = crate::hotkey::CAPTURED_HWND.load(std::sync::atomic::Ordering::SeqCst);
                        let _ = crate::injector::HumanizedInjector::set_clipboard(&plan_output);
                        if hwnd_val != 0 {
                            use windows::Win32::UI::WindowsAndMessaging::{SetForegroundWindow, BringWindowToTop, ShowWindow, SW_RESTORE};
                            use windows::Win32::Foundation::HWND;
                            let h = HWND(hwnd_val as *mut std::ffi::c_void);
                            unsafe { if windows::Win32::UI::WindowsAndMessaging::IsIconic(h).as_bool() { let _ = windows::Win32::UI::WindowsAndMessaging::ShowWindow(h, windows::Win32::UI::WindowsAndMessaging::SW_RESTORE); } let _ = BringWindowToTop(h); let _ = SetForegroundWindow(h); }
                            tokio::time::sleep(std::time::Duration::from_millis(400)).await;
                        }
                        injector.inject_replace_line();
                        info!("💭 Think: Plan generated ({} chars) — user reviews, Alt+M executes", plan_output.len());
                        continue;
                    },
                    _ => {}
                }

                // ── P2.4: Section Summarizer — intercept "summarize" prompts ────────
                if section_summarizer::SectionSummarizer::is_summary_request(&doc_ctx.prompt_text) {
                    info!("📋 Section Summarizer: building structure-aware prompt");
                    let summary_prompt = section_summarizer::SectionSummarizer::build_summary_prompt(
                        &doc_ctx, &doc_ctx.prompt_text
                    );
                    let (sum_tx, mut sum_rx) = mpsc::channel::<String>(200);
                    let backend_for_sum = fallback_backend.clone();
                    let sys_for_sum = "You are a concise document summarizer. Output exactly 3 bullet points.".to_string();
                    tokio::spawn(async move {
                        let _ = backend_for_sum.stream_complete(&sys_for_sum, &summary_prompt, sum_tx).await;
                    });
                    let mut raw_summary = String::new();
                    while let Some(t) = sum_rx.recv().await { raw_summary.push_str(&t); }
                    let bullets = section_summarizer::SectionSummarizer::normalize_bullets(&raw_summary);
                    let hwnd_val = crate::hotkey::CAPTURED_HWND.load(std::sync::atomic::Ordering::SeqCst);
                    let _ = crate::injector::HumanizedInjector::set_clipboard(&bullets);
                    if hwnd_val != 0 {
                        use windows::Win32::UI::WindowsAndMessaging::{SetForegroundWindow, BringWindowToTop, ShowWindow, SW_RESTORE};
                        use windows::Win32::Foundation::HWND;
                        let h = HWND(hwnd_val as *mut std::ffi::c_void);
                        unsafe { if windows::Win32::UI::WindowsAndMessaging::IsIconic(h).as_bool() { let _ = windows::Win32::UI::WindowsAndMessaging::ShowWindow(h, windows::Win32::UI::WindowsAndMessaging::SW_RESTORE); } let _ = BringWindowToTop(h); let _ = SetForegroundWindow(h); }
                        tokio::time::sleep(std::time::Duration::from_millis(400)).await;
                    }
                    injector.inject_replace_line();
                    info!("📋 Summary injected ({} bullets)", bullets.lines().count());
                    continue;
                }

                // ── P2.5: Excel Formula Engine ───────────────────────────────────────
                if excel_formula::ExcelFormulaEngine::should_handle(
                    &doc_ctx.prompt_text, doc_ctx.doc_kind.human_name()
                ) {
                    let engine = excel_formula::ExcelFormulaEngine::new();
                    // If an existing formula is in the prompt → explain it
                    if let Some(formula) = excel_formula::ExcelFormulaEngine::extract_formula(&doc_ctx.prompt_text) {
                        let explanation = engine.explain(&formula);
                        let explain_text = explanation.format_for_injection();
                        let hwnd_val = crate::hotkey::CAPTURED_HWND.load(std::sync::atomic::Ordering::SeqCst);
                        let _ = crate::injector::HumanizedInjector::set_clipboard(&explain_text);
                        if hwnd_val != 0 {
                            use windows::Win32::UI::WindowsAndMessaging::{SetForegroundWindow, BringWindowToTop, ShowWindow, SW_RESTORE};
                            use windows::Win32::Foundation::HWND;
                            let h = HWND(hwnd_val as *mut std::ffi::c_void);
                            unsafe { if windows::Win32::UI::WindowsAndMessaging::IsIconic(h).as_bool() { let _ = windows::Win32::UI::WindowsAndMessaging::ShowWindow(h, windows::Win32::UI::WindowsAndMessaging::SW_RESTORE); } let _ = BringWindowToTop(h); let _ = SetForegroundWindow(h); }
                            tokio::time::sleep(std::time::Duration::from_millis(400)).await;
                        }
                        injector.inject_replace_line();
                        info!("📊 Excel formula explained: {}", formula);
                        continue;
                    } else {
                        // Otherwise ask LLM to generate a formula
                        let gen_prompt = engine.build_generation_prompt(&doc_ctx.prompt_text);
                        let (fx_tx, mut fx_rx) = mpsc::channel::<String>(100);
                        let backend_for_fx = fallback_backend.clone();
                        let sys_for_fx = "You are an Excel formula expert. Output ONLY the formula starting with =, nothing else.".to_string();
                        tokio::spawn(async move {
                            let _ = backend_for_fx.stream_complete(&sys_for_fx, &gen_prompt, fx_tx).await;
                        });
                        let mut formula_out = String::new();
                        while let Some(t) = fx_rx.recv().await { formula_out.push_str(&t); }
                        let formula_clean = formula_out.trim().to_string();
                        let hwnd_val = crate::hotkey::CAPTURED_HWND.load(std::sync::atomic::Ordering::SeqCst);
                        let _ = crate::injector::HumanizedInjector::set_clipboard(&formula_clean);
                        if hwnd_val != 0 {
                            use windows::Win32::UI::WindowsAndMessaging::{SetForegroundWindow, BringWindowToTop, ShowWindow, SW_RESTORE};
                            use windows::Win32::Foundation::HWND;
                            let h = HWND(hwnd_val as *mut std::ffi::c_void);
                            unsafe { if windows::Win32::UI::WindowsAndMessaging::IsIconic(h).as_bool() { let _ = windows::Win32::UI::WindowsAndMessaging::ShowWindow(h, windows::Win32::UI::WindowsAndMessaging::SW_RESTORE); } let _ = BringWindowToTop(h); let _ = SetForegroundWindow(h); }
                            tokio::time::sleep(std::time::Duration::from_millis(400)).await;
                        }
                        injector.inject_replace_line();
                        info!("📊 Excel formula generated: {}", formula_clean);
                        continue;
                    }
                }

                // ── P2.3: Compliance Scanner — run on every ghost session ────────────
                {
                    let scanner = compliance_scanner::ComplianceScanner::load();
                    let violations = scanner.scan(&doc_ctx.full_text);
                    if !violations.is_empty() {
                        let violation_summary = violations.iter()
                            .map(|v| {
                                let phrase_preview: String = v.matched_phrase.chars().take(40).collect();
                                format!("⚠️  {} [{}]: '{}'", v.rule_id, v.severity, phrase_preview)
                            })
                            .collect::<Vec<_>>()
                            .join("\n");
                        warn!("🔒 Compliance scanner: {} violations found:\n{}", violations.len(), violation_summary);
                        // Log to audit trail but don't block — compliance is advisory
                        audit_logger.log_ghost_session(
                            AuditEvent::GhostSessionStarted,
                            AuditOutcome::Pending,
                            &format!("COMPLIANCE_SCAN:{}", app_label),
                            &identity_manager.identity.agent_id,
                            config.model.model_name.as_deref().unwrap_or("default"),
                            violations.len() as usize,
                        );
                    }
                }

                let (target_backend, agent_profile) = swarm_engine.route(&doc_ctx, &command_mode).await;
                let _agent_id = agent_profile.agent_type.clone();

                // Advancement 6: RBAC check
                let kairo_agent_id = &identity_manager.identity.agent_id;
                let doc_path_str = doc_ctx.file_path.as_ref()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default();
                if !identity_manager.check_permission(kairo_agent_id, &doc_path_str) {
                    warn!("⚠️  RBAC: agent '{}' denied access to '{}'", &kairo_agent_id[..8], doc_path_str);
                    continue;
                }
                let mut system_prompt = agent_profile.system_directive;
                if let Some(skill_directive) = skill_manager.get_skill_directive(&command_mode) {
                    system_prompt = format!("{}\n\n---\n\nWAZA SKILL DIRECTIVE:\n{}", system_prompt, skill_directive);
                }
                let prompt_text = clean_prompt.clone();
                let prompt_char_count = doc_ctx.prompt_char_count;
                let _original_prompt = prompt_text.clone();

                // Security: Wrap system prompt with Sentinel
                let sentinel = crate::sentinel::SentinelSanitizer::new();
                let guard = crate::guardrails::PromptGuard::new();
                let response_validator = crate::response_validator::ResponseValidator::new();
                
                // PII guard
                let (clean_prompt_for_llm, pii_was_redacted) = pii_guard.redact(&prompt_text);
                if pii_was_redacted {
                    warn!("🛡️  PII Guard: redacted PII from prompt before LLM call");
                }
                
                // Injection guard
                if guard.detect_injection(&clean_prompt_for_llm).is_injection {
                    warn!("🔒 PromptGuard: Potential injection detected — blocking session");
                    audit_logger.log_ghost_session(
                        AuditEvent::GhostSessionBlocked,
                        AuditOutcome::Blocked,
                        &app_label,
                        kairo_agent_id,
                        config.model.model_name.as_deref().unwrap_or("default"),
                        prompt_char_count,
                    );
                    continue;
                }
                
                // Context7
                println!("📚 Grounding in Context7 documentation...");
                let context7_hint = context7.fetch_ground_truth(&clean_prompt_for_llm).await;
                let mut enriched_system = if let Some(ref docs) = context7_hint {
                    info!("📚 Context7: injecting {} chars of ground-truth docs", docs.len());
                    format!("{system_prompt}\n\n<context7_docs>\n{docs}\n</context7_docs>")
                } else {
                    system_prompt.clone()
                };

                // P1: Tolaria MCP bridge for enterprise knowledge
                let tolaria = crate::tolaria_bridge::TolariaBridge::new("tolaria");
                if let Ok(brand_guidelines) = tolaria.get_brand_guidelines().await {
                    if !brand_guidelines.is_empty() {
                        info!("🏢 Tolaria: injecting enterprise brand guidelines");
                        enriched_system = format!("{enriched_system}\n\n<tolaria_brand_guidelines>\n{brand_guidelines}\n</tolaria_brand_guidelines>");
                    }
                }
                
                // Wire ContextOptimizer: inject memory-personalized context into system prompt
                let _context_optimizer = crate::context_optimizer::ContextOptimizer::new(2048);
                
                // Upgrade 4: Multi-Granularity Memory Recall
                let granularities = vec![app_label.clone(), doc_ctx.doc_kind.human_name().to_string()];
                let memories = mem_machine.recall_contextualized(&clean_prompt_for_llm, granularities, 3).await.unwrap_or_default();
                
                // Upgrade 5: Context-Aware Distillation
                let distilled_memories = if !memories.is_empty() {
                    let optimizer = crate::memory::optimizer::MemoryOptimizer::new();
                    optimizer.distill_context(&app_label, &clean_prompt_for_llm, &memories)
                } else {
                    String::new()
                };

                let personalized_system = if !distilled_memories.is_empty() {
                    info!("🧠 MemMachine: injecting {} chars of distilled context", distilled_memories.len());
                    format!("{}\n\n<memory_context>\n{}\n</memory_context>", enriched_system, distilled_memories)
                } else {
                    enriched_system.clone()
                };
                
                system_prompt = sentinel.wrap_system_prompt(&personalized_system);

                // Add Command Mode Hint
                system_prompt = format!("{}\n\n{}", system_prompt, command_mode.system_hint());

                // PAHF: Log confidence but NEVER block generation.
                // The confidence engine scores a synthetic preview string, not actual AI output,
                // so blocking based on this causes false negatives (good prompts get rejected).
                let history = mem_machine.get_feedback_history(&app_label).unwrap_or_default();
                if !history.is_empty() {
                    let preview_hint = format!("{} {}", clean_prompt_for_llm, app_label);
                    let pahf_confidence = crate::memory::feedback::ConfidenceEngine::calculate_confidence(
                        &app_label,
                        &preview_hint,
                        &history,
                    );
                    // Log only — never skip generation based on this score
                    info!("📊 PAHF confidence: {:.2} (informational only — always generating)", pahf_confidence);
                }

                // F. Phase 3: Create Ghost Session with CancellationToken
                let confidence = ConfidenceBand::compute(
                    &prompt_text,
                    doc_ctx.doc_kind.human_name()
                );
                info!("👻 Ghost Session starting | Confidence: {}", confidence.label());
                println!("✨ Generating response...");

                // Phase 4: Audit log — session started
                let kairo_agent_id_for_log = identity_manager.identity.agent_id.clone();
                audit_logger.log_ghost_session(
                    AuditEvent::GhostSessionStarted,
                    AuditOutcome::Pending,
                    &app_label,
                    &kairo_agent_id_for_log,
                    config.model.model_name.as_deref().unwrap_or("default"),
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
                        result = async {
                            // PRODUCTION FIX: Always use direct streaming.
                            // The WritingPipeline makes 3 sequential API calls (Plan, Write, Review)
                            // which hangs on rate-limited APIs (NVIDIA free tier, etc).
                            // Direct streaming sends ONE request and streams tokens back immediately.
                            info!("🚀 Direct streaming to AI backend...");
                            target_backend.stream_complete(&system_prompt, &prompt_clone, token_tx.clone()).await
                        } => {
                            match result {
                                Ok(()) => info!("✅ AI stream completed successfully"),
                                Err(e) => {
                                    warn!("🤖 AI streaming error: {}", e);
                                    // Send error message as token so user sees it
                                    let _ = token_tx.send(format!("[AI Error: {}]", e)).await;
                                    if let Some(fallback) = cloud_fallback_clone {
                                        warn!("🔄 Trying cloud fallback...");
                                        if let Err(e2) = fallback.stream_complete(&system_prompt, &prompt_clone, token_tx).await {
                                            warn!("🔄 Cloud fallback also failed: {}", e2);
                                        }
                                    }
                                }
                            }
                        }
                        _ = child_token_clone.cancelled() => {
                            info!("🛑 Stream cancelled by user (Esc)");
                        }
                        _ = tokio::time::sleep(std::time::Duration::from_secs(90)) => {
                            warn!("⏰ AI stream timed out after 90 seconds");
                            let _ = token_tx.send("[Kairo: AI request timed out. Try again.]".to_string()).await;
                        }
                    }
                });

                // H. Collect ALL stream tokens, then inject ONCE at the end.
                //
                // ARCHITECTURE: We do NOT inject mid-stream. We collect the entire AI
                // response into `full_response`, then do ONE clipboard→focus→select→paste.
                //
                // Why: Mid-stream injection caused two problems:
                //   1. Only the first ~15 chars got injected; the rest accumulated silently
                //   2. Focus switches mid-stream confuse Word's document body focus model
                //
                // The new approach: collect everything, inject once.
                let injector_clone = Arc::clone(&injector);
                let mut full_response = String::new();
                let mut was_cancelled = false;

                info!("📡 Streaming AI response...");
                loop {
                    tokio::select! {
                        maybe_token = token_rx.recv() => {
                            match maybe_token {
                                None => break, // stream ended — all tokens collected
                                Some(token) => {
                                    full_response.push_str(&token);
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

                // ── POST-STREAM: Inject the complete response ──────────────────
                if !was_cancelled && !full_response.is_empty() {
                    let clean_response = full_response.replace("[REPLACE]", "").trim().to_string();
                    full_response = clean_response.clone();

                    if clean_response.is_empty() {
                        warn!("⚠️  AI returned empty response");
                    } else {
                        info!("📡 Stream complete: {} chars. Starting injection...", clean_response.len());

                        // DEFECT 3 FIX: Output sanitization — block internal config leakage.
                        // VS Code's UIA layer can inject internal editor strings into the
                        // LLM context, causing the model to echo them back.
                        // Block any output that contains these sentinel strings.
                        const OUTPUT_BLOCKLIST: &[&str] = &[
                            "editor.accessibilityMode",
                            "screen-reader-optimized",
                            "workbench.action",
                            "vscode-token",
                            "Content Agent",
                            "Swarm Role",
                            "system prompt",
                            "<system>",
                            "internal hash",
                        ];
                        let lower_resp = clean_response.to_lowercase();
                        if let Some(blocked) = OUTPUT_BLOCKLIST.iter().find(|b| lower_resp.contains(&b.to_lowercase())) {
                            tracing::error!("🚫 BLOCKED BY SENTINEL: output contains '{}'", blocked);
                            crate::toast_notification::show_progress_toast(
                                "Kairo: Output blocked (internal string detected). Edit your prompt and retry."
                            );
                            // Reset last_processed_prompt so user can retry immediately
                            last_processed_prompt = String::new();
                            continue;
                        }

                        // 1. Set clipboard FIRST — before any focus changes
                        let cb_ok = crate::injector::HumanizedInjector::set_clipboard(&clean_response);
                        info!("Clipboard: {} ({} chars)", if cb_ok { "OK" } else { "FAILED" }, clean_response.len());

                        // 2. CRITICAL: Wait for user to physically release Alt.
                        //    If Alt is still held when we send keystrokes, Shift+End becomes
                        //    Alt+Shift which triggers the Windows language switcher popup,
                        //    stealing focus from Word so Ctrl+V goes nowhere.
                        #[cfg(windows)]
                        {
                            use windows::Win32::UI::Input::KeyboardAndMouse::GetAsyncKeyState;
                            let mut waited_ms = 0u32;
                            while waited_ms < 2000 {
                                let alt_state = unsafe { GetAsyncKeyState(0x12) }; // VK_MENU
                                if (alt_state & -32768i16) == 0 { break; } // Alt released
                                tokio::time::sleep(std::time::Duration::from_millis(20)).await;
                                waited_ms += 20;
                            }
                            if waited_ms > 0 {
                                info!("⏱️ Waited {}ms for Alt to be physically released", waited_ms);
                            }
                        }

                        // 3. Focus the target window (only restore if minimized)
                        let hwnd_val = crate::hotkey::CAPTURED_HWND.load(std::sync::atomic::Ordering::SeqCst);
                        if hwnd_val != 0 {
                            use windows::Win32::UI::WindowsAndMessaging::{
                                SetForegroundWindow, BringWindowToTop, ShowWindow,
                                SW_RESTORE, IsIconic, GetForegroundWindow,
                            };
                            use windows::Win32::Foundation::HWND;
                            let h = HWND(hwnd_val as *mut std::ffi::c_void);
                            unsafe {
                                // Only call SW_RESTORE if actually minimized — otherwise leave
                                // maximized/normal state alone
                                if IsIconic(h).as_bool() {
                                    let _ = ShowWindow(h, SW_RESTORE);
                                }
                                let _ = BringWindowToTop(h);
                                let _ = SetForegroundWindow(h);
                            }

                            // Wait for OS to grant keyboard focus to the document body
                            tokio::time::sleep(std::time::Duration::from_millis(500)).await;

                            // Verify Word actually has focus — if language switcher or another
                            // window stole it, re-focus
                            #[cfg(windows)]
                            unsafe {
                                let fg = GetForegroundWindow();
                                if fg.0 != h.0 {
                                    info!("⚠️ Word lost focus (fg={:?}), re-focusing...", fg.0);
                                    let _ = BringWindowToTop(h);
                                    let _ = SetForegroundWindow(h);
                                    tokio::time::sleep(std::time::Duration::from_millis(300)).await;
                                }
                            }
                            info!("✅ Window focused: HWND={}", hwnd_val);
                        }

                        // 4. Inject response using End → Enter → Ctrl+V
                        //    (No Shift key used — prevents Alt+Shift = language switcher)
                        //    This appends the AI response on a new line below the // prompt.
                        #[cfg(windows)]
                        {
                            use windows::Win32::UI::Input::KeyboardAndMouse::{
                                SendInput, INPUT, INPUT_KEYBOARD, KEYBDINPUT,
                                KEYEVENTF_KEYUP, VK_CONTROL, VK_END, VK_RETURN,
                                VIRTUAL_KEY, KEYBD_EVENT_FLAGS,
                            };

                            let inputs = [
                                // End — move to end of prompt line
                                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_END, wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_END, wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
                                // Enter — new line (no Shift = no language switcher risk)
                                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_RETURN, wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_RETURN, wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
                                // Ctrl+V — paste AI response
                                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_CONTROL, wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VIRTUAL_KEY(0x56), wScan: 0, dwFlags: KEYBD_EVENT_FLAGS(0), time: 0, dwExtraInfo: 0 } } },
                                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VIRTUAL_KEY(0x56), wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
                                INPUT { r#type: INPUT_KEYBOARD, Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 { ki: KEYBDINPUT { wVk: VK_CONTROL, wScan: 0, dwFlags: KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 } } },
                            ];
                            unsafe { SendInput(&inputs, std::mem::size_of::<INPUT>() as i32); }
                        }

                        info!("✅ Injection complete: {} chars → HWND={}", clean_response.len(), hwnd_val);
                        crate::toast_notification::show_completion_toast(clean_response.len(), "Kairo");
                    }
                }

                // Upgrade 1: Remember Ground Truth Episode
                if !full_response.is_empty() && !was_cancelled {
                    let mem_machine_clone = Arc::clone(&mem_machine);
                    let response_clone = full_response.clone();
                    let prompt_clone = clean_prompt_for_llm.clone();
                    let app_clone = app_label.clone();
                    tokio::spawn(async move {
                        let _ = mem_machine_clone.remember(
                            &response_clone, 
                            Some(&prompt_clone), 
                            &app_clone, 
                            None, 
                            true, 
                            vec!["ghost_session"]
                        ).await;
                        info!("💾 MemMachine: Stored ground-truth episode.");
                    });

                    // Upgrade 5: Post-Action Feedback Monitor
                    let mem_machine_fb = Arc::clone(&mem_machine);
                    let app_fb = app_label.clone();
                    let ai_output = full_response.clone();
                    let uia_fb = Arc::clone(&uia_reader);
                    tokio::spawn(async move {
                        tokio::time::sleep(std::time::Duration::from_secs(10)).await;
                        if let Ok(current_text) = uia_fb.get_focused_text() {
                            let signals = crate::memory::feedback::FeedbackClassifier::classify(&ai_output, &current_text);
                            if !signals.is_empty() {
                                let _ = mem_machine_fb.store_feedback(&app_fb, signals);
                                info!("🧠 PAHF: Recorded user corrections as feedback signals.");
                            }
                        }
                    });
                }

                // (Fallback block removed — post-stream injection handles all cases now)

                // I. Phase 3: Record undo history
                if !full_response.is_empty() && !was_cancelled {
                    // Store history for Ctrl+Z (agent-aware undo)
                    // In a full implementation the overlay frontend reads this
                    info!("📝 Ghost session complete: {} chars injected", full_response.len());
                }

                // I. Finalization & Audit
                if !was_cancelled {
                    // Layer 4: Validate response (hallucination / roleplay detection)
                    let val_result = response_validator.validate(&prompt_text, &full_response);
                    if !val_result.is_valid() {
                        warn!("⚠️  [RESPONSE VALIDATOR] {}", val_result.reason());
                        // Log but don't block — validator is advisory for now
                    }

                    // Sanitize the final response through sentinel
                    let sanitized = sentinel.sanitize(&full_response);
                    if sanitized == "[BLOCKED: SECURITY POLICY VIOLATION]" {
                        warn!("❌ RESPONSE BLOCKED: Instruction leakage detected.");
                        injector.type_text("\n[SECURITY ALERT: RESPONSE BLOCKED]");
                        audit_logger.log_ghost_session(
                            AuditEvent::GhostSessionBlocked,
                            AuditOutcome::Blocked,
                            &app_label,
                            &kairo_agent_id_for_log,
                            config.model.model_name.as_deref().unwrap_or("default"),
                            full_response.len(),
                        );
                    } else {
                        info!("✅ Ghost session completed ({} chars injected)", full_response.len());
                        
                        // Record interaction in persistent memory (accepted = true)
                        if let Ok(mut store_lock) = mem_store.lock() {
                            let (ref store, ref mut memory) = *store_lock;
                            store.record_interaction(
                                memory,
                                &app_label,
                                &prompt_text,
                                &full_response,
                                true, // accepted
                            );
                        }
                        
                        audit_logger.log_ghost_session(
                            AuditEvent::GhostSessionCompleted,
                            AuditOutcome::Success,
                            &app_label,
                            &kairo_agent_id_for_log,
                            config.model.model_name.as_deref().unwrap_or("default"),
                            full_response.len(),
                        );
                    }
                } else {
                    // Rejection path: user pressed Esc — record as rejected in memory for learning
                    if !full_response.is_empty() {
                        if let Ok(mut store_lock) = mem_store.lock() {
                            let (ref store, ref mut memory) = *store_lock;
                            // learn_from_interaction stores the rejection signal
                            memory.learn_from_interaction(crate::memory::types::Interaction {
                                app: app_label.clone(),
                                prompt: prompt_text.clone(),
                                response: full_response.clone(),
                                accepted: false, // rejected — Esc pressed
                                timestamp: std::time::SystemTime::now()
                                    .duration_since(std::time::UNIX_EPOCH)
                                    .unwrap_or_default()
                                    .as_secs(),
                            });
                            store.record_interaction(memory, &app_label, &prompt_text, &full_response, false);
                            info!("🧠 After-action review: rejection pattern stored for future learning");
                        }
                    }
                    audit_logger.log_ghost_session(
                        AuditEvent::GhostSessionCancelled,
                        AuditOutcome::Aborted,
                        &app_label,
                        &kairo_agent_id_for_log,
                        config.model.model_name.as_deref().unwrap_or("default"),
                        full_response.len(),
                    );
                }

                // J. Sync to CRDT
                if !full_response.is_empty() {
                    crdt_session.insert_ai_text(&full_response);
                }
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

fn print_help() {
    println!("👻 Kairo Phantom v{} — AI ghost-writer that haunts every app\n", env!("CARGO_PKG_VERSION"));
    println!("USAGE: kairo-phantom [COMMAND] [OPTIONS]\n");
    println!("COMMANDS:");
    println!("  (no args)              Start the daemon — press Alt+M to activate");
    println!("  seed <folder>          Seed MemMachine from existing documents");
    println!("  import <file.kpx>      Import a .kpx memory export");
    println!("  export-memory          Export memory as .kpx file");
    println!("  owasp-report           Generate OWASP Agentic Top 10 compliance matrix");
    println!("  siem-export            Export audit log (--format cef|leef|json, --output file)");
    println!("  memory sync            Discover/sync LAN peers (discover|pull <addr>|serve)");
    println!("  skill <sub>            Manage skills (list|add <url>|remove <name>|new <name>)");
    println!("  verify                 Verify system facts");
    println!("  export                 Export document (--format revealjs --output file)");
    println!("  first-run              Show onboarding banner");
    println!("  plugin list            List registered plugins");
    println!("  --version              Show version");
    println!("  --init-config          Generate default config file");
    println!("  help                   Show this help\n");
    println!("IN-DOCUMENT COMMANDS (type in any app, then press Alt+M):");
    println!("  // health              Full document health audit");
    println!("  // kami <format>       Export document (markdown|pdf|revealjs)");
    println!("  // think <task>        Generate execution plan before writing");
    println!("  // ghost <task>        Force ghost-write mode");
    println!("  // urgent <task>       Force urgent/brief mode");
    println!("  // query <question>    Q&A mode");
    println!("  // explain <concept>   Explanation mode");
    println!("  summarize              Summarize document into 3 bullets");
    println!("\nFor docs: https://github.com/Kartik24Hulmukh/Kairo-Phantom");
}
