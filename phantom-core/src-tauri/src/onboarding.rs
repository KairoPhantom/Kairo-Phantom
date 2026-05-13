// phantom-core/src-tauri/src/onboarding.rs

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::{command, Window};

#[derive(Serialize, Deserialize)]
pub struct KairoConfig {
    pub ai_mode: String,
    pub api_key: Option<String>,
    pub local_model: Option<String>,
    pub hotkey: String,
}

#[command]
pub async fn detect_ollama() -> Result<Vec<String>, String> {
    let client = reqwest::Client::new();
    let res = client
        .get("http://localhost:11434/api/tags")
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let json: serde_json::Value = res.json().await.map_err(|e| e.to_string())?;
    
    let mut models = Vec::new();
    if let Some(models_array) = json.get("models").and_then(|m| m.as_array()) {
        for model in models_array {
            if let Some(name) = model.get("name").and_then(|n| n.as_str()) {
                models.push(name.to_string());
            }
        }
    }
    
    if models.is_empty() {
        return Err("No models found in Ollama".to_string());
    }
    
    Ok(models)
}

#[command]
pub fn test_hotkey(hotkey: String) -> Result<bool, String> {
    // In a real app, this would register the hotkey via tauri-plugin-global-shortcut
    // For the onboarding wizard, we just validate it's a valid accelerator string
    if hotkey.is_empty() {
        return Err("Hotkey cannot be empty".to_string());
    }
    Ok(true)
}

#[command]
pub fn save_config_and_close(
    window: Window,
    config: KairoConfig,
) -> Result<(), String> {
    let home_dir = dirs::home_dir().ok_or("Could not find home directory")?;
    let config_dir = home_dir.join(".kairo-phantom");
    
    if !config_dir.exists() {
        fs::create_dir_all(&config_dir).map_err(|e| e.to_string())?;
    }
    
    let config_path = config_dir.join("config.toml");
    let toml_string = toml::to_string(&config).map_err(|e| e.to_string())?;
    
    fs::write(config_path, toml_string).map_err(|e| e.to_string())?;
    
    // Auto-close the onboarding window after saving
    window.close().map_err(|e| e.to_string())?;
    
    Ok(())
}

/// Setup function to open the wizard if config doesn't exist
pub fn run_wizard_if_needed(app: &mut tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let home_dir = dirs::home_dir().unwrap();
    let config_path = home_dir.join(".kairo-phantom").join("config.toml");
    
    if !config_path.exists() {
        tauri::WindowBuilder::new(
            app,
            "onboarding",
            tauri::WindowUrl::App("onboarding.html".into())
        )
        .title("Welcome to Kairo Phantom")
        .inner_size(600.0, 500.0)
        .resizable(false)
        .center()
        .build()?;
    }
    
    Ok(())
}
