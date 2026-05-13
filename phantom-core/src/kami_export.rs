use std::path::PathBuf;
use std::fs;
use chrono::Utc;
use tokio::time::sleep;
use std::time::Duration;

#[derive(Debug, PartialEq)]
pub enum KamiCommand {
    Pdf,
    RevealJs,
    Email,
    LinkedIn,
    TweetThread,
    Notion,
    SlidesGoogle,
    Summary,
    Translate(String),
    Proofread,
}

pub struct CommandParser;

impl CommandParser {
    pub fn detect(text: &str) -> Option<(KamiCommand, String)> {
        let lines: Vec<&str> = text.lines().collect();
        if let Some(first_line) = lines.first() {
            if first_line.starts_with("// kami ") {
                let cmd_str = first_line.strip_prefix("// kami ").unwrap_or("").trim();
                let parts: Vec<&str> = cmd_str.split_whitespace().collect();
                if parts.is_empty() { return None; }
                
                let command = match parts[0].to_lowercase().as_str() {
                    "pdf" => KamiCommand::Pdf,
                    "revealjs" => KamiCommand::RevealJs,
                    "email" => KamiCommand::Email,
                    "linkedin" => KamiCommand::LinkedIn,
                    "tweet-thread" => KamiCommand::TweetThread,
                    "notion" => KamiCommand::Notion,
                    "slides-google" => KamiCommand::SlidesGoogle,
                    "summary" => KamiCommand::Summary,
                    "translate" => {
                        let lang = if parts.len() > 1 { parts[1].to_string() } else { "Spanish".to_string() };
                        KamiCommand::Translate(lang)
                    },
                    "proofread" => KamiCommand::Proofread,
                    _ => return None,
                };
                
                let content = lines[1..].join("\n");
                return Some((command, content));
            }
        }
        None
    }
}

pub struct KamiExporter;

impl KamiExporter {
    pub async fn execute(command: KamiCommand, content: String) -> Result<(), String> {
        let docs_dir = dirs::document_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("Kairo Exports");
        
        fs::create_dir_all(&docs_dir).map_err(|e| e.to_string())?;

        match command {
            KamiCommand::Pdf => Self::handle_pdf(content).await,
            KamiCommand::RevealJs => Self::handle_revealjs(content).await,
            KamiCommand::Email => Self::handle_email(content).await,
            KamiCommand::LinkedIn => Self::handle_linkedin(content).await,
            KamiCommand::TweetThread => Self::handle_tweet_thread(content).await,
            KamiCommand::Notion => Self::handle_notion(content).await,
            KamiCommand::SlidesGoogle => Self::handle_slides_google(content).await,
            KamiCommand::Summary => Self::handle_summary(content).await,
            KamiCommand::Translate(lang) => Self::handle_translate(content, lang).await,
            KamiCommand::Proofread => Self::handle_proofread(content).await,
        }
    }

    fn get_desktop_pdf_path() -> PathBuf {
        let timestamp = Utc::now().format("%Y%m%d_%H%M%S");
        dirs::desktop_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(format!("kairo-export-{}.pdf", timestamp))
    }

    fn get_export_path(ext: &str) -> PathBuf {
        let timestamp = Utc::now().format("%Y%m%d_%H%M%S");
        dirs::document_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("Kairo Exports")
            .join(format!("kairo-export-{}.{}", timestamp, ext))
    }

    async fn handle_pdf(content: String) -> Result<(), String> {
        Self::show_toast("Kairo: exporting as PDF...");
        let pdf_path = Self::get_desktop_pdf_path();
        
        // Mocking PDF conversion via wkhtmltopdf
        let html_content = format!(
            "<html><head><style>body{{font-family:sans-serif; margin:40px;}}</style></head><body>{}</body></html>", 
            content.replace("\n", "<br>")
        );
        let temp_html = std::env::temp_dir().join("kairo_temp.html");
        fs::write(&temp_html, html_content).unwrap();
        
        // Command::new("wkhtmltopdf").arg(temp_html).arg(&pdf_path).output().unwrap();
        fs::write(&pdf_path, "PDF Binary Stub").map_err(|e| e.to_string())?;
        
        Ok(())
    }

    async fn handle_revealjs(content: String) -> Result<(), String> {
        Self::show_toast("Kairo: exporting as RevealJS...");
        let path = Self::get_export_path("html");
        let slides = content.replace("## ", "</section><section><h2>");
        let html = format!("<html><body><div class='reveal'><div class='slides'><section>{}</section></div></div></body></html>", slides);
        fs::write(&path, html).map_err(|e| e.to_string())?;
        Ok(())
    }

    async fn handle_email(content: String) -> Result<(), String> {
        Self::show_toast("Kairo: exporting as email...");
        let subject = content.lines().find(|l| l.starts_with("# ")).unwrap_or("# Default Subject").replace("# ", "");
        let email = format!("Subject: {}\n\n{}\n\nBest regards,\nUser", subject, content);
        Self::copy_to_clipboard(&email);
        Ok(())
    }

    async fn handle_linkedin(content: String) -> Result<(), String> {
        Self::show_toast("Kairo: exporting for LinkedIn...");
        // Reformat logic mock
        let mut clean = content.replace("#", "").replace("*", "");
        if clean.len() > 1300 { clean.truncate(1300); }
        let li_post = format!("{}\n\nThoughts? 👇", clean);
        Self::copy_to_clipboard(&li_post);
        Ok(())
    }

    async fn handle_tweet_thread(content: String) -> Result<(), String> {
        Self::show_toast("Kairo: exporting as Tweet thread...");
        let clean = content.replace("#", "").replace("*", "");
        let mut tweets = Vec::new();
        for (i, chunk) in clean.chars().collect::<Vec<char>>().chunks(270).enumerate() {
            tweets.push(format!("({}/N) {}", i+1, chunk.iter().collect::<String>()));
        }
        Self::copy_to_clipboard(&tweets.join("\n\n"));
        Ok(())
    }

    async fn handle_notion(content: String) -> Result<(), String> {
        Self::show_toast("Kairo: exporting for Notion...");
        Self::copy_to_clipboard(&content);
        Ok(())
    }

    async fn handle_slides_google(_content: String) -> Result<(), String> {
        Self::show_toast("Kairo: exporting to Google Slides...");
        // API Flow mock
        sleep(Duration::from_millis(500)).await;
        println!("Opening OAuth window for Google Slides...");
        Ok(())
    }

    async fn handle_summary(_content: String) -> Result<(), String> {
        Self::show_toast("Kairo: generating summary...");
        // Inject at top mock
        sleep(Duration::from_millis(500)).await;
        println!("Injecting summary via Enigo...");
        Ok(())
    }

    async fn handle_translate(_content: String, lang: String) -> Result<(), String> {
        Self::show_toast(&format!("Kairo: translating to {}...", lang));
        sleep(Duration::from_millis(500)).await;
        println!("Ghost-typing translation...");
        Ok(())
    }

    async fn handle_proofread(_content: String) -> Result<(), String> {
        Self::show_toast("Kairo: proofreading...");
        sleep(Duration::from_millis(500)).await;
        println!("Showing Tauri diff panel...");
        Ok(())
    }

    fn show_toast(msg: &str) {
        println!("{}", msg);
    }

    fn copy_to_clipboard(text: &str) {
        // Mock using arboard or similar
        println!("Copied to clipboard: {}...", &text[0..std::cmp::min(text.len(), 40)]);
    }
}
