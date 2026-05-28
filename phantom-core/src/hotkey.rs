// phantom-core/src/hotkey.rs
//
// Cross-Platform Hotkey Detection — Domain 11: Cross-Platform Hardening
//
// ── Windows ──────────────────────────────────────────────────────────────────
// Uses WH_KEYBOARD_LL (low-level keyboard hook) for maximum compatibility
// with Office apps that intercept Alt before RegisterHotKey can fire.
//
// DESIGN: We ONLY suppress the 'M'/'V' key when Alt is held.
// We NEVER touch Alt key events — they pass through completely.
//
// WHY:
//   - RegisterHotKey fails when Word intercepts Alt for its ribbon first
//   - WH_KEYBOARD_LL fires before any app sees the keys
//   - Suppressing ONLY 'M'/'V' (not Alt) means Alt naturally releases itself
//   - Alt-up passes through → Windows clears Alt state → NO STUCK KEYS
//   - Ribbon might activate briefly, but injection re-focuses Word body
//
// ── macOS / Linux ────────────────────────────────────────────────────────────
// Uses `rdev::listen()` (already in Cargo.toml) which provides global keyboard
// events on macOS (via CGEvent tap) and Linux (via X11 / evdev).
//
// Hotkeys: Alt+M (ghost-write), Alt+V (voice), Alt+Shift+M (screen context)

use tokio::sync::mpsc::Sender;
use tracing::{info, warn, error};
use std::sync::atomic::{AtomicBool, AtomicIsize, Ordering};
use once_cell::sync::Lazy;
use std::sync::Mutex;

use crate::PhantomEvent;

// ── Shared state (all platforms) ─────────────────────────────────────────────

static GLOBAL_TX: Lazy<Mutex<Option<Sender<PhantomEvent>>>> = Lazy::new(|| Mutex::new(None));
static ALT_PRESSED: AtomicBool = AtomicBool::new(false);
static SHIFT_PRESSED: AtomicBool = AtomicBool::new(false);
static CONTROL_PRESSED: AtomicBool = AtomicBool::new(false);

/// HWND of the window that had focus when Alt+M fired (Windows only).
/// On non-Windows platforms this is always 0.
pub static CAPTURED_HWND: AtomicIsize = AtomicIsize::new(0);

// ── HotkeyWatcher — platform-agnostic entry point ────────────────────────────

pub struct HotkeyWatcher {
    hotkey_str: String,
    tx: Sender<PhantomEvent>,
}

impl HotkeyWatcher {
    pub fn new(hotkey_str: String, tx: Sender<PhantomEvent>) -> Self {
        HotkeyWatcher { hotkey_str, tx }
    }

    pub fn get_captured_hwnd() -> isize {
        CAPTURED_HWND.load(Ordering::SeqCst)
    }

    pub fn run(self) {
        {
            let mut guard = GLOBAL_TX.lock().unwrap();
            *guard = Some(self.tx.clone());
        }
        info!("⌨️  Installing keyboard hook (Target: {})", self.hotkey_str);

        #[cfg(windows)]
        Self::run_windows(self.hotkey_str);

        #[cfg(not(windows))]
        Self::run_rdev();
    }

    // ── Windows: WH_KEYBOARD_LL ───────────────────────────────────────────────

    #[cfg(windows)]
    fn run_windows(hotkey_str: String) {
        use windows::Win32::UI::WindowsAndMessaging::{
            SetWindowsHookExW, UnhookWindowsHookEx, CallNextHookEx,
            GetMessageW, DispatchMessageW, TranslateMessage,
            WH_KEYBOARD_LL, MSG,
        };

        std::thread::spawn(move || {
            unsafe {
                let h_hook = SetWindowsHookExW(
                    WH_KEYBOARD_LL,
                    Some(low_level_keyboard_proc),
                    None,
                    0,
                ).expect("Failed to install WH_KEYBOARD_LL hook");

                info!("✅ Keyboard hook active (Windows WH_KEYBOARD_LL). Listening for Alt+M.");
                info!("   Alt events pass through unmodified — no stuck key risk.");

                let mut msg = MSG::default();
                while GetMessageW(&mut msg, None, 0, 0).as_bool() {
                    let _ = TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }

                UnhookWindowsHookEx(h_hook).ok();
                info!("🔑 Keyboard hook removed.");
            }
        });
    }

    // ── macOS / Linux: rdev global listener ─────────────────────────────────

