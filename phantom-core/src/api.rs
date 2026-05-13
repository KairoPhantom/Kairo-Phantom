/// HTTP API server for phantom-core.
/// The Tauri overlay calls these endpoints via localhost:7437.

use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use tokio::net::TcpListener;
use tracing::info;

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use crate::crdt::CrdtSession;
use crate::injector::HumanizedInjector as Injector;
use crate::uia::UiaReader;
use crate::ai::AiBackend;
use crate::context::ContextEngine;
use crate::document_context::{DocumentContext, ExtractorRegistry};
use crate::swarm::{SwarmOrchestrator, AgentType};
use crate::platform::AccessibilityReader;
use crate::command_protocol::CommandMode;

pub const PORT: u16 = 7437;

#[derive(Clone)]
pub struct ApiState {
    pub crdt: Arc<CrdtSession>,
    pub uia: Arc<UiaReader>,
    pub injector: Arc<Injector>,
    pub ai: Arc<dyn AiBackend>,
    pub context_engine: Arc<ContextEngine>,
    pub extractor_registry: Arc<ExtractorRegistry>,
    pub swarm_engine: Arc<SwarmOrchestrator>,
    pub mcp_agent_override: Arc<std::sync::Mutex<Option<String>>>,
}

#[derive(Deserialize)]
pub struct MaterializeRequest {
    pub context: Option<String>,
}

#[derive(Serialize)]
pub struct MaterializeResponse {
    pub suggestion: String,
    pub word_count: usize,
    pub char_count: usize,
}

#[derive(Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub version: &'static str,
}

#[derive(Serialize)]
/*
pub struct ContextResponse {
    pub process_name: String,
    pub window_title: String,
    pub extracted_text: String,
}
*/

#[derive(Deserialize)]
pub struct InjectRequest {
    pub text: String,
}

#[derive(Deserialize)]
pub struct AskRequest {
    pub prompt: String,
}

#[derive(Serialize)]
pub struct AskResponse {
    pub response: String,
}

#[derive(Serialize)]
pub struct AppResponse {
    pub process: String,
    pub environment: String,
}

#[derive(Deserialize)]
pub struct AgentRequest {
    pub agent: String,
}

#[derive(Deserialize)]
pub struct ImageGenerateRequest {
    pub prompt: String,
    #[serde(default)]
    pub backend: String,
}

#[derive(Serialize)]
pub struct ImageGenerateResponse {
    pub status: String,
    pub base64_data: String,
    pub mime_type: String,
    pub backend_used: String,
}

#[derive(Deserialize)]
pub struct MobileSyncRequest {
    pub device_id: String,
    pub content: String,
    pub tags: Vec<String>,
}

#[derive(Serialize)]
pub struct MobileSyncResponse {
    pub status: String,
    pub sync_id: String,
}

/// GET /health
async fn health() -> Json<HealthResponse> {
    Json(HealthResponse { status: "ok", version: env!("CARGO_PKG_VERSION") })
}

