/// Hotkey Watcher — uses low-level Windows keyboard hooks (WH_KEYBOARD_LL).
/// Uses AtomicBool for lock-free state tracking (safe in hook callbacks).

use tokio::sync::mpsc::Sender;
use tracing::{info, debug};
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, AtomicIsize, Ordering};
use once_cell::sync::Lazy;
use windows::Win32::UI::WindowsAndMessaging::{
    SetWindowsHookExW, UnhookWindowsHookEx, CallNextHookEx, GetMessageW, 
    WH_KEYBOARD_LL, KBDLLHOOKSTRUCT, WM_KEYDOWN, WM_SYSKEYDOWN, MSG, HC_ACTION,
    DispatchMessageW, TranslateMessage, GetForegroundWindow,
};
use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM, HWND};
use windows::Win32::UI::Input::KeyboardAndMouse::{VK_MENU, VK_LMENU, VK_RMENU};

use crate::PhantomEvent;

static GLOBAL_TX: Lazy<Mutex<Option<Sender<PhantomEvent>>>> = Lazy::new(|| Mutex::new(None));

// CRITICAL: Use AtomicBool instead of Mutex for hook callback safety.
// Mutex::lock() in a low-level keyboard hook can deadlock or delay the hook chain,
// which causes Windows to skip our hook entirely — breaking ALL keyboard input.
static ALT_PRESSED: AtomicBool = AtomicBool::new(false);
static CONSUME_NEXT_ALT_UP: AtomicBool = AtomicBool::new(false);

/// HWND captured at the exact moment Alt+M fires — this is the user's target window.
pub static CAPTURED_HWND: AtomicIsize = AtomicIsize::new(0);

// Helper to read CAPTURED_HWND from other modules
impl crate::hotkey::HotkeyWatcher {
    pub fn get_captured_hwnd() -> isize {
        CAPTURED_HWND.load(Ordering::SeqCst)
    }
}

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
    if code == HC_ACTION as i32 {
        let kbd = *(lparam.0 as *const KBDLLHOOKSTRUCT);
        let msg = wparam.0 as u32;

        let is_down = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;
        let is_up = msg == 0x0101 /* WM_KEYUP */ || msg == 0x0105 /* WM_SYSKEYUP */;

        // Track Alt key state (lock-free)
        if kbd.vkCode == VK_MENU.0 as u32 || kbd.vkCode == VK_LMENU.0 as u32 || kbd.vkCode == VK_RMENU.0 as u32 {
            ALT_PRESSED.store(is_down, Ordering::SeqCst);

            // When Alt+M fires, we set CONSUME_NEXT_ALT_UP.
            // The NEXT Alt key-up after that is consumed to prevent Windows from
            // interpreting it as "activate menu bar / ribbon".
            if is_up && CONSUME_NEXT_ALT_UP.swap(false, Ordering::SeqCst) {
                info!("🔑 Consumed Alt key-up to prevent ribbon activation");
                return LRESULT(1);
            }
        }

        // Check for 'M' key (0x4D) while Alt is held
        if kbd.vkCode == 0x4D && is_down && ALT_PRESSED.load(Ordering::SeqCst) {
            // Capture the foreground window RIGHT NOW
            let hwnd: HWND = GetForegroundWindow();
            CAPTURED_HWND.store(hwnd.0 as isize, Ordering::SeqCst);
            
            // Set flag to consume the next Alt key-up
            CONSUME_NEXT_ALT_UP.store(true, Ordering::SeqCst);
            
            info!("🔥 HOTKEY TRIGGERED: Alt+M detected! Captured HWND={:?}", hwnd.0);
            
            // Send event to main loop (this is the ONLY Mutex we touch in the hook)
            if let Ok(guard) = GLOBAL_TX.try_lock() {
                if let Some(tx) = guard.as_ref() {
                    let _ = tx.blocking_send(PhantomEvent::HotkeyPressed);
                }
            }
            
            // CONSUME the 'M' key — prevent it from appearing in the document
            return LRESULT(1);
        }
    }

    CallNextHookEx(None, code, wparam, lparam)
}
