use regex::Regex;
use lazy_static::lazy_static;

lazy_static! {
    static ref SSN_RE: Regex = Regex::new(r"\b\d{3}-\d{2}-\d{4}\b").unwrap();
    static ref PHONE_RE: Regex = Regex::new(r"\+1-\d{3}-\d{3}-\d{4}").unwrap();
    static ref EMAIL_RE: Regex = Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b").unwrap();
    static ref CC_RE: Regex = Regex::new(r"\b(?:\d{4}[ -]?){3}\d{4}\b").unwrap();
}

pub fn mask_pii(input: &str) -> String {
    let mut masked = input.to_string();
    
    // Mask SSN
    if SSN_RE.is_match(&masked) {
        masked = SSN_RE.replace_all(&masked, "[REDACTED_SSN]").to_string();
        // Log to audit trail in real app
    }
    
    // Mask Phone
    if PHONE_RE.is_match(&masked) {
        masked = PHONE_RE.replace_all(&masked, "[REDACTED_PHONE]").to_string();
    }
    
    // Mask Email
    if EMAIL_RE.is_match(&masked) {
        masked = EMAIL_RE.replace_all(&masked, "[REDACTED_EMAIL]").to_string();
    }
    
    // Mask Credit Card
    if CC_RE.is_match(&masked) {
        masked = CC_RE.replace_all(&masked, "[REDACTED_CC]").to_string();
    }
    
    masked
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pii_masking() {
        let text = "Contact john.doe@example.com or call +1-555-123-4567. My SSN is 123-45-6789 and card is 1234-5678-9012-3456.";
        let masked = mask_pii(text);
        
        assert_eq!(
            masked,
            "Contact [REDACTED_EMAIL] or call [REDACTED_PHONE]. My SSN is [REDACTED_SSN] and card is [REDACTED_CC]."
        );
    }
}
