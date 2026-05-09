use reqwest::Client;
use serde_json::{json, Value};
use anyhow::Result;

pub struct PhantomClient {
    client: Client,
    base_url: String,
}

impl PhantomClient {
    pub fn new() -> Self {
        Self {
            client: Client::new(),
            base_url: "http://127.0.0.1:7437".to_string(),
        }
    }

    pub async fn get_context(&self) -> Result<Value> {
        let resp = self.client.get(format!("{}/context", self.base_url))
            .send().await?
            .json::<Value>().await?;
        Ok(resp)
    }

    pub async fn inject(&self, text: &str) -> Result<()> {
        self.client.post(format!("{}/inject", self.base_url))
            .json(&json!({ "text": text }))
            .send().await?;
        Ok(())
    }

    pub async fn ask(&self, prompt: &str) -> Result<Value> {
        let resp = self.client.post(format!("{}/ask", self.base_url))
            .json(&json!({ "prompt": prompt }))
            .send().await?
            .json::<Value>().await?;
        Ok(resp)
    }

    pub async fn get_app(&self) -> Result<Value> {
        let resp = self.client.get(format!("{}/app", self.base_url))
            .send().await?
            .json::<Value>().await?;
        Ok(resp)
    }

    pub async fn set_agent(&self, agent: &str) -> Result<()> {
        self.client.post(format!("{}/agent", self.base_url))
            .json(&json!({ "agent": agent }))
            .send().await?;
        Ok(())
    }
}
