use std::sync::atomic::AtomicBool;

// Fault points that can be toggled via config or CLI flags
pub static FAULT_UIA_TIMEOUT: AtomicBool = AtomicBool::new(false);
pub static FAULT_CLIPBOARD_FAILURE: AtomicBool = AtomicBool::new(false);
pub static FAULT_SSE_DISCONNECT: AtomicBool = AtomicBool::new(false);
pub static FAULT_OLLAMA_SLOW: AtomicBool = AtomicBool::new(false);

#[macro_export]
macro_rules! chaos_point {
    ($fault:expr, $action:block) => {
        if $fault.load(std::sync::atomic::Ordering::Relaxed) {
            $action
        }
    };
}
