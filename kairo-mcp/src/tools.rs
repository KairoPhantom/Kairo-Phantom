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
        },
        {
            "name": "kairo_word_process",
            "description": "Word/DOCX domain: extract context, generate response, apply operations to a Word document.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the .docx file" },
                    "instruction": { "type": "string", "description": "User instruction for the Word master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_excel_process",
            "description": "Excel/spreadsheet domain: extract context, generate formulas, validate and apply operations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the .xlsx file" },
                    "instruction": { "type": "string", "description": "User instruction for the Excel master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_pptx_process",
            "description": "PowerPoint domain: extract slide context, generate slide content, apply operations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the .pptx file" },
                    "instruction": { "type": "string", "description": "User instruction for the PPTX master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_pdf_process",
            "description": "PDF domain: extract text, tables, and form fields from PDF documents.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the PDF file" },
                    "instruction": { "type": "string", "description": "User instruction for the PDF master" }
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "kairo_legal_process",
            "description": "Legal domain: CUAD clause extraction, citation graph, redline comparison.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the legal document" },
                    "instruction": { "type": "string", "description": "User instruction for the Legal master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_design_process",
            "description": "Design domain: Figma/tldraw bridge, canvas operations, design generation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the design file" },
                    "instruction": { "type": "string", "description": "User instruction for the Design master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_code_process",
            "description": "Code domain: tree-sitter parsing, code graph, code generation and analysis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the code file" },
                    "instruction": { "type": "string", "description": "User instruction for the Code master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_media_process",
            "description": "Media domain: image processing, embeddings, transcription.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the media file" },
                    "instruction": { "type": "string", "description": "User instruction for the Media master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_browser_process",
            "description": "Browser domain: web page context extraction, browser automation guidance.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": { "type": "string", "description": "URL of the web page" },
                    "instruction": { "type": "string", "description": "User instruction for the Browser master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_terminal_process",
            "description": "Terminal domain: safe command generation, shell context awareness.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "instruction": { "type": "string", "description": "User instruction for the Terminal master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_email_process",
            "description": "Email domain: email drafting, subject validation, PII redaction.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "instruction": { "type": "string", "description": "User instruction for the Email master" }
                },
                "required": ["instruction"]
            }
        },
        {
            "name": "kairo_notes_process",
            "description": "Notes domain: Obsidian/Logseq/Markdown note management and generation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": { "type": "string", "description": "Path to the notes file" },
                    "instruction": { "type": "string", "description": "User instruction for the Notes master" }
                },
                "required": ["instruction"]
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
        // 12 Domain Tools — route through sidecar HTTP API
        "kairo_word_process" | "kairo_excel_process" | "kairo_pptx_process" |
        "kairo_pdf_process" | "kairo_legal_process" | "kairo_design_process" |
        "kairo_code_process" | "kairo_media_process" | "kairo_browser_process" |
        "kairo_terminal_process" | "kairo_email_process" | "kairo_notes_process" => {
            let args = args.unwrap_or(json!({}));
            let instruction = args.get("instruction").and_then(|v| v.as_str()).unwrap_or("");
            let file_path = args.get("file_path").or(args.get("url")).and_then(|v| v.as_str()).unwrap_or("");

            // Route through the sidecar ask endpoint with domain-specific context
            let domain = name.strip_prefix("kairo_").unwrap_or("").strip_suffix("_process").unwrap_or("");
            let prompt = format!("Domain: {}\nFile: {}\nInstruction: {}", domain, file_path, instruction);

            match client.ask(&prompt).await {
                Ok(response) => Ok(json!([{ "type": "text", "text": format!("Domain '{}' tool executed.\nResponse: {}", domain, response["response"]) }])),
                Err(e) => {
                    // Sidecar not running — return structured error (not a crash)
                    Ok(json!([{ "type": "text", "text": format!("Domain '{}' tool called but sidecar not reachable: {}. Start sidecar with: cd kairo-sidecar && python sidecar.py", domain, e) }]))
                }
            }
        }
        _ => Err(anyhow::anyhow!("Unknown tool: {}", name))
    }
}
