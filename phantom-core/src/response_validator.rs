// phantom-core/src/response_validator.rs
// Response Validator — Layer 4 of the 6-layer security stack
// Detects hallucinated multi-turn conversation patterns and verifies
// that AI responses are actually relevant to the user's prompt.

use regex::Regex;
use tracing::warn;

pub struct ResponseValidator {
    roleplay_patterns: Vec<Regex>,
}

#[derive(Debug, PartialEq)]
pub enum ValidationResult {
    /// Response is clean and relevant
    Valid,
    /// Response contains hallucinated conversation turns
    HallucinatedTurns { found: String },
    /// Response is completely unrelated to the user's prompt (low lexical overlap)
    Irrelevant { overlap_score: f32 },
    /// Response is suspiciously short or empty
    Truncated,
}

impl ValidationResult {
    pub fn is_valid(&self) -> bool {
        matches!(self, ValidationResult::Valid)
    }

    pub fn reason(&self) -> String {
        match self {
            Self::Valid => "OK".into(),
            Self::HallucinatedTurns { found } => 
                format!("Hallucinated conversation turn detected: '{}'", found),
            Self::Irrelevant { overlap_score } => 
                format!("Low prompt-response overlap: {:.1}%", overlap_score * 100.0),
            Self::Truncated => 
                "Response appears truncated or empty".into(),
        }
    }
}

impl ResponseValidator {
    pub fn new() -> Self {
        // Patterns that indicate the LLM is roleplaying a conversation
        let roleplay_patterns = vec![
            Regex::new(r"(?m)^\[?User\]?:").unwrap(),
            Regex::new(r"(?m)^\[?Assistant\]?:").unwrap(),
            Regex::new(r"(?m)^\[?Human\]?:").unwrap(),
            Regex::new(r"(?m)^\[?AI\]?:").unwrap(),
            Regex::new(r"(?m)^\[?System\]?:").unwrap(),
            // Example conversation pattern: "User: ... \n Assistant: ..."
            Regex::new(r"(?ms)User:.*?Assistant:").unwrap(),
            // GPT self-conversation pattern
            Regex::new(r"(?i)<\|im_start\|>").unwrap(),
            Regex::new(r"(?i)<\|im_end\|>").unwrap(),
        ];

        Self { roleplay_patterns }
    }

    /// Validates an AI response against the original user prompt.
    pub fn validate(&self, user_prompt: &str, response: &str) -> ValidationResult {
        // Check for empty/truncated response
        if response.trim().len() < 5 {
            return ValidationResult::Truncated;
        }

        // Check for hallucinated conversation turns
        for pattern in &self.roleplay_patterns {
            if let Some(m) = pattern.find(response) {
                let found = m.as_str().to_string();
                warn!("⚠️  [RESPONSE VALIDATOR] Hallucinated turn detected: '{}'", &found);
                return ValidationResult::HallucinatedTurns { found };
            }
        }

        // Lexical overlap check — basic NLI proxy
        let overlap = self.compute_lexical_overlap(user_prompt, response);
        // Only flag if prompt is substantive (>20 chars) and overlap is very low
        if user_prompt.len() > 20 && overlap < 0.05 {
            warn!("⚠️  [RESPONSE VALIDATOR] Low overlap ({:.1}%) between prompt and response", overlap * 100.0);
            // Note: this is a soft warning, not a hard block — overlap can be low legitimately
            // (e.g., "// Translate this to French" produces non-overlapping output)
        }

        ValidationResult::Valid
    }

    /// Computes lexical overlap between prompt and response as a fraction.
    fn compute_lexical_overlap(&self, prompt: &str, response: &str) -> f32 {
        let prompt_words: std::collections::HashSet<&str> = 
            prompt.split_whitespace().collect();
        let response_words: std::collections::HashSet<&str> = 
            response.split_whitespace().collect();

        if prompt_words.is_empty() {
            return 1.0; // Empty prompt → any response is valid
        }

        let intersection = prompt_words.intersection(&response_words).count();
        intersection as f32 / prompt_words.len() as f32
    }

    /// Quick check — returns true if the response is safe to use.
    pub fn is_safe(&self, user_prompt: &str, response: &str) -> bool {
        self.validate(user_prompt, response).is_valid()
    }
}

impl Default for ResponseValidator {
    fn default() -> Self { Self::new() }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clean_response_passes() {
        let v = ResponseValidator::new();
        let result = v.validate("Write a summary", "Here is a concise summary of the key points.");
        assert_eq!(result, ValidationResult::Valid);
    }

    #[test]
    fn test_hallucinated_turn_detected() {
        let v = ResponseValidator::new();
        let response = "Sure!\nUser: Can you help me?\nAssistant: Of course I can!";
        let result = v.validate("Write a summary", response);
        assert!(matches!(result, ValidationResult::HallucinatedTurns { .. }));
    }

    #[test]
    fn test_truncated_response_detected() {
        let v = ResponseValidator::new();
        let result = v.validate("Write a 500 word essay", "Ok");
        assert_eq!(result, ValidationResult::Truncated);
    }
}