/// GET /context — MCP Tool: read context
async fn get_context(State(state): State<ApiState>) -> Json<DocumentContext> {
    let raw_text = state.uia.get_focused_text()
        .or_else(|_| state.uia.get_clipboard_text())
        .unwrap_or_default();

    let app_ctx = state.context_engine.capture(&raw_text);
    
    let doc_ctx = if let Some(ref file_path) = app_ctx.file_path {
        state.extractor_registry
            .extract(file_path, &app_ctx.prompt_text, app_ctx.active_slide)
            .unwrap_or_else(|| {
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

    Json(doc_ctx)
}

/// POST /inject — MCP Tool: ghost write
async fn inject(
    State(state): State<ApiState>,
    Json(req): Json<InjectRequest>,
) -> Result<Json<()>, (StatusCode, String)> {
    let injector = state.injector.clone();
    tokio::task::spawn_blocking(move || injector.type_text(&req.text));
    Ok(Json(()))
}

/// POST /ask — MCP Tool: ask (context-aware swarm generation + inject)
async fn ask(
    State(state): State<ApiState>,
    Json(req): Json<AskRequest>,
) -> Result<Json<AskResponse>, (StatusCode, String)> {
    let raw_text = state.uia.get_focused_text()
        .or_else(|_| state.uia.get_clipboard_text())
        .unwrap_or_default();

    let app_ctx = state.context_engine.capture(&raw_text);
    
    let doc_ctx = if let Some(ref file_path) = app_ctx.file_path {
        state.extractor_registry
            .extract(file_path, &app_ctx.prompt_text, app_ctx.active_slide)
            .unwrap_or_else(|| {
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
    
    // Check if MCP override is set
    let override_agent = {
        let mut lock = state.mcp_agent_override.lock().unwrap();
        lock.take() // Use it once and clear it
    };
    
    let (mode, prompt) = CommandMode::from_prompt(&doc_ctx.prompt_text);
    
    let (target_backend, profile) = if let Some(agent_name) = override_agent {
        let agent_type = match agent_name.to_lowercase().as_str() {
            "design" => AgentType::DesignAndMedia,
            "reasoning" => AgentType::ReasoningAndLogic,
            "student" => AgentType::StudentTutor,
            "engineer" => AgentType::Engineer,
            "data" => AgentType::DataAnalyst,
            _ => AgentType::ContentAndAllRounder,
        };
        state.swarm_engine.get_backend_and_profile_by_type(&agent_type, &doc_ctx)

    } else {
        state.swarm_engine.route(&doc_ctx, &mode).await
    };
    
    let final_prompt = if prompt.is_empty() { &req.prompt } else { &prompt };
    let resp = target_backend.complete(&profile.system_directive, final_prompt).await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        
    let injector = state.injector.clone();
    let text = resp.clone();
    #[allow(clippy::let_underscore_future)]
    let _ = tokio::task::spawn_blocking(move || injector.type_text(&text));
    
    Ok(Json(AskResponse { response: resp }))
}

/// GET /app — MCP Tool: detect app
async fn get_app(State(state): State<ApiState>) -> Json<AppResponse> {
    let raw_text = state.uia.get_focused_text()
        .or_else(|_| state.uia.get_clipboard_text())
        .unwrap_or_default();

    let app_ctx = state.context_engine.capture(&raw_text);

    Json(AppResponse {
        process: app_ctx.process_name,
        environment: app_ctx.environment.label(),
    })
}

/// POST /agent — MCP Tool: switch agent
async fn set_agent(State(state): State<ApiState>, Json(req): Json<AgentRequest>) -> Json<()> {
    let mut lock = state.mcp_agent_override.lock().unwrap();
    *lock = Some(req.agent);
    Json(())
}

/// POST /materialize — Original overlay endpoint
async fn materialize(
    State(state): State<ApiState>,
    Json(req): Json<MaterializeRequest>,
) -> Result<Json<MaterializeResponse>, (StatusCode, String)> {
    let context = if let Some(ctx) = req.context {
        ctx
    } else {
        state.uia.get_focused_text()
            .or_else(|_| state.uia.get_clipboard_text())
            .unwrap_or_default()
    };

    if context.is_empty() {
        return Err((StatusCode::BAD_REQUEST, "No text context available".into()));
    }

    state.crdt.insert_human_text(&context);

    let system = state.crdt.get_system_prompt();
    let user = state.crdt.get_user_context();
    let suggestion = state.ai.complete(system, &user).await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    state.crdt.insert_ai_text(&suggestion);

    let injector = state.injector.clone();
    let suggestion_clone = suggestion.clone();
    tokio::task::spawn_blocking(move || injector.type_text(&suggestion_clone));

    Ok(Json(MaterializeResponse {
        word_count: suggestion.split_whitespace().count(),
        char_count: suggestion.len(),
        suggestion,
    }))
}

/// POST /generate_image — MCP Tool: generate image via image pipeline
async fn generate_image(
    State(state): State<ApiState>,
    Json(req): Json<ImageGenerateRequest>,
) -> Result<Json<ImageGenerateResponse>, (StatusCode, String)> {
    use crate::image_pipeline::{ImageRouter, ImageGenerationConfig};
    use crate::document_context::DocumentContext;
    
    // Build a default doc context for routing
    let raw_text = state.uia.get_focused_text()
        .or_else(|_| state.uia.get_clipboard_text())
        .unwrap_or_default();
    let app_ctx = state.context_engine.capture(&raw_text);
    let doc_ctx = DocumentContext::from_raw_text(
        &app_ctx.prompt_text,
        &app_ctx.document_text,
        app_ctx.environment.to_doc_kind(),
    );

    let config = ImageGenerationConfig::default();
    let router = ImageRouter::new(config);

    match router.generate(&req.prompt, &doc_ctx).await {
        Ok(result) => Ok(Json(ImageGenerateResponse {
            status: "ok".into(),
            base64_data: result.base64_data,
            mime_type: result.mime_type,
            backend_used: result.backend_used,
        })),
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, format!("Image generation failed: {}", e))),
    }
}

/// POST /bedrock/invoke — Tier 8 AWS Emulation
async fn aws_bedrock_invoke(
    State(_state): State<ApiState>,
    Json(req): Json<crate::aws_emulation::BedrockInvokeRequest>,
) -> Json<crate::aws_emulation::BedrockInvokeResponse> {
    Json(crate::aws_emulation::AwsEmulation::handle_invoke(req).await)
}

#[derive(Deserialize)]
pub struct KamiExportRequest {
    pub content: String,
    pub format: String,
    pub output_path: String,
}

async fn kami_export(
    State(_state): State<ApiState>,
    Json(req): Json<KamiExportRequest>,
) -> (StatusCode, Json<()>) {
    let res = match req.format.as_str() {
        "pdf" => crate::kami_export::KamiExporter::execute(crate::kami_export::KamiCommand::Pdf, req.content).await,
        "reveal" => crate::kami_export::KamiExporter::execute(crate::kami_export::KamiCommand::RevealJs, req.content).await,
        "email" => crate::kami_export::KamiExporter::execute(crate::kami_export::KamiCommand::Email, req.content).await,
        "linkedin" => crate::kami_export::KamiExporter::execute(crate::kami_export::KamiCommand::LinkedIn, req.content).await,
        _ => Err("Unsupported format".to_string()),
    };

    match res {
        Ok(_) => (StatusCode::OK, Json(())),
        Err(_) => (StatusCode::INTERNAL_SERVER_ERROR, Json(())),
    }
}

async fn mobile_sync_post(
    State(state): State<ApiState>,
    Json(req): Json<MobileSyncRequest>,
) -> Json<MobileSyncResponse> {
    info!("📱 Mobile Bridge: Received sync from {}", req.device_id);
    
    // Store in memory for now, will eventually go to MemMachine
    let sync_id = uuid::Uuid::new_v4().to_string();
    
    // Inject into CRDT for real-time visibility in overlay
    state.crdt.insert_human_text(&format!("\n--- Mobile Sync ({}) ---\n{}\n", req.device_id, req.content));

    Json(MobileSyncResponse {
        status: "synced".into(),
        sync_id,
    })
}

pub async fn start_api_server(state: ApiState) {
    let app = Router::new()
        .route("/health", get(health))
        .route("/materialize", post(materialize))
        .route("/context", get(get_context))
        .route("/inject", post(inject))
        .route("/ask", post(ask))
        .route("/app", get(get_app))
        .route("/agent", post(set_agent))
        .route("/generate_image", post(generate_image))
        .route("/bedrock/invoke", post(aws_bedrock_invoke))
        .route("/kami/export", post(kami_export))
        .route("/mobile/sync", post(mobile_sync_post))
        .with_state(state);

    let addr = format!("127.0.0.1:{}", PORT);
    let listener = TcpListener::bind(&addr).await
        .unwrap_or_else(|_| panic!("Failed to bind to {}", addr));

    info!("🌐 HTTP API listening on http://{}", addr);
    axum::serve(listener, app).await.unwrap();
}
