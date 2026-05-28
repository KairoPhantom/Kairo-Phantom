//! Toast Notification — P0-B2
//! Native Windows balloon notifications via Shell_NotifyIconW.
//! Replaces the old PowerShell NotifyIcon approach with zero-process-spawn overhead.
//! V4: Added streaming indicator (pulsing ghost icon) + agent selection debug logging.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

// ─── Native Windows Balloon Notification Backend ──────────────────────────────
//
// Uses Shell_NotifyIconW with NIF_INFO to show balloon tips from a hidden window.
// A persistent tray icon is created lazily on first use and reused for all toasts.

#[cfg(windows)]
mod win_balloon {
    use once_cell::sync::OnceCell;
    use std::sync::Mutex;

    use windows::core::PCWSTR;
    use windows::Win32::Foundation::{HINSTANCE, HWND, LPARAM, LRESULT, WPARAM};
    use windows::Win32::UI::Shell::{
        Shell_NotifyIconW, NIF_ICON, NIF_INFO, NIF_MESSAGE, NIF_TIP, NIM_ADD,
        NIM_MODIFY, NOTIFYICONDATAW, NOTIFYICONDATAW_0,
    };
    use windows::Win32::UI::WindowsAndMessaging::{
        CreateWindowExW, DefWindowProcW, LoadIconW, RegisterClassW, CS_HREDRAW,
        CS_VREDRAW, IDI_APPLICATION, WINDOW_EX_STYLE, WM_USER, WNDCLASSW,
        WS_OVERLAPPEDWINDOW,
    };

    /// Balloon icon types — maps to NIIF_* constants.
    #[repr(u32)]
    #[derive(Clone, Copy)]
    pub enum BalloonIcon {
        Info = 0x00000001,    // NIIF_INFO
        Warning = 0x00000002, // NIIF_WARNING
    }

    /// WM_USER + 1 — the callback message the tray icon sends to our hidden window.
    const WM_TRAYICON: u32 = WM_USER + 1;

    /// The hidden HWND used as the tray icon's owner. Created once, lives forever.
    static TRAY_STATE: OnceCell<Mutex<TrayState>> = OnceCell::new();

    struct TrayState {
        hwnd: HWND,
        icon_added: bool,
    }

    // SAFETY: HWND is a pointer-sized handle that Windows guarantees is valid
    // across threads. We protect mutation with a Mutex.
    unsafe impl Send for TrayState {}

    /// Encode a Rust &str into a null-terminated UTF-16 buffer of exactly `N` u16s.
    /// Truncates if the string is too long.
    fn encode_wide<const N: usize>(s: &str) -> [u16; N] {
        let mut buf = [0u16; N];
        for (i, unit) in s.encode_utf16().take(N - 1).enumerate() {
            buf[i] = unit;
        }
        buf
    }

    /// Minimal window-proc — just forwards everything to DefWindowProcW.
    unsafe extern "system" fn wnd_proc(
        hwnd: HWND,
        msg: u32,
        wparam: WPARAM,
        lparam: LPARAM,
    ) -> LRESULT {
        unsafe { DefWindowProcW(hwnd, msg, wparam, lparam) }
    }

    /// Create the hidden message-only window and register the window class.
    fn create_hidden_hwnd() -> HWND {
        unsafe {
            let class_name = encode_wide::<64>("KairoPhantomTrayClass");

            let wc = WNDCLASSW {
                style: CS_HREDRAW | CS_VREDRAW,
                lpfnWndProc: Some(wnd_proc),
                hInstance: HINSTANCE::default(),
                lpszClassName: PCWSTR(class_name.as_ptr()),
                ..Default::default()
            };
            RegisterClassW(&wc);

            let hwnd = CreateWindowExW(
                WINDOW_EX_STYLE::default(),
                PCWSTR(class_name.as_ptr()),
                PCWSTR::null(),
                WS_OVERLAPPEDWINDOW,
                0,
                0,
                0,
                0,
                HWND::default(),
                None,
                HINSTANCE::default(),
                None,
            ).unwrap_or(HWND::default());
            if hwnd == HWND::default() {
                tracing::error!("Failed to create hidden HWND for tray icon");
            }
            hwnd
        }
    }

