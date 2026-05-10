/// AI backends v2 — Production-grade streaming with Application Awareness.
/// Supports: OpenAI / NVIDIA NIM / Anthropic / Gemini / Ollama
/// All backends implement proper SSE streaming for real-time ghost-typing.

use anyhow::{Context, Result};
use reqwest::Client;
use serde::Deserialize;
use std::sync::Arc;
use tracing::info;

use crate::config::ModelConfig;

// ─── System Persona ─────────────────────────────────────────────────────────

pub const KAIRO_SYSTEM_PROMPT: &str = r#"You are Kairo, an elite AI writing engine embedded directly into the user's operating system. You materialize intelligence on demand — replacing the user's instructions with exactly what they need.

## PRIME DIRECTIVE: [REPLACE] TAG
When the user's message is an instruction, request, or command:
1. Begin your response with exactly: [REPLACE]
2. Immediately follow with the requested content — no preamble, no postamble.
3. The [REPLACE] tag tells the engine to erase the user's prompt and substitute your response.

## APPLICATION-AWARE FORMATTING
You receive metadata: `[ENV: <environment> | APP: <process> | WINDOW: <title>]`
Honor these formatting rules strictly:

| Environment | Output Style |
|---|---|
| Microsoft Word / Outlook | Formal professional prose. No markdown syntax. Proper paragraphs. |
| PowerPoint | Title line then bullet points starting with "- ". Max 12 words per bullet. |
| Excel | Data-oriented. Concise. Tab or comma separated if tabular. |
| VS Code / Code Editor | Raw code ONLY. No markdown fences unless explicitly requested. |
| Terminal / PowerShell / CMD | Shell commands only. One command per line. No explanation. |
| Notepad (plain text) | Clean plain text. No formatting characters whatsoever. |
| Chrome / Edge / Firefox | Match context: Google Docs = prose, Gmail = email, general = clear writing. |
| Slack / Discord | Conversational, human, brief. Emojis where natural. |
| Microsoft Teams | Professional, clear, workplace appropriate. |

## INTELLIGENCE RULES
- If the prompt is in a non-English language, respond in the SAME language.
- Match the exact tone of surrounding document context (formal if formal, casual if casual).
- For code requests: detect the language from context and use it.
- For "improve/fix/rewrite": do it silently — output the improved version only.

## STRICT PROHIBITIONS
- NEVER start with "Sure", "Here is", "Of course", "Certainly", "I can", "I'll".
- NEVER end with "Hope this helps", "Let me know", "Feel free to".
- NEVER explain what you are doing. Execute and produce.
- NEVER add your own formatting to plain-text environments.
- NEVER show the [REPLACE] tag if not replacing."#;

// ─── Trait ───────────────────────────────────────────────────────────────────

#[async_trait::async_trait]
pub trait AiBackend: Send + Sync {
    async fn complete(&self, system: &str, user: &str) -> Result<String>;
    async fn stream_complete(
        &self,
        system: &str,
        user: &str,
        tx: tokio::sync::mpsc::Sender<String>,
    ) -> Result<()>;
}

pub fn build_backend(config: &ModelConfig) -> Result<Arc<dyn AiBackend>> {
    match config.provider.as_str() {
        "ollama" => Ok(Arc::new(OllamaBackend::new(
            config.base_url.clone().unwrap_or_else(|| "http://localhost:11434".into()),
            config.model_name.clone().unwrap_or_else(|| "llama3".into()),
        ))),
        "openai" => Ok(Arc::new(OpenAiBackend::new(
            config.api_key.clone().unwrap_or_default(),
            config.model_name.clone().unwrap_or_else(|| "gpt-4o".into()),
            config.base_url.clone().unwrap_or_else(|| "https://api.openai.com/v1/chat/completions".into()),
        ))),
        "nim" => Ok(Arc::new(OpenAiBackend::new(
            config.api_key.clone().unwrap_or_default(),
            config.model_name.clone().unwrap_or_else(|| "meta/llama-3.1-70b-instruct".into()),
            config.base_url.clone().unwrap_or_else(|| "https://integrate.api.nvidia.com/v1/chat/completions".into()),
        ))),
        "anthropic" => Ok(Arc::new(AnthropicBackend::new(
            config.api_key.clone().unwrap_or_default(),
            config.model_name.clone().unwrap_or_else(|| "claude-3-5-sonnet-20241022".into()),
        ))),
        "gemini" => Ok(Arc::new(GeminiBackend::new(
            config.api_key.clone().unwrap_or_default(),
            config.model_name.clone().unwrap_or_else(|| "gemini-1.5-pro".into()),
        ))),
        unknown => anyhow::bail!(
            "Unknown AI provider: '{}'. Supported: ollama, openai, nim, anthropic, gemini",
            unknown
        ),
    }
}

