/// Fuzz target: MCP JSON-RPC parser
/// Attack surface: arbitrary JSON from any AI agent or IDE plugin
/// 
/// Validates: serde_json parsing of MCP payloads never panics on malformed JSON,
/// deeply nested structures, unicode escapes, huge strings, or malicious payloads
#![no_main]
use libfuzzer_sys::fuzz_target;
use serde_json::Value;

fuzz_target!(|data: &[u8]| {
    let s = String::from_utf8_lossy(data);
    
    // 1. Raw parse — must handle any bytes without panic
    let _: Result<Value, _> = serde_json::from_str(&s);
    
    // 2. Validate MCP request structure if parseable
    if let Ok(val) = serde_json::from_str::<Value>(&s) {
        // Extract fields without panicking on wrong types
        let _method = val.get("method").and_then(|v| v.as_str());
        let _id = val.get("id");
        let _params = val.get("params");
        
        // If it looks like a batch request, iterate it
        if let Some(arr) = val.as_array() {
            for _item in arr.iter().take(100) {
                // Just iterate — must not panic on array elements
            }
        }
    }
});
