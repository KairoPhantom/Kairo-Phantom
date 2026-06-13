# Premortem Failure Mode Tracker

*Required by the Foundation-First Hardening Plan constraints: "The premortem failure modes must be re-evaluated weekly."*

**Re-evaluate this file every Monday. Raise a blocking GitHub issue for any risk marked 🔴.**

---

## Evaluation Cadence

| Week | Date | Evaluator | Status |
|---|---|---|---|
| Week 0 (Baseline) | Pre-launch | @KairoPhantom | Identified 10 risks |
| Week 1 | 2026-06-03 | @Antigravity | Integrated CUA 1000x upgrades (World Model, Safety Gate, DP Federated Memory) |
| Week 2 | 2026-06-10 | @Antigravity | Completed facts verifier database validation and launch checklist audit |
| Week 3 | _fill in_ | | |
| Week 4 | _fill in_ | | |

---

## The 10 Failure Modes — Current Status

### 🟢 FM-1: Demo broken for 80% of first-time users
**Risk:** Windows-only; macOS/Linux users hit immediate crashes.
**Mitigation implemented:**
- `cargo install kairo-phantom` works on all 3 platforms (CI-verified)
- `KairoSetup.exe` one-click installer for Windows
- `xa11y` cross-platform accessibility layer active
- `.dmg` and `.AppImage` packaging in CI
- **VLM Local Grounding:** Integrated visual grounding in `vlm_grounding.py` for Canva CUA targeting coordinates
**Gate status:** ✅ CLOSED — cross-platform CI matrix passes, VLM-grounding fallback validated
**Watch for:** macOS Accessibility permission denial on fresh systems. Monitor `kairo status` error logs post-launch.

---

### 🟢 FM-2: Core reliability sacrificed for feature breadth
**Risk:** System-prompt leakage, broken `//` protocol, clipboard-only injection.
**Mitigation implemented:**
- `PromptParser::parse()` returns `None` for non-`//` text — enforced globally
- `SentinelSanitizer` on live hot-path, every LLM response scanned
- Adeu MCP bridge as primary injector (Track Changes preserved)
- Fallback chain: Adeu → safe-docx → clipboard
- **Phase 1.4 Schema Retry**: any DOCX/XLSX/PPTX parse failure retries LLM up to 2× with hardened schema hint before clipboard fallback (`main.rs` — `'docx_schema_retry` / `'xlsx_schema_retry` / `'pptx_schema_retry` labelled loops)
- **Facts Verification CLI**: Integrated `Kairo.facts` database verifying 36 implemented capabilities with cross-platform validation
- 787 tests passing, 0 failures
**Gate status:** ✅ CLOSED — CLI facts verifier passes cleanly
**Watch for:** New LLM models that leak differently. Run `cargo test` on every model upgrade.

---

### 🟢 FM-3: No macOS/Linux support at launch
**Risk:** Lost the viral open-source audience.
**Mitigation implemented:**
- CI matrix: `windows-latest`, `macos-latest`, `ubuntu-latest`
- Platform-specific hotkey registration (CGEvent / X11)
- macOS Accessibility permission handled in `Info.plist`
**Gate status:** ✅ CLOSED
**Watch for:** macOS permission prompts failing on new OS versions (Sequoia, etc.)

---

### 🟢 FM-4: Security audit deferred
**Risk:** OpenClaw's disaster tainted the category; our audit was deferred.
**Mitigation implemented:**
- `docs/security/SECURITY_AUDIT.md` — clean Decepticon audit report
- `docs/security/OWASP_AGENTIC_TOP10_COMPLIANCE.md` — 10/10 controls
- Prompt injection firewall (50 detectors, 6 layers)
- SHA-256 audit chain (`enterprise/audit.db`)
- SPIFFE Ed25519 identity per agent
**Gate status:** ✅ CLOSED
**Watch for:** New OWASP Agentic AI guidance (check owasp.org quarterly). New prompt injection vectors.

---

### 🟢 FM-5: Memory benchmark invisible
**Risk:** Impressive but never published.
**Mitigation implemented:**
- `docs/benchmark/KMB1_BLOG_POST.md` published
- `phantom-core/benches/memory_benchmark.rs` open-sourced (Criterion)
- `phantom-core/tests/core/test_memory_benchmark.rs` — 6 gate tests (CI)
- KMB-1 score: 0.8905 (CI) / 0.9872 (with `--features local-embeddings`)
**Gate status:** ✅ CLOSED
**Watch for:** Score regression below 0.88 gate in CI (`cargo test --test test_memory_benchmark`)

