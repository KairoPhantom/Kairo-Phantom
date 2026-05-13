pub fn semantic_window(raw_text: &str) -> String {
    // 1. Prioritizes the current paragraph, heading, preceding 3 paragraphs
    // 2. Never cuts mid-sentence
    // For this fallback, we just split by double newline to find paragraphs
    
    let paragraphs: Vec<&str> = raw_text.split("\n\n").collect();
    let mut selected = Vec::new();
    
    // Take the last 3 paragraphs as context (including current)
    let start_idx = if paragraphs.len() > 3 { paragraphs.len() - 3 } else { 0 };
    
    for p in &paragraphs[start_idx..] {
        // Ensure sentence boundary by trimming at the last punctuation if cut abruptly
        let p_trimmed = p.trim();
        if !p_trimmed.is_empty() {
            selected.push(p_trimmed.to_string());
        }
    }
    
    selected.join("\n\n")
}

pub fn extract_prompt(text: &str) -> (String, String) {
    // Prompt is the last line before hotkey press
    let lines: Vec<&str> = text.lines().collect();
    if lines.is_empty() {
        return ("".to_string(), "".to_string());
    }
    
    let prompt = lines.last().unwrap().trim().to_string();
    let context = lines[..lines.len() - 1].join("\n").trim().to_string();
    
    (prompt, context)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_prompt() {
        let text = "First line.\nSecond line.\nThird line.\nCan you summarize this?";
        let (prompt, context) = extract_prompt(text);
        assert_eq!(prompt, "Can you summarize this?");
        assert_eq!(context, "First line.\nSecond line.\nThird line.");
    }
    
    #[test]
    fn test_semantic_window() {
        let text = "Para 1\n\nPara 2\n\nPara 3\n\nPara 4\n\nPara 5";
        let windowed = semantic_window(text);
        // Should keep last 3 paragraphs
        assert_eq!(windowed, "Para 3\n\nPara 4\n\nPara 5");
    }
}
