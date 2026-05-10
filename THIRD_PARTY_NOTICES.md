# Third-Party Notices

Kairo Phantom is built on the shoulders of giants. We are incredibly grateful to the open-source developers and communities who maintain the libraries that make this project possible.

## Rust Ecosystem
- **Wasmtime**: Used for our secure WASM plugin sandbox. Licensed under Apache 2.0 with LLVM Exception.
- **Tokio**: The async runtime powering Kairo's core loop. Licensed under MIT.
- **Yrs (Yjs Rust port)**: Used for conflict-free replicated data types (CRDTs). Licensed under MIT.

## Rendering & Visuals
- **WGPU & wgsl**: Used for the native, high-performance visual effects (such as the landing-effects ASCII renderer). Licensed under MIT / Apache 2.0.
- **GL-Transitions**: Kairo's transition shaders are heavily inspired by the incredible open-source `gl-transitions` community. Licensed under MIT.
- **Tearable Cloth Simulation**: Adapted from standard computer graphics mass-spring system techniques; specifically utilizing compute shader patterns established by the WGPU community.

## Data Parsing & Integration
- **Kreuzberg Parsers**: We utilize concepts and parsing strategies inspired by Kreuzberg for extracting semantic intelligence from documents.
- **Tauri**: Used for the glassmorphic overlay UI. Licensed under MIT / Apache 2.0.

*If you believe a dependency or inspiration has been omitted, please open an issue and we will correct it immediately.*
