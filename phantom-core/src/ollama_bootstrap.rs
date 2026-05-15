//! Ollama Bootstrap — P0-A2
//! Silently detects and configures Ollama for offline AI.
//! Called at startup; model pull is non-blocking.

use tokio::time::Duration;

pub struct OllamaBootstrap;

impl OllamaBootstrap {
    /// Returns true if Ollama API is reachable.
    pub async fn is_running() -> bool {
        reqwest::Client::new()
            .get("http://localhost:11434/api/tags")
            .timeout(Duration::from_secs(2))
            .send()
            .await
            .map(|r| r.status().is_success())
            .unwrap_or(false)
    }

    /// Pull a model in the background. Non-blocking — fires and forgets.
    pub async fn ensure_model(model: &str) -> anyhow::Result<()> {
        tracing::info!("🦙 Ensuring Ollama model: {}", model);
        let client = reqwest::Client::new();
        let body = serde_json::json!({"name": model, "stream": false});
        let resp = client
            .post("http://localhost:11434/api/pull")
            .json(&body)
            .timeout(Duration::from_secs(600))
            .send()
            .await?;
        if resp.status().is_success() {
            tracing::info!("✅ Ollama model '{}' ready", model);
        } else {
            tracing::warn!("⚠️  Model pull returned: {}", resp.status());
        }
        Ok(())
    }

    /// Full bootstrap: detect → log → pull model in background.
    pub async fn bootstrap(default_model: &str) {
        if Self::is_running().await {
            tracing::info!("✅ Ollama running at http://localhost:11434");
            let model = default_model.to_string();
            tokio::spawn(async move {
                if let Err(e) = Self::ensure_model(&model).await {
                    tracing::warn!("⚠️  Model pull failed: {}", e);
                }
            });
        } else {
            tracing::warn!(
                "⚠️  Ollama not detected. For offline AI: winget install Ollama.Ollama && ollama serve"
            );
        }
    }
}
