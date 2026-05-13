# Third-Party Notices

Kairo Phantom integrates the following open-source libraries and projects. We are grateful to every maintainer listed here.

All licenses listed are compatible with the MIT license under which Kairo Phantom is distributed.

---

## Core Runtime

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **Tokio** | 1.44 | MIT | https://github.com/tokio-rs/tokio |
| **Serde** | 1.x | MIT / Apache-2.0 | https://github.com/serde-rs/serde |
| **serde_json** | 1.x | MIT / Apache-2.0 | https://github.com/serde-rs/json |
| **anyhow** | 1.x | MIT / Apache-2.0 | https://github.com/dtolnay/anyhow |
| **tracing** | 0.1 | MIT | https://github.com/tokio-rs/tracing |
| **tracing-subscriber** | 0.3 | MIT | https://github.com/tokio-rs/tracing |

## AI & Inference

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **ollama-rs** | 0.2 | MIT | https://github.com/pepperoni21/ollama-rs |
| **reqwest** | 0.12 | MIT / Apache-2.0 | https://github.com/seanmonstar/reqwest |
| **futures** | 0.3 | MIT / Apache-2.0 | https://github.com/rust-lang/futures-rs |

## OS Integration & Input

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **uiautomation** | 0.25 | MIT | https://github.com/leexgone/uiautomation-rs |
| **enigo** | 0.2 | MIT | https://github.com/enigo-rs/enigo |
| **global-hotkey** | 0.6 | MIT / Apache-2.0 | https://github.com/tauri-apps/global-hotkey |
| **rdev** | 0.5 | MIT | https://github.com/Narsil/rdev |
| **windows** | 0.58 | MIT / Apache-2.0 | https://github.com/microsoft/windows-rs |

## Memory & Storage

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **rusqlite** | 0.31 | MIT | https://github.com/rusqlite/rusqlite |
| **dirs** | 5.x | MIT / Apache-2.0 | https://github.com/dirs-dev/dirs-rs |
| **tempfile** | 3.x | MIT / Apache-2.0 | https://github.com/Stebalien/tempfile |

## CRDT & Collaboration

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **yrs** (Yjs Rust port) | 0.21 | MIT | https://github.com/y-crdt/y-crdt |

## WASM Sandbox

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **wasmtime** | 25.x | Apache-2.0 | https://github.com/bytecodealliance/wasmtime |
| **ed25519-dalek** | 2.x | MIT / Apache-2.0 | https://github.com/dalek-cryptography/curve25519-dalek |
| **sha2** | 0.10 | MIT / Apache-2.0 | https://github.com/RustCrypto/hashes |

## UI & Overlay

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **Tauri** | 2.x | MIT / Apache-2.0 | https://github.com/tauri-apps/tauri |
| **wgpu** | 0.20 | MIT / Apache-2.0 | https://github.com/gfx-rs/wgpu |

## Data Formats & Parsing

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **zip** | 2.x | MIT | https://github.com/zip-rs/zip2 |
| **toml** | 0.8 | MIT / Apache-2.0 | https://github.com/toml-rs/toml |
| **hex** | 0.4 | MIT / Apache-2.0 | https://github.com/KokaKiwi/rust-hex |

## Cryptography & Security

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **jsonwebtoken** | 9.x | MIT | https://github.com/Keats/jsonwebtoken |
| **rand** | 0.8 | MIT / Apache-2.0 | https://github.com/rust-random/rand |

## Testing

| Component | Version | License | Upstream |
|:---|:---|:---|:---|
| **proptest** | 1.4 | MIT / Apache-2.0 | https://github.com/proptest-rs/proptest |
| **criterion** | 0.5 | MIT / Apache-2.0 | https://github.com/bheisler/criterion.rs |
| **tempfile** | 3.x | MIT / Apache-2.0 | https://github.com/Stebalien/tempfile |

---

## Conceptual Inspirations

The following projects influenced Kairo Phantom's architecture. Their source code is **not** included in this repository; all integration is via published crates.io dependencies or documented API bridges.

| Inspiration | Role in Kairo | Upstream |
|:---|:---|:---|
| **MemGPT / MemMachine** | Memory tiering and ground-truth storage architecture | https://github.com/cpacker/MemGPT |
| **Alaya** | Cognitive decay curves and memory lifecycle design | Research paper: Alaya Memory Model |
| **PRIME** (Preference Reasoning) | Meta-operation semantics (merge/split/generalize) | Research-inspired design |
| **Waza** | Skill-based agent architecture | Internal design, open-spec |
| **gl-transitions** | WGSL transition shader patterns | https://gl-transitions.com |

---

*If you believe a dependency or attribution has been omitted, please [open an issue](https://github.com/Kartik24Hulmukh/Kairo-Phantom/issues).*