// ─── OpenAI / NIM ────────────────────────────────────────────────────────────

pub struct OpenAiBackend {
    client: Client,
    api_key: String,
    model: String,
    base_url: String,
}



#[derive(Deserialize)]
struct OpenAiResponse {
    choices: Vec<OpenAiChoice>,
}

#[derive(Deserialize)]
struct OpenAiChoice {
    message: OpenAiMessageContent,
}

#[derive(Deserialize)]
struct OpenAiMessageContent {
    content: String,
}

impl OpenAiBackend {
    pub fn new(api_key: String, model: String, base_url: String) -> Self {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(120))
            .build()
            .unwrap_or_default();
        OpenAiBackend { client, api_key, model, base_url }
    }
}

#[async_trait::async_trait]
impl AiBackend for OpenAiBackend {
    async fn complete(&self, system: &str, user: &str) -> Result<String> {
        info!("🤖 OpenAI request (model: {})", self.model);

        let req = serde_json::json!({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": 4096,
            "temperature": 0.7
        });

        let resp = self.client
            .post(&self.base_url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&req)
            .send()
            .await
            .context("Failed to send OpenAI request")?;

        let status = resp.status();
        let body = resp.text().await?;
        if !status.is_success() {
            anyhow::bail!("OpenAI error {}: {}", status, body);
        }

        let parsed: OpenAiResponse = serde_json::from_str(&body)
            .context("Failed to parse OpenAI response")?;

        Ok(parsed.choices.into_iter().next()
            .map(|c| c.message.content.trim().to_string())
            .unwrap_or_default())
    }

    async fn stream_complete(
        &self,
        system: &str,
        user: &str,
        tx: tokio::sync::mpsc::Sender<String>,
    ) -> Result<()> {
        use futures_util::StreamExt;

        let req = serde_json::json!({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": true,
            "max_tokens": 4096,
            "temperature": 0.7
        });

        let mut stream = self.client
            .post(&self.base_url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&req)
            .send()
            .await?
            .bytes_stream();

        let mut parser = crate::perf_engine::ZeroAllocSseParser::new();

        while let Some(item) = stream.next().await {
            let chunk = item?;
            for s in parser.feed(&chunk) {
                if s == "[DONE]" { return Ok(()); }
                if let Some(content) = crate::perf_engine::ZeroAllocSseParser::extract_token_fast(s.as_bytes()) {
                    let _ = tx.send(content).await;
                }
            }
        }

        Ok(())
    }
}

// ─── Ollama ──────────────────────────────────────────────────────────────────

pub struct OllamaBackend {
    client: Client,
    base_url: String,
    model: String,
}

impl OllamaBackend {
    pub fn new(base_url: String, model: String) -> Self {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(300))
            .build()
            .unwrap_or_default();
        OllamaBackend { client, base_url, model }
    }
}

#[async_trait::async_trait]
impl AiBackend for OllamaBackend {
    async fn complete(&self, system: &str, user: &str) -> Result<String> {
        let url = format!("{}/api/chat", self.base_url);
        let req = serde_json::json!({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": false,
            "options": {
                "num_predict": 4096,
                "temperature": 0.4,
                "repeat_penalty": 1.15
            }
        });

        let resp = self.client.post(&url).json(&req).send().await?;
        let body: serde_json::Value = resp.json().await?;
        Ok(body["message"]["content"].as_str().unwrap_or("").trim().to_string())
    }