    /// Show (or update) a balloon notification in the system tray.
    pub fn show_balloon(title: &str, message: &str, icon: BalloonIcon) {
        let state = TRAY_STATE.get_or_init(|| {
            Mutex::new(TrayState {
                hwnd: create_hidden_hwnd(),
                icon_added: false,
            })
        });

        let Ok(mut guard) = state.lock() else {
            tracing::warn!("Tray state mutex poisoned — falling back to log-only");
            return;
        };

        let hwnd = guard.hwnd;
        if hwnd == HWND::default() {
            return;
        }

        unsafe {
            let h_icon = LoadIconW(HINSTANCE::default(), IDI_APPLICATION)
                .unwrap_or_default();

            let mut nid = NOTIFYICONDATAW {
                cbSize: std::mem::size_of::<NOTIFYICONDATAW>() as u32,
                hWnd: hwnd,
                uID: 1,
                uFlags: NIF_ICON | NIF_MESSAGE | NIF_TIP | NIF_INFO,
                uCallbackMessage: WM_TRAYICON,
                hIcon: h_icon,
                szTip: encode_wide::<128>("Kairo Phantom"),
                szInfo: encode_wide::<256>(message),
                szInfoTitle: encode_wide::<64>(title),
                Anonymous: NOTIFYICONDATAW_0::default(),
                ..Default::default()
            };
            nid.dwInfoFlags = windows::Win32::UI::Shell::NOTIFY_ICON_INFOTIP_FLAGS(icon as u32);

            if !guard.icon_added {
                let _ = Shell_NotifyIconW(NIM_ADD, &nid);
                guard.icon_added = true;
            } else {
                let _ = Shell_NotifyIconW(NIM_MODIFY, &nid);
            }
        }
    }
}

// ─── Public API ───────────────────────────────────────────────────────────────

/// Show a Windows toast notification for a PAHF clarification request.
/// Replaces the old behavior of injecting the question text into the document.
pub fn show_clarification_toast(question: &str) {
    tracing::info!("🔔 PAHF clarification (toast): {}", question);

    #[cfg(windows)]
    {
        win_balloon::show_balloon(
            "Kairo Phantom \u{1F480}",
            question,
            win_balloon::BalloonIcon::Info,
        );
    }

    #[cfg(not(windows))]
    {
        eprintln!("[Kairo] Clarification needed: {}", question);
    }
}

/// Show a completion toast when Kairo finishes generating.
pub fn show_completion_toast(chars_injected: usize, agent_name: &str) {
    tracing::info!("✅ Completion toast: {} chars from {}", chars_injected, agent_name);

    #[cfg(windows)]
    {
        let body = format!("{} generated {} characters", agent_name, chars_injected);
        win_balloon::show_balloon(
            "Kairo Phantom \u{1F480}",
            &body,
            win_balloon::BalloonIcon::Info,
        );
    }

    #[cfg(not(windows))]
    {
        println!("[Kairo] ✅ {} generated {} characters", agent_name, chars_injected);
    }
}

/// Show a progress toast for long-running operations (e.g. Ollama model pull).
pub fn show_progress_toast(message: &str) {
    tracing::info!("⏳ Progress toast: {}", message);

    #[cfg(windows)]
    {
        win_balloon::show_balloon(
            "Kairo Phantom \u{1F480}",
            message,
            win_balloon::BalloonIcon::Info,
        );
    }

    #[cfg(not(windows))]
    {
        println!("[Kairo] {}", message);
    }
}

/// Show an error toast for failures and warnings.
pub fn show_error_toast(message: &str) {
    tracing::warn!("❌ Error toast: {}", message);

    #[cfg(windows)]
    {
        win_balloon::show_balloon(
            "Kairo Phantom \u{1F480}",
            message,
            win_balloon::BalloonIcon::Warning,
        );
    }

    #[cfg(not(windows))]
    {
        eprintln!("[Kairo] ❌ {}", message);
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
                let _ = std::process::Command::new("powershell")
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
            let _ = std::process::Command::new("powershell")
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
