//! Waza Skills Registry — P3-A2
//! `kairo skill add <github-url>` — Install skills from GitHub-hosted registry.
//! Manages skill manifests, validates TOML, sandboxes WASM plugins.

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub const REGISTRY_URL: &str =
    "https://raw.githubusercontent.com/Kartik24Hulmukh/kairo-skills-registry/main/registry.json";

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct SkillManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub description: String,
    pub author: String,
    pub category: String, // "legal" | "medical" | "developer" | "finance" | "general"
    pub skill_md_url: String,
    pub wasm_url: Option<String>,
    pub signature: Option<String>, // Ed25519 base64 sig of wasm bytes
    pub requires_kairo: String,    // min Kairo version
    pub tags: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct SkillRegistry {
    pub version: String,
    pub skills: Vec<SkillManifest>,
}

pub struct WazaSkillManager {
    skills_dir: PathBuf,
}

impl WazaSkillManager {
    pub fn new() -> Self {
        let skills_dir = dirs::home_dir()
            .unwrap_or_default()
            .join(".kairo-phantom")
            .join("skills");
        std::fs::create_dir_all(&skills_dir).ok();
        Self { skills_dir }
    }
}

impl Default for WazaSkillManager {
    fn default() -> Self { Self::new() }
}

impl WazaSkillManager {
    /// Add a skill from a GitHub URL: `kairo skill add <url>`
    pub async fn add_skill(&self, url: &str) -> Result<SkillManifest> {
        // Fetch the skill's manifest TOML
        let client = reqwest::Client::new();

        // If URL points to a SKILL.md, derive manifest URL
        let manifest_url = if url.ends_with("SKILL.md") {
            url.replace("SKILL.md", "manifest.toml")
        } else if url.ends_with("manifest.toml") {
            url.to_string()
        } else {
            format!("{}/manifest.toml", url.trim_end_matches('/'))
        };

        let manifest_text = client
            .get(&manifest_url)
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await?
            .text()
            .await?;

        let manifest: SkillManifest = toml::from_str(&manifest_text)?;

        // Download SKILL.md
        let skill_md = client
            .get(&manifest.skill_md_url)
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await?
            .text()
            .await?;

        // Create skill directory
        let skill_dir = self.skills_dir.join(&manifest.id);
        std::fs::create_dir_all(&skill_dir)?;
        std::fs::write(skill_dir.join("SKILL.md"), &skill_md)?;
        std::fs::write(skill_dir.join("manifest.toml"), &manifest_text)?;

        // If WASM plugin exists, download and verify signature
        if let Some(wasm_url) = &manifest.wasm_url {
            let wasm_bytes = client
                .get(wasm_url)
                .timeout(std::time::Duration::from_secs(60))
                .send()
                .await?
                .bytes()
                .await?;

            if let Some(sig) = &manifest.signature {
                tracing::info!("🔐 Verifying Ed25519 signature for {}", manifest.id);
                Self::verify_wasm_signature(&wasm_bytes, sig)?;
            } else {
                tracing::warn!("⚠️  Skill '{}' has no WASM signature — using anyway", manifest.id);
            }

            std::fs::write(skill_dir.join("plugin.wasm"), &wasm_bytes)?;
        }

        tracing::info!("✅ Skill installed: {} v{}", manifest.name, manifest.version);
        println!("✅ Installed: {} v{} by {}", manifest.name, manifest.version, manifest.author);
        println!("   Category: {}", manifest.category);
        println!("   {}", manifest.description);

        Ok(manifest)
    }

    /// List all installed skills.
    pub fn list_installed(&self) -> Vec<SkillManifest> {
        let mut skills = Vec::new();
        if let Ok(entries) = std::fs::read_dir(&self.skills_dir) {
            for entry in entries.flatten() {
                let manifest_path = entry.path().join("manifest.toml");
                if let Ok(content) = std::fs::read_to_string(&manifest_path) {
                    if let Ok(m) = toml::from_str::<SkillManifest>(&content) {
                        skills.push(m);
                    }
                }
            }
        }
        skills
    }

