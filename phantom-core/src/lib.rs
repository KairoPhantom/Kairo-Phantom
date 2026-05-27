// phantom-core/src/lib.rs
//
// Lint configuration:
// Several modules contain scaffolded APIs that are intentionally defined but
// not yet called in main.rs (e.g., telemetry, eval suite, WASM sandbox,
// governance, UIA adapters). These will be activated in future milestones.
// We suppress dead_code and unused warnings crate-wide to avoid obscuring
// real issues with scaffolding noise. This is standard practice for library
// crates with forward-declared APIs.
#![allow(dead_code)]
#![allow(unused_imports)]
#![allow(unused_variables)]
#![allow(clippy::empty_line_after_doc_comments)]
#![allow(clippy::manual_is_multiple_of)]

pub mod ai;
pub mod api;
pub mod config;
pub mod crdt;
pub mod hotkey;
pub mod injector;
pub mod uia;
pub mod context;
pub mod integration;
pub mod swarm;

pub mod platform;
pub mod document_context;
pub mod plugin;
pub mod mcp_client;
pub mod mcp_bridge;
pub mod image_pipeline;
pub mod ghost_session;
pub mod intent_gate;
pub mod planning_engine;
pub mod governance;
pub mod yjs_peer;
pub mod identity;
pub mod wasm_sandbox;
pub mod extractors;
pub mod perf_engine;
pub mod wgpu_effects;
pub mod chaos;
pub mod sentinel;
pub mod persona;
pub mod memory;
pub mod guardrails;
pub mod context7;
pub mod command_protocol;
/// Phase 1 Hardening: strict // protocol gate — returns None for non-command text.
pub mod prompt_parser;
pub mod pii_guard;
pub mod response_validator;
pub mod retry_policy;
pub mod memory_store;
pub mod quality_gate;
pub mod writing_pipeline;
pub mod verify;
pub mod kami_export;
pub mod pdf_context;             // Domain 4: PDF SmartContextCapture structs
pub mod context_optimizer;
pub mod background_worker;
pub mod aws_emulation;
pub mod skills;
pub mod memory_vault;
pub mod tolaria_bridge;
pub mod collaborative;



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
    /// Domain 8: Alt+V — voice dictation trigger
    VoicePressed,
    /// Domain 8: Alt+Shift+M — screen context capture trigger
    ScreenContextPressed,
    /// Shutdown signal
    Shutdown,
}
pub mod telemetry;
pub mod eval;
pub mod xa11y;
pub mod inference;
pub mod mcp_auth;

pub mod waza_sdk;

// ── 100x Roadmap Modules ──────────────────────────────────────────────────────
pub mod ollama_bootstrap;       // P0-A2: Ollama auto-detection & background setup
pub mod toast_notification;     // P0-B2: PAHF toast overlay (replaces doc injection)
pub mod startup_timer;          // P0-A1: Startup checkpoint profiler
pub mod memory_seeder;          // P1-A2: Seed MemMachine from existing doc folder
pub mod kpx_export;             // P1-A4: .kpx portable memory export/import
pub mod health_check;           // P2-A1: Document health check (passive voice, consistency)
pub mod compliance_scanner;     // P2-A3: HIPAA/GDPR/custom compliance clause scanner
pub mod owasp_compliance;       // P2-C1: OWASP Agentic Top 10 compliance matrix
pub mod deep_presenter;         // P2-A7: DeepPresenter-9B local PPT generation bridge
pub mod waza_registry;          // P3-A2/B1: Waza Skills marketplace + skill builder CLI
pub mod siem_export;            // P4-A2: CEF/LEEF/JSON-lines SIEM audit log export
pub mod cross_doc_consistency;  // P2-A2: Cross-document consistency engine
pub mod lan_sync;               // P1-A1: LAN memory sync — UDP discovery + TCP transfer
pub mod excel_formula;          // P2-A5: Excel formula explainer + generator
pub mod section_summarizer;     // P2-A4: 3-bullet section summarizer

// ── Phase 1: Python Sidecar + Document-Native Pipeline ────────────────────────
pub mod sidecar_client;         // TCP client → Python sidecar (DOCX/XLSX/PPTX/PDF I/O)
pub mod doc_prompt_builder;     // Format-specific LLM prompt builder + JSON op parser

// ── Phase 4A: Markdown Section-Aware Writer ───────────────────────────────────
pub mod md_writer;              // pulldown-cmark AST-aware markdown insertion
pub mod code_context;
pub mod code_injector;

// ── Domain 8: Multimodal Input ──────────────────────────────────────────────
pub mod voice_engine;
pub mod screen_context;
pub mod tts_engine;
pub mod wake_word;

// ── Domain 9: Enterprise Governance & Compliance ────────────────────────────
pub mod enterprise;            // SSO, SPIFFE, audit chain, compliance, RBAC

// ── Domain 10: Security Hardening & Penetration Testing ─────────────────────
pub mod prompt_injection_firewall; // 50-detector 6-layer prompt injection firewall
pub mod red_team;              // Autonomous red-team simulation (Decepticon-style)
pub mod supply_chain;          // SBOM, license compliance, vulnerability audit