    async fn stream_complete(
        &self,
        system: &str,
        user: &str,
        tx: tokio::sync::mpsc::Sender<String>,
    ) -> Result<()> {
        use futures_util::StreamExt;
        let url = format!("{}/api/chat", self.base_url);
        let req = serde_json::json!({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": true,
            "options": {
                "num_predict": 4096,
                "temperature": 0.4,
                "repeat_penalty": 1.15
            }
        });

        let mut stream = self.client.post(&url).json(&req).send().await?.bytes_stream();
        let mut buf = String::new();

        while let Some(item) = stream.next().await {
            let chunk = item?;
            buf.push_str(&String::from_utf8_lossy(&chunk));
            
            while let Some(nl) = buf.find('\n') {
                let line = buf[..nl].trim().to_string();
                buf = buf[nl + 1..].to_string();
                
                if line.is_empty() {
                    continue;
                }
                
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(&line) {
                    if let Some(msg) = val.get("message") {
                        if let Some(token) = msg.get("content").and_then(|c| c.as_str()) {
                            if !token.is_empty() {
                                let _ = tx.send(token.to_string()).await;
                            }
                        }
                    }
                    if val["done"].as_bool().unwrap_or(false) {
                        return Ok(());
                    }
                }
            }
        }
        Ok(())
    }
}

// ─── Anthropic (Claude) ──────────────────────────────────────────────────────

pub struct AnthropicBackend {
    client: Client,
    api_key: String,
    model: String,
}

impl AnthropicBackend {
    pub fn new(api_key: String, model: String) -> Self {
        AnthropicBackend {
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(120))
                .build()
                .unwrap_or_default(),
            api_key,
            model,
        }
    }
}

#[async_trait::async_trait]
impl AiBackend for AnthropicBackend {
    async fn complete(&self, system: &str, user: &str) -> Result<String> {
        let req = serde_json::json!({
            "model": self.model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}]
        });

        let resp = self.client
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .header("Content-Type", "application/json")
            .json(&req)
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;

        Ok(resp["content"][0]["text"]
            .as_str()
            .unwrap_or("")
            .trim()
            .to_string())
    }

    async fn stream_complete(
        &self,
        system: &str,
        user: &str,
        tx: tokio::sync::mpsc::Sender<String>,
    ) -> Result<()> {
        use futures_util::StreamExt;

        let req = serde_json::json!({
            "model": self.model,
            "max_tokens": 4096,
            "system": system,
            "stream": true,
            "messages": [{"role": "user", "content": user}]
        });

        let mut stream = self.client
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .header("Content-Type", "application/json")
            .json(&req)
            .send()
            .await?
            .bytes_stream();

        let mut parser = crate::perf_engine::ZeroAllocSseParser::new();
        while let Some(item) = stream.next().await {
            let chunk = item?;
            for s in parser.feed(&chunk) {
                if let Some(content) = crate::perf_engine::ZeroAllocSseParser::extract_token_fast(s.as_bytes()) {
                    let _ = tx.send(content).await;
                }
            }
        }
        Ok(())
    }
}

// ─── Gemini ───────────────────────────────────────────────────────────────────

pub struct GeminiBackend {
    client: Client,
    api_key: String,
    model: String,
}

impl GeminiBackend {
    pub fn new(api_key: String, model: String) -> Self {
        GeminiBackend {
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(120))
                .build()
                .unwrap_or_default(),
            api_key,
            model,
        }
    }
}

#[async_trait::async_trait]
impl AiBackend for GeminiBackend {
    async fn complete(&self, system: &str, user: &str) -> Result<String> {
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.model, self.api_key
        );

        let req = serde_json::json!({
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}]
        });

        let resp = self.client.post(&url).json(&req).send().await?
            .json::<serde_json::Value>().await?;

        Ok(resp["candidates"][0]["content"]["parts"][0]["text"]
            .as_str()
            .unwrap_or("")
            .trim()
            .to_string())
    }

    async fn stream_complete(
        &self,
        system: &str,
        user: &str,
        tx: tokio::sync::mpsc::Sender<String>,
    ) -> Result<()> {
        use futures_util::StreamExt;

        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:streamGenerateContent?alt=sse&key={}",
            self.model, self.api_key
        );

        let req = serde_json::json!({
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}]
        });

        let mut stream = self.client.post(&url).json(&req).send().await?.bytes_stream();
        let mut parser = crate::perf_engine::ZeroAllocSseParser::new();
        while let Some(item) = stream.next().await {
            let chunk = item?;
            for s in parser.feed(&chunk) {
                if let Some(content) = crate::perf_engine::ZeroAllocSseParser::extract_token_fast(s.as_bytes()) {
                    let _ = tx.send(content).await;
                }
            }
        }
        Ok(())
    }
}
