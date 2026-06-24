# Kairo Phantom 100X Plan — Part 1: INFRA_PENDING.md

> **Items blocked by infrastructure limitations in the current sandbox.**
> Each item has the exact command to verify on proper hardware.
> Updated: 2026-06-24

---

## BLOCKED ITEMS

### 1. Opik self-hosted dashboard (Phase 0.1, Step 1)
- **Blocker**: Docker is not available in this sandbox
- **Impact**: Cannot run `docker compose up` for Opik self-hosted (localhost:5173)
- **Workaround**: Implement provenance receipt + observability emit layer writing to local file/queue sink (built on identity.rs). The receipt emission is real and tested. Only the dashboard UI is deferred.
- **Verification command (on real hardware)**:
  ```bash
  git clone https://github.com/comet-ml/opik.git /data/opik
  cd /data/opik && docker compose up -d
  curl http://localhost:5173  # Should return 200
  ```

### 2. Linux ghost-typing verification on a real display (Phase 0 — pre-existing)
- **Blocker**: No X11/Wayland display server in this sandbox
- **Impact**: `inject_replace_line()` and `erase_prompt()` in `LinuxPlatformInjector` are implemented via xdotool but cannot be runtime-verified without a display
- **Workaround**: Implementation is complete and compiles. At runtime, if xdotool is missing or no display is available, the methods log a loud error (never return silently).
- **Verification command (on real hardware)**:
  ```bash
  # Requires: xdotool installed, DISPLAY set, X11 or Wayland session active
  cargo test --bin kairo-phantom -- test_injector
  # Or manually: run kairo-phantom, trigger Alt+Ctrl+M in a text editor
  ```

### 3. Rust binary compilation memory limit (workspace --no-run)
- **Blocker**: Sandbox has 3.8GB RAM, 2 cores, no swap. Full workspace `cargo test --workspace --no-run` can OOM-kill the linker when compiling the kairo-phantom binary.
- **Impact**: Must compile binary tests separately (`cargo test --bin kairo-phantom --no-run`) which works but takes ~55s.
- **Workaround**: Use `CARGO_INCREMENTAL=0` and compile targets individually. All tests pass when compiled this way.
- **Verification command (on real hardware)**:
  ```bash
  cargo test --workspace  # Should complete without OOM on a machine with ≥8GB RAM
  ```
- **NOTE**: Full Rust suite (478 tests) IS reproducible in this sandbox by compiling targets individually. The OOM only affects the single `--workspace --no-run` command that tries to compile everything at once.

---

## RESOLVED ITEMS
(none yet)