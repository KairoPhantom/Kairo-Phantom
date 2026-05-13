use serde::{Deserialize, Serialize};
use tracing::info;

#[derive(Debug, Serialize, Deserialize)]
pub struct BedrockInvokeRequest {
    pub model_id: String,
    pub body: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BedrockInvokeResponse {
    pub body: String,
}

pub struct AwsEmulation;

impl AwsEmulation {
    pub async fn handle_invoke(req: BedrockInvokeRequest) -> BedrockInvokeResponse {
        info!("☁️  AWS Emulation: Invoking model {}", req.model_id);
        
        // Simulating Bedrock response format
        let response_body = serde_json::json!({
            "results": [
                {
                    "outputText": "Kairo Phantom AWS Emulation: Hello from the local engine."
                }
            ]
        });
        
        BedrockInvokeResponse {
            body: response_body.to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_bedrock_invoke() {
        let req = BedrockInvokeRequest {
            model_id: "anthropic.claude-v2".to_string(),
            body: "{}".to_string(),
        };
        let res = AwsEmulation::handle_invoke(req).await;
        assert!(res.body.contains("Kairo Phantom AWS Emulation"));
    }
}
