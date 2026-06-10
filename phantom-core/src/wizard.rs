/// First-run setup wizard — guides new users through configuration interactively.
/// No manual file editing required. Just run and answer questions.

use anyhow::Result;
use std::io::{self, Write};
use crate::config::{PhantomConfig, ModelConfig};

pub fn run_setup_wizard() -> Result<PhantomConfig> {
    println!();
    println!("╔═══════════════════════════════════════════════════╗");
    println!("║          👻 Kairo Phantom — First-Run Setup        ║");
    println!("╚═══════════════════════════════════════════════════╝");
    println!();
    println!("  Welcome! Let's get you set up in 60 seconds.");
    println!("  You can always edit ~/.kairo-phantom/config.toml later.");
    println!();

    // ── Step 1: Choose AI Provider ──────────────────────────────────────────
    println!("  Step 1/3 — Choose your AI provider:");
    println!();
    println!("    [1] NVIDIA NIM   — Free tier, fast, no credit card (recommended)");
    println!("    [2] OpenAI       — GPT-4o, requires OpenAI API key");
    println!("    [3] Anthropic    — Claude 3.5 Sonnet, requires Anthropic API key");
    println!("    [4] Google       — Gemini 1.5 Pro, requires Google AI API key");
    println!("    [5] Ollama       — 100% local, free, requires Ollama installed");
    println!();
    print!("  Your choice [1-5, default: 1]: ");
    io::stdout().flush()?;

    let provider_choice = read_line()?.trim().to_string();
    let (provider, model_name, needs_key, key_hint) = match provider_choice.as_str() {
        "2" => ("openai", "gpt-4o", true, "https://platform.openai.com/api-keys"),
        "3" => ("anthropic", "claude-3-5-sonnet-20241022", true, "https://console.anthropic.com/"),
        "4" => ("gemini", "gemini-1.5-pro", true, "https://aistudio.google.com/app/apikey"),
        "5" => ("ollama", "llama3", false, ""),
        _ => ("nim", "meta/llama-3.1-70b-instruct", true, "https://build.nvidia.com/"),
    };

    println!();
    println!("  ✅ Provider: {}", provider.to_uppercase());
    println!("     Model:    {}", model_name);
    println!();

    // ── Step 2: API Key ──────────────────────────────────────────────────────
    let api_key = if needs_key {
        println!("  Step 2/3 — Enter your API key:");
        if !key_hint.is_empty() {
            println!("  (Get your key at: {})", key_hint);
        }
        println!();
        print!("  API Key: ");
        io::stdout().flush()?;
        let key = read_line()?.trim().to_string();
        if key.is_empty() {
            println!();
            println!("  ⚠️  No key entered. You can add it later in config.toml");
        } else {
            println!("  ✅ API key saved.");
        }
        Some(key)
    } else {
        println!("  Step 2/3 — No API key needed for Ollama.");
        println!("  ✅ Make sure Ollama is running: https://ollama.com");
        None
    };

    println!();

    // ── Step 3: Hotkey ───────────────────────────────────────────────────────
    println!("  Step 3/3 — Choose your activation hotkey:");
    println!();
    println!("    [1] Alt+Ctrl+M (recommended — no conflicts)");
    println!("    [2] Ctrl+K     (common in VS Code, may conflict)");
    println!("    [3] Ctrl+Space (may conflict with IME/accessibility)");
    println!("    [4] Custom     (type your own)");
    println!();
    print!("  Your choice [1-4, default: 1]: ");
    io::stdout().flush()?;

    let hotkey_choice = read_line()?.trim().to_string();
    let hotkey = match hotkey_choice.as_str() {
        "2" => "ctrl+k".to_string(),
        "3" => "ctrl+space".to_string(),
        "4" => {
            print!("  Enter hotkey (e.g. alt+g): ");
            io::stdout().flush()?;
            read_line()?.trim().to_string()
        }
        _ => "alt+ctrl+m".to_string(),
    };

    println!();
    println!("  ✅ Hotkey: {}", hotkey.to_uppercase());
    println!();

    // ── Done ─────────────────────────────────────────────────────────────────
    let config = PhantomConfig {
        hotkey: hotkey.clone(),
        typing_delay_ms: 0, // Fast by default
        model: ModelConfig {
            provider: provider.into(),
            model_name: Some(model_name.into()),
            api_key,
            base_url: None,
        },
    };

    // Save it
    let config_path = PhantomConfig::config_path();
    if let Some(parent) = config_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let toml_str = toml::to_string_pretty(&config)?;
    std::fs::write(&config_path, &toml_str)?;

    println!("╔═══════════════════════════════════════════════════╗");
    println!("║              ✅ Setup Complete!                    ║");
    println!("╚═══════════════════════════════════════════════════╝");
    println!();
    println!("  Kairo Phantom is ready. Usage:");
    println!();
    println!("  1. Open any app (Word, Notion, browser, VS Code...)");
    println!("  2. Type what you want or place your cursor in text");
    println!("  3. Press  {} ", hotkey.to_uppercase());
    println!("  4. Watch Kairo materialize professional content");
    println!();
    println!("  Config saved to: {}", config_path.display());
    println!("  Logs: kairo.log / kairo_err.log");
    println!();

    Ok(config)
}

fn read_line() -> Result<String> {
    let mut buf = String::new();
    io::stdin().read_line(&mut buf)?;
    Ok(buf)
}

/// Check if this is a fresh install (no config exists).
pub fn is_first_run() -> bool {
    !PhantomConfig::config_path().exists()
}
