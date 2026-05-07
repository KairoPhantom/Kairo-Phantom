/// Hotkey Watcher — listens for the global hotkey (Ctrl+Space by default)
/// using the rdev crate. Runs on its own blocking thread.

use rdev::{listen, Event, EventType, Key};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::sync::mpsc::Sender;
use tracing::{debug, warn};

use crate::PhantomEvent;

pub struct HotkeyWatcher {
    hotkey: String,
    tx: Sender<PhantomEvent>,
}

impl HotkeyWatcher {
    pub fn new(hotkey: String, tx: Sender<PhantomEvent>) -> Self {
        HotkeyWatcher { hotkey, tx }
    }

    /// Run the hotkey listener (blocking — must be on a dedicated thread)
    pub fn run(self) {
        let ctrl_pressed = Arc::new(AtomicBool::new(false));
        let ctrl_clone = ctrl_pressed.clone();
        let tx = self.tx;

        if let Err(e) = listen(move |event: Event| {
            match event.event_type {
                EventType::KeyPress(Key::ControlLeft) | EventType::KeyPress(Key::ControlRight) => {
                    ctrl_clone.store(true, Ordering::SeqCst);
                }
                EventType::KeyRelease(Key::ControlLeft) | EventType::KeyRelease(Key::ControlRight) => {
                    ctrl_clone.store(false, Ordering::SeqCst);
                }
                EventType::KeyPress(Key::Space) => {
                    if ctrl_clone.load(Ordering::SeqCst) {
                        debug!("Hotkey Ctrl+Space detected — firing event");
                        // Blocking send on async channel from sync context
                        let _ = tx.blocking_send(PhantomEvent::HotkeyPressed);
                    }
                }
                EventType::KeyPress(_) => {
                    // Any other key = user is typing
                    let _ = tx.blocking_send(PhantomEvent::UserTyping);
                }
                _ => {}
            }
        }) {
            warn!("Hotkey watcher error: {:?}", e);
        }
    }
}