---

### 🟢 FM-6: Enterprise procurement blocked
**Risk:** Missing SOC 2 docs and SSO.
**Mitigation implemented:**
- `docs/enterprise/SOC2_READINESS.md` — Trust Service Criteria mapping
- Audit logging with SHA-256 chain
- SSO integration documented
- Data-residency guarantees documented (all data local by default)
**Gate status:** ✅ CLOSED
**Watch for:** Actual enterprise prospects asking for a live SOC 2 Type II report. Plan Type II audit for v1.0.

---

### 🟡 FM-7: Google Magic Pointer captured the narrative
**Risk:** Zero marketing; competitor set the frame.
**Mitigation implemented:**
- `docs/launch/LAUNCH_KIT.md` — Show HN post, 4 Reddit posts, Product Hunt
- `docs/launch/VIDEO_SCRIPT.md` — 90-second launch video script
- Privacy-first positioning ("your data never leaves your machine")
**Gate status:** 🟡 PARTIAL — Launch kit ready, actual posts not yet executed
**Action required:** Execute launch sequence on Day 35 per LAUNCH_KIT.md
**Watch for:** Timing — don't launch on a Friday. Don't launch the same week as a major AI announcement.

---

### 🟢 FM-8: Waza Skills marketplace had zero community agents
**Risk:** No discovery, no builder tools.
**Mitigation implemented:**
- `kairo skill new` CLI scaffolds a new agent
- `kairo skill list`, `add`, `rm`, `test` commands
- 5 seed agents: legal-review, academic-editor, marketing-copywriter, code-reviewer, medical-scribe
- `docs/launch/WAZA_TUTORIAL.md` — 10-minute builder guide
- GitHub issue templates with `good first issue` label
**Gate status:** ✅ CLOSED
**Watch for:** Community adoption. Track PRs with `waza` label. Goal: 20 community agents by 6 months post-launch.

---

### 🟢 FM-9: One-click installer didn't exist
**Risk:** 12 manual steps to first ghost-write.
**Mitigation implemented:**
- `installer/KairoSetup.iss` — Windows NSIS installer (installs Ollama, pulls model, starts daemon)
- `scripts/package-macos.sh` — `.dmg` builder
- `scripts/package-linux.sh` — `.AppImage` and `.deb` builder
- `install.sh` — Linux apt repository installer
- `docs/QUICKSTART.md` — 60-second quickstart guide
**Gate status:** ✅ CLOSED
**Watch for:** Ollama download timeouts on slow connections. Add progress indicator to installer.

---

### 🟡 FM-10: Founder burnout chasing 100× instead of 1.0
**Risk:** Product still fails 20% of the time on basic operations.
**Mitigation implemented:**
- Phase 1 gate enforced: no new features until 768 tests pass
- W1–W10, E1–E7, P1–P7 scenario coverage
- `#[cfg(feature = "advanced")]` flag guards unfinished domain work
- Weekly premortem re-evaluation (this document)
**Gate status:** 🟡 MONITOR — Tests pass; real-world 20% failure rate not yet measured
**Action required:** Set up telemetry (opt-in) to measure actual accept/reject rate post-launch
**Watch for:** Community bug reports clustering around a specific scenario. First 10 issues are the product's truth.

---

## Risk Heatmap

```
         │ Likelihood of occurring
Severity │  Low      Medium     High
─────────┼──────────────────────────────
Critical │  FM-2     FM-4       
High     │  FM-5     FM-10      FM-7
Medium   │  FM-8     FM-1       FM-6
Low      │  FM-9     FM-3       
```

---

## Action Items This Week

| # | Action | Owner | Due |
|---|---|---|---|
| 1 | Execute launch sequence (FM-7) | @KairoPhantom | Day 35 |
| 2 | Set up opt-in telemetry for accept/reject rate (FM-10) | Engineering | v0.4 |
| 3 | Record demo GIF (FM-1) | @KairoPhantom | Day 34 |
| 4 | Plan SOC 2 Type II audit (FM-6) | @KairoPhantom | v1.0 planning |

---

## How to Raise a Blocking Issue

If any FM reverts to 🔴:

1. Open a GitHub issue with title: `[BLOCKING] FM-N: <description>`
2. Label it `premortem-blocker` and `p0`
3. Tag `@KairoPhantom`
4. Do not merge PRs or ship new features until the blocking issue is resolved

---

*This document is part of the Foundation-First Hardening Plan constraints. Last updated: 2026-06-12.
