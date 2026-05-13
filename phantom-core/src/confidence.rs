// phantom-core/src/confidence.rs

use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConfidenceLevel {
    High,
    Medium,
    Low,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceScore {
    pub score: f32,
    pub level: ConfidenceLevel,
    pub message: String,
}

/// Calculate a confidence score based on various system factors.
pub fn calculate_confidence(
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
pub fn show_confidence_band(app_handle: &tauri::AppHandle, score: &ConfidenceScore) {
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
