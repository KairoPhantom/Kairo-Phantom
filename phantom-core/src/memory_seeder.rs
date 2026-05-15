//! Memory Seeder — P1-A2
//! `kairo seed <folder>` — Scans existing documents to pre-populate MemMachine.
//! Solves the cold-start problem by extracting style patterns from a folder of docs.

use anyhow::Result;
use std::path::{Path, PathBuf};
use crate::document_context::ExtractorRegistry;
use crate::memory::mem_machine::MemMachine;

pub struct MemorySeeder {
    registry: ExtractorRegistry,
}

impl MemorySeeder {
    pub fn new() -> Self {
        Self { registry: ExtractorRegistry::with_defaults() }
    }

    /// Seed MemMachine from all documents in a folder. Returns count of seeded docs.
    pub async fn seed_from_folder(&self, folder: &Path, mem: &MemMachine) -> Result<usize> {
        let supported_exts = ["docx", "doc", "pptx", "ppt", "xlsx", "xls", "txt", "md"];
        let mut seeded = 0;

        let entries = walkdir_simple(folder);
        for path in entries {
            let ext = path.extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_lowercase();

            if !supported_exts.contains(&ext.as_str()) { continue; }

            match self.registry.extract(&path, "", None) {
                Some(doc_ctx) => {
                    let style = self.extract_style_signals(&doc_ctx.full_text);
                    let app_ctx = format!("{:?}", doc_ctx.doc_kind);

                    // Store inferred preferences as MemMachine episodes
                    for (pref_key, pref_val) in &style {
                        let content = format!("Style preference: {} = {}", pref_key, pref_val);
                        let _ = mem.remember(
                            &content,
                            Some(&doc_ctx.full_text[..doc_ctx.full_text.len().min(500)]),
                            &app_ctx,
                            Some(pref_key.as_str()),
                            true, // is_ground_truth — seeded from real docs
                            vec!["seeded", "style-preference"],
                        ).await;
                    }

                    seeded += 1;
                    tracing::info!("🌱 Seeded: {} ({} style signals)", path.display(), style.len());
                }
                None => {
                    tracing::debug!("⏭️  Skipped (no extractor): {}", path.display());
                }
            }
        }

        tracing::info!("✅ Memory seeding complete: {} documents processed", seeded);
        Ok(seeded)
    }

    /// Extract style signals from document text.
    /// Returns key-value pairs like ("avg_sentence_length", "12 words")
    fn extract_style_signals(&self, text: &str) -> Vec<(String, String)> {
        let mut signals = Vec::new();
        let words: Vec<&str> = text.split_whitespace().collect();
        let word_count = words.len();
        if word_count == 0 { return signals; }

        // Avg sentence length
        let sentences = text.chars().filter(|&c| c == '.' || c == '!' || c == '?').count().max(1);
        let avg_sentence_len = word_count / sentences;
        let length_pref = if avg_sentence_len < 12 { "concise" }
            else if avg_sentence_len < 20 { "moderate" }
            else { "detailed" };
        signals.push(("sentence_style".to_string(), length_pref.to_string()));

        // Bullet point usage
        let bullet_lines = text.lines().filter(|l| {
            let t = l.trim();
            t.starts_with("• ") || t.starts_with("- ") || t.starts_with("* ") || t.starts_with("· ")
        }).count();
        let total_lines = text.lines().count().max(1);
        let bullet_ratio = bullet_lines as f32 / total_lines as f32;
        let format_pref = if bullet_ratio > 0.3 { "bullet_points" } else { "prose" };
        signals.push(("format_preference".to_string(), format_pref.to_string()));

        // Tone: formal vs casual (simple heuristic — presence of contractions)
        let contractions = ["don't", "can't", "won't", "it's", "i'm", "we're", "they're", "isn't", "aren't"];
        let has_contractions = contractions.iter().any(|c| text.to_lowercase().contains(c));
        signals.push(("tone".to_string(), if has_contractions { "casual" } else { "formal" }.to_string()));

        // Avg word length → vocabulary level
        let avg_word_len = words.iter().map(|w| w.len()).sum::<usize>() / word_count;
        let vocab_level = if avg_word_len < 5 { "simple" } else if avg_word_len < 7 { "moderate" } else { "advanced" };
        signals.push(("vocabulary".to_string(), vocab_level.to_string()));

        signals
    }
}

/// Simple recursive directory walker returning file paths.
fn walkdir_simple(folder: &Path) -> Vec<PathBuf> {
    let mut paths = Vec::new();
    if let Ok(entries) = std::fs::read_dir(folder) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                paths.extend(walkdir_simple(&path));
            } else {
                paths.push(path);
            }
        }
    }
    paths
}

/// CLI handler: `kairo seed <folder>`
pub async fn run_seed_command(folder_str: &str) -> Result<()> {
    let folder = PathBuf::from(folder_str);
    if !folder.exists() {
        anyhow::bail!("Folder not found: {}", folder_str);
    }

    println!("🌱 Kairo Memory Seeding");
    println!("   Scanning: {}", folder.display());
    println!("   This extracts style patterns to pre-populate MemMachine.\n");

    let mem_vault = dirs::home_dir()
        .unwrap_or_default()
        .join(".kairo-phantom");

    let mem = MemMachine::new(mem_vault)?;

    let seeder = MemorySeeder::new();
    let count = seeder.seed_from_folder(&folder, &mem).await?;

    println!("✅ Done! Seeded {} documents into MemMachine.", count);
    println!("   Kairo now knows your writing style from day one.");
    Ok(())
}
