use anyhow::Result;
use std::sync::Arc;
use tokio::sync::mpsc;
use tracing::{info, warn};
use tracing_subscriber::EnvFilter;

mod ai;
mod config;
mod crdt;
mod hotkey;
mod injector;
mod uia;

use config::PhantomConfig;
use crdt::CrdtSession;
use hotkey::HotkeyWatcher;
use injector::Injector;
use uia::UiaReader;

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

    info!("👻 Kairo Phantom starting...");

    // Load config from ~/.kairo-phantom/config.toml
    let config = PhantomConfig::load_or_default()?;
    info!("⚙️  Config loaded: model={}", config.model.provider);

    // Create CRDT session (AI peer with fixed clientID 999)
    let crdt = Arc::new(CrdtSession::new(999));
    info!("📄 CRDT session initialized (AI clientID: 999)");

    // Main event channel — all threads talk through this
    let (tx, mut rx) = mpsc::channel::<PhantomEvent>(64);

    // Spawn hotkey listener thread
    let hotkey_tx = tx.clone();
    let hotkey_combo = config.hotkey.clone();
    tokio::task::spawn_blocking(move || {
        HotkeyWatcher::new(hotkey_combo, hotkey_tx).run();
    });
    info!("⌨️  Hotkey listener active ({})", config.hotkey);

    // UIA Reader (Windows only — reads text from active app)
    let uia_reader = UiaReader::new();

    // AI backend
    let ai_backend = ai::build_backend(&config)?;

    // Injector (ghost types into active app)
    let injector = Injector::new(config.typing_delay_ms);

    info!("✅ Kairo Phantom ready — press {} to materialize", config.hotkey);

    // Main event loop
    loop {
        match rx.recv().await {
            Some(PhantomEvent::HotkeyPressed) => {
                info!("🔮 Hotkey pressed — capturing context...");

                // 1. Read focused element text via UIA
                let context = match uia_reader.get_focused_text() {
                    Ok(text) if !text.is_empty() => text,
                    Ok(_) => {
                        warn!("⚠️  Focused element has no text — skipping");
                        continue;
                    }
                    Err(e) => {
                        warn!("⚠️  UIA read failed: {} — using clipboard fallback", e);
                        uia_reader.get_clipboard_text().unwrap_or_default()
                    }
                };

                info!("📖 Context captured ({} chars)", context.len());

                // 2. Push context into CRDT session
                crdt.insert_human_text(&context);

                // 3. Build AI prompt from CRDT state
                let prompt = crdt.build_prompt();
                let ai_backend = ai_backend.clone();
                let injector_clone = injector.clone();
                let crdt_clone = crdt.clone();
                let event_tx = tx.clone();

                // 4. Call AI + inject in a separate task (non-blocking)
                tokio::spawn(async move {
                    match ai_backend.complete(&prompt).await {
                        Ok(suggestion) if !suggestion.is_empty() => {
                            info!("🤖 AI suggestion ({} chars): {}...", suggestion.len(), &suggestion[..suggestion.len().min(50)]);

                            // 5. Push AI response into CRDT as AI peer
                            crdt_clone.insert_ai_text(&suggestion);

                            // 6. Ghost-type into active app
                            injector_clone.type_text(&suggestion);
                            info!("✨ Materialization complete");
                        }
                        Ok(_) => warn!("⚠️  AI returned empty suggestion"),
                        Err(e) => warn!("⚠️  AI call failed: {}", e),
                    }

                    let _ = event_tx.send(PhantomEvent::SuggestionReady(String::new())).await;
                });
            }

            Some(PhantomEvent::Shutdown) | None => {
                info!("👋 Kairo Phantom shutting down");
                break;
            }

            _ => {}
        }
    }

    Ok(())
}