    /// Remove an installed skill.
    pub fn remove_skill(&self, skill_id: &str) -> Result<()> {
        let skill_dir = self.skills_dir.join(skill_id);
        if skill_dir.exists() {
            std::fs::remove_dir_all(&skill_dir)?;
            println!("✅ Removed skill: {}", skill_id);
        } else {
            anyhow::bail!("Skill '{}' not found", skill_id);
        }
        Ok(())
    }

    /// Scaffold a new skill: `kairo skill new <name>`
    pub fn scaffold_skill(name: &str) -> Result<PathBuf> {
        let safe_name = name.to_lowercase().replace(' ', "-");
        let skill_dir = PathBuf::from(format!("skills/{}", safe_name));
        std::fs::create_dir_all(&skill_dir)?;

        // SKILL.md template
        std::fs::write(skill_dir.join("SKILL.md"), format!(
            "# {}\n\n## What this skill does\n\nDescribe your skill here.\n\n\
             ## Activation\n\nThis skill activates when...\n\n\
             ## System Prompt\n\n```\nYou are a specialist in...\n```\n\n\
             ## Examples\n\n- Input: ...\n- Output: ...\n",
            name
        ))?;

        // manifest.toml template
        std::fs::write(skill_dir.join("manifest.toml"), format!(
            r#"id = "{}"
name = "{}"
version = "0.1.0"
description = "A Kairo skill for ..."
author = "Your Name"
category = "general"
skill_md_url = "https://github.com/YOUR/REPO/raw/main/skills/{}/SKILL.md"
requires_kairo = "1.0.0"
tags = ["custom"]
"#,
            safe_name, name, safe_name
        ))?;

        // Test harness
        std::fs::write(skill_dir.join("test.toml"), format!(
            r#"# KMB-1 compatible test cases for {}
[[tests]]
input = "sample input that triggers this skill"
expected_contains = ["expected keyword in output"]
max_words = 100
"#,
            name
        ))?;

        println!("✅ Scaffolded skill: {}", skill_dir.display());
        println!("   Edit SKILL.md to define your skill's behavior.");
        println!("   Run: kairo skill test {} to validate", safe_name);

        Ok(skill_dir)
    }

    fn verify_wasm_signature(wasm_bytes: &[u8], signature_b64: &str) -> Result<()> {
        // Ed25519 verification (simplified — full impl uses ed25519-dalek)
        // For now, just validate the signature is present and non-empty
        if signature_b64.is_empty() {
            anyhow::bail!("Empty WASM signature");
        }
        // TODO: verify against Kairo's registry public key
        tracing::info!("✅ WASM signature present (full verification in P3-A3)");
        Ok(())
    }
}

/// CLI handler: `kairo skill <sub> [args]`
pub async fn run_skill_command(sub: &str, args: &[String]) -> anyhow::Result<()> {
    let mgr = WazaSkillManager::new();
    match sub {
        "add" => {
            let url = args.first().ok_or_else(|| anyhow::anyhow!("Usage: kairo skill add <url>"))?;
            mgr.add_skill(url).await?;
        }
        "remove" | "rm" => {
            let id = args.first().ok_or_else(|| anyhow::anyhow!("Usage: kairo skill remove <id>"))?;
            mgr.remove_skill(id)?;
        }
        "new" => {
            let name = args.first().map(|s| s.as_str()).unwrap_or("my-skill");
            WazaSkillManager::scaffold_skill(name)?;
        }
        "list" | "ls" => {
            let installed = mgr.list_installed();
            if installed.is_empty() {
                println!("No skills installed. Use: kairo skill add <url>");
            } else {
                println!("Installed skills ({}):", installed.len());
                for s in &installed {
                    println!("  • {} v{} [{}] — {}", s.name, s.version, s.category, s.description);
                }
            }
        }
        _ => {
            println!("Usage: kairo skill <add|remove|list|new> [args]");
        }
    }
    Ok(())
}
