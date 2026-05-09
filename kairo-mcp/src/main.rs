mod protocol;
mod client;
mod tools;

use anyhow::Result;
use protocol::{JsonRpcRequest, JsonRpcResponse};
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};
use tracing::{info, error};

#[tokio::main]
async fn main() -> Result<()> {
    // Setup file logging since stdout is used for MCP protocol
    let file_appender = tracing_appender::rolling::never(".kairo-phantom", "mcp-server.log");
    tracing_subscriber::fmt()
        .with_writer(file_appender)
        .init();

    info!("🚀 kairo-mcp server starting...");

    let client = client::PhantomClient::new();
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    let mut iterator = stdin.lock().lines();

    while let Some(line) = iterator.next() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                error!("Error reading stdin: {}", e);
                break;
            }
        };

        if line.trim().is_empty() {
            continue;
        }

        let req: Result<JsonRpcRequest, _> = serde_json::from_str(&line);
        if let Ok(req) = req {
            info!("Received request: {}", req.method);

            let res = match req.method.as_str() {
                "initialize" => {
                    JsonRpcResponse::success(req.id.clone().unwrap_or(Value::Null), json!({
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "kairo-phantom-mcp",
                            "version": "3.0.0"
                        }
                    }))
                }
                "tools/list" => {
                    JsonRpcResponse::success(req.id.clone().unwrap_or(Value::Null), json!({
                        "tools": tools::get_tools()
                    }))
                }
                "tools/call" => {
                    let params = req.params.clone().unwrap_or(json!({}));
                    let name = params.get("name").and_then(|v| v.as_str()).unwrap_or("");
                    let arguments = params.get("arguments").cloned();
                    
                    match tools::handle_tool_call(name, arguments, &client).await {
                        Ok(content) => JsonRpcResponse::success(req.id.clone().unwrap_or(Value::Null), json!({
                            "content": content
                        })),
                        Err(e) => {
                            error!("Tool execution error: {}", e);
                            JsonRpcResponse::success(req.id.clone().unwrap_or(Value::Null), json!({
                                "isError": true,
                                "content": [{ "type": "text", "text": format!("Error: {}", e) }]
                            }))
                        }
                    }
                }
                _ => {
                    JsonRpcResponse::error(req.id.clone().unwrap_or(Value::Null), -32601, "Method not found".to_string())
                }
            };

            // Needs exact JSON-RPC stdio formatting (no extra prints to stdout)
            let response_str = serde_json::to_string(&res)?;
            writeln!(stdout, "{}", response_str)?;
            stdout.flush()?;
            
            // Note: MCP standard states we should send an empty initialized notification next
            // but for simplicity, responding to initialize is enough for Cursor/Claude Code
        } else {
            error!("Failed to parse request: {}", line);
        }
    }

    Ok(())
}