    #[cfg(not(windows))]
    fn run_rdev() {
        use rdev::{listen, EventType, Key};

        std::thread::spawn(move || {
            info!("✅ Keyboard hook active (rdev cross-platform). Listening for Alt+M.");

            // rdev::listen blocks the thread and calls the callback for every event.
            // We cannot return a Result from listen's callback, so we use the atomics.
            if let Err(e) = listen(move |event| {
                match event.event_type {
                    // Track modifier key state
                    EventType::KeyPress(Key::Alt) | EventType::KeyPress(Key::AltGr) => {
                        ALT_PRESSED.store(true, Ordering::SeqCst);
                    }
                    EventType::KeyRelease(Key::Alt) | EventType::KeyRelease(Key::AltGr) => {
                        ALT_PRESSED.store(false, Ordering::SeqCst);
                    }
                    EventType::KeyPress(Key::ShiftLeft) | EventType::KeyPress(Key::ShiftRight) => {
                        SHIFT_PRESSED.store(true, Ordering::SeqCst);
                    }
                    EventType::KeyRelease(Key::ShiftLeft) | EventType::KeyRelease(Key::ShiftRight) => {
                        SHIFT_PRESSED.store(false, Ordering::SeqCst);
                    }
                    EventType::KeyPress(Key::ControlLeft) | EventType::KeyPress(Key::ControlRight) => {
                        CONTROL_PRESSED.store(true, Ordering::SeqCst);
                    }
                    EventType::KeyRelease(Key::ControlLeft) | EventType::KeyRelease(Key::ControlRight) => {
                        CONTROL_PRESSED.store(false, Ordering::SeqCst);
                    }

                    EventType::KeyPress(key) => {
                        let alt = ALT_PRESSED.load(Ordering::SeqCst);
                        let shift = SHIFT_PRESSED.load(Ordering::SeqCst);
                        let ctrl = CONTROL_PRESSED.load(Ordering::SeqCst);

                        // Ctrl+Shift+Z → Undo
                        if ctrl && shift && key == Key::KeyZ {
                            info!("↩️ Ctrl+Shift+Z detected (rdev)! Undo triggered.");
                            send_event(PhantomEvent::UndoPressed);
                        }
                        // Alt+Shift+M → Screen Context (must check before Alt+M)
                        else if alt && shift && key == Key::KeyM {
                            info!("📸 Alt+Shift+M detected (rdev)! Screen Context triggered.");
                            send_event(PhantomEvent::ScreenContextPressed);
                        }
                        // Alt+V → Voice Dictation
                        else if alt && key == Key::KeyV {
                            info!("🎤 Alt+V detected (rdev)! Voice Dictation triggered.");
                            send_event(PhantomEvent::VoicePressed);
                        }
                        // Alt+M (no Shift) → Ghost-Write
                        else if alt && !shift && key == Key::KeyM {
                            info!("🔥 Alt+M detected (rdev)! Ghost-Write triggered.");
                            send_event(PhantomEvent::HotkeyPressed);
                        }
                    }
                    _ => {}
                }
            }) {
                error!("[rdev] Global keyboard listener error: {:?}", e);
                warn!("On Linux, rdev requires X11 (DISPLAY env var) or root for evdev.");
                warn!("On macOS, you may need to grant Accessibility permission.");
            }
        });
    }
}

// ── Helper: send PhantomEvent to main loop ────────────────────────────────────

fn send_event(event: PhantomEvent) {
    if let Ok(guard) = GLOBAL_TX.try_lock() {
        if let Some(tx) = guard.as_ref() {
            let _ = tx.blocking_send(event);
        }
    }
}

// ── Windows: Low-Level Keyboard Hook Callback ─────────────────────────────────
//
// This function is only compiled on Windows. It captures the exact HWND that
// was focused when Alt+M fired — critical for the injector to type into the
// correct window.

#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{
    CallNextHookEx, KBDLLHOOKSTRUCT, WM_KEYDOWN, WM_SYSKEYDOWN, HC_ACTION,
    GetForegroundWindow,
};
#[cfg(windows)]
use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM, HWND};
#[cfg(windows)]
use windows::Win32::UI::Input::KeyboardAndMouse::{
    VK_MENU, VK_LMENU, VK_RMENU, VK_SHIFT, VK_LSHIFT, VK_RSHIFT,
    VK_CONTROL, VK_LCONTROL, VK_RCONTROL,
};

