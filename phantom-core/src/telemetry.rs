// phantom-core/src/telemetry.rs
//! OpenTelemetry Observability Stack for Kairo Phantom.

use tracing::{info, span, Level};
use std::time::Instant;

pub struct TelemetryProvider {
    session_id: String,
}

impl Default for TelemetryProvider {
    fn default() -> Self {
        Self::new()
    }
}

impl TelemetryProvider {
    pub fn new() -> Self {
        Self {
            session_id: uuid::Uuid::new_v4().to_string(),
        }
    }

    pub fn start_ghost_session_trace(&self) -> tracing::Span {
        span!(Level::INFO, "ghost_session", session_id = %self.session_id)
    }

    pub fn record_latency(&self, operation: &str, start_time: Instant) {
        let elapsed = start_time.elapsed().as_millis();
        info!(
            target: "metrics",
            operation = operation,
            latency_ms = elapsed,
            "Latency metric recorded"
        );
    }

    pub fn track_tokens(&self, prompt_tokens: usize, completion_tokens: usize) {
        info!(
            target: "metrics",
            prompt_tokens = prompt_tokens,
            completion_tokens = completion_tokens,
            "Token consumption metric"
        );
    }

    pub fn record_hallucination_rate(&self, rate: f64) {
        info!(target: "metrics", hallucination_rate = rate, "Quality metric");
    }
}
