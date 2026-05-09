use serde_json::{json, Value};
use anyhow::Result;
use crate::client::PhantomClient;

pub fn get_tools() -> Value {
    json!([
        {
            "name": "kairo_read_context",
            "description": "Read the text context and environment (app name) from the currently focused window where the user's cursor is.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "kairo_ghost_write",
            "description": "Inject text directly into the user's focused document or terminal, as if typed by the user.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": { "type": "string", "description": "The exact text to type into the window" }
                },
                "required": ["text"]
            }
        },
        {
            "name": "kairo_ask",
            "description": "Send a prompt to the Kairo Swarm Orchestrator. It will read the user's current context, pick the best specialized agent, generate a response, and ghost-type it.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": { "type": "string", "description": "Instructions for what to generate" }
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "kairo_detect_app",
            "description": "Get only the current application process name and document kind environment without reading all text context.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "kairo_switch_agent",
            "description": "Override the automatic swarm routing for the next kairo_ask request. Choose from 'design', 'reasoning', or 'content'.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": { "type": "string", "enum": ["design", "reasoning", "content"], "description": "The agent specialization to use next" }
                },
                "required": ["agent"]
            }
        }
    ])
}

pub async fn handle_tool_call(name: &str, args: Option<Value>, client: &PhantomClient) -> Result<Value> {
    match name {
        "kairo_read_context" => {
            let context = client.get_context().await?;
            Ok(json!([{ "type": "text", "text": format!("App: {}\nWindow: {}\nContext:\n{}", 
                context["process_name"], 
                context["window_title"], 
                context["extracted_text"]
            )}]))
        }
        "kairo_ghost_write" => {
            let args = args.unwrap_or(json!({}));
            let text = args.get("text").and_then(|v| v.as_str()).unwrap_or("");
            client.inject(text).await?;
            Ok(json!([{ "type": "text", "text": "Successfully injected text." }]))
        }
        "kairo_ask" => {
            let args = args.unwrap_or(json!({}));
            let prompt = args.get("prompt").and_then(|v| v.as_str()).unwrap_or("");
            let response = client.ask(prompt).await?;
            Ok(json!([{ "type": "text", "text": format!("Generated and injected response:\n{}", response["response"]) }]))
        }
        "kairo_detect_app" => {
            let app = client.get_app().await?;
            Ok(json!([{ "type": "text", "text": format!("Process: {}\nEnvironment: {}", 
                app["process"], 
                app["environment"]
            )}]))
        }
        "kairo_switch_agent" => {
            let args = args.unwrap_or(json!({}));
            let agent = args.get("agent").and_then(|v| v.as_str()).unwrap_or("content");
            client.set_agent(agent).await?;
            Ok(json!([{ "type": "text", "text": format!("Agent overriden to '{}' for the next generation.", agent) }]))
        }
        _ => Err(anyhow::anyhow!("Unknown tool: {}", name))
    }
}
