# Handoff Report — Milestone 1 (CI/CD & Reliability Engineering)

This handoff report is prepared by the Explorer agent to document the investigation findings and recommended remediation strategy for Kairo Phantom's Milestone 1.

---

## 1. Observation

During read-only codebase discovery, the following exact paths, line numbers, configuration details, and commands were observed:

1.  **Global Keyboard Intercept Hotkey**:
    *   `repositories/kairo-phantom/phantom-core/src/hotkey.rs` defines the global keyboard hook callback:
        ```rust
        // Line 25
        pub fn register_hotkey_listener<F>(callback: F) -> Result<()>
        ```
        It intercepts key events. The target combination is hardcoded to `Alt+Ctrl+M`.
2.  **Deprecated Hotkey Triggers (`Alt+M`) in Workflows and Scripts**:
    *   **GUI Gauntlet Workflow**: `.github/workflows/gui_gauntlet.yml` triggers the daemon at Line 212 using `$wshell.SendKeys("%m")`. Here, `%m` represents `Alt+M`.
    *   **Notepad Test Scenario**: `tests/scripts/win/t11_notepad.py` calls the hotkey at Line 144 using `pyautogui.hotkey('alt', 'm')`.
    *   **Terminal Test Scenario**: `tests/scripts/win/t12_terminal.py` calls the hotkey at Line 92 using `pyautogui.hotkey('alt', 'm')`.
    *   **App scenario scripts** under `scripts/win/` (`scenario_word.py` line 131, `scenario_excel.py` line 94, `scenario_pptx.py` line 56, `scenario_notepad.py` lines 20/47/67, `scenario_terminal.py` lines 35/49/65/80/98, `scenario_vscode.py` lines 51/64/95/119/141/157, `kairo_test_utils.py` line 126) all call the hotkey using `pyautogui.hotkey('alt', 'm')` (or `pg.hotkey('alt', 'm')`).
3.  **Missing Integration Test Targets**:
    *   `.github/workflows/ci.yml` contains build steps for `test_cross_platform` (Line 86) and `test_domain11_e2e` (Line 90) but their target mappings are completely absent from `phantom-core/Cargo.toml`.
    *   The test source files themselves (`tests/platform/test_cross_platform.rs` and `tests/security/test_domain11_e2e.rs`) do not exist in the physical file system under `repositories/kairo-phantom/phantom-core/tests/`.
4.  **Incomplete Outcome Gate Checks**:
    *   `.github/workflows/ci.yml` defines the `production-gate` job starting at Line 172. It only checks for the existence of files and static strings (such as `THIRD_PARTY_NOTICES.md` or `install.sh`) but does not run any code to verify performance/resource indicators like the memory constraint `bmc@k`, task completion rates, or the API ceiling for VLM calls.

---

## 2. Logic Chain

1.  **Hotkey Issue**:
    *   *Step 1*: The Rust daemon intercepts `Alt+Ctrl+M` (Observation 1).
    *   *Step 2*: The test scripts and GitHub Actions workflows send `Alt+M` (Observation 2).
    *   *Conclusion*: Because the simulated keystrokes do not match the daemon's registered hotkey combination, the daemon is never triggered during automated execution, causing test timeouts or failures.
    *   *Remediation*: Refactor `%m` and `'alt', 'm'` calls to `^%m` and `'ctrl', 'alt', 'm'` across all test files and scenarios.
2.  **Missing Test Targets**:
    *   *Step 1*: The CI runner invokes `cargo test --test test_cross_platform` and `cargo test --test test_domain11_e2e` (Observation 3).
    *   *Step 2*: Neither the targets are declared in `Cargo.toml`, nor do the test files exist (Observation 3).
    *   *Conclusion*: Running the cargo commands results in build failures or target-not-found errors during the matrix build phase.
    *   *Remediation*: Add target sections to `Cargo.toml` and write correct, functional Rust integration tests inside `tests/platform/test_cross_platform.rs` and `tests/security/test_domain11_e2e.rs` to satisfy compilation.
3.  **Metric Enforcement**:
    *   *Step 1*: The production gate is purely static and file-based (Observation 4).
    *   *Step 2*: The project specifies strict requirements for reliability, memory limits (`bmc@k`), and LLM costs.
    *   *Conclusion*: A static file check allows broken implementations (such as memory leaks or loop stalls) to pass.
    *   *Remediation*: Integrate a python metric verification script `verify_production_metrics.py` into the `production-gate` job of `ci.yml` that checks the output of E2E JSON results and benchmarks.

---

## 3. Caveats

*   **GUI Display Environment**: Standard GitHub Actions headless environments will require display emulation/fallbacks (e.g. `xvfb` or windows autologon configuration) for GUI E2E tests, which must be addressed in detail during implementation by the implementer.
*   **Daemon Initialization Delay**: The daemon startup speed might require adjustment of timing sleep buffers (currently 3 seconds) depending on host system resource constraints.

---

## 4. Conclusion

Milestone 1 requires:
1.  Aligning all simulated keystrokes with the registered `Alt+Ctrl+M` hotkey combination to fix trigger failures.
2.  Adding missing integration targets (`test_cross_platform`, `test_domain11_e2e`) to `Cargo.toml` and writing corresponding verification tests.
3.  Enhancing the production gate check to dynamically verify the E2E task completion rate, memory threshold, and VLM call rate metrics using a dedicated python verification script.

---

## 5. Verification Method

Once implemented, the orchestrator/user can verify the changes by running:
1.  **Headless Smoke Tests**:
    ```bash
    cargo test --test layer1_unit_tests --test test_sentinel_retry
    ```
2.  **Cross-Platform Targets Compilation**:
    ```bash
    cargo test --test test_cross_platform --no-run
    cargo test --test test_domain11_e2e --no-run
    ```
3.  **Production Gate Verification Simulation**:
    ```bash
    python scripts/verify_production_metrics.py
    ```
    This script must output exit code `0` when all metrics (Completion Rate >= 80%, Memory <= 15MB, VLM Call Rate <= 1.2) are satisfied.
