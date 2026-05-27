// phantom-core/src/code_context.rs
//
// Syntax-aware code context extraction for Kairo Phantom.
// Supports 8 target languages: Rust, Python, Go, C#, Java, TypeScript, JavaScript.
// Incorporates tree-sitter AST parsing for Rust and Python, with high-fidelity
// lexical fallback for robust production use.

use std::fs::File;
use std::io::{self, Read};
use std::path::Path;
use anyhow::{Result, Context as AnyhowContext};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LineEnding {
    CRLF,
    LF,
}

impl LineEnding {
    pub fn as_str(&self) -> &'static str {
        match self {
            LineEnding::CRLF => "\r\n",
            LineEnding::LF => "\n",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionInfo {
    pub name: String,
    pub signature: String,
    pub start_line: usize,
    pub end_line: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeContext {
    pub file_path: String,
    pub language: String,
    pub cursor_line: usize,
    pub cursor_col: usize,
    pub enclosing_function: Option<FunctionInfo>,
    pub enclosing_class: Option<String>,
    pub imports: Vec<String>,
    pub nearby_symbols: Vec<String>,
    pub surrounding_code: String,     // 30 lines around cursor
    pub indentation: String,          // whitespace prefix at cursor line
    pub line_ending: LineEnding,      // CRLF or LF
}

/// Detect language from file extension
pub fn detect_language(ext: &str) -> String {
    match ext.to_lowercase().as_str() {
        "rs" => "rust".to_string(),
        "py" => "python".to_string(),
        "go" => "go".to_string(),
        "cs" => "c_sharp".to_string(),
        "java" => "java".to_string(),
        "ts" | "tsx" => "typescript".to_string(),
        "js" | "jsx" => "javascript".to_string(),
        _ => "plaintext".to_string(),
    }
}

/// Helper function to extract AST context using tree-sitter for Rust and Python
fn extract_ast_context(
    source_code: &str,
    language: &str,
    cursor_line: usize,
) -> Option<(Option<FunctionInfo>, Option<String>, Vec<String>, Vec<String>)> {
    let mut parser = tree_sitter::Parser::new();
    let lang = match language {
        "rust" => tree_sitter_rust::language(),
        "python" => tree_sitter_python::language(),
        _ => return None,
    };
    parser.set_language(&lang).ok()?;
    
    let tree = parser.parse(source_code, None)?;
    let root = tree.root_node();
    
    // 0-based point
    let row = cursor_line.saturating_sub(1);
    let target_point = tree_sitter::Point { row, column: 0 };
    
    let mut enclosing_func = None;
    let mut enclosing_class = None;
    let mut imports = Vec::new();
    let mut nearby_symbols = Vec::new();
    
    walk_ast(
        root,
        target_point,
        source_code,
        &mut enclosing_func,
        &mut enclosing_class,
        &mut imports,
        &mut nearby_symbols,
    );
    
    // Dedup imports and nearby symbols
    imports.sort();
    imports.dedup();
    
    nearby_symbols.sort();
    nearby_symbols.dedup();
    nearby_symbols.truncate(15);
    
    Some((enclosing_func, enclosing_class, imports, nearby_symbols))
}

fn walk_ast(
    node: tree_sitter::Node,
    target: tree_sitter::Point,
    source: &str,
    enclosing_func: &mut Option<FunctionInfo>,
    enclosing_class: &mut Option<String>,
    imports: &mut Vec<String>,
    nearby_symbols: &mut Vec<String>,
) {
    let start = node.start_position();
    let end = node.end_position();
    let node_type = node.kind();
    
    // Check if target point is within node boundaries
    let contains_target = (start.row < target.row || (start.row == target.row && start.column <= target.column))
        && (end.row > target.row || (end.row == target.row && end.column >= target.column));
        
    // Identify imports
    if node_type == "import_statement" || node_type == "import_from_statement" || node_type == "use_declaration" {
        if let Ok(text) = node.utf8_text(source.as_bytes()) {
            imports.push(text.trim().to_string());
        }
    }
    
    // Identify nearby functions/structs/classes
    if node_type == "function_definition" || node_type == "function_item" ||
       node_type == "class_definition" || node_type == "struct_item" || node_type == "impl_item" {
        if let Ok(text) = node.utf8_text(source.as_bytes()) {
            let signature = text.lines().next().unwrap_or("").to_string();
            nearby_symbols.push(signature);
        }
    }
    
    if contains_target {
        if node_type == "function_definition" || node_type == "function_item" {
            if let Ok(text) = node.utf8_text(source.as_bytes()) {
                let signature = text.lines().next().unwrap_or("").to_string();
                let name = node.child_by_field_name("name")
                    .and_then(|n| n.utf8_text(source.as_bytes()).ok())
                    .unwrap_or("unknown")
                    .to_string();
                    
                *enclosing_func = Some(FunctionInfo {
                    name,
                    signature,
                    start_line: start.row + 1,
                    end_line: end.row + 1,
                });
            }
        } else if node_type == "class_definition" {
            if let Some(name_node) = node.child_by_field_name("name") {
                if let Ok(name_str) = name_node.utf8_text(source.as_bytes()) {
                    *enclosing_class = Some(name_str.to_string());
                }
            }
        } else if node_type == "struct_item" {
            if let Some(name_node) = node.child_by_field_name("name") {
                if let Ok(name_str) = name_node.utf8_text(source.as_bytes()) {
                    *enclosing_class = Some(format!("struct {}", name_str));
                }
            }
        } else if node_type == "impl_item" {
            if let Some(type_node) = node.child_by_field_name("type") {
                if let Ok(type_str) = type_node.utf8_text(source.as_bytes()) {
                    *enclosing_class = Some(type_str.trim().to_string());
                }
            } else if let Ok(text) = node.utf8_text(source.as_bytes()) {
                let signature = text.lines().next().unwrap_or("").to_string();
                *enclosing_class = Some(signature);
            }
        }
    }
    
    // Recurse into children
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        walk_ast(child, target, source, enclosing_func, enclosing_class, imports, nearby_symbols);
    }
}

/// Extract lexical context (fallback for non-AST languages or failed parsing)
fn extract_lexical_context(
    lines: &[String],
    language: &str,
    cursor_idx: usize,
    cursor_line_text: &str,
) -> (Option<FunctionInfo>, Option<String>, Vec<String>, Vec<String>) {
    let mut enclosing_function = None;
    let mut enclosing_class = None;
    let mut imports = Vec::new();
    let mut nearby_symbols = Vec::new();

    match language {
        "python" => {
            let mut current_idx = cursor_idx;
            while current_idx > 0 {
                current_idx -= 1;
                let line_text = &lines[current_idx];
                let trimmed = line_text.trim_start();
                if trimmed.starts_with("def ") {
                    let func_indent = line_text.len() - trimmed.len();
                    let cursor_line_indent = cursor_line_text.len() - cursor_line_text.trim_start().len();
                    if cursor_idx == current_idx || cursor_line_indent > func_indent || cursor_line_text.trim().is_empty() {
                        let parts: Vec<&str> = trimmed.split_whitespace().collect();
                        if parts.len() > 1 {
                            let func_name = parts[1].split('(').next().unwrap_or("").to_string();
                            let mut end_line = lines.len();
                            for check_idx in (current_idx + 1)..lines.len() {
                                let check_line = &lines[check_idx];
                                let check_trimmed = check_line.trim_start();
                                if !check_trimmed.is_empty() {
                                    let check_indent = check_line.len() - check_trimmed.len();
                                    if check_indent <= func_indent {
                                        end_line = check_idx;
                                        break;
                                    }
                                }
                            }
                            enclosing_function = Some(FunctionInfo {
                                name: func_name,
                                signature: trimmed.to_string(),
                                start_line: current_idx + 1,
                                end_line,
                            });
                            break;
                        }
                    }
                } else if trimmed.starts_with("class ") {
                    let parts: Vec<&str> = trimmed.split_whitespace().collect();
                    if parts.len() > 1 {
                        let class_name = parts[1].split(':').next().unwrap_or("").split('(').next().unwrap_or("").to_string();
                        enclosing_class = Some(class_name);
                        break;
                    }
                }
            }

            for line in lines {
                let trimmed = line.trim();
                if trimmed.starts_with("import ") || trimmed.starts_with("from ") {
                    imports.push(trimmed.to_string());
                }
            }

            let symbol_start = cursor_idx.saturating_sub(20);
            let symbol_end = std::cmp::min(lines.len(), cursor_idx + 21);
            for line in &lines[symbol_start..symbol_end] {
                let trimmed = line.trim();
                if trimmed.starts_with("def ") || trimmed.starts_with("class ") {
                    nearby_symbols.push(trimmed.to_string());
                }
            }
        }
        "rust" => {
            let mut current_idx = cursor_idx;
            let mut brace_count: usize = 0;
            while current_idx > 0 {
                current_idx -= 1;
                let line_text = &lines[current_idx];
                let trimmed = line_text.trim();
                
                if trimmed.contains('}') { brace_count += 1; }
                if trimmed.contains('{') { brace_count = brace_count.saturating_sub(1); }

                if (trimmed.contains("fn ") || trimmed.starts_with("fn ")) && brace_count == 0 {
                    let parts: Vec<&str> = trimmed.split("fn ").collect();
                    if parts.len() > 1 {
                        let name_part = parts[1].split('(').next().unwrap_or("").trim();
                        if !name_part.is_empty() {
                            let mut b_count = 0;
                            let mut end_line = lines.len();
                            for (idx, l) in lines.iter().enumerate().skip(current_idx) {
                                if l.contains('{') { b_count += 1; }
                                if l.contains('}') { b_count -= 1; }
                                if b_count == 0 && idx > current_idx {
                                    end_line = idx + 1;
                                    break;
                                }
                            }
                            enclosing_function = Some(FunctionInfo {
                                name: name_part.to_string(),
                                signature: trimmed.to_string(),
                                start_line: current_idx + 1,
                                end_line,
                            });
                            break;
                        }
                    }
                } else if trimmed.starts_with("impl") || trimmed.starts_with("pub struct") || trimmed.starts_with("struct ") {
                    enclosing_class = Some(trimmed.to_string());
                }
            }

            for line in lines {
                let trimmed = line.trim();
                if trimmed.starts_with("use ") {
                    imports.push(trimmed.to_string());
                }
            }

            let symbol_start = cursor_idx.saturating_sub(20);
            let symbol_end = std::cmp::min(lines.len(), cursor_idx + 21);
            for line in &lines[symbol_start..symbol_end] {
                let trimmed = line.trim();
                if trimmed.contains("fn ") || trimmed.starts_with("struct ") || trimmed.starts_with("impl ") {
                    nearby_symbols.push(trimmed.to_string());
                }
            }
        }
        _ => {
            let mut current_idx = cursor_idx;
            while current_idx > 0 {
                current_idx -= 1;
                let line_text = &lines[current_idx];
                let trimmed = line_text.trim();
                if (trimmed.contains("function ") || trimmed.contains("func ") || trimmed.contains("void ") || trimmed.contains("int ") || trimmed.contains("public ")) 
                    && trimmed.contains('(') {
                    let parts: Vec<&str> = trimmed.split('(').collect();
                    let name_words: Vec<&str> = parts[0].split_whitespace().collect();
                    if let Some(&name) = name_words.last() {
                        let name_clean = name.trim_start_matches('*').to_string();
                        let mut b_count = 0;
                        let mut end_line = lines.len();
                        for (idx, l) in lines.iter().enumerate().skip(current_idx) {
                            if l.contains('{') { b_count += 1; }
                            if l.contains('}') { b_count -= 1; }
                            if b_count == 0 && idx > current_idx {
                                    end_line = idx + 1;
                                    break;
                            }
                        }
                        enclosing_function = Some(FunctionInfo {
                            name: name_clean,
                            signature: trimmed.to_string(),
                            start_line: current_idx + 1,
                            end_line,
                        });
                        break;
                    }
                } else if trimmed.starts_with("class ") {
                    enclosing_class = Some(trimmed.to_string());
                }
            }

            for line in lines {
                let trimmed = line.trim();
                if trimmed.starts_with("import ") || trimmed.starts_with("using ") || trimmed.starts_with("include ") || trimmed.starts_with("require(") {
                    imports.push(trimmed.to_string());
                }
            }
        }
    }

    (enclosing_function, enclosing_class, imports, nearby_symbols)
}

/// Extract context from a source code file. Uses tree-sitter AST parsing where supported,
/// with robust fallback to lexical analysis.
pub fn extract_code_context(file_path: &str, cursor_line: usize) -> Result<CodeContext> {
    let path = Path::new(file_path);
    if !path.exists() {
        return Err(anyhow::anyhow!("File not found: {}", file_path));
    }

    let mut file = File::open(path).context("Failed to open code file")?;
    let mut source_code = String::new();
    file.read_to_string(&mut source_code).context("Failed to read code file content")?;
    
    let mut line_ending = LineEnding::LF;
    if source_code.contains("\r\n") {
        line_ending = LineEnding::CRLF;
    }
    
    let mut lines = Vec::new();
    for line in source_code.lines() {
        lines.push(line.to_string());
    }

    let ext = path.extension()
        .and_then(|e| e.to_str())
        .unwrap_or("");
    let language = detect_language(ext);

    let adjusted_cursor = if cursor_line == 0 { 1 } else { cursor_line };
    let cursor_idx = adjusted_cursor.saturating_sub(1);
    
    let cursor_line_text = lines.get(cursor_idx).cloned().unwrap_or_default();
    let indentation = cursor_line_text.chars()
        .take_while(|c| c.is_whitespace())
        .collect::<String>();

    let start_surrounding = cursor_idx.saturating_sub(15);
    let end_surrounding = std::cmp::min(lines.len(), cursor_idx + 16);
    let surrounding_lines = &lines[start_surrounding..end_surrounding];
    let surrounding_code = surrounding_lines.join(line_ending.as_str());

    // Try AST extraction first for Rust and Python
    let (enclosing_function, enclosing_class, imports, nearby_symbols) = 
        if language == "rust" || language == "python" {
            match extract_ast_context(&source_code, &language, adjusted_cursor) {
                Some(ast_res) => ast_res,
                None => {
                    tracing::warn!("[CodeContext] Tree-sitter extraction failed, falling back to lexical parser.");
                    extract_lexical_context(&lines, &language, cursor_idx, &cursor_line_text)
                }
            }
        } else {
            extract_lexical_context(&lines, &language, cursor_idx, &cursor_line_text)
        };

    Ok(CodeContext {
        file_path: file_path.to_string(),
        language,
        cursor_line,
        cursor_col: indentation.len(),
        enclosing_function,
        enclosing_class,
        imports,
        nearby_symbols,
        surrounding_code,
        indentation,
        line_ending,
    })
}
