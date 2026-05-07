/// HTTP API server for phantom-core.
/// The Tauri overlay calls these endpoints via localhost:7437.

use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::net::TcpListener;
use tracing::info;

use crate::crdt::CrdtSession;
use crate::injector::Injector;
use crate::uia::UiaReader;
use crate::ai::AiBackend;

pub const PORT: u16 = 7437;

#[derive(Clone)]
pub struct ApiState {
    pub crdt: Arc<CrdtSession>,
    pub uia: Arc<UiaReader>,
    pub injector: Arc<Injector>,
    pub ai: Arc<dyn AiBackend>,
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

/// GET /health — overlay checks if core is running
async fn health() -> Json<HealthResponse> {
    Json(HealthResponse { status: "ok", version: env!("CARGO_PKG_VERSION") })
}

/// POST /materialize — read context, get AI suggestion, ghost-type it
async fn materialize(
    State(state): State<ApiState>,
    Json(req): Json<MaterializeRequest>,
) -> Result<Json<MaterializeResponse>, (StatusCode, String)> {

    // 1. Get context from UIA or caller-provided
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

    // 2. Push to CRDT
    state.crdt.insert_human_text(&context);

    // 3. Build prompt and call AI
    let prompt = state.crdt.build_prompt();
    let suggestion = state.ai.complete(&prompt).await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    if suggestion.is_empty() {
        return Err((StatusCode::NO_CONTENT, "AI returned empty suggestion".into()));
    }

    // 4. Push AI suggestion to CRDT
    state.crdt.insert_ai_text(&suggestion);

    // 5. Ghost-type into the focused app
    let injector = state.injector.clone();
    let suggestion_clone = suggestion.clone();
    tokio::task::spawn_blocking(move || injector.type_text(&suggestion_clone));

    Ok(Json(MaterializeResponse {
        word_count: suggestion.split_whitespace().count(),
        char_count: suggestion.len(),
        suggestion,
    }))
}

/// Start the HTTP API server (non-blocking — runs in background)
pub async fn start_api_server(state: ApiState) {
    let app = Router::new()
        .route("/health", get(health))
        .route("/materialize", post(materialize))
        .with_state(state);

    let addr = format!("127.0.0.1:{}", PORT);
    let listener = TcpListener::bind(&addr).await
        .expect(&format!("Failed to bind to {}", addr));

    info!("🌐 HTTP API listening on http://{}", addr);
    axum::serve(listener, app).await.unwrap();
}
