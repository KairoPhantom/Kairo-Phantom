# 🗺️ Kairo Phantom - 6-Month Roadmap

Kairo Phantom is rapidly evolving from a proof-of-concept into the definitive open-source document intelligence layer. This roadmap outlines our vision for the next 6 months.

## Phase 1: Stability & The Core Experience (Current - Month 1)
- [x] Panic-proof Rust engine with deterministic simulation testing.
- [x] Secure WASM Sandbox (Wasmtime JIT) for plugins.
- [x] Cross-platform Ghost Typing (Windows UIAutomation, macOS AXUIElement/CGEvent, Linux X11/Wayland shims).
- [ ] **Canary Beta (v0.4.0-beta.1)**: Harden against real-world OS idiosyncrasies.

## Phase 2: Enhanced Interoperability (Months 2-3)
- **Advanced Linux Support**: First-class Wayland protocol support for background ghost typing without relying on XWayland fallbacks.
- **Mobile Companion App**: A seamless way to send context from your phone to your desktop's Kairo Swarm.
- **Cross-Platform Clipboard sync**: Native memory synchronization allowing context sharing across physically separated devices on a local network.

## Phase 3: The Plugin Ecosystem (Months 4-5)
- **Community Plugin Registry**: A decentralized package manager for Kairo WASM plugins, protected by Ed25519 signatures.
- **Multi-Modal Native Overlay**: Allowing users to drag-and-drop images directly onto the Tauri glassmorphic overlay for instant `gpt-4o` or `llava` multimodal reasoning.
- **Memory Nexus API**: Expose the FoundationDB/SurrealDB graph to third-party tools, allowing your CRM or IDE to query Kairo's semantic knowledge base.

## Phase 4: Enterprise Integrations (Month 6)
- **Enterprise SSO & Audit Logs**: Integration with SAML/OIDC and strict compliance logging.
- **Air-Gapped Operation Mode**: Official support and documentation for deploying Kairo Phantom entirely offline inside classified or secure enterprise environments using local models (Ollama/vLLM) only.
- **Swarm Clustering**: Allow multiple instances of Kairo across an organization to share a synchronized Swarm Brain and peer-to-peer Yjs context.

---
*Note: This roadmap is a living document. We prioritize based on community feedback via GitHub Discussions and Discord.*
