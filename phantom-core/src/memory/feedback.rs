use strsim::normalized_levenshtein;
use tracing::info;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FeedbackSignal {
    pub channel: String,
    pub from: String,
    pub to: String,
    pub confidence: f64,
}

pub struct FeedbackClassifier;

impl FeedbackClassifier {
    /// Analyzes the diff between rejected AI output and user's manual correction.
    pub fn classify(original: &str, corrected: &str) -> Vec<FeedbackSignal> {
        let mut signals = Vec::new();
        
        let sim = normalized_levenshtein(original, corrected);
        
        // 1. Check for format change (e.g., bullets to prose)
        if original.contains("- ") && !corrected.contains("- ") {
            signals.push(FeedbackSignal {
                channel: "format_changed".into(),
                from: "bullet".into(),
                to: "prose".into(),
                confidence: 0.9,
            });
        } else if !original.contains("- ") && corrected.contains("- ") {
            signals.push(FeedbackSignal {
                channel: "format_changed".into(),
                from: "prose".into(),
                to: "bullet".into(),
                confidence: 0.9,
            });
        }

        // 2. Check for length change
        let orig_len = original.split_whitespace().count();
        let corr_len = corrected.split_whitespace().count();
        
        if corr_len < orig_len / 2 {
            signals.push(FeedbackSignal {
                channel: "length_preference".into(),
                from: "verbose".into(),
                to: "concise".into(),
                confidence: 0.8,
            });
        }

        // 3. Generic tone/content mismatch if similarity is low
        if sim < 0.6 {
            signals.push(FeedbackSignal {
                channel: "tone_mismatch".into(),
                from: "hallucinated/wrong_tone".into(),
                to: "user_style".into(),
                confidence: 0.5,
            });
        }

        info!("🧠 PAHF: Detected feedback signals: {:?}", signals);
        signals
    }
}

pub struct ConfidenceEngine;

impl ConfidenceEngine {
    /// Calculates confidence for a proposed response based on past feedback.
    pub fn calculate_confidence(app: &str, response: &str, history: &[FeedbackSignal]) -> f64 {
        let mut confidence: f64 = 0.95; // Baseline high confidence
        
        for signal in history {
            // If we have a history of changing format in this app, lower confidence if new response uses old format
            if signal.channel == "format_changed" && app.to_lowercase().contains("word")
                && signal.to == "prose" && response.contains("- ") {
                    confidence -= 0.15;
                }
            
            if signal.channel == "length_preference" && signal.to == "concise"
                && response.split_whitespace().count() > 100 {
                    confidence -= 0.1;
                }
        }
        
        confidence.clamp(0.1, 1.0)
    }
}
