// phantom-core/src/memory.rs
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::info;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct UserPreference {
    pub key: String,
    pub value: String,
    pub weight: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Interaction {
    pub app: String,
    pub prompt: String,
    pub response: String,
    pub accepted: bool,
    pub timestamp: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SessionMemory {
    pub active_document: String,
    pub recent_interactions: Vec<Interaction>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SkillMemory {
    pub reusable_patterns: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct UserModel {
    pub user_id: String,
    pub word_preferences: HashMap<String, String>,
    pub ppt_preferences: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct KnowledgeGraph {
    pub nodes: Vec<String>,
    pub edges: Vec<(usize, usize, String)>, // (from_idx, to_idx, relationship)
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct KairoMemory {
    pub preferences: Vec<UserPreference>,
    pub interactions: Vec<Interaction>,
    pub app_bias: HashMap<String, String>,
    pub session: SessionMemory,
    pub skill: SkillMemory,
    pub user_model: UserModel,
    pub graph: KnowledgeGraph,
}

impl KairoMemory {
    pub fn new() -> Self {
        // In production, this would load from a local database (SurrealDB/SQLite)
        Self::default()
    }

    pub fn learn_from_interaction(&mut self, interaction: Interaction) {
        info!("🧠 Memory learning from interaction in {}", interaction.app);
        
        // Stylistic Extraction Logic
        if interaction.accepted {
            // Detect technical level
            if interaction.response.contains("struct") || interaction.response.contains("impl") || interaction.response.contains("pub fn") {
                self.add_preference("technical_level", "highly technical / code-centric", 0.2);
            } else if interaction.response.contains("strategic") || interaction.response.contains("roadmap") {
                self.add_preference("technical_level", "executive / strategic", 0.2);
            }

            // Detect tone
            if interaction.response.contains("!") || interaction.response.contains("exciting") {
                self.add_preference("tone", "energetic / optimistic", 0.1);
            } else if interaction.response.contains("shall") || interaction.response.contains("hereby") {
                self.add_preference("tone", "formal / legalistic", 0.3);
            }

            // Detect formatting
            if interaction.response.contains("- ") {
                self.add_preference("formatting", "prefers bullet points", 0.1);
            }
            if interaction.response.contains("| --- |") {
                self.add_preference("formatting", "uses markdown tables", 0.2);
            }

            // Graph-based concept extraction
            self.graph_update(&interaction.prompt, &interaction.response);
        }
        
        self.interactions.push(interaction);
    }

    fn graph_update(&mut self, prompt: &str, response: &str) {
        let concepts = self.extract_concepts(prompt, response);
        for concept in concepts {
            if !self.graph.nodes.contains(&concept) {
                self.graph.nodes.push(concept);
            }
        }
        
        // Simple relationship linking (subject-object-predicate heuristic)
        if self.graph.nodes.len() >= 2 {
            let last = self.graph.nodes.len() - 1;
            let prev = last - 1;
            self.graph.edges.push((prev, last, "related_to".to_string()));
        }
    }

    fn extract_concepts(&self, prompt: &str, response: &str) -> Vec<String> {
        let mut concepts = Vec::new();
        // Heuristic: capitalized words in technical contexts
        for word in prompt.split_whitespace().chain(response.split_whitespace()) {
            if word.len() > 3 && word.chars().next().unwrap().is_uppercase() {
                concepts.push(word.trim_matches(|c: char| !c.is_alphanumeric()).to_string());
            }
        }
        concepts.truncate(5);
        concepts
    }

    pub fn add_preference(&mut self, category: &str, value: &str, boost: f32) {
        let key = category.to_string();
        if let Some(pref) = self.preferences.iter_mut().find(|p| p.key == key && p.value == value) {
            pref.weight += boost;
        } else {
            self.preferences.push(UserPreference {
                key,
                value: value.to_string(),
                weight: boost,
            });
        }
    }

    pub fn build_memory_fragment(&self, app_name: &str) -> String {
        let mut parts = Vec::new();
        parts.push("## USER MEMORY (PERSISTENT)".to_string());
        
        // Find top preferences
        for pref in self.preferences.iter().filter(|p| p.weight > 0.5) {
            parts.push(format!("- {}: {}", pref.key, pref.value));
        }
        
        if let Some(bias) = self.app_bias.get(app_name) {
            parts.push(format!("- App-specific pattern: {}", bias));
        }

        parts.push("\n## USER MODEL".to_string());
        for (k, v) in &self.user_model.word_preferences {
            parts.push(format!("- Word Pref {}: {}", k, v));
        }
        for (k, v) in &self.user_model.ppt_preferences {
            parts.push(format!("- PPT Pref {}: {}", k, v));
        }
        
        if parts.len() <= 2 {
            return "".into(); // No significant memory yet
        }
        
        parts.join("\n")
    }

    pub fn process_rejection(&mut self, prompt: &str, final_accepted_prompt: &str) {
        info!("🧠 Processing rejection learning loop.");
        // Simple extraction pattern mapping logic
        self.skill.reusable_patterns.insert(prompt.to_string(), final_accepted_prompt.to_string());
    }
}
impl KairoMemory {
    /// After-action review: called after each completed ghost session.
    /// Extracts patterns and updates user model based on accepted/rejected output.
    pub fn after_action_review(&mut self, app: &str, prompt: &str, response: &str, accepted: bool) {
        info!("📋 After-action review: app={} accepted={}", app, accepted);

        let interaction = Interaction {
            app: app.to_string(),
            prompt: prompt.to_string(),
            response: response.to_string(),
            accepted,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0),
        };

        if accepted {
            // Update user model per app
            self.update_user_model(app, response);
            self.learn_from_interaction(interaction);
        } else {
            // Record rejection pattern
            self.skill.reusable_patterns.insert(
                format!("REJECTED:{}:{}", app, &prompt[..prompt.len().min(50)]),
                response[..response.len().min(100)].to_string(),
            );
            self.interactions.push(interaction);
        }
    }

    /// Update Honcho-style user model: learns per-app tone/formatting preferences.
    fn update_user_model(&mut self, app: &str, response: &str) {
        let app_lower = app.to_lowercase();

        if app_lower.contains("word") || app_lower.contains("winword") {
            // Detect tone preference
            if response.contains("shall") || response.contains("hereby") || response.contains("pursuant") {
                self.user_model.word_preferences.insert("tone".to_string(), "formal".to_string());
            } else if response.contains("let's") || response.contains("we'll") {
                self.user_model.word_preferences.insert("tone".to_string(), "conversational".to_string());
            }
            // Detect formatting preference  
            if response.matches("- ").count() > 3 {
                self.user_model.word_preferences.insert("formatting".to_string(), "bullet-heavy".to_string());
            } else if response.matches('\n').count() < 3 {
                self.user_model.word_preferences.insert("formatting".to_string(), "paragraph".to_string());
            }
            // Detect length preference
            let word_count = response.split_whitespace().count();
            self.user_model.word_preferences.insert("avg_length".to_string(), word_count.to_string());

        } else if app_lower.contains("powerpnt") || app_lower.contains("powerpoint") {
            // PPT preferences
            let lines: Vec<&str> = response.lines().collect();
            if lines.len() <= 5 {
                self.user_model.ppt_preferences.insert("style".to_string(), "concise".to_string());
            }
            if response.to_lowercase().contains("•") || response.contains("- ") {
                self.user_model.ppt_preferences.insert("bullet_style".to_string(), "action-verbs".to_string());
            }
        }
    }

    /// Build a memory-aware context hint for the given app and task.
    /// Used by SwarmOrchestrator to personalize system prompts.
    pub fn build_context_hint(&self, app: &str, task: &str) -> Option<String> {
        let app_lower = app.to_lowercase();
        let mut hints = Vec::new();

        // Strong preferences (weight > 1.0)
        for pref in self.preferences.iter().filter(|p| p.weight > 1.0) {
            hints.push(format!("User {} {}", pref.key, pref.value));
        }

        // App-specific model
        if app_lower.contains("word") || app_lower.contains("winword") {
            if let Some(tone) = self.user_model.word_preferences.get("tone") {
                hints.push(format!("User prefers {} tone in Word documents", tone));
            }
            if let Some(fmt) = self.user_model.word_preferences.get("formatting") {
                hints.push(format!("User prefers {} formatting", fmt));
            }
        } else if app_lower.contains("powerpnt") {
            if let Some(style) = self.user_model.ppt_preferences.get("style") {
                hints.push(format!("User prefers {} slides in PowerPoint", style));
            }
        }

        // Task-specific patterns
        let task_key = format!("REJECTED:{}:{}", app, &task[..task.len().min(50)]);
        if self.skill.reusable_patterns.contains_key(&task_key) {
            hints.push("NOTE: User previously rejected a similar response. Vary the approach.".to_string());
        }

        if hints.is_empty() {
            None
        } else {
            Some(format!("## LEARNED USER PREFERENCES\n{}", hints.join("\n")))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_graphify() {
        let mut memory = KairoMemory::default();
        let interaction = Interaction {
            app: "Word".to_string(),
            prompt: "How do I use Sentinel in Rust?".to_string(),
            response: "You can use the Sentinel struct in phantom-core.".to_string(),
            timestamp: 0u64,
            accepted: true,
        };
        memory.learn_from_interaction(interaction);
        
        assert!(memory.graph.nodes.contains(&"Sentinel".to_string()));
        assert!(memory.graph.nodes.contains(&"Rust".to_string()));
        assert!(!memory.graph.edges.is_empty());
    }

    #[test]
    fn test_after_action_review_acceptance() {
        let mut memory = KairoMemory::default();
        memory.after_action_review(
            "WINWORD.EXE",
            "Write formal closing paragraph",
            "In conclusion, we remain committed to excellence and shall endeavour to deliver the highest standards.",
            true,
        );
        // Should have updated word tone preference
        assert_eq!(memory.user_model.word_preferences.get("tone").map(|s| s.as_str()), Some("formal"));
    }

    #[test]
    fn test_after_action_review_rejection() {
        let mut memory = KairoMemory::default();
        memory.after_action_review(
            "WINWORD.EXE",
            "Write formal closing",
            "Let's wrap this up!",
            false,
        );
        // Rejection should be stored in skill patterns
        let has_rejection = memory.skill.reusable_patterns.keys()
            .any(|k| k.starts_with("REJECTED:WINWORD"));
        assert!(has_rejection);
    }
}
