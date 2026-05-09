/// Hotkey Watcher — uses low-level Windows keyboard hooks (WH_KEYBOARD_LL).
/// Enhanced with Diagnostic Logging and Admin-check awareness.

use tokio::sync::mpsc::Sender;
use tracing::{info, warn, debug, error};
use std::sync::Mutex;
use once_cell::sync::Lazy;
use windows::Win32::UI::WindowsAndMessaging::{
    SetWindowsHookExW, UnhookWindowsHookEx, CallNextHookEx, GetMessageW, 
    WH_KEYBOARD_LL, KBDLLHOOKSTRUCT, WM_KEYDOWN, WM_SYSKEYDOWN, MSG, HC_ACTION,
    WM_KEYUP, WM_SYSKEYUP, DispatchMessageW, TranslateMessage
};
use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM};
use windows::Win32::UI::Input::KeyboardAndMouse::{VK_MENU, VK_LMENU, VK_RMENU};

use crate::PhantomEvent;

static GLOBAL_TX: Lazy<Mutex<Option<Sender<PhantomEvent>>>> = Lazy::new(|| Mutex::new(None));
static ALT_PRESSED: Lazy<Mutex<bool>> = Lazy::new(|| Mutex::new(false));

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

        info!("⌨️  DIAGNOSTIC MODE: Starting Keyboard Hook (Target: {})", self.hotkey_str);

        std::thread::spawn(move || {
            unsafe {
                let h_hook = SetWindowsHookExW(WH_KEYBOARD_LL, Some(low_level_keyboard_proc), None, 0)
                    .expect("Failed to install keyboard hook");

                info!("✅ Keyboard Hook active. If you don't see 'KEY:' logs when typing, Kairo is being blocked by Windows security.");

                let mut msg = MSG::default();
                // Standard Win32 Message Loop
                while GetMessageW(&mut msg, None, 0, 0).as_bool() {
                    TranslateMessage(&msg);
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
        let is_up = msg == WM_KEYUP || msg == WM_SYSKEYUP;

        // Diagnostic: Log keys in DEBUG
        // 0x4D is 'M'
        // 0x12 is Alt (VK_MENU)
        
        // Track ALL Alt keys (Left, Right, or General)
        if kbd.vkCode == VK_MENU.0 as u32 || kbd.vkCode == VK_LMENU.0 as u32 || kbd.vkCode == VK_RMENU.0 as u32 {
            let mut alt = ALT_PRESSED.lock().unwrap();
            *alt = is_down;
            debug!("KEY: Alt State Changed -> {}", is_down);
        }

        if kbd.vkCode == 0x4D && is_down {
            let alt = *ALT_PRESSED.lock().unwrap();
            debug!("KEY: 'M' Pressed (Alt held: {})", alt);
            
            if alt {
                info!("🔥 HOTKEY TRIGGERED: Alt + M detected!");
                if let Some(tx) = &*GLOBAL_TX.lock().unwrap() {
                    let _ = tx.blocking_send(PhantomEvent::HotkeyPressed);
                    // CONSUME THE KEY
                    return LRESULT(1);
                }
            }
        }
    }

    CallNextHookEx(None, code, wparam, lparam)
}
