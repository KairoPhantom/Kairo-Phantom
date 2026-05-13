// phantom-core/src/pipeline.rs

use enigo::{Enigo, KeyboardControllable};
use reqwest::Client;
use std::time::Duration;
use tokio::time::sleep;
use tokio_util::sync::CancellationToken;
use futures_util::StreamExt;

/// Manages pre-warmed connections for sub-100ms LLM latency.
pub struct HotkeyPipeline {
    client: Client,
    endpoint: String,
}

impl HotkeyPipeline {
    pub fn new(endpoint: String) -> Self {
        // Pre-warm TCP pool: keep-alive prevents TLS handshake on hotkey press
        let client = Client::builder()
            .pool_idle_timeout(Duration::from_secs(300))
            .pool_max_idle_per_host(10)
            .tcp_keepalive(Duration::from_secs(60))
            .build()
            .expect("Failed to build HTTP client");
        
        Self { client, endpoint }
    }

    /// Pre-warm by sending a dummy HEAD or generic request (fire and forget)
    pub async fn prewarm(&self) {
        let _ = self.client.get(&self.endpoint).send().await;
    }

    /// Parallel context capture and API request setup using tokio::join!
    pub async fn parallel_capture_and_request(
        &self, 
        prompt: String, 
        cancel_token: CancellationToken
    ) -> Result<(), String> {
        // Run UIA capture and LLM request concurrently
        let (capture_result, request_result) = tokio::join!(
            Self::capture_context_lazy(),
            self.initiate_stream(prompt, cancel_token.clone())
        );

        let mut stream = request_result?;
        let _context = capture_result?;

        let mut injector = StreamInjector::new();
        
        // Process stream
        while let Some(chunk) = stream.next().await {
            if cancel_token.is_cancelled() {
                break;
            }
            if let Ok(bytes) = chunk {
                let text = String::from_utf8_lossy(&bytes).to_string();
                injector.inject_chunk(&text).await;
            }
        }
        
        injector.flush().await;
        Ok(())
    }

    async fn capture_context_lazy() -> Result<String, String> {
        // Mock UIA capture latency
        sleep(Duration::from_millis(15)).await;
        Ok("Active window context".to_string())
    }

    async fn initiate_stream(
        &self, 
        prompt: String, 
        cancel_token: CancellationToken
    ) -> Result<impl futures_util::Stream<Item = reqwest::Result<bytes::Bytes>>, String> {
        let request = self.client
            .post(&self.endpoint)
            .json(&serde_json::json!({
                "prompt": prompt,
                "stream": true
            }));
            
        let response = request.send().await.map_err(|e| e.to_string())?;
        Ok(response.bytes_stream())
    }
}

/// Batches keystrokes into 5-character chunks with a 16ms delay.
pub struct StreamInjector {
    enigo: Enigo,
    buffer: String,
}

impl StreamInjector {
    pub fn new() -> Self {
        Self {
            enigo: Enigo::new(),
            buffer: String::new(),
        }
    }

    pub async fn inject_chunk(&mut self, text: &str) {
        self.buffer.push_str(text);
        
        while self.buffer.len() >= 5 {
            let chunk: String = self.buffer.drain(..5).collect();
            self.enigo.key_sequence(&chunk);
            sleep(Duration::from_millis(16)).await;
        }
    }

    pub async fn flush(&mut self) {
        if !self.buffer.is_empty() {
            self.enigo.key_sequence(&self.buffer);
            self.buffer.clear();
        }
    }
}
