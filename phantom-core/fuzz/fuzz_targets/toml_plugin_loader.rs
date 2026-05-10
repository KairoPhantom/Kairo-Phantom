/// Fuzz target: TOML plugin loader
/// Attack surface: arbitrary TOML files from plugin marketplace
/// 
/// Validates: toml::from_str() and plugin config parsing never panics on 
/// malformed TOML, deeply nested tables, unicode keys, circular-looking structures
#![no_main]
use libfuzzer_sys::fuzz_target;
use phantom_core::config::PhantomConfig;
use serde_json::Value;

fuzz_target!(|data: &[u8]| {
    let s = String::from_utf8_lossy(data);
    
    // 1. Raw TOML parse — must not panic on any input
    let _: Result<toml::Value, _> = toml::from_str(&s);
    
    // 2. Try to parse as PhantomConfig — must not panic, only Err or Ok
    let _: Result<PhantomConfig, _> = toml::from_str(&s);
    
    // 3. If valid TOML, test round-trip stability
    if let Ok(val) = toml::from_str::<toml::Value>(&s) {
        // Serialize back — must not panic
        let _serialized = toml::to_string(&val);
    }
});
