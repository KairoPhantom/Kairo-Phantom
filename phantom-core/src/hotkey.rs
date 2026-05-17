/// Hotkey detection using WH_KEYBOARD_LL.
///
/// DESIGN: We ONLY suppress the 'M' key when Alt is held.
/// We NEVER touch Alt key events — they pass through completely.
///
/// WHY:
///   - RegisterHotKey fails when Word intercepts Alt for its ribbon first
///   - WH_KEYBOARD_LL fires before any app sees the keys
///   - Suppressing ONLY 'M' (not Alt) means Alt naturally releases itself
///   - Alt-up passes through → Windows clears Alt state → NO STUCK KEYS
///   - Ribbon might activate briefly, but injection re-focuses Word body
///
/// WHAT WE DON'T DO (and why):
///   - We don't consume Alt-up (that's what caused stuck Alt in all prior attempts)
///   - We don't inject synthetic key events in the hook callback (deadlock risk)
///   - We don't use Mutex in the hook callback (deadlock risk)

use tokio::sync::mpsc::Sender;
use tracing::{info, error};
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, AtomicIsize, Ordering};
use once_cell::sync::Lazy;

use windows::Win32::UI::WindowsAndMessaging::{
    SetWindowsHookExW, UnhookWindowsHookEx, CallNextHookEx,
    GetMessageW, DispatchMessageW, TranslateMessage,
    WH_KEYBOARD_LL, KBDLLHOOKSTRUCT, WM_KEYDOWN, WM_SYSKEYDOWN,
    HC_ACTION, MSG, GetForegroundWindow,
};
use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM, HWND};
use windows::Win32::UI::Input::KeyboardAndMouse::{VK_MENU, VK_LMENU, VK_RMENU};

use crate::PhantomEvent;

static GLOBAL_TX: Lazy<Mutex<Option<Sender<PhantomEvent>>>> = Lazy::new(|| Mutex::new(None));

// Lock-free atomics — NEVER use Mutex in a keyboard hook callback
static ALT_PRESSED: AtomicBool = AtomicBool::new(false);

/// HWND of the window that had focus when Alt+M fired.
pub static CAPTURED_HWND: AtomicIsize = AtomicIsize::new(0);

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

        std::thread::spawn(move || {
            unsafe {
                let h_hook = SetWindowsHookExW(
                    WH_KEYBOARD_LL,
                    Some(low_level_keyboard_proc),
                    None,
                    0,
                ).expect("Failed to install WH_KEYBOARD_LL hook");

                info!("✅ Keyboard hook active. Listening for Alt+M.");
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
}

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
        // Update our tracking — but let the event pass through to Windows
        ALT_PRESSED.store(is_down, Ordering::SeqCst);
        // DO NOT return LRESULT(1) here — that would consume Alt and stick it
        return CallNextHookEx(None, code, wparam, lparam);
    }

    // Detect 'M' key DOWN while Alt is held
    if kbd.vkCode == 0x4D && is_down && ALT_PRESSED.load(Ordering::SeqCst) {
        // Capture focused window BEFORE we do anything else
        let hwnd: HWND = GetForegroundWindow();
        CAPTURED_HWND.store(hwnd.0 as isize, Ordering::SeqCst);

        info!("🔥 Alt+M detected! HWND={:?}", hwnd.0);

        // Signal main loop (try_lock only — never block in a hook)
        if let Ok(guard) = GLOBAL_TX.try_lock() {
            if let Some(tx) = guard.as_ref() {
                let _ = tx.blocking_send(PhantomEvent::HotkeyPressed);
            }
        }

        // SUPPRESS ONLY 'M' — prevents 'm' appearing in the document.
        // Alt passes through naturally and will release on its own.
        return LRESULT(1);
    }

    // All other keys pass through unchanged
    CallNextHookEx(None, code, wparam, lparam)
}
