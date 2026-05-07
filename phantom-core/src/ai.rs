/// AI backends — Ollama (local, default), OpenAI, Anthropic, Gemini.
/// All implement the `AiBackend` trait for hot-swappable LLM providers.

use anyhow::Result;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tracing::debug;

use crate::config::PhantomConfig;

/// Common interface for all AI backends
#[async_trait::async_trait]
pub trait AiBackend: Send + Sync {
    async fn complete(&self, prompt: &str) -> Result<String>;
}

/// Build the correct backend from config
pub fn build_backend(config: &PhantomConfig) -> Result<Arc<dyn AiBackend>> {
    match config.model.provider.as_str() {
        "ollama" => Ok(Arc::new(OllamaBackend::new(
            config.model.base_url.clone().unwrap_or_else(|| "http://localhost:11434".into()),
            config.model.model_name.clone().unwrap_or_else(|| "llama3".into()),
        ))),
        "openai" => Ok(Arc::new(OpenAiBackend::new(
            config.model.api_key.clone().unwrap_or_default(),
            config.model.model_name.clone().unwrap_or_else(|| "gpt-4o-mini".into()),
        ))),
        "anthropic" => Ok(Arc::new(AnthropicBackend::new(
            config.model.api_key.clone().unwrap_or_default(),
            config.model.model_name.clone().unwrap_or_else(|| "claude-3-haiku-20240307".into()),
        ))),
        "gemini" => Ok(Arc::new(GeminiBackend::new(
            config.model.api_key.clone().unwrap_or_default(),
            config.model.model_name.clone().unwrap_or_else(|| "gemini-1.5-flash".into()),
        ))),
        unknown => anyhow::bail!("Unknown AI provider: '{}'. Supported: ollama, openai, anthropic, gemini", unknown),
    }
}

// ─── Ollama (local, default) ───────────────────────────────────────────────

pub struct OllamaBackend {
    client: Client,
    base_url: String,
    model: String,
}

#[derive(Serialize)]
struct OllamaRequest {
    model: String,
    prompt: String,
    stream: bool,
}

#[derive(Deserialize)]
struct OllamaResponse {
    response: String,
}

impl OllamaBackend {
    pub fn new(base_url: String, model: String) -> Self {
        OllamaBackend { client: Client::new(), base_url, model }
    }
}

#[async_trait::async_trait]
impl AiBackend for OllamaBackend {
    async fn complete(&self, prompt: &str) -> Result<String> {
        let url = format!("{}/api/generate", self.base_url);
        let req = OllamaRequest {
            model: self.model.clone(),
            prompt: prompt.to_string(),
            stream: false,
        };

        debug!("Ollama: POST {} model={}", url, req.model);
        let resp = self.client.post(&url).json(&req).send().await?;
        let body: OllamaResponse = resp.json().await?;
        Ok(body.response.trim().to_string())
    }
}

// ─── OpenAI ────────────────────────────────────────────────────────────────

pub struct OpenAiBackend {
    client: Client,
    api_key: String,
    model: String,
}

#[derive(Serialize)]
struct OpenAiRequest {
    model: String,
    messages: Vec<OpenAiMessage>,
    max_tokens: u32,
}

#[derive(Serialize)]
struct OpenAiMessage {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct OpenAiResponse {
    choices: Vec<OpenAiChoice>,
}

#[derive(Deserialize)]
struct OpenAiChoice {
    message: OpenAiMessageResponse,
}

#[derive(Deserialize)]
struct OpenAiMessageResponse {
    content: String,
}

impl OpenAiBackend {
    pub fn new(api_key: String, model: String) -> Self {
        OpenAiBackend { client: Client::new(), api_key, model }
    }
}

#[async_trait::async_trait]
impl AiBackend for OpenAiBackend {
    async fn complete(&self, prompt: &str) -> Result<String> {
        let resp = self.client
            .post("https://api.openai.com/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&OpenAiRequest {
                model: self.model.clone(),
                messages: vec![OpenAiMessage { role: "user".into(), content: prompt.into() }],
                max_tokens: 150,
            })
            .send()
            .await?
            .json::<OpenAiResponse>()
            .await?;

        Ok(resp.choices.into_iter().next()
            .map(|c| c.message.content.trim().to_string())
            .unwrap_or_default())
    }
}

// ─── Anthropic ─────────────────────────────────────────────────────────────

pub struct AnthropicBackend {
    client: Client,
    api_key: String,
    model: String,
}

#[derive(Serialize)]
struct AnthropicRequest {
    model: String,
    max_tokens: u32,
    messages: Vec<AnthropicMessage>,
}

#[derive(Serialize)]
struct AnthropicMessage {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct AnthropicResponse {
    content: Vec<AnthropicContent>,
}

#[derive(Deserialize)]
struct AnthropicContent {
    text: String,
}

impl AnthropicBackend {
    pub fn new(api_key: String, model: String) -> Self {
        AnthropicBackend { client: Client::new(), api_key, model }
    }
}

#[async_trait::async_trait]
impl AiBackend for AnthropicBackend {
    async fn complete(&self, prompt: &str) -> Result<String> {
        let resp = self.client
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .json(&AnthropicRequest {
                model: self.model.clone(),
                max_tokens: 150,
                messages: vec![AnthropicMessage { role: "user".into(), content: prompt.into() }],
            })
            .send()
            .await?
            .json::<AnthropicResponse>()
            .await?;

        Ok(resp.content.into_iter().next()
            .map(|c| c.text.trim().to_string())
            .unwrap_or_default())
    }
}

// ─── Gemini ────────────────────────────────────────────────────────────────

pub struct GeminiBackend {
    client: Client,
    api_key: String,
    model: String,
}

#[derive(Serialize)]
struct GeminiRequest {
    contents: Vec<GeminiContent>,
}

#[derive(Serialize)]
struct GeminiContent {
    parts: Vec<GeminiPart>,
}

#[derive(Serialize)]
struct GeminiPart {
    text: String,
}

#[derive(Deserialize)]
struct GeminiResponse {
    candidates: Vec<GeminiCandidate>,
}

#[derive(Deserialize)]
struct GeminiCandidate {
    content: GeminiCandidateContent,
}

#[derive(Deserialize)]
struct GeminiCandidateContent {
    parts: Vec<GeminiPartResponse>,
}

#[derive(Deserialize)]
struct GeminiPartResponse {
    text: String,
}

impl GeminiBackend {
    pub fn new(api_key: String, model: String) -> Self {
        GeminiBackend { client: Client::new(), api_key, model }
    }
}

#[async_trait::async_trait]
impl AiBackend for GeminiBackend {
    async fn complete(&self, prompt: &str) -> Result<String> {
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.model, self.api_key
        );

        let resp = self.client
            .post(&url)
            .json(&GeminiRequest {
                contents: vec![GeminiContent {
                    parts: vec![GeminiPart { text: prompt.into() }]
                }]
            })
            .send()
            .await?
            .json::<GeminiResponse>()
            .await?;

        Ok(resp.candidates.into_iter().next()
            .and_then(|c| c.content.parts.into_iter().next())
            .map(|p| p.text.trim().to_string())
            .unwrap_or_default())
    }
}
