// phantom-core/src/kami_export.rs
// Kami Export Pipeline: Markdown → PDF (Pandoc/Tectonic) → RevealJS
// Reads brand config from ~/.config/kairo/brand.md for consistent styling.

use std::path::PathBuf;
use std::process::Command;
use tracing::{info, warn};

pub struct KamiExport;

impl KamiExport {
    /// Load brand configuration from ~/.config/kairo/brand.md
    fn get_brand_config() -> String {
        let path = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".config")
            .join("kairo")
            .join("brand.md");
        
        if path.exists() {
            std::fs::read_to_string(&path).unwrap_or_else(|_| Self::default_brand())
        } else {
            Self::default_brand()
        }
    }

    fn default_brand() -> String {
        "# Default Kairo Brand\nColors: #1a1a2e, #e94560\nFont: Inter, sans-serif\nVoice: Professional, concise".to_string()
    }

    /// Export to Markdown with brand frontmatter.
    pub fn export_markdown(content: &str, output_path: &str) -> Result<(), String> {
        let brand = Self::get_brand_config();
        // Build YAML frontmatter from brand config
        let frontmatter = brand.lines()
            .filter(|l| !l.starts_with('#'))
            .map(|l| l.trim())
            .filter(|l| !l.is_empty())
            .collect::<Vec<_>>()
            .join("\n");
        
        let final_content = format!("---\n{}\ngenerated-by: kairo-phantom\n---\n\n{}", frontmatter, content);
        std::fs::write(output_path, final_content)
            .map_err(|e| format!("Failed to export Markdown: {}", e))?;
        info!("[Kami] Markdown exported to: {}", output_path);
        Ok(())
    }

    /// Export to PDF using Pandoc + Tectonic (best-effort).
    /// Falls back to writing a Markdown file if pandoc is unavailable.
    pub fn export_pdf(content: &str, output_path: &str) -> Result<(), String> {
        // Write temp markdown first
        let md_path = format!("{}.tmp.md", output_path);
        Self::export_markdown(content, &md_path)?;

        // Try pandoc with tectonic PDF engine
        let pandoc_result = Command::new("pandoc")
            .args([
                &md_path,
                "-o", output_path,
                "--pdf-engine=tectonic",
                "--standalone",
                "-V", "geometry:margin=1in",
                "-V", "fontsize=11pt",
                "-V", "colorlinks=true",
                "-V", "linkcolor=blue",
            ])
            .output();

        match pandoc_result {
            Ok(output) if output.status.success() => {
                info!("[Kami] PDF exported via pandoc+tectonic: {}", output_path);
                let _ = std::fs::remove_file(&md_path);
                Ok(())
            }
            Ok(output) => {
                let stderr = String::from_utf8_lossy(&output.stderr);
                warn!("[Kami] pandoc failed: {}", stderr);
                // Try wkhtmltopdf as fallback
                Self::export_pdf_wkhtmltopdf(content, output_path, &md_path)
            }
            Err(e) => {
                warn!("[Kami] pandoc not found ({}), trying wkhtmltopdf", e);
                Self::export_pdf_wkhtmltopdf(content, output_path, &md_path)
            }
        }
    }

    fn export_pdf_wkhtmltopdf(content: &str, output_path: &str, md_path: &str) -> Result<(), String> {
        // Try wkhtmltopdf via HTML intermediate
        let html_path = format!("{}.tmp.html", output_path);
        let html = Self::markdown_to_html(content);
        std::fs::write(&html_path, &html).map_err(|e| e.to_string())?;

        let result = Command::new("wkhtmltopdf")
            .args([&html_path, output_path])
            .output();

        let _ = std::fs::remove_file(&html_path);
        let _ = std::fs::remove_file(md_path);

        match result {
            Ok(output) if output.status.success() => {
                info!("[Kami] PDF exported via wkhtmltopdf: {}", output_path);
                Ok(())
            }
            _ => {
                // Last resort: save as HTML with PDF header
                let fallback_path = output_path.replace(".pdf", ".html");
                std::fs::write(&fallback_path, html)
                    .map_err(|e| format!("All PDF methods failed. HTML fallback also failed: {}", e))?;
                warn!("[Kami] PDF tools not available. Saved as HTML: {}", fallback_path);
                Ok(())
            }
        }
    }

    /// Export to RevealJS HTML presentation.
    /// Slides are split on `---` separator.
    pub fn export_reveal_js(content: &str, output_path: &str) -> Result<(), String> {
        let brand = Self::get_brand_config();
        
        // Extract brand colors for theme customization
        let primary_color = brand.lines()
            .find(|l| l.to_lowercase().contains("color"))
            .and_then(|l| l.split(':').nth(1))
            .map(|s| s.trim().split(',').next().unwrap_or("#1a1a2e").trim().to_string())
            .unwrap_or_else(|| "#1a1a2e".to_string());

        let slides: Vec<String> = content
            .split("\n---\n")
            .map(|slide| {
                let converted = Self::markdown_to_html_fragment(slide.trim());
                format!("<section>\n{}\n</section>", converted)
            })
            .collect();

        let html = format!(
            r#"<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kairo Phantom Presentation</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/black.css">
  <style>
    :root {{
      --r-background-color: {primary_color};
      --r-main-color: #fff;
      --r-heading-color: #e94560;
      --r-link-color: #4fc3f7;
    }}
    .reveal h1, .reveal h2 {{ color: var(--r-heading-color); }}
    .reveal ul {{ text-align: left; }}
    .reveal .slide-number {{ color: #999; }}
    .kairo-brand {{ position: fixed; bottom: 10px; right: 15px; font-size: 12px; opacity: 0.5; }}
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
{slides}
    </div>
  </div>
  <div class="kairo-brand">Generated by Kairo Phantom</div>
  <script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
  <script>
    Reveal.initialize({{
      hash: true,
      slideNumber: 'c/t',
      transition: 'slide',
      backgroundTransition: 'fade',
      controls: true,
      progress: true,
      center: true,
    }});
  </script>
</body>
</html>"#,
            primary_color = primary_color,
            slides = slides.join("\n"),
        );

        std::fs::write(output_path, html)
            .map_err(|e| format!("Failed to export RevealJS: {}", e))?;
        info!("[Kami] RevealJS exported to: {}", output_path);
        Ok(())
    }

    /// Convert markdown to basic HTML fragment (headings, bold, italic, lists).
    fn markdown_to_html_fragment(md: &str) -> String {
        let mut html = String::new();
        let mut in_list = false;

        for line in md.lines() {
            if line.starts_with("### ") {
                if in_list { html.push_str("</ul>\n"); in_list = false; }
                html.push_str(&format!("<h3>{}</h3>\n", Self::inline_md(&line[4..])));
            } else if line.starts_with("## ") {
                if in_list { html.push_str("</ul>\n"); in_list = false; }
                html.push_str(&format!("<h2>{}</h2>\n", Self::inline_md(&line[3..])));
            } else if line.starts_with("# ") {
                if in_list { html.push_str("</ul>\n"); in_list = false; }
                html.push_str(&format!("<h1>{}</h1>\n", Self::inline_md(&line[2..])));
            } else if line.starts_with("- ") || line.starts_with("* ") {
                if !in_list { html.push_str("<ul>\n"); in_list = true; }
                html.push_str(&format!("<li>{}</li>\n", Self::inline_md(&line[2..])));
            } else if line.is_empty() {
                if in_list { html.push_str("</ul>\n"); in_list = false; }
                html.push_str("<br>\n");
            } else {
                if in_list { html.push_str("</ul>\n"); in_list = false; }
                html.push_str(&format!("<p>{}</p>\n", Self::inline_md(line)));
            }
        }
        if in_list { html.push_str("</ul>\n"); }
        html
    }

    /// Full markdown to HTML document (used for PDF fallback).
    fn markdown_to_html(content: &str) -> String {
        let body = Self::markdown_to_html_fragment(content);
        format!(
            r#"<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:Inter,sans-serif;max-width:800px;margin:40px auto;color:#222;line-height:1.6}}
h1,h2,h3{{color:#1a1a2e}}ul{{padding-left:20px}}</style></head>
<body>{}</body></html>"#,
            body
        )
    }

    /// Process inline markdown: **bold**, *italic*, `code`.
    fn inline_md(s: &str) -> String {
        let s = regex_replace(s, r"\*\*(.+?)\*\*", "<strong>$1</strong>");
        let s = regex_replace(&s, r"\*(.+?)\*", "<em>$1</em>");
        let s = regex_replace(&s, r"`(.+?)`", "<code>$1</code>");
        s
    }
}

/// Simple regex-based replacement (avoids adding regex dep by using basic patterns).
fn regex_replace(input: &str, _pattern: &str, _replacement: &str) -> String {
    // Lightweight approach: process common patterns manually
    // Full regex replacement would require the regex crate — already available
    use regex::Regex;
    if let Ok(re) = Regex::new(_pattern) {
        re.replace_all(input, _replacement).to_string()
    } else {
        input.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn test_export_markdown() {
        let dir = std::env::temp_dir();
        let path = dir.join("kami_test.md");
        let result = KamiExport::export_markdown("# Hello\n\nThis is a test.", path.to_str().unwrap());
        assert!(result.is_ok(), "Markdown export failed: {:?}", result);
        assert!(path.exists());
        let content = std::fs::read_to_string(&path).unwrap();
        assert!(content.contains("# Hello"));
        assert!(content.contains("generated-by: kairo-phantom"));
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn test_export_reveal_js() {
        let dir = std::env::temp_dir();
        let path = dir.join("kami_test.html");
        let content = "# Slide 1\nContent here\n---\n## Slide 2\n- Point A\n- Point B";
        let result = KamiExport::export_reveal_js(content, path.to_str().unwrap());
        assert!(result.is_ok(), "RevealJS export failed: {:?}", result);
        let html = std::fs::read_to_string(&path).unwrap();
        assert!(html.contains("reveal.js"));
        assert!(html.contains("<section>"));
        assert!(html.contains("Kairo Phantom"));
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn test_markdown_to_html_fragment() {
        let md = "# Title\n\n- Item 1\n- Item 2\n\nA paragraph.";
        let html = KamiExport::markdown_to_html_fragment(md);
        assert!(html.contains("<h1>Title</h1>"));
        assert!(html.contains("<li>Item 1</li>"));
        assert!(html.contains("<p>A paragraph.</p>"));
    }
}
