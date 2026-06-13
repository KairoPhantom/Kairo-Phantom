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

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub enum ConfidenceLevel {
    High,
    Medium,
    Low,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ConfidenceScore {
    pub score: f32,
    pub level: ConfidenceLevel,
    pub message: String,
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

    /// Calculate a confidence score based on various system factors.
    pub fn calculate_context_confidence(
        context_length: usize,
        prompt: &str,
        waza_confidence: f32,
        memory_vault_hit: bool,
    ) -> ConfidenceScore {
        let mut score = 0.0;

        // Context length captured (>500 chars = +0.3)
        if context_length > 500 {
            score += 0.3;
        } else {
            score += 0.1 * (context_length as f32 / 500.0);
        }

        // Prompt clarity score: does the prompt contain a clear verb? (+0.2)
        // Simplified verb list for heuristic
        let verbs = ["write", "summarize", "edit", "explain", "draft", "create", "make", "format"];
        let prompt_lower = prompt.to_lowercase();
        if verbs.iter().any(|v| prompt_lower.contains(v)) {
            score += 0.2;
        }

        // Agent match certainty (+0.3 max)
        score += waza_confidence * 0.3;

        // Memory vault hit (+0.2)
        if memory_vault_hit {
            score += 0.2;
        }

        // Clamp score
        let score = score.clamp(0.0, 1.0);

        let (level, message) = if score >= 0.7 {
            (ConfidenceLevel::High, "● Kairo is confident".to_string())
        } else if score >= 0.4 {
            (ConfidenceLevel::Medium, "◑ Kairo is estimating".to_string())
        } else {
            (ConfidenceLevel::Low, "○ Kairo is guessing — review carefully".to_string())
        };

        ConfidenceScore {
            score,
            level,
            message,
        }
    }

    /// Setup the floating Tauri window for the confidence band
    #[cfg(feature = "tauri")]
    pub fn show_confidence_band(app_handle: &tauri::AppHandle, score: &ConfidenceScore) {
        use tauri::Manager;
        if let Some(window) = app_handle.get_window("confidence_band") {
            let _ = window.emit("confidence_update", score);
            let _ = window.show();
        } else {
            tauri::WindowBuilder::new(
                app_handle,
                "confidence_band",
                tauri::WindowUrl::App("confidence.html".into())
            )
            .inner_size(280.0, 36.0)
            .decorations(false)
            .transparent(true)
            .always_on_top(true)
            .skip_taskbar(true)
            .build()
            .unwrap();
        }
    }
}
