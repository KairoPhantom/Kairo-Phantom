//! Toast Notification — P0-B2
//! Replaces PAHF document injection with non-intrusive Windows toast overlays.
//! Shows clarification requests as balloon/toast notifications, not in-document text.

use std::process::Command;

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
