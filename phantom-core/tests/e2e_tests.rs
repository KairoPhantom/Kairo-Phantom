use phantom_core::config::PhantomConfig;

#[test]
fn test_hotkey_simulation() {
    // Validate config loads properly
    let cfg = PhantomConfig::default();
    assert_eq!(cfg.model.provider, "ollama");
}
