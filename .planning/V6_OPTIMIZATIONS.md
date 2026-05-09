# Kairo Phantom v6.0 — Production Optimization Roadmap
## Graphify Memory Graph — Agent Shared Context

### MISSION
Transform Kairo from a prototype-grade copilot into a category-defining document intelligence layer.
Target: 4-8x end-to-end latency improvement, enterprise-grade security, GPU-native rendering.

---

## PHASE_GROUP_A: Core Rust Engine Optimizations
**Priority: CRITICAL | Target File: phantom-core/src/**

### A1 — Zero-Alloc Tokio Async Pipeline
- **File**: phantom-core/src/main.rs, phantom-core/src/ai.rs
- **Action**: Add `once_cell::sync::Lazy<tokio::runtime::Runtime>` global runtime
- **Action**: Replace `Box<dyn Future>` pattern with inline enum state machines in hot path
- **Dependency**: memchr crate for SIMD text scanning
- **Expected Impact**: Async overhead 70-112ns → 30-45ns (40% improvement)
- **Cargo.toml add**: `memchr = "2.7"`

### A2 — SIMD-Accelerated Text Processing  
- **File**: phantom-core/src/ghost_session.rs, phantom-core/src/swarm.rs
- **Action**: Use `memchr::memmem::Finder` for token diffing in ghost session
- **Action**: Use SIMD byte-search for prompt preprocessing
- **Expected Impact**: 3-8x faster text diffs

### A3 — SSE Streaming Upgrade
- **File**: phantom-core/src/ai.rs (SSE client implementation)
- **Action**: Add `eventsource-stream` or use `reqwest::Response::bytes_stream()` with custom SSE parser
- **Action**: Write a zero-alloc hand-state-machine SSE parser (no eager String alloc)
- **Expected Impact**: ~3x faster token delivery to ghost overlay

---

## PHASE_GROUP_B: MCP Infrastructure Optimizations
**Priority: HIGH | Target: kairo-mcp/, phantom-core/src/mcp_bridge.rs**

### B1 — Global Model + Storage Caching
- **File**: phantom-core/src/mcp_bridge.rs, kairo-mcp/server.js
- **Action**: Add `once_cell::sync::Lazy` caches for model instances and DB connections
- **Action**: Implement TTL-based cache eviction (5min TTL for model, 30min for DB)
- **Expected Impact**: ~41x faster repeated tool calls (2485ms → 0.01ms warmup)

### B2 — Batch MCP Operations Tool
- **File**: kairo-mcp/server.js, phantom-core/src/mcp_bridge.rs
- **Action**: Add `kairo_batch_execute` MCP tool that chains: context_read → app_detect → ghost_write
- **Action**: Accept array of sub-operations, return all results in single response
- **Expected Impact**: 2-3x fewer round trips

### B3 — Parallel Swarm Execution
- **File**: phantom-core/src/swarm.rs
- **Action**: Use `futures::future::join_all` for independent agent calls
- **Action**: When Swarm Brain dispatches Prose + Design agents, run concurrently
- **Expected Impact**: ~50% reduction in multi-agent response time

---

## PHASE_GROUP_C: Presentation Engine — WGPU Native GPU
**Priority: HIGH | New file: phantom-core/src/wgpu_effects.rs**

### C1 — WGPU Rendering Pipeline
- **File**: phantom-core/src/wgpu_effects.rs (NEW)
- **Cargo.toml add**: `wgpu = "0.20"`, `image = "0.25"`, `bytemuck = "1.16"`
- **Action**: Create WgpuEffectsEngine struct with initialize/render/encode methods
- **Action**: Implement gl-transitions spec as WGPU fragment shaders (cloth_tear, glitch, wipe)
- **Action**: Hardware video encoding via OS APIs (NVENC/VideoToolbox/VAAPI)
- **Expected Impact**: 10-100x faster than CPU/Puppeteer, eliminates Node.js dependency

### C2 — Wire WGPU into Effects MCP
- **File**: mcp-servers/kairo-effects/server.py
- **Action**: Call wgpu_effects binary subprocess instead of Puppeteer for high-quality renders
- **Action**: Keep Puppeteer as fallback for compatibility
- **Cargo.toml add**: `wgpu = { version = "0.20", features = ["vulkan-portability"] }`

---

## PHASE_GROUP_D: WASM Plugin Sandbox Hardening
**Priority: HIGH | Target: phantom-core/src/wasm_sandbox.rs**

### D1 — Wasmtime Defense-in-Depth
- **File**: phantom-core/src/wasm_sandbox.rs
- **Cargo.toml**: already has `wasmtime = "21.0"`
- **Action**: Replace CompiledPlugin stub with REAL wasmtime Engine + Module
- **Action**: Enable guard pages, bounds checking, memory zeroing on teardown
- **Action**: Use Cranelift JIT compiler with `cranelift-native` CPU target
- **Action**: Wizer preinitialization for 32% faster cold starts

### D2 — Ed25519 Plugin Signature Verification
- **File**: phantom-core/src/wasm_sandbox.rs, phantom-core/src/identity.rs
- **Cargo.toml add**: `ed25519-dalek = "2.1"`, `sha2 = "0.10"`
- **Action**: Replace stub signature check with real Ed25519 verify
- **Action**: Generate actual Ed25519 keypair in identity.rs using ed25519-dalek

### D3 — Mandatory Security Manifest Enforcement
- **File**: phantom-core/src/wasm_sandbox.rs
- **Action**: Enforce at runtime: if plugin calls host fn not in manifest, KILL instance
- **Action**: Track actual imported host functions vs. declared capabilities

---

## PHASE_GROUP_E: Yjs CRDT Scaling
**Priority: MEDIUM | Target: phantom-core/src/yjs_peer.rs**

### E1 — Sub-Document Segmentation
- **File**: phantom-core/src/yjs_peer.rs
- **Action**: Split large docs into independently-synced YText fragments
- **Action**: Implement section-level YText: "heading_1", "body_1", "body_2", etc.
- **Expected Impact**: Large docs (>5MB) no longer require full state sync

### E2 — Awareness Throttling
- **File**: phantom-core/src/yjs_peer.rs
- **Action**: Only broadcast awareness on state TRANSITIONS, not continuously
- **Action**: Debounce awareness updates with 200ms threshold
- **Expected Impact**: Works at thousands of concurrent docs

### E3 — Snapshot-Based State Vectors
- **File**: phantom-core/src/yjs_peer.rs
- **Action**: Periodic StateVector diff capture every 30s
- **Action**: New sync: send only changes since last snapshot
- **Expected Impact**: Reduced sync overhead for reconnecting peers

---

## PHASE_GROUP_F: Enterprise Security Infrastructure
**Priority: MEDIUM | Target: phantom-core/src/identity.rs, governance.rs**

### F1 — Real Ed25519 Keypair (replacing pseudo-random)
- **File**: phantom-core/src/identity.rs
- **Cargo.toml add**: `ed25519-dalek = "2.1"`, `rand = "0.8"`, `sha2 = "0.10"`
- **Action**: Replace `generate_seed()` + manual hash with real `SigningKey::generate(&mut OsRng)`
- **Action**: Store keypair as PEM/DER, verify on load

### F2 — Append-Only Audit Log (JSONL)
- **File**: phantom-core/src/governance.rs
- **Action**: Write every AuditEvent to `~/.kairo-phantom/audit.jsonl` (append-only)
- **Action**: Include agent_id, user_id, doc_path, action, timestamp, result
- **Action**: Tamper-evident: each line includes hash of previous line (chain)

### F3 — JIT Permission Revocation
- **File**: phantom-core/src/identity.rs, phantom-core/src/main.rs
- **Action**: RBAC check returns scoped permission token with TTL
- **Action**: Token expires after operation completes (JIT + Just-Enough-Privilege)

---

## DEPENDENCY MATRIX
```
A1 (Async) → feeds → B3 (Parallel Swarm)
B1 (Caching) → feeds → B2 (Batching)
D1 (Wasmtime Real) → requires → D2 (Ed25519)
D2 (Ed25519) → same dep as → F1 (Real Ed25519)
C1 (WGPU) → independent
E1, E2, E3 (Yjs) → independent
F2 (Audit) → requires → F1 (Ed25519)
```

## AGENT ASSIGNMENTS
- **Agent Alpha (Rust Engine)**: A1 + A2 + A3 — Cargo.toml, ai.rs, ghost_session.rs, swarm.rs
- **Agent Beta (MCP/Swarm)**: B1 + B2 + B3 — mcp_bridge.rs, swarm.rs, kairo-mcp/server.js
- **Agent Gamma (WGPU)**: C1 + C2 — wgpu_effects.rs, mcp-servers/kairo-effects/
- **Agent Delta (WASM)**: D1 + D2 + D3 — wasm_sandbox.rs, Cargo.toml
- **Agent Epsilon (Security)**: F1 + F2 + F3 — identity.rs, governance.rs
- **Agent Zeta (Yjs)**: E1 + E2 + E3 — yjs_peer.rs
