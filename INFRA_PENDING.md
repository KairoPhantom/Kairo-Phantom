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
- **NOTE**: Full Rust suite (591 tests) IS reproducible in this sandbox by compiling targets individually. The OOM only affects the single `--workspace --no-run` command that tries to compile everything at once.

---

### 5. pdf_oxide not installed (Domain 4 — PDF Enhancement)
- **Blocker**: `pdf_oxide` (MIT-licensed pure-Rust PDF parser) is not available as a pip package in this sandbox
- **Impact**: Cannot run pdf_oxide vs PyMuPDF comparison tests on real fixtures
- **Workaround**: 4 comparison tests are marked `pytest.mark.skip(reason='pdf_oxide not installed')`. Routing table is documented and tested. All other Domain 4 tests (82 passed) use PyMuPDF (real, not mocked).
- **Verification command (on hardware with pdf_oxide)**:
  ```bash
  pip install pdf_oxide
  python3 -m pytest test_domain4_pdf.py::TestPdfOxideComparison -v --tb=short -p no:asyncio
  # Remove the skip marks or set env var KAIRO_PDF_OXIDE=1 to activate
  ```

### 6. Live paperless-ngx + Karakeep integration (Phase 0.7)
- **Blocker**: Docker is not available in this sandbox — cannot run paperless-ngx or Karakeep instances
- **Impact**: Bridge logic is tested against mock HTTP servers (clearly labeled as non-production).
  Live integration against real services is not verified here.
- **Workaround**: Bridge code is REAL (real urllib HTTP client, real auth, real JSON parsing).
  Mock servers simulate the API responses. The bridges FAIL LOUDLY (raise ConnectionError)
  when the real service is unreachable — they never silently no-op or fake success.
- **Verification command (on real hardware with Docker)**:
  ```bash
  # Start paperless-ngx
  docker compose up -d  # with paperless-ngx docker-compose.yml
  export KAIRO_CONNECTORS=paperless
  export PAPERLESS_URL=http://localhost:8000
  export PAPERLESS_TOKEN=<real_token>
  python3 -m pytest test_phase0_7_bridges.py -v  # All tests should pass against real service

  # Start Karakeep
  docker run -p 3000:3000 karakeep/karakeep
  export KAIRO_CONNECTORS=karakeep
  export KARAKEEP_URL=http://localhost:3000
  export KARAKEEP_TOKEN=<real_token>
  python3 -m pytest test_phase0_7_bridges.py -v
  ```
- **RESOLVED**: fastembed AllMiniLML6-v2 (86MB ONNX) successfully downloaded via scripts/download_models.sh
  - Model cached in ~/.cache/fastembed/ — subsequent runs work offline
  - Semantic relevance test passes: `cargo test --lib -p phantom-core embedding --features local-embeddings → 12 passed`
  - fastembed upgraded from v3 to v4 to fix ort-sys/ureq TLS compile error
  - For air-gap: copy ~/.cache/fastembed/ to air-gapped machine, then run with --features local-embeddings