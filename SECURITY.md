# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | ✅ Active security updates |
| 0.2.x   | ⚠️ Critical fixes only |
| < 0.2   | ❌ End of life |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues privately:

1. Go to the [GitHub Security Advisories](https://github.com/Kartik24Hulmukh/Kairo-Phantom/security/advisories/new) page for this repository.
2. Click **"Report a vulnerability"**.
3. Fill in the details: affected version, reproduction steps, and potential impact.

We will acknowledge your report within **48 hours** and provide a resolution timeline within **7 days**.

## Security Architecture

Kairo Phantom is designed with security as a core constraint:

- **Zero telemetry by default.** No data leaves your machine unless you explicitly configure a cloud LLM provider.
- **ToolGate enforcement.** All tool calls are validated against an explicit allowlist before execution. File access is restricted to `~/.kairo-phantom/` and explicitly approved paths.
- **SPIFFE identity.** Each internal agent carries a cryptographically signed SPIFFE ID verified at every inter-agent call boundary.
- **WASM sandbox.** Third-party plugins run in a Wasmtime sandbox with Ed25519 signature verification and capability bounding. A plugin cannot access the network or filesystem unless its manifest explicitly declares and the user approves those capabilities.
- **Sentinel sanitizer.** All AI-generated output is scanned for prompt injection, system prompt leakage, and PII before being typed into the active window.
- **No vendored secrets.** Kairo Phantom contains zero hardcoded API keys, tokens, or credentials. All cloud provider keys are stored in `~/.kairo-phantom/config.toml` (user-controlled, never committed to git).

## Disclosure Policy

We follow responsible disclosure. Once a fix is ready, we will:

1. Release a patched version.
2. Publish a GitHub Security Advisory with full details.
3. Credit the reporter (unless they prefer anonymity).