#[cfg(windows)]
unsafe extern "system" fn low_level_keyboard_proc(
    code: i32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    if code != HC_ACTION as i32 {
        return CallNextHookEx(None, code, wparam, lparam);
    }

    let kbd = *(lparam.0 as *const KBDLLHOOKSTRUCT);
    let msg = wparam.0 as u32;
    let is_down = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;
    let is_up = msg == 0x0101 /* WM_KEYUP */ || msg == 0x0105 /* WM_SYSKEYUP */;

    // Track Alt state — but PASS THROUGH all Alt events unchanged.
    // Not consuming Alt-up is what prevents Alt from getting stuck.
    let is_alt_vk = kbd.vkCode == VK_MENU.0 as u32
        || kbd.vkCode == VK_LMENU.0 as u32
        || kbd.vkCode == VK_RMENU.0 as u32;

    if is_alt_vk {
        ALT_PRESSED.store(is_down, Ordering::SeqCst);
        return CallNextHookEx(None, code, wparam, lparam);
    }

    // Track Shift state (same principle — pass through, only track)
    let is_shift_vk = kbd.vkCode == VK_SHIFT.0 as u32
        || kbd.vkCode == VK_LSHIFT.0 as u32
        || kbd.vkCode == VK_RSHIFT.0 as u32;

    if is_shift_vk {
        SHIFT_PRESSED.store(is_down, Ordering::SeqCst);
        return CallNextHookEx(None, code, wparam, lparam);
    }

    // Track Ctrl state (same principle — pass through, only track)
    let is_ctrl_vk = kbd.vkCode == VK_CONTROL.0 as u32
        || kbd.vkCode == VK_LCONTROL.0 as u32
        || kbd.vkCode == VK_RCONTROL.0 as u32;

    if is_ctrl_vk {
        CONTROL_PRESSED.store(is_down, Ordering::SeqCst);
        return CallNextHookEx(None, code, wparam, lparam);
    }

    // ── Ctrl+Shift+Z: Undo last injection ──────────────────────────────
    if kbd.vkCode == 0x5A /* Z */ && is_down
       && CONTROL_PRESSED.load(Ordering::SeqCst)
       && SHIFT_PRESSED.load(Ordering::SeqCst)
    {
        let hwnd: HWND = GetForegroundWindow();
        CAPTURED_HWND.store(hwnd.0 as isize, Ordering::SeqCst);
        info!("↩️ Ctrl+Shift+Z detected! Triggering Undo. HWND={:?}", hwnd.0);
        send_event(PhantomEvent::UndoPressed);
        return LRESULT(1); // Suppress 'Z'
    }

    // ── Alt+Shift+M: Screen Context (must check BEFORE Alt+M) ─────────────
    if kbd.vkCode == 0x4D && is_down
       && ALT_PRESSED.load(Ordering::SeqCst)
       && SHIFT_PRESSED.load(Ordering::SeqCst)
    {
        let hwnd: HWND = GetForegroundWindow();
        CAPTURED_HWND.store(hwnd.0 as isize, Ordering::SeqCst);
        info!("📸 Alt+Shift+M detected! Screen Context → HWND={:?}", hwnd.0);
        send_event(PhantomEvent::ScreenContextPressed);
        return LRESULT(1); // Suppress 'M'
    }

    // ── Alt+V: Voice Dictation ─────────────────────────────────────────────
    if kbd.vkCode == 0x56 /* V */ && is_down && ALT_PRESSED.load(Ordering::SeqCst) {
        let hwnd: HWND = GetForegroundWindow();
        CAPTURED_HWND.store(hwnd.0 as isize, Ordering::SeqCst);
        info!("🎤 Alt+V detected! Voice Dictation → HWND={:?}", hwnd.0);
        send_event(PhantomEvent::VoicePressed);
        return LRESULT(1); // Suppress 'V'
    }

    // ── Alt+M: Ghost-Write (original hotkey) ──────────────────────────────
    if kbd.vkCode == 0x4D && is_down && ALT_PRESSED.load(Ordering::SeqCst)
       && !SHIFT_PRESSED.load(Ordering::SeqCst)  // NOT Alt+Shift+M
    {
        let hwnd: HWND = GetForegroundWindow();
        CAPTURED_HWND.store(hwnd.0 as isize, Ordering::SeqCst);
        info!("🔥 Alt+M detected! HWND={:?}", hwnd.0);
        send_event(PhantomEvent::HotkeyPressed);
        return LRESULT(1); // SUPPRESS ONLY 'M'
    }

    // All other keys pass through unchanged
    CallNextHookEx(None, code, wparam, lparam)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_atomic_state_initial_values() {
        assert!(!ALT_PRESSED.load(Ordering::SeqCst));
        assert!(!SHIFT_PRESSED.load(Ordering::SeqCst));
        assert_eq!(CAPTURED_HWND.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn test_hotkey_watcher_construction() {
        let (tx, _rx) = tokio::sync::mpsc::channel(10);
        let watcher = HotkeyWatcher::new("Alt+M".to_string(), tx);
        assert_eq!(watcher.hotkey_str, "Alt+M");
    }

    #[test]
    fn test_get_captured_hwnd_returns_zero_initially() {
        CAPTURED_HWND.store(0, Ordering::SeqCst);
        assert_eq!(HotkeyWatcher::get_captured_hwnd(), 0);
    }
}
