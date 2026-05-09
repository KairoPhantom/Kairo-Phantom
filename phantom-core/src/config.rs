/// Config — loads ~/.kairo-phantom/config.toml
/// Falls back to sensible defaults (Ollama local).

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PhantomConfig {
    /// Hotkey combination to trigger materialization
    #[serde(default = "default_hotkey")]
    pub hotkey: String,

    /// Milliseconds between each typed character (15 = realistic human speed)
    #[serde(default = "default_typing_delay")]
    pub typing_delay_ms: u64,

    /// Legacy single model config (used as fallback if swarm is not configured)
    #[serde(default)]
    pub model: ModelConfig,

    /// Optional cloud fallback when Ollama is unavailable
    #[serde(default)]
    pub fallback: Option<ModelConfig>,

    /// The Multi-Agent Swarm Configuration
    #[serde(default)]
    pub swarm: SwarmConfig,

    /// List of paths to plugin TOML files
    #[serde(default)]
    pub plugins: Vec<String>,
}


#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct SwarmConfig {
    /// Enables the multi-agent LLM routing pipeline.
    #[serde(default)]
    pub enabled: bool,
    
    /// The Brain: analyzes the context and delegates.
    pub brain: Option<ModelConfig>,
    
    /// Content & Prose Specialist
    pub content_agent: Option<ModelConfig>,
    
    /// Reasoning & Code Specialist
    pub reasoning_agent: Option<ModelConfig>,
    
    /// Design & Layout Specialist
    pub design_agent: Option<ModelConfig>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModelConfig {
    /// AI provider: "ollama" | "openai" | "anthropic" | "gemini"
    #[serde(default = "default_provider")]
    pub provider: String,

    /// Model name (e.g. "llama3", "gpt-4o-mini", "claude-3-haiku-20240307")
    pub model_name: Option<String>,

    /// API key (not needed for Ollama)
    pub api_key: Option<String>,

    /// Base URL override (for Ollama or self-hosted)
    pub base_url: Option<String>,
}

impl Default for ModelConfig {
    fn default() -> Self {
        ModelConfig {
            provider: default_provider(),
            model_name: Some("qwen2.5-coder:14b".into()),
            api_key: None,
            base_url: Some("http://localhost:11434".into()),
        }
    }
}

fn default_hotkey() -> String { "ctrl+space".into() }
fn default_typing_delay() -> u64 { 15 }
fn default_provider() -> String { "ollama".into() }

impl Default for PhantomConfig {
    fn default() -> Self {
        PhantomConfig {
            hotkey: default_hotkey(),
            typing_delay_ms: default_typing_delay(),
            model: ModelConfig::default(),
            fallback: None,
            swarm: SwarmConfig::default(),
            plugins: Vec::new(),
        }
    }
}


impl PhantomConfig {
    /// Load config from ~/.kairo-phantom/config.toml or return defaults
    pub fn load_or_default() -> Result<Self> {
        let config_path = Self::config_path();

        if config_path.exists() {
            let content = std::fs::read_to_string(&config_path)?;
            let config: PhantomConfig = toml::from_str(&content)?;
            Ok(config)
        } else {
            // First run — create default config file
            let config = PhantomConfig::default();
            if let Some(parent) = config_path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            let toml_str = toml::to_string_pretty(&config)?;
            std::fs::write(&config_path, &toml_str)?;
            tracing::info!("Created default config at: {}", config_path.display());
            Ok(config)
        }
    }

    pub fn config_path() -> PathBuf {
        dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".kairo-phantom")
            .join("config.toml")
    }
}
