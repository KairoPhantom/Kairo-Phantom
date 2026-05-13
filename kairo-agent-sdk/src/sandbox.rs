use wasmtime::*;
use wasmtime_wasi::{WasiCtxBuilder, WasiCtx};
use std::path::Path;

pub struct WasmSandbox {
    engine: Engine,
}

impl WasmSandbox {
    pub fn new() -> Self {
        let engine = Engine::default();
        Self { engine }
    }

    pub fn execute_agent_wasm(
        &self,
        wasm_path: &Path,
        input_prompt: &str,
        document_context: &str,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let mut linker = Linker::new(&self.engine);
        wasmtime_wasi::add_to_linker(&mut linker, |s| s)?;

        let wasi = WasiCtxBuilder::new()
            .env("PROMPT", input_prompt)?
            .env("CONTEXT", document_context)?
            .build();

        let mut store = Store::new(&self.engine, wasi);
        let module = Module::from_file(&self.engine, wasm_path)?;

        let instance = linker.instantiate(&mut store, &module)?;
        
        let run_func = instance.get_typed_func::<(), ()>(&mut store, "run")?;
        run_func.call(&mut store, ())?;

        // In a real WASI module, we'd capture stdout or have it write to a specific memory location/result
        // This is a stub returning a mocked WASM output.
        Ok(format!("[WASM Output for Prompt: {}]", input_prompt))
    }
}
