# Codebase Concerns

**Analysis Date:** 2026-05-10

## Tech Debt

**Real-world E2E surface is split across a thin manifest and several standalone demos:**
- Issue: The official dispatcher only executes a narrow subset of tests, while other app scenarios exist as separate scripts or docs.
- Files: [`dispatch_gauntlet.ps1`](dispatch_gauntlet.ps1), [`test_manifest.json`](test_manifest.json), [`agent_runner.js`](agent_runner.js), [`scripts/e2e_windows_t1.py`](scripts/e2e_windows_t1.py), [`scripts/e2e_yjs_t4.py`](scripts/e2e_yjs_t4.py)
- Impact: The roadmap reads as if the whole matrix is runnable, but the actual automated surface is only partially wired.
- Fix approach: Consolidate the runnable scenarios under one manifest and fail the gauntlet when a declared scenario file is missing.

**App-awareness exists at the routing layer, but not as verified desktop automation for most targets:**
- Issue: `phantom-core` knows about Word, PowerPoint, Excel, VS Code, Terminal, Notepad, and browsers in formatting/routing logic, but that does not mean each app has a physical E2E script.
- Files: [`phantom-core/src/ai.rs`](phantom-core/src/ai.rs), [`phantom-core/tests/layer2_property_tests.rs`](phantom-core/tests/layer2_property_tests.rs), [`phantom-core/tests/layer4_e2e_tests.rs`](phantom-core/tests/layer4_e2e_tests.rs)
- Impact: App support can be overstated if the report treats prompt formatting or agent routing as end-to-end coverage.
- Fix approach: Add one real desktop automation per app family and keep routing tests separate from GUI tests.

## Known Bugs

**Manifest entries reference scripts that are not present in the repo tree:**
- Symptoms: The gauntlet advertises `t2`, `t3`, `t5`, `t6`, `t7`, `t8`, and `t10`, but the `tests/scripts/win` tree only contains `t1_word.py` and `chaos_advanced.ps1`.
- Files: [`test_manifest.json`](test_manifest.json), [`tests/scripts/win`](tests/scripts/win), [`tests/scripts/browser`](tests/scripts/browser)
- Trigger: Running `dispatch_gauntlet.ps1` or `agent_runner.js` against the manifest as written.
- Workaround: The runner skips missing scripts instead of failing hard.

**The browser path is a mock/stub rather than a true remote-document integration test:**
- Symptoms: The browser automation creates a local contenteditable page and does not exercise a live Google Docs or Yjs-backed session.
- Files: [`scripts/e2e_yjs_t4.py`](scripts/e2e_yjs_t4.py), [`tests/scripts/browser/t4_yjs_google_docs.js`](tests/scripts/browser/t4_yjs_google_docs.js)
- Trigger: Browser scenario T4 runs.
- Workaround: None in the current script; it prints PASS after the local DOM interaction.

## Security Considerations

**Chaos scripts can alter machine/network state during test execution:**
- Risk: The chaos monkey calls network release/renew, clears clipboard contents, spawns CPU load, and adds/removes a firewall rule.
- Files: [`scripts/chaos_windows_advanced.ps1`](scripts/chaos_windows_advanced.ps1), [`tests/scripts/win/chaos_advanced.ps1`](tests/scripts/win/chaos_advanced.ps1)
- Current mitigation: The scripts target the local machine and are intended for CI or controlled test hosts only.
- Recommendations: Guard these scripts behind an explicit opt-in flag and keep them out of default local runs.

## Fragile Areas

**The real-world GUI matrix is mostly aspirational outside Word and browser demos:**
- Files: [`test-realworld.md`](test-realworld.md), [`AGENT_MEMORY.md`](AGENT_MEMORY.md), [`dispatch_gauntlet.ps1`](dispatch_gauntlet.ps1)
- Why fragile: The docs define Word, PowerPoint, Excel, VS Code, Chrome, Notepad, and Terminal coverage, but the runnable files do not yet back that up.
- Safe modification: Add one script per application family and keep each script self-validating with screenshot/log output on failure.
- Test coverage: Only Word and browser automation are present as executable paths; PowerPoint, Excel, VS Code, and Terminal lack corresponding desktop scripts.

## Missing Critical Features

**Physical desktop coverage for PowerPoint, Excel, VS Code, and Terminal is absent:**
- Problem: There is no on-disk GUI automation that opens `powerpnt.exe`, `excel.exe`, `code.exe`, or `wt.exe` and performs Alt+M verification.
- Blocks: The roadmap scenarios P1-P7, E1-E5, V1-V6, and Terminal behavior remain unproven at the desktop layer.

**Notepad coverage exists only as a standalone demo script, not as part of the primary gauntlet:**
- Problem: `scripts/e2e_windows_t1.py` opens Notepad and sends Alt+M, but the dispatcher does not route it.
- Blocks: Notepad is not part of the current official test matrix.

## Test Coverage Gaps

**Missing app-specific automation scripts:**
- What's not tested: PowerPoint deck creation/editing, Excel formula/data cleanup, VS Code code generation/refactoring, and Windows Terminal command assistance.
- Files: [`test-realworld.md`](test-realworld.md), [`test_manifest.json`](test_manifest.json), [`dispatch_gauntlet.ps1`](dispatch_gauntlet.ps1)
- Risk: The product can claim broad app support without proving those flows on the desktop.
- Priority: High

**Missing live browser integration:**
- What's not tested: A real browser-backed Google Docs or Yjs session with networked state.
- Files: [`scripts/e2e_yjs_t4.py`](scripts/e2e_yjs_t4.py), [`tests/scripts/browser/t4_yjs_google_docs.js`](tests/scripts/browser/t4_yjs_google_docs.js)
- Risk: The current PASS can be achieved without external collaboration state or a live browser document.
- Priority: Medium

**Missing manifest enforcement:**
- What's not tested: The dispatcher does not fail when a manifest entry points to a missing script.
- Files: [`dispatch_gauntlet.ps1`](dispatch_gauntlet.ps1), [`agent_runner.js`](agent_runner.js), [`test_manifest.json`](test_manifest.json)
- Risk: A green run can hide absent scenarios.
- Priority: High

---

*Concerns audit: 2026-05-10*
