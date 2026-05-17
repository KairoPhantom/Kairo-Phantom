/// Hotkey Watcher — WH_KEYBOARD_LL hook for Alt+M detection.
///
/// KEY DESIGN DECISIONS:
/// 1. Uses AtomicBool/AtomicIsize (lock-free) — Mutex in hook callbacks can deadlock.
/// 2. When consuming the Alt key-up, we FIRST inject a synthetic Alt-up via SendInput
///    (with LLMHF_INJECTED flag set via dwExtraInfo) so Windows clears its internal
///    Alt-key-down state. Then we consume the real Alt-up. This prevents Alt from
///    getting "stuck" in the OS keyboard state machine.
/// 3. We skip injected events in the hook (dwExtraInfo == KAIRO_INJECTED_MAGIC)
///    so our synthetic Alt-up doesn't trigger recursive processing.

use tokio::sync::mpsc::Sender;
use tracing::info;
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, AtomicIsize, Ordering};
use once_cell::sync::Lazy;
use windows::Win32::UI::WindowsAndMessaging::{
    SetWindowsHookExW, UnhookWindowsHookEx, CallNextHookEx, GetMessageW,
    WH_KEYBOARD_LL, KBDLLHOOKSTRUCT, WM_KEYDOWN, WM_SYSKEYDOWN, MSG, HC_ACTION,
    DispatchMessageW, TranslateMessage, GetForegroundWindow,
};
use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM, HWND};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    VK_MENU, VK_LMENU, VK_RMENU,
    SendInput, INPUT, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP,
};

use crate::PhantomEvent;

/// Magic value used in dwExtraInfo to mark our own injected events.
/// The hook skips events with this value to prevent infinite recursion.
const KAIRO_INJECTED_MAGIC: usize = 0xCA1B0FF0;

static GLOBAL_TX: Lazy<Mutex<Option<Sender<PhantomEvent>>>> = Lazy::new(|| Mutex::new(None));
static ALT_PRESSED: AtomicBool = AtomicBool::new(false);
static CONSUME_NEXT_ALT_UP: AtomicBool = AtomicBool::new(false);

/// HWND captured at the exact moment Alt+M fires.
pub static CAPTURED_HWND: AtomicIsize = AtomicIsize::new(0);

pub struct HotkeyWatcher {
    hotkey_str: String,
    tx: Sender<PhantomEvent>,
}

impl HotkeyWatcher {
    pub fn new(hotkey_str: String, tx: Sender<PhantomEvent>) -> Self {
        HotkeyWatcher { hotkey_str, tx }
    }

    pub fn run(self) {
        {
            let mut guard = GLOBAL_TX.lock().unwrap();
            *guard = Some(self.tx.clone());
        }
        info!("⌨️  Starting Keyboard Hook (Target: {})", self.hotkey_str);
        std::thread::spawn(move || {
            unsafe {
                let h_hook = SetWindowsHookExW(WH_KEYBOARD_LL, Some(low_level_keyboard_proc), None, 0)
                    .expect("Failed to install keyboard hook");
                info!("✅ Keyboard Hook active.");
                let mut msg = MSG::default();
                while GetMessageW(&mut msg, None, 0, 0).as_bool() {
                    let _ = TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }
                UnhookWindowsHookEx(h_hook).ok();
            }
        });
    }
}

unsafe extern "system" fn low_level_keyboard_proc(code: i32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    if code != HC_ACTION as i32 {
        return CallNextHookEx(None, code, wparam, lparam);
    }

    let kbd = *(lparam.0 as *const KBDLLHOOKSTRUCT);
    let msg = wparam.0 as u32;

    // Skip events WE injected (prevents infinite recursion)
    if kbd.dwExtraInfo == KAIRO_INJECTED_MAGIC {
        return CallNextHookEx(None, code, wparam, lparam);
    }

    let is_down = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;
    let is_up = msg == 0x0101 /* WM_KEYUP */ || msg == 0x0105 /* WM_SYSKEYUP */;

    // Track Alt key state
    let is_alt = kbd.vkCode == VK_MENU.0 as u32
        || kbd.vkCode == VK_LMENU.0 as u32
        || kbd.vkCode == VK_RMENU.0 as u32;

    if is_alt {
        ALT_PRESSED.store(is_down, Ordering::SeqCst);

        if is_up && CONSUME_NEXT_ALT_UP.swap(false, Ordering::SeqCst) {
            // CRITICAL FIX: Inject a synthetic Alt-up FIRST so Windows clears its
            // internal "Alt is held" state. Without this, Alt stays stuck forever.
            // We mark it with KAIRO_INJECTED_MAGIC so our hook ignores it.
            let synthetic_alt_up = [INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_MENU,
                        wScan: 0,
                        dwFlags: KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: KAIRO_INJECTED_MAGIC,
                    },
                },
            }];
            SendInput(&synthetic_alt_up, std::mem::size_of::<INPUT>() as i32);

            info!("🔑 Alt-up: injected synthetic release (clears OS state) + consumed real event");
            // Consume the REAL Alt-up so Windows doesn't see two Alt-ups (which would
            // toggle ribbon focus weirdly)
            return LRESULT(1);
        }
    }

    // Detect Alt+M
    if kbd.vkCode == 0x4D && is_down && ALT_PRESSED.load(Ordering::SeqCst) {
        let hwnd: HWND = GetForegroundWindow();
        CAPTURED_HWND.store(hwnd.0 as isize, Ordering::SeqCst);
        CONSUME_NEXT_ALT_UP.store(true, Ordering::SeqCst);

        info!("🔥 HOTKEY: Alt+M — HWND={:?}", hwnd.0);

        if let Ok(guard) = GLOBAL_TX.try_lock() {
            if let Some(tx) = guard.as_ref() {
                let _ = tx.blocking_send(PhantomEvent::HotkeyPressed);
            }
        }
        // Consume 'M' so it doesn't appear in the document
        return LRESULT(1);
    }

    CallNextHookEx(None, code, wparam, lparam)
}
