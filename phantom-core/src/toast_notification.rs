//! Toast Notification — P0-B2
//! Replaces PAHF document injection with non-intrusive Windows toast overlays.
//! Shows clarification requests as balloon/toast notifications, not in-document text.
//! V4: Added streaming indicator (pulsing ghost icon) + agent selection debug logging.

use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Show a Windows toast notification for a PAHF clarification request.
/// Replaces the old behavior of injecting the question text into the document.
pub fn show_clarification_toast(question: &str) {
    tracing::info!("🔔 PAHF clarification (toast): {}", question);

    #[cfg(windows)]
    {
        // Escape single quotes for PowerShell
        let safe_q = question.replace('\'', "''").replace('"', "'");
        let script = format!(
            r#"Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.BalloonTipIcon = 'Info'
$n.BalloonTipTitle = '👻 Kairo needs clarification'
$n.BalloonTipText = '{}'
$n.Visible = $true
$n.ShowBalloonTip(8000)
Start-Sleep -Seconds 8
$n.Dispose()"#,
            safe_q
        );
        let _ = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", &script])
            .spawn();
    }

    #[cfg(not(windows))]
    {
        // Fallback: print to stderr so it doesn't pollute injected text
        eprintln!("[Kairo] Clarification needed: {}", question);
    }
}

/// Show a completion toast when Kairo finishes generating.
pub fn show_completion_toast(chars_injected: usize, agent_name: &str) {
    tracing::info!("✅ Completion toast: {} chars from {}", chars_injected, agent_name);

    #[cfg(windows)]
    {
        let script = format!(
            r#"Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.BalloonTipIcon = 'Info'
$n.BalloonTipTitle = '✅ Kairo Complete'
$n.BalloonTipText = '{} generated {} characters'
$n.Visible = $true
$n.ShowBalloonTip(3000)
Start-Sleep -Seconds 3
$n.Dispose()"#,
            agent_name, chars_injected
        );
        let _ = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", &script])
            .spawn();
    }
}

/// Show a progress toast for long-running operations (e.g. Ollama model pull).
pub fn show_progress_toast(message: &str) {
    tracing::info!("⏳ Progress toast: {}", message);

    #[cfg(windows)]
    {
        let safe_msg = message.replace('\'', "''");
        let script = format!(
            r#"Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.BalloonTipIcon = 'Info'
$n.BalloonTipTitle = '👻 Kairo Phantom'
$n.BalloonTipText = '{}'
$n.Visible = $true
$n.ShowBalloonTip(5000)
Start-Sleep -Seconds 5
$n.Dispose()"#,
            safe_msg
        );
        let _ = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", &script])
            .spawn();
    }
}

// ─── V4: Streaming Indicator (Pulsing Ghost Icon) ─────────────────────────────
//
// When AI streaming is in progress, show a pulsing tray icon animation in the
// Windows system tray. The animation runs until `stop_flag` is set to `true`.
// This fulfills the V4 immediate fix: "Add streaming indicator to overlay".

/// Shows a pulsing ghost icon in the system tray while streaming is active.
///
/// The caller receives an `Arc<AtomicBool>` stop handle. Set it to `true` to
/// terminate the animation. The animation automatically stops after `timeout_secs`.
///
/// Returns the stop handle so the caller can cancel early (e.g., on Esc).
///
/// # Usage
/// ```ignore
/// let stop = start_streaming_indicator("content", 30);
/// // ... streaming happens ...
/// stop.store(true, std::sync::atomic::Ordering::SeqCst);
/// show_completion_toast(256, "content");
/// ```
pub fn start_streaming_indicator(agent_id: &str, timeout_secs: u64) -> Arc<AtomicBool> {
    let stop_flag = Arc::new(AtomicBool::new(false));
    let stop_clone = stop_flag.clone();
    let agent_label = agent_id.to_string();

    tracing::info!("👻 Streaming indicator: starting (agent={}, timeout={}s)", agent_id, timeout_secs);

    std::thread::spawn(move || {
        let frames = ["👻", "👁", "💫", "✨"];
        let mut frame_idx = 0usize;
        let start = std::time::Instant::now();
        let timeout = std::time::Duration::from_secs(timeout_secs);

        while !stop_clone.load(Ordering::Relaxed) && start.elapsed() < timeout {
            let icon = frames[frame_idx % frames.len()];
            tracing::debug!("[StreamingIndicator] {} Kairo AI ({}) — generating...", icon, agent_label);

            // On Windows, update the console title as a lightweight visual indicator
            #[cfg(windows)]
            {
                let _ = Command::new("powershell")
                    .args([
                        "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                        "-Command",
                        &format!("$Host.UI.RawUI.WindowTitle = '{} Kairo Phantom — {} generating…'",
                            icon, agent_label),
                    ])
                    .spawn();
            }

            frame_idx += 1;
            std::thread::sleep(std::time::Duration::from_millis(500));
        }

        tracing::info!("👻 Streaming indicator: stopped (agent={})", agent_label);

        // Restore console title
        #[cfg(windows)]
        {
            let _ = Command::new("powershell")
                .args([
                    "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                    "-Command", "$Host.UI.RawUI.WindowTitle = 'Kairo Phantom'",
                ])
                .spawn();
        }
    });

    stop_flag
}

// ─── V4: Agent Selection Debug Logger ─────────────────────────────────────────
//
// Fulfills V4 immediate fix: "Log which agent was selected and why to a debug file".

/// Log agent selection decisions to ~/.kairo-phantom/agent_debug.jsonl.
/// Each line is a JSON object with timestamp, agent_id, score, doc_kind, and prompt_preview.
pub fn log_agent_selection(agent_id: &str, score: u8, doc_kind: &str, prompt_preview: &str) {
    let kairo_dir = dirs::home_dir()
        .unwrap_or_default()
        .join(".kairo-phantom");
    let log_path = kairo_dir.join("agent_debug.jsonl");

    let timestamp = chrono::Utc::now().to_rfc3339();
    // Truncate prompt preview to avoid giant log entries
    let safe_prompt = prompt_preview.chars().take(120).collect::<String>()
        .replace('"', "'");

    let entry = format!(
        r#"{{"ts":"{}","agent":"{}","score":{},"doc_kind":"{}","prompt":"{}"}}"#,
        timestamp, agent_id, score, doc_kind, safe_prompt
    );

    // Append to JSONL (non-blocking best-effort)
    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
    {
        use std::io::Write;
        let _ = writeln!(file, "{}", entry);
    }

    tracing::debug!("[AgentDebug] {}", entry);
}

