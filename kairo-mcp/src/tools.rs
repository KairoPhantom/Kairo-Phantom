use serde_json::{json, Value};
use anyhow::Result;
use crate::client::PhantomClient;
use tracing::info;

async fn call_docsagent_index(file_path: &str) -> Result<()> {
    info!("DocsAgent: Indexing document: {}", file_path);
    // Execute DocsAgent CLI to index the document locally
    let _ = tokio::process::Command::new("npx")
        .args(&["-y", "@google/docsagent", "index", file_path])
        .status()
        .await;
    Ok(())
}

async fn call_docsagent_search(query: &str) -> Result<String> {
    info!("DocsAgent: Searching documents for query: {}", query);
    // Execute DocsAgent CLI search
    let output = tokio::process::Command::new("npx")
        .args(&["-y", "@google/docsagent", "search", query])
        .output()
        .await;
    match output {
        Ok(out) => {
            let res = String::from_utf8_lossy(&out.stdout).to_string();
            if res.trim().is_empty() {
                Ok("No matches found in DocsAgent local database.".to_string())
            } else {
                Ok(res)
            }
        }
        Err(_) => Ok("DocsAgent search failed. Make sure @google/docsagent is installed locally.".to_string())
    }
}

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
        },
        {
            "name": "docsagent_index",
            "description": "Index a document path in DocsAgent for Q&A.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "The absolute file path to index" }
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "docsagent_search",
            "description": "Search indexed documents for a query via DocsAgent.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Search query text" }
                },
                "required": ["query"]
            }
        }
    ])
}

pub async fn handle_tool_call(name: &str, args: Option<Value>, client: &PhantomClient) -> Result<Value> {
    match name {
        "kairo_read_context" => {
            let context = client.get_context().await?;
            if let Some(file_path) = context.get("file_path").and_then(|v| v.as_str()) {
                if !file_path.is_empty() {
                    let _ = call_docsagent_index(file_path).await;
                }
            }
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
        "docsagent_index" => {
            let args = args.unwrap_or(json!({}));
            let file_path = args.get("file_path").and_then(|v| v.as_str()).unwrap_or("");
            call_docsagent_index(file_path).await?;
            Ok(json!([{ "type": "text", "text": format!("Successfully scheduled DocsAgent indexing for: {}", file_path) }]))
        }
        "docsagent_search" => {
            let args = args.unwrap_or(json!({}));
            let query = args.get("query").and_then(|v| v.as_str()).unwrap_or("");
            let search_results = call_docsagent_search(query).await?;
            Ok(json!([{ "type": "text", "text": search_results }]))
        }
        _ => Err(anyhow::anyhow!("Unknown tool: {}", name))
    }
}
