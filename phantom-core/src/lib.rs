pub mod ai;
pub mod api;
pub mod config;
pub mod crdt;
pub mod hotkey;
pub mod injector;
pub mod uia;
pub mod context;
pub mod swarm;
pub mod platform;
pub mod document_context;
pub mod plugin;
pub mod mcp_client;
pub mod mcp_bridge;
pub mod image_pipeline;
pub mod ghost_session;
pub mod governance;
pub mod yjs_peer;
pub mod identity;
pub mod wasm_sandbox;
pub mod extractors;
pub mod perf_engine;
pub mod wgpu_effects;
pub mod chaos;

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
