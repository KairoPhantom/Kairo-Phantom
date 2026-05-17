/// Hotkey detection using RegisterHotKey Win32 API.
///
/// WHY RegisterHotKey instead of WH_KEYBOARD_LL:
///   WH_KEYBOARD_LL intercepts raw key events. If you consume Alt key-up
///   in the hook (return LRESULT(1)), Windows never marks Alt as released
///   in its internal key-state machine → Alt stays "stuck" forever.
///   This causes: G=Gemini, Ctrl+V broken, double-click=properties, etc.
///
///   RegisterHotKey is the CORRECT Windows API for global hotkeys:
///   - Windows manages ALL modifier state internally
///   - No risk of stuck keys — ever
///   - Used by AutoHotkey, PowerToys, every professional hotkey manager
///   - Simpler: just handle WM_HOTKEY in a message loop

use tokio::sync::mpsc::Sender;
use tracing::{info, error};
use std::sync::Mutex;
use std::sync::atomic::{AtomicIsize, Ordering};
use once_cell::sync::Lazy;

use windows::Win32::UI::WindowsAndMessaging::{
    GetMessageW, MSG, WM_HOTKEY, GetForegroundWindow,
};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    RegisterHotKey, UnregisterHotKey, MOD_ALT,
};
use windows::Win32::Foundation::HWND;

use crate::PhantomEvent;

static GLOBAL_TX: Lazy<Mutex<Option<Sender<PhantomEvent>>>> = Lazy::new(|| Mutex::new(None));

/// HWND of the window that had focus when Alt+M fired.
pub static CAPTURED_HWND: AtomicIsize = AtomicIsize::new(0);

const HOTKEY_ID: i32 = 0xCA1B; // unique ID for our Alt+M hotkey

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
        info!("⌨️  Registering system hotkey: {}", self.hotkey_str);

        std::thread::spawn(move || {
            unsafe {
                // Register Alt+M as a system hotkey.
                // Windows handles ALL modifier key state — no stuck keys possible.
                // MOD_ALT = 0x0001, 'M' = 0x4D
                let registered = unsafe {
                    RegisterHotKey(
                        HWND(std::ptr::null_mut()),
                        HOTKEY_ID,
                        MOD_ALT,
                        0x4D, // VK for 'M'
                    )
                };

                if registered.is_err() {
                    error!("❌ RegisterHotKey failed! Another app may own Alt+M.");
                    error!("   Try closing AutoHotkey or other keyboard tools.");
                    return;
                }
                info!("✅ Alt+M registered as system hotkey (RegisterHotKey).");
                info!("   No keyboard hook installed — zero risk of stuck modifier keys.");

                let mut msg = MSG::default();
                while unsafe { GetMessageW(&mut msg, None, 0, 0) }.as_bool() {
                    // WM_HOTKEY fires when user presses Alt+M.
                    // Windows has already handled modifier state — no stuck keys.
                    if msg.message == WM_HOTKEY && msg.wParam.0 as i32 == HOTKEY_ID {
                        // Capture the foreground window right as the hotkey fires
                        let hwnd: HWND = unsafe { GetForegroundWindow() };
                        CAPTURED_HWND.store(hwnd.0 as isize, Ordering::SeqCst);

                        info!("🔥 HOTKEY: Alt+M — HWND={:?}", hwnd.0);

                        if let Ok(guard) = GLOBAL_TX.try_lock() {
                            if let Some(tx) = guard.as_ref() {
                                let _ = tx.blocking_send(PhantomEvent::HotkeyPressed);
                            }
                        }
                    }
                }

                // Cleanup
                unsafe { let _ = UnregisterHotKey(HWND(std::ptr::null_mut()), HOTKEY_ID); }
                info!("🔑 Hotkey unregistered.");
            }
        });
    }
}
